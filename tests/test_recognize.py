from src.models import AdministrativeDocument
from src.recognize import (
    MIN_CONFIDENCE,
    normalize_text,
    recognize_catalog,
    recognize_document,
)


def catalog() -> list[AdministrativeDocument]:
    return [
        AdministrativeDocument(
            ente="Comune di Prova",
            codice="MOD-ABC-123",
            titolo_ufficiale="Richiesta di cambio di residenza",
            categoria="anagrafe",
            descrizione_ufficiale="Descrizione verificabile.",
            significato_semplice="Serve a comunicare un nuovo indirizzo.",
            versione="test",
            data_rilevazione="2026-08-04",
            stato_verifica="demo",
            parole_chiave=(
                "nuovo indirizzo",
                "dimora abituale",
                "dati anagrafici",
            ),
        ),
        AdministrativeDocument(
            ente="Ente Trasporti",
            codice="PAT-TEST-9",
            titolo_ufficiale="Domanda di rinnovo patente",
            categoria="motorizzazione",
            descrizione_ufficiale="Seconda descrizione.",
            significato_semplice="Riguarda una patente.",
            versione="test",
            data_rilevazione="2026-08-04",
            stato_verifica="demo",
            parole_chiave=("patente di guida", "rinnovo", "conducente"),
        ),
    ]


def test_normalization() -> None:
    assert normalize_text("  Cambio,  di RESIDENZA! ") == "cambio di residenza"


def test_recognition_by_exact_code() -> None:
    result = recognize_document("Riferimento pratica: MOD-ABC-123", catalog())

    assert result.recognized
    assert result.document is not None
    assert result.document.codice == "MOD-ABC-123"
    assert "codice esatto" in result.matched_signals


def test_recognition_by_title() -> None:
    result = recognize_document("Richiesta di cambio di residenza", catalog())

    assert result.recognized
    assert result.document is not None
    assert result.document.codice == "MOD-ABC-123"
    assert "titolo" in result.matched_signals


def test_recognition_by_keywords() -> None:
    text = "Nuovo indirizzo, dimora abituale e dati anagrafici del richiedente."
    result = recognize_document(text, catalog())

    assert result.recognized
    assert result.document is not None
    assert result.document.codice == "MOD-ABC-123"
    assert "parole chiave" in result.matched_signals


def test_unknown_document_is_rejected() -> None:
    result = recognize_document(
        "Programma musicale della festa di quartiere di sabato sera.",
        catalog(),
    )

    assert not result.recognized
    assert result.document is None


def test_sr211_inps_keeps_strong_document_match() -> None:
    document = AdministrativeDocument(
        ente="INPS",
        codice="SR211",
        titolo_ufficiale="Rinuncia dei beneficiari alla Carta Acquisti",
        categoria="prestazioni",
        descrizione_ufficiale=None,
        significato_semplice=None,
        versione=None,
        data_rilevazione="2026-08-10",
        stato_verifica="da_verificare",
    )

    result = recognize_catalog(
        "INPS SR211 Rinuncia dei beneficiari alla Carta Acquisti",
        [document],
        [],
    )

    assert result.match_type == "DOCUMENT_MATCH"
    assert result.document is document


def test_real_ade_title_and_entity_keep_document_match() -> None:
    document = AdministrativeDocument(
        ente="Agenzia delle Entrate",
        codice="730",
        titolo_ufficiale="730/2026",
        categoria="Dichiarazioni",
        descrizione_ufficiale=None,
        significato_semplice=None,
        versione="2026",
        data_rilevazione="2026-08-10",
        stato_verifica="da_verificare",
    )

    result = recognize_catalog(
        "Agenzia delle Entrate 730/2026",
        [document],
        [],
    )

    assert result.match_type == "DOCUMENT_MATCH"
    assert result.document is document


def test_minimum_threshold_is_respected() -> None:
    text = "Richiesta di cambio di residenza"

    assert recognize_document(
        text,
        catalog(),
        min_confidence=MIN_CONFIDENCE,
    ).recognized
    assert not recognize_document(
        text,
        catalog(),
        min_confidence=95.0,
    ).recognized


def test_confidence_is_always_between_zero_and_one_hundred() -> None:
    texts = (
        "testo casuale",
        "MOD-ABC-123 Comune di Prova Richiesta di cambio di residenza "
        "nuovo indirizzo dimora abituale dati anagrafici",
    )

    for text in texts:
        result = recognize_document(text, catalog())
        assert 0.0 <= result.confidence <= 100.0
