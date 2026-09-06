from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.database import (
    connect_database,
    initialize_database,
    insert_document,
    list_documents,
)
from src.importers.inps import (
    InpsModule,
    InpsImportError,
    _find_existing,
    derive_search_endpoint,
    import_inps_modules,
    is_official_inps_url,
    parse_inps_html,
    parse_inps_json,
    preview_lines,
    validate_limit,
    validate_page,
)
from src.models import AdministrativeDocument
from src.sources import search_sources_by_ente


FIXTURES = Path(__file__).parent / "fixtures"
LISTING_URL = "https://www.inps.it/it/it/moduli.html"


def load_payload() -> dict[str, object]:
    return json.loads((FIXTURES / "inps_modules.json").read_text(encoding="utf-8"))


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload
        self.text = json.dumps(payload)

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self._payload


class FakeGet:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.calls: list[tuple[str, dict[str, object]]] = []

    def __call__(self, url: str, **kwargs: object) -> FakeResponse:
        self.calls.append((url, kwargs))
        return FakeResponse(self.payload)


def test_json_extracts_code_title_date_and_official_urls() -> None:
    batch = parse_inps_json(load_payload(), LISTING_URL, limit=4)

    module = batch.modules[0]
    assert module.codice == "AP17"
    assert module.titolo_ufficiale == "Domanda di prestazione di prova"
    assert module.data_pubblicazione == "2024-08-01"
    assert module.detail_url == "https://www.inps.it/content/inps-site/it/it/moduli/dettaglio-moduli.moduli.ap17.html"
    assert module.download_url == "https://www.inps.it/content/dam/inps-site/moduli/ap17/AP17.pdf"
    assert module.categoria == "aree:previdenza"
    assert module.descrizione_ufficiale == "Descrizione ufficiale pubblicata da INPS."
    assert module.versione == "2.0"


def test_missing_optional_values_stay_none() -> None:
    batch = parse_inps_json(load_payload(), LISTING_URL, limit=2)

    module = batch.modules[1]
    assert module.codice is None
    assert module.categoria is None
    assert module.descrizione_ufficiale is None
    assert module.download_url is None
    assert module.data_pubblicazione is None
    assert module.versione is None


def test_json_respects_limit_and_discards_bad_rows() -> None:
    one = parse_inps_json(load_payload(), LISTING_URL, limit=1)
    all_rows = parse_inps_json(load_payload(), LISTING_URL, limit=4)

    assert one.examined == 1
    assert len(one.modules) == 1
    assert all_rows.examined == 4
    assert len(all_rows.modules) == 2
    assert all_rows.discarded == 2


def test_local_html_fixture_is_parsed_without_network() -> None:
    html = (FIXTURES / "inps_modules.html").read_text(encoding="utf-8")
    batch = parse_inps_html(html, LISTING_URL, limit=3)

    assert batch.examined == 3
    assert batch.discarded == 1
    assert [module.codice for module in batch.modules] == ["HTML-01", None]
    assert batch.modules[0].data_pubblicazione == "2026-08-02"
    assert batch.modules[0].download_url == "https://www.inps.it/content/dam/inps-site/moduli/html-01.pdf"


@pytest.mark.parametrize(
    "url",
    (
        "https://inps.it/moduli",
        "https://www.inps.it/moduli",
        "https://search.inps.it/wrapper/api",
    ),
)
def test_official_inps_domains_are_allowed(url: str) -> None:
    assert is_official_inps_url(url)


@pytest.mark.parametrize(
    "url",
    (
        "http://www.inps.it/moduli",
        "https://inps.it.example.org/moduli",
        "https://example.org/moduli",
        "https://user@www.inps.it/moduli",
    ),
)
def test_external_or_unsafe_domains_are_rejected(url: str) -> None:
    assert not is_official_inps_url(url)


def test_endpoint_is_derived_from_registry_url() -> None:
    assert derive_search_endpoint(LISTING_URL) == (
        "https://www.inps.it/it/it/moduli.cfListDynamic.search.json"
    )
    with pytest.raises(InpsImportError):
        derive_search_endpoint("https://example.org/moduli.html")


def test_limit_above_hard_cap_is_rejected() -> None:
    assert validate_limit(200) == 200
    with pytest.raises(ValueError):
        validate_limit(201)
    assert validate_page(2) == 2
    with pytest.raises(ValueError):
        validate_page(0)


def test_same_code_with_distinct_language_url_is_not_conflated() -> None:
    existing = AdministrativeDocument(
        ente="INPS",
        codice="SC80",
        titolo_ufficiale="Rapporto di lavoro domestico",
        categoria=None,
        descrizione_ufficiale=None,
        significato_semplice=None,
        versione=None,
        data_rilevazione="2026-08-10",
        stato_verifica="da_verificare",
        download_url="https://www.inps.it/moduli/sc80.pdf",
        detail_url="https://www.inps.it/moduli/sc80.it.html",
    )
    english = InpsModule(
        codice="SC80",
        titolo_ufficiale="Domestic work relationship",
        categoria=None,
        descrizione_ufficiale=None,
        fonte_url=LISTING_URL,
        download_url="https://www.inps.it/moduli/sc80.pdf",
        detail_url="https://www.inps.it/moduli/sc80.en.html",
        data_pubblicazione=None,
        versione=None,
    )

    assert _find_existing(english, [existing]) is None


def test_dry_run_does_not_write_and_uses_one_request(tmp_path) -> None:
    db_path = tmp_path / "dry-run.db"
    initialize_database(db_path, seed_demo=True)
    fake_get = FakeGet(load_payload())
    with connect_database(db_path) as connection:
        before = len(list_documents(connection))
        report = import_inps_modules(
            connection,
            limit=2,
            dry_run=True,
            request_get=fake_get,
            detection_date="2026-08-04",
        )
        after = len(list_documents(connection))

    assert before == after == 10
    assert report.examined == 2
    assert len(fake_get.calls) == 1
    assert fake_get.calls[0][1]["params"] == {
        "maxItems": 2,
        "currentPage": 1,
        "lang": "it",
    }
    assert preview_lines(report)[0] == "CODICE | TITOLO | DATA | URL"


def test_inps_uses_native_page_parameter(tmp_path) -> None:
    db_path = tmp_path / "page.db"
    initialize_database(db_path, seed_demo=True)
    fake_get = FakeGet(load_payload())
    with connect_database(db_path) as connection:
        import_inps_modules(
            connection,
            limit=2,
            page=2,
            dry_run=True,
            request_get=fake_get,
        )

    assert fake_get.calls[0][1]["params"]["currentPage"] == 2


def test_commit_links_source_and_repeat_avoids_duplicates(tmp_path) -> None:
    db_path = tmp_path / "commit.db"
    initialize_database(db_path, seed_demo=True)
    fake_get = FakeGet(load_payload())
    with connect_database(db_path) as connection:
        first = import_inps_modules(
            connection,
            limit=2,
            dry_run=False,
            request_get=fake_get,
            detection_date="2026-08-04",
        )
        second = import_inps_modules(
            connection,
            limit=2,
            dry_run=False,
            request_get=fake_get,
            detection_date="2026-08-04",
        )
        documents = list_documents(connection)
        inps_source = search_sources_by_ente(connection, "INPS")[0]

    assert first.new == 2
    assert second.new == 0
    assert second.already_present == 2
    assert len(documents) == 12
    imported = [document for document in documents if document.stato_verifica == "da_verificare"]
    assert len(imported) == 2
    assert all(document.source_id == inps_source.id for document in imported)
    assert all(document.significato_semplice is None for document in imported)


def test_normalized_title_is_dedup_fallback(tmp_path) -> None:
    db_path = tmp_path / "title-dedup.db"
    initialize_database(db_path, seed_demo=True)
    payload = load_payload()
    no_code_item = payload["items"][1]
    assert isinstance(no_code_item, dict)
    fake_get = FakeGet({"items": [no_code_item]})
    with connect_database(db_path) as connection:
        first = import_inps_modules(
            connection,
            limit=1,
            dry_run=False,
            request_get=fake_get,
            detection_date="2026-08-04",
        )
        no_code_item["title"] = "NEW-CODE"
        elements = no_code_item["elements"]
        assert isinstance(elements, dict)
        elements["codice"] = {"value": "NEW-CODE"}
        elements["titolo"] = {"value": "  MODULO senza metadati facoltativi  "}
        second = import_inps_modules(
            connection,
            limit=1,
            dry_run=False,
            request_get=fake_get,
            detection_date="2026-08-04",
        )
        imported = [
            document
            for document in list_documents(connection)
            if document.stato_verifica == "da_verificare"
        ]

    assert first.new == 1
    assert second.updated == 1
    assert len(imported) == 1
    assert imported[0].codice == "NEW-CODE"


def test_verified_document_is_not_overwritten(tmp_path) -> None:
    db_path = tmp_path / "verified.db"
    initialize_database(db_path, seed_demo=True)
    with connect_database(db_path) as connection:
        source = search_sources_by_ente(connection, "INPS")[0]
        verified_id = insert_document(
            connection,
            AdministrativeDocument(
                ente="INPS",
                codice="AP17",
                titolo_ufficiale="Titolo verificato manualmente",
                categoria="manuale",
                descrizione_ufficiale="Testo verificato manualmente.",
                significato_semplice="Spiegazione editoriale.",
                versione="manuale",
                data_rilevazione="2026-08-03",
                stato_verifica="verificato",
                source_id=source.id,
            ),
        )
        report = import_inps_modules(
            connection,
            limit=1,
            dry_run=False,
            request_get=FakeGet(load_payload()),
            detection_date="2026-08-04",
        )
        recovered = next(
            document
            for document in list_documents(connection)
            if document.id == verified_id
        )

    assert report.already_present == 1
    assert recovered.titolo_ufficiale == "Titolo verificato manualmente"
    assert recovered.descrizione_ufficiale == "Testo verificato manualmente."
