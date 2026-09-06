"""Restore the complete public catalog on first start; never replace user data."""
from __future__ import annotations
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from datetime import UTC, datetime

from src.database import DEFAULT_DB_PATH, PROJECT_ROOT, initialize_database


def prepare_database(db_path: str | Path = DEFAULT_DB_PATH) -> Path:
    path = Path(db_path)
    if not path.exists():
        seed = PROJECT_ROOT / "data/catalog_seed.sqlite3"
        manifest = json.loads((PROJECT_ROOT / "data/catalog_manifest.json").read_text(encoding="utf-8"))
        if hashlib.sha256(seed.read_bytes()).hexdigest() != manifest["sha256"]:
            raise ValueError("Il catalogo iniziale non corrisponde alla sua impronta: ripristina il pacchetto originale.")
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".catalog-", suffix=".sqlite3", dir=path.parent)
        os.close(fd)
        try:
            with closing(sqlite3.connect(seed.resolve().as_uri() + "?mode=ro", uri=True)) as source:
                with closing(sqlite3.connect(temporary)) as target, target:
                    source.backup(target)
                    with closing(target.cursor()) as cursor:
                        if cursor.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                            raise ValueError("Catalogo iniziale non integro.")
                        cursor.execute("CREATE TABLE IF NOT EXISTS catalog_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
                        cursor.executemany("INSERT OR REPLACE INTO catalog_metadata VALUES (?, ?)", [
                            ("seed_version", manifest["catalog_version"]), ("seed_sha256", manifest["sha256"]),
                            ("initialized_at", datetime.now(UTC).isoformat()),
                        ])
            # Atomic hard-link publication prevents partial files and overwrite races.
            try:
                os.link(temporary, path)
            except FileExistsError:
                pass
        finally:
            Path(temporary).unlink(missing_ok=True)
    initialize_database(path, seed_demo=True)
    return path
