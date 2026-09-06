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
    validate_offset,
    validate_record_limit,
)
from src.models import AdministrativeDocument, DocumentProvenance, OfficialSource
from src.official_urls import is_official_ade_url
from src.provenance import upsert_document_provenance
from src.recognize import normalize_text
from src.sources import list_sources, update_source_coverage


DEFAULT_LIMIT = 50
MAX_LIMIT = 500
DOWNLOAD_SUFFIXES = {".pdf", ".doc", ".docx", ".rtf", ".zip"}


class AdeImportError(RuntimeError):
    """Errore controllato durante l'acquisizione dei metadati ADE."""


@dataclass(frozen=True, slots=True)
class AdeModule:
    titolo_ufficiale: str
    categoria: str | None
    anno: str | None
    codice: str | None
    fonte_url: str
    detail_url: str
    model_url: str | None = None
    instructions_url: str | None = None


@dataclass(frozen=True, slots=True)
class ParsedAdeBatch:
    modules: tuple[AdeModule, ...]
    examined: int
    discarded: int
    errors: int = 0
    total_available: int = 0


@dataclass(frozen=True, slots=True)
class AdeImportReport:
    source: str = "Agenzia delle Entrate"
    examined: int = 0
    new: int = 0
    updated: int = 0
    already_present: int = 0
    discarded: int = 0
    errors: int = 0
    total_available: int = 0
    modules: tuple[AdeModule, ...] = field(default_factory=tuple)


def validate_limit(limit: int) -> int:
    return validate_record_limit(limit, maximum=MAX_LIMIT, source_name="ADE")


def _year_from(*values: str | None) -> str | None:
    for value in values:
        years = re.findall(r"(?<!\d)((?:19|20)\d{2})(?!\d)", value or "")
        if years:
            return years[-1]
    return None


def _code_from_title(title: str) -> str | None:
    match = re.search(
        r"\b(?:F(?:23|24)|730|770|CU|AA\d{1,2}(?:/\d{1,2})?)\b",
        title,
        flags=re.IGNORECASE,
    )
    return match.group(0).upper() if match else None


class _AdeListingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.records: list[tuple[str, str, str | None]] = []
        self._button_depth = 0
        self._button_text: list[str] = []
        self._category: str | None = None
        self._eligible_li_depth = 0
        self._anchor_href: str | None = None
        self._anchor_text: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = {name: value or "" for name, value in attrs}
        if tag == "button":
            self._button_depth += 1
            self._button_text = []
        if tag == "li" and "data-tag" in attributes:
            self._eligible_li_depth += 1
        if tag == "a" and self._eligible_li_depth and attributes.get("href"):
            self._anchor_href = attributes["href"]
            self._anchor_text = []

    def handle_data(self, data: str) -> None:
        if self._button_depth:
            self._button_text.append(data)
        if self._anchor_href is not None:
            self._anchor_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "button" and self._button_depth:
            self._button_depth -= 1
            if not self._button_depth:
                candidate = clean_text(" ".join(self._button_text))
                if candidate and not candidate.casefold().startswith("filtra per"):
                    self._category = candidate
        if tag == "a" and self._anchor_href is not None:
            title = clean_text(" ".join(self._anchor_text))
            if title:
                self.records.append((self._anchor_href, title, self._category))
            self._anchor_href = None
            self._anchor_text = []
        if tag == "li" and self._eligible_li_depth:
            self._eligible_li_depth -= 1


class _AdeDetailParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self._anchor_href: str | None = None
        self._anchor_text: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = {name: value or "" for name, value in attrs}
        if tag == "a" and attributes.get("href"):
            self._anchor_href = attributes["href"]
            self._anchor_text = []

    def handle_data(self, data: str) -> None:
        if self._anchor_href is not None:
            self._anchor_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._anchor_href is not None:
            self.links.append(
                (self._anchor_href, clean_text(" ".join(self._anchor_text)) or "")
            )
            self._anchor_href = None
            self._anchor_text = []


def parse_ade_html(
    html: str,
    listing_url: str,
    *,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> ParsedAdeBatch:
    validate_limit(limit)
    validate_offset(offset)
    if not is_official_ade_url(listing_url):
        raise AdeImportError("La URL modulistica registrata non appartiene ad ADE.")
    parser = _AdeListingParser()
    parser.feed(html)
    available_modules: list[AdeModule] = []
    discarded = 0
    seen_urls: set[str] = set()
    for raw_url, title, category in parser.records:
        detail_url = urljoin(listing_url, raw_url)
        if not is_official_ade_url(detail_url) or detail_url in seen_urls:
            discarded += 1
            continue
        seen_urls.add(detail_url)
        available_modules.append(
            AdeModule(
                titolo_ufficiale=title,
                categoria=category,
                anno=_year_from(title, detail_url),
                codice=_code_from_title(title),
                fonte_url=listing_url,
                detail_url=detail_url,
            )
        )
    modules = available_modules[offset : offset + limit]
    examined = min(len(parser.records), offset + len(modules) + discarded)
    return ParsedAdeBatch(
        tuple(modules),
        examined,
        discarded,
        total_available=len(available_modules),
    )


def parse_ade_detail_html(
    html: str, detail_url: str
) -> tuple[str | None, str | None]:
    if not is_official_ade_url(detail_url):
        raise AdeImportError("La pagina dettaglio ADE non usa un dominio ufficiale.")
    parser = _AdeDetailParser()
    parser.feed(html)
    model_url: str | None = None
    instructions_url: str | None = None
    for raw_url, label in parser.links:
        url = urljoin(detail_url, raw_url)
        suffix = urlsplit(url).path.casefold()
        if not is_official_ade_url(url):
            continue
        is_download = any(suffix.endswith(extension) for extension in DOWNLOAD_SUFFIXES)
        if not is_download and "/document" not in suffix:
            continue
        normalized_label = normalize_text(label)
        if "istruz" in normalized_label and instructions_url is None:
            instructions_url = url
        elif (
            any(token in normalized_label for token in ("modello", "fac simile"))
            and model_url is None
        ):
            model_url = url
    return model_url, instructions_url


def get_verified_ade_source(connection: sqlite3.Connection) -> OfficialSource:
    matches = [
        source
        for source in list_sources(connection)
        if source.ente.casefold() == "agenzia delle entrate"
        and source.stato_verifica == "verificato"
        and source.attiva
        and source.url_modulistica
    ]
    if len(matches) != 1:
        raise AdeImportError(
            "Serve una sola fonte ADE attiva, verificata e dotata di URL modulistica."
        )
    source = matches[0]
    if source.id is None or not is_official_ade_url(source.url_modulistica):
        raise AdeImportError("La fonte ADE registrata non usa un dominio ufficiale.")
    return source


def fetch_ade_modules(
    listing_url: str,
    *,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    request_get: Callable[..., Any] = requests.get,
) -> ParsedAdeBatch:
    validate_limit(limit)
    validate_offset(offset)
    html = fetch_official_html(
        listing_url,
        source_name="ADE",
        url_validator=is_official_ade_url,
        error_type=AdeImportError,
        request_get=request_get,
    )
    batch = parse_ade_html(html, listing_url, limit=limit, offset=offset)
    enriched: list[AdeModule] = []
    detail_errors = 0
    for module in batch.modules:
        try:
            detail_html = fetch_official_html(
                module.detail_url,
                source_name="ADE",
                url_validator=is_official_ade_url,
                error_type=AdeImportError,
                request_get=request_get,
            )
            model_url, instructions_url = parse_ade_detail_html(
                detail_html, module.detail_url
            )
            enriched.append(
                replace(
                    module,
                    model_url=model_url,
                    instructions_url=instructions_url,
                )
            )
        except AdeImportError as exc:
            if "non tenta di aggirare" in str(exc):
                raise
            detail_errors += 1
            enriched.append(module)
    return replace(batch, modules=tuple(enriched), errors=detail_errors)


def _as_document(
    module: AdeModule, source: OfficialSource, detection_date: str
) -> AdministrativeDocument:
    return AdministrativeDocument(
        ente=source.ente,
        codice=module.codice,
        titolo_ufficiale=module.titolo_ufficiale,
        categoria=module.categoria,
        descrizione_ufficiale=None,
        significato_semplice=None,
        fonte_url=module.fonte_url,
        download_url=module.model_url,
        detail_url=module.detail_url,
        data_pubblicazione=None,
        versione=module.anno,
        data_rilevazione=detection_date,
        stato_verifica="da_verificare",
        parole_chiave=(),
        source_id=source.id,
    )


def _find_existing(
    module: AdeModule, documents: list[AdministrativeDocument]
) -> AdministrativeDocument | None:
    # Il modello PDF pu\u00f2 essere condiviso da schede ADE diverse: la pagina
    # dettaglio, insieme a titolo/anno/codice, \u00e8 l'identit\u00e0 stabile.
    for document in documents:
        if document.detail_url == module.detail_url:
            return document
    normalized_title = normalize_text(module.titolo_ufficiale)
    return next(
        (
            document
            for document in documents
            if normalize_text(document.titolo_ufficiale) == normalized_title
            and document.versione == module.anno
            and (not module.codice or document.codice == module.codice)
        ),
        None,
    )


def _source_metadata(document: AdministrativeDocument) -> tuple[object, ...]:
    return (
        document.ente,
        document.codice,
        document.titolo_ufficiale,
        document.categoria,
        document.fonte_url,
        document.download_url,
        document.detail_url,
        document.versione,
        document.source_id,
    )


def _record_provenance(
    connection: sqlite3.Connection,
    document: AdministrativeDocument,
    module: AdeModule,
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
            download_url=module.model_url,
            acquired_at=detection_date,
            last_seen_at=detection_date,
            content_hash=metadata_hash(
                {
                    "title": module.titolo_ufficiale,
                    "category": module.categoria,
                    "year": module.anno,
                    "code": module.codice,
                    "detail_url": module.detail_url,
                    "model_url": module.model_url,
                    "instructions_url": module.instructions_url,
                }
            ),
            acquisition_method="ade_html",
            source_status="rilevato",
        ),
    )


def import_ade_modules(
    connection: sqlite3.Connection,
    *,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    dry_run: bool = True,
    request_get: Callable[..., Any] = requests.get,
    detection_date: str | None = None,
) -> AdeImportReport:
    validate_limit(limit)
    validate_offset(offset)
    source = get_verified_ade_source(connection)
    assert source.url_modulistica is not None and source.id is not None
    batch = fetch_ade_modules(
        source.url_modulistica,
        limit=limit,
        offset=offset,
        request_get=request_get,
    )
    if dry_run:
        return AdeImportReport(
            examined=batch.examined,
            discarded=batch.discarded,
            errors=batch.errors,
            total_available=batch.total_available,
            modules=batch.modules,
        )

    detected_on = detection_date or date.today().isoformat()
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
    document_count = int(
        connection.execute(
            "SELECT COUNT(*) FROM documents WHERE source_id = ? "
            "AND stato_verifica <> 'demo'",
            (source.id,),
        ).fetchone()[0]
    )
    if document_count >= batch.total_available:
        update_source_coverage(
            connection, source.id, "completa_rispetto_alla_fonte"
        )
    return AdeImportReport(
        examined=batch.examined,
        new=new,
        updated=updated,
        already_present=already_present,
        discarded=batch.discarded,
        errors=errors,
        total_available=batch.total_available,
        modules=batch.modules,
    )


def preview_lines(report: AdeImportReport) -> list[str]:
    lines = ["TITOLO | CATEGORIA | ANNO | MODELLO | ISTRUZIONI | DETTAGLIO"]
    lines.extend(
        " | ".join(
            (
                module.titolo_ufficiale,
                module.categoria or "-",
                module.anno or "-",
                module.model_url or "-",
                module.instructions_url or "-",
                module.detail_url,
            )
        )
        for module in report.modules
    )
    return lines


def format_report(report: AdeImportReport) -> str:
    return "\n".join(
        (
            f"Fonte: {report.source}",
            f"Esaminati: {report.examined}",
            f"Nuovi: {report.new}",
            f"Aggiornati: {report.updated}",
            f"Già presenti: {report.already_present}",
            f"Scartati: {report.discarded}",
            f"Errori: {report.errors}",
            f"Disponibili nella raccolta analizzata: {report.total_available}",
        )
    )
