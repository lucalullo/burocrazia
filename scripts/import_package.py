"""Anteprima e applicazione esplicita di un pacchetto locale già presente."""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import asdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database import DEFAULT_DB_PATH, connect_database, create_schema
from src.local_packages import PackageValidationError, import_local_package


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Valida un pacchetto BurOCRazia locale. L'anteprima è la modalità predefinita.")
    parser.add_argument("package", type=Path, help="File ZIP locale già disponibile sul dispositivo")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--resource-root", type=Path, help="Cartella base dei materiali; altrimenti usa la radice registrata nel database o quella predefinita")
    parser.add_argument("--commit", action="store_true", help="Applica il pacchetto verificato; richiede --expected-sha256")
    parser.add_argument("--expected-sha256", help="Hash SHA-256 esatto stampato dall'anteprima")
    args = parser.parse_args(argv)
    if args.commit and not args.expected_sha256:
        parser.error("--commit richiede --expected-sha256 ottenuto dall'anteprima")
    if not args.db.is_file():
        parser.error("Database assente: inizializzarlo prima con python scripts/init_db.py")
    try:
        with connect_database(args.db) as connection:
            if args.commit:
                create_schema(connection)
            report = import_local_package(connection, args.package, args.resource_root, dry_run=not args.commit, expected_sha256=args.expected_sha256)
        print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
        if report.demo:
            print("PACCHETTO DIMOSTRATIVO: contenuti sintetici, nessuna fonte ufficiale riprodotta.")
        if not args.commit:
            print("Anteprima: nessuna scrittura. Per applicare, ripetere con --commit --expected-sha256 " + report.sha256)
        return 0
    except (PackageValidationError, OSError, sqlite3.Error) as exc:
        print(f"Importazione rifiutata: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
