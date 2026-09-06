from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any, Callable

from src import offline_transport as requests

from src.database import list_documents
from src.explanations import EXPLANATION_STATUS_PENDING, create_explanation
from src.models import AdministrativeDocument, DocumentExplanation
from src.official_urls import is_official_inps_url


MAX_ENRICHMENT_LIMIT = 3
DEFAULT_ENRICHMENT_LIMIT = 3
EXPLANATION_VERSION = "0.1"
REQUEST_TIMEOUT = (5, 20)
USER_AGENT = "BurOCRazia/0.4 (limited official-source explanation review)"
SUPPORTED_CODES = ("SR211", "CI544", "CI543")


class InpsEnrichmentError(RuntimeError):
    """Errore controllato durante la consultazione delle fonti per le schede."""


@dataclass(frozen=True, slots=True)
class ExplanationContent:
    official_summary: str | None
    simple_explanation: str
    intended_use: str | None
    possible_users: tuple[str, ...]
    missing_information: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EnrichmentReport:
    examined: int = 0
    previewed: int = 0
    saved: int = 0
    duplicates_avoided: int = 0
    errors: int = 0
    explanations: tuple[DocumentExplanation, ...] = field(default_factory=tuple)


CONTENTS: dict[str, ExplanationContent] = {
    "SR211": ExplanationContent(
        official_summary=(
            "Modulo INPS relativo alla rinuncia dei beneficiari alla Carta Acquisti."
        ),
        simple_explanation=(
            "È un modulo per comunicare all'INPS la rinuncia alla Carta Acquisti "
            "da parte di chi ne beneficia. Può comparire quando un beneficiario "
            "intende formalizzare la rinuncia; modalità ed effetti devono essere "
            "verificati nelle indicazioni ufficiali."
        ),
        intended_use=(
            "Comunicare all'INPS la rinuncia di un beneficiario alla Carta Acquisti."
        ),
        possible_users=("beneficiari della Carta Acquisti",),
        missing_information=(
            "Le modalità di presentazione non sono specificate nei metadati consultati.",
            "Non è indicato nei metadati consultati se siano richiesti allegati.",
        ),
    ),
    "CI544": ExplanationContent(
        official_summary=(
            "Certificato INPS di opzione contributiva collegato all'accordo tra "
            "Italia e Albania in materia di sicurezza sociale."
        ),
        simple_explanation=(
            "È un certificato relativo all'opzione contributiva nell'ambito "
            "dell'accordo di sicurezza sociale tra Italia e Albania. Può comparire "
            "in una pratica previdenziale che coinvolge i due Paesi; soggetti, "
            "requisiti e procedura vanno verificati nelle indicazioni ufficiali."
        ),
        intended_use=(
            "Documentare un'opzione contributiva nell'ambito dell'accordo di "
            "sicurezza sociale tra Italia e Albania."
        ),
        possible_users=(),
        missing_information=(
            "I soggetti tenuti a compilare o utilizzare il certificato non sono indicati nei metadati consultati.",
            "Requisiti e modalità di presentazione non sono indicati nei metadati consultati.",
        ),
    ),
    "CI543": ExplanationContent(
        official_summary=(
            "Certificato INPS di distacco collegato all'accordo tra Italia e Albania "
            "in materia di sicurezza sociale."
        ),
        simple_explanation=(
            "È un certificato relativo al distacco nell'ambito dell'accordo di "
            "sicurezza sociale tra Italia e Albania. Può comparire in una pratica "
            "previdenziale con elementi nei due Paesi; soggetti, requisiti e "
            "procedura vanno verificati nelle indicazioni ufficiali."
        ),
        intended_use=(
            "Documentare un distacco nell'ambito dell'accordo di sicurezza sociale "
            "tra Italia e Albania."
        ),
        possible_users=(),
        missing_information=(
            "I soggetti tenuti a compilare o utilizzare il certificato non sono indicati nei metadati consultati.",
            "Durata, requisiti e modalità di presentazione non sono indicati nei metadati consultati.",
        ),
    ),
}


def validate_enrichment_limit(limit: int) -> int:
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("Il limite deve essere un numero intero.")
    if not 1 <= limit <= MAX_ENRICHMENT_LIMIT:
        raise ValueError(
            f"Il limite deve essere compreso tra 1 e {MAX_ENRICHMENT_LIMIT}."
        )
    return limit


def _select_documents(
    connection: sqlite3.Connection,
    limit: int,
) -> list[AdministrativeDocument]:
    by_code = {
        document.codice: document
        for document in list_documents(connection)
        if document.ente.casefold() == "inps"
        and document.stato_verifica == "da_verificare"
        and document.id is not None
        and document.codice in CONTENTS
    }
    return [by_code[code] for code in SUPPORTED_CODES if code in by_code][:limit]


def _source_url(document: AdministrativeDocument) -> str:
    source_url = document.detail_url or document.download_url or document.fonte_url
    if not is_official_inps_url(source_url):
        raise InpsEnrichmentError(
            f"La fonte del documento {document.codice or document.id} non è una URL INPS ufficiale."
        )
    assert source_url is not None
    return source_url


def _read_official_source(
    source_url: str,
    request_get: Callable[..., Any],
) -> None:
    if not is_official_inps_url(source_url):
        raise InpsEnrichmentError("URL esterna o non istituzionale rifiutata.")
    try:
        response = request_get(
            source_url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml",
            },
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise InpsEnrichmentError(
            "La fonte ufficiale INPS non è raggiungibile tramite HTTP semplice."
        ) from exc

    final_url = str(getattr(response, "url", source_url) or source_url)
    if not is_official_inps_url(final_url):
        raise InpsEnrichmentError("Reindirizzamento verso un dominio non INPS rifiutato.")
    page_text = getattr(response, "text", None)
    if not isinstance(page_text, str) or not page_text.strip():
        raise InpsEnrichmentError("La pagina ufficiale INPS consultata è vuota.")


def _build_explanation(
    document: AdministrativeDocument,
    source_url: str,
    source_access_date: str,
    timestamp: str,
) -> DocumentExplanation:
    assert document.id is not None
    assert document.codice is not None
    content = CONTENTS[document.codice]
    facts = [
        "La fonte consultata appartiene al dominio ufficiale INPS.",
        f"Il codice del modulo è {document.codice}.",
        f"Il titolo ufficiale è: {document.titolo_ufficiale}",
    ]
    if document.versione:
        facts.append(f"La versione indicata nei metadati INPS è {document.versione}.")
    if document.data_pubblicazione:
        facts.append(
            "La data di pubblicazione indicata nei metadati INPS è "
            f"{document.data_pubblicazione}."
        )
    return DocumentExplanation(
        document_id=document.id,
        official_summary=content.official_summary,
        simple_explanation=content.simple_explanation,
        intended_use=content.intended_use,
        possible_users=content.possible_users,
        facts_from_source=tuple(facts),
        missing_information=content.missing_information,
        warnings=(
            "Verificare sul sito INPS che il modulo e le indicazioni siano aggiornati.",
            "La spiegazione non sostituisce le indicazioni ufficiali dell'INPS.",
        ),
        source_url=source_url,
        source_access_date=source_access_date,
        verification_status=EXPLANATION_STATUS_PENDING,
        verified_by=None,
        verified_at=None,
        version=EXPLANATION_VERSION,
        created_at=timestamp,
        updated_at=timestamp,
    )


def enrich_inps_documents(
    connection: sqlite3.Connection,
    *,
    limit: int = DEFAULT_ENRICHMENT_LIMIT,
    dry_run: bool = True,
    request_get: Callable[..., Any] = requests.get,
    source_access_date: str | None = None,
    timestamp: str | None = None,
) -> EnrichmentReport:
    validate_enrichment_limit(limit)
    selected = _select_documents(connection, limit)
    accessed_on = source_access_date or date.today().isoformat()
    now = timestamp or datetime.now(UTC).replace(microsecond=0).isoformat()
    explanations: list[DocumentExplanation] = []
    saved = duplicates = errors = 0

    for document in selected:
        try:
            source_url = _source_url(document)
            _read_official_source(source_url, request_get)
            explanation = _build_explanation(
                document,
                source_url,
                accessed_on,
                now,
            )
            explanations.append(explanation)
            if not dry_run:
                _explanation_id, created = create_explanation(connection, explanation)
                if created:
                    saved += 1
                else:
                    duplicates += 1
        except (InpsEnrichmentError, KeyError, sqlite3.Error, ValueError):
            errors += 1

    return EnrichmentReport(
        examined=len(selected),
        previewed=len(explanations),
        saved=saved,
        duplicates_avoided=duplicates,
        errors=errors,
        explanations=tuple(explanations),
    )


def preview_lines(report: EnrichmentReport) -> list[str]:
    lines: list[str] = []
    for explanation in report.explanations:
        lines.extend(
            (
                f"Documento ID: {explanation.document_id}",
                f"Sintesi ufficiale: {explanation.official_summary or '-'}",
                f"Spiegazione semplice: {explanation.simple_explanation or '-'}",
                f"Uso generale: {explanation.intended_use or '-'}",
                f"Fatti dalla fonte: {'; '.join(explanation.facts_from_source)}",
                f"Informazioni mancanti: {'; '.join(explanation.missing_information) or '-'}",
                f"Fonte: {explanation.source_url}",
                f"Stato: {explanation.verification_status}",
                "",
            )
        )
    return lines


def format_report(report: EnrichmentReport) -> str:
    return "\n".join(
        (
            f"Documenti esaminati: {report.examined}",
            f"Schede in anteprima: {report.previewed}",
            f"Schede salvate: {report.saved}",
            f"Duplicate evitate: {report.duplicates_avoided}",
            f"Errori: {report.errors}",
        )
    )
