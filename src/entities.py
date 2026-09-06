from __future__ import annotations

import sqlite3

from src.models import Entity


CATALOG_STATES = (
    "non_analizzato",
    "fonte_trovata",
    "in_catalogazione",
    "catalogato",
    "manuale",
    "errore",
)

ENTITIES_SCHEMA = f"""
CREATE TABLE IF NOT EXISTS entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codice_ipa TEXT NOT NULL UNIQUE,
    denominazione TEXT NOT NULL,
    categoria TEXT,
    livello TEXT,
    sito_istituzionale TEXT,
    stato_catalogazione TEXT NOT NULL DEFAULT 'non_analizzato'
        CHECK (stato_catalogazione IN ({', '.join(repr(state) for state in CATALOG_STATES)})),
    last_checked_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_entities_name ON entities (denominazione);
CREATE INDEX IF NOT EXISTS idx_entities_state ON entities (stato_catalogazione);
"""


def create_entities_table(connection: sqlite3.Connection) -> None:
    connection.executescript(ENTITIES_SCHEMA)


def _row_to_entity(row: sqlite3.Row) -> Entity:
    return Entity(
        id=row["id"],
        codice_ipa=row["codice_ipa"],
        denominazione=row["denominazione"],
        categoria=row["categoria"],
        livello=row["livello"],
        sito_istituzionale=row["sito_istituzionale"],
        stato_catalogazione=row["stato_catalogazione"],
        last_checked_at=row["last_checked_at"],
    )


def get_entity_by_ipa_code(
    connection: sqlite3.Connection,
    codice_ipa: str,
) -> Entity | None:
    row = connection.execute(
        "SELECT * FROM entities WHERE codice_ipa = ? COLLATE NOCASE",
        (codice_ipa.strip(),),
    ).fetchone()
    return _row_to_entity(row) if row else None


def list_entities(connection: sqlite3.Connection) -> list[Entity]:
    rows = connection.execute(
        "SELECT * FROM entities ORDER BY denominazione, id"
    ).fetchall()
    return [_row_to_entity(row) for row in rows]


def upsert_entity(connection: sqlite3.Connection, entity: Entity) -> tuple[int, bool]:
    existing = get_entity_by_ipa_code(connection, entity.codice_ipa)
    if existing is None:
        cursor = connection.execute(
            """
            INSERT INTO entities (
                codice_ipa, denominazione, categoria, livello,
                sito_istituzionale, stato_catalogazione, last_checked_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entity.codice_ipa,
                entity.denominazione,
                entity.categoria,
                entity.livello,
                entity.sito_istituzionale,
                entity.stato_catalogazione,
                entity.last_checked_at,
            ),
        )
        connection.commit()
        return int(cursor.lastrowid), True

    connection.execute(
        """
        UPDATE entities SET
            denominazione = ?, categoria = ?, livello = ?,
            sito_istituzionale = ?, last_checked_at = ?
        WHERE id = ?
        """,
        (
            entity.denominazione,
            entity.categoria,
            entity.livello,
            entity.sito_istituzionale,
            entity.last_checked_at,
            existing.id,
        ),
    )
    connection.commit()
    assert existing.id is not None
    return existing.id, False
