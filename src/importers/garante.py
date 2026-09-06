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
from src.official_urls import is_official_garante_url
from src.provenance import upsert_document_provenance
from src.recognize import normalize_text
from src.sources import list_sources


DEFAULT_LIMIT = 50
MAX_LIMIT = 50
DOWNLOAD_SUFFIXES = {".pdf", ".doc", ".docx", ".odt", ".rtf"}
GARANTE_CATEGORY = "Modulistica e servizi online"


class GaranteImportError(RuntimeError):
    """Errore controllato durante l'acquisizione dei metadati del Garante."""


@dataclass(frozen=True, slots=True)
class GaranteModule:
    titolo_ufficiale: str
    categoria: str | None
    descrizione_ufficiale: str | None
    fonte_url: str
    detail_url: str
    download_url: str | None
    formati: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ParsedGaranteBatch:
    modules: tuple[GaranteModule, ...]
    examined: int
    discarded: int


@dataclass(frozen=True, slots=True)
class GaranteImportReport:
    source: str = "Garante per la protezione dei dati personali"
    examined: int = 0
    new: int = 0
    updated: int = 0
    already_present: int = 0
    discarded: int = 0
    errors: int = 0
    modules: tuple[GaranteModule, ...] = field(default_factory=tuple)


def validate_limit(limit: int) -> int:
    return validate_record_limit(limit, maximum=MAX_LIMIT, source_name="Garante")


@dataclass(slots=True)
class _PrivacySection:
    title: str
    paragraphs: list[str] = field(default_factory=list)
    links: list[tuple[str, str]] = field(default_factory=list)


class _GaranteParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.sections: list[_PrivacySection] = []
        self._section: _PrivacySection | None = None
        self._content_div_depth = 0
        self._heading_depth = 0
        self._heading_text: list[str] = []
        self._paragraph_depth = 0
        self._paragraph_text: list[str] = []
        self._anchor_href: str | None = None
        self._anchor_text: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = {name: value or "" for name, value in attrs}
        if tag == "div" and attributes.get("id") == "interna-webcontent":
            self._content_div_depth += 1
            return
        if self._content_div_depth and tag == "div":
            self._content_div_depth += 1
        if not self._content_div_depth:
            return
        if tag == "span" and "font-size:28" in attributes.get("style", "").replace(
            " ", ""
        ).casefold():
            self._heading_depth += 1
            self._heading_text = []
        if tag == "p":
            self._paragraph_depth += 1
            self._paragraph_text = []
        if tag == "a" and attributes.get("href"):
            self._anchor_href = attributes["href"]
            self._anchor_text = []

    def handle_data(self, data: str) -> None:
        if not self._content_div_depth:
            return
        if self._heading_depth:
            self._heading_text.append(data)
        if self._paragraph_depth:
            self._paragraph_text.append(data)
        if self._anchor_href is not None:
            self._anchor_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if not self._content_div_depth:
            return
        if tag == "span" and self._heading_depth:
            self._heading_depth -= 1
            if not self._heading_depth:
                title = clean_text(" ".join(self._heading_text))
                title = clean_text(re.sub(r"^\s*-\s*", "", title or ""))
                if title:
                    if self._section is not None:
                        self.sections.append(self._section)
                    self._section = _PrivacySection(title=title)
        if tag == "a" and self._anchor_href is not None:
            if self._section is not None:
                self._section.links.append(
                    (
                        self._anchor_href,
                        clean_text(" ".join(self._anchor_text)) or "",
                    )
                )
            self._anchor_href = None
            self._anchor_text = []
        if tag == "p" and self._paragraph_depth:
            self._paragraph_depth -= 1
            if not self._paragraph_depth and self._section is not None:
                paragraph = clean_text(" ".join(self._paragraph_text))
                if paragraph:
                    self._section.paragraphs.append(paragraph)
        if tag == "div":
            self._content_div_depth -= 1

    def close(self) -> None:
        super().close()
        if self._section is not None:
            self.sections.append(self._section)
            self._section = None


def _is_download(url: str, label: str) -> bool:
    path = urlsplit(url).path.casefold()
    normalized_label = label.casefold()
    return (
        any(path.endswith(suffix) for suffix in DOWNLOAD_SUFFIXES)
        or any(suffix in normalized_label for suffix in DOWNLOAD_SUFFIXES)
        or path.endswith("/garante/document")
    )


def _description(section: _PrivacySection) -> str | None:
    normalized_title = section.title.casefold()
    for paragraph in section.paragraphs:
        normalized = paragraph.casefold().lstrip("- ")
        if (
            len(paragraph) >= 40
            and not normalized.startswith(normalized_title)
            and not normalized.startswith(("pagina informativa", "modello", "formato"))
            and "attenzione:" not in normalized
        ):
            return paragraph
    return None


def parse_garante_html(
    html: str, listing_url: str, *, limit: int = DEFAULT_LIMIT
) -> ParsedGaranteBatch:
    validate_limit(limit)
    if not is_official_garante_url(listing_url):
        raise GaranteImportError(
            "La URL modulistica registrata non appartiene al Garante Privacy."
        )
    parser = _GaranteParser()
    parser.feed(html)
    parser.close()
    modules: list[GaranteModule] = []
    discarded = 0
    seen_titles: set[str] = set()
    for section in parser.sections:
        if len(modules) >= limit:
            break
        official_links: list[tuple[str, str]] = []
        for raw_url, label in section.links:
            url = urljoin(listing_url, raw_url)
            if is_official_garante_url(url):
                official_links.append((url, label))
        if not official_links:
            discarded += 1
            continue
        normalized_title = section.title.casefold()
        if normalized_title in seen_titles:
            discarded += 1
            continue
        seen_titles.add(normalized_title)
        downloads = [item for item in official_links if _is_download(*item)]
        detail_links = [item for item in official_links if not _is_download(*item)]
        download_url = downloads[0][0] if downloads else None
        detail_url = detail_links[0][0] if detail_links else listing_url
        formats: list[str] = []
        for url, label in downloads:
            combined = f"{url} {label}".casefold()
            for extension in re.findall(r"\.(docx|doc|pdf|odt|rtf)\b", combined):
                if extension.upper() not in formats:
                    formats.append(extension.upper())
        modules.append(
            GaranteModule(
                titolo_ufficiale=section.title,
                categoria=GARANTE_CATEGORY,
                descrizione_ufficiale=_description(section),
                fonte_url=listing_url,
                detail_url=detail_url,
                download_url=download_url,
                formati=tuple(formats),
            )
        )
    return ParsedGaranteBatch(
        tuple(modules), min(len(parser.sections), limit + discarded), discarded
    )


def get_verified_garante_source(connection: sqlite3.Connection) -> OfficialSource:
    matches = [
        source
        for source in list_sources(connection)
        if source.ente.casefold()
        == "garante per la protezione dei dati personali"
        and source.stato_verifica == "verificato"
        and source.attiva
        and source.url_modulistica
    ]
    if len(matches) != 1:
        raise GaranteImportError(
            "Serve una sola fonte Garante attiva, verificata e dotata di URL modulistica."
        )
    source = matches[0]
    if source.id is None or not is_official_garante_url(source.url_modulistica):
        raise GaranteImportError(
            "La fonte Garante registrata non usa un dominio ufficiale."
        )
    return source


def fetch_garante_modules(
    listing_url: str,
    *,
    limit: int = DEFAULT_LIMIT,
    request_get: Callable[..., Any] = requests.get,
) -> ParsedGaranteBatch:
    validate_limit(limit)
    html = fetch_official_html(
        listing_url,
        source_name="Garante Privacy",
        url_validator=is_official_garante_url,
        error_type=GaranteImportError,
        request_get=request_get,
    )
    return parse_garante_html(html, listing_url, limit=limit)


def _as_document(
    module: GaranteModule, source: OfficialSource, detection_date: str
) -> AdministrativeDocument:
    return AdministrativeDocument(
        ente=source.ente,
        codice=None,
        titolo_ufficiale=module.titolo_ufficiale,
        categoria=module.categoria,
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
        document.titolo_ufficiale,
        document.categoria,
        document.descrizione_ufficiale,
        document.fonte_url,
        document.download_url,
        document.detail_url,
        document.source_id,
    )


def _find_existing(
    module: GaranteModule, documents: list[AdministrativeDocument]
) -> AdministrativeDocument | None:
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
    module: GaranteModule,
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
                    "description": module.descrizione_ufficiale,
                    "detail_url": module.detail_url,
                    "download_url": module.download_url,
                    "formats": module.formati,
                }
            ),
            acquisition_method="garante_html",
            source_status="rilevato",
        ),
    )


def import_garante_modules(
    connection: sqlite3.Connection,
    *,
    limit: int = DEFAULT_LIMIT,
    dry_run: bool = True,
    request_get: Callable[..., Any] = requests.get,
    detection_date: str | None = None,
) -> GaranteImportReport:
    validate_limit(limit)
    source = get_verified_garante_source(connection)
    assert source.url_modulistica is not None and source.id is not None
    batch = fetch_garante_modules(
        source.url_modulistica, limit=limit, request_get=request_get
    )
    if dry_run:
        return GaranteImportReport(
            examined=batch.examined,
            discarded=batch.discarded,
            modules=batch.modules,
        )

    detected_on = detection_date or date.today().isoformat()
    existing_documents = list_documents_for_source(connection, source.id)
    new = updated = already_present = errors = 0
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
    return GaranteImportReport(
        examined=batch.examined,
        new=new,
        updated=updated,
        already_present=already_present,
        discarded=batch.discarded,
        errors=errors,
        modules=batch.modules,
    )


def preview_lines(report: GaranteImportReport) -> list[str]:
    lines = ["TITOLO | FORMATI | DOWNLOAD | DETTAGLIO"]
    lines.extend(
        " | ".join(
            (
                module.titolo_ufficiale,
                ", ".join(module.formati) or "-",
                module.download_url or "-",
                module.detail_url,
            )
        )
        for module in report.modules
    )
    return lines


def format_report(report: GaranteImportReport) -> str:
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
