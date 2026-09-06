from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.bootstrap import prepare_database
from src.database import DEFAULT_DB_PATH, connect_database, initialize_database
from src.explanations import EXPLANATION_STATUSES
from src.review_export import export_review_report


DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "exports" / "review_report.csv"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Esporta un report CSV locale delle revisioni delle spiegazioni."
    )
    parser.add_argument(
        "--status",
        choices=sorted(EXPLANATION_STATUSES),
        help="Esporta soltanto le spiegazioni nello stato indicato.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args(argv)
    try:
        initialize_database(DEFAULT_DB_PATH, seed_demo=False)
        with connect_database(DEFAULT_DB_PATH) as connection:
            exported = export_review_report(
                connection,
                DEFAULT_OUTPUT_PATH,
                verification_status=args.status,
            )
    except (OSError, sqlite3.Error, ValueError) as exc:
        print(f"Errore esportazione revisioni: {exc}", file=sys.stderr)
        return 1
    print(f"Report revisioni esportato: {exported} righe -> {DEFAULT_OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
