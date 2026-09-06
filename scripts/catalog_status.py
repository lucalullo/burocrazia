from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.catalog_metrics import format_catalog_status, get_catalog_metrics
from src.bootstrap import prepare_database
from src.database import DEFAULT_DB_PATH, connect_database, initialize_database


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    prepare_database(DEFAULT_DB_PATH)
    with connect_database(DEFAULT_DB_PATH) as connection:
        metrics = get_catalog_metrics(connection)
    print(format_catalog_status(metrics))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
