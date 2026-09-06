from __future__ import annotations

from pathlib import Path

import pytest

from src.database import connect_database, initialize_database, list_documents
from src.families import list_document_families
from src.importers.ade import (
    AdeModule,
    AdeImportError,
    _find_existing,
    fetch_ade_modules,
    import_ade_modules,
    parse_ade_detail_html,
    parse_ade_html,
    validate_limit,
)
from src.recognize import recognize_catalog
from src.models import AdministrativeDocument


FIXTURES = Path(__file__).parent / "fixtures"
LISTING_URL = (
    "https://www.agenziaentrate.gov.it/portale/strumenti/modelli/tutti-i-modelli"
)


class FakeResponse:
    def __init__(self, text: str, status_code: int = 200) -> None:
        self.text = text
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise AssertionError("Il blocco deve essere gestito prima di questa chiamata.")


class AdeFakeGet:
    def __init__(self, status_code: int = 200) -> None:
        self.status_code = status_code
        self.calls: list[str] = []

    def __call__(self, url: str, **_kwargs: object) -> FakeResponse:
        self.calls.append(url)
        if url == LISTING_URL:
            return FakeResponse(
                (FIXTURES / "ade_models.html").read_text(encoding="utf-8"),
                self.status_code,
            )
        return FakeResponse("<html><body><main></main></body></html>")


def test_ade_parser_keeps_category_year_version_url_and_rejects_external() -> None:
    batch = parse_ade_html(
        (FIXTURES / "ade_models.html").read_text(encoding="utf-8"),
        LISTING_URL,
    )

    assert len(batch.modules) == 3
    assert batch.discarded == 1
    assert batch.modules[0].categoria == "Agevolazioni"
    assert batch.modules[0].anno == "2025"
    assert batch.modules[1].anno == "2026"
    assert batch.modules[2].codice == "730"
    assert all("example.org" not in module.detail_url for module in batch.modules)


def test_ade_detail_parser_distinguishes_model_and_instructions() -> None:
    model_url, instructions_url = parse_ade_detail_html(
        (FIXTURES / "ade_detail.html").read_text(encoding="utf-8"),
        "https://www.agenziaentrate.gov.it/portale/credito-zes-2026/modello-e-istruzioni",
    )

    assert model_url and model_url.endswith("modello-credito-zes-2026.pdf")
    assert instructions_url and instructions_url.endswith(
        "istruzioni-credito-zes-2026.pdf"
    )


def test_ade_limit_obeys_configurable_hard_cap() -> None:
    assert validate_limit(500) == 500
    with pytest.raises(ValueError):
        validate_limit(501)


def test_ade_offset_selects_a_stable_batch() -> None:
    batch = parse_ade_html(
        (FIXTURES / "ade_models.html").read_text(encoding="utf-8"),
        LISTING_URL,
        limit=1,
        offset=1,
    )

    assert len(batch.modules) == 1
    assert batch.modules[0].anno == "2026"
    assert batch.total_available == 3


def test_ade_shared_model_url_is_not_used_as_document_identity() -> None:
    shared_model = "https://www.agenziaentrate.gov.it/portale/documents/shared.pdf"
    existing = AdministrativeDocument(
        ente="Agenzia delle Entrate",
        codice=None,
        titolo_ufficiale="F23",
        categoria="Pagamenti",
        descrizione_ufficiale=None,
        significato_semplice=None,
        versione=None,
        data_rilevazione="2026-08-10",
        stato_verifica="da_verificare",
        download_url=shared_model,
        detail_url="https://www.agenziaentrate.gov.it/portale/f23",
    )
    distinct = AdeModule(
        titolo_ufficiale="Contributo unificato",
        categoria="Pagamenti",
        anno=None,
        codice=None,
        fonte_url=LISTING_URL,
        detail_url="https://www.agenziaentrate.gov.it/portale/contributo-unificato",
        model_url=shared_model,
    )

    assert _find_existing(distinct, [existing]) is None


def test_ade_dry_run_commit_idempotency_and_recognition(tmp_path) -> None:
    db_path = tmp_path / "ade.db"
    initialize_database(db_path, seed_demo=True)
    fake_get = AdeFakeGet()
    with connect_database(db_path) as connection:
        before = len(list_documents(connection))
        dry = import_ade_modules(
            connection, limit=3, dry_run=True, request_get=fake_get
        )
        assert len(list_documents(connection)) == before
        first = import_ade_modules(
            connection,
            limit=3,
            dry_run=False,
            request_get=fake_get,
            detection_date="2026-08-10",
        )
        second = import_ade_modules(
            connection,
            limit=3,
            dry_run=False,
            request_get=fake_get,
            detection_date="2026-08-11",
        )
        imported = [
            document
            for document in list_documents(connection)
            if document.ente == "Agenzia delle Entrate"
            and document.stato_verifica != "demo"
        ]
        result = recognize_catalog(
            "Agenzia delle Entrate - Credito ZES 2026",
            imported,
            list_document_families(connection),
        )

    assert len(dry.modules) == 3
    assert first.new == 3
    assert second.already_present == 3
    assert len(imported) == 3
    assert all(document.significato_semplice is None for document in imported)
    assert result.match_type == "DOCUMENT_MATCH"


def test_ade_respects_403_without_retrying() -> None:
    fake_get = AdeFakeGet(status_code=403)
    with pytest.raises(AdeImportError, match="non tenta di aggirare"):
        fetch_ade_modules(LISTING_URL, limit=1, request_get=fake_get)
    assert len(fake_get.calls) == 1
