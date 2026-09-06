from __future__ import annotations

from pathlib import Path

from src.database import connect_database, initialize_database, list_documents
from src.importers.lavoro import (
    fetch_lavoro_modules,
    import_lavoro_modules,
    parse_lavoro_html,
)


FIXTURE = Path(__file__).parent / "fixtures" / "lavoro_modules_v052.html"
LISTING_URL = (
    "https://www.lavoro.gov.it/strumenti-e-servizi/Modulistica/Pagine/Modulistica"
)


class FakeResponse:
    status_code = 200

    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        return None


class FakeGet:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(self, url: str, **_kwargs: object) -> FakeResponse:
        self.calls.append(url)
        return FakeResponse(FIXTURE.read_text(encoding="utf-8"))


def test_lavoro_parser_preserves_exposed_fields_and_nulls() -> None:
    batch = parse_lavoro_html(FIXTURE.read_text(encoding="utf-8"), LISTING_URL)

    assert len(batch.modules) == 2
    assert batch.discarded == 1
    first, second = batch.modules
    assert first.titolo_ufficiale == "Modello rendiconto 5 per mille"
    assert first.area == "Terzo settore"
    assert first.categoria == "Contributi"
    assert first.tipologia_utente == "Enti"
    assert first.finalita == "Agevolazioni"
    assert first.descrizione_ufficiale
    assert second.area is None
    assert second.categoria is None
    assert second.descrizione_ufficiale is None
    assert all("example.org" not in (module.download_url or "") for module in batch.modules)


def test_lavoro_offset_selects_records_after_the_first_batch() -> None:
    batch = fetch_lavoro_modules(
        LISTING_URL,
        limit=1,
        offset=1,
        request_get=FakeGet(),
    )

    assert len(batch.modules) == 1
    assert batch.modules[0].titolo_ufficiale == "Modulo per istanza di interpello"


def test_lavoro_dry_run_and_commit_are_idempotent(tmp_path) -> None:
    db_path = tmp_path / "lavoro.db"
    initialize_database(db_path, seed_demo=True)
    fake_get = FakeGet()
    with connect_database(db_path) as connection:
        before = len(list_documents(connection))
        dry = import_lavoro_modules(
            connection, limit=10, dry_run=True, request_get=fake_get
        )
        assert len(list_documents(connection)) == before
        first = import_lavoro_modules(
            connection,
            limit=10,
            dry_run=False,
            request_get=fake_get,
            detection_date="2026-08-10",
        )
        second = import_lavoro_modules(
            connection,
            limit=10,
            dry_run=False,
            request_get=fake_get,
            detection_date="2026-08-11",
        )
        imported = [
            document
            for document in list_documents(connection)
            if document.ente == "Ministero del Lavoro"
            and document.stato_verifica != "demo"
        ]

    assert len(dry.modules) == 2
    assert first.new == 2
    assert second.already_present == 2
    assert len(imported) == 2
    assert all(document.significato_semplice is None for document in imported)
