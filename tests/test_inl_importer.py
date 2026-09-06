from __future__ import annotations

from pathlib import Path

from src.database import connect_database, initialize_database, list_documents
from src.importers.inl import (
    EMPLOYERS_URL,
    WORKERS_URL,
    InlModule,
    _find_existing,
    fetch_inl_modules,
    import_inl_modules,
    parse_inl_detail_html,
    parse_inl_listing_html,
)
from src.models import AdministrativeDocument


FIXTURES = Path(__file__).parent / "fixtures"


class FakeResponse:
    status_code = 200

    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        return None


class FakeGet:
    def __init__(self, *, include_download: bool = False) -> None:
        self.include_download = include_download
        self.calls: list[str] = []

    def __call__(self, url: str, **_kwargs: object) -> FakeResponse:
        self.calls.append(url)
        if url == WORKERS_URL:
            return FakeResponse((FIXTURES / "inl_workers.html").read_text("utf-8"))
        if url == EMPLOYERS_URL:
            return FakeResponse((FIXTURES / "inl_employers.html").read_text("utf-8"))
        if self.include_download:
            return FakeResponse((FIXTURES / "inl_detail.html").read_text("utf-8"))
        return FakeResponse(
            "<html><body><main><p>Descrizione ufficiale del servizio presente "
            "nella pagina istituzionale dell'Ispettorato Nazionale del Lavoro.</p>"
            "</main></body></html>"
        )


def test_inl_listing_distinguishes_worker_area_and_rejects_external() -> None:
    batch = parse_inl_listing_html(
        (FIXTURES / "inl_workers.html").read_text("utf-8"),
        WORKERS_URL,
        user_type="lavoratori o delegati",
    )

    assert len(batch.modules) == 2
    assert batch.modules[0].tipo_utente == "lavoratori o delegati"
    assert batch.modules[0].area == "Vigilanza"
    assert all("example.org" not in module.detail_url for module in batch.modules)


def test_inl_detail_extracts_description_module_and_code() -> None:
    description, download_url, code = parse_inl_detail_html(
        (FIXTURES / "inl_detail.html").read_text("utf-8"),
        "https://www.ispettorato.gov.it/servizio/richiesta-di-intervento-ispettivo/",
    )

    assert description and description.startswith("Il servizio permette")
    assert download_url and download_url.endswith("richiesta-intervento.pdf")
    assert code == "INL-31"


def test_inl_merges_worker_and_employer_duplicates() -> None:
    batch = fetch_inl_modules(limit=10, request_get=FakeGet())
    access = next(
        module for module in batch.modules if module.titolo_ufficiale == "Accesso documentale"
    )

    assert len(batch.modules) == 3
    assert "lavoratori o delegati" in access.tipo_utente
    assert "datori di lavoro o delegati" in access.tipo_utente


def test_inl_dedup_does_not_merge_distinct_services_with_related_codes() -> None:
    existing = AdministrativeDocument(
        ente="Ispettorato Nazionale del Lavoro",
        codice="INL-17",
        titolo_ufficiale="Accesso documentale",
        categoria="Altro",
        descrizione_ufficiale=None,
        significato_semplice=None,
        versione=None,
        data_rilevazione="2026-08-10",
        stato_verifica="da_verificare",
        detail_url="https://www.ispettorato.gov.it/servizio/accesso-documentale/",
        download_url="https://www.ispettorato.gov.it/files/modulo-condiviso.pdf",
    )
    distinct = InlModule(
        titolo_ufficiale="Accesso civico semplice e generalizzato",
        tipo_utente="lavoratori o delegati",
        area="Altro",
        descrizione_ufficiale=None,
        codice="INL-17",
        fonte_url=WORKERS_URL,
        detail_url="https://www.ispettorato.gov.it/servizio/accesso-civico/",
        download_url="https://www.ispettorato.gov.it/files/modulo-condiviso.pdf",
    )

    assert _find_existing(distinct, [existing]) is None


def test_inl_dry_run_and_commit_are_idempotent(tmp_path) -> None:
    db_path = tmp_path / "inl.db"
    initialize_database(db_path, seed_demo=True)
    fake_get = FakeGet()
    with connect_database(db_path) as connection:
        before = len(list_documents(connection))
        dry = import_inl_modules(
            connection, limit=10, dry_run=True, request_get=fake_get
        )
        assert len(list_documents(connection)) == before
        first = import_inl_modules(
            connection,
            limit=10,
            dry_run=False,
            request_get=fake_get,
            detection_date="2026-08-10",
        )
        second = import_inl_modules(
            connection,
            limit=10,
            dry_run=False,
            request_get=fake_get,
            detection_date="2026-08-11",
        )
        imported = [
            document
            for document in list_documents(connection)
            if document.ente == "Ispettorato Nazionale del Lavoro"
        ]

    assert len(dry.modules) == 3
    assert first.new == 3
    assert second.already_present == 3
    assert len(imported) == 3
    assert all(document.significato_semplice is None for document in imported)
