from __future__ import annotations

from pathlib import Path

import pytest

from src.database import connect_database, initialize_database, list_documents
from src.importers.garante import (
    GaranteModule,
    GaranteImportError,
    _find_existing,
    fetch_garante_modules,
    import_garante_modules,
    parse_garante_html,
)
from src.models import AdministrativeDocument


FIXTURE = Path(__file__).parent / "fixtures" / "garante_modules.html"
LISTING_URL = "https://www.garanteprivacy.it/home/modulistica-e-servizi-online"


class FakeResponse:
    def __init__(self, text: str, status_code: int = 200) -> None:
        self.text = text
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise AssertionError("Il blocco deve essere gestito prima di questa chiamata.")


class FakeGet:
    def __init__(self, status_code: int = 200) -> None:
        self.status_code = status_code
        self.calls: list[str] = []

    def __call__(self, url: str, **_kwargs: object) -> FakeResponse:
        self.calls.append(url)
        return FakeResponse(FIXTURE.read_text("utf-8"), self.status_code)


def test_garante_parser_keeps_titles_description_pdf_docx_and_official_domain() -> None:
    batch = parse_garante_html(FIXTURE.read_text("utf-8"), LISTING_URL)

    assert len(batch.modules) == 3
    assert batch.discarded == 1
    reclamo = batch.modules[0]
    rights = batch.modules[1]
    assert reclamo.titolo_ufficiale == "RECLAMO"
    assert reclamo.descrizione_ufficiale and "consente" in reclamo.descrizione_ufficiale
    assert rights.formati == ("DOCX", "PDF")
    assert rights.download_url and "garante/document" in rights.download_url
    assert rights.descrizione_ufficiale is None
    assert all("example.org" not in module.detail_url for module in batch.modules)


def test_garante_dry_run_and_commit_are_idempotent(tmp_path) -> None:
    db_path = tmp_path / "garante.db"
    initialize_database(db_path, seed_demo=True)
    fake_get = FakeGet()
    with connect_database(db_path) as connection:
        before = len(list_documents(connection))
        dry = import_garante_modules(
            connection, limit=10, dry_run=True, request_get=fake_get
        )
        assert len(list_documents(connection)) == before
        first = import_garante_modules(
            connection,
            limit=10,
            dry_run=False,
            request_get=fake_get,
            detection_date="2026-08-10",
        )
        second = import_garante_modules(
            connection,
            limit=10,
            dry_run=False,
            request_get=fake_get,
            detection_date="2026-08-11",
        )
        imported = [
            document
            for document in list_documents(connection)
            if document.ente == "Garante per la protezione dei dati personali"
        ]

    assert len(dry.modules) == 3
    assert first.new == 3
    assert second.already_present == 3
    assert len(imported) == 3
    assert all(document.significato_semplice is None for document in imported)


def test_garante_dedup_keeps_distinct_titles_on_shared_detail_page() -> None:
    listing_url = LISTING_URL
    existing = AdministrativeDocument(
        ente="Garante per la protezione dei dati personali",
        codice=None,
        titolo_ufficiale="ESERCIZIO DEI DIRITTI",
        categoria="Modulistica e servizi online",
        descrizione_ufficiale=None,
        significato_semplice=None,
        versione=None,
        data_rilevazione="2026-08-10",
        stato_verifica="da_verificare",
        detail_url=listing_url,
    )
    distinct = GaranteModule(
        titolo_ufficiale="VIDEOSORVEGLIANZA",
        categoria="Modulistica e servizi online",
        descrizione_ufficiale=None,
        fonte_url=listing_url,
        detail_url=listing_url,
        download_url=None,
    )

    assert _find_existing(distinct, [existing]) is None


def test_garante_respects_429_without_retrying() -> None:
    fake_get = FakeGet(status_code=429)
    with pytest.raises(GaranteImportError, match="non tenta di aggirare"):
        fetch_garante_modules(LISTING_URL, request_get=fake_get)
    assert len(fake_get.calls) == 1
