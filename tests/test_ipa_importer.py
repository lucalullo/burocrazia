from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from src.database import connect_database, initialize_database, list_documents
from src.entities import get_entity_by_ipa_code, list_entities
from src.importers.common import validate_batch_limit
from src.importers.ipa import (
    IPA_DATA_API,
    IPA_RESOURCE_ID,
    fetch_ipa_entities,
    import_ipa_entities,
    parse_ipa_payload,
)
from src.official_urls import is_official_ipa_url


FIXTURE = Path(__file__).parent / "fixtures" / "ipa_entities.json"


def load_payload() -> dict[str, object]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class FakeResponse:
    status_code = 200

    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self.payload


class FakeGet:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.calls: list[tuple[str, dict[str, object]]] = []

    def __call__(self, url: str, **kwargs: object) -> FakeResponse:
        self.calls.append((url, kwargs))
        return FakeResponse(copy.deepcopy(self.payload))


def test_ipa_fixture_extracts_code_category_and_site() -> None:
    batch = parse_ipa_payload(load_payload(), limit=4)

    assert batch.examined == 4
    assert batch.discarded == 2
    assert batch.total_available == 10452
    assert len(batch.entities) == 2
    assert batch.entities[0].codice_ipa == "agid"
    assert batch.entities[0].denominazione == "Agenzia per l'Italia Digitale"
    assert batch.entities[0].categoria == "Agenzie ed enti per il digitale"
    assert batch.entities[0].sito_istituzionale == "https://www.agid.gov.it/"
    assert batch.entities[0].livello is None


def test_ipa_fetch_is_one_official_request_with_batch_and_offset() -> None:
    fake_get = FakeGet(load_payload())

    batch = fetch_ipa_entities(limit=2, offset=100, request_get=fake_get)

    assert batch.examined == 2
    assert len(fake_get.calls) == 1
    url, options = fake_get.calls[0]
    assert url == IPA_DATA_API
    assert is_official_ipa_url(url)
    assert options["params"] == {
        "resource_id": IPA_RESOURCE_ID,
        "limit": 2,
        "offset": 100,
    }


def test_batch_limit_supports_100_to_500_and_rejects_more() -> None:
    assert validate_batch_limit(100) == 100
    assert validate_batch_limit(500) == 500
    with pytest.raises(ValueError):
        validate_batch_limit(501)


def test_ipa_dry_run_does_not_write(tmp_path) -> None:
    db_path = tmp_path / "ipa-dry-run.db"
    initialize_database(db_path, seed_demo=True)
    with connect_database(db_path) as connection:
        before_documents = len(list_documents(connection))
        report = import_ipa_entities(
            connection,
            limit=2,
            dry_run=True,
            request_get=FakeGet(load_payload()),
            detection_date="2026-08-05",
        )
        entities = list_entities(connection)
        after_documents = len(list_documents(connection))

    assert report.examined == 2
    assert len(report.entities) == 2
    assert entities == []
    assert before_documents == after_documents == 10


def test_ipa_commit_is_idempotent_and_preserves_catalog_state(tmp_path) -> None:
    db_path = tmp_path / "ipa-commit.db"
    initialize_database(db_path, seed_demo=True)
    fake_get = FakeGet(load_payload())
    with connect_database(db_path) as connection:
        first = import_ipa_entities(
            connection,
            limit=2,
            dry_run=False,
            request_get=fake_get,
            detection_date="2026-08-05",
        )
        second = import_ipa_entities(
            connection,
            limit=2,
            dry_run=False,
            request_get=fake_get,
            detection_date="2026-08-06",
        )
        entities = list_entities(connection)
        agid = get_entity_by_ipa_code(connection, "AGID")

    assert first.new == 2
    assert second.new == 0
    assert second.already_present == 2
    assert len(entities) == 2
    assert agid is not None
    assert agid.stato_catalogazione == "non_analizzato"
    assert agid.last_checked_at == "2026-08-06"


def test_ipa_code_is_the_deduplication_key(tmp_path) -> None:
    db_path = tmp_path / "ipa-update.db"
    initialize_database(db_path, seed_demo=True)
    payload = load_payload()
    with connect_database(db_path) as connection:
        import_ipa_entities(
            connection,
            limit=1,
            dry_run=False,
            request_get=FakeGet(payload),
            detection_date="2026-08-05",
        )
        records = payload["result"]["records"]  # type: ignore[index]
        records[0]["Denominazione_ente"] = "Agenzia per l'Italia Digitale aggiornata"
        report = import_ipa_entities(
            connection,
            limit=1,
            dry_run=False,
            request_get=FakeGet(payload),
            detection_date="2026-08-06",
        )
        entities = list_entities(connection)

    assert report.updated == 1
    assert len(entities) == 1
    assert entities[0].denominazione.endswith("aggiornata")


@pytest.mark.parametrize(
    "url",
    (
        "http://indicepa.gov.it/ipa-dati/api/3/action/datastore_search",
        "https://indicepa.gov.it.example.org/api",
        "https://example.org/ipa",
    ),
)
def test_non_official_ipa_urls_are_rejected(url: str) -> None:
    assert not is_official_ipa_url(url)
