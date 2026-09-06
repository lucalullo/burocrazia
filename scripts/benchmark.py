"""Reproducible synthetic text regression; never modifies the live catalog."""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import closing
from dataclasses import asdict
import hashlib
from importlib.metadata import version as dependency_version
import json
from pathlib import Path
import platform
import sqlite3
import sys
import tempfile
import time

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.bootstrap import prepare_database
from src.database import connect_database, list_documents
from src.families import list_document_families
from src.recognize import RULES_VERSION, recognize_catalog

DEFAULT_CORPUS = PROJECT_ROOT / "tests/fixtures/benchmark.json"
OUTCOMES = ("DOCUMENT_MATCH", "FAMILY_MATCH", "NO_MATCH")


def ratio(numerator: int, denominator: int) -> dict:
    return {"numerator": numerator, "denominator": denominator, "value": numerator / denominator if denominator else None}


def load_corpus(path: str | Path) -> tuple[dict, str]:
    raw = Path(path).read_bytes()
    corpus = json.loads(raw)
    if not isinstance(corpus, dict) or corpus.get("schema_version") != 1 or not isinstance(corpus.get("cases"), list) or not corpus["cases"]:
        raise ValueError("Corpus mancante o schema non supportato.")
    ids = set()
    for case in corpus["cases"]:
        if not isinstance(case, dict) or not isinstance(case.get("id"), str) or case["id"] in ids:
            raise ValueError("Gli identificativi dei casi devono essere stringhe univoche.")
        ids.add(case["id"])
        if not all(isinstance(case.get(field), str) and case[field].strip() for field in ("group", "category", "text")):
            raise ValueError(f"Caso {case['id']}: gruppo, categoria o testo mancante.")
        expected = case.get("expected", {})
        if not isinstance(expected, dict) or expected.get("match_type") not in OUTCOMES:
            raise ValueError(f"Caso {case['id']}: esito atteso non valido.")
        identity = {"DOCUMENT_MATCH": "document_id", "FAMILY_MATCH": "family_id"}.get(expected["match_type"])
        if identity and (not isinstance(expected.get(identity), int) or expected[identity] < 1):
            raise ValueError(f"Caso {case['id']}: identità attesa mancante.")
    return corpus, hashlib.sha256(raw).hexdigest()


def evaluate_case(case: dict, result, elapsed_ms: float = 0.0) -> dict:
    expected, document, family = case["expected"], result.document, result.family
    entity = document.ente if document else family.ente if family else None
    emitted = result.match_type != "NO_MATCH"
    entity_labelled = emitted and ("entity" in expected or bool(expected.get("forbidden_entities")))
    entity_error = entity_labelled and (("entity" in expected and entity != expected["entity"]) or entity in expected.get("forbidden_entities", []))
    version_labelled = document is not None and ("version" in expected or bool(expected.get("forbidden_document_versions")))
    version_error = version_labelled and (("version" in expected and document.versione != expected["version"]) or document.versione in expected.get("forbidden_document_versions", []))
    document_correct = result.match_type == "DOCUMENT_MATCH" and document is not None and document.id == expected.get("document_id") and not entity_error and not version_error
    family_correct = result.match_type == "FAMILY_MATCH" and family is not None and family.id == expected.get("family_id") and not entity_error
    correct = result.match_type == expected["match_type"] and (document_correct or family_correct or result.match_type == "NO_MATCH")
    return {"id": case["id"], "group": case["group"], "category": case["category"], "expected": expected,
            "observed": {"match_type": result.match_type, "document_id": document.id if document else None,
                         "family_id": family.id if family else None, "entity": entity, "version": document.versione if document else None},
            "correct": bool(correct), "document_correct": bool(document_correct), "family_correct": bool(family_correct),
            "entity_labelled": bool(entity_labelled), "entity_error": bool(entity_error), "version_labelled": bool(version_labelled), "version_error": bool(version_error),
            "reason": result.reason, "conflicts": list(result.conflicts), "matching_ms": round(elapsed_ms, 3)}


def summarize(rows: list[dict]) -> dict:
    expected = Counter(row["expected"]["match_type"] for row in rows)
    observed = Counter(row["observed"]["match_type"] for row in rows)
    matrix = {wanted: {actual: 0 for actual in OUTCOMES} for wanted in OUTCOMES}
    for row in rows:
        matrix[row["expected"]["match_type"]][row["observed"]["match_type"]] += 1
    exact = sum(row["document_correct"] for row in rows)
    family = sum(row["family_correct"] for row in rows)
    unknowns = [row for row in rows if row["category"] == "unknown" and row["expected"]["match_type"] == "NO_MATCH"]
    unknown_rejected = sum(row["observed"]["match_type"] == "NO_MATCH" for row in unknowns)
    supported = expected["DOCUMENT_MATCH"] + expected["FAMILY_MATCH"]
    return {"cases": len(rows), "passed": sum(row["correct"] for row in rows), "failed": sum(not row["correct"] for row in rows),
            "confusion_outcomes": matrix, "metrics": {
                "document_precision": ratio(exact, observed["DOCUMENT_MATCH"]), "family_precision": ratio(family, observed["FAMILY_MATCH"]),
                "exact_coverage": ratio(exact, expected["DOCUMENT_MATCH"]), "useful_coverage": ratio(exact + family, len(rows)),
                "unknown_false_acceptance": ratio(len(unknowns) - unknown_rejected, len(unknowns)),
                "unknown_correct_rejection": ratio(unknown_rejected, len(unknowns)),
                "all_expected_rejections": ratio(matrix["NO_MATCH"]["NO_MATCH"], expected["NO_MATCH"]),
                "supported_rejection": ratio(matrix["DOCUMENT_MATCH"]["NO_MATCH"] + matrix["FAMILY_MATCH"]["NO_MATCH"], supported),
                "entity_errors": ratio(sum(row["entity_error"] for row in rows), sum(row["entity_labelled"] for row in rows)),
                "version_errors": ratio(sum(row["version_error"] for row in rows), sum(row["version_labelled"] for row in rows))}}


def run_benchmark(corpus_path: str | Path = DEFAULT_CORPUS, catalog_path: str | Path | None = None) -> dict:
    corpus, corpus_hash = load_corpus(corpus_path)
    source = Path(catalog_path) if catalog_path else PROJECT_ROOT / "data/catalog_seed.sqlite3"
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix="burocrazia-benchmark-") as directory:
        database = Path(directory) / "catalog.sqlite3"
        if catalog_path:
            with closing(sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)) as original, original:
                with closing(sqlite3.connect(database)) as copy, copy:
                    original.backup(copy)
            source_hash = hashlib.sha256(database.read_bytes()).hexdigest()
        prepare_database(database)
        with closing(connect_database(database)) as connection, connection:
            documents, families = list_documents(connection), list_document_families(connection)
            with closing(connection.cursor()) as cursor:
                schema_version = cursor.execute("PRAGMA user_version").fetchone()[0]
        signature = {"documents": [asdict(document) for document in sorted(documents, key=lambda item: item.id or 0)],
                     "families": [asdict(family) for family in sorted(families, key=lambda item: item.id or 0)]}
        # Migration timestamps are operational metadata, not recognition inputs.
        for family in signature["families"]:
            family.pop("created_at", None)
            family.pop("updated_at", None)
        catalog_hash = hashlib.sha256(json.dumps(signature, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        rows, rules_catalog_hash = [], None
        for case in corpus["cases"]:
            started = time.perf_counter()
            result = recognize_catalog(case["text"], documents, families)
            rows.append(evaluate_case(case, result, (time.perf_counter() - started) * 1000))
            rules_catalog_hash = result.catalog_revision
    summary = summarize(rows)
    return {"schema_version": 1, "status": "passed" if not summary["failed"] else "failed", "corpus_id": corpus.get("corpus_id"),
            "purpose": corpus.get("purpose"), "split": corpus.get("split", "unspecified"),
            "limits": ["Casi sintetici pubblici di sviluppo: nessuna stima di generalizzazione o copertura nazionale.",
                       "Solo classificazione di testi leggibili; estrazione, OCR, spiegazioni e risorse ufficiali non sono valutati.",
                       "Demo separate dai record reali nei riepiloghi per categoria; un esito corretto non verifica editorialmente il documento.",
                       "Sconosciuti: solo categoria unknown; i rifiuti per conflitto o ambiguità sono conteggiati separatamente. Denominatore zero: null."],
            "acquisition": {"evaluated": False, "input": "synthetic_readable_text", "errors": None, "formats": None, "ocr": None},
            "identity": {"corpus_sha256": corpus_hash, "catalog_source_sha256": source_hash, "catalog_semantic_sha256": catalog_hash,
                         "recognizer_catalog_revision": rules_catalog_hash, "rules_version": RULES_VERSION,
                         "rules_source_sha256": hashlib.sha256((PROJECT_ROOT / "src/recognize.py").read_bytes()).hexdigest(), "database_schema": schema_version},
            "environment": {"python": platform.python_version(), "system": platform.system(), "machine": platform.machine(), "rapidfuzz": dependency_version("rapidfuzz")},
            "catalog": {"documents_real": sum(document.stato_verifica != "demo" for document in documents),
                        "documents_demo": sum(document.stato_verifica == "demo" for document in documents), "families": len(families)},
            "summary": summary, "summary_excluding_demo": summarize([row for row in rows if row["category"] != "demo"]),
            "by_category": {category: summarize([row for row in rows if row["category"] == category]) for category in sorted({row["category"] for row in rows})},
            "failed_case_ids": [row["id"] for row in rows if not row["correct"]], "cases": rows}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Regressione sintetica text-only sul catalogo completo; database live non modificato.")
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--catalog", type=Path, help="Catalogo alternativo: viene copiato e migrato in una directory temporanea.")
    parser.add_argument("--output", "--path", type=Path, help="Report JSON; se omesso scrive su stdout.")
    args = parser.parse_args(argv)
    try:
        report = run_benchmark(args.corpus, args.catalog)
        output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            protected = {DEFAULT_CORPUS.resolve(), args.corpus.resolve(), (PROJECT_ROOT / "data/burocrazia.db").resolve(), (PROJECT_ROOT / "data/catalog_seed.sqlite3").resolve()}
            if args.catalog:
                protected.add(args.catalog.resolve())
            if args.output.resolve() in protected:
                raise ValueError("Il report non può sovrascrivere corpus o database.")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(output, encoding="utf-8")
        else:
            print(output, end="")
        return 0 if report["status"] == "passed" else 1
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
        print(f"Benchmark non eseguito: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
