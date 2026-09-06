from dataclasses import asdict, replace

import pytest

from src.database import connect_database, initialize_database, insert_document
from src.explanations import (can_verify_explanation, create_explanation, create_explanation_revision, get_explanation,
                              list_review_events, update_explanation, verify_explanation)
from src.models import AdministrativeDocument, DocumentExplanation
from src.review import save_editorial_changes, submit_document_review, submit_explanation_review


CREATED_AT = "2026-09-05T08:00:00+00:00"
REVIEWED_AT = "2026-09-05T09:00:00+00:00"


def prepare_draft(tmp_path, text, status="bozza"):
    path = tmp_path / "explanation-review.db"
    initialize_database(path, seed_demo=False)
    with connect_database(path) as connection:
        document_id = insert_document(connection, AdministrativeDocument(
            ente="INPS", titolo_ufficiale="Documento sintetico di revisione", categoria=None,
            descrizione_ufficiale=None, significato_semplice=None, versione="1",
            data_rilevazione="2026-09-05", stato_verifica="da_verificare",
            fonte_url="https://www.inps.it/moduli/prova"))
        explanation_id, _ = create_explanation(connection, DocumentExplanation(
            document_id=document_id, official_summary=None, simple_explanation=text,
            intended_use=None, possible_users=(), facts_from_source=("Titolo registrato nella fonte.",),
            missing_information=(), warnings=(), source_url="https://www.inps.it/moduli/prova",
            source_access_date="2026-09-05", verification_status=status, version="1",
            created_at=CREATED_AT, updated_at=CREATED_AT, review_notes="Bozza da completare."),
            created_by="Autore della bozza")
        # Conserva anche i valori grezzi legacy: non basta controllare il None
        # prodotto dalla normalizzazione dell'editor corrente.
        connection.execute("UPDATE document_explanations SET simple_explanation = ? WHERE id = ?", (text, explanation_id))
    return path, document_id, explanation_id


def review(path, explanation_id, route):
    if route == "application":
        return submit_explanation_review(explanation_id, "verificato", "Revisore", source_confirmed=True,
                                         review_notes="Confronto umano eseguito.", db_path=path,
                                         reviewed_at=REVIEWED_AT)
    with connect_database(path) as connection:
        return verify_explanation(connection, explanation_id, "Revisore", source_confirmed=True,
                                  review_notes="Confronto umano eseguito.", verified_at=REVIEWED_AT)


def snapshot(path, explanation_id):
    with connect_database(path) as connection:
        return (asdict(get_explanation(connection, explanation_id)), list_review_events(connection),
                [dict(row) for row in connection.execute("SELECT * FROM documents ORDER BY id")])


@pytest.mark.parametrize("route", ["direct", "application"])
@pytest.mark.parametrize("text", [None, "", " \t\n "], ids=["none", "empty", "whitespace"])
def test_a02_incomplete_explanation_cannot_be_verified_and_failure_is_atomic(tmp_path, route, text):
    path, _, explanation_id = prepare_draft(tmp_path, text)
    before = snapshot(path, explanation_id)
    with pytest.raises(ValueError, match="[Ss]piegazione semplice"):
        review(path, explanation_id, route)
    assert snapshot(path, explanation_id) == before


@pytest.mark.parametrize("route", ["direct", "application"])
def test_a02_rejected_document_blocks_verification_without_partial_updates(tmp_path, route):
    path, document_id, explanation_id = prepare_draft(tmp_path, "Spiegazione compilata dal revisore.")
    assert submit_document_review(document_id, "rifiutato", "Curatore", review_notes="Fonte da riesaminare.",
                                  db_path=path, reviewed_at=CREATED_AT)
    before = snapshot(path, explanation_id)
    with pytest.raises(ValueError, match="documento.*rifiutato"):
        review(path, explanation_id, route)
    assert snapshot(path, explanation_id) == before


@pytest.mark.parametrize("text", [None, "", " \t\n "], ids=["none", "empty", "whitespace"])
@pytest.mark.parametrize("status", ["bozza", "da_verificare"])
def test_a02_incomplete_draft_can_be_created_and_edited(tmp_path, text, status):
    path, _, explanation_id = prepare_draft(tmp_path, text, status)
    assert save_editorial_changes(explanation_id, official_summary=None, simple_explanation=text,
                                  intended_use=None, possible_users=(), facts_from_source=("Fatto dalla fonte.",),
                                  missing_information=(), warnings=(), review_notes="Lavorazione incompleta.",
                                  db_path=path, updated_at=REVIEWED_AT, reviewed_by="Autore")
    explanation, events, _ = snapshot(path, explanation_id)
    assert explanation["simple_explanation"] is None
    assert explanation["verification_status"] == status
    assert explanation["verified_by"] is None and explanation["verified_at"] is None
    assert [event["decision"] for event in events] == ["creazione", "modifica_editoriale"]


@pytest.mark.parametrize("route", ["direct", "application"])
def test_a02_minimum_editorial_content_is_verifiable_without_optional_fields(tmp_path, route):
    path, _, explanation_id = prepare_draft(tmp_path, "Spiegazione controllata dal revisore.")
    before, _, _ = snapshot(path, explanation_id)
    assert review(path, explanation_id, route)
    explanation, events, _ = snapshot(path, explanation_id)
    assert explanation["verification_status"] == "verificato"
    assert explanation["verified_by"] == "Revisore" and explanation["verified_at"] == REVIEWED_AT
    assert explanation["intended_use"] is None and explanation["official_summary"] is None
    for field in ("document_id", "version", "source_url", "source_access_date", "created_at", "simple_explanation"):
        assert explanation[field] == before[field]
    assert [event["decision"] for event in events] == ["creazione", "verifica"]


def test_a02_public_create_and_update_cannot_bypass_review_transition(tmp_path):
    path, _, explanation_id = prepare_draft(tmp_path, None)
    before = snapshot(path, explanation_id)
    with connect_database(path) as connection:
        current = get_explanation(connection, explanation_id)
        verified = replace(current, verification_status="verificato", verified_by="Revisore", verified_at=REVIEWED_AT)
        with pytest.raises(ValueError, match="bozza|spiegazione semplice"):
            create_explanation(connection, replace(verified, id=None, version="2"))
        with pytest.raises(ValueError, match="campi protetti"):
            update_explanation(connection, verified)
    assert snapshot(path, explanation_id) == before


def test_a02_verified_version_and_audit_survive_an_incomplete_new_revision(tmp_path):
    path, _, explanation_id = prepare_draft(tmp_path, "Versione controllata dal revisore.")
    assert review(path, explanation_id, "direct")
    original, events, _ = snapshot(path, explanation_id)
    with connect_database(path) as connection:
        new_id = create_explanation_revision(connection, explanation_id, "2", "Autore", created_at=REVIEWED_AT)
        fresh = get_explanation(connection, new_id)
        assert update_explanation(connection, replace(fresh, simple_explanation=None), reviewed_by="Autore")
    before = snapshot(path, new_id)
    with pytest.raises(ValueError, match="[Ss]piegazione semplice"):
        review(path, new_id, "application")
    assert snapshot(path, new_id) == before
    after, all_events, _ = snapshot(path, explanation_id)
    assert after == original and all_events[:len(events)] == events


@pytest.mark.parametrize("text", [None, "", " \t\n ", "Spiegazione compilata."])
@pytest.mark.parametrize("document_status", ["da_verificare", "rifiutato"])
def test_a02_review_button_respects_saved_text_and_document_status(tmp_path, text, document_status):
    path, _, explanation_id = prepare_draft(tmp_path, text)
    with connect_database(path) as connection:
        explanation = get_explanation(connection, explanation_id)
    assert can_verify_explanation("Revisore", True, explanation=explanation, document_status=document_status) == (
        bool(text and text.strip()) and document_status != "rifiutato")
