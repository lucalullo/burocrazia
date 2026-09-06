from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date
from html.parser import HTMLParser
import re
import sqlite3
from typing import Any, Callable
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

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
    validate_offset,
    validate_record_limit,
)
from src.models import AdministrativeDocument, DocumentProvenance, OfficialSource
from src.official_urls import is_official_lavoro_url
from src.provenance import upsert_document_provenance
from src.recognize import normalize_text
from src.sources import list_sources, update_source_coverage


DEFAULT_LIMIT = 50
MAX_LIMIT = 500
MAX_LISTING_PAGES = 25


class LavoroImportError(RuntimeError):
    """Errore controllato durante l'acquisizione del Ministero del Lavoro."""


@dataclass(frozen=True, slots=True)
class LavoroModule:
    titolo_ufficiale: str
    area: str | None
    categoria: str | None
    tipologia_utente: str | None
    finalita: str | None
    descrizione_ufficiale: str | None
    anno: str | None
    fonte_url: str
    detail_url: str
    download_url: str | None


@dataclass(frozen=True, slots=True)
class ParsedLavoroBatch:
    modules: tuple[LavoroModule, ...]
    examined: int
    discarded: int
    source_exhausted: bool = False


@dataclass(frozen=True, slots=True)
class LavoroImportReport:
    source: str = "Ministero del Lavoro"
    examined: int = 0
    new: int = 0
    updated: int = 0
    already_present: int = 0
    discarded: int = 0
    errors: int = 0
    source_exhausted: bool = False
    modules: tuple[LavoroModule, ...] = field(default_factory=tuple)


def validate_limit(limit: int) -> int:
    return validate_record_limit(limit, maximum=MAX_LIMIT, source_name="Lavoro")


def _year_from(*values: str | None) -> str | None:
    for value in values:
        matches = re.findall(r"(?<!\d)((?:19|20)\d{2})(?!\d)", value or "")
        if matches:
            return matches[-1]
    return None


@dataclass(slots=True)
class _ListingRow:
    title: str | None = None
    text: list[str] = field(default_factory=list)
    downloads: list[tuple[str, str]] = field(default_factory=list)
    area: str | None = None
    category: str | None = None
    user_type: str | None = None
    purpose: str | None = None


class _LavoroListingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[_ListingRow] = []
        self._row: _ListingRow | None = None
        self._row_div_depth = 0
        self._heading_depth = 0
        self._heading_text: list[str] = []
        self._anchor_href: str | None = None
        self._anchor_download = False
        self._anchor_text: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = {name: value or "" for name, value in attrs}
        classes = set(attributes.get("class", "").split())
        if tag == "div" and self._row is None and "views-row" in classes:
            self._row = _ListingRow(
                area=clean_text(attributes.get("data-area")),
                category=clean_text(attributes.get("data-category")),
                user_type=clean_text(attributes.get("data-user")),
                purpose=clean_text(attributes.get("data-purpose")),
            )
            self._row_div_depth = 1
            return
        if self._row is None:
            return
        if tag == "div":
            self._row_div_depth += 1
        if tag in {"h2", "h3"}:
            self._heading_depth += 1
            self._heading_text = []
        if tag == "a" and attributes.get("href"):
            self._anchor_href = attributes["href"]
            self._anchor_download = "download" in attributes
            self._anchor_text = []

    def handle_data(self, data: str) -> None:
        if self._row is None:
            return
        self._row.text.append(data)
        if self._heading_depth:
            self._heading_text.append(data)
        if self._anchor_href is not None:
            self._anchor_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._row is None:
            return
        if tag in {"h2", "h3"} and self._heading_depth:
            self._heading_depth -= 1
            if not self._heading_depth and self._row.title is None:
                self._row.title = clean_text(" ".join(self._heading_text))
        if tag == "a" and self._anchor_href is not None:
            label = clean_text(" ".join(self._anchor_text))
            if label and (
                self._anchor_download
                or "compila il modulo" not in label.casefold()
            ):
                self._row.downloads.append((self._anchor_href, label))
            self._anchor_href = None
            self._anchor_download = False
            self._anchor_text = []
        if tag == "div":
            self._row_div_depth -= 1
            if self._row_div_depth == 0:
                self.rows.append(self._row)
                self._row = None


def _row_description(row: _ListingRow) -> str | None:
    text = clean_text(" ".join(row.text))
    if not text:
        return None
    removable = sorted(
        [row.title or "", *(label for _url, label in row.downloads)],
        key=len,
        reverse=True,
    )
    for value in removable:
        if value:
            text = re.sub(re.escape(value), " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\bCompila il modulo\b", " ", text, flags=re.IGNORECASE)
    return clean_text(text)


def parse_lavoro_html(
    html: str, listing_url: str, *, limit: int = DEFAULT_LIMIT
) -> ParsedLavoroBatch:
    validate_limit(limit)
    if not is_official_lavoro_url(listing_url):
        raise LavoroImportError(
            "La URL modulistica registrata non appartiene al Ministero del Lavoro."
        )
    parser = _LavoroListingParser()
    parser.feed(html)
    modules: list[LavoroModule] = []
    discarded = 0
    seen_urls: set[str] = set()
    for row in parser.rows:
        description = _row_description(row)
        links = row.downloads or []
        if not links:
            discarded += 1
            continue
        for raw_url, label in links:
            if len(modules) >= limit:
                break
            url = urljoin(listing_url, raw_url)
            if not is_official_lavoro_url(url) or url in seen_urls:
                discarded += 1
                continue
            seen_urls.add(url)
            title = label or row.title
            if not title:
                discarded += 1
                continue
            modules.append(
                LavoroModule(
                    titolo_ufficiale=title,
                    area=row.area,
                    categoria=row.category,
                    tipologia_utente=row.user_type,
                    finalita=row.purpose,
                    descrizione_ufficiale=description,
                    anno=_year_from(title, row.title, description, url),
                    fonte_url=listing_url,
                    detail_url=listing_url,
                    download_url=url,
                )
            )
        if len(modules) >= limit:
            break
    return ParsedLavoroBatch(
        tuple(modules), min(len(parser.rows), limit + discarded), discarded
    )


def _page_url(listing_url: str, page: int) -> str:
    parsed = urlsplit(listing_url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["page"] = str(page)
    return urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment)
    )


def get_verified_lavoro_source(connection: sqlite3.Connection) -> OfficialSource:
    matches = [
        source
        for source in list_sources(connection)
        if source.ente.casefold() == "ministero del lavoro"
        and source.stato_verifica == "verificato"
        and source.attiva
        and source.url_modulistica
    ]
    if len(matches) != 1:
        raise LavoroImportError(
            "Serve una sola fonte Lavoro attiva, verificata e dotata di URL modulistica."
        )
    source = matches[0]
    if source.id is None or not is_official_lavoro_url(source.url_modulistica):
        raise LavoroImportError("La fonte Lavoro registrata non usa un dominio ufficiale.")
    return source


def fetch_lavoro_modules(
    listing_url: str,
    *,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    request_get: Callable[..., Any] = requests.get,
) -> ParsedLavoroBatch:
    validate_limit(limit)
    validate_offset(offset)
    available_modules: list[LavoroModule] = []
    seen_urls: set[str] = set()
    examined = discarded = 0
    source_exhausted = False
    for page in range(MAX_LISTING_PAGES):
        page_url = listing_url if page == 0 else _page_url(listing_url, page)
        html = fetch_official_html(
            page_url,
            source_name="Ministero del Lavoro",
            url_validator=is_official_lavoro_url,
            error_type=LavoroImportError,
            request_get=request_get,
        )
        batch = parse_lavoro_html(html, page_url, limit=MAX_LIMIT)
        fresh = [
            module for module in batch.modules if module.download_url not in seen_urls
        ]
        if not fresh:
            source_exhausted = True
            break
        for module in fresh:
            seen_urls.add(module.download_url or module.detail_url)
            available_modules.append(replace(module, fonte_url=listing_url))
        examined += batch.examined
        discarded += batch.discarded + (len(batch.modules) - len(fresh))
        if len(available_modules) >= offset + limit:
            break
    return ParsedLavoroBatch(
        tuple(available_modules[offset : offset + limit]),
        examined,
        discarded,
        source_exhausted,
    )


def _as_document(
    module: LavoroModule, source: OfficialSource, detection_date: str
) -> AdministrativeDocument:
    return AdministrativeDocument(
        ente=source.ente,
        codice=None,
        titolo_ufficiale=module.titolo_ufficiale,
        categoria=module.categoria or module.area,
        descrizione_ufficiale=module.descrizione_ufficiale,
        significato_semplice=None,
        fonte_url=module.fonte_url,
        download_url=module.download_url,
        detail_url=module.detail_url,
        data_pubblicazione=None,
        versione=module.anno,
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
        document.descrizione_ufficiale,
        document.fonte_url,
        document.download_url,
        document.detail_url,
        document.versione,
        document.source_id,
    )


def _record_provenance(
    connection: sqlite3.Connection,
    document: AdministrativeDocument,
    module: LavoroModule,
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
                    "area": module.area,
                    "category": module.categoria,
                    "user_type": module.tipologia_utente,
                    "purpose": module.finalita,
                    "description": module.descrizione_ufficiale,
                    "year": module.anno,
                    "download_url": module.download_url,
                }
            ),
            acquisition_method="lavoro_html",
            source_status="rilevato",
        ),
    )


def import_lavoro_modules(
    connection: sqlite3.Connection,
    *,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    dry_run: bool = True,
    request_get: Callable[..., Any] = requests.get,
    detection_date: str | None = None,
) -> LavoroImportReport:
    validate_limit(limit)
    validate_offset(offset)
    source = get_verified_lavoro_source(connection)
    assert source.url_modulistica is not None and source.id is not None
    batch = fetch_lavoro_modules(
        source.url_modulistica,
        limit=limit,
        offset=offset,
        request_get=request_get,
    )
    if dry_run:
        return LavoroImportReport(
            examined=batch.examined,
            discarded=batch.discarded,
            source_exhausted=batch.source_exhausted,
            modules=batch.modules,
        )

    detected_on = detection_date or date.today().isoformat()
    existing_documents = list_documents_for_source(connection, source.id)
    new = updated = already_present = errors = 0
    for module in batch.modules:
        candidate = _as_document(module, source, detected_on)
        existing = next(
            (
                document
                for document in existing_documents
                if module.download_url
                and module.download_url
                in {document.download_url, document.detail_url}
            ),
            None,
        )
        if existing is None:
            normalized_title = normalize_text(module.titolo_ufficiale)
            existing = next(
                (
                    document
                    for document in existing_documents
                    if normalize_text(document.titolo_ufficiale) == normalized_title
                    and document.versione == module.anno
                ),
                None,
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
    document_count = int(
        connection.execute(
            "SELECT COUNT(*) FROM documents WHERE source_id = ? "
            "AND stato_verifica <> 'demo'",
            (source.id,),
        ).fetchone()[0]
    )
    if batch.source_exhausted and errors == 0 and document_count >= offset:
        update_source_coverage(
            connection, source.id, "completa_rispetto_alla_fonte"
        )
    return LavoroImportReport(
        examined=batch.examined,
        new=new,
        updated=updated,
        already_present=already_present,
        discarded=batch.discarded,
        errors=errors,
        source_exhausted=batch.source_exhausted,
        modules=batch.modules,
    )


def preview_lines(report: LavoroImportReport) -> list[str]:
    lines = ["TITOLO | AREA | CATEGORIA | UTENTE | FINALITÀ | URL"]
    lines.extend(
        " | ".join(
            (
                module.titolo_ufficiale,
                module.area or "-",
                module.categoria or "-",
                module.tipologia_utente or "-",
                module.finalita or "-",
                module.download_url or module.detail_url,
            )
        )
        for module in report.modules
    )
    return lines


def format_report(report: LavoroImportReport) -> str:
    return "\n".join(
        (
            f"Fonte: {report.source}",
            f"Esaminati: {report.examined}",
            f"Nuovi: {report.new}",
            f"Aggiornati: {report.updated}",
            f"Già presenti: {report.already_present}",
            f"Scartati: {report.discarded}",
            f"Errori: {report.errors}",
            "Fonte analizzata esaurita: "
            + ("s\u00ec" if report.source_exhausted else "no"),
        )
    )
