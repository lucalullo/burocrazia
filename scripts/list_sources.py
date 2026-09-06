from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.bootstrap import prepare_database
from src.database import DEFAULT_DB_PATH, connect_database, initialize_database
from src.sources import list_sources


def main() -> None:
    prepare_database(DEFAULT_DB_PATH)
    with connect_database(DEFAULT_DB_PATH) as connection:
        sources = list_sources(connection)

    if not sources:
        print("Nessuna fonte presente nel registro.")
        return

    for source in sources:
        print(f"ENTE: {source.ente}")
        print(f"STATO: {source.stato_verifica}")
        print(f"URL PRINCIPALE: {source.url_principale or 'Non disponibile'}")
        print(f"URL MODULISTICA: {source.url_modulistica or 'Non disponibile'}")
        print(f"METODO: {source.metodo_acquisizione}")
        print()


if __name__ == "__main__":
    main()
