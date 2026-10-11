import hashlib
import json

import pytest

from scripts.benchmark import DEFAULT_CORPUS, PROJECT_ROOT, evaluate_case, load_corpus, main, ratio, run_benchmark, summarize
from src.models import AdministrativeDocument, CatalogRecognitionResult, DocumentFamily


def test_synthetic_corpus_preserves_catalog_and_reports_every_failure():
    seed = PROJECT_ROOT / "data/catalog_seed.sqlite3"
    before = hashlib.sha256(seed.read_bytes()).hexdigest()
    report = run_benchmark()
    assert hashlib.sha256(seed.read_bytes()).hexdigest() == before
    manifest=json.loads((PROJECT_ROOT/'data/catalog_manifest.json').read_text(encoding='utf-8'))
    assert report["catalog"] == {"documents_real": manifest['real_documents'], "documents_demo": 10, "families": 16}
    assert report["summary"]["cases"] >= 25
    assert report["split"] == "development_regression"
    assert report["acquisition"]["evaluated"] is False
    assert report["identity"]["corpus_sha256"] == hashlib.sha256(DEFAULT_CORPUS.read_bytes()).hexdigest()
    assert report["summary"]["failed"] == 0, {case["id"]: case["observed"] for case in report["cases"] if not case["correct"]}


def test_metrics_do_not_count_family_fallback_as_exact_or_empty_denominators_as_perfect():
    family = DocumentFamily(id=14, source_id=None, ente="Agenzia delle Entrate", nome="Certificazione Unica", categoria=None,
                            descrizione_ufficiale=None, keywords=(), identifying_phrases=(), official_url=None, stato_verifica="verificato", data_verifica=None)
    expected = {"id": "metric", "group": "metric", "category": "test", "expected": {"match_type": "DOCUMENT_MATCH", "document_id": 53, "family_id": 14, "entity": family.ente, "version": "2026"}}
    result = CatalogRecognitionResult(match_type="FAMILY_MATCH", confidence_document=0, confidence_family=80, family=family)
    row = evaluate_case(expected, result)
    assert not row["correct"] and row["family_correct"]
    metrics = summarize([row])["metrics"]
    assert metrics["exact_coverage"] == ratio(0, 1)
    assert metrics["useful_coverage"] == ratio(1, 1)
    assert metrics["document_precision"] == {"numerator": 0, "denominator": 0, "value": None}
    assert metrics["unknown_correct_rejection"]["value"] is None


def test_entity_version_errors_and_unknown_false_accepts_are_counted_separately():
    document = AdministrativeDocument(id=49, ente="INAIL", codice="730", titolo_ufficiale="730/2026", categoria=None,
                                      descrizione_ufficiale=None, significato_semplice=None, versione="2026", data_rilevazione="2026-01-01", stato_verifica="da_verificare")
    result = CatalogRecognitionResult(match_type="DOCUMENT_MATCH", confidence_document=99, confidence_family=0, document=document)
    supported = {"id": "wrong", "group": "wrong", "category": "test", "expected": {"match_type": "DOCUMENT_MATCH", "document_id": 49, "entity": "Agenzia delle Entrate", "version": "2024"}}
    unknown = {"id": "unknown", "group": "unknown", "category": "unknown", "expected": {"match_type": "NO_MATCH"}}
    rows = [evaluate_case(supported, result), evaluate_case(unknown, result)]
    summary = summarize(rows)
    assert summary["failed"] == 2
    assert summary["metrics"]["entity_errors"] == ratio(1, 1)
    assert summary["metrics"]["version_errors"] == ratio(1, 1)
    assert summary["metrics"]["unknown_false_acceptance"] == ratio(1, 1)
    assert summary["metrics"]["document_precision"] == ratio(0, 2)


def test_ambiguous_known_inputs_do_not_inflate_unknown_rejection():
    case = {"id": "ambiguous", "group": "f24", "category": "ambiguous", "expected": {"match_type": "NO_MATCH"}}
    result = CatalogRecognitionResult(match_type="NO_MATCH", confidence_document=0, confidence_family=0)
    metrics = summarize([evaluate_case(case, result)])["metrics"]
    assert metrics["all_expected_rejections"] == ratio(1, 1)
    assert metrics["unknown_correct_rejection"] == ratio(0, 0)


def test_cli_fails_on_true_regression_and_refuses_overwriting_inputs(tmp_path):
    corpus = json.loads(DEFAULT_CORPUS.read_text())
    corpus["cases"] = [corpus["cases"][0]]
    corpus["cases"][0]["expected"]["document_id"] = 999999
    path, output = tmp_path / "corpus.json", tmp_path / "result.json"
    path.write_text(json.dumps(corpus), encoding="utf-8")
    assert main(["--corpus", str(path), "--output", str(output)]) == 1
    assert json.loads(output.read_text())["failed_case_ids"] == ["EX01"]
    before = path.read_bytes()
    assert main(["--corpus", str(path), "--output", str(path)]) == 2
    assert path.read_bytes() == before


def test_duplicate_case_ids_are_rejected(tmp_path):
    corpus = json.loads(DEFAULT_CORPUS.read_text())
    corpus["cases"].append(corpus["cases"][0])
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(corpus), encoding="utf-8")
    with pytest.raises(ValueError, match="univoche"):
        load_corpus(path)
