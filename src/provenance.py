from __future__ import annotations

import sqlite3

from src.models import DocumentProvenance


PROVENANCE_SCHEMA = """
CREATE TABLE IF NOT EXISTS document_provenance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL UNIQUE REFERENCES documents(id) ON DELETE CASCADE,
    source_id INTEGER NOT NULL REFERENCES sources(id),
    listing_url TEXT,
    detail_url TEXT,
    download_url TEXT,
    acquired_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    content_hash TEXT,
    acquisition_method TEXT NOT NULL,
    source_status TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_provenance_source ON document_provenance (source_id);
CREATE INDEX IF NOT EXISTS idx_provenance_status ON document_provenance (source_status);
"""


def create_provenance_table(connection: sqlite3.Connection) -> None:
    connection.executescript(PROVENANCE_SCHEMA)


def upsert_document_provenance(
    connection: sqlite3.Connection,
    provenance: DocumentProvenance,
) -> int:
    connection.execute(
        """
        INSERT INTO document_provenance (
            document_id, source_id, listing_url, detail_url, download_url,
            acquired_at, last_seen_at, content_hash, acquisition_method,
            source_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(document_id) DO UPDATE SET
            source_id = excluded.source_id,
            listing_url = excluded.listing_url,
            detail_url = excluded.detail_url,
            download_url = excluded.download_url,
            last_seen_at = excluded.last_seen_at,
            content_hash = excluded.content_hash,
            acquisition_method = excluded.acquisition_method,
            source_status = excluded.source_status
        """,
        (
            provenance.document_id,
            provenance.source_id,
            provenance.listing_url,
            provenance.detail_url,
            provenance.download_url,
            provenance.acquired_at,
            provenance.last_seen_at,
            provenance.content_hash,
            provenance.acquisition_method,
            provenance.source_status,
        ),
    )
    row = connection.execute(
        "SELECT id FROM document_provenance WHERE document_id = ?",
        (provenance.document_id,),
    ).fetchone()
    connection.commit()
    return int(row["id"])


def get_document_provenance(
    connection: sqlite3.Connection,
    document_id: int,
) -> DocumentProvenance | None:
    row = connection.execute(
        "SELECT * FROM document_provenance WHERE document_id = ?",
        (document_id,),
    ).fetchone()
    if row is None:
        return None
    return DocumentProvenance(
        id=row["id"],
        document_id=row["document_id"],
        source_id=row["source_id"],
        listing_url=row["listing_url"],
        detail_url=row["detail_url"],
        download_url=row["download_url"],
        acquired_at=row["acquired_at"],
        last_seen_at=row["last_seen_at"],
        content_hash=row["content_hash"],
        acquisition_method=row["acquisition_method"],
        source_status=row["source_status"],
    )


def backfill_document_provenance(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT OR IGNORE INTO document_provenance (
            document_id, source_id, listing_url, detail_url, download_url,
            acquired_at, last_seen_at, content_hash, acquisition_method,
            source_status
        )
        SELECT
            id, source_id, fonte_url, detail_url, download_url,
            data_rilevazione, data_rilevazione, NULL, 'legacy_import', 'rilevato'
        FROM documents
        WHERE stato_verifica <> 'demo' AND source_id IS NOT NULL
        """
    )
