from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import re
import sqlite3

from src.official_urls import is_official_entity_url
from src.recognize import normalize_text


HTML_MARKUP = re.compile(r"<\s*/?\s*(?:html|body|div|span|a|p|script|style)\b", re.I)
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True, slots=True)
class StructuralSampleItem:
    document_id: int
    title: str
    code: str | None
    passed: bool
    problems: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class StructuralSampleReport:
    entity: str
    checked: int
    passed: int
    failed: int
    codes_available: int
    items: tuple[StructuralSampleItem, ...]


def structural_sample(
    connection: sqlite3.Connection,
    entity: str,
    *,
    sample_size: int = 5,
) -> StructuralSampleReport:
    if isinstance(sample_size, bool) or not 1 <= sample_size <= 20:
        raise ValueError("Il campione deve contenere da 1 a 20 documenti.")

    all_rows = connection.execute(
        """
        SELECT id, titolo_ufficiale, versione
        FROM documents
        WHERE ente = ? COLLATE NOCASE AND stato_verifica <> 'demo'
        """,
        (entity,),
    ).fetchall()
    identity_counts = Counter(
        (
            normalize_text(str(row["titolo_ufficiale"])),
            str(row["versione"] or "").casefold().strip(),
        )
        for row in all_rows
    )
    rows = connection.execute(
        """
        SELECT
            d.id, d.titolo_ufficiale, d.codice, d.categoria,
            d.descrizione_ufficiale, d.fonte_url, d.detail_url,
            d.download_url, d.versione, d.data_rilevazione, d.source_id,
            s.id AS registered_source_id, s.stato_verifica AS source_verification,
            s.attiva AS source_active,
            p.source_id AS provenance_source_id,
            p.source_status AS provenance_status
        FROM documents AS d
        LEFT JOIN sources AS s ON s.id = d.source_id
        LEFT JOIN document_provenance AS p ON p.document_id = d.id
        WHERE d.ente = ? COLLATE NOCASE AND d.stato_verifica <> 'demo'
        ORDER BY d.id DESC
        LIMIT ?
        """,
        (entity, sample_size),
    ).fetchall()

    items: list[StructuralSampleItem] = []
    for row in rows:
        problems: list[str] = []
        title = str(row["titolo_ufficiale"] or "").strip()
        if not title:
            problems.append("titolo mancante")
        if row["source_id"] is None or row["registered_source_id"] != row["source_id"]:
            problems.append("source_id mancante o non valido")
        urls = [
            str(row[name])
            for name in ("fonte_url", "detail_url", "download_url")
            if row[name]
        ]
        if not urls:
            problems.append("URL mancante")
        elif any(not is_official_entity_url(url, entity) for url in urls):
            problems.append("URL non ufficiale")
        if not ISO_DATE.fullmatch(str(row["data_rilevazione"] or "")):
            problems.append("data acquisizione mancante o non valida")
        text_fields = " ".join(
            str(row[name] or "")
            for name in ("titolo_ufficiale", "categoria", "descrizione_ufficiale")
        )
        if HTML_MARKUP.search(text_fields):
            problems.append("HTML grezzo nei metadati")
        identity = (
            normalize_text(title),
            str(row["versione"] or "").casefold().strip(),
        )
        if title and identity_counts[identity] > 1:
            problems.append("duplicato evidente titolo/versione")
        if not (
            row["source_verification"] == "verificato"
            and bool(row["source_active"])
            and row["provenance_source_id"] == row["source_id"]
            and row["provenance_status"] == "rilevato"
        ):
            problems.append("provenienza ufficiale non tracciata")
        items.append(
            StructuralSampleItem(
                document_id=int(row["id"]),
                title=title,
                code=str(row["codice"]) if row["codice"] else None,
                passed=not problems,
                problems=tuple(problems),
            )
        )

    passed = sum(item.passed for item in items)
    return StructuralSampleReport(
        entity=entity,
        checked=len(items),
        passed=passed,
        failed=len(items) - passed,
        codes_available=sum(item.code is not None for item in items),
        items=tuple(items),
    )


def format_structural_sample(report: StructuralSampleReport) -> str:
    lines = [
        f"Campione strutturale {report.entity}: {report.passed}/{report.checked} conforme",
        f"Codice disponibile: {report.codes_available}/{report.checked}",
    ]
    for item in report.items:
        outcome = "OK" if item.passed else "; ".join(item.problems)
        lines.append(f"- #{item.document_id} {item.title}: {outcome}")
    return "\n".join(lines)
