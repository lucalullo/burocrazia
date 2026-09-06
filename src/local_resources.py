"""Risorse consultabili esclusivamente come testo, senza rendering HTML o link."""
from __future__ import annotations

import hashlib
import os
import sqlite3
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

DEFAULT_RESOURCE_ROOT = Path(__file__).resolve().parents[1] / "data" / "local_resources"
MAX_RESOURCE_BYTES = 2 * 1024 * 1024
RESOURCE_ROOT_KEY = "local_resource_root"


@dataclass(frozen=True, slots=True)
class LocalResource:
    id: int
    document_id: int
    source_id: int
    title: str
    relative_path: str
    media_type: str
    size_bytes: int
    sha256: str
    provenance: str
    acquired_at: str
    version: str | None
    reuse_conditions: str
    verification_status: str
    package_id: str


def create_local_resources_table(connection: sqlite3.Connection) -> None:
    connection.execute("""CREATE TABLE IF NOT EXISTS local_resources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER NOT NULL REFERENCES documents(id),
        source_id INTEGER NOT NULL REFERENCES sources(id),
        title TEXT NOT NULL, relative_path TEXT NOT NULL UNIQUE,
        media_type TEXT NOT NULL CHECK(media_type = 'text/plain'),
        size_bytes INTEGER NOT NULL CHECK(size_bytes >= 0 AND size_bytes <= 2097152),
        sha256 TEXT NOT NULL, provenance TEXT NOT NULL, acquired_at TEXT NOT NULL,
        version TEXT, reuse_conditions TEXT NOT NULL,
        verification_status TEXT NOT NULL CHECK(verification_status IN ('demo', 'da_verificare', 'verificato', 'rifiutato')),
        package_id TEXT NOT NULL,
        UNIQUE(document_id, sha256)
    )""")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_resources_document ON local_resources(document_id)")


def list_local_resources(connection: sqlite3.Connection, document_id: int | None = None) -> list[LocalResource]:
    present = connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='local_resources'").fetchone()
    if not present:
        return []
    sql, parameters = "SELECT * FROM local_resources", ()
    if document_id is not None:
        sql, parameters = sql + " WHERE document_id = ?", (document_id,)
    rows = connection.execute(sql + " ORDER BY id", parameters).fetchall()
    return [LocalResource(**dict(row)) for row in rows]


def safe_relative_path(value: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value or ":" in value:
        raise ValueError("Percorso locale non valido.")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in value.split("/")):
        raise ValueError("Il percorso deve essere relativo e privo di attraversamenti.")
    reserved = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
    if any(part.startswith(".") or len(part) > 120 or part.endswith((".", " ")) or part.split(".")[0].upper() in reserved or any(ord(char) < 32 or char in '<>"|?*' for char in part) for part in path.parts) or len(value) > 240:
        raise ValueError("Percorso locale non consentito.")
    return path


def resolve_resource_root(connection: sqlite3.Connection, root: str | Path | None = None) -> Path:
    """Risoluzione condivisa e senza scritture; una radice registrata non viene cambiata."""
    exists = connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='catalog_metadata'").fetchone()
    stored = connection.execute("SELECT value FROM catalog_metadata WHERE key = ?", (RESOURCE_ROOT_KEY,)).fetchone() if exists else None
    configured = Path(stored[0]).absolute() if stored else None
    requested = Path(root).absolute() if root is not None else None
    if configured is not None and requested is not None and configured != requested:
        raise ValueError("Il database usa già un'altra cartella dei materiali. Conservare la radice registrata; nessuno spostamento automatico è consentito.")
    selected = configured if configured is not None else requested if requested is not None else DEFAULT_RESOURCE_ROOT.absolute()
    if any(part.is_symlink() for part in (selected, *selected.parents)):
        raise ValueError("La cartella delle risorse non può attraversare collegamenti simbolici.")
    return selected


def read_resource_text(resource: LocalResource, root: str | Path | None = None, *, connection: sqlite3.Connection | None = None) -> str:
    """Restituisce stringhe inerti: la UI deve usare st.text, mai markdown/HTML."""
    relative = safe_relative_path(resource.relative_path)
    if resource.verification_status == "rifiutato":
        raise ValueError("Risorsa ritirata dalla consultazione dopo revisione.")
    base = resolve_resource_root(connection, root) if connection is not None else Path(root if root is not None else DEFAULT_RESOURCE_ROOT).absolute()
    if any(part.is_symlink() for part in (base, *base.parents)):
        raise ValueError("La cartella delle risorse non può essere un collegamento simbolico.")
    current = base
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("Risorsa con collegamento simbolico non consentita.")
    try:
        current.resolve().relative_to(base.resolve())
    except ValueError as exc:
        raise ValueError("Risorsa fuori dalla cartella autorizzata.") from exc
    if resource.media_type != "text/plain" or not 0 <= resource.size_bytes <= MAX_RESOURCE_BYTES:
        raise ValueError("Formato o dimensione della risorsa non consentiti.")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
    try:
        descriptor = os.open(current, flags)
        with os.fdopen(descriptor, "rb") as handle:
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size != resource.size_bytes:
                raise ValueError("La dimensione della risorsa non coincide con il registro.")
            content = handle.read(MAX_RESOURCE_BYTES + 1)
    except OSError as exc:
        raise ValueError("Risorsa locale assente o non accessibile.") from exc
    if len(content) != resource.size_bytes or hashlib.sha256(content).hexdigest() != resource.sha256:
        raise ValueError("L'impronta della risorsa non coincide con il registro.")
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("La risorsa deve contenere testo UTF-8.") from exc
    if "\x00" in text:
        raise ValueError("La risorsa contiene byte non testuali.")
    return text


def resource_status(connection: sqlite3.Connection, document_id: int) -> str:
    resources = list_local_resources(connection, document_id)
    if not resources:
        return "Solo riferimento: materiale ufficiale locale non disponibile."
    if all(resource.verification_status == "demo" for resource in resources):
        return "Materiale dimostrativo locale; nessuna copia ufficiale inclusa."
    if any(resource.verification_status == "verificato" for resource in resources):
        return "Materiale locale revisionato disponibile; consultare lo storico della revisione."
    if all(resource.verification_status == "rifiutato" for resource in resources):
        return "Materiale locale ritirato dalla consultazione dopo revisione."
    return "Materiale locale da verificare: l'impronta non certifica l'autenticità istituzionale."
