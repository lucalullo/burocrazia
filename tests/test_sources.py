from dataclasses import replace

from app import source_to_display_row
from src.database import (
    connect_database,
    create_schema,
    get_document,
    initialize_database,
    insert_document,
)
from src.models import AdministrativeDocument, OfficialSource
from src.sources import (
    filter_sources_by_status,
    get_source,
    insert_source,
    list_active_sources,
    list_sources,
    search_sources_by_ambito,
    search_sources_by_ente,
    update_source,
)


def sample_source(
    *,
    ente: str = "Ente di prova",
    nome_fonte: str = "Fonte di prova",
    ambito: str = "generale",
    stato_verifica: str = "da_verificare",
    attiva: bool = True,
) -> OfficialSource:
    return OfficialSource(
        ente=ente,
        nome_fonte=nome_fonte,
        tipo_ente="altro ente pubblico",
        livello="nazionale",
        ambito=ambito,
        url_principale=None,
        url_modulistica=None,
        metodo_acquisizione="manuale",
        stato_verifica=stato_verifica,
        data_verifica=None,
        note="Dato usato dai test.",
        attiva=attiva,
    )


def test_sources_table_creation(tmp_path) -> None:
    with connect_database(tmp_path / "sources.db") as connection:
        create_schema(connection)
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(sources)").fetchall()
        }

    assert {
        "id",
        "ente",
        "nome_fonte",
        "tipo_ente",
        "livello",
        "ambito",
        "url_principale",
        "url_modulistica",
        "metodo_acquisizione",
        "stato_verifica",
        "coverage_status",
        "data_verifica",
        "note",
        "attiva",
    } <= columns


def test_insert_and_retrieve_source(tmp_path) -> None:
    with connect_database(tmp_path / "source.db") as connection:
        create_schema(connection)
        source_id = insert_source(connection, sample_source())
        recovered = get_source(connection, source_id)

    assert recovered is not None
    assert recovered.id == source_id
    assert recovered.ente == "Ente di prova"
    assert recovered.attiva
    assert recovered.url_principale is None
    assert recovered.url_modulistica is None
    assert recovered.coverage_status == "da_valutare"


def test_update_source(tmp_path) -> None:
    with connect_database(tmp_path / "update.db") as connection:
        create_schema(connection)
        source_id = insert_source(connection, sample_source())
        original = get_source(connection, source_id)
        assert original is not None

        changed = replace(
            original,
            stato_verifica="verificato",
            data_verifica="2026-08-04",
            url_principale="https://istituzionale.example.test/",
            url_modulistica="https://istituzionale.example.test/moduli",
        )
        assert update_source(connection, changed)
        recovered = get_source(connection, source_id)

    assert recovered is not None
    assert recovered.stato_verifica == "verificato"
    assert recovered.data_verifica == "2026-08-04"
    assert recovered.url_principale == "https://istituzionale.example.test/"
    assert recovered.url_modulistica == "https://istituzionale.example.test/moduli"


def test_search_sources_by_ente(tmp_path) -> None:
    with connect_database(tmp_path / "ente.db") as connection:
        create_schema(connection)
        insert_source(connection, sample_source(ente="INPS", nome_fonte="Fonte INPS"))
        insert_source(connection, sample_source(ente="INAIL", nome_fonte="Fonte INAIL"))
        matches = search_sources_by_ente(connection, "inps")

    assert [source.ente for source in matches] == ["INPS"]


def test_search_sources_by_ambito(tmp_path) -> None:
    with connect_database(tmp_path / "ambito.db") as connection:
        create_schema(connection)
        insert_source(connection, sample_source(nome_fonte="Fonte fiscale", ambito="fiscale"))
        insert_source(connection, sample_source(nome_fonte="Fonte lavoro", ambito="lavoro"))
        matches = search_sources_by_ambito(connection, "FISCALE")

    assert len(matches) == 1
    assert matches[0].ambito == "fiscale"


def test_filter_sources_by_status(tmp_path) -> None:
    with connect_database(tmp_path / "status.db") as connection:
        create_schema(connection)
        insert_source(connection, sample_source(nome_fonte="Fonte verificata", stato_verifica="verificato"))
        insert_source(connection, sample_source(nome_fonte="Fonte da verificare"))
        matches = filter_sources_by_status(connection, "verificato")

    assert len(matches) == 1
    assert matches[0].nome_fonte == "Fonte verificata"


def test_list_active_sources(tmp_path) -> None:
    with connect_database(tmp_path / "active.db") as connection:
        create_schema(connection)
        insert_source(connection, sample_source(nome_fonte="Fonte attiva"))
        insert_source(connection, sample_source(nome_fonte="Fonte inattiva", attiva=False))
        matches = list_active_sources(connection)

    assert [source.nome_fonte for source in matches] == ["Fonte attiva"]


def test_document_can_reference_source(tmp_path) -> None:
    with connect_database(tmp_path / "relation.db") as connection:
        create_schema(connection)
        source_id = insert_source(connection, sample_source())
        document_id = insert_document(
            connection,
            AdministrativeDocument(
                ente="Ente di prova",
                codice="DOC-SOURCE-01",
                titolo_ufficiale="Documento collegato",
                categoria="generale",
                descrizione_ufficiale="Descrizione di prova.",
                significato_semplice="Significato di prova.",
                versione="test",
                data_rilevazione="2026-08-04",
                stato_verifica="demo",
                parole_chiave=("collegamento",),
                source_id=source_id,
            ),
        )
        recovered = get_document(connection, document_id)

    assert recovered is not None
    assert recovered.source_id == source_id


def test_initial_registry_is_idempotent(tmp_path) -> None:
    db_path = tmp_path / "initial.db"

    initialize_database(db_path, seed_demo=True)
    initialize_database(db_path, seed_demo=True)
    with connect_database(db_path) as connection:
        sources = list_sources(connection)

    assert len(sources) == 15
    assert {source.stato_verifica for source in sources} == {"verificato"}
    assert {source.data_verifica for source in sources} == {
        "2026-08-04",
        "2026-08-05",
        "2026-08-10",
    }
    assert all(source.url_principale is not None for source in sources)
    assert sum(source.url_modulistica is not None for source in sources) == 12
    coverage = {source.ente: source.coverage_status for source in sources}
    assert coverage["Ispettorato Nazionale del Lavoro"] == (
        "completa_rispetto_alla_fonte"
    )
    assert coverage["Garante per la protezione dei dati personali"] == (
        "completa_rispetto_alla_fonte"
    )
    assert coverage["Agenzia delle Entrate-Riscossione"] == "bloccata"


def test_source_display_row_preserves_urls_as_text_and_missing_values() -> None:
    source = replace(
        sample_source(stato_verifica="verificato"),
        url_principale="https://istituzionale.example.test/",
        url_modulistica=None,
        data_verifica="2026-08-04",
    )

    row = source_to_display_row(source)

    assert row["URL principale"] == "https://istituzionale.example.test/"
    assert row["URL modulistica"] == "Non disponibile"
    assert row["Stato verifica"] == "verificato"
    assert row["Copertura"] == "da_valutare"
    assert row["Data verifica"] == "04/08/2026"
