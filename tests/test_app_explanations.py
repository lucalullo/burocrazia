from __future__ import annotations

from dataclasses import replace

from app import (
    PRELIMINARY_EXPLANATION_MESSAGE,
    REJECTED_EXPLANATION_MESSAGE,
    explanation_collection_state,
    explanation_display_state,
    select_explanation_for_display,
    verified_revision_lines,
)
from src.database import connect_database, initialize_database, list_documents
from src.explanations import create_explanation, get_explanation
from src.models import DocumentExplanation
from src.models import AdministrativeDocument
from src.recognize import recognize_document
from src.review import submit_explanation_review


BASE_TIME = "2026-08-04T12:00:00+00:00"


def explanation(
    status: str,
    *,
    explanation_id: int = 1,
    verified_at: str | None = None,
) -> DocumentExplanation:
    return DocumentExplanation(
        id=explanation_id,
        document_id=11,
        official_summary="Sintesi ufficiale.",
        simple_explanation="Spiegazione semplice.",
        intended_use="Uso generale.",
        possible_users=(),
        facts_from_source=("Fatto dalla fonte.",),
        missing_information=("Informazione mancante.",),
        warnings=(),
        source_url="https://www.inps.it/moduli/test.html",
        source_access_date="2026-08-04",
        verification_status=status,
        verified_by="Revisore" if status == "verificato" else None,
        verified_at=verified_at,
        version="0.1",
        created_at=BASE_TIME,
        updated_at=BASE_TIME,
    )


def test_document_without_explanation_is_unavailable() -> None:
    assert select_explanation_for_display([]) is None
    assert explanation_display_state(None) == "non_disponibile"


def test_pending_explanation_is_preliminary() -> None:
    selected = select_explanation_for_display([explanation("da_verificare")])

    assert selected is not None
    assert explanation_display_state(selected) == "preliminare"
    assert PRELIMINARY_EXPLANATION_MESSAGE == (
        "Spiegazione preliminare non ancora revisionata"
    )


def test_verified_explanation_is_valid_for_user_display() -> None:
    selected = select_explanation_for_display(
        [
            explanation(
                "verificato",
                verified_at="2026-08-04T13:00:00+00:00",
            )
        ]
    )

    assert selected is not None
    assert explanation_display_state(selected) == "verificata"
    assert verified_revision_lines(selected) == (
        "Contenuto revisionato da: Revisore",
        "Data della revisione: 04/08/2026",
    )


def test_rejected_explanation_is_not_displayed_as_valid() -> None:
    rejected = explanation("rifiutato")

    assert select_explanation_for_display([rejected]) is None
    assert explanation_display_state(rejected) == "non_disponibile"
    assert explanation_collection_state([rejected]) == "rifiutata"
    assert REJECTED_EXPLANATION_MESSAGE == (
        "Documento riconosciuto, ma la spiegazione disponibile non ha superato "
        "la revisione."
    )


def test_rejected_only_message_does_not_apply_when_a_preliminary_card_exists() -> None:
    assert (
        explanation_collection_state(
            [explanation("rifiutato"), explanation("bozza", explanation_id=2)]
        )
        == "preliminare"
    )


def test_verified_explanation_takes_precedence_over_preliminary() -> None:
    preliminary = explanation("da_verificare", explanation_id=2)
    verified = explanation(
        "verificato",
        explanation_id=1,
        verified_at="2026-08-04T13:00:00+00:00",
    )

    assert select_explanation_for_display([preliminary, verified]) == verified


def test_recognized_document_id_selects_its_preliminary_explanation() -> None:
    document = AdministrativeDocument(
        id=11,
        ente="INPS",
        codice="SR211",
        titolo_ufficiale="RINUNCIA DEI BENEFICIARI ALLA CARTA ACQUISTI",
        categoria="prestazioni",
        descrizione_ufficiale=None,
        significato_semplice=None,
        versione="1.0",
        data_rilevazione="2026-08-04",
        stato_verifica="da_verificare",
    )
    result = recognize_document(
        "SR211 RINUNCIA DEI BENEFICIARI ALLA CARTA ACQUISTI",
        [document],
    )
    explanations = [explanation("da_verificare")]
    linked = [
        item
        for item in explanations
        if result.document is not None and item.document_id == result.document.id
    ]
    selected = select_explanation_for_display(linked)

    assert result.recognized
    assert selected is not None
    assert explanation_display_state(selected) == "preliminare"


def test_review_submission_requires_name_for_verification_and_supports_rejection(
    tmp_path,
) -> None:
    db_path = tmp_path / "review.db"
    initialize_database(db_path, seed_demo=True)
    with connect_database(db_path) as connection:
        document = list_documents(connection)[0]
        pending = replace(explanation("da_verificare"), id=None, document_id=document.id)
        explanation_id, _created = create_explanation(connection, pending)

    try:
        submit_explanation_review(
            explanation_id,
            "verificato",
            "",
            source_confirmed=True,
            db_path=db_path,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("La verifica senza revisore doveva essere rifiutata.")

    assert submit_explanation_review(
        explanation_id,
        "rifiutato",
        "Revisore di prova",
        source_confirmed=False,
        review_notes="Non supera la revisione.",
        db_path=db_path,
    )
    with connect_database(db_path) as connection:
        recovered = get_explanation(connection, explanation_id)

    assert recovered is not None
    assert recovered.verification_status == "rifiutato"
    assert recovered.review_notes == "Non supera la revisione."
