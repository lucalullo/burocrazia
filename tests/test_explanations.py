from __future__ import annotations

import sqlite3
from dataclasses import replace

import pytest

from src.database import connect_database, initialize_database, list_documents
from src.explanations import (
    can_verify_explanation,
    create_explanation,
    deserialize_string_list,
    filter_explanations_by_status,
    get_explanation,
    get_explanation_for_document,
    get_latest_verified_explanation,
    list_explanations,
    normalize_reviewer_name,
    reject_explanation,
    serialize_string_list,
    update_explanation,
    validate_explanation_status,
    verify_explanation,
)
from src.models import DocumentExplanation


NOW = "2026-08-04T12:00:00+00:00"


def make_explanation(
    document_id: int,
    *,
    version: str = "0.1",
) -> DocumentExplanation:
    return DocumentExplanation(
        document_id=document_id,
        official_summary="Sintesi ricavata dalla fonte INPS.",
        simple_explanation="Spiegazione semplice distinta dalla sintesi ufficiale.",
        intended_use=None,
        possible_users=("cittadini interessati",),
        facts_from_source=("Il codice è TEST-01.", "La fonte è INPS."),
        missing_information=("La modalità di invio non è indicata.",),
        warnings=("Controllare la versione sul sito INPS.",),
        source_url="https://www.inps.it/it/it/moduli/test.html",
        source_access_date="2026-08-04",
        verification_status="da_verificare",
        verified_by=None,
        verified_at=None,
        version=version,
        created_at=NOW,
        updated_at=NOW,
    )


def initialized_database(tmp_path):
    db_path = tmp_path / "explanations.db"
    initialize_database(db_path, seed_demo=True)
    return db_path


def test_explanations_table_is_created_with_required_columns(tmp_path) -> None:
    db_path = initialized_database(tmp_path)
    with connect_database(db_path) as connection:
        columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(document_explanations)"
            ).fetchall()
        }

    assert {
        "id",
        "document_id",
        "official_summary",
        "simple_explanation",
        "intended_use",
        "possible_users",
        "facts_from_source",
        "missing_information",
        "warnings",
        "source_url",
        "source_access_date",
        "verification_status",
        "review_notes",
        "verified_by",
        "verified_at",
        "version",
        "created_at",
        "updated_at",
    } <= columns


def test_explanation_is_linked_to_existing_document(tmp_path) -> None:
    db_path = initialized_database(tmp_path)
    with connect_database(db_path) as connection:
        document = list_documents(connection)[0]
        explanation_id, created = create_explanation(
            connection,
            make_explanation(document.id),
        )
        recovered = get_explanation(explanation_id=explanation_id, connection=connection)

        with pytest.raises(sqlite3.IntegrityError):
            create_explanation(connection, make_explanation(99_999))

    assert created
    assert recovered is not None
    assert recovered.document_id == document.id


def test_create_and_recover_explanation_by_document_id(tmp_path) -> None:
    db_path = initialized_database(tmp_path)
    with connect_database(db_path) as connection:
        document = list_documents(connection)[0]
        explanation_id, _created = create_explanation(
            connection,
            make_explanation(document.id),
        )
        by_id = get_explanation(connection, explanation_id)
        by_document = get_explanation_for_document(connection, document.id)

    assert by_id == by_document
    assert by_document is not None
    assert by_document.simple_explanation == (
        "Spiegazione semplice distinta dalla sintesi ufficiale."
    )


def test_json_lists_support_italian_empty_null_and_invalid_values(tmp_path) -> None:
    assert deserialize_string_list(serialize_string_list(("città", "  perché  "))) == (
        "città",
        "perché",
    )
    assert deserialize_string_list(serialize_string_list(())) == ()
    assert deserialize_string_list(None) == ()
    assert deserialize_string_list("non-json") == ()
    assert deserialize_string_list('{"valore": "non-lista"}') == ()

    db_path = initialized_database(tmp_path)
    with connect_database(db_path) as connection:
        document = list_documents(connection)[0]
        explanation_id, _created = create_explanation(
            connection,
            make_explanation(document.id),
        )
        connection.execute(
            "UPDATE document_explanations SET warnings = 'non-json' WHERE id = ?",
            (explanation_id,),
        )
        connection.commit()
        recovered = get_explanation(connection, explanation_id)

    assert recovered is not None
    assert recovered.warnings == ()


def test_new_explanation_stays_pending_and_has_no_reviewer(tmp_path) -> None:
    db_path = initialized_database(tmp_path)
    with connect_database(db_path) as connection:
        document = list_documents(connection)[0]
        explanation_id, _created = create_explanation(
            connection,
            make_explanation(document.id),
        )
        recovered = get_explanation(connection, explanation_id)

    assert recovered is not None
    assert recovered.verification_status == "da_verificare"
    assert recovered.verified_by is None
    assert recovered.verified_at is None


def test_source_access_date_must_be_iso(tmp_path) -> None:
    db_path = initialized_database(tmp_path)
    with connect_database(db_path) as connection:
        document = list_documents(connection)[0]
        invalid = replace(
            make_explanation(document.id),
            source_access_date="04/08/2026",
        )
        with pytest.raises(ValueError, match="formato ISO"):
            create_explanation(connection, invalid)


def test_verification_requires_a_reviewer_name(tmp_path) -> None:
    db_path = initialized_database(tmp_path)
    with connect_database(db_path) as connection:
        document = list_documents(connection)[0]
        explanation_id, _created = create_explanation(
            connection,
            make_explanation(document.id),
        )
        with pytest.raises(ValueError, match="revisore"):
            verify_explanation(
                connection,
                explanation_id,
                "   ",
                source_confirmed=True,
            )


def test_verification_records_reviewer_and_datetime(tmp_path) -> None:
    db_path = initialized_database(tmp_path)
    verified_at = "2026-08-04T15:30:00+00:00"
    with connect_database(db_path) as connection:
        document = list_documents(connection)[0]
        explanation_id, _created = create_explanation(
            connection,
            make_explanation(document.id),
        )
        assert verify_explanation(
            connection,
            explanation_id,
            "Revisore di prova",
            source_confirmed=True,
            verified_at=verified_at,
            review_notes="Fonte e contenuto controllati.",
        )
        recovered = get_explanation(connection, explanation_id)

    assert recovered is not None
    assert recovered.verification_status == "verificato"
    assert recovered.verified_by == "Revisore di prova"
    assert recovered.verified_at == verified_at
    assert recovered.review_notes == "Fonte e contenuto controllati."


def test_rejected_explanation_is_retained(tmp_path) -> None:
    db_path = initialized_database(tmp_path)
    with connect_database(db_path) as connection:
        document = list_documents(connection)[0]
        explanation_id, _created = create_explanation(
            connection,
            make_explanation(document.id),
        )
        assert reject_explanation(
            connection,
            explanation_id,
            reviewed_by="Revisore di prova",
            reviewed_at="2026-08-04T16:00:00+00:00",
            review_notes="Contenuto da correggere.",
        )
        recovered = get_explanation(connection, explanation_id)

    assert recovered is not None
    assert recovered.verification_status == "rifiutato"
    assert recovered.verified_by == "Revisore di prova"
    assert recovered.verified_at is None
    assert recovered.review_notes == "Contenuto da correggere."


def test_versioning_allows_new_version_and_deduplicates_same_version(tmp_path) -> None:
    db_path = initialized_database(tmp_path)
    with connect_database(db_path) as connection:
        document = list_documents(connection)[0]
        first_id, first_created = create_explanation(
            connection,
            make_explanation(document.id, version="0.1"),
        )
        duplicate_id, duplicate_created = create_explanation(
            connection,
            make_explanation(document.id, version="0.1"),
        )
        second_id, second_created = create_explanation(
            connection,
            make_explanation(document.id, version="0.2"),
        )
        explanations = list_explanations(connection)

    assert first_created and second_created
    assert not duplicate_created
    assert duplicate_id == first_id
    assert second_id != first_id
    assert len(explanations) == 2


def test_filter_and_latest_verified_explanation(tmp_path) -> None:
    db_path = initialized_database(tmp_path)
    with connect_database(db_path) as connection:
        document = list_documents(connection)[0]
        first_id, _ = create_explanation(
            connection,
            make_explanation(document.id, version="0.1"),
        )
        second_id, _ = create_explanation(
            connection,
            make_explanation(document.id, version="0.2"),
        )
        verify_explanation(
            connection,
            first_id,
            "Primo revisore",
            source_confirmed=True,
            verified_at="2026-08-04T10:00:00+00:00",
        )
        verify_explanation(
            connection,
            second_id,
            "Secondo revisore",
            source_confirmed=True,
            verified_at="2026-08-04T11:00:00+00:00",
        )
        verified = filter_explanations_by_status(connection, "verificato")
        latest = get_latest_verified_explanation(connection, document.id)

    assert len(verified) == 2
    assert latest is not None
    assert latest.id == second_id


def test_update_explanation_changes_content_without_breaking_link(tmp_path) -> None:
    db_path = initialized_database(tmp_path)
    with connect_database(db_path) as connection:
        document = list_documents(connection)[0]
        explanation_id, _ = create_explanation(
            connection,
            make_explanation(document.id),
        )
        current = get_explanation(connection, explanation_id)
        assert current is not None
        updated = replace(
            current,
            simple_explanation="Testo semplice corretto dal revisore.",
            review_notes="Reso il testo piu chiaro.",
            updated_at="2026-08-04T14:00:00+00:00",
        )
        assert update_explanation(connection, updated)
        recovered = get_explanation(connection, explanation_id)

    assert recovered is not None
    assert recovered.document_id == document.id
    assert recovered.simple_explanation == "Testo semplice corretto dal revisore."
    assert recovered.review_notes == "Reso il testo piu chiaro."


def test_invalid_statuses_are_rejected(tmp_path) -> None:
    with pytest.raises(ValueError, match="Stato spiegazione non valido"):
        validate_explanation_status("approvato")

    db_path = initialized_database(tmp_path)
    with connect_database(db_path) as connection:
        document = list_documents(connection)[0]
        with pytest.raises(ValueError, match="Stato spiegazione non valido"):
            create_explanation(
                connection,
                replace(
                    make_explanation(document.id),
                    verification_status="approvato",
                ),
            )


@pytest.mark.parametrize(
    "reviewer",
    ["", "   ", "\u200b\u2060", "\t\n", "\u034f\ufe0f"],
)
def test_empty_or_invisible_reviewer_names_are_rejected(reviewer: str) -> None:
    with pytest.raises(ValueError, match="revisore"):
        normalize_reviewer_name(reviewer)

    assert not can_verify_explanation(reviewer, source_confirmed=True)


def test_reviewer_name_is_normalized_and_has_a_reasonable_limit(tmp_path) -> None:
    assert normalize_reviewer_name("  Mario\u200b   Rossi  ") == "Mario Rossi"
    with pytest.raises(ValueError, match="120"):
        normalize_reviewer_name("R" * 121)

    db_path = initialized_database(tmp_path)
    with connect_database(db_path) as connection:
        document = list_documents(connection)[0]
        explanation_id, _ = create_explanation(
            connection,
            make_explanation(document.id),
        )
        assert verify_explanation(
            connection,
            explanation_id,
            "  Mario\u200b   Rossi  ",
            source_confirmed=True,
            verified_at="2026-08-04T15:30:00+00:00",
        )
        recovered = get_explanation(connection, explanation_id)

    assert recovered is not None
    assert recovered.verified_by == "Mario Rossi"


def test_verification_requires_explicit_source_confirmation(tmp_path) -> None:
    assert not can_verify_explanation("Revisore", source_confirmed=False)
    assert can_verify_explanation("Revisore", source_confirmed=True)

    db_path = initialized_database(tmp_path)
    with connect_database(db_path) as connection:
        document = list_documents(connection)[0]
        explanation_id, _ = create_explanation(
            connection,
            make_explanation(document.id),
        )
        with pytest.raises(ValueError, match="fonte INPS"):
            verify_explanation(
                connection,
                explanation_id,
                "Revisore",
                source_confirmed=False,
            )
        recovered = get_explanation(connection, explanation_id)

    assert recovered is not None
    assert recovered.verification_status == "da_verificare"


def test_editorial_update_cannot_change_protected_fields_or_status(tmp_path) -> None:
    db_path = initialized_database(tmp_path)
    with connect_database(db_path) as connection:
        document = list_documents(connection)[0]
        explanation_id, _ = create_explanation(
            connection,
            make_explanation(document.id),
        )
        current = get_explanation(connection, explanation_id)
        assert current is not None

        for changed in (
            replace(current, document_id=document.id + 1),
            replace(current, source_url="https://example.org/sostituita"),
            replace(current, version="9.9"),
            replace(current, verification_status="verificato"),
        ):
            with pytest.raises(ValueError, match="campi protetti"):
                update_explanation(connection, changed)

        recovered = get_explanation(connection, explanation_id)

    assert recovered is not None
    assert recovered.document_id == document.id
    assert recovered.source_url == "https://www.inps.it/it/it/moduli/test.html"
    assert recovered.version == "0.1"
    assert recovered.verification_status == "da_verificare"
