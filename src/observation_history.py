"""Append-only technical observations; never confer editorial verification."""
from __future__ import annotations
import hashlib
import json
import sqlite3
from datetime import datetime

SCHEMA = """
CREATE TABLE IF NOT EXISTS document_observations (
    id INTEGER PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id),
    source_id INTEGER NOT NULL REFERENCES sources(id),
    observed_at TEXT NOT NULL,
    listing_sha256 TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    observer TEXT NOT NULL,
    observation_sha256 TEXT NOT NULL UNIQUE
);
CREATE INDEX IF NOT EXISTS idx_observations_document_time ON document_observations(document_id, observed_at);
CREATE TABLE IF NOT EXISTS document_replacements (
    prior_document_id INTEGER NOT NULL REFERENCES documents(id),
    replacement_document_id INTEGER NOT NULL REFERENCES documents(id),
    observed_at TEXT NOT NULL,
    evidence_url TEXT NOT NULL,
    author TEXT NOT NULL CHECK(length(trim(author)) > 0),
    PRIMARY KEY(prior_document_id,replacement_document_id,observed_at),
    CHECK(prior_document_id <> replacement_document_id)
);
CREATE TRIGGER IF NOT EXISTS observations_no_update BEFORE UPDATE ON document_observations
BEGIN SELECT RAISE(ABORT,'Technical observations are append-only'); END;
CREATE TRIGGER IF NOT EXISTS observations_no_delete BEFORE DELETE ON document_observations
BEGIN SELECT RAISE(ABORT,'Technical observations are append-only'); END;
CREATE TRIGGER IF NOT EXISTS replacements_no_update BEFORE UPDATE ON document_replacements
BEGIN SELECT RAISE(ABORT,'Replacement evidence is append-only'); END;
CREATE TRIGGER IF NOT EXISTS replacements_no_delete BEFORE DELETE ON document_replacements
BEGIN SELECT RAISE(ABORT,'Replacement evidence is append-only'); END;
"""

def create_observation_tables(connection: sqlite3.Connection):
    connection.executescript(SCHEMA)

def append_observation(connection, *, document_id, source_id, observed_at, listing_sha256, metadata, observer):
    """Caller owns the transaction. Only actual receipt dates/hashes are accepted."""
    datetime.fromisoformat(observed_at)
    if not observer.strip():raise ValueError('Technical observer required')
    if len(listing_sha256)!=64 or any(c not in '0123456789abcdef' for c in listing_sha256):raise ValueError('Listing SHA-256 required')
    row=connection.execute('SELECT source_id FROM documents WHERE id=?',(document_id,)).fetchone()
    if row is None or row[0]!=source_id:raise ValueError('Observation source does not match the catalog document')
    encoded=json.dumps(metadata,ensure_ascii=False,sort_keys=True,separators=(',',':'))
    fingerprint=hashlib.sha256(json.dumps([document_id,source_id,observed_at,listing_sha256,encoded,observer],ensure_ascii=False).encode()).hexdigest()
    cursor=connection.execute('INSERT OR IGNORE INTO document_observations(document_id,source_id,observed_at,listing_sha256,metadata_json,observer,observation_sha256) VALUES (?,?,?,?,?,?,?)',
        (document_id,source_id,observed_at,listing_sha256,encoded,observer,fingerprint))
    return bool(cursor.rowcount)

def observation_times(connection, document_id):
    # Historical acquisition timestamp is retained as a historical observation,
    # not relabelled as a current source check or a human review.
    row=connection.execute('SELECT min(t),max(t) FROM (SELECT acquired_at AS t FROM document_provenance WHERE document_id=? UNION ALL SELECT observed_at AS t FROM document_observations WHERE document_id=?)',(document_id,document_id)).fetchone()
    return dict(first_seen=row[0],last_seen=row[1])
