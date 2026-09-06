from __future__ import annotations

from src.database import connect_database, initialize_database, list_documents
from src.explanations import create_explanation, get_explanation
from src.models import DocumentExplanation
from src.review import editorial_lines_to_items, save_editorial_changes


TIMESTAMP = "2026-08-04T12:00:00+00:00"


def pending_explanation(document_id: int) -> DocumentExplanation:
    return DocumentExplanation(
        document_id=document_id,
        official_summary="Sintesi iniziale.",
        simple_explanation="Spiegazione iniziale.",
        intended_use=None,
        possible_users=("Persona interessata",),
        facts_from_source=("Fatto iniziale.",),
        missing_information=("Dato non presente.",),
        warnings=("Controllare la versione.",),
        source_url="https://www.inps.it/it/it/moduli/test.html",
        source_access_date="2026-08-04",
        verification_status="da_verificare",
        verified_by=None,
        verified_at=None,
        version="0.1",
        created_at=TIMESTAMP,
        updated_at=TIMESTAMP,
    )


def test_editorial_lines_ignore_empty_rows() -> None:
    assert editorial_lines_to_items(" prima \n\n seconda\n   ") == (
        "prima",
        "seconda",
    )


def test_minimal_editor_updates_only_editorial_fields_and_notes(tmp_path) -> None:
    db_path = tmp_path / "editor.db"
    initialize_database(db_path, seed_demo=True)
    with connect_database(db_path) as connection:
        document = list_documents(connection)[0]
        explanation_id, _ = create_explanation(
            connection,
            pending_explanation(document.id),
        )
        before = get_explanation(connection, explanation_id)

    assert before is not None
    assert save_editorial_changes(
        explanation_id,
        official_summary="Sintesi corretta.",
        simple_explanation="Spiegazione corretta.",
        intended_use="Uso descritto dalla scheda.",
        possible_users=("Primo utente", "Secondo utente"),
        facts_from_source=("Primo fatto.", "Secondo fatto."),
        missing_information=("Informazione ancora assente.",),
        warnings=("Non e una consulenza personalizzata.",),
        review_notes="Revisione editoriale completata.",
        updated_at="2026-08-04T14:00:00+00:00",
        db_path=db_path,
    )

    with connect_database(db_path) as connection:
        recovered = get_explanation(connection, explanation_id)

    assert recovered is not None
    assert recovered.official_summary == "Sintesi corretta."
    assert recovered.simple_explanation == "Spiegazione corretta."
    assert recovered.intended_use == "Uso descritto dalla scheda."
    assert recovered.possible_users == ("Primo utente", "Secondo utente")
    assert recovered.facts_from_source == ("Primo fatto.", "Secondo fatto.")
    assert recovered.missing_information == ("Informazione ancora assente.",)
    assert recovered.warnings == ("Non e una consulenza personalizzata.",)
    assert recovered.review_notes == "Revisione editoriale completata."
    assert recovered.updated_at == "2026-08-04T14:00:00+00:00"
    assert recovered.document_id == before.document_id
    assert recovered.source_url == before.source_url
    assert recovered.source_access_date == before.source_access_date
    assert recovered.version == before.version
    assert recovered.verification_status == "da_verificare"
