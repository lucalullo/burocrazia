"""Read-only integrity and coverage verification of the installed catalog."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.database import DEFAULT_DB_PATH


def verify(path: Path) -> dict:
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as db:
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        counts = {table: db.execute(f"SELECT count(*) FROM {table}").fetchone()[0] for table in sorted(tables) if not table.startswith("sqlite_")}
        return {
            "integrity": db.execute("PRAGMA integrity_check").fetchone()[0],
            "foreign_key_violations": [list(row) for row in db.execute("PRAGMA foreign_key_check")],
            "tables": counts,
            "real_documents": db.execute("SELECT count(*) FROM documents WHERE stato_verifica <> 'demo'").fetchone()[0],
            "active_real_documents": db.execute("SELECT count(*) FROM documents WHERE stato_verifica NOT IN ('demo','rifiutato')").fetchone()[0],
            "rejected_real_documents": db.execute("SELECT count(*) FROM documents WHERE stato_verifica = 'rifiutato'").fetchone()[0],
            "demo_documents": db.execute("SELECT count(*) FROM documents WHERE stato_verifica = 'demo'").fetchone()[0],
            "real_documents_without_provenance": db.execute("SELECT count(*) FROM documents d WHERE stato_verifica <> 'demo' AND NOT EXISTS (SELECT 1 FROM document_provenance p WHERE p.document_id=d.id)").fetchone()[0],
            "unverified_explanations": db.execute("SELECT count(*) FROM document_explanations WHERE verification_status <> 'verificato'").fetchone()[0],
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    args = parser.parse_args()
    try:
        result = verify(args.db)
    except (OSError, sqlite3.Error) as exc:
        print(f"Catalogo non leggibile: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(result["integrity"] != "ok" or bool(result["foreign_key_violations"]) or result["real_documents_without_provenance"] != 0)


if __name__ == "__main__":
    raise SystemExit(main())
