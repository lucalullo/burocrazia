from __future__ import annotations

from dataclasses import dataclass
import sqlite3
from typing import Iterable

from src.models import AdministrativeDocument, DocumentFamily


IMPORTER_ENTITIES = {
    "indice delle pubbliche amministrazioni (ipa)",
    "inps",
    "inail",
    "agenzia delle entrate-riscossione",
    "agenzia delle entrate",
    "ministero del lavoro",
    "ispettorato nazionale del lavoro",
    "garante per la protezione dei dati personali",
}
AUTOMATIC_IMPORTER_ENTITIES = {
    "indice delle pubbliche amministrazioni (ipa)",
    "inps",
    "inail",
    "agenzia delle entrate",
    "ministero del lavoro",
    "ispettorato nazionale del lavoro",
    "garante per la protezione dei dati personali",
}
MANUAL_SOURCE_ENTITIES = {"agenzia delle entrate-riscossione"}
BLOCKED_SOURCE_ENTITIES = {"agenzia delle entrate-riscossione"}


@dataclass(frozen=True, slots=True)
class CatalogMetrics:
    entities: int
    entities_with_site: int
    entities_analyzed: int
    entities_not_analyzed: int
    verified_sources: int
    sources_with_importer: int
    automatic_sources: int
    manual_sources: int
    blocked_sources: int
    documents_total: int
    documents_real: int
    documents_demo: int
    pending: int
    verified: int
    official_provenance: int
    manually_reviewed: int
    families: int
    source_coverage: tuple[tuple[str, str, str, int], ...]
    documents_by_entity: tuple[tuple[str, int], ...]
    families_by_entity: tuple[tuple[str, int], ...]


@dataclass(frozen=True, slots=True)
class CatalogSummary:
    real_documents: int
    covered_entities: int
    families: int
    pending: int
    verified: int


def catalog_summary(
    documents: Iterable[AdministrativeDocument],
    families: Iterable[DocumentFamily],
) -> CatalogSummary:
    document_list = list(documents)
    real_documents = [
        document for document in document_list if document.stato_verifica != "demo"
    ]
    covered = {document.ente for document in real_documents}
    return CatalogSummary(
        real_documents=len(real_documents),
        covered_entities=len(covered),
        families=sum(1 for _family in families),
        pending=sum(
            document.stato_verifica == "da_verificare"
            for document in document_list
        ),
        verified=sum(
            document.stato_verifica == "verificato"
            for document in document_list
        ),
    )


def get_catalog_metrics(connection: sqlite3.Connection) -> CatalogMetrics:
    entities = int(connection.execute("SELECT COUNT(*) FROM entities").fetchone()[0])
    entities_with_site = int(
        connection.execute(
            """
            SELECT COUNT(*) FROM entities
            WHERE sito_istituzionale IS NOT NULL AND trim(sito_istituzionale) <> ''
            """
        ).fetchone()[0]
    )
    entities_not_analyzed = int(
        connection.execute(
            "SELECT COUNT(*) FROM entities WHERE stato_catalogazione = 'non_analizzato'"
        ).fetchone()[0]
    )
    entities_analyzed = entities - entities_not_analyzed
    verified_sources = int(
        connection.execute(
            "SELECT COUNT(*) FROM sources WHERE stato_verifica = 'verificato'"
        ).fetchone()[0]
    )
    source_entities = {
        str(row["ente"]).casefold()
        for row in connection.execute(
            "SELECT ente FROM sources WHERE attiva = 1"
        ).fetchall()
    }
    sources_with_importer = len(source_entities.intersection(IMPORTER_ENTITIES))
    automatic_sources = len(
        source_entities.intersection(AUTOMATIC_IMPORTER_ENTITIES)
    )
    manual_sources = len(source_entities.intersection(MANUAL_SOURCE_ENTITIES))
    blocked_sources = len(source_entities.intersection(BLOCKED_SOURCE_ENTITIES))
    documents_total = int(
        connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    )
    documents_demo = int(
        connection.execute(
            "SELECT COUNT(*) FROM documents WHERE stato_verifica = 'demo'"
        ).fetchone()[0]
    )
    pending = int(
        connection.execute(
            "SELECT COUNT(*) FROM documents WHERE stato_verifica = 'da_verificare'"
        ).fetchone()[0]
    )
    verified = int(
        connection.execute(
            "SELECT COUNT(*) FROM documents WHERE stato_verifica = 'verificato'"
        ).fetchone()[0]
    )
    official_provenance = int(
        connection.execute(
            """
            SELECT COUNT(*)
            FROM documents AS d
            JOIN sources AS s ON s.id = d.source_id
            JOIN document_provenance AS p
              ON p.document_id = d.id AND p.source_id = d.source_id
            WHERE d.stato_verifica <> 'demo'
              AND s.attiva = 1
              AND s.stato_verifica = 'verificato'
              AND p.source_status = 'rilevato'
            """
        ).fetchone()[0]
    )
    families = int(
        connection.execute("SELECT COUNT(*) FROM document_families").fetchone()[0]
    )
    by_entity_rows = connection.execute(
        """
        SELECT ente, COUNT(*) AS document_count
        FROM documents
        WHERE stato_verifica <> 'demo'
        GROUP BY ente
        ORDER BY document_count DESC, ente
        """
    ).fetchall()
    family_rows = connection.execute(
        """
        SELECT ente, COUNT(*) AS family_count
        FROM document_families
        GROUP BY ente
        ORDER BY family_count DESC, ente
        """
    ).fetchall()
    coverage_rows = connection.execute(
        """
        SELECT s.ente, s.nome_fonte, s.coverage_status,
               COUNT(d.id) AS document_count
        FROM sources AS s
        LEFT JOIN documents AS d
          ON d.source_id = s.id AND d.stato_verifica <> 'demo'
        GROUP BY s.id
        ORDER BY s.ente, s.id
        """
    ).fetchall()
    return CatalogMetrics(
        entities=entities,
        entities_with_site=entities_with_site,
        entities_analyzed=entities_analyzed,
        entities_not_analyzed=entities_not_analyzed,
        verified_sources=verified_sources,
        sources_with_importer=sources_with_importer,
        automatic_sources=automatic_sources,
        manual_sources=manual_sources,
        blocked_sources=blocked_sources,
        documents_total=documents_total,
        documents_real=documents_total - documents_demo,
        documents_demo=documents_demo,
        pending=pending,
        verified=verified,
        official_provenance=official_provenance,
        manually_reviewed=verified,
        families=families,
        source_coverage=tuple(
            (
                str(row["ente"]),
                str(row["nome_fonte"]),
                str(row["coverage_status"]),
                int(row["document_count"]),
            )
            for row in coverage_rows
        ),
        documents_by_entity=tuple(
            (str(row["ente"]), int(row["document_count"]))
            for row in by_entity_rows
        ),
        families_by_entity=tuple(
            (str(row["ente"]), int(row["family_count"])) for row in family_rows
        ),
    )


def format_catalog_status(metrics: CatalogMetrics) -> str:
    document_lines = [
        f"{entity}: {count}" for entity, count in metrics.documents_by_entity
    ] or ["Nessun documento"]
    family_lines = [
        f"{entity}: {count}" for entity, count in metrics.families_by_entity
    ] or ["Nessuna famiglia"]
    coverage_lines = [
        f"{entity} | {source}: {status} ({count} documenti)"
        for entity, source, status, count in metrics.source_coverage
    ] or ["Nessuna fonte"]
    return "\n".join(
        (
            "ENTI IPA:",
            f"CENSITI: {metrics.entities}",
            f"CON SITO ISTITUZIONALE: {metrics.entities_with_site}",
            f"ANALIZZATI: {metrics.entities_analyzed}",
            f"NON ANALIZZATI: {metrics.entities_not_analyzed}",
            "",
            "FONTI:",
            f"VERIFICATE: {metrics.verified_sources}",
            f"IMPORTATORI TOTALI: {metrics.sources_with_importer}",
            f"CON IMPORTATORE AUTOMATICO: {metrics.automatic_sources}",
            f"MANUALI: {metrics.manual_sources}",
            f"BLOCCATE: {metrics.blocked_sources}",
            "",
            "DOCUMENTI:",
            f"REALI: {metrics.documents_real}",
            f"DEMO: {metrics.documents_demo}",
            f"DA VERIFICARE: {metrics.pending}",
            f"VERIFICATI: {metrics.verified}",
            f"PROVENIENZA UFFICIALE TRACCIATA: {metrics.official_provenance}/{metrics.documents_real}",
            f"CONTENUTI REVISIONATI MANUALMENTE: {metrics.manually_reviewed}",
            "COPERTURA DOCUMENTALE PER ENTE:",
            *document_lines,
            "",
            "COPERTURA PER FONTE/IMPORTATORE:",
            *coverage_lines,
            "",
            "FAMIGLIE:",
            f"TOTALI: {metrics.families}",
            *family_lines,
        )
    )
