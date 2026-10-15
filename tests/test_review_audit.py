from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
from dataclasses import replace

import pytest

from src.database import connect_database, create_schema, get_document, initialize_database, list_documents
from src.explanations import (create_explanation, create_explanation_revision, get_explanation,
                              list_review_events, reject_explanation, update_explanation, verify_explanation)
from src.models import DocumentExplanation
from src.review import submit_document_review, submit_explanation_draft, submit_resource_review
from src.review_export import export_review_events, export_review_report


def prepare_database(tmp_path):
    path = tmp_path / "audit.db"
    initialize_database(path)
    return path


def draft(document_id):
    return DocumentExplanation(document_id=document_id, official_summary="Sintesi registrata.",
        simple_explanation="Spiegazione da controllare.", intended_use=None, possible_users=(),
        facts_from_source=("Titolo del documento presente nella fonte.",), missing_information=(), warnings=(),
        source_url="https://www.inps.it/moduli/prova", source_access_date="2026-09-05",
        verification_status="da_verificare", version="0.1", created_at="2026-09-05T08:00:00+00:00",
        updated_at="2026-09-05T08:00:00+00:00")


def test_verification_and_revocation_preserve_history_and_require_reason(tmp_path):
    path = prepare_database(tmp_path)
    with connect_database(path) as connection:
        explanation_id, _ = create_explanation(connection, draft(1))
        assert verify_explanation(connection, explanation_id, "Mario Rossi", source_confirmed=True,
                                  verified_at="2026-09-05T09:00:00+00:00")
        verified = get_explanation(connection, explanation_id)
        for notes in (None, "", "\u200b\u2060"):
            with pytest.raises(ValueError, match="motivazione"):
                reject_explanation(connection, explanation_id, reviewed_by="Anna Verdi", review_notes=notes)
        assert get_explanation(connection, explanation_id) == verified
        assert reject_explanation(connection, explanation_id, reviewed_by="Anna Verdi",
                                  review_notes="La spiegazione richiede una rettifica.",
                                  reviewed_at="2026-09-05T10:00:00+00:00")
        events = list_review_events(connection, object_type="explanation", object_id=explanation_id)
        assert [event["decision"] for event in events] == ["creazione", "verifica", "rifiuto"]
        old = json.loads(events[-1]["before_json"])
        assert old["verified_by"] == "Mario Rossi"
        assert old["verified_at"] == "2026-09-05T09:00:00+00:00"
        assert events[-1]["reviewer"] == "Anna Verdi"
        assert events[-1]["reviewed_at"] == "2026-09-05T10:00:00+00:00"
        assert events[-1]["object_version"] == "0.1"
        with pytest.raises(ValueError, match="nuova versione"):
            update_explanation(connection, replace(get_explanation(connection, explanation_id), simple_explanation="Altro testo"))


@pytest.mark.parametrize("statement", ["UPDATE review_events SET reviewer = 'Altro'", "DELETE FROM review_events"])
def test_audit_events_cannot_be_overwritten_or_deleted(tmp_path, statement):
    path = prepare_database(tmp_path)
    with connect_database(path) as connection:
        create_explanation(connection, draft(1))
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(statement)
        assert len(list_review_events(connection)) == 1


def test_new_revision_keeps_verified_version_unchanged_and_starts_draft(tmp_path):
    path = prepare_database(tmp_path)
    with connect_database(path) as connection:
        explanation_id, _ = create_explanation(connection, draft(1))
        verify_explanation(connection, explanation_id, "Revisore", source_confirmed=True)
        original = get_explanation(connection, explanation_id)
        new_id = create_explanation_revision(connection, explanation_id, "0.2", "Nuovo autore")
        fresh = get_explanation(connection, new_id)
        assert get_explanation(connection, explanation_id) == original
        assert fresh.verification_status == "bozza"
        assert fresh.verified_by is None and fresh.verified_at is None
        assert fresh.simple_explanation == original.simple_explanation
        assert list_review_events(connection)[-1]["decision"] == "nuova_versione"
        assert update_explanation(connection, replace(fresh, simple_explanation="Nuova bozza"), reviewed_by="Autore")
        assert get_explanation(connection, explanation_id) == original
        with pytest.raises(ValueError, match="esiste già"):
            create_explanation_revision(connection, explanation_id, "0.2", "Nuovo autore")


def test_state_change_rolls_back_when_audit_cannot_be_written(tmp_path):
    path = prepare_database(tmp_path)
    with connect_database(path) as connection:
        explanation_id, _ = create_explanation(connection, draft(1))
        original = get_explanation(connection, explanation_id)
        connection.execute("CREATE TRIGGER fail_audit BEFORE INSERT ON review_events BEGIN SELECT RAISE(ABORT, 'test failure'); END")
        with pytest.raises(sqlite3.IntegrityError, match="test failure"):
            verify_explanation(connection, explanation_id, "Revisore", source_confirmed=True)
        connection.commit()
        assert get_explanation(connection, explanation_id) == original


def test_migration_backup_is_idempotent_and_does_not_invent_reviews(tmp_path):
    path = prepare_database(tmp_path)
    with connect_database(path) as connection:
        before = list_documents(connection)
        connection.execute("DROP TABLE review_events")
        connection.execute("DROP TABLE schema_migrations")
        connection.execute("PRAGMA user_version = 0")
        connection.commit()
    with connect_database(path) as connection:
        create_schema(connection)
        create_schema(connection)
        assert list_documents(connection) == before
        assert list_review_events(connection) == []
        from src.database import SCHEMA_VERSION
        assert connection.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    backups = list((tmp_path / "backups").glob("*.db"))
    assert len(backups) == 1
    with connect_database(backups[0]) as old:
        assert old.execute("PRAGMA user_version").fetchone()[0] == 0
        assert list_documents(old) == before


def test_document_review_is_explicit_and_preserves_each_decision(tmp_path):
    path = prepare_database(tmp_path)
    with connect_database(path) as connection:
        connection.execute("UPDATE documents SET stato_verifica='da_verificare', fonte_url='https://www.inps.it/moduli/prova' WHERE id=1")
        connection.commit()
        create_schema(connection)
    with pytest.raises(ValueError, match="Confermare"):
        submit_document_review(1, "verificato", "Revisore", db_path=path)
    assert submit_document_review(1, "verificato", "Revisore", source_confirmed=True, db_path=path)
    with pytest.raises(ValueError, match="motivazione"):
        submit_document_review(1, "rifiutato", "Revisore", db_path=path)
    assert submit_document_review(1, "da_verificare", "Revisore", review_notes="Necessario nuovo confronto.", db_path=path)
    with connect_database(path) as connection:
        assert get_document(connection, 1).stato_verifica == "da_verificare"
        events = list_review_events(connection, object_type="document", object_id=1)
        assert [event["new_status"] for event in events] == ["verificato", "da_verificare"]
        assert all(event["reviewer"] and event["reviewed_at"] and event["object_version"] for event in events)
    with pytest.raises(ValueError, match="demo"):
        submit_document_review(2, "verificato", "Revisore", source_confirmed=True, db_path=path)


def test_export_includes_historic_decisions_and_neutralizes_csv_formulas(tmp_path):
    path = prepare_database(tmp_path)
    with connect_database(path) as connection:
        explanation_id, _ = create_explanation(connection, draft(1))
        verify_explanation(connection, explanation_id, "=HYPERLINK(1)", source_confirmed=True, review_notes="=1+2")
        assert export_review_events(connection, tmp_path / "audit.csv") == 2
        assert export_review_report(connection, tmp_path / "review.csv") == 1
    with (tmp_path / "review.csv").open(newline="", encoding="utf-8") as source:
        row = next(csv.DictReader(source))
        assert row["revisore"].startswith("'=")
        assert row["note_revisione"].startswith("'=")


def test_editor_can_create_a_first_draft_for_another_official_entity(tmp_path):
    path = prepare_database(tmp_path)
    with connect_database(path) as connection:
        connection.execute("UPDATE documents SET fonte_url = 'https://www.agenziaentrate.gov.it/modello-730' WHERE id = 2")
    explanation_id = submit_explanation_draft(2, "0.1", "Autore", "2026-09-05", db_path=path)
    with connect_database(path) as connection:
        explanation = get_explanation(connection, explanation_id)
        assert explanation.verification_status == "bozza"
        assert explanation.simple_explanation is None
        assert list_review_events(connection)[-1]["reviewer"] == "Autore"


def test_resource_review_checks_bytes_and_records_verification_and_revocation(tmp_path):
    path = prepare_database(tmp_path)
    resource_root = tmp_path / "resources"
    resource_root.mkdir()
    content = b"Materiale locale per test di revisione."
    material = resource_root / "source.txt"
    material.write_bytes(content)
    with connect_database(path) as connection:
        source_id = get_document(connection, 1).source_id
        connection.execute("""INSERT INTO local_resources
            (document_id,source_id,title,relative_path,media_type,size_bytes,sha256,provenance,
             acquired_at,version,reuse_conditions,verification_status,package_id)
            VALUES (1,?,'Materiale','source.txt','text/plain',?,?,'Test locale','2026-09-05',
                    '1','Uso di test','da_verificare','review-test')""", (source_id, len(content), hashlib.sha256(content).hexdigest()))
    material.write_bytes(b"Contenuto manomesso")
    with pytest.raises(ValueError, match="dimensione|impronta"):
        submit_resource_review(1, "verificato", "Revisore", source_confirmed=True, db_path=path, resource_root=resource_root)
    with connect_database(path) as connection:
        assert list_review_events(connection, object_type="resource") == []
    material.write_bytes(content)
    assert submit_resource_review(1, "verificato", "Revisore", source_confirmed=True, db_path=path, resource_root=resource_root)
    with pytest.raises(ValueError, match="motivazione"):
        submit_resource_review(1, "rifiutato", "Secondo revisore", db_path=path, resource_root=resource_root)
    assert submit_resource_review(1, "rifiutato", "Secondo revisore", review_notes="Necessario controllo sulla provenienza.", db_path=path, resource_root=resource_root)
    with connect_database(path) as connection:
        events = list_review_events(connection, object_type="resource")
        assert [event["new_status"] for event in events] == ["verificato", "rifiutato"]
        assert json.loads(events[-1]["before_json"])["verification_status"] == "verificato"
