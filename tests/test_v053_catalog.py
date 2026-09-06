from __future__ import annotations

from src.catalog_metrics import format_catalog_status, get_catalog_metrics
from src.catalog_quality import structural_sample
from src.database import connect_database, initialize_database, insert_document
from src.models import AdministrativeDocument, DocumentProvenance
from src.provenance import upsert_document_provenance
from src.sources import search_sources_by_ente


def test_catalog_status_separates_provenance_review_and_source_coverage(tmp_path) -> None:
    db_path = tmp_path / "metrics.db"
    initialize_database(db_path, seed_demo=True)
    with connect_database(db_path) as connection:
        output = format_catalog_status(get_catalog_metrics(connection))

    assert "COPERTURA PER FONTE/IMPORTATORE:" in output
    assert "completa_rispetto_alla_fonte" in output
    assert "PROVENIENZA UFFICIALE TRACCIATA:" in output
    assert "CONTENUTI REVISIONATI MANUALMENTE: 0" in output
    assert "IMPORTATORI TOTALI: 8" in output


def test_structural_sample_checks_official_provenance_without_requiring_code(
    tmp_path,
) -> None:
    db_path = tmp_path / "quality.db"
    initialize_database(db_path, seed_demo=True)
    with connect_database(db_path) as connection:
        source = search_sources_by_ente(connection, "INPS")[0]
        assert source.id is not None
        document_id = insert_document(
            connection,
            AdministrativeDocument(
                ente="INPS",
                codice=None,
                titolo_ufficiale="Modulo ufficiale senza codice esposto",
                categoria="previdenza",
                descrizione_ufficiale="Metadato ufficiale di prova.",
                significato_semplice=None,
                versione=None,
                data_rilevazione="2026-08-10",
                stato_verifica="da_verificare",
                fonte_url="https://www.inps.it/it/it/moduli.html",
                detail_url="https://www.inps.it/it/it/moduli/dettaglio.html",
                source_id=source.id,
            ),
        )
        upsert_document_provenance(
            connection,
            DocumentProvenance(
                document_id=document_id,
                source_id=source.id,
                listing_url="https://www.inps.it/it/it/moduli.html",
                detail_url="https://www.inps.it/it/it/moduli/dettaglio.html",
                download_url=None,
                acquired_at="2026-08-10",
                last_seen_at="2026-08-10",
                content_hash="fixture",
                acquisition_method="inps_json",
                source_status="rilevato",
            ),
        )
        report = structural_sample(connection, "INPS", sample_size=5)

    assert report.checked == 1
    assert report.passed == 1
    assert report.codes_available == 0
