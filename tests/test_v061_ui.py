"""A01/A02/A04/A05: interfaccia reale Streamlit, dati esclusivamente temporanei."""
from __future__ import annotations

import pytest

from src.database import connect_database, initialize_database
from src.explanations import get_explanation, list_review_events
from src.local_packages import import_local_package
from src.local_resources import list_local_resources
from src.review import submit_document_review, submit_explanation_review
from test_local_packages import write_package
from test_offline_ui import HOSTILE_TEXT, assert_no_active_external_content, start_ui, ui_catalog, upload


def reject_document(catalog):
    submit_document_review(catalog.document_id, "rifiutato", "Revisore di prova",
                           review_notes="Rifiuto sintetico motivato", db_path=catalog.path)


def test_rejected_document_keeps_history_but_hides_verified_explanation(ui_catalog):
    submit_explanation_review(ui_catalog.explanation_id, "verificato", "Revisore di prova",
                              source_confirmed=True, db_path=ui_catalog.path)
    with connect_database(ui_catalog.path) as connection:
        before = get_explanation(connection, ui_catalog.explanation_id)
        history = list_review_events(connection, object_type="explanation", object_id=ui_catalog.explanation_id)
    reject_document(ui_catalog)
    at = start_ui().radio(key="main_navigation").set_value("Catalogo").run()
    at.text_input(key="catalog_search").set_value("TEST-UI-01").run()
    assert len(at.dataframe[0].value) == 1
    assert any("Documento rifiutato" in item.value for item in at.warning)
    assert not any("non hanno ancora completato" in item.value for item in at.warning)
    assert HOSTILE_TEXT not in [item.value for item in at.text]
    assert not at.success
    at.radio(key="main_navigation").set_value("Revisione").run()
    assert at.text_area(key=f"simple_explanation_{ui_catalog.explanation_id}").value == HOSTILE_TEXT
    with connect_database(ui_catalog.path) as connection:
        assert get_explanation(connection, ui_catalog.explanation_id) == before
        assert list_review_events(connection, object_type="explanation", object_id=ui_catalog.explanation_id) == history
    assert_no_active_external_content(at)


def test_same_session_reloads_decision_after_document_review(ui_catalog, monkeypatch):
    upload(monkeypatch, b"INPS TEST-UI-01 Documento sintetico di prova della consultazione locale versione 2026.")
    at = start_ui()
    assert "Esito: DOCUMENT_MATCH" in [item.value for item in at.text]
    revision = next(item.value for item in at.text if item.value.startswith("catalog_revision:"))
    reject_document(ui_catalog)
    at.run()
    assert "Esito: NO_MATCH" in [item.value for item in at.text]
    assert not any(item.value == "Documento riconosciuto" for item in at.header)
    changed = next(item.value for item in at.text if item.value.startswith("catalog_revision:"))
    assert changed != revision
    at.run()
    assert changed in [item.value for item in at.text]
    submit_document_review(ui_catalog.document_id, "da_verificare", "Revisore di prova", db_path=ui_catalog.path)
    at.run()
    assert "Esito: DOCUMENT_MATCH" in [item.value for item in at.text]
    assert revision in [item.value for item in at.text]
    assert_no_active_external_content(at)


@pytest.mark.parametrize("blank", [None, "", "   "])
def test_incomplete_draft_verify_disabled_in_ui(ui_catalog, blank):
    with connect_database(ui_catalog.path) as connection:
        connection.execute("UPDATE document_explanations SET simple_explanation = ?, intended_use = NULL WHERE id = ?",
                           (blank, ui_catalog.explanation_id))
    at = start_ui().radio(key="main_navigation").set_value("Revisione").run()
    at.text_input(key=f"explanation_reviewer_{ui_catalog.explanation_id}").set_value("Revisore di prova").run()
    at.checkbox(key=f"source_confirmed_{ui_catalog.explanation_id}").check().run()
    assert at.button(key=f"verify_{ui_catalog.explanation_id}").disabled
    assert not at.button(key=f"save_editorial_{ui_catalog.explanation_id}").disabled
    assert any("spiegazione semplice" in item.value.lower() for item in at.warning)
    assert_no_active_external_content(at)


def test_rejected_document_blocks_verification_in_ui(ui_catalog):
    reject_document(ui_catalog)
    at = start_ui().radio(key="main_navigation").set_value("Revisione").run()
    at.text_input(key=f"explanation_reviewer_{ui_catalog.explanation_id}").set_value("Revisore di prova").run()
    at.checkbox(key=f"source_confirmed_{ui_catalog.explanation_id}").check().run()
    assert at.button(key=f"verify_{ui_catalog.explanation_id}").disabled
    assert any("Documento rifiutato" in item.value for item in at.warning)
    assert_no_active_external_content(at)


def test_saved_simple_text_can_be_verified_without_optional_intended_use(ui_catalog):
    identifier = ui_catalog.explanation_id
    with connect_database(ui_catalog.path) as connection:
        connection.execute("UPDATE document_explanations SET simple_explanation = NULL, intended_use = NULL WHERE id = ?", (identifier,))
    at = start_ui().radio(key="main_navigation").set_value("Revisione").run()
    at.text_input(key=f"explanation_reviewer_{identifier}").set_value("Revisore di prova").run()
    at.text_area(key=f"simple_explanation_{identifier}").set_value("Spiegazione sintetica completata dal revisore.").run()
    at.button(key=f"save_editorial_{identifier}").click().run()
    at.checkbox(key=f"source_confirmed_{identifier}").check().run()
    assert not at.button(key=f"verify_{identifier}").disabled
    at.button(key=f"verify_{identifier}").click().run()
    assert not at.error
    with connect_database(ui_catalog.path) as connection:
        saved = get_explanation(connection, identifier)
        assert saved.verification_status == "verificato"
        assert saved.intended_use is None
    assert_no_active_external_content(at)


def test_two_databases_resources_visible_after_new_ui_sessions(tmp_path, monkeypatch):
    import app
    package = write_package(tmp_path / "package.zip")
    root = tmp_path / "common-base"
    for name in ("first.sqlite3", "second.sqlite3"):
        path = tmp_path / name
        initialize_database(path, seed_demo=False)
        with connect_database(path) as connection:
            preview = import_local_package(connection, package, root)
            import_local_package(connection, package, root, dry_run=False, expected_sha256=preview.sha256)
            resource = list_local_resources(connection)[0]
        monkeypatch.setattr(app, "DEFAULT_DB_PATH", path)
        at = start_ui().radio(key="main_navigation").set_value("Catalogo").run()
        at.selectbox(key="catalog_document").set_value(resource.document_id).run()
        assert not at.error
        assert any("SINTETICO" in item.value for item in at.text)
        assert_no_active_external_content(at)
