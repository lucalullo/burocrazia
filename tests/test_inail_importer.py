from __future__ import annotations

from pathlib import Path

import pytest

from src.database import connect_database, initialize_database, list_documents
from src.importers.inail import (
    InailImportError,
    fetch_inail_modules,
    import_inail_modules,
    parse_inail_html,
    validate_limit,
)
from src.official_urls import is_official_inail_url
from src.provenance import get_document_provenance
from src.sources import search_sources_by_ente


FIXTURE = Path(__file__).parent / "fixtures" / "inail_modules.html"
LISTING_URL = (
    "https://www.inail.it/portale/it/atti-e-documenti/moduli-e-modelli/"
    "altri-moduli/abilitazione-ai-servizi-online.html"
)


def fixture_html() -> str:
    return FIXTURE.read_text(encoding="utf-8")


class FakeResponse:
    def __init__(self, text: str, status_code: int = 200) -> None:
        self.text = text
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise AssertionError("Il test deve gestire il blocco prima di questa chiamata.")


class FakeGet:
    def __init__(self, text: str, status_code: int = 200) -> None:
        self.text = text
        self.status_code = status_code
        self.calls: list[tuple[str, dict[str, object]]] = []

    def __call__(self, url: str, **kwargs: object) -> FakeResponse:
        self.calls.append((url, kwargs))
        return FakeResponse(self.text, self.status_code)


def test_inail_source_and_urls_are_official(tmp_path) -> None:
    db_path = tmp_path / "source.db"
    initialize_database(db_path, seed_demo=True)
    with connect_database(db_path) as connection:
        source = search_sources_by_ente(connection, "INAIL")[0]

    assert source.url_modulistica == LISTING_URL
    assert source.metodo_acquisizione == "inail_html"
    assert is_official_inail_url(source.url_modulistica)
    assert not is_official_inail_url("https://inail.it.example.org/modulo.pdf")


def test_inail_parser_keeps_only_official_download_metadata() -> None:
    batch = parse_inail_html(fixture_html(), LISTING_URL, limit=3)

    assert batch.examined == 3
    assert batch.discarded == 1
    assert len(batch.modules) == 2
    assert batch.modules[0].titolo_ufficiale == "Modulo per professionisti"
    assert batch.modules[0].categoria == "Abilitazione ai servizi online"
    assert batch.modules[1].download_url.startswith("https://www.inail.it/")


def test_inail_limit_has_hard_cap_of_twenty() -> None:
    assert validate_limit(20) == 20
    with pytest.raises(ValueError):
        validate_limit(21)


def test_inail_dry_run_uses_one_request_and_does_not_write(tmp_path) -> None:
    db_path = tmp_path / "dry.db"
    initialize_database(db_path, seed_demo=True)
    fake_get = FakeGet(fixture_html())
    with connect_database(db_path) as connection:
        before = len(list_documents(connection))
        report = import_inail_modules(
            connection, limit=2, dry_run=True, request_get=fake_get
        )
        after = len(list_documents(connection))

    assert before == after == 10
    assert len(report.modules) == 2
    assert len(fake_get.calls) == 1


def test_inail_commit_is_idempotent_and_records_provenance(tmp_path) -> None:
    db_path = tmp_path / "commit.db"
    initialize_database(db_path, seed_demo=True)
    fake_get = FakeGet(fixture_html())
    with connect_database(db_path) as connection:
        first = import_inail_modules(
            connection,
            limit=2,
            dry_run=False,
            request_get=fake_get,
            detection_date="2026-08-05",
        )
        second = import_inail_modules(
            connection,
            limit=2,
            dry_run=False,
            request_get=fake_get,
            detection_date="2026-08-06",
        )
        imported = [
            document
            for document in list_documents(connection)
            if document.ente == "INAIL" and document.stato_verifica == "da_verificare"
        ]
        provenance = get_document_provenance(connection, imported[0].id or 0)

    assert first.new == 2
    assert second.already_present == 2
    assert len(imported) == 2
    assert provenance is not None
    assert provenance.last_seen_at == "2026-08-06"
    assert provenance.acquisition_method == "inail_html"


def test_inail_respects_403_without_retrying() -> None:
    fake_get = FakeGet("", 403)
    with pytest.raises(InailImportError, match="non tenta di aggirare"):
        fetch_inail_modules(LISTING_URL, request_get=fake_get)
    assert len(fake_get.calls) == 1
