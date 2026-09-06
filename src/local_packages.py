"""Importazione offline, conservativa e tracciata di pacchetti ZIP di soli dati."""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import sqlite3
import stat
import tempfile
import unicodedata
import zipfile
import zlib
from dataclasses import asdict, dataclass, replace
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from src.explanations import _validate_explanation
from src.local_resources import MAX_RESOURCE_BYTES, RESOURCE_ROOT_KEY, create_local_resources_table, list_local_resources, read_resource_text, resolve_resource_root, safe_relative_path
from src.models import DocumentExplanation

MAX_ARCHIVE_BYTES = 20 * 1024 * 1024
MAX_EXPANDED_BYTES = 50 * 1024 * 1024
MAX_METADATA_BYTES = 8 * 1024 * 1024
MAX_FILES = 1000
MAX_RECORDS = 5000
MAX_RATIO = 100
FORMAT_VERSION = 1
CATALOG_SCHEMA_VERSION = 1
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}\Z")
HEX_HASH = re.compile(r"[a-f0-9]{64}\Z")
COLLECTIONS = ("sources", "entities", "documents", "families", "explanations", "provenance")
TABLES = {"sources": "sources", "entities": "entities", "documents": "documents", "families": "document_families", "explanations": "document_explanations", "provenance": "document_provenance"}
FIELDS = {
    "sources": "ente nome_fonte tipo_ente livello ambito url_principale url_modulistica metodo_acquisizione stato_verifica coverage_status data_verifica note attiva".split(),
    "entities": "codice_ipa denominazione categoria livello sito_istituzionale stato_catalogazione last_checked_at".split(),
    "documents": "ente codice titolo_ufficiale categoria descrizione_ufficiale significato_semplice fonte_url download_url detail_url data_pubblicazione versione data_rilevazione stato_verifica parole_chiave source_id".split(),
    "families": "source_id ente nome categoria descrizione_ufficiale keywords identifying_phrases official_url stato_verifica data_verifica created_at updated_at".split(),
    "explanations": "document_id official_summary simple_explanation intended_use possible_users facts_from_source missing_information warnings source_url source_access_date verification_status verified_by verified_at review_notes version created_at updated_at".split(),
    "provenance": "document_id source_id listing_url detail_url download_url acquired_at last_seen_at content_hash acquisition_method source_status".split(),
}
REQUIRED = {
    "sources": "ente nome_fonte tipo_ente livello ambito metodo_acquisizione stato_verifica".split(),
    "entities": "codice_ipa denominazione".split(),
    "documents": "ente titolo_ufficiale data_rilevazione stato_verifica source_key".split(),
    "families": "ente nome stato_verifica created_at updated_at".split(),
    "explanations": "document_key source_url source_access_date verification_status version created_at updated_at facts_from_source".split(),
    "provenance": "document_key source_key acquired_at last_seen_at acquisition_method source_status".split(),
}
ARRAY_FIELDS = {"parole_chiave", "keywords", "identifying_phrases", "possible_users", "facts_from_source", "missing_information", "warnings"}
DATE_FIELDS = {"data_rilevazione", "data_pubblicazione", "data_verifica", "source_access_date"}
TIME_FIELDS = {"created_at", "updated_at", "acquired_at", "last_seen_at", "last_checked_at"}
URL_FIELDS = {"url_principale", "url_modulistica", "sito_istituzionale", "fonte_url", "download_url", "detail_url", "official_url", "source_url", "listing_url"}


class PackageValidationError(ValueError):
    """Pacchetto rifiutato: nessuna modifica al catalogo è stata applicata."""


@dataclass(frozen=True, slots=True)
class PackageImportReport:
    package_id: str
    package_version: str
    catalog_version: str
    sha256: str
    new_records: dict[str, int]
    duplicate_records: dict[str, int]
    resource_count: int
    missing_resources: tuple[str, ...]
    applied: bool = False
    already_imported: bool = False
    demo: bool = False
    format_version: int = FORMAT_VERSION
    catalog_schema_version: int = CATALOG_SCHEMA_VERSION


def create_local_package_tables(connection: sqlite3.Connection) -> None:
    connection.execute("""CREATE TABLE IF NOT EXISTS package_imports (
        id INTEGER PRIMARY KEY AUTOINCREMENT, package_id TEXT NOT NULL,
        package_version TEXT NOT NULL, format_version INTEGER NOT NULL,
        catalog_version TEXT NOT NULL, sha256 TEXT NOT NULL UNIQUE,
        imported_at TEXT NOT NULL, summary_json TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status = 'applied'),
        UNIQUE(package_id, package_version)
    )""")
    connection.execute("""CREATE TABLE IF NOT EXISTS package_import_attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT, attempted_at TEXT NOT NULL,
        package_id TEXT, sha256 TEXT, status TEXT NOT NULL CHECK(status IN ('applied','rejected','already_imported')),
        detail TEXT NOT NULL
    )""")


def catalog_state(connection: sqlite3.Connection) -> dict[str, str | None]:
    exists = connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='package_imports'").fetchone()
    row = connection.execute("SELECT catalog_version, package_id, imported_at FROM package_imports ORDER BY id DESC LIMIT 1").fetchone() if exists else None
    if row:
        return dict(row)
    metadata_exists = connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='catalog_metadata'").fetchone()
    metadata = dict(connection.execute("SELECT key, value FROM catalog_metadata")) if metadata_exists else {}
    return {"catalog_version": metadata.get("seed_version"), "package_id": None, "imported_at": metadata.get("initialized_at")}


def _json_bytes(content: bytes, name: str) -> Any:
    def unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in pairs:
            if key in result:
                raise PackageValidationError(f"Chiave JSON duplicata in {name}: {key}.")
            result[key] = value
        return result
    try:
        return json.loads(content.decode("utf-8"), object_pairs_hook=unique_pairs, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Costante JSON non valida")))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise PackageValidationError(f"JSON non valido: {name}.") from exc


def _text(value: Any, name: str, *, nullable: bool = False, maximum: int = 20_000) -> None:
    if value is None and nullable:
        return
    if not isinstance(value, str) or not value.strip() or len(value) > maximum or "\x00" in value:
        raise PackageValidationError(f"Campo {name} assente o non valido.")


def _identifier(value: Any, name: str) -> None:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise PackageValidationError(f"Identificativo {name} non valido.")


def _exact_keys(value: Any, allowed: set[str], required: set[str], name: str) -> None:
    if not isinstance(value, dict) or set(value) - allowed or required - set(value):
        raise PackageValidationError(f"Schema non valido per {name}: campi sconosciuti o obbligatori mancanti.")


def _read_package(path: str | Path, expected_sha256: str | None) -> tuple[dict[str, Any], dict[str, Any], dict[str, bytes], str]:
    try:
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
        descriptor = os.open(Path(path), flags)
        with os.fdopen(descriptor, "rb") as handle:
            if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                raise PackageValidationError("Il pacchetto deve essere un file regolare locale.")
            raw = handle.read(MAX_ARCHIVE_BYTES + 1)
    except OSError as exc:
        raise PackageValidationError("Pacchetto non accessibile.") from exc
    if len(raw) > MAX_ARCHIVE_BYTES:
        raise PackageValidationError("Archivio oltre il limite di 20 MiB.")
    digest = hashlib.sha256(raw).hexdigest()
    if expected_sha256 is not None and (not HEX_HASH.fullmatch(expected_sha256) or digest != expected_sha256):
        raise PackageValidationError("Il pacchetto è cambiato rispetto all'anteprima: rigenerare la verifica.")
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            if len(entries) > MAX_FILES:
                raise PackageValidationError("Troppi file nel pacchetto.")
            total, names, content = 0, set(), {}
            for entry in entries:
                safe_relative_path(entry.filename)
                name_key = unicodedata.normalize("NFKC", entry.filename).casefold()
                mode = entry.external_attr >> 16
                if name_key in names or entry.is_dir() or (stat.S_IFMT(mode) not in {0, stat.S_IFREG}) or entry.flag_bits & 1:
                    raise PackageValidationError("File duplicato, cifrato, speciale o collegamento simbolico nel pacchetto.")
                if entry.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}:
                    raise PackageValidationError("Compressione ZIP non supportata.")
                names.add(name_key)
                limit = MAX_METADATA_BYTES if entry.filename in {"manifest.json", "records.json"} else MAX_RESOURCE_BYTES
                total += entry.file_size
                if entry.file_size > limit or total > MAX_EXPANDED_BYTES or entry.file_size / max(entry.compress_size, 1) > MAX_RATIO:
                    raise PackageValidationError("Archivio oltre i limiti di espansione o compressione.")
                with archive.open(entry) as member:
                    data = member.read(limit + 1)
                if len(data) != entry.file_size:
                    raise PackageValidationError("Dimensione ZIP incoerente.")
                content[entry.filename] = data
    except (OSError, zipfile.BadZipFile, RuntimeError, NotImplementedError, ValueError, zlib.error) as exc:
        if isinstance(exc, PackageValidationError):
            raise
        raise PackageValidationError(f"Archivio ZIP rifiutato: {exc}") from exc
    if not {"manifest.json", "records.json"} <= set(content):
        raise PackageValidationError("Il pacchetto richiede manifest.json e records.json.")
    manifest = _json_bytes(content["manifest.json"], "manifest")
    manifest_fields = {"format_version", "catalog_schema_version", "package_id", "package_version", "catalog_version", "created_at", "producer", "demo", "files", "resources"}
    _exact_keys(manifest, manifest_fields, manifest_fields, "manifest")
    if type(manifest["format_version"]) is not int or manifest["format_version"] != FORMAT_VERSION or type(manifest["catalog_schema_version"]) is not int or manifest["catalog_schema_version"] != CATALOG_SCHEMA_VERSION:
        raise PackageValidationError("Versione del formato o dello schema del catalogo non supportata.")
    for field in ("package_id", "package_version", "catalog_version"):
        _identifier(manifest[field], field)
    _text(manifest["producer"], "producer", maximum=200)
    _iso_date(manifest["created_at"], "created_at", timestamp=True)
    if type(manifest["demo"]) is not bool or not isinstance(manifest["files"], list) or not isinstance(manifest["resources"], list):
        raise PackageValidationError("Metadati manifest non validi.")
    declared = set()
    for item in manifest["files"]:
        _exact_keys(item, {"path", "size_bytes", "sha256"}, {"path", "size_bytes", "sha256"}, "file")
        name = item["path"]
        safe_relative_path(name)
        if name == "manifest.json" or name in declared or name not in content:
            raise PackageValidationError("File del manifest mancante o dichiarato più volte.")
        declared.add(name)
        if type(item["size_bytes"]) is not int or item["size_bytes"] != len(content[name]) or not isinstance(item["sha256"], str) or hashlib.sha256(content[name]).hexdigest() != item["sha256"]:
            raise PackageValidationError(f"Impronta o dimensione non valida per {name}.")
    if declared != set(content) - {"manifest.json"}:
        raise PackageValidationError("Il pacchetto contiene file non dichiarati nel manifest.")
    records = _json_bytes(content["records.json"], "records")
    _exact_keys(records, set(COLLECTIONS), set(COLLECTIONS), "records")
    _validate_records(records, manifest["demo"])
    _validate_resources(manifest, content, records)
    return manifest, records, content, digest


def _iso_date(value: Any, name: str, *, timestamp: bool = False) -> None:
    _text(value, name, maximum=40)
    try:
        if timestamp:
            datetime.fromisoformat(value)
        else:
            date.fromisoformat(value)
    except ValueError as exc:
        raise PackageValidationError(f"Data ISO non valida: {name}.") from exc


def _validate_records(records: dict[str, Any], demo: bool) -> None:
    if any(not isinstance(records[name], list) for name in COLLECTIONS) or sum(len(records[name]) for name in COLLECTIONS) > MAX_RECORDS:
        raise PackageValidationError("Collezioni non valide o oltre 5000 record.")
    for collection in COLLECTIONS:
        keys = set()
        for record in records[collection]:
            if not isinstance(record, dict):
                raise PackageValidationError("Un record deve essere un oggetto JSON.")
            if "existing_id" in record:
                _exact_keys(record, {"key", "existing_id"}, {"key", "existing_id"}, collection)
                if collection == "provenance" or type(record["existing_id"]) is not int or record["existing_id"] <= 0:
                    raise PackageValidationError("Riferimento a record esistente non valido.")
            else:
                allowed = (set(FIELDS[collection]) - {"source_id", "document_id"}) | {"key"}
                if "source_id" in FIELDS[collection]:
                    allowed.add("source_key")
                if "document_id" in FIELDS[collection]:
                    allowed.add("document_key")
                _exact_keys(record, allowed, set(REQUIRED[collection]) | {"key"}, collection)
                for field, value in record.items():
                    if field == "attiva":
                        if type(value) is not bool:
                            raise PackageValidationError("attiva deve essere un valore booleano.")
                    elif field in ARRAY_FIELDS:
                        if not isinstance(value, list) or len(value) > 100:
                            raise PackageValidationError(f"Elenco non valido: {field}.")
                        for item in value:
                            _text(item, field, maximum=2000)
                    else:
                        _text(value, field, nullable=field not in REQUIRED[collection])
                    if value is not None and field in DATE_FIELDS:
                        _iso_date(value, field)
                    if value is not None and field in TIME_FIELDS:
                        _iso_date(value, field, timestamp=True)
                    if value is not None and field in URL_FIELDS:
                        try:
                            url = urlsplit(value)
                            if url.scheme != "https" or not url.hostname or url.username or url.password or any(char.isspace() for char in value):
                                raise ValueError("URL non valida")
                        except ValueError as exc:
                            raise PackageValidationError(f"Riferimento HTTPS non valido: {field}.") from exc
                status = record.get("verification_status", record.get("stato_verifica"))
                if status is not None and status not in {"bozza", "da_verificare", "rilevato", "demo"}:
                    raise PackageValidationError("Un pacchetto non può attribuire automaticamente uno stato verificato.")
                if status == "demo" and not demo:
                    raise PackageValidationError("Record demo in un pacchetto non dichiarato demo.")
                if demo and collection in {"sources", "families"} and status != "demo":
                    raise PackageValidationError("Fonti e famiglie sintetiche devono essere marcate demo.")
                if demo and collection == "entities":
                    raise PackageValidationError("Gli enti IPA dimostrativi non possono entrare nell'inventario reale.")
                if collection == "documents" and ((demo and status != "demo") or record.get("significato_semplice") is not None):
                    raise PackageValidationError("Documenti demo espliciti; spiegazioni separate in explanations.")
                if collection == "explanations":
                    if status not in {"bozza", "da_verificare"} or record.get("verified_by") is not None or record.get("verified_at") is not None or not record["facts_from_source"]:
                        raise PackageValidationError("La spiegazione deve contenere fatti e richiedere revisione umana.")
                if collection == "provenance" and record.get("content_hash") is not None and not HEX_HASH.fullmatch(record["content_hash"]):
                    raise PackageValidationError("Impronta della provenienza non valida.")
            _identifier(record["key"], "key")
            if record["key"] in keys:
                raise PackageValidationError(f"Chiave duplicata in {collection}.")
            keys.add(record["key"])


def _validate_resources(manifest: dict[str, Any], content: dict[str, bytes], records: dict[str, Any]) -> None:
    fields = {"path", "document_key", "source_key", "title", "media_type", "provenance", "acquired_at", "version", "reuse_conditions", "verification_status"}
    resource_paths = set()
    for resource in manifest["resources"]:
        _exact_keys(resource, fields, fields, "risorsa")
        for field, value in resource.items():
            _text(value, field, nullable=field == "version")
        name = resource["path"]
        safe_relative_path(f"{'0' * 64}/{name}")
        if not name.startswith("resources/") or not name.endswith(".txt") or name not in content or name in resource_paths:
            raise PackageValidationError("La risorsa richiede un file resources/*.txt unico e presente.")
        if resource["media_type"] != "text/plain" or resource["verification_status"] != ("demo" if manifest["demo"] else "da_verificare"):
            raise PackageValidationError("Formato o stato della risorsa non valido.")
        _iso_date(resource["acquired_at"], "acquired_at", timestamp=True)
        try:
            decoded = content[name].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise PackageValidationError("Le risorse devono essere testo UTF-8.") from exc
        if "\x00" in decoded:
            raise PackageValidationError("Risorsa non testuale.")
        resource_paths.add(name)
    if resource_paths != set(content) - {"manifest.json", "records.json"}:
        raise PackageValidationError("Tutti i materiali devono essere risorse testuali dichiarate.")


def _canonical(value: Any) -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFKC", value).strip().casefold()
    return value


def _identity(collection: str, values: Any) -> tuple[Any, ...]:
    identities = {
        "sources": ("ente", "nome_fonte"), "entities": ("codice_ipa",),
        "documents": ("ente", "versione"), "families": ("source_id", "ente", "nome"),
        "explanations": ("document_id", "version"), "provenance": ("document_id",),
    }[collection]
    return tuple(_canonical(values[field]) for field in identities)


def _matches(collection: str, values: dict[str, Any], index: dict[tuple[Any, ...], list[Any]]) -> list[Any]:
    matches = index.get(_identity(collection, values), [])
    if collection == "documents":
        matches = [row for row in matches if _canonical(row["titolo_ufficiale"]) == _canonical(values["titolo_ufficiale"]) or (values["codice"] is not None and _canonical(row["codice"]) == _canonical(values["codice"]))]
    return matches


def _prepare_values(collection: str, record: dict[str, Any], ids: dict[str, dict[str, int]]) -> dict[str, Any]:
    values = {field: record.get(field) for field in FIELDS[collection]}
    for field in ARRAY_FIELDS & set(values):
        values[field] = json.dumps(record.get(field, []), ensure_ascii=False)
    for field, target in (("source_id", "sources"), ("document_id", "documents")):
        if field in values:
            key = record.get(field.replace("_id", "_key"))
            if key is not None and key not in ids[target]:
                raise PackageValidationError(f"Relazione inesistente: {target}/{key}.")
            values[field] = ids[target].get(key)
    if collection == "sources":
        values.update(attiva=int(record.get("attiva", False)), coverage_status=record.get("coverage_status", "da_valutare"))
    if collection == "entities":
        values["stato_catalogazione"] = record.get("stato_catalogazione", "non_analizzato")
    return values


def _insert_records(connection: sqlite3.Connection, records: dict[str, Any], manifest: dict[str, Any], content: dict[str, bytes], digest: str, storage_key: str) -> PackageImportReport:
    ids: dict[str, dict[str, int]] = {name: {} for name in COLLECTIONS}
    counts, duplicates = {name: 0 for name in COLLECTIONS}, {name: 0 for name in COLLECTIONS}
    imported_documents = set()
    for collection in COLLECTIONS:
        table = TABLES[collection]
        index: dict[tuple[Any, ...], list[Any]] = {}
        for row in connection.execute(f"SELECT * FROM {table}"):
            index.setdefault(_identity(collection, row), []).append(row)
        for record in records[collection]:
            if "existing_id" in record:
                row = connection.execute(f"SELECT id FROM {table} WHERE id = ?", (record["existing_id"],)).fetchone()
                if row is None:
                    raise PackageValidationError(f"Record esistente non trovato: {collection}/{record['existing_id']}.")
                ids[collection][record["key"]] = row["id"]
                duplicates[collection] += 1
                continue
            values = _prepare_values(collection, record, ids)
            if collection == "explanations":
                validation_values = {field: tuple(json.loads(value)) if field in ARRAY_FIELDS else value for field, value in values.items()}
                _validate_explanation(DocumentExplanation(**validation_values))
            if collection in {"documents", "families"} and values["source_id"] is not None:
                source = connection.execute("SELECT ente, stato_verifica FROM sources WHERE id = ?", (values["source_id"],)).fetchone()
                if _canonical(source["ente"]) != _canonical(values["ente"]):
                    raise PackageValidationError("L'ente del record non coincide con la fonte associata.")
                if (source["stato_verifica"] == "demo") != (values["stato_verifica"] == "demo"):
                    raise PackageValidationError("Documenti e famiglie demo richiedono una fonte demo coerente.")
            if collection == "provenance":
                document = connection.execute("SELECT source_id FROM documents WHERE id = ?", (values["document_id"],)).fetchone()
                if document["source_id"] != values["source_id"]:
                    raise PackageValidationError("Fonte della provenienza incoerente con il documento.")
            matches = _matches(collection, values, index)
            if len(matches) > 1:
                raise PackageValidationError(f"Identità ambigua nel catalogo: {collection}/{record['key']}.")
            if matches:
                row = matches[0]
                equal = all((json.loads(row[field] or "[]") == json.loads(value)) if field in ARRAY_FIELDS else row[field] == value for field, value in values.items())
                if not equal:
                    raise PackageValidationError(f"Conflitto con record esistente: {collection}/{record['key']}. Nessuna sostituzione automatica consentita.")
                ids[collection][record["key"]] = row["id"]
                duplicates[collection] += 1
            else:
                columns = ", ".join(values)
                cursor = connection.execute(f"INSERT INTO {table} ({columns}) VALUES ({', '.join('?' for _ in values)})", tuple(values.values()))
                ids[collection][record["key"]] = int(cursor.lastrowid)
                index.setdefault(_identity(collection, values), []).append({**values, "id": int(cursor.lastrowid)})
                counts[collection] += 1
                if collection == "documents":
                    imported_documents.add(int(cursor.lastrowid))
    for document_id in imported_documents:
        if connection.execute("SELECT 1 FROM document_provenance WHERE document_id = ?", (document_id,)).fetchone() is None:
            raise PackageValidationError("Ogni nuovo documento richiede una provenienza esplicita nello stesso pacchetto.")
    resource_count = 0
    for resource in manifest["resources"]:
        document_id = ids["documents"].get(resource["document_key"])
        source_id = ids["sources"].get(resource["source_key"])
        if document_id is None or source_id is None:
            raise PackageValidationError("Relazione della risorsa inesistente.")
        document = connection.execute("SELECT source_id, stato_verifica FROM documents WHERE id = ?", (document_id,)).fetchone()
        if document["source_id"] != source_id or (document["stato_verifica"] == "demo") != manifest["demo"]:
            raise PackageValidationError("Risorsa incompatibile con fonte o natura del documento.")
        data = content[resource["path"]]
        values = dict(document_id=document_id, source_id=source_id, title=resource["title"], relative_path=f"{storage_key}/{resource['path']}", media_type="text/plain", size_bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), provenance=resource["provenance"], acquired_at=resource["acquired_at"], version=resource["version"], reuse_conditions=resource["reuse_conditions"], verification_status=resource["verification_status"], package_id=manifest["package_id"])
        existing = connection.execute("SELECT * FROM local_resources WHERE document_id = ? AND sha256 = ?", (document_id, values["sha256"])).fetchone()
        if existing:
            if any(existing[field] != value for field, value in values.items() if field not in {"relative_path", "package_id"}):
                raise PackageValidationError("Conflitto nei metadati di una risorsa già presente.")
            continue
        connection.execute(f"INSERT INTO local_resources ({', '.join(values)}) VALUES ({', '.join('?' for _ in values)})", tuple(values.values()))
        resource_count += 1
    missing = tuple(row["titolo_ufficiale"] for row in connection.execute("SELECT titolo_ufficiale FROM documents WHERE id IN (SELECT value FROM json_each(?)) AND NOT EXISTS (SELECT 1 FROM local_resources WHERE local_resources.document_id = documents.id) ORDER BY id", (json.dumps(list(ids["documents"].values())),)))
    if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
        raise PackageValidationError("Violazione delle relazioni nel catalogo.")
    return PackageImportReport(manifest["package_id"], manifest["package_version"], manifest["catalog_version"], digest, counts, duplicates, resource_count, missing, demo=manifest["demo"])


def _existing_import(connection: sqlite3.Connection, manifest: dict[str, Any], digest: str) -> PackageImportReport | None:
    row = connection.execute("SELECT * FROM package_imports WHERE (package_id = ? AND package_version = ?) OR sha256 = ?", (manifest["package_id"], manifest["package_version"], digest)).fetchone()
    if not row:
        return None
    if row["sha256"] != digest:
        raise PackageValidationError("Questa versione del pacchetto esiste già con byte differenti.")
    data = json.loads(row["summary_json"])
    data["missing_resources"] = tuple(data["missing_resources"])
    report = PackageImportReport(**data)
    return replace(report, new_records={name: 0 for name in COLLECTIONS}, duplicate_records={name: report.new_records[name] + report.duplicate_records[name] for name in COLLECTIONS}, resource_count=0, already_imported=True, applied=False)


def _record_attempt(connection: sqlite3.Connection, status: str, manifest: dict[str, Any] | None, digest: str | None, detail: str) -> None:
    connection.execute("INSERT INTO package_import_attempts (attempted_at, package_id, sha256, status, detail) VALUES (?, ?, ?, ?, ?)", (datetime.now(UTC).isoformat(), manifest.get("package_id") if manifest else None, digest, status, detail[:2000]))


def _resource_root(root: str | Path) -> Path:
    root = Path(root).absolute()
    if any(part.is_symlink() for part in (root, *root.parents)):
        raise PackageValidationError("La cartella delle risorse non può attraversare collegamenti simbolici.")
    root.mkdir(parents=True, exist_ok=True)
    return root


def _database_fingerprint(connection: sqlite3.Connection) -> str:
    db_path = next(row[2] for row in connection.execute("PRAGMA database_list") if row[1] == "main")
    return hashlib.sha256((db_path or ":memory:").encode()).hexdigest()


def _storage_key(connection: sqlite3.Connection, digest: str) -> str:
    """Namespace deterministico per percorso database, senza allungare i percorsi."""
    return hashlib.sha256(f"{_database_fingerprint(connection)}:{digest}".encode("ascii")).hexdigest()


def _remember_resource_root(connection: sqlite3.Connection, root: Path) -> None:
    resources = list_local_resources(connection)
    if not resources:
        return
    exists = connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='catalog_metadata'").fetchone()
    stored = connection.execute("SELECT value FROM catalog_metadata WHERE key = ?", (RESOURCE_ROOT_KEY,)).fetchone() if exists else None
    if stored is None:
        # Consente l'adozione esplicita della radice legacy solo se tutti i byte
        # già registrati sono disponibili: nessun file viene spostato o riscritto.
        for resource in resources:
            read_resource_text(replace(resource, verification_status="da_verificare"), root)
        connection.execute("CREATE TABLE IF NOT EXISTS catalog_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        connection.execute("INSERT INTO catalog_metadata (key, value) VALUES (?, ?)", (RESOURCE_ROOT_KEY, str(root)))


def _recover_orphans(connection: sqlite3.Connection, root: Path) -> None:
    """Chiamare soltanto sotto BEGIN IMMEDIATE; recupera un'interruzione prima del COMMIT."""
    imported = {row[0] for row in connection.execute("SELECT sha256 FROM package_imports")}
    known = imported | {_storage_key(connection, digest) for digest in imported}
    database_fingerprint = _database_fingerprint(connection)
    for directory in root.iterdir():
        if directory.is_symlink() or not directory.is_dir():
            continue
        marker = directory / ".burocrazia-package"
        if marker.is_symlink() or not marker.is_file() or marker.stat().st_size > 1024:
            continue
        try:
            journal = json.loads(marker.read_text(encoding="ascii"))
        except (OSError, ValueError):
            continue
        if not isinstance(journal, dict) or journal.get("database") != database_fingerprint:
            continue
        if (HEX_HASH.fullmatch(directory.name) and directory.name not in known) or directory.name.startswith(".burocrazia-stage-"):
            shutil.rmtree(directory)


def import_local_package(connection: sqlite3.Connection, path: str | Path, resource_root: str | Path | None = None, *, dry_run: bool = True, expected_sha256: str | None = None) -> PackageImportReport:
    """Anteprima senza scritture; commit solo confermando l'hash ZIP dell'anteprima.

    La connessione deve avere schema già inizializzato e nessuna transazione aperta.
    Un commit rifiutato registra soltanto il tentativo, senza cambiare dati/catalogo.
    """
    if connection.in_transaction:
        raise PackageValidationError("Terminare la transazione aperta prima di importare un pacchetto.")
    if not dry_run and expected_sha256 is None:
        raise PackageValidationError("Prima eseguire l'anteprima e confermare il suo hash con expected_sha256.")
    manifest, digest, staging, published = None, None, None, None
    record_rejection = not dry_run
    try:
        manifest, records, content, digest = _read_package(path, expected_sha256)
        if not dry_run and manifest["resources"] and not next(row[2] for row in connection.execute("PRAGMA database_list") if row[1] == "main"):
            record_rejection = False
            raise PackageValidationError("L'importazione dei materiali richiede un database SQLite su file; per un database in memoria è disponibile soltanto l'anteprima.")
        root = resolve_resource_root(connection, resource_root)
        storage_key = _storage_key(connection, digest)
        if dry_run:
            preview = sqlite3.connect(":memory:")
            preview.row_factory = sqlite3.Row
            try:
                connection.backup(preview)
                preview.execute("PRAGMA foreign_keys = ON")
                create_local_package_tables(preview)
                create_local_resources_table(preview)
                previous = _existing_import(preview, manifest, digest)
                return previous or _insert_records(preview, records, manifest, content, digest, storage_key)
            finally:
                preview.close()
        connection.execute("BEGIN IMMEDIATE")
        create_local_package_tables(connection)
        create_local_resources_table(connection)
        root = resolve_resource_root(connection, resource_root)
        previous = _existing_import(connection, manifest, digest)
        if previous:
            _remember_resource_root(connection, root)
            _record_attempt(connection, "already_imported", manifest, digest, "Nessuna modifica: pacchetto già applicato.")
            connection.commit()
            return previous
        report = _insert_records(connection, records, manifest, content, digest, storage_key)
        root = _resource_root(root)
        _recover_orphans(connection, root)
        if manifest["resources"]:
            destination = root / storage_key
            if destination.exists():
                raise PackageValidationError("Cartella del pacchetto già presente e non recuperabile automaticamente.")
            staging = Path(tempfile.mkdtemp(prefix=".burocrazia-stage-", dir=root))
            (staging / ".burocrazia-package").write_text(json.dumps({"sha256": digest, "database": _database_fingerprint(connection)}), encoding="ascii")
            for resource in manifest["resources"]:
                target = staging / resource["path"]
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as handle:
                    handle.write(content[resource["path"]])
                    handle.flush()
                    os.fsync(handle.fileno())
            os.replace(staging, destination)
            staging, published = None, destination
        _remember_resource_root(connection, root)
        applied = replace(report, applied=True)
        connection.execute("INSERT INTO package_imports (package_id, package_version, format_version, catalog_version, sha256, imported_at, summary_json, status) VALUES (?, ?, ?, ?, ?, ?, ?, 'applied')", (manifest["package_id"], manifest["package_version"], FORMAT_VERSION, manifest["catalog_version"], digest, datetime.now(UTC).isoformat(), json.dumps(asdict(applied), ensure_ascii=False)))
        _record_attempt(connection, "applied", manifest, digest, json.dumps(asdict(applied), ensure_ascii=False))
        connection.commit()
        return applied
    except Exception as exc:
        if record_rejection:
            connection.rollback()
            for directory in (staging, published):
                if directory is not None:
                    shutil.rmtree(directory, ignore_errors=True)
            create_local_package_tables(connection)
            _record_attempt(connection, "rejected", manifest, digest, str(exc))
            connection.commit()
        if isinstance(exc, PackageValidationError):
            raise
        if isinstance(exc, (OSError, sqlite3.Error, ValueError, TypeError, KeyError)):
            raise PackageValidationError(f"Importazione rifiutata: {exc}") from exc
        raise
