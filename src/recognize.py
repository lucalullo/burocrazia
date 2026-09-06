from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable

from rapidfuzz import fuzz

from src.models import (
    AdministrativeDocument,
    CatalogRecognitionResult,
    DocumentFamily,
    FamilyRecognitionResult,
    RecognitionResult,
)


MIN_CONFIDENCE = 70.0
MIN_SCORE_MARGIN = 5.0
RULES_VERSION = "deterministic-2"

# Evidence points for the MVP. They are intentionally centralized and are not a
# scientifically calibrated probability model.
WEIGHTS = {
    "exact_code": 75.0,
    "title": 70.0,
    "entity": 10.0,
    "keywords": 70.0,
    "general_similarity": 15.0,
}
MIN_TITLE_SIMILARITY = 75.0
MIN_STRONG_TITLE_SIMILARITY = 90.0
MIN_FAMILY_CONFIDENCE = 75.0
MIN_FAMILY_SCORE_MARGIN = 8.0
MIN_FAMILY_IDENTIFYING_PHRASES = 2
ENTITY_CONFLICT_PENALTY = 40.0
VERSION_CONFLICT_PENALTY = 80.0
DISTINCT_ENTITY_NAMES = (
    "Agenzia delle Entrate",
    "Agenzia delle Entrate-Riscossione",
    "INPS",
    "INAIL",
    "Ispettorato Nazionale del Lavoro",
    "Ministero delle Infrastrutture e dei Trasporti",
    "Garante per la protezione dei dati personali",
)
ENTITY_ALIASES = {
    "istituto nazionale della previdenza sociale": "inps",
    "istituto nazionale per l assicurazione contro gli infortuni sul lavoro": "inail",
    "ader": "agenzia delle entrate riscossione",
}
YEAR_PATTERN = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")
ANNUAL_MODEL_PATTERNS = {
    "730": re.compile(
        r"(?<!\w)(?:modello\s+)?730\s*(?:[/_-]\s*)?((?:19|20)\d{2})(?!\d)",
        re.IGNORECASE,
    ),
    "cu": re.compile(
        r"(?<!\w)(?:certificazione\s+unica|modello\s+cu|cu)"
        r"\s*(?:[/_-]\s*)?((?:19|20)\d{2})(?!\d)",
        re.IGNORECASE,
    ),
}
# OCR tolerance is restricted to family evidence. These substitutions never
# establish an exact code or a catalogued year.
OCR_730_PATTERN = re.compile(r"(?<!\w)7\s*3\s*[0o](?!\w)", re.IGNORECASE)
OCR_CU_PATTERN = re.compile(
    r"(?<!\w)(?:cert[il1]f[il1]caz[il1][o0]ne\s*un[il1]ca|c[ .\t]+u)(?![a-z])",
    re.IGNORECASE,
)
OCR_MODEL_PATTERN = re.compile(r"\bm[o0]de[li1]{2}[o0]\b", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class _CandidateScore:
    document: AdministrativeDocument
    score: float
    signals: tuple[str, ...]
    strong_evidence: bool
    evidence_rank: int
    entity_conflict: bool
    identity_evidence: bool
    conflicts: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _FamilyCandidateScore:
    family: DocumentFamily
    score: float
    identifying_phrase_count: int
    signals: tuple[str, ...]
    conflicts: tuple[str, ...] = ()


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    normalized = normalized.replace("\u00ad", "").replace("_", " ")
    normalized = re.sub(r"[^\w\s]", " ", normalized, flags=re.UNICODE)
    return re.sub(r"\s+", " ", normalized).strip()


def _contains_phrase(normalized_text: str, phrase: str | None) -> bool:
    normalized_phrase = normalize_text(phrase or "")
    if not normalized_phrase:
        return False
    return f" {normalized_phrase} " in f" {normalized_text} "


def _detect_entities(
    normalized_text: str,
    entity_names: Iterable[str],
) -> frozenset[str]:
    matched = {
        normalized_entity
        for entity in entity_names
        if (normalized_entity := normalize_text(entity))
        and _contains_phrase(normalized_text, normalized_entity)
    }
    matched.update(canonical for alias, canonical in ENTITY_ALIASES.items() if _contains_phrase(normalized_text, alias))
    # Quando un nome è contenuto in uno più specifico, conserva il più lungo:
    # "Agenzia delle Entrate" non equivale a "...-Riscossione".
    return frozenset(
        entity
        for entity in matched
        if not any(
            entity != other and _contains_phrase(other, entity)
            for other in matched
        )
    )


def _is_distinctive_title(normalized_title: str) -> bool:
    tokens = normalized_title.split()
    return len(tokens) >= 2 and len(normalized_title) >= 6


def _annual_model_years(text: str) -> dict[str, frozenset[str]]:
    return {
        model: frozenset(
            match.group(1) for match in pattern.finditer(text)
            if not _is_incidental_reference(text, match.start())
        )
        for model, pattern in ANNUAL_MODEL_PATTERNS.items()
    }


def _is_incidental_reference(text: str, start: int) -> bool:
    prefix = normalize_text(text[max(0, start - 60):start])
    return bool(re.search(
        r"\b(?:protocollo|prot|fattura|pratica|ricevuta|importo|pagina|articolo)"
        r"(?:\s+(?:n|numero))?$", prefix,
    ))


def _candidate_annual_model(document: AdministrativeDocument) -> str | None:
    identity = " ".join(
        part for part in (document.codice, document.titolo_ufficiale) if part
    )
    contextual_years = _annual_model_years(identity)
    for model, years in contextual_years.items():
        if years:
            return model

    normalized_identity = normalize_text(identity)
    if re.search(r"\b730\b", normalized_identity):
        return "730"
    if (
        _contains_phrase(normalized_identity, "certificazione unica")
        or re.search(r"\bcu\b", normalized_identity)
    ):
        return "cu"
    return None


def _is_plain_annual_model(document: AdministrativeDocument, model: str) -> bool:
    title = normalize_text(document.titolo_ufficiale)
    base = r"(?:modello )?730" if model == "730" else r"(?:certificazione unica|(?:modello )?cu)"
    return bool(re.fullmatch(base + r"(?: (?:19|20)\d{2})?", title))


def _annual_model_is_mentioned(text: str, model: str) -> bool:
    normalized = normalize_text(text)
    if model == "730":
        return bool(re.search(r"\b(?:modello\s+)?730\b", normalized) or OCR_730_PATTERN.search(text))
    return _contains_phrase(normalized, "certificazione unica") or bool(
        re.search(r"\bcu\b", normalized) or OCR_CU_PATTERN.search(text)
    )


def _annual_family_alias(text: str, family_name: str, entity_match: bool) -> tuple[bool, bool]:
    """Return (supported family, OCR-only evidence), without inferring a year."""
    normalized = normalize_text(text)
    years = _annual_model_years(text)
    if family_name == "modello 730":
        exact = bool(years["730"]) or _contains_phrase(normalized, "modello 730")
        marker = OCR_730_PATTERN.search(text)
        noisy = bool(marker and not _is_incidental_reference(text, marker.start())) and (
            bool(OCR_MODEL_PATTERN.search(text))
            or (entity_match and marker.group().casefold() != "730")
            or _contains_phrase(normalized, "dichiarazione dei redditi")
        )
    elif family_name == "certificazione unica":
        exact = bool(years["cu"]) or _contains_phrase(normalized, "certificazione unica") or (
            bool(re.search(r"\bcu\b", normalized)) and entity_match
        )
        noisy = bool(OCR_CU_PATTERN.search(text)) and (
            "cert" in normalized or entity_match
            or _contains_phrase(normalized, "sostituto d imposta")
        )
    else:
        return False, False
    return exact or noisy, noisy and not exact


def _local_entity_conflict(text: str, entity: str) -> bool:
    """Reject another explicit local authority, including one outside the catalog.

    Only headings or text after a sentence boundary are considered; a generic
    reference such as 'comune di residenza' must not become an invented issuer.
    """
    normalized_entity = normalize_text(entity)
    prefix = next((part for part in ("comune di ", "provincia di ", "regione ") if normalized_entity.startswith(part)), None)
    if prefix is None:
        return False
    headings = re.split(r"[\n\r;]", text)
    for heading in headings:
        normalized_heading = normalize_text(heading)
        if normalized_heading.startswith(prefix):
            suffix = normalized_heading[len(prefix):]
            if not suffix or suffix.startswith(("residenza", "nascita", "domicilio")):
                continue
            if not _contains_phrase(normalized_heading, normalized_entity):
                return True
    return False


def _generic_version_context(
    text: str,
    document: AdministrativeDocument,
    candidate_years: frozenset[str],
) -> tuple[frozenset[str], bool]:
    normalized_text = normalize_text(text)
    normalized_title = normalize_text(document.titolo_ufficiale)
    base_title = YEAR_PATTERN.sub(" ", normalized_title)
    base_title = re.sub(r"\s+", " ", base_title).strip()
    base_present = _is_distinctive_title(base_title) and _contains_phrase(
        normalized_text, base_title
    )
    observed: set[str] = set()
    contextual_bases: list[str] = []
    if base_present:
        contextual_bases.append(base_title)

    normalized_code = normalize_text(document.codice or "")
    if (
        normalized_code
        and not YEAR_PATTERN.search(normalized_code)
        and len(normalized_code) >= 2
        and _contains_phrase(normalized_text, normalized_code)
    ):
        contextual_bases.append(normalized_code)

    for base in contextual_bases:
        escaped_base = re.escape(base).replace(r"\ ", r"\s+")
        for pattern in (
            rf"(?:^|\s){escaped_base}\s+((?:19|20)\d{{2}})(?=\s|$)",
            rf"(?:^|\s)((?:19|20)\d{{2}})\s+{escaped_base}(?=\s|$)",
        ):
            observed.update(re.findall(pattern, normalized_text))

    model_present = bool(contextual_bases)
    if observed:
        return frozenset(observed), model_present
    if candidate_years and model_present:
        # The annual document type is present but its catalogued year is not.
        return frozenset(), True
    return frozenset(), False


def _annual_version_evidence(
    text: str,
    document: AdministrativeDocument,
) -> tuple[bool, bool]:
    """Return (consistent alias, conflict) for contextual annual models."""
    # An explicitly labelled revision is evidence of a version, unlike a date
    # appearing elsewhere in the document. Missing metadata cannot confirm it.
    revisions = {
        value.casefold() for value in re.findall(
            r"\b(?:versione|version|revisione|rev\.)\s*[:=]?\s*(\d+(?:[.]\d+)+)\b",
            text, flags=re.IGNORECASE,
        )
    }
    if revisions and revisions != {(document.versione or "").strip().casefold()}:
        return False, True
    candidate_identity = " ".join(
        part for part in (document.titolo_ufficiale, document.versione) if part
    )
    candidate_years = frozenset(YEAR_PATTERN.findall(candidate_identity))
    model = _candidate_annual_model(document)
    if model is not None:
        observed_years = _annual_model_years(text)[model]
        if not observed_years:
            missing_version = bool(candidate_years) and _annual_model_is_mentioned(
                text, model
            )
            return False, missing_version
        if len(candidate_years) != 1 or len(observed_years) != 1:
            return False, True
        consistent = observed_years == candidate_years
        return consistent and _is_plain_annual_model(document, model), not consistent

    if not candidate_years:
        return False, False
    observed_years, model_mentioned = _generic_version_context(
        text, document, candidate_years
    )
    if not observed_years:
        return False, model_mentioned
    consistent = len(candidate_years) == len(observed_years) == 1 and observed_years == candidate_years
    # A contextual year validates the version; it does not prove a missing
    # subtype or replace the title of a generic annual document.
    return False, not consistent


def _score_candidate(
    original_text: str,
    normalized_text: str,
    document: AdministrativeDocument,
    detected_entities: frozenset[str],
) -> _CandidateScore:
    score = 0.0
    signals: list[str] = []

    annual_alias_match, version_conflict = _annual_version_evidence(
        original_text, document
    )

    exact_code = bool(
        document.codice and _contains_phrase(normalized_text, document.codice)
    )
    if exact_code:
        score += WEIGHTS["exact_code"]
        signals.append("codice esatto")

    normalized_title = normalize_text(document.titolo_ufficiale)
    exact_title = _contains_phrase(normalized_text, document.titolo_ufficiale)
    if exact_title or annual_alias_match:
        title_similarity = 100.0
    else:
        title_similarity = float(fuzz.partial_ratio(normalized_title, normalized_text))
        # partial_ratio alone gives 100 when only one word of a long title is
        # supplied. Require coverage of the candidate title before using it.
        title_tokens = set(normalized_title.split())
        covered_tokens = title_tokens & set(normalized_text.split())
        if title_tokens and len(covered_tokens) / len(title_tokens) < 0.7:
            title_similarity = min(title_similarity, MIN_TITLE_SIMILARITY - 1)
    if title_similarity >= MIN_TITLE_SIMILARITY:
        score += WEIGHTS["title"] * title_similarity / 100.0
        signals.append("modello e versione" if annual_alias_match else "titolo")

    normalized_entity = normalize_text(document.ente)
    entity_match = normalized_entity in detected_entities
    entity_conflict = (bool(detected_entities) and not entity_match) or _local_entity_conflict(original_text, document.ente)
    if entity_match:
        score += WEIGHTS["entity"]
        signals.append("ente")

    keyword_count = len(document.parole_chiave)
    matched_keywords = sum(
        1
        for keyword in document.parole_chiave
        if _contains_phrase(normalized_text, keyword)
    )
    if keyword_count and matched_keywords:
        score += WEIGHTS["keywords"] * matched_keywords / keyword_count
        signals.append("parole chiave")

    distinctive_title = _is_distinctive_title(normalized_title)
    strong_keywords = (
        matched_keywords >= 2
        and keyword_count > 0
        and matched_keywords / keyword_count >= 2 / 3
    )
    if annual_alias_match:
        evidence_rank = 4 if exact_code else 3
    elif exact_code and exact_title and distinctive_title:
        evidence_rank = 4
    elif exact_title and distinctive_title:
        evidence_rank = 3
    elif exact_code:
        evidence_rank = 2
    elif (
        title_similarity >= MIN_STRONG_TITLE_SIMILARITY
        and distinctive_title
        and entity_match
    ) or strong_keywords:
        evidence_rank = 1
    else:
        evidence_rank = 0
    strong_evidence = evidence_rank > 0
    annual_model = _candidate_annual_model(document)
    identity_evidence = strong_evidence or bool(annual_model and _annual_model_is_mentioned(original_text, annual_model))
    if annual_model and not _is_plain_annual_model(document, annual_model) and exact_code and normalize_text(document.codice or "") == annual_model and not exact_title:
        strong_evidence = False
        evidence_rank = 0
    conflicts: list[str] = []
    if entity_conflict:
        score -= ENTITY_CONFLICT_PENALTY
        strong_evidence = False
        evidence_rank = 0
        if identity_evidence:
            conflicts.append("ente incompatibile")
    if version_conflict:
        score -= VERSION_CONFLICT_PENALTY
        strong_evidence = False
        evidence_rank = 0
        if identity_evidence:
            conflicts.append("annualità assente, ambigua o incompatibile")

    signature = normalize_text(
        " ".join(
            part
            for part in (
                document.ente,
                document.titolo_ufficiale,
                " ".join(document.parole_chiave),
            )
            if part
        )
    )
    general_similarity = float(fuzz.token_set_ratio(signature, normalized_text))
    if general_similarity:
        score += WEIGHTS["general_similarity"] * general_similarity / 100.0
        signals.append("similarità generale")

    bounded_score = round(min(100.0, max(0.0, score)), 1)
    return _CandidateScore(
        document,
        bounded_score,
        tuple(signals),
        strong_evidence,
        evidence_rank,
        entity_conflict,
        identity_evidence,
        tuple(conflicts),
    )


def recognize_document(
    text: str,
    documents: Iterable[AdministrativeDocument],
    *,
    min_confidence: float = MIN_CONFIDENCE,
    known_entities: Iterable[str] = (),
) -> RecognitionResult:
    if not 0.0 <= min_confidence <= 100.0:
        raise ValueError("La soglia di confidenza deve essere compresa tra 0 e 100.")

    normalized_text = normalize_text(text)
    if not normalized_text:
        return RecognitionResult(recognized=False, confidence=0.0, reason="Nessun testo leggibile disponibile.")

    document_list = list(documents)
    # Anche l'ente di un record rifiutato resta noto: escludere il documento
    # operativo non deve indebolire la protezione contro un emittente errato.
    detected_entities = _detect_entities(
        normalized_text,
        (
            *(document.ente for document in document_list),
            *known_entities,
            *DISTINCT_ENTITY_NAMES,
        ),
    )
    candidates = sorted(
        (
            _score_candidate(text, normalized_text, document, detected_entities)
            for document in document_list
            if document.stato_verifica != "rifiutato"
        ),
        key=lambda candidate: candidate.score,
        reverse=True,
    )
    if not candidates:
        return RecognitionResult(recognized=False, confidence=0.0, reason="Nessun documento nel catalogo considerato.")

    conflicts = tuple(sorted({conflict for candidate in candidates for conflict in candidate.conflicts}))
    candidate_ids = tuple(sorted({candidate.document.id for candidate in candidates if candidate.identity_evidence and candidate.document.id is not None}))

    eligible = [
        candidate
        for candidate in candidates
        if candidate.strong_evidence and not candidate.entity_conflict
    ]
    if not eligible:
        return RecognitionResult(
            recognized=False, confidence=candidates[0].score,
            matched_signals=candidates[0].signals if candidates[0].identity_evidence else (),
            reason="Conflitti di ente o annualità impediscono l'identificazione specifica." if conflicts else "Evidenze insufficienti per identificare un documento specifico.",
            conflicts=conflicts, candidate_ids=candidate_ids,
        )

    strongest_rank = max(candidate.evidence_rank for candidate in eligible)
    strongest = [
        candidate for candidate in eligible if candidate.evidence_rank == strongest_rank
    ]
    best = strongest[0]
    runner_up_score = strongest[1].score if len(strongest) > 1 else 0.0
    has_clear_margin = best.score - runner_up_score >= MIN_SCORE_MARGIN
    recognized = best.score >= min_confidence and has_clear_margin
    reason = (
        "Documento sostenuto dai segnali e dai vincoli di ente e annualità."
        if recognized else "Punteggio inferiore alla soglia del documento."
        if best.score < min_confidence else "Candidati specifici troppo vicini: identità ambigua."
    )

    return RecognitionResult(
        recognized=recognized,
        confidence=best.score,
        document=best.document if recognized else None,
        matched_signals=best.signals,
        reason=reason,
        conflicts=() if recognized else conflicts,
        score_margin=round(best.score - runner_up_score, 1),
        candidate_ids=candidate_ids,
    )


def _score_family(
    original_text: str,
    normalized_text: str,
    family: DocumentFamily,
    detected_entities: frozenset[str],
) -> _FamilyCandidateScore:
    if family.stato_verifica != "verificato":
        return _FamilyCandidateScore(family, 0.0, 0, ())

    strong_by_normalized: dict[str, str] = {}
    for phrase in (family.nome, *family.identifying_phrases):
        normalized_phrase = normalize_text(phrase)
        if normalized_phrase:
            strong_by_normalized.setdefault(normalized_phrase, phrase)
    strong_phrases = tuple(strong_by_normalized.values())
    matched_phrases = tuple(
        phrase
        for phrase in strong_phrases
        if _contains_phrase(normalized_text, phrase)
    )
    signals: list[str] = []
    identifying_phrase_count = len(matched_phrases)
    score = min(75.0, 25.0 * identifying_phrase_count)
    if matched_phrases:
        signals.append("frasi identificative")

    normalized_family_name = normalize_text(family.nome)
    family_entity = normalize_text(family.ente)
    family_entity_match = family_entity in detected_entities
    annual_alias, noisy_alias = _annual_family_alias(original_text, normalized_family_name, family_entity_match)
    if annual_alias:
        identifying_phrase_count = max(2, identifying_phrase_count)
        score = max(75.0, score)
        signals.append("alias di famiglia con rumore OCR" if noisy_alias else "modello annuale; versione non attribuita")

    entity_match = family_entity_match
    entity_conflict = (
        family.ente in DISTINCT_ENTITY_NAMES
        and bool(detected_entities)
        and not entity_match
    )
    if entity_conflict:
        conflicts = ("ente della famiglia incompatibile",) if identifying_phrase_count else ()
        return _FamilyCandidateScore(family, 0.0, 0, (), conflicts)

    if entity_match:
        score += 15.0
        signals.append("ente")

    matched_keywords = sum(
        1
        for keyword in family.keywords
        if _contains_phrase(normalized_text, keyword)
    )
    if family.keywords and matched_keywords:
        score += 10.0 * matched_keywords / len(family.keywords)
        signals.append("parole chiave forti")

    return _FamilyCandidateScore(
        family=family,
        score=round(min(100.0, score), 1),
        identifying_phrase_count=identifying_phrase_count,
        signals=tuple(signals),
    )


def recognize_document_family(
    text: str,
    families: Iterable[DocumentFamily],
    *,
    min_confidence: float = MIN_FAMILY_CONFIDENCE,
) -> FamilyRecognitionResult:
    if not 0.0 <= min_confidence <= 100.0:
        raise ValueError("La soglia famiglia deve essere compresa tra 0 e 100.")
    normalized_text = normalize_text(text)
    if not normalized_text:
        return FamilyRecognitionResult(False, 0.0, reason="Nessun testo leggibile disponibile.")

    family_list = list(families)
    detected_entities = _detect_entities(
        normalized_text,
        (
            *(family.ente for family in family_list),
            *DISTINCT_ENTITY_NAMES,
        ),
    )

    candidates = sorted(
        (
            _score_family(text, normalized_text, family, detected_entities)
            for family in family_list
        ),
        key=lambda candidate: candidate.score,
        reverse=True,
    )
    if not candidates:
        return FamilyRecognitionResult(False, 0.0, reason="Nessuna famiglia nel catalogo considerato.")

    best = candidates[0]
    runner_up_score = candidates[1].score if len(candidates) > 1 else 0.0
    recognized = (
        best.score >= min_confidence
        and best.identifying_phrase_count >= MIN_FAMILY_IDENTIFYING_PHRASES
        and best.score - runner_up_score >= MIN_FAMILY_SCORE_MARGIN
    )
    conflicts = tuple(sorted({conflict for candidate in candidates for conflict in candidate.conflicts}))
    reason = (
        "Famiglia sostenuta da evidenze proprie; ente specifico e versione non sono attribuiti."
        if recognized else "Ente incompatibile con le famiglie candidate."
        if conflicts and not best.score else "Famiglie troppo vicine: tipo ambiguo."
        if best.score >= min_confidence and best.identifying_phrase_count >= MIN_FAMILY_IDENTIFYING_PHRASES else "Evidenze insufficienti per identificare una famiglia."
    )
    return FamilyRecognitionResult(
        recognized=recognized,
        confidence=best.score,
        family=best.family if recognized else None,
        matched_signals=best.signals,
        reason=reason,
        conflicts=() if recognized else conflicts,
        score_margin=round(best.score - runner_up_score, 1),
    )


def catalog_revision(
    documents: Iterable[AdministrativeDocument],
    families: Iterable[DocumentFamily],
) -> str:
    """Impronta deterministica degli input di scoring e ammissione del catalogo."""
    # Session diagnostics contain catalog identity and decisions, never upload
    # text or extracted personal fields. Sorting makes the revision independent
    # of database iteration order and includes every rule-relevant field.
    catalog_signature = {
        "documents": sorted((
            (document.id, document.ente, document.codice, document.titolo_ufficiale,
             document.versione, document.parole_chiave, document.stato_verifica)
            for document in documents
        ), key=repr),
        "families": sorted((
            (family.id, family.ente, family.nome, family.keywords,
             family.identifying_phrases, family.stato_verifica)
            for family in families
        ), key=repr),
    }
    return "sha256:" + hashlib.sha256(json.dumps(catalog_signature, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def recognize_catalog(
    text: str,
    documents: Iterable[AdministrativeDocument],
    families: Iterable[DocumentFamily],
    *,
    min_document_confidence: float = MIN_CONFIDENCE,
    min_family_confidence: float = MIN_FAMILY_CONFIDENCE,
) -> CatalogRecognitionResult:
    document_list = list(documents)
    family_list = list(families)
    document_result = recognize_document(
        text,
        document_list,
        min_confidence=min_document_confidence,
        known_entities=(family.ente for family in family_list),
    )
    family_result = recognize_document_family(
        text,
        family_list,
        min_confidence=min_family_confidence,
    )
    diagnostics = {
        "document_score_margin": document_result.score_margin,
        "family_score_margin": family_result.score_margin,
        "rules_version": RULES_VERSION,
        "catalog_revision": catalog_revision(document_list, family_list),
        "candidate_ids": document_result.candidate_ids,
    }
    if document_result.recognized and document_result.document is not None:
        return CatalogRecognitionResult(
            match_type="DOCUMENT_MATCH",
            confidence_document=document_result.confidence,
            confidence_family=family_result.confidence,
            document=document_result.document,
            document_signals=document_result.matched_signals,
            family_signals=family_result.matched_signals,
            reason=document_result.reason,
            **diagnostics,
        )
    if family_result.recognized and family_result.family is not None:
        return CatalogRecognitionResult(
            match_type="FAMILY_MATCH",
            confidence_document=document_result.confidence,
            confidence_family=family_result.confidence,
            family=family_result.family,
            document_signals=document_result.matched_signals,
            family_signals=family_result.matched_signals,
            reason=f"{family_result.reason} {document_result.reason}",
            conflicts=document_result.conflicts,
            **diagnostics,
        )
    return CatalogRecognitionResult(
        match_type="NO_MATCH",
        confidence_document=document_result.confidence,
        confidence_family=family_result.confidence,
        document_signals=document_result.matched_signals,
        family_signals=family_result.matched_signals,
        reason=f"{document_result.reason} {family_result.reason}",
        conflicts=tuple(sorted(set(document_result.conflicts + family_result.conflicts))),
        **diagnostics,
    )
