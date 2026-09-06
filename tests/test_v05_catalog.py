from __future__ import annotations

from pathlib import Path

import pytest

from src.catalog_metrics import (
    catalog_summary,
    format_catalog_status,
    get_catalog_metrics,
)
from src.database import (
    connect_database,
    initialize_database,
    insert_document,
    list_documents,
)
from src.entities import list_entities, upsert_entity
from src.families import list_document_families
from src.models import AdministrativeDocument, Entity
from src.provenance import get_document_provenance
from src.recognize import recognize_catalog, recognize_document
from src.sources import search_sources_by_ente


FIXTURE = Path(__file__).parent / "fixtures" / "cartella_pagamento_anonimizzata.txt"


def anonymized_cartella_text() -> str:
    return FIXTURE.read_text(encoding="utf-8")


def test_v05_schema_contains_entities_families_and_provenance(tmp_path) -> None:
    db_path = tmp_path / "schema-v05.db"
    initialize_database(db_path, seed_demo=True)
    with connect_database(db_path) as connection:
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        entity_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(entities)").fetchall()
        }
        family_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(document_families)"
            ).fetchall()
        }

    assert {"entities", "document_families", "document_provenance"} <= tables
    assert {"codice_ipa", "stato_catalogazione", "last_checked_at"} <= entity_columns
    assert {"keywords", "identifying_phrases", "official_url"} <= family_columns


def test_cartella_family_is_seeded_idempotently_with_structural_phrases(tmp_path) -> None:
    db_path = tmp_path / "family.db"
    initialize_database(db_path, seed_demo=True)
    initialize_database(db_path, seed_demo=True)
    with connect_database(db_path) as connection:
        families = list_document_families(connection)

    assert len(families) == 16
    family = next(item for item in families if item.nome == "Cartella di pagamento")
    assert family.nome == "Cartella di pagamento"
    assert family.ente == "Agenzia delle Entrate-Riscossione"
    assert family.identifying_phrases == (
        "cartella di pagamento",
        "agenzia delle entrate-riscossione",
        "agente della riscossione",
    )
    assert family.stato_verifica == "verificato"


def test_anonymized_cartella_matches_family_but_not_exact_document(tmp_path) -> None:
    db_path = tmp_path / "family-match.db"
    initialize_database(db_path, seed_demo=True)
    with connect_database(db_path) as connection:
        documents = list_documents(connection)
        families = list_document_families(connection)

    exact = recognize_document(anonymized_cartella_text(), documents)
    result = recognize_catalog(anonymized_cartella_text(), documents, families)

    assert not exact.recognized
    assert result.match_type == "FAMILY_MATCH"
    assert result.document is None
    assert result.family is not None
    assert result.family.nome == "Cartella di pagamento"
    assert result.family.ente == "Agenzia delle Entrate-Riscossione"
    assert result.confidence_family >= 75
    assert result.confidence_document < result.confidence_family


def test_v0531_cartella_rejects_weak_cupe_candidate_from_wrong_entity(
    tmp_path,
) -> None:
    db_path = tmp_path / "cupe-regression.db"
    initialize_database(db_path, seed_demo=True)
    with connect_database(db_path) as connection:
        families = list_document_families(connection)

    documents = [
        AdministrativeDocument(
            ente="Agenzia delle Entrate",
            codice=None,
            titolo_ufficiale="Cupe",
            categoria="Dichiarazioni",
            descrizione_ufficiale=None,
            significato_semplice=None,
            versione="2020",
            data_rilevazione="2026-08-10",
            stato_verifica="da_verificare",
        ),
        AdministrativeDocument(
            ente="Agenzia delle Entrate",
            codice=None,
            titolo_ufficiale="Modulo di pagamento Cupe",
            categoria="Dichiarazioni",
            descrizione_ufficiale=None,
            significato_semplice=None,
            versione="2020",
            data_rilevazione="2026-08-10",
            stato_verifica="da_verificare",
        ),
    ]

    result = recognize_catalog(anonymized_cartella_text(), documents, families)

    assert result.match_type == "FAMILY_MATCH"
    assert result.document is None
    assert result.family is not None
    assert result.family.nome == "Cartella di pagamento"
    assert result.family.ente == "Agenzia delle Entrate-Riscossione"


def test_exact_document_match_has_priority_over_family_match(tmp_path) -> None:
    db_path = tmp_path / "exact-priority.db"
    initialize_database(db_path, seed_demo=True)
    with connect_database(db_path) as connection:
        source = search_sources_by_ente(
            connection, "Agenzia delle Entrate-Riscossione"
        )[0]
        insert_document(
            connection,
            AdministrativeDocument(
                ente="Agenzia delle Entrate-Riscossione",
                codice="ADER-EXACT-01",
                titolo_ufficiale="Cartella di pagamento catalogata",
                categoria="riscossione",
                descrizione_ufficiale=None,
                significato_semplice=None,
                versione=None,
                data_rilevazione="2026-08-05",
                stato_verifica="da_verificare",
                source_id=source.id,
            ),
        )
        documents = list_documents(connection)
        families = list_document_families(connection)

    text = f"ADER-EXACT-01\n{anonymized_cartella_text()}"
    result = recognize_catalog(text, documents, families)

    assert result.match_type == "DOCUMENT_MATCH"
    assert result.document is not None
    assert result.document.codice == "ADER-EXACT-01"
    assert result.confidence_document >= 75
    assert result.confidence_family >= 75
    assert result.document_signals


def test_one_generic_family_phrase_is_not_enough(tmp_path) -> None:
    db_path = tmp_path / "prudent-family.db"
    initialize_database(db_path, seed_demo=True)
    with connect_database(db_path) as connection:
        families = list_document_families(connection)

    result = recognize_catalog("È presente una cartella di pagamento.", [], families)

    assert result.match_type == "NO_MATCH"
    assert result.family is None


@pytest.mark.parametrize(
    ("expected_family", "text"),
    (
        (
            "Modulo di pagamento pagoPA",
            """Agenzia delle Entrate-Riscossione
            Modulo di pagamento pagoPA
            Nuovo modulo di pagamento pagoPA""",
        ),
        (
            "Accertamento esecutivo",
            """Agenzia delle Entrate-Riscossione
            Accertamento esecutivo
            Avviso di accertamento esecutivo
            Avviso di presa in carico""",
        ),
        (
            "Avviso di addebito INPS",
            """Agenzia delle Entrate-Riscossione
            Avviso di addebito INPS
            Avviso di addebito
            Crediti previdenziali""",
        ),
    ),
)
def test_new_ader_families_are_recognized_prudently(
    tmp_path, expected_family: str, text: str
) -> None:
    db_path = tmp_path / f"{expected_family}.db"
    initialize_database(db_path, seed_demo=True)
    with connect_database(db_path) as connection:
        families = list_document_families(connection)

    result = recognize_catalog(text, [], families)

    assert result.match_type == "FAMILY_MATCH"
    assert result.family is not None
    assert result.family.nome == expected_family
    assert result.confidence_family >= 75


def test_anonymized_fixture_contains_no_real_personal_or_payment_codes() -> None:
    text = anonymized_cartella_text().casefold()

    assert "codice fiscale" not in text
    assert "cbill" not in text
    assert "importo" not in text
    assert "numero cartella" not in text
    assert "qr" not in text


def test_catalog_metrics_use_real_database_counts(tmp_path) -> None:
    db_path = tmp_path / "metrics.db"
    initialize_database(db_path, seed_demo=True)
    with connect_database(db_path) as connection:
        upsert_entity(
            connection,
            Entity(
                codice_ipa="ente_test",
                denominazione="Ente di test",
                categoria=None,
                livello=None,
                sito_istituzionale=None,
            ),
        )
        source = search_sources_by_ente(connection, "INPS")[0]
        insert_document(
            connection,
            AdministrativeDocument(
                ente="INPS",
                codice="REAL-01",
                titolo_ufficiale="Documento reale di test",
                categoria=None,
                descrizione_ufficiale=None,
                significato_semplice=None,
                versione=None,
                data_rilevazione="2026-08-05",
                stato_verifica="da_verificare",
                source_id=source.id,
            ),
        )
        metrics = get_catalog_metrics(connection)
        output = format_catalog_status(metrics)

    assert metrics.entities == 1
    assert metrics.entities_with_site == 0
    assert metrics.entities_analyzed == 0
    assert metrics.entities_not_analyzed == 1
    assert metrics.verified_sources == 15
    assert metrics.sources_with_importer == 8
    assert metrics.automatic_sources == 7
    assert metrics.manual_sources == 1
    assert metrics.blocked_sources == 1
    assert metrics.documents_total == 11
    assert metrics.documents_real == 1
    assert metrics.documents_demo == 10
    assert metrics.pending == 1
    assert metrics.families == 16
    assert "CENSITI: 1" in output
    assert "TOTALI: 16" in output
    assert "INPS: 1" in output


def test_catalog_dashboard_summary_is_separate_from_ipa_inventory(tmp_path) -> None:
    db_path = tmp_path / "summary.db"
    initialize_database(db_path, seed_demo=True)
    with connect_database(db_path) as connection:
        documents = list_documents(connection)
        families = list_document_families(connection)

    summary = catalog_summary(documents, families)

    assert summary.real_documents == 0
    assert summary.covered_entities == 0
    assert summary.families == 16
    assert summary.pending == 0


def test_v05_migration_is_non_destructive_and_backfills_provenance(tmp_path) -> None:
    db_path = tmp_path / "migration-v05.db"
    initialize_database(db_path, seed_demo=True)
    with connect_database(db_path) as connection:
        source = search_sources_by_ente(connection, "INPS")[0]
        document_id = insert_document(
            connection,
            AdministrativeDocument(
                ente="INPS",
                codice="LEGACY-REAL",
                titolo_ufficiale="Documento reale preesistente",
                categoria=None,
                descrizione_ufficiale=None,
                significato_semplice=None,
                versione=None,
                data_rilevazione="2026-08-04",
                stato_verifica="da_verificare",
                fonte_url="https://www.inps.it/it/it/moduli.html",
                source_id=source.id,
            ),
        )
        before = len(list_documents(connection))

    initialize_database(db_path, seed_demo=True)
    initialize_database(db_path, seed_demo=True)
    with connect_database(db_path) as connection:
        after = len(list_documents(connection))
        provenance = get_document_provenance(connection, document_id)
        sources = connection.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
        families = connection.execute(
            "SELECT COUNT(*) FROM document_families"
        ).fetchone()[0]
        entities = list_entities(connection)

    assert before == after == 11
    assert sources == 15
    assert families == 16
    assert entities == []
    assert provenance is not None
    assert provenance.acquisition_method == "legacy_import"
