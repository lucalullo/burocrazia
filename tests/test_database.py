from __future__ import annotations

from datetime import UTC, datetime

from src.database import (
    connect_database,
    create_schema,
    get_document,
    initialize_database,
    insert_document,
    list_documents,
)
from src.explanations import create_explanation, get_explanation
from src.models import AdministrativeDocument, DocumentExplanation


def test_init_script_distinguishes_total_documents_from_demo(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    from scripts import init_db as init_db_script

    db_path = tmp_path / "init-script.db"
    monkeypatch.setattr(init_db_script, "DEFAULT_DB_PATH", db_path)

    init_db_script.main()

    output = capsys.readouterr().out
    assert "399 documenti, di cui 10 demo" in output


def sample_document() -> AdministrativeDocument:
    return AdministrativeDocument(
        ente="Ente di prova",
        codice="TEST-01",
        titolo_ufficiale="Documento di prova",
        categoria="test",
        descrizione_ufficiale="Descrizione di prova.",
        significato_semplice="Significato semplice di prova.",
        fonte_url=None,
        download_url=None,
        versione="test",
        data_rilevazione="2026-08-04",
        stato_verifica="demo",
        parole_chiave=("prova", "documento"),
    )


def sample_explanation(document_id: int) -> DocumentExplanation:
    timestamp = datetime.now(UTC).replace(microsecond=0).isoformat()
    return DocumentExplanation(
        document_id=document_id,
        official_summary="Sintesi dalla fonte.",
        simple_explanation="Spiegazione semplice separata.",
        intended_use=None,
        possible_users=(),
        facts_from_source=("Fatto verificabile dalla fonte.",),
        missing_information=(),
        warnings=(),
        source_url="https://www.inps.it/it/it/moduli/test.html",
        source_access_date="2026-08-04",
        verification_status="da_verificare",
        verified_by=None,
        verified_at=None,
        version="0.1",
        created_at=timestamp,
        updated_at=timestamp,
    )


def test_database_schema(tmp_path) -> None:
    db_path = tmp_path / "schema.db"
    with connect_database(db_path) as connection:
        create_schema(connection)
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(documents)").fetchall()
        }

    assert {
        "id",
        "ente",
        "codice",
        "titolo_ufficiale",
        "categoria",
        "descrizione_ufficiale",
        "significato_semplice",
        "fonte_url",
        "download_url",
        "detail_url",
        "data_pubblicazione",
        "versione",
        "data_rilevazione",
        "stato_verifica",
        "parole_chiave",
        "source_id",
    } <= columns


def test_insert_and_retrieve_document(tmp_path) -> None:
    db_path = tmp_path / "documents.db"
    with connect_database(db_path) as connection:
        create_schema(connection)
        document_id = insert_document(connection, sample_document())
        recovered = get_document(connection, document_id)

    assert recovered is not None
    assert recovered.id == document_id
    assert recovered.codice == "TEST-01"
    assert recovered.parole_chiave == ("prova", "documento")


def test_import_metadata_can_be_null(tmp_path) -> None:
    db_path = tmp_path / "nullable.db"
    with connect_database(db_path) as connection:
        create_schema(connection)
        document_id = insert_document(
            connection,
            AdministrativeDocument(
                ente="INPS",
                codice=None,
                titolo_ufficiale="Modulo reale senza metadati facoltativi",
                categoria=None,
                descrizione_ufficiale=None,
                significato_semplice=None,
                versione=None,
                data_rilevazione="2026-08-04",
                stato_verifica="da_verificare",
            ),
        )
        recovered = get_document(connection, document_id)

    assert recovered is not None
    assert recovered.categoria is None
    assert recovered.descrizione_ufficiale is None
    assert recovered.significato_semplice is None
    assert recovered.versione is None


def test_demo_initialization_is_idempotent(tmp_path) -> None:
    db_path = tmp_path / "demo.db"

    assert initialize_database(db_path, seed_demo=True) == 10
    assert initialize_database(db_path, seed_demo=True) == 0

    with connect_database(db_path) as connection:
        documents = list_documents(connection)

    assert len(documents) == 10
    assert {document.stato_verifica for document in documents} == {"demo"}
    assert all(document.fonte_url is None for document in documents)


def test_v041_migration_is_idempotent_and_preserves_existing_data(tmp_path) -> None:
    db_path = tmp_path / "migration.db"
    initialize_database(db_path, seed_demo=True)
    with connect_database(db_path) as connection:
        document = list_documents(connection)[0]
        explanation_id, _ = create_explanation(
            connection,
            sample_explanation(document.id),
        )
        connection.execute(
            "ALTER TABLE document_explanations DROP COLUMN review_notes"
        )
        connection.commit()

    assert initialize_database(db_path, seed_demo=True) == 0
    assert initialize_database(db_path, seed_demo=True) == 0

    with connect_database(db_path) as connection:
        columns = [
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(document_explanations)"
            ).fetchall()
        ]
        recovered = get_explanation(connection, explanation_id)
        document_count = connection.execute(
            "SELECT COUNT(*) FROM documents"
        ).fetchone()[0]

    assert columns.count("review_notes") == 1
    assert recovered is not None
    assert recovered.simple_explanation == "Spiegazione semplice separata."
    assert recovered.review_notes is None
    assert document_count == 10


def test_explanations_foreign_key_is_valid_and_cascades_on_document_delete(
    tmp_path,
) -> None:
    db_path = tmp_path / "foreign-key.db"
    initialize_database(db_path, seed_demo=False)
    with connect_database(db_path) as connection:
        document_id = insert_document(connection, sample_document())
        explanation_id, _ = create_explanation(
            connection,
            sample_explanation(document_id),
        )
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []

        connection.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        connection.commit()

        assert get_explanation(connection, explanation_id) is None
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
