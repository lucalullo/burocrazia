from __future__ import annotations

from typing import Any

import pytest

from src.database import (
    connect_database,
    initialize_database,
    insert_document,
)
from src.enrichment import enrich_inps_documents, validate_enrichment_limit
from src.explanations import list_explanations
from src.models import AdministrativeDocument
from src.sources import search_sources_by_ente


TITLES = {
    "SR211": "RINUNCIA DEI BENEFICIARI ALLA CARTA ACQUISTI",
    "CI544": "CERTIFICATO DI OPZIONE CONTRIBUTIVA - ACCORDO ITALIA ALBANIA",
    "CI543": "CERTIFICATO DI DISTACCO - ACCORDO ITALIA ALBANIA",
}


class FakeResponse:
    def __init__(self, url: str) -> None:
        self.url = url
        self.text = "<html><main>Pagina ufficiale INPS del modulo.</main></html>"

    def raise_for_status(self) -> None:
        return None


class FakeGet:
    def __init__(self, *, final_url: str | None = None) -> None:
        self.final_url = final_url
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def __call__(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append((url, kwargs))
        return FakeResponse(self.final_url or url)


def seed_documents(tmp_path, *, external_first: bool = False):
    db_path = tmp_path / "enrichment.db"
    initialize_database(db_path, seed_demo=True)
    with connect_database(db_path) as connection:
        source = search_sources_by_ente(connection, "INPS")[0]
        for index, (code, title) in enumerate(TITLES.items()):
            host = "example.org" if external_first and index == 0 else "www.inps.it"
            insert_document(
                connection,
                AdministrativeDocument(
                    ente="INPS",
                    codice=code,
                    titolo_ufficiale=title,
                    categoria="test",
                    descrizione_ufficiale=title,
                    significato_semplice=None,
                    versione="1.0",
                    data_rilevazione="2026-08-04",
                    stato_verifica="da_verificare",
                    fonte_url="https://www.inps.it/it/it/moduli.html",
                    detail_url=f"https://{host}/moduli/{code.casefold()}.html",
                    download_url=f"https://www.inps.it/moduli/{code}.pdf",
                    data_pubblicazione="2026-08-04",
                    source_id=source.id,
                ),
            )
    return db_path


def test_enrichment_limit_is_hard_capped_at_three() -> None:
    assert validate_enrichment_limit(3) == 3
    with pytest.raises(ValueError):
        validate_enrichment_limit(50)


def test_official_inps_source_is_read_with_bounded_http_options(tmp_path) -> None:
    db_path = seed_documents(tmp_path)
    fake_get = FakeGet()
    with connect_database(db_path) as connection:
        report = enrich_inps_documents(
            connection,
            limit=1,
            dry_run=True,
            request_get=fake_get,
            source_access_date="2026-08-04",
            timestamp="2026-08-04T12:00:00+00:00",
        )

    assert report.previewed == 1
    assert report.errors == 0
    assert len(fake_get.calls) == 1
    url, options = fake_get.calls[0]
    assert url.startswith("https://www.inps.it/")
    assert options["timeout"] == (5, 20)
    assert options["allow_redirects"] is True
    assert "BurOCRazia/0.4" in options["headers"]["User-Agent"]


def test_external_document_source_is_rejected_before_request(tmp_path) -> None:
    db_path = seed_documents(tmp_path, external_first=True)
    fake_get = FakeGet()
    with connect_database(db_path) as connection:
        report = enrich_inps_documents(
            connection,
            limit=1,
            dry_run=True,
            request_get=fake_get,
        )

    assert report.previewed == 0
    assert report.errors == 1
    assert fake_get.calls == []


def test_external_redirect_is_rejected(tmp_path) -> None:
    db_path = seed_documents(tmp_path)
    fake_get = FakeGet(final_url="https://example.org/copia.html")
    with connect_database(db_path) as connection:
        report = enrich_inps_documents(
            connection,
            limit=1,
            dry_run=True,
            request_get=fake_get,
        )

    assert report.previewed == 0
    assert report.errors == 1


def test_dry_run_previews_three_without_writing(tmp_path) -> None:
    db_path = seed_documents(tmp_path)
    with connect_database(db_path) as connection:
        before = len(list_explanations(connection))
        report = enrich_inps_documents(
            connection,
            limit=3,
            dry_run=True,
            request_get=FakeGet(),
            source_access_date="2026-08-04",
            timestamp="2026-08-04T12:00:00+00:00",
        )
        after = len(list_explanations(connection))

    assert before == after == 0
    assert report.examined == report.previewed == 3
    assert report.saved == 0


def test_second_commit_avoids_duplicate_explanations(tmp_path) -> None:
    db_path = seed_documents(tmp_path)
    with connect_database(db_path) as connection:
        first = enrich_inps_documents(
            connection,
            limit=3,
            dry_run=False,
            request_get=FakeGet(),
            source_access_date="2026-08-04",
            timestamp="2026-08-04T12:00:00+00:00",
        )
        second = enrich_inps_documents(
            connection,
            limit=3,
            dry_run=False,
            request_get=FakeGet(),
            source_access_date="2026-08-04",
            timestamp="2026-08-04T13:00:00+00:00",
        )
        stored = list_explanations(connection)

    assert first.saved == 3
    assert second.saved == 0
    assert second.duplicates_avoided == 3
    assert len(stored) == 3


def test_generated_drafts_keep_facts_explanation_and_missing_data_separate(
    tmp_path,
) -> None:
    db_path = seed_documents(tmp_path)
    with connect_database(db_path) as connection:
        report = enrich_inps_documents(
            connection,
            limit=3,
            dry_run=True,
            request_get=FakeGet(),
            source_access_date="2026-08-04",
            timestamp="2026-08-04T12:00:00+00:00",
        )

    assert len(report.explanations) == 3
    for explanation in report.explanations:
        assert explanation.facts_from_source
        assert explanation.source_url.startswith("https://www.inps.it/")
        assert explanation.simple_explanation != explanation.official_summary
        assert explanation.simple_explanation is not None
        assert len(explanation.simple_explanation) <= 600
        assert explanation.missing_information
        assert explanation.verification_status == "da_verificare"
        assert explanation.verified_by is None
        assert explanation.verified_at is None
        for value in (
            explanation.official_summary,
            explanation.simple_explanation,
            explanation.intended_use,
        ):
            assert value is None or value != ""

