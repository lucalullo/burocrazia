from app import document_to_display_row
from src.models import AdministrativeDocument


def test_imported_document_display_distinguishes_real_data_and_nulls() -> None:
    document = AdministrativeDocument(
        ente="INPS",
        codice="AP17",
        titolo_ufficiale="Modulo INPS",
        categoria=None,
        descrizione_ufficiale=None,
        significato_semplice=None,
        versione=None,
        data_rilevazione="2026-08-04",
        stato_verifica="da_verificare",
        detail_url="https://www.inps.it/it/it/moduli/ap17.html",
        data_pubblicazione=None,
        source_id=2,
    )

    row = document_to_display_row(document)

    assert row["Tipo record"] == "Reale importato"
    assert row["Categoria"] == "Non disponibile"
    assert row["Stato"] == "Da verificare"
    assert row["Fonte"] == "https://www.inps.it/it/it/moduli/ap17.html"
    assert row["Data pubblicazione"] == "Non disponibile"


def test_demo_document_display_is_explicit() -> None:
    document = AdministrativeDocument(
        ente="INPS",
        codice="DEMO",
        titolo_ufficiale="Documento demo",
        categoria="demo",
        descrizione_ufficiale="Demo",
        significato_semplice="Demo",
        versione="demo",
        data_rilevazione="2026-08-04",
        stato_verifica="demo",
    )

    assert document_to_display_row(document)["Tipo record"] == "Demo"
