from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime
from html.parser import HTMLParser
from typing import Any, Callable, Mapping
from urllib.parse import urljoin, urlsplit, urlunsplit

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
    metadata_hash,
    validate_record_limit,
)
from src.models import AdministrativeDocument, DocumentProvenance, OfficialSource
from src.official_urls import is_official_inps_url
from src.provenance import upsert_document_provenance
from src.recognize import normalize_text
from src.sources import list_sources


DEFAULT_LIMIT = DEFAULT_BATCH_SIZE
MAX_LIMIT = 200


class InpsImportError(RuntimeError):
    """Errore controllato durante l'acquisizione dei metadati INPS."""


@dataclass(frozen=True, slots=True)
class InpsModule:
    codice: str | None
    titolo_ufficiale: str
    categoria: str | None
    descrizione_ufficiale: str | None
    fonte_url: str
    download_url: str | None
    detail_url: str | None
    data_pubblicazione: str | None
    versione: str | None


@dataclass(frozen=True, slots=True)
class ParsedBatch:
    modules: tuple[InpsModule, ...]
    examined: int
    discarded: int


@dataclass(frozen=True, slots=True)
class ImportReport:
    source: str = "INPS"
    examined: int = 0
    new: int = 0
    updated: int = 0
    already_present: int = 0
    discarded: int = 0
    errors: int = 0
    modules: tuple[InpsModule, ...] = field(default_factory=tuple)


def validate_limit(limit: int) -> int:
    return validate_record_limit(limit, maximum=MAX_LIMIT, source_name="INPS")


def validate_page(page: int) -> int:
    if isinstance(page, bool) or not isinstance(page, int) or page < 1:
        raise ValueError("La pagina INPS deve essere un intero maggiore o uguale a 1.")
    return page


def _official_url(raw_url: object, base_url: str) -> str | None:
    if raw_url is None:
        return None
    cleaned = str(raw_url).strip()
    if not cleaned:
        return None
    resolved = urljoin(base_url, cleaned)
    if not is_official_inps_url(resolved):
        raise ValueError("URL esterno o non istituzionale rifiutato.")
    return resolved


def derive_search_endpoint(listing_url: str) -> str:
    if not is_official_inps_url(listing_url):
        raise InpsImportError("La URL modulistica registrata non appartiene a INPS.")
    parsed = urlsplit(listing_url)
    if not parsed.path.endswith(".html"):
        raise InpsImportError("La URL modulistica INPS non ha il formato atteso.")
    endpoint_path = parsed.path.removesuffix(".html") + ".cfListDynamic.search.json"
    endpoint = urlunsplit((parsed.scheme, parsed.netloc, endpoint_path, "", ""))
    if not is_official_inps_url(endpoint):
        raise InpsImportError("L'endpoint derivato non appartiene a INPS.")
    return endpoint


def get_verified_inps_source(connection: sqlite3.Connection) -> OfficialSource:
    matches = [
        source
        for source in list_sources(connection)
        if source.ente.casefold() == "inps"
        and source.stato_verifica == "verificato"
        and source.attiva
        and source.url_modulistica
    ]
    if len(matches) != 1:
        raise InpsImportError(
            "Serve una sola fonte INPS attiva, verificata e dotata di URL modulistica."
        )
    source = matches[0]
    if source.id is None:
        raise InpsImportError("La fonte INPS verificata non ha un identificativo.")
    if not is_official_inps_url(source.url_modulistica):
        raise InpsImportError("La URL modulistica registrata non appartiene a INPS.")
    return source


def _clean_text(value: object) -> str | None:
    if value is None or isinstance(value, (dict, list, tuple)):
        return None
    cleaned = re.sub(r"\s+", " ", str(value)).strip()
    return cleaned or None


def _element_value(item: Mapping[str, Any], name: str) -> Any:
    elements = item.get("elements")
    if not isinstance(elements, Mapping):
        return None
    element = elements.get(name)
    if not isinstance(element, Mapping):
        return None
    return element.get("value")


def _category_value(value: object) -> str | None:
    if isinstance(value, list):
        values = [_clean_text(item) for item in value]
        present = [item for item in values if item]
        return "; ".join(present) or None
    return _clean_text(value)


def _publication_date(value: object) -> str | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        try:
            seconds = float(value) / 1000 if float(value) > 10_000_000_000 else float(value)
            return datetime.fromtimestamp(seconds, tz=UTC).date().isoformat()
        except (OverflowError, OSError, ValueError):
            return None
    cleaned = _clean_text(value)
    if not cleaned:
        return None
    for date_format in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(cleaned, date_format).date().isoformat()
        except ValueError:
            continue
    return None


def _module_from_json_item(
    item: Mapping[str, Any],
    listing_url: str,
) -> InpsModule | None:
    codice = _clean_text(_element_value(item, "codice")) or _clean_text(item.get("title"))
    titolo = _clean_text(_element_value(item, "titolo")) or _clean_text(
        item.get("description")
    )
    if not titolo:
        return None

    raw_date = _element_value(item, "datapubblicazione")
    if raw_date is None:
        metadata = item.get("metadata")
        if isinstance(metadata, Mapping):
            raw_date = metadata.get("dataDiPubblicazione")

    detail_url = _official_url(item.get("paginaDettaglio"), listing_url)
    download_url = _official_url(_element_value(item, "filepdf"), listing_url)
    return InpsModule(
        codice=codice,
        titolo_ufficiale=titolo,
        categoria=_category_value(_element_value(item, "aree")),
        descrizione_ufficiale=_clean_text(_element_value(item, "descrizione")),
        fonte_url=listing_url,
        download_url=download_url,
        detail_url=detail_url,
        data_pubblicazione=_publication_date(raw_date),
        versione=_clean_text(_element_value(item, "versione")),
    )


def parse_inps_json(
    payload: Mapping[str, Any],
    listing_url: str,
    *,
    limit: int = DEFAULT_LIMIT,
) -> ParsedBatch:
    validate_limit(limit)
    if not is_official_inps_url(listing_url):
        raise InpsImportError("La URL modulistica registrata non appartiene a INPS.")
    raw_items = payload.get("items", [])
    if not isinstance(raw_items, list):
        raise InpsImportError("La risposta INPS non contiene una lista di moduli valida.")

    modules: list[InpsModule] = []
    discarded = 0
    candidates = raw_items[:limit]
    for raw_item in candidates:
        if not isinstance(raw_item, Mapping):
            discarded += 1
            continue
        try:
            module = _module_from_json_item(raw_item, listing_url)
        except ValueError:
            discarded += 1
            continue
        if module is None:
            discarded += 1
            continue
        modules.append(module)
    return ParsedBatch(tuple(modules), len(candidates), discarded)


class _InpsTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[dict[str, str]] = []
        self._row: dict[str, str] | None = None
        self._field: str | None = None
        self._text: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        attributes = dict(attrs)
        if tag == "tr":
            self._row = {
                key.removeprefix("data-"): value or ""
                for key, value in attrs
                if key.startswith("data-")
            }
        elif tag == "td" and self._row is not None:
            self._field = attributes.get("data-field")
            self._text = []
        elif tag == "a" and self._row is not None and self._field:
            href = attributes.get("href")
            if href:
                self._row[f"{self._field}_url"] = href

    def handle_data(self, data: str) -> None:
        if self._row is not None and self._field:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "td" and self._row is not None and self._field:
            self._row[self._field] = " ".join(self._text)
            self._field = None
            self._text = []
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None
            self._field = None
            self._text = []


def parse_inps_html(
    html: str,
    listing_url: str,
    *,
    limit: int = DEFAULT_LIMIT,
) -> ParsedBatch:
    """Fallback per una eventuale tabella HTML ufficiale, testato offline."""
    validate_limit(limit)
    if not is_official_inps_url(listing_url):
        raise InpsImportError("La URL modulistica registrata non appartiene a INPS.")
    parser = _InpsTableParser()
    parser.feed(html)
    candidates = parser.rows[:limit]
    modules: list[InpsModule] = []
    discarded = 0
    for row in candidates:
        titolo = _clean_text(row.get("titolo") or row.get("title"))
        if not titolo:
            discarded += 1
            continue
        try:
            detail_url = _official_url(
                row.get("detail_url") or row.get("titolo_url"), listing_url
            )
            download_url = _official_url(
                row.get("download_url") or row.get("pdf_url"), listing_url
            )
        except ValueError:
            discarded += 1
            continue
        modules.append(
            InpsModule(
                codice=_clean_text(row.get("codice") or row.get("code")),
                titolo_ufficiale=titolo,
                categoria=_clean_text(row.get("categoria")),
                descrizione_ufficiale=_clean_text(row.get("descrizione")),
                fonte_url=listing_url,
                download_url=download_url,
                detail_url=detail_url,
                data_pubblicazione=_publication_date(row.get("data")),
                versione=_clean_text(row.get("versione")),
            )
        )
    return ParsedBatch(tuple(modules), len(candidates), discarded)


def fetch_inps_modules(
    listing_url: str,
    *,
    limit: int = DEFAULT_LIMIT,
    page: int = 1,
    request_get: Callable[..., Any] = requests.get,
) -> ParsedBatch:
    validate_limit(limit)
    validate_page(page)
    endpoint = derive_search_endpoint(listing_url)
    last_error: Exception | None = None
    for _attempt in range(MAX_HTTP_ATTEMPTS):
        try:
            response = request_get(
                endpoint,
                params={"maxItems": limit, "currentPage": page, "lang": "it"},
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                timeout=REQUEST_TIMEOUT,
            )
            if getattr(response, "status_code", None) in {403, 429}:
                raise InpsImportError(
                    "La fonte INPS ha rifiutato o limitato la richiesta; "
                    "l'importatore non tenta di aggirare il blocco."
                )
            response.raise_for_status()
            try:
                payload = response.json()
            except (json.JSONDecodeError, requests.exceptions.JSONDecodeError, ValueError):
                return parse_inps_html(response.text, listing_url, limit=limit)
            if not isinstance(payload, Mapping):
                raise InpsImportError("La risposta INPS non è un oggetto JSON valido.")
            return parse_inps_json(payload, listing_url, limit=limit)
        except InpsImportError:
            raise
        except requests.RequestException as exc:
            last_error = exc
    raise InpsImportError(
        "La fonte INPS non è raggiungibile tramite HTTP semplice."
    ) from last_error


def _as_document(
    module: InpsModule,
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
        versione=module.versione,
        data_rilevazione=detection_date,
        stato_verifica="da_verificare",
        parole_chiave=(),
        source_id=source.id,
    )


def _find_existing(
    module: InpsModule,
    documents: list[AdministrativeDocument],
) -> AdministrativeDocument | None:
    for document in documents:
        if module.detail_url and document.detail_url == module.detail_url:
            return document
        if (
            not module.detail_url
            and module.download_url
            and document.download_url == module.download_url
        ):
            return document

    normalized_title = normalize_text(module.titolo_ufficiale)
    if module.codice:
        normalized_code = module.codice.casefold().strip()
        verified_match = next(
            (
                document
                for document in documents
                if document.stato_verifica == "verificato"
                and document.codice
                and document.codice.casefold().strip() == normalized_code
            ),
            None,
        )
        if verified_match is not None:
            return verified_match
        match = next(
            (
                document
                for document in documents
                if document.codice
                and document.codice.casefold().strip() == normalized_code
                and normalize_text(document.titolo_ufficiale) == normalized_title
            ),
            None,
        )
        if match is not None:
            return match
    return next(
        (
            document
            for document in documents
            if normalize_text(document.titolo_ufficiale) == normalized_title
        ),
        None,
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
    module: InpsModule,
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
                    "code": module.codice,
                    "title": module.titolo_ufficiale,
                    "category": module.categoria,
                    "description": module.descrizione_ufficiale,
                    "detail_url": module.detail_url,
                    "download_url": module.download_url,
                    "publication_date": module.data_pubblicazione,
                    "version": module.versione,
                }
            ),
            acquisition_method="inps_json",
            source_status="rilevato",
        ),
    )


def import_inps_modules(
    connection: sqlite3.Connection,
    *,
    limit: int = DEFAULT_LIMIT,
    page: int = 1,
    dry_run: bool = True,
    request_get: Callable[..., Any] = requests.get,
    detection_date: str | None = None,
) -> ImportReport:
    validate_limit(limit)
    validate_page(page)
    source = get_verified_inps_source(connection)
    assert source.url_modulistica is not None and source.id is not None
    batch = fetch_inps_modules(
        source.url_modulistica,
        limit=limit,
        page=page,
        request_get=request_get,
    )
    if dry_run:
        return ImportReport(
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
                document_id = insert_document(connection, candidate)
                inserted = AdministrativeDocument(
                    ente=candidate.ente,
                    titolo_ufficiale=candidate.titolo_ufficiale,
                    categoria=candidate.categoria,
                    descrizione_ufficiale=candidate.descrizione_ufficiale,
                    significato_semplice=candidate.significato_semplice,
                    versione=candidate.versione,
                    data_rilevazione=candidate.data_rilevazione,
                    stato_verifica=candidate.stato_verifica,
                    parole_chiave=candidate.parole_chiave,
                    codice=candidate.codice,
                    fonte_url=candidate.fonte_url,
                    download_url=candidate.download_url,
                    detail_url=candidate.detail_url,
                    data_pubblicazione=candidate.data_pubblicazione,
                    source_id=candidate.source_id,
                    id=document_id,
                )
                existing_documents.append(inserted)
                _record_provenance(connection, inserted, module, detected_on)
                new += 1
            elif existing.stato_verifica == "verificato":
                _record_provenance(connection, existing, module, detected_on)
                already_present += 1
            elif _source_metadata(existing) == _source_metadata(candidate):
                _record_provenance(connection, existing, module, detected_on)
                already_present += 1
            elif existing.id is not None and update_document_source_metadata(
                connection, existing.id, candidate
            ):
                existing_documents.remove(existing)
                refreshed = replace(
                    candidate,
                    id=existing.id,
                    data_rilevazione=existing.data_rilevazione,
                    stato_verifica=existing.stato_verifica,
                    significato_semplice=existing.significato_semplice,
                    parole_chiave=existing.parole_chiave,
                )
                existing_documents.append(refreshed)
                _record_provenance(connection, refreshed, module, detected_on)
                updated += 1
            else:
                already_present += 1
        except sqlite3.Error:
            errors += 1

    return ImportReport(
        examined=batch.examined,
        new=new,
        updated=updated,
        already_present=already_present,
        discarded=batch.discarded,
        errors=errors,
        modules=batch.modules,
    )


def preview_lines(report: ImportReport) -> list[str]:
    lines = ["CODICE | TITOLO | DATA | URL"]
    lines.extend(
        " | ".join(
            (
                module.codice or "-",
                module.titolo_ufficiale,
                module.data_pubblicazione or "-",
                module.detail_url or module.download_url or module.fonte_url,
            )
        )
        for module in report.modules
    )
    return lines


def format_report(report: ImportReport) -> str:
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
