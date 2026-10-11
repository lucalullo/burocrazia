"""Release evaluation: exact identities, group bootstrap, coverage and timings."""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import closing
from datetime import UTC, datetime
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import random
import sqlite3
import subprocess
import sys
import time
import tracemalloc

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.benchmark import load_corpus, evaluate_case, ratio, OUTCOMES
from src.database import list_documents
from src.families import list_document_families
from src.recognize import recognize_catalog, catalog_revision, RULES_VERSION, _catalog_features


def quantile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * fraction
    lower = int(index)
    return round(ordered[lower] + (ordered[min(lower + 1, len(ordered)-1)] - ordered[lower]) * (index-lower), 4)


def metrics(rows):
    expected = Counter(r["expected"]["match_type"] for r in rows)
    observed = Counter(r["observed"]["match_type"] for r in rows)
    tp_doc = sum(r["document_correct"] for r in rows)
    tp_family = sum(r["family_correct"] for r in rows)
    unknown = [r for r in rows if r["expected"]["match_type"] == "NO_MATCH"]
    rejected = sum(r["observed"]["match_type"] == "NO_MATCH" for r in unknown)
    supported = expected["DOCUMENT_MATCH"] + expected["FAMILY_MATCH"]
    result = {}
    for label, tp, outcome in [("document", tp_doc, "DOCUMENT_MATCH"), ("family", tp_family, "FAMILY_MATCH")]:
        # A labelled family fallback on an exact-document case is useful, but
        # the family recall denominator must include those labelled cases.
        targets = sum(r["expected"].get("family_id") is not None for r in rows) if label == "family" else expected[outcome]
        result[label+"_precision"] = ratio(tp, observed[outcome])
        result[label+"_recall"] = ratio(tp, targets)
        result[label+"_f1"] = ratio(2*tp, observed[outcome]+targets)
    result.update(exact_document_coverage=ratio(tp_doc, expected["DOCUMENT_MATCH"]),
                  useful_coverage=ratio(tp_doc+tp_family, supported),
                  unknown_false_acceptance_rate=ratio(len(unknown)-rejected, len(unknown)),
                  unknown_correct_rejection_rate=ratio(rejected, len(unknown)),
                  supported_rejection_rate=ratio(sum(r["observed"]["match_type"]=="NO_MATCH" and r["expected"]["match_type"]!="NO_MATCH" for r in rows), supported),
                  entity_error_rate=ratio(sum(r["entity_error"] for r in rows),sum(r["entity_labelled"] for r in rows)),
                  version_year_error_rate=ratio(sum(r["version_error"] for r in rows),sum(r["version_labelled"] for r in rows)))
    return result


def summary(rows):
    matrix = {wanted: {actual: 0 for actual in OUTCOMES} for wanted in OUTCOMES}
    for row in rows:
        matrix[row["expected"]["match_type"]][row["observed"]["match_type"]] += 1
    return dict(cases=len(rows), passed=sum(r["correct"] for r in rows), failed=sum(not r["correct"] for r in rows),
                metrics=metrics(rows), confusion_matrix=matrix,
                latency_ms={"p50": quantile([r["matching_ms"] for r in rows],.5),
                            "p95": quantile([r["matching_ms"] for r in rows],.95),
                            "p99": quantile([r["matching_ms"] for r in rows],.99) if len(rows)>=100 else None})


def bootstrap(rows, repetitions=500):
    groups = {}
    for row in rows:
        groups.setdefault(row["group"], []).append(row)
    if len(groups) < 5:
        return {"method": "group_percentile", "groups": len(groups), "intervals": None, "reason": "Meno di cinque gruppi"}
    rng = random.Random(20261011)
    samples = {k: [] for k in metrics(rows)}
    keys = sorted(groups)
    for _ in range(repetitions):
        sample = [r for key in rng.choices(keys, k=len(keys)) for r in groups[key]]
        for key, value in metrics(sample).items():
            if value["value"] is not None:
                samples[key].append(value["value"])
    return dict(method="group_percentile", confidence=.95, repetitions=repetitions, seed=20261011, groups=len(keys),
                limits="Intervalli descrittivi del corpus pubblico; possono degenerare con zero errori e non stimano il rischio su documenti reali.",
                intervals={k: [quantile(v,.025),quantile(v,.975)] if v else None for k,v in samples.items()})


def canonical_cases(documents):
    return [dict(id="C"+str(d.id),group="document:"+str(d.id),category=d.categoria or "unspecified",source=d.ente,noise="canonical_metadata",
                 text="\n".join(x for x in [d.ente, d.codice, d.titolo_ufficiale, "Versione "+d.versione if d.versione else None] if x),
                 expected=dict(match_type="DOCUMENT_MATCH",document_id=d.id,entity=d.ente,version=d.versione))
            for d in documents if d.stato_verifica not in {"demo","rifiutato"}]


def code_hash():
    files = sorted([*ROOT.glob("src/**/*.py"), *ROOT.glob("maintenance/*.py"), *ROOT.glob("benchmarks/*.py"), ROOT/"scripts/benchmark.py", ROOT/"app.py",ROOT/"run.py"])
    return hashlib.sha256(b"".join(str(p.relative_to(ROOT)).replace("\\","/").encode()+b"\0"+p.read_bytes()+b"\0" for p in files)).hexdigest()


def run(catalog, corpus_path=None, *, coverage=False, intervals=True):
    started = time.perf_counter()
    with closing(sqlite3.connect(Path(catalog).resolve().as_uri()+"?mode=ro",uri=True)) as db:
        db.row_factory=sqlite3.Row
        documents, families = list_documents(db), list_document_families(db)
    load_ms=(time.perf_counter()-started)*1000
    _catalog_features.cache_clear()
    preparing=time.perf_counter()
    for document in documents:_catalog_features(document)
    prepare_ms=(time.perf_counter()-preparing)*1000
    if coverage:
        cases=canonical_cases(documents)
        corpus=dict(corpus_id="catalog-canonical-coverage-v1",split="catalog_coverage",synthetic=True,cases=cases)
        corpus_hash=hashlib.sha256(json.dumps(corpus,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    else:
        corpus,corpus_hash=load_corpus(corpus_path)
        cases=corpus["cases"]
    rows=[]
    for case in cases:
        start=time.perf_counter()
        result=recognize_catalog(case["text"],documents,families)
        row=evaluate_case(case,result,(time.perf_counter()-start)*1000)
        row.update(source=case.get("source",case["expected"].get("entity","unspecified")),noise=case.get("noise","unspecified"),prefiltered_candidates=len(documents))
        rows.append(row)
    # Memory instrumentation is separate so latency is not distorted.
    _catalog_features.cache_clear()
    tracemalloc.start()
    if cases:
        recognize_catalog(cases[0]["text"],documents,families)
    _,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    breakdown={}
    for field in ["source","category","noise"]:
        breakdown[field]={key:summary([r for r in rows if r[field]==key]) for key in sorted({r[field] for r in rows})}
    macro={key:(sum(v)/len(v) if v else None) for key in metrics(rows) for v in [[s["metrics"][key]["value"] for s in breakdown["source"].values() if s["metrics"][key]["value"] is not None]]}
    git_commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    report=dict(schema_version=2,executed_at=datetime.now(UTC).isoformat(),corpus_id=corpus["corpus_id"],split=corpus["split"],
                synthetic=corpus.get("synthetic",True),purpose=corpus.get("purpose","Canonical metadata self-coverage; no generalization claim."),
                identity=dict(corpus_sha256=corpus_hash,catalog_file_sha256=hashlib.sha256(Path(catalog).read_bytes()).hexdigest(),
                              catalog_semantic_sha256=catalog_revision(documents,families),rules_version=RULES_VERSION,code_sha256=code_hash(),
                              git_commit=git_commit,working_tree_dirty=bool(subprocess.check_output(["git","status","--porcelain"],cwd=ROOT,text=True).strip())),
                environment=dict(python=platform.python_version(),system=platform.system(),machine=platform.machine(),rapidfuzz=version("rapidfuzz")),
                catalog=dict(real_documents=sum(d.stato_verifica!="demo" for d in documents),demo_documents=sum(d.stato_verifica=="demo" for d in documents),families=len(families)),
                summary=summary(rows),by=breakdown,macro_by_source=macro,cases=rows,
                performance=dict(catalog_load_ms=round(load_ms,3),catalog_feature_prepare_ms=round(prepare_ms,3),index_build_ms=None,index="full_scan_with_catalog_metadata_cache",peak_traced_python_bytes=peak,
                                 metadata_cache_max_entries=4096,
                                 memory_scope="one recognition with cold catalog metadata cache, Python allocations only; excludes native heap and catalog loading",catalog_size=len(documents)),
                bootstrap=bootstrap(rows) if intervals else None)
    if coverage:
        report["coverage"]=dict(documents_tested=len(rows),exact=sum(r["document_correct"] for r in rows),family_fallback=sum(r["observed"]["match_type"]=="FAMILY_MATCH" for r in rows),
                                no_match=sum(r["observed"]["match_type"]=="NO_MATCH" for r in rows),wrong_identity=sum(r["observed"]["match_type"]=="DOCUMENT_MATCH" and not r["document_correct"] for r in rows),
                                entity_errors=sum(r["entity_error"] for r in rows),version_errors=sum(r["version_error"] for r in rows))
    return report


def verify_locks():
    locks=json.loads((ROOT/"benchmarks/manifests/corpus_locks_v1.json").read_text(encoding="utf-8"))["sha256"]
    for name,digest in locks.items():
        if hashlib.sha256((ROOT/"benchmarks/corpora"/name).read_bytes()).hexdigest()!=digest:
            raise ValueError("Corpus congelato modificato: "+name)
    file_locks=json.loads((ROOT/'benchmarks/manifests/file_corpus_locks_v1.json').read_text(encoding='utf-8'))['sha256']
    for name,digest in file_locks.items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('Manifest file congelato modificato: '+name)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--catalog",type=Path,default=ROOT/"data/catalog_seed.sqlite3")
    p.add_argument("--output-dir",type=Path,default=ROOT/"benchmarks/results/candidate")
    p.add_argument("--coverage",action="store_true")
    p.add_argument("--no-intervals",action="store_true")
    p.add_argument("--fast",action="store_true",help="Tre corpus testuali, senza bootstrap; niente OCR o rete")
    args=p.parse_args(argv)
    verify_locks()
    args.output_dir.mkdir(parents=True,exist_ok=True)
    reports=[]
    for name in ["development_regression","release_locked_v1","hard_negatives_v1"]:
        report=run(args.catalog,ROOT/"benchmarks/corpora"/(name+".json"),intervals=not (args.no_intervals or args.fast))
        (args.output_dir/(name+".json")).write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(name,report["summary"]["passed"],"/",report["summary"]["cases"],flush=True)
        reports.append(report)
    if args.coverage:
        report=run(args.catalog,coverage=True,intervals=False)
        (args.output_dir/"catalog_coverage.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print("coverage",report["coverage"],flush=True)
    return int(any(r["summary"]["failed"] for r in reports))


if __name__=="__main__":
    raise SystemExit(main())
