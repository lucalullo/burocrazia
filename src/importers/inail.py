from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date
from html.parser import HTMLParser
import re
import sqlite3
from typing import Any, Callable
from urllib.parse import urljoin, urlsplit

from src import offline_transport as requests

from src.database import (
    insert_document,
    list_documents_for_source,
    update_document_source_metadata,
)
from src.importers.common import (
    MAX_HTTP_ATTEMPTS,
    REQUEST_TIMEOUT,
    USER_AGENT,
    clean_text,
    find_existing_document,
    metadata_hash,
)
from src.models import AdministrativeDocument, DocumentProvenance, OfficialSource
from src.official_urls import is_official_inail_url
from src.provenance import upsert_document_provenance
from src.sources import list_sources


DEFAULT_LIMIT = 20
MAX_LIMIT = 20
SUPPORTED_SUFFIXES = {".pdf", ".doc", ".docx"}
INAIL_CATEGORY = "Abilitazione ai servizi online"


class InailImportError(RuntimeError):
    """Errore controllato durante l'acquisizione dei metadati INAIL."""


@dataclass(frozen=True, slots=True)
class InailModule:
    titolo_ufficiale: str
    categoria: str | None
    fonte_url: str
    detail_url: str
    download_url: str


@dataclass(frozen=True, slots=True)
class ParsedInailBatch:
    modules: tuple[InailModule, ...]
    examined: int
    discarded: int


@dataclass(frozen=True, slots=True)
class InailImportReport:
    source: str = "INAIL"
    examined: int = 0
    new: int = 0
    updated: int = 0
    already_present: int = 0
    discarded: int = 0
    errors: int = 0
    modules: tuple[InailModule, ...] = field(default_factory=tuple)


def validate_limit(limit: int) -> int:
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("Il limite deve essere un numero intero.")
    if not 1 <= limit <= MAX_LIMIT:
        raise ValueError(f"Il limite INAIL deve essere compreso tra 1 e {MAX_LIMIT}.")
    return limit


class _InailDownloadParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.records: list[tuple[str, str, str]] = []
        self._page_heading: str | None = None
        self._heading_depth = 0
        self._heading_text: list[str] = []
        self._anchor_href: str | None = None
        self._anchor_title = ""
        self._anchor_text: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = {name: value or "" for name, value in attrs}
        if tag == "h1":
            self._heading_depth += 1
            self._heading_text = []
        if tag == "a" and attributes.get("href"):
            self._anchor_href = attributes["href"]
            self._anchor_title = attributes.get("title", "")
            self._anchor_text = []

    def handle_data(self, data: str) -> None:
        if self._heading_depth:
            self._heading_text.append(data)
        if self._anchor_href is not None:
            self._anchor_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "h1" and self._heading_depth:
            self._heading_depth -= 1
            if not self._heading_depth:
                self._page_heading = clean_text(" ".join(self._heading_text))
        if tag == "a" and self._anchor_href is not None:
            suffix = urlsplit(self._anchor_href).path.casefold()
            if any(suffix.endswith(extension) for extension in SUPPORTED_SUFFIXES):
                self.records.append(
                    (
                        self._anchor_href,
                        self._anchor_title,
                        " ".join(self._anchor_text),
                    )
                )
            self._anchor_href = None
            self._anchor_title = ""
            self._anchor_text = []


def _module_title(title_attribute: str, anchor_text: str) -> str | None:
    title = clean_text(title_attribute) or clean_text(anchor_text)
    if not title:
        return None
    title = re.sub(r"^Scarica file\s*[-:]\s*", "", title, flags=re.IGNORECASE)
    title = re.sub(
        r"\s+Formato\s+(?:PDF|DOCX?)\b.*$", "", title, flags=re.IGNORECASE
    )
    return clean_text(title)


def parse_inail_html(
    html: str, listing_url: str, *, limit: int = DEFAULT_LIMIT
) -> ParsedInailBatch:
    validate_limit(limit)
    if not is_official_inail_url(listing_url):
        raise InailImportError("La URL modulistica registrata non appartiene a INAIL.")
    parser = _InailDownloadParser()
    parser.feed(html)
    candidates = parser.records[:limit]
    modules: list[InailModule] = []
    discarded = 0
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    for raw_url, title_attribute, anchor_text in candidates:
        download_url = urljoin(listing_url, raw_url)
        title = _module_title(title_attribute, anchor_text)
        normalized_title = title.casefold() if title else ""
        if (
            not title
            or not is_official_inail_url(download_url)
            or download_url in seen_urls
            or normalized_title in seen_titles
        ):
            discarded += 1
            continue
        seen_urls.add(download_url)
        seen_titles.add(normalized_title)
        modules.append(
            InailModule(
                titolo_ufficiale=title,
                categoria=INAIL_CATEGORY,
                fonte_url=listing_url,
                detail_url=listing_url,
                download_url=download_url,
            )
        )
    return ParsedInailBatch(tuple(modules), len(candidates), discarded)


def get_verified_inail_source(connection: sqlite3.Connection) -> OfficialSource:
    matches = [
        source
        for source in list_sources(connection)
        if source.ente.casefold() == "inail"
        and source.stato_verifica == "verificato"
        and source.attiva
        and source.url_modulistica
    ]
    if len(matches) != 1:
        raise InailImportError(
            "Serve una sola fonte INAIL attiva, verificata e dotata di URL modulistica."
        )
    source = matches[0]
    if source.id is None or not is_official_inail_url(source.url_modulistica):
        raise InailImportError("La fonte INAIL registrata non usa un dominio ufficiale.")
    return source


def fetch_inail_modules(
    listing_url: str,
    *,
    limit: int = DEFAULT_LIMIT,
    request_get: Callable[..., Any] = requests.get,
) -> ParsedInailBatch:
    validate_limit(limit)
    if not is_official_inail_url(listing_url):
        raise InailImportError("La URL modulistica registrata non appartiene a INAIL.")
    last_error: Exception | None = None
    for _attempt in range(MAX_HTTP_ATTEMPTS):
        try:
            response = request_get(
                listing_url,
                headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
                timeout=REQUEST_TIMEOUT,
            )
            if getattr(response, "status_code", None) in {403, 429}:
                raise InailImportError(
                    "La fonte INAIL ha rifiutato o limitato la richiesta; "
                    "l'importatore non tenta di aggirare il blocco."
                )
            response.raise_for_status()
            return parse_inail_html(response.text, listing_url, limit=limit)
        except InailImportError:
            raise
        except requests.RequestException as exc:
            last_error = exc
    raise InailImportError(
        "La fonte INAIL non è raggiungibile tramite HTTP semplice."
    ) from last_error


def _as_document(
    module: InailModule, source: OfficialSource, detection_date: str
) -> AdministrativeDocument:
    return AdministrativeDocument(
        ente=source.ente,
        codice=None,
        titolo_ufficiale=module.titolo_ufficiale,
        categoria=module.categoria,
        descrizione_ufficiale=None,
        significato_semplice=None,
        fonte_url=module.fonte_url,
        download_url=module.download_url,
        detail_url=module.detail_url,
        data_pubblicazione=None,
        versione=None,
        data_rilevazione=detection_date,
        stato_verifica="da_verificare",
        parole_chiave=(),
        source_id=source.id,
    )


def _source_metadata(document: AdministrativeDocument) -> tuple[object, ...]:
    return (
        document.ente,
        document.titolo_ufficiale,
        document.categoria,
        document.fonte_url,
        document.download_url,
        document.detail_url,
        document.source_id,
    )


def _record_provenance(
    connection: sqlite3.Connection,
    document: AdministrativeDocument,
    module: InailModule,
    detection_date: str,
) -> None:
    assert document.id is not None and document.source_id is not None
    upsert_document_provenance(
        connection,
        DocumentProvenance(
            document_id=document.id,
            source_id=document.source_id,
            listing_url=module.fonte_url,
            detail_url=module.detail_url,
            download_url=module.download_url,
            acquired_at=detection_date,
            last_seen_at=detection_date,
            content_hash=metadata_hash(
                {
                    "title": module.titolo_ufficiale,
                    "category": module.categoria,
                    "detail_url": module.detail_url,
                    "download_url": module.download_url,
                }
            ),
            acquisition_method="inail_html",
            source_status="rilevato",
        ),
    )


def import_inail_modules(
    connection: sqlite3.Connection,
    *,
    limit: int = DEFAULT_LIMIT,
    dry_run: bool = True,
    request_get: Callable[..., Any] = requests.get,
    detection_date: str | None = None,
) -> InailImportReport:
    validate_limit(limit)
    source = get_verified_inail_source(connection)
    assert source.url_modulistica is not None and source.id is not None
    batch = fetch_inail_modules(
        source.url_modulistica, limit=limit, request_get=request_get
    )
    if dry_run:
        return InailImportReport(
            examined=batch.examined,
            discarded=batch.discarded,
            modules=batch.modules,
        )

    detected_on = detection_date or date.today().isoformat()
    existing_documents = list_documents_for_source(connection, source.id)
    new = updated = already_present = errors = 0
    for module in batch.modules:
        candidate = _as_document(module, source, detected_on)
        existing = find_existing_document(
            code=None,
            official_urls=(module.download_url,),
            title=module.titolo_ufficiale,
            documents=existing_documents,
        )
        try:
            if existing is None:
                inserted = replace(candidate, id=insert_document(connection, candidate))
                existing_documents.append(inserted)
                _record_provenance(connection, inserted, module, detected_on)
                new += 1
            elif existing.stato_verifica == "verificato" or _source_metadata(
                existing
            ) == _source_metadata(candidate):
                _record_provenance(connection, existing, module, detected_on)
                already_present += 1
            elif existing.id is not None and update_document_source_metadata(
                connection, existing.id, candidate
            ):
                refreshed = replace(
                    candidate,
                    id=existing.id,
                    data_rilevazione=existing.data_rilevazione,
                    stato_verifica=existing.stato_verifica,
                    significato_semplice=existing.significato_semplice,
                    parole_chiave=existing.parole_chiave,
                )
                existing_documents.remove(existing)
                existing_documents.append(refreshed)
                _record_provenance(connection, refreshed, module, detected_on)
                updated += 1
            else:
                already_present += 1
        except sqlite3.Error:
            errors += 1
    return InailImportReport(
        examined=batch.examined,
        new=new,
        updated=updated,
        already_present=already_present,
        discarded=batch.discarded,
        errors=errors,
        modules=batch.modules,
    )


def preview_lines(report: InailImportReport) -> list[str]:
    lines = ["TITOLO | CATEGORIA | URL"]
    lines.extend(
        " | ".join(
            (
                module.titolo_ufficiale,
                module.categoria or "-",
                module.download_url,
            )
        )
        for module in report.modules
    )
    return lines


def format_report(report: InailImportReport) -> str:
    return "\n".join(
        (
            f"Fonte: {report.source}",
            f"Esaminati: {report.examined}",
            f"Nuovi: {report.new}",
            f"Aggiornati: {report.updated}",
            f"Già presenti: {report.already_present}",
            f"Scartati: {report.discarded}",
            f"Errori: {report.errors}",
        )
    )
