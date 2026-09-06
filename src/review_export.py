from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from src.explanations import list_review_events, validate_explanation_status


REVIEW_REPORT_COLUMNS = (
    "document_id",
    "codice",
    "titolo",
    "ente",
    "stato_spiegazione",
    "versione",
    "revisore",
    "data_verifica",
    "fonte",
    "note_revisione",
)
AUDIT_REPORT_COLUMNS = ("id", "entity_type", "entity_id", "object_version", "decision", "previous_status",
                        "new_status", "reviewer", "reviewed_at", "notes", "before_json", "after_json")


def _safe_csv_cell(value):
    """Evita formule attive quando il CSV viene aperto in un foglio di calcolo."""
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + value
    return value


def export_review_report(
    connection: sqlite3.Connection,
    output_path: str | Path,
    *,
    verification_status: str | None = None,
) -> int:
    parameters: tuple[str, ...] = ()
    status_filter = ""
    if verification_status is not None:
        validated = validate_explanation_status(verification_status)
        status_filter = "WHERE e.verification_status = ?"
        parameters = (validated,)

    rows = connection.execute(
        f"""
        SELECT
            e.document_id,
            d.codice,
            d.titolo_ufficiale AS titolo,
            d.ente,
            e.verification_status AS stato_spiegazione,
            e.version AS versione,
            e.verified_by AS revisore,
            e.verified_at AS data_verifica,
            e.source_url AS fonte,
            e.review_notes AS note_revisione
        FROM document_explanations AS e
        JOIN documents AS d ON d.id = e.document_id
        {status_filter}
        ORDER BY e.document_id, e.id
        """,
        parameters,
    ).fetchall()

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=REVIEW_REPORT_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: _safe_csv_cell(row[column]) for column in REVIEW_REPORT_COLUMNS})
    return len(rows)


def export_review_events(connection: sqlite3.Connection, output_path: str | Path) -> int:
    rows = list_review_events(connection)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=AUDIT_REPORT_COLUMNS)
        writer.writeheader()
        writer.writerows({column: _safe_csv_cell(row[column]) for column in AUDIT_REPORT_COLUMNS} for row in rows)
    return len(rows)
