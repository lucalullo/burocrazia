from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, date
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
    DEFAULT_BATCH_SIZE,
    MAX_HTTP_ATTEMPTS,
    REQUEST_TIMEOUT,
    USER_AGENT,
    clean_text,
    find_existing_document,
    metadata_hash,
    validate_batch_limit,
)
from src.models import AdministrativeDocument, DocumentProvenance, OfficialSource
from src.official_urls import is_official_ader_url
from src.provenance import upsert_document_provenance
from src.sources import list_sources


class AderImportError(RuntimeError):
    """Safe failure while importing official ADER metadata."""


@dataclass(frozen=True, slots=True)
class AderModule:
    codice: str | None
    titolo_ufficiale: str
    categoria: str | None
    descrizione_ufficiale: str | None
    fonte_url: str
    detail_url: str | None
    download_url: str | None
    data_pubblicazione: str | None


@dataclass(frozen=True, slots=True)
class ParsedAderBatch:
    modules: tuple[AderModule, ...]
    examined: int
    discarded: int


@dataclass(frozen=True, slots=True)
class AderImportReport:
    source: str = "ADER"
    examined: int = 0
    new: int = 0
    updated: int = 0
    already_present: int = 0
    discarded: int = 0
    errors: int = 0
    modules: tuple[AderModule, ...] = field(default_factory=tuple)


class _AderListingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.records: list[dict[str, str]] = []
        self.declared_source_urls: list[str] = []
        self._record: dict[str, str] | None = None
        self._section_category: str | None = None
        self._heading_depth = 0
        self._heading_text: list[str] = []
        self._paragraph_depth = 0
        self._paragraph_text: list[str] = []
        self._anchor_href: str | None = None
        self._anchor_text: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        attributes = {name: value or "" for name, value in attrs}
        class_names = set(attributes.get("class", "").casefold().split())
        relation = set(attributes.get("rel", "").casefold().split())
        if tag == "link" and "canonical" in relation and attributes.get("href"):
            self.declared_source_urls.append(attributes["href"])
        if (
            tag == "meta"
            and attributes.get("property", "").casefold() == "og:url"
            and attributes.get("content")
        ):
            self.declared_source_urls.append(attributes["content"])
        if tag == "base" and attributes.get("href"):
            self.declared_source_urls.append(attributes["href"])
        if tag == "section" and attributes.get("data-category"):
            self._section_category = attributes["data-category"]
        if tag in {"article", "li"} and (
            tag == "article"
            or class_names.intersection({"module", "modulo", "modulistica-item"})
            or attributes.get("data-code")
        ):
            self._record = {
                "codice": attributes.get("data-code", ""),
                "categoria": attributes.get("data-category", "")
                or self._section_category
                or "",
                "data": attributes.get("data-date", ""),
                "titolo": attributes.get("data-title", ""),
            }
        if tag in {"h1", "h2", "h3", "h4"}:
            self._heading_depth += 1
            if self._heading_depth == 1:
                self._heading_text = []
        if tag == "p" and self._record is not None:
            self._paragraph_depth += 1
            if self._paragraph_depth == 1:
                self._paragraph_text = []
        if tag == "time" and self._record is not None and attributes.get("datetime"):
            self._record["data"] = attributes["datetime"]
        if tag == "a" and attributes.get("href"):
            self._anchor_href = attributes["href"]
            self._anchor_text = []

    def handle_data(self, data: str) -> None:
        if self._heading_depth:
            self._heading_text.append(data)
        if self._paragraph_depth:
            self._paragraph_text.append(data)
        if self._anchor_href is not None:
            self._anchor_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._anchor_href is not None:
            anchor_text = " ".join(self._anchor_text).strip()
            href = self._anchor_href
            is_pdf = urlsplit(href).path.casefold().endswith(".pdf")
            if self._record is not None:
                if is_pdf:
                    self._record["download_url"] = href
                else:
                    self._record.setdefault("detail_url", href)
                    if anchor_text:
                        self._record.setdefault("titolo_link", anchor_text)
            elif is_pdf and anchor_text:
                self.records.append(
                    {
                        "titolo": anchor_text,
                        "categoria": self._section_category or "",
                        "download_url": href,
                    }
                )
            self._anchor_href = None
            self._anchor_text = []
        if tag == "p" and self._record is not None and self._paragraph_depth:
            self._paragraph_depth -= 1
            if self._paragraph_depth == 0:
                paragraph = " ".join(self._paragraph_text).strip()
                if paragraph:
                    self._record.setdefault("descrizione", paragraph)
        if tag in {"h1", "h2", "h3", "h4"} and self._heading_depth:
            self._heading_depth -= 1
            if self._heading_depth == 0:
                heading = " ".join(self._heading_text).strip()
                if self._record is not None and heading:
                    self._record["titolo"] = heading
                elif heading:
                    self._section_category = heading
        if tag in {"article", "li"} and self._record is not None:
            self.records.append(self._record)
            self._record = None


def _official_url(raw_url: object, base_url: str) -> str | None:
    cleaned = clean_text(raw_url)
    if not cleaned:
        return None
    resolved = urljoin(base_url, cleaned)
    if not is_official_ader_url(resolved):
        raise ValueError("URL esterno o non istituzionale rifiutato.")
    return resolved


def _official_code(explicit_code: object, title: str) -> str | None:
    code = clean_text(explicit_code)
    if code:
        return code
    match = re.match(
        r"^(?:mod(?:ello)?\.?\s*)?([A-Z]{1,6}\d{1,4})\b",
        title,
        flags=re.IGNORECASE,
    )
    return match.group(1).upper() if match else None


def _publication_date(value: object) -> str | None:
    cleaned = clean_text(value)
    if not cleaned:
        return None
    for date_format in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(cleaned[:10], date_format).date().isoformat()
        except ValueError:
            continue
    return None


def parse_ader_html(
    html: str,
    listing_url: str,
    *,
    limit: int = DEFAULT_BATCH_SIZE,
) -> ParsedAderBatch:
    validate_batch_limit(limit)
    if not is_official_ader_url(listing_url):
        raise AderImportError("La URL modulistica registrata non appartiene ad ADER.")
    parser = _AderListingParser()
    parser.feed(html)

    candidates = parser.records[:limit]
    modules: list[AderModule] = []
    discarded = 0
    for record in candidates:
        title = clean_text(record.get("titolo") or record.get("titolo_link"))
        if not title:
            discarded += 1
            continue
        try:
            detail_url = _official_url(record.get("detail_url"), listing_url)
            download_url = _official_url(record.get("download_url"), listing_url)
        except ValueError:
            discarded += 1
            continue
        if not detail_url and not download_url:
            discarded += 1
            continue
        modules.append(
            AderModule(
                codice=_official_code(record.get("codice"), title),
                titolo_ufficiale=title,
                categoria=clean_text(record.get("categoria")),
                descrizione_ufficiale=clean_text(record.get("descrizione")),
                fonte_url=listing_url,
                detail_url=detail_url,
                download_url=download_url,
                data_pubblicazione=_publication_date(record.get("data")),
            )
        )
    return ParsedAderBatch(tuple(modules), len(candidates), discarded)


def parse_saved_ader_html(
    html: str,
    listing_url: str,
    *,
    limit: int = DEFAULT_BATCH_SIZE,
) -> ParsedAderBatch:
    """Parse a manually saved page only when its ADER origin is declared."""
    provenance_parser = _AderListingParser()
    provenance_parser.feed(html)
    declared_urls = tuple(provenance_parser.declared_source_urls)
    if not declared_urls:
        raise AderImportError(
            "Il file HTML non dichiara una URL canonica: provenienza ADER "
            "non verificabile."
        )
    if not all(is_official_ader_url(url) for url in declared_urls):
        raise AderImportError(
            "Il file HTML dichiara una provenienza esterna ad ADER."
        )
    return parse_ader_html(html, listing_url, limit=limit)


def get_verified_ader_source(connection: sqlite3.Connection) -> OfficialSource:
    matches = [
        source
        for source in list_sources(connection)
        if source.ente.casefold() == "agenzia delle entrate-riscossione"
        and source.stato_verifica == "verificato"
        and source.attiva
        and source.url_modulistica
    ]
    if len(matches) != 1:
        raise AderImportError(
            "Serve una sola fonte ADER attiva, verificata e dotata di URL modulistica."
        )
    source = matches[0]
    if source.id is None or not is_official_ader_url(source.url_modulistica):
        raise AderImportError("La fonte ADER registrata non usa un dominio ufficiale.")
    return source


def fetch_ader_modules(
    listing_url: str,
    *,
    limit: int = DEFAULT_BATCH_SIZE,
    request_get: Callable[..., Any] = requests.get,
) -> ParsedAderBatch:
    validate_batch_limit(limit)
    if not is_official_ader_url(listing_url):
        raise AderImportError("La URL modulistica registrata non appartiene ad ADER.")
    last_error: Exception | None = None
    for _attempt in range(MAX_HTTP_ATTEMPTS):
        try:
            response = request_get(
                listing_url,
                headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
                timeout=REQUEST_TIMEOUT,
            )
            if getattr(response, "status_code", None) in {403, 429}:
                raise AderImportError(
                    "La fonte ADER ha rifiutato o limitato la richiesta; "
                    "l'importatore non tenta di aggirare il blocco."
                )
            response.raise_for_status()
            return parse_ader_html(response.text, listing_url, limit=limit)
        except AderImportError:
            raise
        except requests.RequestException as exc:
            last_error = exc
    raise AderImportError(
        "La fonte ADER non è raggiungibile tramite HTTP semplice."
    ) from last_error


def _as_document(
    module: AderModule,
    source: OfficialSource,
    detection_date: str,
) -> AdministrativeDocument:
    return AdministrativeDocument(
        ente=source.ente,
        codice=module.codice,
        titolo_ufficiale=module.titolo_ufficiale,
        categoria=module.categoria,
        descrizione_ufficiale=module.descrizione_ufficiale,
        significato_semplice=None,
        fonte_url=module.fonte_url,
        download_url=module.download_url,
        detail_url=module.detail_url,
        data_pubblicazione=module.data_pubblicazione,
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
        document.data_pubblicazione,
        document.versione,
        document.source_id,
    )


def _record_provenance(
    connection: sqlite3.Connection,
    document: AdministrativeDocument,
    module: AderModule,
    detection_date: str,
    acquisition_method: str,
) -> None:
    assert document.id is not None and document.source_id is not None
    content_hash = metadata_hash(
        {
            "code": module.codice,
            "title": module.titolo_ufficiale,
            "category": module.categoria,
            "description": module.descrizione_ufficiale,
            "detail_url": module.detail_url,
            "download_url": module.download_url,
            "publication_date": module.data_pubblicazione,
        }
    )
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
            content_hash=content_hash,
            acquisition_method=acquisition_method,
            source_status="rilevato",
        ),
    )


def _apply_ader_batch(
    connection: sqlite3.Connection,
    source: OfficialSource,
    batch: ParsedAderBatch,
    *,
    dry_run: bool = True,
    detection_date: str | None = None,
    acquisition_method: str = "ader_html",
) -> AderImportReport:
    if dry_run:
        return AderImportReport(
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
            code=module.codice,
            official_urls=(module.detail_url, module.download_url),
            title=module.titolo_ufficiale,
            documents=existing_documents,
        )
        try:
            if existing is None:
                inserted = replace(candidate, id=insert_document(connection, candidate))
                existing_documents.append(inserted)
                _record_provenance(
                    connection, inserted, module, detected_on, acquisition_method
                )
                new += 1
            elif existing.stato_verifica == "verificato":
                _record_provenance(
                    connection, existing, module, detected_on, acquisition_method
                )
                already_present += 1
            elif _source_metadata(existing) == _source_metadata(candidate):
                _record_provenance(
                    connection, existing, module, detected_on, acquisition_method
                )
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
                _record_provenance(
                    connection, refreshed, module, detected_on, acquisition_method
                )
                updated += 1
            else:
                already_present += 1
        except sqlite3.Error:
            errors += 1

    return AderImportReport(
        examined=batch.examined,
        new=new,
        updated=updated,
        already_present=already_present,
        discarded=batch.discarded,
        errors=errors,
        modules=batch.modules,
    )


def import_ader_modules(
    connection: sqlite3.Connection,
    *,
    limit: int = DEFAULT_BATCH_SIZE,
    dry_run: bool = True,
    request_get: Callable[..., Any] = requests.get,
    detection_date: str | None = None,
) -> AderImportReport:
    validate_batch_limit(limit)
    source = get_verified_ader_source(connection)
    assert source.url_modulistica is not None and source.id is not None
    batch = fetch_ader_modules(
        source.url_modulistica,
        limit=limit,
        request_get=request_get,
    )
    return _apply_ader_batch(
        connection,
        source,
        batch,
        dry_run=dry_run,
        detection_date=detection_date,
        acquisition_method="ader_html",
    )


def import_saved_ader_html(
    connection: sqlite3.Connection,
    html: str,
    *,
    limit: int = DEFAULT_BATCH_SIZE,
    dry_run: bool = True,
    detection_date: str | None = None,
) -> AderImportReport:
    validate_batch_limit(limit)
    source = get_verified_ader_source(connection)
    assert source.url_modulistica is not None and source.id is not None
    batch = parse_saved_ader_html(html, source.url_modulistica, limit=limit)
    return _apply_ader_batch(
        connection,
        source,
        batch,
        dry_run=dry_run,
        detection_date=detection_date,
        acquisition_method="ader_html_manuale",
    )


def preview_lines(report: AderImportReport) -> list[str]:
    lines = ["CODICE | TITOLO | CATEGORIA | URL"]
    lines.extend(
        " | ".join(
            (
                module.codice or "-",
                module.titolo_ufficiale,
                module.categoria or "-",
                module.detail_url or module.download_url or module.fonte_url,
            )
        )
        for module in report.modules
    )
    return lines


def format_report(report: AderImportReport) -> str:
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
