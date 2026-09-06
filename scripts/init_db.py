from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.bootstrap import prepare_database
from src.database import DEFAULT_DB_PATH, connect_database, initialize_database


def main() -> None:
    prepare_database(DEFAULT_DB_PATH)
    with connect_database(DEFAULT_DB_PATH) as connection:
        document_count = int(
            connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        )
        demo_count = int(
            connection.execute(
                "SELECT COUNT(*) FROM documents WHERE stato_verifica = 'demo'"
            ).fetchone()[0]
        )
        source_count = int(
            connection.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
        )
    print(
        f"Database pronto con {document_count} documenti, di cui {demo_count} demo, e "
        f"{source_count} fonti: {DEFAULT_DB_PATH}"
    )


if __name__ == "__main__":
    main()
