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
    clean_text,
    fetch_official_html,
    metadata_hash,
    validate_record_limit,
)
from src.models import AdministrativeDocument, DocumentProvenance, OfficialSource
from src.official_urls import is_official_inl_url
from src.provenance import upsert_document_provenance
from src.recognize import normalize_text
from src.sources import list_sources


DEFAULT_LIMIT = 50
MAX_LIMIT = 50
WORKERS_URL = (
    "https://www.ispettorato.gov.it/servizi-e-modulistica/per-i-lavoratori/"
)
EMPLOYERS_URL = (
    "https://www.ispettorato.gov.it/servizi-e-modulistica/"
    "per-il-datore-di-lavoro/"
)
LISTING_PAGES = (
    (WORKERS_URL, "lavoratori o delegati"),
    (EMPLOYERS_URL, "datori di lavoro o delegati"),
)
DOWNLOAD_SUFFIXES = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".odt"}


class InlImportError(RuntimeError):
    """Errore controllato durante l'acquisizione dei metadati INL."""


@dataclass(frozen=True, slots=True)
class InlModule:
    titolo_ufficiale: str
    tipo_utente: str
    area: str | None
    descrizione_ufficiale: str | None
    codice: str | None
    fonte_url: str
    detail_url: str
    download_url: str | None


@dataclass(frozen=True, slots=True)
class ParsedInlBatch:
    modules: tuple[InlModule, ...]
    examined: int
    discarded: int
    errors: int = 0


@dataclass(frozen=True, slots=True)
class InlImportReport:
    source: str = "Ispettorato Nazionale del Lavoro"
    examined: int = 0
    new: int = 0
    updated: int = 0
    already_present: int = 0
    discarded: int = 0
    errors: int = 0
    modules: tuple[InlModule, ...] = field(default_factory=tuple)


def validate_limit(limit: int) -> int:
    return validate_record_limit(limit, maximum=MAX_LIMIT, source_name="INL")


def _area_from_id(value: str | None) -> str | None:
    if not value:
        return None
    area = re.sub(r"-content$", "", value, flags=re.IGNORECASE)
    if area.casefold() in {"tuttiservizi", "tutti-servizi"}:
        return None
    return clean_text(area.replace("-", " ").capitalize())


class _InlListingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.records: list[tuple[str, str, str | None]] = []
        self._tab_stack: list[tuple[int, str | None]] = []
        self._div_depth = 0
        self._anchor_href: str | None = None
        self._anchor_text: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = {name: value or "" for name, value in attrs}
        if tag == "div":
            self._div_depth += 1
            classes = set(attributes.get("class", "").split())
            if "tab-pane" in classes:
                self._tab_stack.append(
                    (self._div_depth, _area_from_id(attributes.get("id")))
                )
        if tag == "a" and attributes.get("href"):
            path = urlsplit(attributes["href"]).path.casefold()
            if "/servizio/" in path:
                self._anchor_href = attributes["href"]
                self._anchor_text = []

    def handle_data(self, data: str) -> None:
        if self._anchor_href is not None:
            self._anchor_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._anchor_href is not None:
            title = clean_text(" ".join(self._anchor_text))
            if title:
                area = self._tab_stack[-1][1] if self._tab_stack else None
                self.records.append((self._anchor_href, title, area))
            self._anchor_href = None
            self._anchor_text = []
        if tag == "div":
            if self._tab_stack and self._tab_stack[-1][0] == self._div_depth:
                self._tab_stack.pop()
            self._div_depth -= 1


class _InlDetailParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.paragraphs: list[str] = []
        self.downloads: list[tuple[str, str]] = []
        self._main_depth = 0
        self._main_tag_depth = 0
        self._paragraph_depth = 0
        self._paragraph_text: list[str] = []
        self._anchor_href: str | None = None
        self._anchor_download = False
        self._anchor_text: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = {name: value or "" for name, value in attrs}
        if self._main_depth:
            self._main_tag_depth += 1
        if tag == "main" or (tag == "div" and attributes.get("id") == "main"):
            if not self._main_depth:
                self._main_depth = 1
                self._main_tag_depth = 1
        if not self._main_depth:
            return
        if tag == "p":
            self._paragraph_depth += 1
            self._paragraph_text = []
        if tag == "a" and attributes.get("href"):
            self._anchor_href = attributes["href"]
            self._anchor_download = "download" in attributes
            self._anchor_text = []

    def handle_data(self, data: str) -> None:
        if not self._main_depth:
            return
        if self._paragraph_depth:
            self._paragraph_text.append(data)
        if self._anchor_href is not None:
            self._anchor_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if not self._main_depth:
            return
        if tag == "p" and self._paragraph_depth:
            self._paragraph_depth -= 1
            if not self._paragraph_depth:
                paragraph = clean_text(" ".join(self._paragraph_text))
                if paragraph:
                    self.paragraphs.append(paragraph)
        if tag == "a" and self._anchor_href is not None:
            label = clean_text(" ".join(self._anchor_text)) or ""
            path = urlsplit(self._anchor_href).path.casefold()
            if self._anchor_download or any(
                path.endswith(extension) for extension in DOWNLOAD_SUFFIXES
            ):
                self.downloads.append((self._anchor_href, label))
            self._anchor_href = None
            self._anchor_download = False
            self._anchor_text = []
        self._main_tag_depth -= 1
        if self._main_tag_depth <= 0:
            self._main_depth = 0
            self._main_tag_depth = 0


def parse_inl_listing_html(
    html: str,
    listing_url: str,
    *,
    user_type: str,
    limit: int = DEFAULT_LIMIT,
) -> ParsedInlBatch:
    validate_limit(limit)
    if not is_official_inl_url(listing_url):
        raise InlImportError("La pagina di elenco INL non usa un dominio ufficiale.")
    parser = _InlListingParser()
    parser.feed(html)
    by_url: dict[str, InlModule] = {}
    discarded = 0
    for raw_url, title, area in parser.records:
        detail_url = urljoin(listing_url, raw_url)
        if not is_official_inl_url(detail_url):
            discarded += 1
            continue
        existing = by_url.get(detail_url)
        candidate = InlModule(
            titolo_ufficiale=title,
            tipo_utente=user_type,
            area=area,
            descrizione_ufficiale=None,
            codice=None,
            fonte_url=listing_url,
            detail_url=detail_url,
            download_url=None,
        )
        if existing is None:
            by_url[detail_url] = candidate
        elif existing.area is None and area is not None:
            by_url[detail_url] = candidate
        else:
            discarded += 1
    modules = tuple(list(by_url.values())[:limit])
    return ParsedInlBatch(
        modules=modules,
        examined=min(len(parser.records), limit + discarded),
        discarded=discarded,
    )


def parse_inl_detail_html(
    html: str, detail_url: str
) -> tuple[str | None, str | None, str | None]:
    if not is_official_inl_url(detail_url):
        raise InlImportError("La pagina dettaglio INL non usa un dominio ufficiale.")
    parser = _InlDetailParser()
    parser.feed(html)
    description = next(
        (
            paragraph
            for paragraph in parser.paragraphs
            if len(paragraph) >= 40
            and not paragraph.casefold().startswith(("sede", "contatti"))
        ),
        None,
    )
    official_downloads: list[tuple[str, str]] = []
    for raw_url, label in parser.downloads:
        url = urljoin(detail_url, raw_url)
        if is_official_inl_url(url):
            official_downloads.append((url, label))
    preferred = next(
        (
            item
            for item in official_downloads
            if any(
                token in f"{item[0]} {item[1]}".casefold()
                for token in (
                    "modul",
                    "istanza",
                    "domanda",
                    "dichiarazione",
                    "fac-simile",
                    "facsimile",
                )
            )
        ),
        official_downloads[0] if official_downloads else (None, None),
    )
    download_url, download_label = preferred
    code_match = re.search(
        r"\bINL[\s_-]*\d+(?:\.\d+)?\b",
        download_label or download_url or "",
        flags=re.IGNORECASE,
    )
    code = re.sub(r"[\s_]", "-", code_match.group(0).upper()) if code_match else None
    return description, download_url, code


def get_verified_inl_source(connection: sqlite3.Connection) -> OfficialSource:
    matches = [
        source
        for source in list_sources(connection)
        if source.ente.casefold() == "ispettorato nazionale del lavoro"
        and source.stato_verifica == "verificato"
        and source.attiva
        and source.url_modulistica
    ]
    if len(matches) != 1:
        raise InlImportError(
            "Serve una sola fonte INL attiva, verificata e dotata di URL modulistica."
        )
    source = matches[0]
    if source.id is None or not is_official_inl_url(source.url_modulistica):
        raise InlImportError("La fonte INL registrata non usa un dominio ufficiale.")
    return source


def fetch_inl_modules(
    *,
    limit: int = DEFAULT_LIMIT,
    request_get: Callable[..., Any] = requests.get,
) -> ParsedInlBatch:
    validate_limit(limit)
    merged: dict[str, InlModule] = {}
    examined = discarded = 0
    for listing_url, user_type in LISTING_PAGES:
        html = fetch_official_html(
            listing_url,
            source_name="INL",
            url_validator=is_official_inl_url,
            error_type=InlImportError,
            request_get=request_get,
        )
        batch = parse_inl_listing_html(
            html, listing_url, user_type=user_type, limit=limit
        )
        examined += batch.examined
        discarded += batch.discarded
        for module in batch.modules:
            key = normalize_text(module.titolo_ufficiale)
            existing = merged.get(key)
            if existing is None:
                if len(merged) < limit:
                    merged[key] = module
            else:
                types = {part.strip() for part in existing.tipo_utente.split(";")}
                types.add(module.tipo_utente)
                merged[key] = replace(
                    existing,
                    tipo_utente="; ".join(sorted(types)),
                    area=existing.area or module.area,
                )
                discarded += 1
        if len(merged) >= limit:
            break

    enriched: list[InlModule] = []
    detail_errors = 0
    for module in merged.values():
        try:
            detail_html = fetch_official_html(
                module.detail_url,
                source_name="INL",
                url_validator=is_official_inl_url,
                error_type=InlImportError,
                request_get=request_get,
            )
            description, download_url, code = parse_inl_detail_html(
                detail_html, module.detail_url
            )
            enriched.append(
                replace(
                    module,
                    descrizione_ufficiale=description,
                    download_url=download_url,
                    codice=code,
                )
            )
        except InlImportError as exc:
            if "non tenta di aggirare" in str(exc):
                raise
            detail_errors += 1
            enriched.append(module)
    return ParsedInlBatch(
        tuple(enriched), examined, discarded, errors=detail_errors
    )


def _as_document(
    module: InlModule, source: OfficialSource, detection_date: str
) -> AdministrativeDocument:
    return AdministrativeDocument(
        ente=source.ente,
        codice=module.codice,
        titolo_ufficiale=module.titolo_ufficiale,
        categoria=module.area,
        descrizione_ufficiale=module.descrizione_ufficiale,
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
        document.codice,
        document.titolo_ufficiale,
        document.categoria,
        document.descrizione_ufficiale,
        document.fonte_url,
        document.download_url,
        document.detail_url,
        document.source_id,
    )


def _find_existing(
    module: InlModule, documents: list[AdministrativeDocument]
) -> AdministrativeDocument | None:
    if module.detail_url:
        detail_match = next(
            (
                document
                for document in documents
                if document.detail_url == module.detail_url
            ),
            None,
        )
        if detail_match is not None:
            return detail_match
    candidate_urls = {module.download_url} if module.download_url else set()
    for document in documents:
        if (
            candidate_urls
            and document.detail_url is None
            and document.download_url in candidate_urls
        ):
            return document
    normalized_title = normalize_text(module.titolo_ufficiale)
    return next(
        (
            document
            for document in documents
            if normalize_text(document.titolo_ufficiale) == normalized_title
        ),
        None,
    )


def _record_provenance(
    connection: sqlite3.Connection,
    document: AdministrativeDocument,
    module: InlModule,
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
                    "user_type": module.tipo_utente,
                    "area": module.area,
                    "description": module.descrizione_ufficiale,
                    "code": module.codice,
                    "detail_url": module.detail_url,
                    "download_url": module.download_url,
                }
            ),
            acquisition_method="inl_html",
            source_status="rilevato",
        ),
    )


def import_inl_modules(
    connection: sqlite3.Connection,
    *,
    limit: int = DEFAULT_LIMIT,
    dry_run: bool = True,
    request_get: Callable[..., Any] = requests.get,
    detection_date: str | None = None,
) -> InlImportReport:
    validate_limit(limit)
    source = get_verified_inl_source(connection)
    batch = fetch_inl_modules(limit=limit, request_get=request_get)
    if dry_run:
        return InlImportReport(
            examined=batch.examined,
            discarded=batch.discarded,
            errors=batch.errors,
            modules=batch.modules,
        )

    detected_on = detection_date or date.today().isoformat()
    assert source.id is not None
    existing_documents = list_documents_for_source(connection, source.id)
    new = updated = already_present = 0
    errors = batch.errors
    for module in batch.modules:
        candidate = _as_document(module, source, detected_on)
        existing = _find_existing(module, existing_documents)
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
    return InlImportReport(
        examined=batch.examined,
        new=new,
        updated=updated,
        already_present=already_present,
        discarded=batch.discarded,
        errors=errors,
        modules=batch.modules,
    )


def preview_lines(report: InlImportReport) -> list[str]:
    lines = ["TITOLO | UTENTE | AREA | MODULO | DETTAGLIO"]
    lines.extend(
        " | ".join(
            (
                module.titolo_ufficiale,
                module.tipo_utente,
                module.area or "-",
                module.download_url or "-",
                module.detail_url,
            )
        )
        for module in report.modules
    )
    return lines


def format_report(report: InlImportReport) -> str:
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
