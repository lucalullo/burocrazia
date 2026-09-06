from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import sqlite3
from typing import Any, Callable, Mapping
from urllib.parse import urlsplit

from src import offline_transport as requests

from src.entities import get_entity_by_ipa_code, upsert_entity
from src.importers.common import (
    DEFAULT_BATCH_SIZE,
    MAX_HTTP_ATTEMPTS,
    REQUEST_TIMEOUT,
    USER_AGENT,
    clean_text,
    validate_batch_limit,
)
from src.models import Entity, OfficialSource
from src.official_urls import is_official_ipa_url
from src.sources import list_sources


IPA_RESOURCE_ID = "d09adf99-dc10-4349-8c53-27b1e5aa97b6"
IPA_DATA_API = "https://indicepa.gov.it/ipa-dati/api/3/action/datastore_search"


class IpaImportError(RuntimeError):
    """Safe failure while importing official IPA metadata."""


@dataclass(frozen=True, slots=True)
class ParsedEntityBatch:
    entities: tuple[Entity, ...]
    examined: int
    discarded: int
    total_available: int | None = None


@dataclass(frozen=True, slots=True)
class IpaImportReport:
    source: str = "IPA"
    examined: int = 0
    new: int = 0
    updated: int = 0
    already_present: int = 0
    discarded: int = 0
    errors: int = 0
    total_available: int | None = None
    entities: tuple[Entity, ...] = field(default_factory=tuple)


def validate_offset(offset: int) -> int:
    if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
        raise ValueError("L'offset IPA deve essere un intero maggiore o uguale a zero.")
    return offset


def _safe_reported_site(value: object) -> str | None:
    site = clean_text(value)
    if not site:
        return None
    try:
        parsed = urlsplit(site)
    except ValueError:
        return None
    if (
        parsed.scheme.casefold() not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        return None
    return site


def parse_ipa_payload(
    payload: Mapping[str, Any],
    *,
    limit: int = DEFAULT_BATCH_SIZE,
) -> ParsedEntityBatch:
    validate_batch_limit(limit)
    if payload.get("success") is not True:
        raise IpaImportError("La risposta IPA non segnala un esito valido.")
    result = payload.get("result")
    if not isinstance(result, Mapping):
        raise IpaImportError("La risposta IPA non contiene un risultato valido.")
    raw_records = result.get("records")
    if not isinstance(raw_records, list):
        raise IpaImportError("La risposta IPA non contiene una lista di enti valida.")

    entities: list[Entity] = []
    seen_codes: set[str] = set()
    discarded = 0
    candidates = raw_records[:limit]
    for record in candidates:
        if not isinstance(record, Mapping):
            discarded += 1
            continue
        codice_ipa = clean_text(record.get("Codice_IPA"))
        denominazione = clean_text(record.get("Denominazione_ente"))
        if not codice_ipa or not denominazione:
            discarded += 1
            continue
        normalized_code = codice_ipa.casefold()
        if normalized_code in seen_codes:
            discarded += 1
            continue
        seen_codes.add(normalized_code)
        entities.append(
            Entity(
                codice_ipa=codice_ipa,
                denominazione=denominazione,
                categoria=clean_text(record.get("Tipologia")),
                livello=None,
                sito_istituzionale=_safe_reported_site(
                    record.get("Sito_istituzionale")
                ),
            )
        )

    total = result.get("total")
    total_available = total if isinstance(total, int) and not isinstance(total, bool) else None
    return ParsedEntityBatch(
        entities=tuple(entities),
        examined=len(candidates),
        discarded=discarded,
        total_available=total_available,
    )


def get_verified_ipa_source(connection: sqlite3.Connection) -> OfficialSource:
    matches = [
        source
        for source in list_sources(connection)
        if "indice delle pubbliche amministrazioni" in source.ente.casefold()
        and source.stato_verifica == "verificato"
        and source.attiva
    ]
    if len(matches) != 1:
        raise IpaImportError("Serve una sola fonte IPA attiva e verificata.")
    source = matches[0]
    if not is_official_ipa_url(source.url_principale):
        raise IpaImportError("La fonte IPA registrata non usa un dominio ufficiale.")
    return source


def fetch_ipa_entities(
    *,
    limit: int = DEFAULT_BATCH_SIZE,
    offset: int = 0,
    request_get: Callable[..., Any] = requests.get,
) -> ParsedEntityBatch:
    validate_batch_limit(limit)
    validate_offset(offset)
    if not is_official_ipa_url(IPA_DATA_API):
        raise IpaImportError("L'endpoint IPA configurato non è ufficiale.")

    last_error: Exception | None = None
    for _attempt in range(MAX_HTTP_ATTEMPTS):
        try:
            response = request_get(
                IPA_DATA_API,
                params={
                    "resource_id": IPA_RESOURCE_ID,
                    "limit": limit,
                    "offset": offset,
                },
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                timeout=REQUEST_TIMEOUT,
            )
            if getattr(response, "status_code", None) in {403, 429}:
                raise IpaImportError(
                    "La fonte IPA ha rifiutato o limitato la richiesta; "
                    "l'importatore non tenta di aggirare il blocco."
                )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, Mapping):
                raise IpaImportError("La risposta IPA non è un oggetto JSON valido.")
            return parse_ipa_payload(payload, limit=limit)
        except IpaImportError:
            raise
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
    raise IpaImportError(
        "La fonte IPA non è raggiungibile tramite HTTP semplice."
    ) from last_error


def _entity_metadata(entity: Entity) -> tuple[object, ...]:
    return (
        entity.denominazione,
        entity.categoria,
        entity.livello,
        entity.sito_istituzionale,
    )


def import_ipa_entities(
    connection: sqlite3.Connection,
    *,
    limit: int = DEFAULT_BATCH_SIZE,
    offset: int = 0,
    dry_run: bool = True,
    request_get: Callable[..., Any] = requests.get,
    detection_date: str | None = None,
) -> IpaImportReport:
    validate_batch_limit(limit)
    validate_offset(offset)
    get_verified_ipa_source(connection)
    batch = fetch_ipa_entities(
        limit=limit,
        offset=offset,
        request_get=request_get,
    )
    if dry_run:
        return IpaImportReport(
            examined=batch.examined,
            discarded=batch.discarded,
            total_available=batch.total_available,
            entities=batch.entities,
        )

    checked_on = detection_date or date.today().isoformat()
    new = updated = already_present = errors = 0
    for entity in batch.entities:
        candidate = Entity(
            codice_ipa=entity.codice_ipa,
            denominazione=entity.denominazione,
            categoria=entity.categoria,
            livello=entity.livello,
            sito_istituzionale=entity.sito_istituzionale,
            last_checked_at=checked_on,
        )
        existing = get_entity_by_ipa_code(connection, candidate.codice_ipa)
        try:
            if existing is None:
                upsert_entity(connection, candidate)
                new += 1
            elif _entity_metadata(existing) == _entity_metadata(candidate):
                upsert_entity(connection, candidate)
                already_present += 1
            else:
                upsert_entity(connection, candidate)
                updated += 1
        except sqlite3.Error:
            errors += 1

    return IpaImportReport(
        examined=batch.examined,
        new=new,
        updated=updated,
        already_present=already_present,
        discarded=batch.discarded,
        errors=errors,
        total_available=batch.total_available,
        entities=batch.entities,
    )


def preview_lines(report: IpaImportReport) -> list[str]:
    lines = ["CODICE IPA | DENOMINAZIONE | CATEGORIA | SITO"]
    lines.extend(
        " | ".join(
            (
                entity.codice_ipa,
                entity.denominazione,
                entity.categoria or "-",
                entity.sito_istituzionale or "-",
            )
        )
        for entity in report.entities
    )
    return lines


def format_report(report: IpaImportReport) -> str:
    total = str(report.total_available) if report.total_available is not None else "-"
    return "\n".join(
        (
            f"Fonte: {report.source}",
            f"Disponibili alla fonte: {total}",
            f"Esaminati: {report.examined}",
            f"Nuovi: {report.new}",
            f"Aggiornati: {report.updated}",
            f"Già presenti: {report.already_present}",
            f"Scartati: {report.discarded}",
            f"Errori: {report.errors}",
        )
    )
