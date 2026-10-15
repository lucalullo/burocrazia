from __future__ import annotations

from contextlib import closing
import json
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

from src.explanations import create_explanations_table, create_review_events_table
from src.entities import create_entities_table
from src.families import create_families_table, seed_initial_families
from src.models import AdministrativeDocument
from src.provenance import backfill_document_provenance, create_provenance_table
from src.sources import create_sources_table, seed_initial_sources


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = Path(os.environ.get("BUROCRAZIA_DB_PATH", PROJECT_ROOT / "data" / "burocrazia.db"))
SCHEMA_VERSION = 610

DOCUMENTS_TABLE_TEMPLATE = """
CREATE TABLE IF NOT EXISTS {table_name} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ente TEXT NOT NULL,
    codice TEXT,
    titolo_ufficiale TEXT NOT NULL,
    categoria TEXT,
    descrizione_ufficiale TEXT,
    significato_semplice TEXT,
    fonte_url TEXT,
    download_url TEXT,
    detail_url TEXT,
    data_pubblicazione TEXT,
    versione TEXT,
    data_rilevazione TEXT NOT NULL,
    stato_verifica TEXT NOT NULL,
    parole_chiave TEXT NOT NULL DEFAULT '[]',
    source_id INTEGER REFERENCES sources(id)
);
"""

DOCUMENT_COLUMNS = (
    "id",
    "ente",
    "codice",
    "titolo_ufficiale",
    "categoria",
    "descrizione_ufficiale",
    "significato_semplice",
    "fonte_url",
    "download_url",
    "detail_url",
    "data_pubblicazione",
    "versione",
    "data_rilevazione",
    "stato_verifica",
    "parole_chiave",
    "source_id",
)

NULLABLE_METADATA_COLUMNS = {
    "categoria",
    "descrizione_ufficiale",
    "significato_semplice",
    "versione",
}


DEMO_DOCUMENTS = (
    AdministrativeDocument(
        ente="INPS",
        codice="INPS-DEMO-01",
        titolo_ufficiale="Domanda dimostrativa di pensione",
        categoria="previdenza",
        descrizione_ufficiale="Descrizione dimostrativa di una domanda relativa a un trattamento pensionistico.",
        significato_semplice="Esempio di documento usato per chiedere l'avvio della valutazione di una pensione.",
        fonte_url=None,
        download_url=None,
        versione="demo-0.1",
        data_rilevazione="2026-08-04",
        stato_verifica="demo",
        parole_chiave=("pensione", "contribuzione", "trattamento previdenziale", "domanda pensionistica"),
    ),
    AdministrativeDocument(
        ente="Agenzia delle Entrate",
        codice="ADE-DEMO-01",
        titolo_ufficiale="Comunicazione dimostrativa di irregolarità fiscale",
        categoria="fiscale",
        descrizione_ufficiale="Descrizione dimostrativa di una comunicazione relativa a possibili irregolarità fiscali.",
        significato_semplice="Esempio di avviso che segnala al cittadino dati fiscali da controllare.",
        fonte_url=None,
        download_url=None,
        versione="demo-0.1",
        data_rilevazione="2026-08-04",
        stato_verifica="demo",
        parole_chiave=("irregolarità fiscale", "dichiarazione", "imposta", "controllo fiscale"),
    ),
    AdministrativeDocument(
        ente="INAIL",
        codice="INAIL-DEMO-01",
        titolo_ufficiale="Denuncia dimostrativa di infortunio sul lavoro",
        categoria="lavoro",
        descrizione_ufficiale="Descrizione dimostrativa di una comunicazione riguardante un infortunio lavorativo.",
        significato_semplice="Esempio di documento con cui viene comunicato un infortunio avvenuto durante il lavoro.",
        fonte_url=None,
        download_url=None,
        versione="demo-0.1",
        data_rilevazione="2026-08-04",
        stato_verifica="demo",
        parole_chiave=("infortunio", "lavoratore", "datore di lavoro", "evento lesivo"),
    ),
    AdministrativeDocument(
        ente="Comune",
        codice="COM-DEMO-01",
        titolo_ufficiale="Richiesta dimostrativa di cambio di residenza",
        categoria="anagrafe",
        descrizione_ufficiale="Descrizione dimostrativa di una richiesta di aggiornamento della residenza anagrafica.",
        significato_semplice="Esempio di modulo per comunicare al Comune un nuovo indirizzo di residenza.",
        fonte_url=None,
        download_url=None,
        versione="demo-0.1",
        data_rilevazione="2026-08-04",
        stato_verifica="demo",
        parole_chiave=("cambio di residenza", "indirizzo", "anagrafe", "abitazione"),
    ),
    AdministrativeDocument(
        ente="Ministero delle Infrastrutture e dei Trasporti",
        codice="MIT-DEMO-01",
        titolo_ufficiale="Domanda dimostrativa di rinnovo della patente",
        categoria="motorizzazione",
        descrizione_ufficiale="Descrizione dimostrativa di una domanda relativa al rinnovo della patente di guida.",
        significato_semplice="Esempio di documento collegato alla richiesta di rinnovo di una patente.",
        fonte_url=None,
        download_url=None,
        versione="demo-0.1",
        data_rilevazione="2026-08-04",
        stato_verifica="demo",
        parole_chiave=("rinnovo patente", "patente di guida", "conducente", "motorizzazione"),
    ),
    AdministrativeDocument(
        ente="Regione",
        codice="REG-DEMO-01",
        titolo_ufficiale="Richiesta dimostrativa di esenzione dal ticket",
        categoria="sanità",
        descrizione_ufficiale="Descrizione dimostrativa di una richiesta relativa all'esenzione dal ticket sanitario.",
        significato_semplice="Esempio di modulo per chiedere che venga valutata un'esenzione dal ticket sanitario.",
        fonte_url=None,
        download_url=None,
        versione="demo-0.1",
        data_rilevazione="2026-08-04",
        stato_verifica="demo",
        parole_chiave=("esenzione ticket", "assistenza sanitaria", "prestazione", "servizio sanitario"),
    ),
    AdministrativeDocument(
        ente="Comune",
        codice="COM-SCIA-DEMO",
        titolo_ufficiale="Segnalazione dimostrativa certificata di inizio attività",
        categoria="attività produttive",
        descrizione_ufficiale="Descrizione dimostrativa di una segnalazione collegata all'inizio di un'attività.",
        significato_semplice="Esempio di documento con cui si segnala l'avvio di un'attività al Comune.",
        fonte_url=None,
        download_url=None,
        versione="demo-0.1",
        data_rilevazione="2026-08-04",
        stato_verifica="demo",
        parole_chiave=("inizio attività", "segnalazione certificata", "attività produttiva", "sportello unico"),
    ),
    AdministrativeDocument(
        ente="Comune",
        codice="COM-DEMO-03",
        titolo_ufficiale="Domanda dimostrativa di permesso di costruire",
        categoria="edilizia",
        descrizione_ufficiale="Descrizione dimostrativa di una domanda relativa a un intervento edilizio.",
        significato_semplice="Esempio di modulo per sottoporre al Comune una richiesta relativa a lavori edilizi.",
        fonte_url=None,
        download_url=None,
        versione="demo-0.1",
        data_rilevazione="2026-08-04",
        stato_verifica="demo",
        parole_chiave=("permesso di costruire", "intervento edilizio", "immobile", "titolo edilizio"),
    ),
    AdministrativeDocument(
        ente="Ministero del Lavoro",
        codice="MINLAV-DEMO-01",
        titolo_ufficiale="Comunicazione dimostrativa di assunzione",
        categoria="lavoro",
        descrizione_ufficiale="Descrizione dimostrativa di una comunicazione relativa all'avvio di un rapporto di lavoro.",
        significato_semplice="Esempio di comunicazione che registra l'inizio di un rapporto di lavoro.",
        fonte_url=None,
        download_url=None,
        versione="demo-0.1",
        data_rilevazione="2026-08-04",
        stato_verifica="demo",
        parole_chiave=("assunzione", "rapporto di lavoro", "datore di lavoro", "data inizio"),
    ),
    AdministrativeDocument(
        ente="Comune",
        codice="COM-DEMO-04",
        titolo_ufficiale="Domanda dimostrativa di iscrizione anagrafica",
        categoria="anagrafe",
        descrizione_ufficiale="Descrizione dimostrativa di una domanda relativa all'iscrizione nell'anagrafe comunale.",
        significato_semplice="Esempio di modulo per chiedere la registrazione di una persona nell'anagrafe del Comune.",
        fonte_url=None,
        download_url=None,
        versione="demo-0.1",
        data_rilevazione="2026-08-04",
        stato_verifica="demo",
        parole_chiave=("iscrizione anagrafica", "anagrafe comunale", "dati anagrafici", "residente"),
    ),
)


def connect_database(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _documents_table_sql(table_name: str = "documents") -> str:
    if not table_name.replace("_", "").isalnum():
        raise ValueError("Nome tabella non valido.")
    return DOCUMENTS_TABLE_TEMPLATE.format(table_name=table_name)


def _migrate_documents_to_v03(connection: sqlite3.Connection) -> None:
    old_columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(documents)").fetchall()
    }
    copied_columns = [column for column in DOCUMENT_COLUMNS if column in old_columns]
    old_count = int(connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0])

    connection.execute("SAVEPOINT migrate_documents_v03")
    try:
        connection.execute("ALTER TABLE documents RENAME TO documents_v02_backup")
        connection.execute(_documents_table_sql())
        column_list = ", ".join(copied_columns)
        connection.execute(
            f"INSERT INTO documents ({column_list}) "
            f"SELECT {column_list} FROM documents_v02_backup"
        )
        new_count = int(
            connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        )
        if new_count != old_count:
            raise RuntimeError("La migrazione del catalogo non ha conservato tutti i record.")
        connection.execute("DROP TABLE documents_v02_backup")
    except Exception:
        connection.execute("ROLLBACK TO migrate_documents_v03")
        connection.execute("RELEASE migrate_documents_v03")
        raise
    else:
        connection.execute("RELEASE migrate_documents_v03")


def create_schema(connection: sqlite3.Connection) -> None:
    _backup_before_migration(connection)
    create_sources_table(connection)
    table_exists = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'documents'"
    ).fetchone()
    if not table_exists:
        connection.execute(_documents_table_sql())
    else:
        column_rows = connection.execute("PRAGMA table_info(documents)").fetchall()
        columns = {row["name"] for row in column_rows}
        requires_nullable_migration = any(
            row["name"] in NULLABLE_METADATA_COLUMNS and bool(row["notnull"])
            for row in column_rows
        )
        if requires_nullable_migration:
            _migrate_documents_to_v03(connection)
            columns = set(DOCUMENT_COLUMNS)
        for column, definition in (
            ("source_id", "INTEGER REFERENCES sources(id)"),
            ("detail_url", "TEXT"),
            ("data_pubblicazione", "TEXT"),
        ):
            if column not in columns:
                connection.execute(
                    f"ALTER TABLE documents ADD COLUMN {column} {definition}"
                )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_documents_source_id ON documents (source_id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_documents_status ON documents (stato_verifica)"
    )
    create_explanations_table(connection)
    create_review_events_table(connection)
    create_entities_table(connection)
    create_families_table(connection)
    create_provenance_table(connection)
    backfill_document_provenance(connection)
    from src.observation_history import create_observation_tables
    create_observation_tables(connection)
    from src.local_packages import create_local_package_tables
    from src.local_resources import create_local_resources_table
    create_local_package_tables(connection)
    create_local_resources_table(connection)
    connection.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
    connection.execute("INSERT OR IGNORE INTO schema_migrations VALUES (?, ?)", (SCHEMA_VERSION, datetime.now(UTC).isoformat()))
    if connection.execute("PRAGMA user_version").fetchone()[0] < SCHEMA_VERSION:
        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    connection.commit()


def _backup_before_migration(connection: sqlite3.Connection) -> Path | None:
    """Conserva lo stato persistito prima della prima migrazione v0.6.0."""
    if connection.execute("PRAGMA user_version").fetchone()[0] >= SCHEMA_VERSION:
        return None
    if connection.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'documents'").fetchone() is None:
        return None
    database = next((row[2] for row in connection.execute("PRAGMA database_list") if row[1] == "main"), "")
    if not database:
        return None
    original = Path(database)
    backup_directory = original.parent / "backups"
    backup_directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    destination = backup_directory / f"{original.stem}.pre-v060.{timestamp}.db"
    # Una connessione separata evita deadlock se il chiamante ha scritture pendenti.
    with closing(sqlite3.connect(original.as_uri() + "?mode=ro", uri=True)) as source, source:
        with closing(sqlite3.connect(destination)) as target, target:
            source.backup(target)
            with closing(target.cursor()) as cursor:
                if cursor.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise RuntimeError("Il backup prima della migrazione non supera il controllo di integrità.")
    return destination


def insert_document(
    connection: sqlite3.Connection,
    document: AdministrativeDocument,
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO documents (
            ente, codice, titolo_ufficiale, categoria,
            descrizione_ufficiale, significato_semplice,
            fonte_url, download_url, detail_url, data_pubblicazione,
            versione, data_rilevazione, stato_verifica,
            parole_chiave, source_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            document.ente,
            document.codice,
            document.titolo_ufficiale,
            document.categoria,
            document.descrizione_ufficiale,
            document.significato_semplice,
            document.fonte_url,
            document.download_url,
            document.detail_url,
            document.data_pubblicazione,
            document.versione,
            document.data_rilevazione,
            document.stato_verifica,
            json.dumps(document.parole_chiave, ensure_ascii=False),
            document.source_id,
        ),
    )
    connection.commit()
    return int(cursor.lastrowid)


def insert_documents(
    connection: sqlite3.Connection,
    documents: Iterable[AdministrativeDocument],
) -> int:
    inserted = 0
    for document in documents:
        insert_document(connection, document)
        inserted += 1
    return inserted


def _row_to_document(row: sqlite3.Row) -> AdministrativeDocument:
    raw_keywords = json.loads(row["parole_chiave"] or "[]")
    return AdministrativeDocument(
        id=row["id"],
        ente=row["ente"],
        codice=row["codice"],
        titolo_ufficiale=row["titolo_ufficiale"],
        categoria=row["categoria"],
        descrizione_ufficiale=row["descrizione_ufficiale"],
        significato_semplice=row["significato_semplice"],
        fonte_url=row["fonte_url"],
        download_url=row["download_url"],
        detail_url=row["detail_url"],
        data_pubblicazione=row["data_pubblicazione"],
        versione=row["versione"],
        data_rilevazione=row["data_rilevazione"],
        stato_verifica=row["stato_verifica"],
        parole_chiave=tuple(str(keyword) for keyword in raw_keywords),
        source_id=row["source_id"],
    )


def get_document(
    connection: sqlite3.Connection,
    document_id: int,
) -> AdministrativeDocument | None:
    row = connection.execute(
        "SELECT * FROM documents WHERE id = ?",
        (document_id,),
    ).fetchone()
    return _row_to_document(row) if row else None


def list_documents(connection: sqlite3.Connection) -> list[AdministrativeDocument]:
    rows = connection.execute("SELECT * FROM documents ORDER BY id").fetchall()
    return [_row_to_document(row) for row in rows]


def list_documents_for_source(
    connection: sqlite3.Connection,
    source_id: int,
) -> list[AdministrativeDocument]:
    rows = connection.execute(
        "SELECT * FROM documents WHERE source_id = ? ORDER BY id",
        (source_id,),
    ).fetchall()
    return [_row_to_document(row) for row in rows]


def update_document_source_metadata(
    connection: sqlite3.Connection,
    document_id: int,
    document: AdministrativeDocument,
) -> bool:
    """Aggiorna solo metadati provenienti dalla fonte su record non verificati."""
    existing = connection.execute(
        "SELECT stato_verifica FROM documents WHERE id = ?",
        (document_id,),
    ).fetchone()
    if existing is None or existing["stato_verifica"] == "verificato":
        return False

    cursor = connection.execute(
        """
        UPDATE documents SET
            ente = ?, codice = ?, titolo_ufficiale = ?, categoria = ?,
            descrizione_ufficiale = ?, fonte_url = ?, download_url = ?,
            detail_url = ?, data_pubblicazione = ?, versione = ?,
            source_id = ?
        WHERE id = ?
        """,
        (
            document.ente,
            document.codice,
            document.titolo_ufficiale,
            document.categoria,
            document.descrizione_ufficiale,
            document.fonte_url,
            document.download_url,
            document.detail_url,
            document.data_pubblicazione,
            document.versione,
            document.source_id,
            document_id,
        ),
    )
    connection.commit()
    return cursor.rowcount > 0


def initialize_database(
    db_path: str | Path = DEFAULT_DB_PATH,
    *,
    seed_demo: bool = True,
) -> int:
    with closing(connect_database(db_path)) as connection, connection:
        create_schema(connection)
        if seed_demo:
            seed_initial_sources(connection)
            seed_initial_families(connection)
        count = int(connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0])
        inserted = 0
        if seed_demo and count == 0:
            inserted = insert_documents(connection, DEMO_DOCUMENTS)
        if seed_demo:
            connection.execute(
                """
                UPDATE documents
                SET source_id = (
                    SELECT sources.id
                    FROM sources
                    WHERE sources.ente = documents.ente COLLATE NOCASE
                    ORDER BY sources.id
                    LIMIT 1
                )
                WHERE source_id IS NULL
                  AND EXISTS (
                    SELECT 1 FROM sources
                    WHERE sources.ente = documents.ente COLLATE NOCASE
                  )
                """
            )
            connection.commit()
        return inserted
