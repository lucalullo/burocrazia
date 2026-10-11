from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable

from rapidfuzz import fuzz
from src.title_evidence import title_windows, exact_code_candidates
from src.text_quality import text_quality
from src.technical_anchors import match_anchors, feature_revision
from src.recognition_profiles import load as safety_profiles, revision as profile_revision
from src.title_evidence import tokens as identity_tokens

from src.models import (
    AdministrativeDocument,
    CatalogRecognitionResult,
    DocumentFamily,
    FamilyRecognitionResult,
    RecognitionResult,
)


MIN_CONFIDENCE = 70.0
MIN_SCORE_MARGIN = 5.0
RULES_VERSION = "deterministic-7-fingerprint-v1"

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
    "ministro del lavoro e delle politiche sociali": "ministero del lavoro",
    "tribunale ordinario di venezia": "tribunale di venezia",
    "ispettorato territoriale del lavoro": "ispettorato nazionale del lavoro",
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


@dataclass(frozen=True)
class _CatalogFeatures:
    code: str
    title: str
    entity: str
    signature: str
    years: frozenset[str]
    code_pattern: re.Pattern | None
    contexts: tuple
    keywords: tuple[str, ...]
    title_tokens: frozenset[str]
    acronyms: frozenset[str]
    identity_tokens: frozenset[str]
    annex: str | None


@lru_cache(maxsize=4096)
def _catalog_features(document: AdministrativeDocument) -> _CatalogFeatures:
    """Cache catalog metadata only; uploaded text never enters this cache."""
    code=normalize_text(document.codice or '')
    title=normalize_text(document.titolo_ufficiale)
    base=re.sub(r'\s+',' ',YEAR_PATTERN.sub(' ',title)).strip()
    contexts=[]
    for value in [base if _is_distinctive_title(base) else '',code if code and not YEAR_PATTERN.search(code) and len(code)>=2 else '']:
        if value:
            escaped=re.escape(value).replace(r'\ ',r'\s+')
            patterns=tuple(re.compile(p) for p in [rf'(?:^|\s){escaped}\s+((?:19|20)\d{{2}})(?=\s|$)',rf'(?:^|\s)((?:19|20)\d{{2}})\s+{escaped}(?=\s|$)'])
            contexts.append((value,patterns))
    return _CatalogFeatures(code,title,normalize_text(document.ente),
        normalize_text(' '.join(x for x in [document.ente,document.titolo_ufficiale,' '.join(document.parole_chiave)] if x)),
        frozenset(YEAR_PATTERN.findall(' '.join(x for x in [document.titolo_ufficiale,document.versione] if x))),
        re.compile(r'(?<!\w)'+re.escape(code)+r'(?!\w)') if code else None,tuple(contexts),
        tuple(normalize_text(k) for k in document.parole_chiave),frozenset(title.split()),
        frozenset(normalize_text(k) for k in re.findall(r'\b[A-Z][A-Z0-9]{1,}\b',document.titolo_ufficiale)),frozenset(identity_tokens(title)),
        (m.group(1) if (m:=re.match(r'^[A-Z][.]([1-9]\d?)\s+(?:Modulo|Modello)\b',document.titolo_ufficiale)) else None))


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
        for entity in dict.fromkeys(entity_names)
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


def _informational_heading(text: str) -> bool:
    """A guide quoting a form is not the form; only explicit headings count."""
    lines = [normalize_text(line) for line in text[:800].splitlines() if line.strip()]
    return any(re.match(r"^(?:circolare|manuale|guida|istruzioni|faq|domande frequenti|provvedimento|comunicato|regolamento)\b", line)
               for line in lines[:6])


def _heading_entities(text: str, entity_names: Iterable[str]) -> frozenset[str] | None:
    """Prefer an issuer heading to entity names in references and model codes."""
    names = tuple(set(entity_names))
    for line in [line for line in text[:1000].splitlines() if line.strip()][:5]:
        normalized = normalize_text(line)
        if any(normalized.startswith(p+' ') for p in safety_profiles()['weak_entity_prefixes']):
            continue
        normalized = re.sub(r'^logo\s+', '', normalized)
        for alias, canonical in ENTITY_ALIASES.items():
            if normalized == alias or normalized.startswith(alias+' '):
                return frozenset({canonical})
        detected = _detect_entities(normalized, names)
        beginning = frozenset(e for e in detected if e not in {'comune', 'comuni', 'regione', 'regioni', 'enti locali'} and (normalized == e or normalized.startswith(e + " ")))
        if beginning:
            return beginning
        if re.match(r"^(?:comune di|regione|provincia di|università|universita|ministero|dipartimento|tribunale|corte di)\b", normalized):
            return frozenset({normalized})
    return None


def _issuer_entities(text: str, entity_names: Iterable[str]) -> frozenset[str]:
    heading = _heading_entities(text, entity_names)
    if heading is not None:
        return heading
    # Unheaded body mentions and recipient addresses are not issuer evidence.
    lines = [normalize_text(s) for s in text[:800].splitlines() if s.strip()][:5]
    return frozenset(e for line in lines if len(line) <= 250
                     and not any(line.startswith(p+' ') for p in safety_profiles()['weak_entity_prefixes'])
                     for e in _detect_entities(line, entity_names)
                     if line == e or line.startswith(e+' ') or line.startswith('logo '+e))


@lru_cache(maxsize=16)
def _unversioned_annual_peers(documents):
    annual = [(d.ente, frozenset(identity_tokens(YEAR_PATTERN.sub('', d.titolo_ufficiale))))
              for d in documents if re.fullmatch(r'(?:19|20)\d{2}', d.versione or '')]
    return frozenset(d.id for d in documents if not d.versione and any(
        entity == d.ente and len(base := frozenset(identity_tokens(d.titolo_ufficiale))) >= 4
        and base <= title for entity, title in annual))


def _qualifier_conflict(title_tokens, text_tokens, heading_tokens=None):
    for group in safety_profiles()['exclusive_qualifiers']:
        required = set(group) & title_tokens
        observed = set(group) & (heading_tokens or set())
        if not observed:observed = set(group) & text_tokens
        if required and observed and not required & observed:
            return True
    return False


@lru_cache(maxsize=16)
def _catalog_domains(documents):
    domains = set()
    for d in documents:
        m = re.match(r'https://(?:www\.)?([^/:]+)', d.fonte_url or '')
        if m:
            domains.add((m.group(1).casefold(), normalize_text(d.ente)))
    return tuple(sorted(domains))


def _scope_entities(text, documents, entity_names):
    # A recipient/reference alone is weak. It may corroborate a distinctive
    # title window or eight independent metadata anchors, never establish an
    # issuer score or overrule an explicit incompatible heading.
    found = set(_detect_entities(normalize_text(text[:2000]), entity_names))
    opening = text[:800].casefold()
    for domain, entity in _catalog_domains(tuple(documents)):
        if re.search(r'(?<![\w.-])(?:www\.)?'+re.escape(domain)+r'(?![\w.-])', opening):
            found.add(entity)
    return frozenset(found) if len(found) == 1 else frozenset()


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


@lru_cache(maxsize=4096)
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


@lru_cache(maxsize=4096)
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
    normalized_text: str | None = None,
) -> tuple[frozenset[str], bool]:
    normalized_text = normalized_text if normalized_text is not None else normalize_text(text)
    observed: set[str] = set()
    model_present = False
    for base,patterns in _catalog_features(document).contexts:
        if f' {base} ' in f' {normalized_text} ':
            model_present=True
            for pattern in patterns: observed.update(pattern.findall(normalized_text))
    labelled = frozenset(re.findall(r"\b(?:versione|version|revisione|annualità)\s+((?:19|20)\d{2})\b", text, flags=re.I))
    if labelled and model_present:
        observed.update(labelled)
    if observed:
        return frozenset(observed), model_present
    if candidate_years and model_present:
        # The annual document type is present but its catalogued year is not.
        return frozenset(), True
    return frozenset(), False


def _annual_version_evidence(
    text: str,
    document: AdministrativeDocument,
    normalized_text: str | None = None,
    input_features: dict | None = None,
) -> tuple[bool, bool]:
    """Return (consistent alias, conflict) for contextual annual models."""
    # An explicitly labelled revision is evidence of a version, unlike a date
    # appearing elsewhere in the document. Missing metadata cannot confirm it.
    revisions = input_features['revisions'] if input_features is not None else {
        value.casefold() for value in re.findall(
            r"\b(?:versione|version|revisione|rev\.)\s*[:=]?\s*(\d+(?:[.]\d+)+)\b",
            text, flags=re.IGNORECASE,
        )
    }
    if revisions and revisions != {(document.versione or "").strip().casefold()}:
        return False, True
    if _candidate_annual_model(document) is None and re.fullmatch(r"\d+(?:[.]\d+)+", document.versione or ""):
        # A revision such as 1.2 is not the year of a cited law in the title.
        return False, False
    candidate_years = _catalog_features(document).years
    model = _candidate_annual_model(document)
    if model is not None:
        observed_years = input_features['annual_years'][model] if input_features is not None else _annual_model_years(text)[model]
        if not observed_years:
            missing_version = bool(candidate_years) and (input_features['mentions'][model] if input_features is not None else _annual_model_is_mentioned(text, model))
            return False, missing_version
        if len(candidate_years) != 1 or len(observed_years) != 1:
            return False, True
        consistent = observed_years == candidate_years
        return consistent and _is_plain_annual_model(document, model), not consistent

    if re.fullmatch(r'(?:19|20)\d{2}', document.versione or ''):
        labelled = set(re.findall(r'\b(?:anno|annualità|annualita|versione|revisione)\s*[:/-]?\s*((?:19|20)\d{2})\b', text, re.I))
        if labelled:
            return False, labelled != {document.versione}
        contextual, _ = _generic_version_context(text, document, candidate_years, normalized_text)
        return False, contextual != {document.versione}

    if not candidate_years:
        return False, False
    observed_years, model_mentioned = _generic_version_context(
        text, document, candidate_years, normalized_text
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
    identity_text: str | None = None,
    input_features: dict | None = None,
) -> _CandidateScore:
    original_text = original_text[:2000]
    score = 0.0
    signals: list[str] = []
    identity_text = identity_text if identity_text is not None else normalize_text(original_text[:2000])
    features = _catalog_features(document)

    annual_alias_match, version_conflict = _annual_version_evidence(
        original_text, document, normalized_text, None if input_features and input_features.get('reference') else input_features
    )

    code = features.code
    # A code cannot be assembled across page/line boundaries or inferred from
    # a payment/privacy reference late in a form. A numeric suffix belongs to
    # the code (INL 29.2 is distinct from INL 29), except an annual model year.
    code_lines = input_features['code_lines'] if input_features is not None else tuple(normalize_text(line) for line in original_text[:2000].splitlines())
    exact_code = bool(code) and any(
        not re.search(r"\b(?:protocollo|prot|fattura|importo|pagina|articolo)(?:\s+(?:n|numero))?$", line[max(0, match.start()-60):match.start()].strip())
        and not (code[-1:].isdigit() and re.match(r'\s+\d{1,3}(?:\s|$)',line[match.end():]))
        for line in code_lines for match in features.code_pattern.finditer(line)
    )
    exact_code = exact_code or bool(input_features and document.id in input_features.get('exact_code_candidates',()))
    if exact_code:
        score += WEIGHTS["exact_code"]
        signals.append("codice esatto")

    normalized_title = features.title
    # A privacy footer can name another authority and quote its generic forms.
    # Only the opening establishes title identity; the rest is fuzzy context.
    exact_title = bool(features.title) and f' {features.title} ' in f' {identity_text} '
    window_title = bool(input_features and document.id in input_features.get('title_windows',{}))
    window_title = window_title and not version_conflict
    technical_title = bool(input_features and document.id in input_features.get('technical_anchors',())) and not version_conflict
    if technical_title and not features.entity in detected_entities:
        technical_title = len(features.identity_tokens & input_features['identity_tokens']) >= 3
    if input_features and document.id in input_features.get('unversioned_annual_peers', ()) and input_features['identity_years']:
        version_conflict = True
    qualifier_conflict = _qualifier_conflict(features.title_tokens,
        input_features['opening_tokens'] if input_features is not None else set(identity_text.split()),
        frozenset(' '.join(input_features['title_lines']).split()) if input_features is not None else None)
    annex_conflict = bool(features.annex and input_features and input_features['annexes'] and input_features['annexes'] != {features.annex})
    if qualifier_conflict:
        technical_title = window_title = False
    if (window_title or technical_title) and document.versione:
        version=document.versione.strip()
        if re.fullmatch(r'(?:19|20)\d{2}',version):
            explicit=set(re.findall(r'\b(?:anno|annualità|annualita|versione|modello)\s*[:/-]?\s*((?:19|20)\d{2})\b',original_text,re.I))
            supported=explicit=={version} or annual_alias_match
        else:
            supported=bool(re.search(r'\b(?:versione|version|revisione|rev[.]?)\s*[:=]?\s*'+re.escape(version)+r'(?!\w)',original_text,re.I))
        window_title=window_title and supported
        technical_title=technical_title and supported
    if exact_title or annual_alias_match or window_title or technical_title:
        title_similarity = 100.0
    else:
        title_similarity = float(fuzz.partial_ratio(normalized_title, identity_text))
        # partial_ratio alone gives 100 when only one word of a long title is
        # supplied. Require coverage of the candidate title before using it.
        title_tokens = features.title_tokens
        covered_tokens = title_tokens & (input_features['opening_tokens'] if input_features is not None else set(identity_text.split()))
        if title_tokens and len(covered_tokens) / len(title_tokens) < 0.7:
            title_similarity = min(title_similarity, MIN_TITLE_SIMILARITY - 1)
    if title_similarity >= MIN_TITLE_SIMILARITY:
        score += WEIGHTS["title"] * title_similarity / 100.0
        signals.append("modello e versione" if annual_alias_match else "titolo")
        if technical_title:signals.append('anchor tecnici derivati da file ufficiale development')

    normalized_entity = features.entity
    entity_match = normalized_entity in detected_entities
    entity_conflict = (bool(detected_entities) and not entity_match) or (len(detected_entities)>1 and not exact_code) or _local_entity_conflict(original_text, document.ente)
    if entity_match:
        score += WEIGHTS["entity"]
        signals.append("ente")

    keyword_count = len(document.parole_chiave)
    matched_keywords = sum(
        1
        for keyword in features.keywords
        if keyword and f' {keyword} ' in f' {normalized_text} '
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
    elif exact_code and (exact_title or window_title) and len(features.identity_tokens) >= 2:
        evidence_rank = 5
    elif exact_code:
        evidence_rank = 4
    elif (exact_title or window_title or technical_title) and distinctive_title:
        evidence_rank = 3
    elif (
        title_similarity >= MIN_STRONG_TITLE_SIMILARITY
        and distinctive_title
        and entity_match
    ) or strong_keywords:
        evidence_rank = 1
    else:
        evidence_rank = 0
    strong_evidence = evidence_rank > 0
    alias_only = features.entity in {'tribunale di venezia','ispettorato nazionale del lavoro'} and not _contains_phrase(identity_text,features.entity)
    if alias_only and not exact_code and not exact_title and not window_title and not technical_title:
        strong_evidence=False
        evidence_rank=0
    if not exact_code:
        title_heading = any(line == normalized_title or line.startswith(normalized_title+' ') for line in
                            (input_features['title_lines'] if input_features is not None else tuple(normalize_text(line) for line in original_text[:800].splitlines() if line.strip())[:5]))
        # A literal title in the body can describe an exemption or another
        # authority's form. Missing issuer evidence requires a title heading.
        if (exact_title and not entity_match and not title_heading) or (not exact_title and not window_title and not technical_title and not features.acronyms.issubset(set(identity_text.split()))):
            strong_evidence = False
            evidence_rank = 0
        # Two generic title words in legal instructions cannot establish a form.
        if len(features.identity_tokens) < 3 and not title_heading and not annual_alias_match and not strong_keywords:
            strong_evidence = False
            evidence_rank = 0
    annual_model = _candidate_annual_model(document)
    identity_evidence = strong_evidence or bool(annual_model and (input_features['mentions'][annual_model] if input_features is not None else _annual_model_is_mentioned(original_text, annual_model)))
    if annual_model and not _is_plain_annual_model(document, annual_model) and exact_code and normalize_text(document.codice or "") == annual_model and not exact_title:
        strong_evidence = False
        evidence_rank = 0
    conflicts: list[str] = []
    if annex_conflict:
        strong_evidence = False
        evidence_rank = 0
        if identity_evidence:
            conflicts.append('numero allegato incompatibile')
    if qualifier_conflict:
        strong_evidence = False
        evidence_rank = 0
        if identity_evidence:
            conflicts.append('sottotipo incompatibile')
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

    signature = features.signature
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
    reference_full_scan: bool = False,
) -> RecognitionResult:
    if not 0.0 <= min_confidence <= 100.0:
        raise ValueError("La soglia di confidenza deve essere compresa tra 0 e 100.")

    normalized_text = normalize_text(text[:2000])
    if not normalized_text:
        return RecognitionResult(recognized=False, confidence=0.0, reason="Nessun testo leggibile disponibile.")
    if _informational_heading(text):
        return RecognitionResult(recognized=False, confidence=0.0, reason="Intestazione informativa: i riferimenti a moduli non ne provano l'identità.", conflicts=("risorsa informativa",))

    document_list = list(documents)
    # Anche l'ente di un record rifiutato resta noto: escludere il documento
    # operativo non deve indebolire la protezione contro un emittente errato.
    entity_names = (
            *(document.ente for document in document_list),
            *known_entities,
            *DISTINCT_ENTITY_NAMES,
    )
    opening_text = normalize_text(text[:2000])
    detected_entities = _issuer_entities(text, entity_names)
    scopes = detected_entities or _scope_entities(text, document_list, entity_names)
    # Request-local only: uploaded text and its derivatives are never cached.
    input_features = dict(
        revisions={v.casefold() for v in re.findall(r'\b(?:versione|version|revisione|rev\.)\s*[:=]?\s*(\d+(?:[.]\d+)+)\b', text[:2000], flags=re.I)},
        annual_years=_annual_model_years(text[:2000]),
        mentions={m:_annual_model_is_mentioned(text[:2000],m) for m in ANNUAL_MODEL_PATTERNS},
        opening_tokens=frozenset(opening_text.split()),
        code_lines=tuple(normalize_text(line) for line in text[:2000].splitlines()),
        title_lines=tuple(normalize_text(line) for line in text[:800].splitlines() if line.strip())[:5],
        title_windows=title_windows(text,document_list,tuple(d.ente for d in document_list if normalize_text(d.ente) in scopes),reference=reference_full_scan),
        exact_code_candidates=exact_code_candidates(text,document_list,reference=reference_full_scan),
        technical_anchors=match_anchors(text,document_list,tuple(d.ente for d in document_list if normalize_text(d.ente) in scopes)),
        identity_tokens=frozenset(identity_tokens(text[:800])),
        annexes=frozenset(re.findall(r'^\s*Allegato\s+(?:n[.]?\s*)?([1-9]\d?)\b',text[:300],re.I|re.M)),
        unversioned_annual_peers=(_unversioned_annual_peers.__wrapped__ if reference_full_scan else _unversioned_annual_peers)(tuple(document_list)),
        identity_years=frozenset(re.findall(r'\b(?:anno|annualità|annualita|versione|modello)\s*[:/-]?\s*((?:19|20)\d{2})\b',text[:2000],re.I)) or frozenset(re.findall(r'^\s*((?:19|20)\d{2})\s*$',text[:800],re.M)),
    )
    if reference_full_scan:
        # Reference computes the same new evidence without annual-analysis caches.
        input_features = dict(input_features,reference=True)
    candidates = sorted(
        (
            _score_candidate(text, normalized_text, document, detected_entities, opening_text, input_features)
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
    # A complete longer title disambiguates its shorter literal substring.
    # This does not resolve equal titles/codes, incompatible versions or entities.
    strongest = [c for c in strongest if not any(
        c.document.ente == other.document.ente
        and c.evidence_rank >= 3 and other.evidence_rank >= 3
        and _catalog_features(c.document).title != _catalog_features(other.document).title
        and f' {_catalog_features(c.document).title} ' in f' {_catalog_features(other.document).title} '
        and f' {_catalog_features(other.document).title} ' in f' {opening_text} '
        for other in strongest
    )]
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
    # Nested variants and the issuer's name are not independent type signals.
    matched_phrases = tuple(p for p in matched_phrases
                            if normalize_text(p) != normalize_text(family.ente)
                            and not any(normalize_text(p) != normalize_text(q) and _contains_phrase(normalize_text(q), p) for q in matched_phrases))
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
    scope = normalize_text(family.ente)
    if scope == 'polizia locale ente locale':
        entity_match = any(e.startswith('comune di ') or e.startswith('comando polizia locale') for e in detected_entities)
    elif scope == 'regione ente regionale':
        entity_match = any(e.startswith('regione ') for e in detected_entities)
    entity_conflict = (
        bool(detected_entities)
        and not entity_match
    )
    if entity_conflict:
        conflicts = ("ente della famiglia incompatibile",) if identifying_phrase_count else ()
        return _FamilyCandidateScore(family, 0.0, 0, (), conflicts)
    independent_tax_context = annual_alias and noisy_alias and not detected_entities and (
        (normalized_family_name == 'modello 730' and _contains_phrase(normalized_text,'dichiarazione dei redditi'))
        or (normalized_family_name == 'certificazione unica' and _contains_phrase(normalized_text,'sostituto d imposta')))
    if not entity_match and not independent_tax_context:
        return _FamilyCandidateScore(family, 0.0, 0, ())
    if independent_tax_context:
        signals.append('modello OCR e contesto fiscale indipendente; emittente non provato')

    if entity_match:
        score += 15.0
        signals.append("ente")

    # A complete, distinctive family heading plus an explicit issuer is an
    # independent fallback signal; no version or document identity is inferred.
    heading = any(line == normalized_family_name or line.startswith(normalized_family_name+' ')
                  for line in (normalize_text(s) for s in original_text[:600].splitlines() if s.strip()))
    required_context = safety_profiles()['family_context'].get(normalized_family_name)
    if required_context and not any(_contains_phrase(normalized_text, p) for p in required_context):
        return _FamilyCandidateScore(family, 0.0, 0, (), ('contesto indipendente della famiglia assente',) if identifying_phrase_count else ())
    if required_context and identifying_phrase_count and entity_match:
        identifying_phrase_count += 1
        score = max(85.0, score)
        signals.append('contesto indipendente della famiglia')
    if heading and entity_match and len(normalized_family_name.split())>=4:
        identifying_phrase_count=max(2,identifying_phrase_count)
        score=max(90.0,score)
        signals.append('intestazione completa della famiglia ed ente')
    elif entity_match and identifying_phrase_count >= 2:
        score = max(85.0, score)
    elif entity_match and identifying_phrase_count == 1 and len(set(identity_tokens(normalized_family_name))) >= 2 and len(set(identity_tokens(normalized_family_name)) & set(identity_tokens(matched_phrases[0]))) / len(set(identity_tokens(normalized_family_name))) >= .7:
        # A distinctive type together with the issuer is sufficient only for
        # these unversioned verified scopes; nested strings remain one signal.
        identifying_phrase_count = 2
        score = max(85.0, score)

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
    known_entities: Iterable[str] = (),
) -> FamilyRecognitionResult:
    if not 0.0 <= min_confidence <= 100.0:
        raise ValueError("La soglia famiglia deve essere compresa tra 0 e 100.")
    normalized_text = normalize_text(text[:2000])
    if not normalized_text:
        return FamilyRecognitionResult(False, 0.0, reason="Nessun testo leggibile disponibile.")
    if _informational_heading(text):
        return FamilyRecognitionResult(False, 0.0, reason="Intestazione informativa: famiglia non attribuita.")

    family_list = list(families)
    entity_names = (
            *(family.ente for family in family_list),
            *known_entities,
            *DISTINCT_ENTITY_NAMES,
    )
    detected_entities = _issuer_entities(text, entity_names)

    candidates = sorted(
        (
            _score_family(text[:2000], normalized_text, family, detected_entities)
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
        "document_fingerprints": __import__('src.document_fingerprints',fromlist=['revision']).revision(),
        "technical_features": feature_revision(),
        "safety_profiles": profile_revision(),
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
    reference_full_scan: bool = False,
    file_sha256: str | None = None,
    form_field_names: Iterable[str] = (),
) -> CatalogRecognitionResult:
    document_list = list(documents)
    family_list = list(families)
    from src.fingerprint_match import match as match_fingerprint
    fingerprint_result = match_fingerprint(text, document_list, file_sha256=file_sha256,
        field_names=form_field_names, reference=reference_full_scan)
    if fingerprint_result is not None:
        return CatalogRecognitionResult(match_type='DOCUMENT_MATCH',
            confidence_document=fingerprint_result.confidence,confidence_family=0.0,
            document=fingerprint_result.document,document_signals=fingerprint_result.matched_signals,
            reason=fingerprint_result.reason,document_score_margin=fingerprint_result.score_margin,
            candidate_ids=fingerprint_result.candidate_ids,rules_version=RULES_VERSION,
            catalog_revision=catalog_revision(document_list,family_list),
            pipeline_stages=(('file_safety','validated_by_extraction'),
                ('fingerprint',fingerprint_result.matched_signals[0]),('entity_version_constraints','passed')))
    quality = text_quality(text)
    if not quality['usable']:
        return CatalogRecognitionResult(match_type='NO_MATCH',confidence_document=0.0,confidence_family=0.0,
            reason='Qualità del testo insufficiente per il riconoscimento.',rules_version=RULES_VERSION,
            catalog_revision=catalog_revision(document_list,family_list),pipeline_stages=(('extraction_quality','unusable'),('decision','NO_MATCH')))
    opening = normalize_text(text[:2000])
    operational_documents = [d for d in document_list if d.stato_verifica != 'demo' or
                             bool(d.codice and _contains_phrase(opening,d.codice))]
    document_result = recognize_document(
        text,
        operational_documents,
        min_confidence=min_document_confidence,
        known_entities=tuple(family.ente for family in family_list)+tuple(d.ente for d in document_list),
        reference_full_scan=reference_full_scan,
    )
    family_result = recognize_document_family(
        text,
        family_list,
        min_confidence=min_family_confidence,
        known_entities=(document.ente for document in document_list),
    )
    diagnostics = {
        "document_score_margin": document_result.score_margin,
        "family_score_margin": family_result.score_margin,
        "rules_version": RULES_VERSION,
        "catalog_revision": catalog_revision(document_list, family_list),
        "candidate_ids": document_result.candidate_ids,
        "pipeline_stages": (('extraction_quality','usable'),('exact_code_candidates','evaluated'),
            ('entity_candidates','evaluated'),('version_year_constraints','evaluated'),
            ('title_anchor_windows','evaluated'),('exact_document_scoring','accepted' if document_result.recognized else 'rejected'),
            ('family_fallback','supported' if family_result.recognized else 'unsupported')),
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
