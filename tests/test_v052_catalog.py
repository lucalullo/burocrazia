from __future__ import annotations

from src.catalog_metrics import format_catalog_status, get_catalog_metrics
from src.database import connect_database, initialize_database
from src.families import list_document_families
from src.models import AdministrativeDocument
from src.recognize import recognize_catalog


def test_v052_families_are_official_verified_and_recognizable(tmp_path) -> None:
    db_path = tmp_path / "families.db"
    initialize_database(db_path, seed_demo=True)
    with connect_database(db_path) as connection:
        families = list_document_families(connection)

    new_families = [
        family
        for family in families
        if family.ente
        in {
            "Ispettorato Nazionale del Lavoro",
            "Garante per la protezione dei dati personali",
        }
    ]
    result = recognize_catalog(
        "Ispettorato Nazionale del Lavoro - richiesta di intervento ispettivo, "
        "modulo INL 31 per l'Ispettorato territoriale del lavoro",
        [],
        families,
    )

    assert len(families) == 16
    assert len(new_families) == 3
    assert all(family.stato_verifica == "verificato" for family in new_families)
    assert all(family.official_url.startswith("https://") for family in new_families)
    assert result.match_type == "FAMILY_MATCH"
    assert result.family and result.family.nome == "Richiesta di intervento ispettivo"


def test_v052_document_match_keeps_priority_over_family_match(tmp_path) -> None:
    db_path = tmp_path / "precedence.db"
    initialize_database(db_path, seed_demo=True)
    with connect_database(db_path) as connection:
        families = list_document_families(connection)

    document = AdministrativeDocument(
        ente="Ispettorato Nazionale del Lavoro",
        codice="INL-31",
        titolo_ufficiale="Richiesta di intervento ispettivo",
        categoria="vigilanza",
        descrizione_ufficiale=None,
        significato_semplice=None,
        versione=None,
        data_rilevazione="2026-08-10",
        stato_verifica="da_verificare",
    )
    text = (
        "Ispettorato Nazionale del Lavoro - Richiesta di intervento ispettivo "
        "modulo INL-31 per l'Ispettorato territoriale del lavoro"
    )

    result = recognize_catalog(text, [document], families)

    assert result.match_type == "DOCUMENT_MATCH"
    assert result.document == document


def test_v052_catalog_status_has_document_coverage_heading(tmp_path) -> None:
    db_path = tmp_path / "metrics.db"
    initialize_database(db_path, seed_demo=True)
    with connect_database(db_path) as connection:
        output = format_catalog_status(get_catalog_metrics(connection))

    assert "COPERTURA DOCUMENTALE PER ENTE:" in output
    assert "CON IMPORTATORE AUTOMATICO: 7" in output
