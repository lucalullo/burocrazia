"""Functional UI checks with Streamlit AppTest, entirely local and synthetic."""
from __future__ import annotations

import hashlib
from types import SimpleNamespace

import pytest
from streamlit.testing.v1 import AppTest

import app
from src.database import connect_database, initialize_database, insert_document
from src.explanations import create_explanation, get_explanation, list_explanations, list_review_events
from src.extract import ExtractionResult
from src.local_resources import create_local_resources_table
from src.models import AdministrativeDocument, DocumentExplanation
from src.offline import blocked_attempts
from src.review import submit_explanation_review

URL = "https://www.inps.it/it/it/moduli/test-ui.html"
HOSTILE_TEXT = "Testo sintetico https://example.invalid [vai](https://example.invalid) ![remota](https://example.invalid/p.png) <iframe src='https://example.invalid'></iframe>"


@pytest.fixture
def ui_catalog(tmp_path, monkeypatch):
    path = tmp_path / "ui.sqlite3"
    initialize_database(path, seed_demo=True)
    with connect_database(path) as connection:
        source_id = connection.execute("SELECT id FROM sources WHERE ente = 'INPS'").fetchone()[0]
        document_id = insert_document(connection, AdministrativeDocument(
            ente="INPS", codice="TEST-UI-01", titolo_ufficiale="Documento sintetico di prova della consultazione locale",
            categoria="prove", descrizione_ufficiale="Metadati sintetici di una fixture di test.",
            significato_semplice=None, versione=None, data_rilevazione="2026-09-01",
            stato_verifica="da_verificare", fonte_url=URL, detail_url=URL, source_id=source_id,
        ))
        explanation_id, _ = create_explanation(connection, DocumentExplanation(
            document_id=document_id, official_summary="Sintesi registrata di prova.", simple_explanation=HOSTILE_TEXT,
            intended_use="Solo verifiche sintetiche dell'interfaccia.", possible_users=("Collaudatore sintetico",),
            facts_from_source=("Fatto sintetico registrato nel catalogo di prova.",), missing_information=(), warnings=(),
            source_url=URL, source_access_date="2026-09-01", verification_status="da_verificare", version="1.0",
            created_at="2026-09-01T10:00:00+00:00", updated_at="2026-09-01T10:00:00+00:00",
        ))
    monkeypatch.setattr(app, "DEFAULT_DB_PATH", path)
    return SimpleNamespace(path=path, document_id=document_id, explanation_id=explanation_id, source_id=source_id)


def start_ui() -> AppTest:
    return AppTest.from_string("import app\napp.main()", default_timeout=15).run()


def assert_no_active_external_content(at: AppTest) -> None:
    assert not at.exception
    assert not at.get("link_button")
    assert not at.get("iframe")
    assert not at.get("imgs")
    for element in [*at.markdown, *at.caption, *at.info, *at.warning, *at.error, *at.success]:
        assert "https://" not in element.value
        assert "<iframe" not in element.value
        assert "![" not in element.value


def upload(monkeypatch, content: bytes, filename: str = "sintetico.txt", mime: str = "text/plain") -> None:
    value = SimpleNamespace(name=filename, size=len(content), type=mime, getvalue=lambda: content)
    monkeypatch.setattr(app.st, "file_uploader", lambda *args, **kwargs: value)


def test_four_areas_and_filters_work_without_network(ui_catalog):
    previous_attempts = len(blocked_attempts)
    at = start_ui()
    assert at.radio(key="main_navigation").options == [app.NAVIGATION_LABELS[area] for area in app.NAVIGATION_AREAS]
    for area in app.NAVIGATION_AREAS:
        at.radio(key="main_navigation").set_value(area).run()
        assert not at.error
        assert_no_active_external_content(at)
    at.radio(key="main_navigation").set_value("Catalogo").run()
    at.text_input(key="catalog_search").set_value("TEST-UI-01").run()
    assert len(at.dataframe[0].value) == 1
    assert at.selectbox(key="catalog_document").value == ui_catalog.document_id
    at.text_input(key="catalog_search").set_value("nessun documento con questa stringa").run()
    assert any("Nessun documento" in element.value for element in at.info)
    assert len(blocked_attempts) == previous_attempts


def test_preliminary_explanation_stays_in_editor_only(ui_catalog):
    at = start_ui().radio(key="main_navigation").set_value("Catalogo").run()
    at.text_input(key="catalog_search").set_value("TEST-UI-01").run()
    assert any(app.PRELIMINARY_EXPLANATION_MESSAGE == element.value for element in at.warning)
    assert all(HOSTILE_TEXT not in element.value for element in at.text)
    at.radio(key="main_navigation").set_value("Revisione").run()
    assert at.text_area(key=f"simple_explanation_{ui_catalog.explanation_id}").value == HOSTILE_TEXT
    assert_no_active_external_content(at)


def test_verified_editorial_urls_render_as_inert_text(ui_catalog):
    submit_explanation_review(ui_catalog.explanation_id, "verificato", "Revisore di prova", source_confirmed=True, db_path=ui_catalog.path)
    at = start_ui().radio(key="main_navigation").set_value("Catalogo").run()
    at.text_input(key="catalog_search").set_value("TEST-UI-01").run()
    assert HOSTILE_TEXT in [element.value for element in at.text]
    assert URL in [element.value for element in at.text]
    assert any(app.VERIFIED_EXPLANATION_MESSAGE == element.value for element in at.success)
    assert_no_active_external_content(at)


def test_oversized_upload_is_rejected_before_reading(ui_catalog, monkeypatch):
    def forbidden_read():
        pytest.fail("Oversized upload must not be copied or parsed")
    uploaded = SimpleNamespace(name="eccessivo.txt", size=app.MAX_UPLOAD_BYTES + 1, type="text/plain", getvalue=forbidden_read)
    monkeypatch.setattr(app.st, "file_uploader", lambda *args, **kwargs: uploaded)
    at = start_ui()
    assert not at.exception
    assert any("limite" in element.value for element in at.text)
    assert not any("Documento non riconosciuto" == element.value for element in at.header)


def test_corrupt_image_is_an_extraction_error_not_no_match(ui_catalog, monkeypatch):
    upload(monkeypatch, b"not a PNG", "corrotta.png", "image/png")
    at = start_ui()
    assert not at.exception
    assert any("Impossibile acquisire" in element.value for element in at.warning)
    assert not any("Documento non riconosciuto" == element.value for element in at.header)


def test_text_upload_identifies_document_without_creating_catalog_rows(ui_catalog, monkeypatch):
    upload(monkeypatch, b"INPS TEST-UI-01 Documento sintetico di prova della consultazione locale versione 2026.")
    with connect_database(ui_catalog.path) as connection:
        before = connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    at = start_ui()
    assert not at.exception
    assert any("Documento riconosciuto" == element.value for element in at.header)
    assert any("Esito: DOCUMENT_MATCH" == element.value for element in at.text)
    assert any("non è una probabilità" in element.value for element in at.text)
    with connect_database(ui_catalog.path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == before
    assert_no_active_external_content(at)


def test_unknown_upload_has_no_specific_explanation(ui_catalog, monkeypatch):
    content = "Testo narrativo sintetico senza indizi amministrativi: passeggiata nel bosco fra alberi e ruscelli. " + HOSTILE_TEXT
    upload(monkeypatch, content.encode())
    at = start_ui()
    assert any("Documento non riconosciuto" == element.value for element in at.header)
    assert any("Esito: NO_MATCH" == element.value for element in at.text)
    assert not any("Che cos'è" == element.value for element in at.subheader)
    assert_no_active_external_content(at)


def test_partial_extraction_coverage_is_visible(ui_catalog, monkeypatch):
    upload(monkeypatch, b"fixture")
    monkeypatch.setattr(app, "extract_document", lambda *args, **kwargs: ExtractionResult(
        text="INPS TEST-UI-01 Documento sintetico di prova della consultazione locale versione 2026.",
        method="pdf_mixed", used_ocr=True, pages_processed=5, total_pages=12, ocr_pages=2,
        warning="Sette pagine non sono state lette.",
    ))
    at = start_ui()
    assert not at.exception
    assert "Pagine lette: 5/12; pagine lette tramite OCR: 2." in [element.value for element in at.text]
    assert "Sette pagine non sono state lette." in [element.value for element in at.text]
    assert any("Lettura parziale" in element.value for element in at.warning)


def test_reset_discards_session_fields_and_changes_upload_widget(ui_catalog):
    at = start_ui()
    at.session_state["private_result"] = "Testo personale sintetico da rimuovere"
    at.session_state["private_filename"] = "persona-sintetica.txt"
    at.button(key="reset_session").click().run()
    assert not at.exception
    assert "private_result" not in at.session_state
    assert "private_filename" not in at.session_state
    assert at.session_state["upload_generation"] == 1
    assert any(element.value == "Sessione ripulita." for element in at.success)
    uploader = at.get("file_uploader")[0]
    assert uploader.proto.id.endswith("document_upload_1")


def test_editor_blocks_unsaved_verification_and_records_new_version(ui_catalog):
    identifier = ui_catalog.explanation_id
    at = start_ui().radio(key="main_navigation").set_value("Revisione").run()
    at.text_input(key=f"explanation_reviewer_{identifier}").set_value("Revisore sintetico")
    at.checkbox(key=f"source_confirmed_{identifier}").check()
    at.text_area(key=f"simple_explanation_{identifier}").set_value("Nuova spiegazione sintetica di prova.").run()
    assert at.button(key=f"verify_{identifier}").disabled
    at.button(key=f"save_editorial_{identifier}").click().run()
    assert not at.exception
    at.checkbox(key=f"source_confirmed_{identifier}").check().run()
    assert not at.button(key=f"verify_{identifier}").disabled
    at.button(key=f"verify_{identifier}").click().run()
    assert at.text_area(key=f"simple_explanation_{identifier}").disabled
    assert at.button(key=f"reject_{identifier}").disabled
    at.text_area(key=f"review_notes_{identifier}").set_value("Ritiro motivato di una fixture già verificata.").run()
    at.button(key=f"reject_{identifier}").click().run()
    assert at.text_area(key=f"simple_explanation_{identifier}").disabled
    at.text_input(key=f"new_version_{identifier}").set_value("2.0").run()
    at.button(key=f"create_revision_{identifier}").click().run()
    assert not at.exception
    with connect_database(ui_catalog.path) as connection:
        original = get_explanation(connection, identifier)
        versions = list_explanations(connection)
        events = list_review_events(connection)
    assert original.verification_status == "rifiutato"
    draft = next(item for item in versions if item.version == "2.0")
    assert draft.verification_status == "bozza"
    assert at.selectbox(key="explanation_review_selection").value == draft.id
    assert not at.text_area(key=f"simple_explanation_{draft.id}").disabled
    assert any(event["new_status"] == "verificato" for event in events)
    assert any(event["new_status"] == "rifiutato" for event in events)
    assert any(event["decision"] == "nuova_versione" for event in events)
    assert_no_active_external_content(at)


def test_first_draft_is_created_without_generated_explanation(ui_catalog):
    at = start_ui().radio(key="main_navigation").set_value("Revisione").run()
    at.text_input(key="new_explanation_version").set_value("3.0")
    at.text_input(key="new_explanation_author").set_value("Autore sintetico")
    at.text_input(key="new_explanation_access_date").set_value("2026-09-01").run()
    at.button(key="create_first_draft").click().run()
    assert not at.exception
    with connect_database(ui_catalog.path) as connection:
        draft = next(item for item in list_explanations(connection) if item.version == "3.0")
    assert draft.verification_status == "bozza"
    assert draft.simple_explanation is None
    assert at.selectbox(key="explanation_review_selection").value == draft.id


def test_local_material_is_hash_checked_and_rendered_as_text(ui_catalog, tmp_path, monkeypatch):
    from src import local_resources
    resource_root = tmp_path / "resources"
    resource_root.mkdir()
    content = HOSTILE_TEXT.encode()
    (resource_root / "fixture.txt").write_bytes(content)
    with connect_database(ui_catalog.path) as connection:
        create_local_resources_table(connection)
        connection.execute("""INSERT INTO local_resources
            (document_id, source_id, title, relative_path, media_type, size_bytes, sha256, provenance,
             acquired_at, version, reuse_conditions, verification_status, package_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
            ui_catalog.document_id, ui_catalog.source_id, "Materiale sintetico UI", "fixture.txt", "text/plain", len(content),
            hashlib.sha256(content).hexdigest(), URL, "2026-09-01", "1.0", "Fixture sintetica di test", "da_verificare", "test-ui",
        ))
    monkeypatch.setattr(app, "read_resource_text", lambda resource, root: local_resources.read_resource_text(resource, root))
    monkeypatch.setattr(local_resources, "DEFAULT_RESOURCE_ROOT", resource_root)
    at = start_ui().radio(key="main_navigation").set_value("Catalogo").run()
    at.text_input(key="catalog_search").set_value("TEST-UI-01").run()
    assert HOSTILE_TEXT in [element.value for element in at.text]
    assert_no_active_external_content(at)
    at.radio(key="main_navigation").set_value("Revisione").run()
    resource_id = at.selectbox(key="resource_review_selection").value
    at.text_input(key=f"resource_reviewer_{resource_id}").set_value("Revisore sintetico")
    at.checkbox(key=f"resource_confirmed_{resource_id}").check()
    at.selectbox(key=f"resource_decision_{resource_id}").set_value("verificato").run()
    at.button(key=f"resource_submit_{resource_id}").click().run()
    assert not at.exception
    assert not at.error
    with connect_database(ui_catalog.path) as connection:
        assert connection.execute("SELECT verification_status FROM local_resources WHERE id = ?", (resource_id,)).fetchone()[0] == "verificato"
        assert list_review_events(connection, object_type="resource", object_id=resource_id)[-1]["new_status"] == "verificato"
    (resource_root / "fixture.txt").write_bytes(b"File sostituito")
    at.radio(key="main_navigation").set_value("Catalogo").run()
    at.text_input(key="catalog_search").set_value("TEST-UI-01").run()
    assert any("non è consultabile in sicurezza" in element.value for element in at.error)
    assert HOSTILE_TEXT not in [element.value for element in at.text]
    assert not at.exception
