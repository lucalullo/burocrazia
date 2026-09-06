from __future__ import annotations

import pytest

from app import (
    confidence_label,
    display_category,
    display_title,
    explanation_status_label,
    recognition_result_state,
    select_explanation_for_display,
)
from src.models import (
    AdministrativeDocument,
    DocumentExplanation,
    RecognitionResult,
)


TIMESTAMP = "2026-08-04T12:00:00+00:00"


def document(title: str = "Documento di prova") -> AdministrativeDocument:
    return AdministrativeDocument(
        id=11,
        ente="INPS",
        codice="TEST-01",
        titolo_ufficiale=title,
        categoria="aree:convenzioni-internazionali",
        descrizione_ufficiale=None,
        significato_semplice=None,
        versione="1.0",
        data_rilevazione="2026-08-04",
        stato_verifica="da_verificare",
    )


def explanation(status: str) -> DocumentExplanation:
    return DocumentExplanation(
        id=1,
        document_id=11,
        official_summary="Sintesi dalla fonte.",
        simple_explanation="Spiegazione semplice.",
        intended_use="Uso generale.",
        possible_users=("Persona interessata",),
        facts_from_source=("Fatto dalla fonte.",),
        missing_information=("Informazione non presente.",),
        warnings=(),
        source_url="https://www.inps.it/it/it/moduli/test.html",
        source_access_date="2026-08-04",
        verification_status=status,
        verified_by="Revisore" if status == "verificato" else None,
        verified_at=(
            "2026-08-04T13:00:00+00:00" if status == "verificato" else None
        ),
        version="0.1",
        created_at=TIMESTAMP,
        updated_at=TIMESTAMP,
    )


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("verificato", "Spiegazione revisionata"),
        ("da_verificare", "Spiegazione preliminare non ancora revisionata"),
        ("bozza", "Spiegazione preliminare non ancora revisionata"),
        ("rifiutato", "Spiegazione non disponibile"),
        (None, "Spiegazione non disponibile"),
    ],
)
def test_explanation_status_is_translated_for_users(status, expected) -> None:
    assert explanation_status_label(status) == expected


@pytest.mark.parametrize(
    ("confidence", "expected"),
    [
        (100.0, "Punteggio interno: 100/100 (non è una probabilità di correttezza)"),
        (89.0, "Punteggio interno: 89/100 (non è una probabilità di correttezza)"),
        (70.0, "Punteggio interno: 70/100 (non è una probabilità di correttezza)"),
        (69.9, "Punteggio interno: 69.9/100 (non è una probabilità di correttezza)"),
    ],
)
def test_confidence_is_identified_as_an_uncalibrated_internal_score(
    confidence: float,
    expected: str,
) -> None:
    assert confidence_label(confidence) == expected


@pytest.mark.parametrize(
    ("category", "expected"),
    [
        (
            "aree:prestazioni-a-sostegno-del-reddito",
            "Prestazioni a sostegno del reddito",
        ),
        ("aree:convenzioni-internazionali", "Convenzioni internazionali"),
        ("attività_produttive", "Attività produttive"),
        (None, "Non disponibile"),
    ],
)
def test_technical_categories_are_normalized_for_display(category, expected) -> None:
    assert display_category(category) == expected


def test_bilingual_title_uses_only_the_italian_part_in_primary_display() -> None:
    title = "CERTIFICATO DI DISTACCO / CERTIFIKATË MBULIMI"

    assert display_title(title) == "CERTIFICATO DI DISTACCO"


def test_title_presentation_does_not_change_the_original_document() -> None:
    full_title = "CERTIFICATO DI DISTACCO / CERTIFIKATË MBULIMI"
    original = document(full_title)

    assert display_title(original.titolo_ufficiale) != original.titolo_ufficiale
    assert original.titolo_ufficiale == full_title


def test_rejected_explanation_is_not_selected_as_valid_content() -> None:
    rejected = explanation("rifiutato")
    result = RecognitionResult(True, 100.0, document())

    assert select_explanation_for_display([rejected]) is None
    assert recognition_result_state(result, [rejected]) == "riconosciuto_rifiutato"


def test_unknown_document_has_a_dedicated_experience_state() -> None:
    result = RecognitionResult(False, 42.0)

    assert recognition_result_state(result, []) == "non_riconosciuto"


def test_recognized_document_without_explanation_has_a_dedicated_state() -> None:
    result = RecognitionResult(True, 90.0, document())

    assert recognition_result_state(result, []) == "riconosciuto_senza_spiegazione"


def test_recognized_document_with_preliminary_explanation_has_a_dedicated_state() -> None:
    result = RecognitionResult(True, 90.0, document())

    assert recognition_result_state(result, [explanation("da_verificare")]) == (
        "riconosciuto_preliminare"
    )


def test_recognized_document_with_verified_explanation_has_a_dedicated_state() -> None:
    result = RecognitionResult(True, 90.0, document())

    assert recognition_result_state(result, [explanation("verificato")]) == (
        "riconosciuto_verificato"
    )
