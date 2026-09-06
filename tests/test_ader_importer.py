from __future__ import annotations

from pathlib import Path

import pytest

from src.database import connect_database, initialize_database, list_documents
from src.importers.ader import (
    AderImportError,
    fetch_ader_modules,
    import_ader_modules,
    parse_ader_html,
    import_saved_ader_html,
    parse_saved_ader_html,
)
from src.official_urls import is_official_ader_url
from src.provenance import get_document_provenance
from src.sources import list_sources


FIXTURE = Path(__file__).parent / "fixtures" / "ader_modules.html"
LISTING_URL = (
    "https://www.agenziaentrateriscossione.gov.it/it/modulistica/index.html"
)


def fixture_html() -> str:
    return FIXTURE.read_text(encoding="utf-8")


class FakeResponse:
    def __init__(self, text: str, status_code: int = 200) -> None:
        self.text = text
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise AssertionError("Il test 403 deve fermarsi prima di raise_for_status.")


class FakeGet:
    def __init__(self, html: str, status_code: int = 200) -> None:
        self.html = html
        self.status_code = status_code
        self.calls: list[tuple[str, dict[str, object]]] = []

    def __call__(self, url: str, **kwargs: object) -> FakeResponse:
        self.calls.append((url, kwargs))
        return FakeResponse(self.html, self.status_code)


def test_ader_is_a_distinct_verified_source(tmp_path) -> None:
    db_path = tmp_path / "sources.db"
    initialize_database(db_path, seed_demo=True)
    with connect_database(db_path) as connection:
        sources = list_sources(connection)

    names = {source.ente: source for source in sources}
    assert "Agenzia delle Entrate" in names
    assert "Agenzia delle Entrate-Riscossione" in names
    ader = names["Agenzia delle Entrate-Riscossione"]
    assert ader.stato_verifica == "verificato"
    assert ader.url_modulistica == LISTING_URL
    assert is_official_ader_url(ader.url_modulistica)


def test_ader_parser_extracts_official_metadata_and_rejects_external_url() -> None:
    batch = parse_ader_html(fixture_html(), LISTING_URL, limit=3)

    assert batch.examined == 3
    assert batch.discarded == 1
    assert len(batch.modules) == 2
    first = batch.modules[0]
    assert first.codice == "RD1"
    assert first.titolo_ufficiale == "RD1 - Richiesta documenti ed estratti"
    assert first.categoria == "Cartella di pagamento"
    assert first.descrizione_ufficiale == "Modulo per richiedere documenti ed estratti."
    assert first.data_pubblicazione == "2026-07-01"
    assert first.detail_url == (
        "https://www.agenziaentrateriscossione.gov.it/it/modulistica/"
        "richiesta-documenti/"
    )
    assert first.download_url == (
        "https://www.agenziaentrateriscossione.gov.it/export/.files/"
        "it/modulistica/RD1.pdf"
    )


@pytest.mark.parametrize(
    "url",
    (
        "http://www.agenziaentrateriscossione.gov.it/it/modulistica/",
        "https://agenziaentrateriscossione.gov.it.example.org/modulo",
        "https://bit.ly/modulo-ader",
        "https://example.org/modulo",
    ),
)
def test_external_or_unsafe_ader_urls_are_rejected(url: str) -> None:
    assert not is_official_ader_url(url)


def test_ader_fetch_uses_one_sequential_request_and_batch_limit() -> None:
    fake_get = FakeGet(fixture_html())

    batch = fetch_ader_modules(LISTING_URL, limit=2, request_get=fake_get)

    assert batch.examined == 2
    assert len(batch.modules) == 2
    assert len(fake_get.calls) == 1
    url, options = fake_get.calls[0]
    assert url == LISTING_URL
    assert options["timeout"] == (5, 20)


def test_ader_dry_run_does_not_modify_catalog(tmp_path) -> None:
    db_path = tmp_path / "ader-dry.db"
    initialize_database(db_path, seed_demo=True)
    with connect_database(db_path) as connection:
        before = len(list_documents(connection))
        report = import_ader_modules(
            connection,
            limit=3,
            dry_run=True,
            request_get=FakeGet(fixture_html()),
            detection_date="2026-08-05",
        )
        after = len(list_documents(connection))

    assert before == after == 10
    assert len(report.modules) == 2
    assert report.discarded == 1


def test_ader_commit_is_idempotent_and_records_provenance(tmp_path) -> None:
    db_path = tmp_path / "ader-commit.db"
    initialize_database(db_path, seed_demo=True)
    fake_get = FakeGet(fixture_html())
    with connect_database(db_path) as connection:
        first = import_ader_modules(
            connection,
            limit=3,
            dry_run=False,
            request_get=fake_get,
            detection_date="2026-08-05",
        )
        second = import_ader_modules(
            connection,
            limit=3,
            dry_run=False,
            request_get=fake_get,
            detection_date="2026-08-06",
        )
        documents = list_documents(connection)
        imported = [
            document
            for document in documents
            if document.ente == "Agenzia delle Entrate-Riscossione"
            and document.stato_verifica == "da_verificare"
        ]
        provenance = get_document_provenance(connection, imported[0].id or 0)

    assert first.new == 2
    assert second.new == 0
    assert second.already_present == 2
    assert len(documents) == 12
    assert len(imported) == 2
    assert all(document.significato_semplice is None for document in imported)
    assert provenance is not None
    assert provenance.acquired_at == "2026-08-05"
    assert provenance.last_seen_at == "2026-08-06"
    assert provenance.acquisition_method == "ader_html"
    assert provenance.content_hash is not None


def test_ader_deduplicates_by_official_url_before_title(tmp_path) -> None:
    db_path = tmp_path / "ader-url-dedup.db"
    initialize_database(db_path, seed_demo=True)
    original = fixture_html()
    changed = original.replace(
        'data-code="RD1"',
        'data-code="RD1-NUOVO"',
    ).replace(
        "RD1 - Richiesta documenti ed estratti",
        "Titolo ufficiale aggiornato",
    )
    with connect_database(db_path) as connection:
        import_ader_modules(
            connection,
            limit=1,
            dry_run=False,
            request_get=FakeGet(original),
            detection_date="2026-08-05",
        )
        report = import_ader_modules(
            connection,
            limit=1,
            dry_run=False,
            request_get=FakeGet(changed),
            detection_date="2026-08-06",
        )
        imported = [
            document
            for document in list_documents(connection)
            if document.ente == "Agenzia delle Entrate-Riscossione"
            and document.stato_verifica == "da_verificare"
        ]

    assert report.updated == 1
    assert len(imported) == 1
    assert imported[0].titolo_ufficiale == "Titolo ufficiale aggiornato"


def test_ader_respects_403_without_retrying() -> None:
    fake_get = FakeGet("", status_code=403)

    with pytest.raises(AderImportError, match="non tenta di aggirare"):
        fetch_ader_modules(LISTING_URL, request_get=fake_get)

    assert len(fake_get.calls) == 1


def test_saved_ader_html_requires_declared_official_provenance() -> None:
    batch = parse_saved_ader_html(fixture_html(), LISTING_URL, limit=2)
    assert len(batch.modules) == 2

    without_canonical = fixture_html().replace(
        '<link rel="canonical" href="https://www.agenziaentrateriscossione.gov.it/it/modulistica/index.html">',
        "",
    )
    with pytest.raises(AderImportError, match="provenienza ADER non verificabile"):
        parse_saved_ader_html(without_canonical, LISTING_URL, limit=2)

    external = fixture_html().replace(
        "https://www.agenziaentrateriscossione.gov.it/it/modulistica/index.html",
        "https://example.org/falso.html",
        1,
    )
    with pytest.raises(AderImportError, match="provenienza esterna"):
        parse_saved_ader_html(external, LISTING_URL, limit=2)


def test_saved_ader_html_commit_records_manual_method(tmp_path) -> None:
    db_path = tmp_path / "ader-local.db"
    initialize_database(db_path, seed_demo=True)
    with connect_database(db_path) as connection:
        report = import_saved_ader_html(
            connection,
            fixture_html(),
            limit=1,
            dry_run=False,
            detection_date="2026-08-05",
        )
        imported = next(
            document
            for document in list_documents(connection)
            if document.ente == "Agenzia delle Entrate-Riscossione"
            and document.stato_verifica == "da_verificare"
        )
        provenance = get_document_provenance(connection, imported.id or 0)

    assert report.new == 1
    assert provenance is not None
    assert provenance.acquisition_method == "ader_html_manuale"
