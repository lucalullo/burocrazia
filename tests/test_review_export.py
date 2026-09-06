from __future__ import annotations

import csv

import pytest

from src.database import connect_database, initialize_database, list_documents
from src.explanations import create_explanation, verify_explanation
from src.models import DocumentExplanation
from src.review_export import REVIEW_REPORT_COLUMNS, export_review_report


TIMESTAMP = "2026-08-04T12:00:00+00:00"


def explanation(document_id: int, version: str = "0.1") -> DocumentExplanation:
    return DocumentExplanation(
        document_id=document_id,
        official_summary="Sintesi dalla fonte.",
        simple_explanation="Spiegazione semplice separata.",
        intended_use=None,
        possible_users=(),
        facts_from_source=("Fatto dalla fonte.",),
        missing_information=(),
        warnings=(),
        source_url="https://www.inps.it/it/it/moduli/test.html",
        source_access_date="2026-08-04",
        verification_status="da_verificare",
        verified_by=None,
        verified_at=None,
        version=version,
        created_at=TIMESTAMP,
        updated_at=TIMESTAMP,
    )


def database_with_reviews(tmp_path):
    db_path = tmp_path / "reviews.db"
    initialize_database(db_path, seed_demo=True)
    with connect_database(db_path) as connection:
        documents = list_documents(connection)
        verified_id, _ = create_explanation(
            connection,
            explanation(documents[0].id),
        )
        create_explanation(connection, explanation(documents[1].id))
        verify_explanation(
            connection,
            verified_id,
            "  Revisore   CSV ",
            source_confirmed=True,
            review_notes="Controllo eseguito.",
            verified_at="2026-08-04T16:00:00+00:00",
        )
    return db_path


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def test_csv_report_has_fixed_columns_and_expected_content(tmp_path) -> None:
    db_path = database_with_reviews(tmp_path)
    output_path = tmp_path / "exports" / "review_report.csv"
    with connect_database(db_path) as connection:
        exported = export_review_report(connection, output_path)

    rows = read_csv(output_path)
    assert exported == 2
    assert len(rows) == 2
    assert tuple(rows[0]) == REVIEW_REPORT_COLUMNS
    assert rows[0]["stato_spiegazione"] == "verificato"
    assert rows[0]["revisore"] == "Revisore CSV"
    assert rows[0]["data_verifica"] == "2026-08-04T16:00:00+00:00"
    assert rows[0]["note_revisione"] == "Controllo eseguito."
    assert rows[0]["fonte"].startswith("https://www.inps.it/")
    assert rows[1]["stato_spiegazione"] == "da_verificare"
    assert rows[1]["revisore"] == ""


def test_csv_report_can_filter_by_valid_status(tmp_path) -> None:
    db_path = database_with_reviews(tmp_path)
    output_path = tmp_path / "verified.csv"
    with connect_database(db_path) as connection:
        exported = export_review_report(
            connection,
            output_path,
            verification_status="verificato",
        )

    rows = read_csv(output_path)
    assert exported == 1
    assert [row["stato_spiegazione"] for row in rows] == ["verificato"]


def test_csv_report_rejects_invalid_status_filter(tmp_path) -> None:
    db_path = database_with_reviews(tmp_path)
    with connect_database(db_path) as connection:
        with pytest.raises(ValueError, match="Stato spiegazione non valido"):
            export_review_report(
                connection,
                tmp_path / "invalid.csv",
                verification_status="qualsiasi",
            )

    assert not (tmp_path / "invalid.csv").exists()


def test_export_script_does_not_seed_demo_documents(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    from scripts import export_reviews as export_script

    db_path = tmp_path / "empty.db"
    output_path = tmp_path / "exports" / "review_report.csv"
    monkeypatch.setattr(export_script, "DEFAULT_DB_PATH", db_path)
    monkeypatch.setattr(export_script, "DEFAULT_OUTPUT_PATH", output_path)

    assert export_script.main([]) == 0
    with connect_database(db_path) as connection:
        assert list_documents(connection) == []

    assert read_csv(output_path) == []
    assert "0 righe" in capsys.readouterr().out


def test_export_script_reports_write_errors(tmp_path, monkeypatch, capsys) -> None:
    from scripts import export_reviews as export_script

    monkeypatch.setattr(export_script, "DEFAULT_DB_PATH", tmp_path / "report.db")

    def fail_export(*_args, **_kwargs):
        raise OSError("destinazione non scrivibile")

    monkeypatch.setattr(export_script, "export_review_report", fail_export)

    assert export_script.main([]) == 1
    assert "Errore esportazione revisioni" in capsys.readouterr().err
