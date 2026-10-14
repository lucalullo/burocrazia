"""Seven predetermined paired warm runs; OCR and input preparation are separate."""
from collections import defaultdict
from datetime import UTC, datetime
import hashlib
import json
import os
import platform
import statistics
import time

from benchmarks.round8_common import ROOT, catalog, read, raw_record, identity
from benchmarks.round9_performance import describe
from benchmarks.transactional_writer import atomic_json
from src.extract import extract_document
from src.fingerprint_pages import RequestPages, prepare
from src.fingerprint_v3 import public_index, read_bundle
from src.recognize import recognize_catalog

OUT = ROOT / 'benchmarks/results/round21/performance_stability.json'
SEED = 2026101316


def fresh_request(context):
    return RequestPages(context.texts, context.representation, context.field_set,
                        context.numbers, context.raw, context.filename)


def stability(runs):
    values = [r['latency_ms']['p95'] for r in runs]
    median = statistics.median(values) if values else None
    return dict(completed_runs=len(runs), median_p95=median,
                pass_count=sum(v <= 250 for v in values),
                required_pass=len(runs) == 7 and median <= 250,
                preferred_stability_pass=len(runs) == 7 and sum(v <= 250 for v in values) >= 5,
                preferred_latency_pass=len(runs) == 7 and median <= 180, substantially_over_count=sum(v > 275 for v in values),
                prudent_fragile=len(runs) == 7 and sum(v > 275 for v in values) >= 2)


def suite():
    """Same 35 + 16 + 14 + 2 inputs as the unchanged R9/R11 worker."""
    cases = []
    e2e = []
    for c in read('benchmarks/corpora/development_regression.json')['cases']:
        cases.append(dict(id='synthetic:' + c['id'], text=c['text'], context=RequestPages((c['text'],)), group='historical_fixed51'))
    records = read_bundle()['records']
    for item in read('benchmarks/results/round7/baseline/performance_sample.json')['resources']:
        r = next(r for r in records if r['document_id'] == item['document_id'] and r['canonical_file_sha256'] == item['sha256'])
        raw = raw_record(r)
        name = 'canonical' + ('.pdf' if r['mime_type'] == 'application/pdf' else '.docx')
        ex = extract_document(raw, name)
        cases.append(dict(id='native:' + str(r['document_id']) + ':' + item['sha256'], text=ex.text,
                          context=prepare(raw, name, ex), group='historical_fixed51'))
    chosen, names = [], set()
    for path in sorted((ROOT / 'benchmarks/work/round6-representations').glob('*')):
        if path.suffix not in ['.pdf', '.jpg', '.png']:
            continue
        tag = path.stem.split('-', 1)[-1]
        if tag in ['digital_exact', 'first_page_only'] or tag in names:
            continue
        names.add(tag)
        chosen.append(path)
        if len(chosen) == 14:
            break
    assert len(chosen) == 14, 'Historical scan suite missing; do not reduce the sample'
    for path in chosen:
        raw = path.read_bytes()
        started = time.perf_counter()
        ex = extract_document(raw, path.name)
        e2e.append(dict(id=path.name, sha256=hashlib.sha256(raw).hexdigest(), milliseconds=(time.perf_counter() - started) * 1000))
        cases.append(dict(id='scan:' + path.name, text=ex.text, context=prepare(raw, path.name, ex), group='historical_scans'))
    import pymupdf
    for case in cases[-14:-12]:
        context = case['context']
        assert context.representation == 'image'
        with pymupdf.open() as pdf:
            page = pdf.new_page()
            page.insert_image(page.rect, stream=context.raw)
            raw = pdf.tobytes()
        cases.append(dict(id='wrapped:' + case['id'], text=case['text'],
                          context=RequestPages(context.texts, 'scanned_pdf', numbers=(1,), raw=raw, filename='wrapped.pdf'),
                          group='historical_scans_wrapped_pdf'))
    assert len(cases) == 67
    return cases, e2e


def main():
    if OUT.exists():
        raise ValueError('Stability run already started; preserve the recorded runs')
    from benchmarks import round8_common
    round8_common.SEED = SEED
    ident = identity()
    docs, families = catalog()
    public_index()
    prepared_at = time.perf_counter()
    cases, e2e = suite()
    preparation_ms = (time.perf_counter() - prepared_at) * 1000
    descriptors = [dict(id=c['id'], text_sha256=hashlib.sha256(c['text'].encode()).hexdigest(),
                        representation=c['context'].representation, group=c['group'],
                        raw_sha256=hashlib.sha256(c['context'].raw).hexdigest() if c['context'].raw and not c['id'].startswith('wrapped:') else None)
                   for c in cases]
    environment = dict(python=platform.python_version(), platform=platform.platform(), machine=platform.machine(),
                       processor=os.environ.get('PROCESSOR_IDENTIFIER'), logical_cpus=os.cpu_count(),
                       omp_thread_limit=os.environ.get('OMP_THREAD_LIMIT'), pid=os.getpid(),
                       process='one isolated process, normal priority; no concurrent project CPU jobs')
    try:
        import psutil
        process = psutil.Process()
        environment.update(cpu_affinity=process.cpu_affinity(), priority=str(process.nice()), total_memory=psutil.virtual_memory().total)
    except ImportError:
        environment['affinity_and_priority'] = 'unavailable: psutil absent'
    for c in cases:
        recognize_catalog(c['text'], docs, families, page_context=fresh_request(c['context']))
    result = dict(schema_version=1, identity=ident, status='incomplete', environment=environment,
                  protocol=dict(seed=SEED, predetermined_runs=7, requests_per_run=402, unique_inputs=67,
                                order='Six paired passes A/B/A/B/A/B; A forward, B reverse. Same inputs in every run.',
                                timed_scope='Warm recognition only; extraction/OCR and RequestPages construction excluded; per-request feature generation and lazy visual rendering included.',
                                cached_state='Catalog/public fingerprint index only. Fresh request and memo for every timed invocation.',
                                prudent_fragility_policy='Declared before timing: at least two p95 above275ms (10% over) mark fragile; do not optimize or pick favorable reruns.'),
                  corpus=descriptors, corpus_sha256=hashlib.sha256(json.dumps(descriptors, sort_keys=True).encode()).hexdigest(),
                  preparation_ms=preparation_ms, ocr_end_to_end_samples=e2e,
                  ocr_end_to_end_ms=describe([r['milliseconds'] for r in e2e]), runs=[])
    atomic_json(OUT, result)
    for number in range(1, 8):
        samples, grouped = [], defaultdict(list)
        started, cpu = datetime.now(UTC).isoformat(), time.process_time()
        for repeat in range(6):
            for c in cases if repeat % 2 == 0 else reversed(cases):
                request = fresh_request(c['context'])
                before = time.perf_counter()
                recognize_catalog(c['text'], docs, families, page_context=request)
                elapsed = (time.perf_counter() - before) * 1000
                samples.append(dict(case_id=c['id'], pair_pass=repeat + 1, milliseconds=elapsed))
                grouped[c['group']].append(elapsed)
                grouped['representation:' + request.representation].append(elapsed)
        assert len(samples) == 402 and len({r['case_id'] for r in samples}) == 67
        run = dict(run=number, cold_warm_marker='warm_after_full_suite_warmup', started_at=started,
                   completed_at=datetime.now(UTC).isoformat(), process_cpu_seconds=time.process_time() - cpu,
                   sample_count=len(samples), latency_ms=describe([r['milliseconds'] for r in samples]),
                   by_input_group={k: describe(v) for k, v in grouped.items()}, samples=samples)
        result['runs'].append(run)
        result.update(stability(result['runs']))
        result['status'] = 'complete' if number == 7 else 'incomplete'
        atomic_json(OUT, result)
        print('R21 performance run', number, run['latency_ms'], flush=True)
    print('R21 stability', stability(result['runs']), flush=True)


if __name__ == '__main__':
    main()
