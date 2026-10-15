"""Lock Round 12 measurements and verify preservation; not an engine freeze."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from benchmarks.round3_audit import read
from benchmarks.round9_performance import describe
from benchmarks.transactional_writer import atomic_json
from benchmarks.unknown_release import validate, select
from src.benchmark_display import load_summary

BASELINE = 'd911fccae4042c5c720a22d9e8767793a9aec61d'
OUT = ROOT / 'benchmarks/results/round12'


def digest(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def main():
    for path in ['data/catalog_seed.sqlite3', 'data/document_recognition_fingerprints_v3.json',
                 'benchmarks/manifests/official_unknown_master_v1.json', 'benchmarks/manifests/official_unknown_release_v1.json']:
        assert (ROOT / path).read_bytes() == subprocess.check_output(['git', 'show', BASELINE + ':' + path], cwd=ROOT), path
    master = validate(read('benchmarks/manifests/official_unknown_master_v1.json'))
    release = validate(read('benchmarks/manifests/official_unknown_release_v1.json'))
    assert [c['case_id'] for c in select(master['cases'])] == [c['case_id'] for c in release['cases']]
    for c in master['cases']:
        assert digest('benchmarks/cache/' + c['SHA256'] + '.body') == c['SHA256']
    unknown = read('benchmarks/results/round12/unknown_release_v1.json')
    assert unknown['status'] == 'not_run' and unknown['recognition_calls'] == unknown['actual_count'] == 0
    assert unknown['manifest_sha256'] == digest('benchmarks/manifests/official_unknown_release_v1.json')
    assert unknown['rejection_rate'] is None and not unknown['cases']
    perf = read('benchmarks/results/round12/performance_stability.json')
    assert perf['status'] == 'complete' and len(perf['runs']) == 5
    ids = {r['id'] for r in perf['corpus']}
    assert len(ids) == 67
    for run in perf['runs']:
        assert len(run['samples']) == run['sample_count'] == 402
        assert Counter(r['case_id'] for r in run['samples']) == Counter({i: 6 for i in ids})
        assert describe([r['milliseconds'] for r in run['samples']]) == run['latency_ms']
    assert statistics.median(r['latency_ms']['p95'] for r in perf['runs']) == perf['median_p95']
    recovery = read('benchmarks/results/round12/recovery_attempts.json')
    assert recovery['temporary_converted_outputs_deleted'] and not recovery['native_additions']
    for item in recovery['derived_legacy_bindings']:
        assert not item['runtime_supported']
        assert digest('benchmarks/cache/' + item['original_sha256'] + '.body') == item['original_sha256']
    archives = {}
    for number in [8, 9, 10, 11]:
        previous = read(f'dist/package-verification-round{number}.json')
        path = 'dist/' + previous['archive']
        assert digest(path) == previous['sha256']
        archives[previous['archive']] = previous['sha256']
    latest = load_summary(ROOT / 'benchmarks/latest_summary.json')
    assert latest['round'] == 12 and latest['status'] == 'NOT READY'
    for name in ['known_robustness', 'scan_ocr', 'filled_forms', 'unknown_official']:
        assert latest[name]['status'] == 'not_run' and not latest[name]['summary']['metrics']
    gates = read('docs/release_gates.json')
    assert gates['round'] == 12 and gates['freeze'] is None and gates['tests']['status'] == 'passed'
    for p in OUT.iterdir():
        if p.suffix in {'.json', '.csv', '.md'}:
            assert not re.search(rb'C:\\+(?:Users|users)\\', p.read_bytes()), p.name
    for path, sha in read('benchmarks/results/round8/baseline/metrics.json')['prior_raw_sha256'].items():
        assert digest(path) == sha
    atomic_json(OUT / 'prepackage_audit.json', dict(status='verified', unknown_official_hashes_verified=len(master['cases']),
                release_selection_reproducible=True, release_recognition_calls=0, performance_runs_verified=5,
                performance_samples_verified=2010, prior_archives_sha256=archives,
                prior_fingerprint_bundle_sha256=digest('data/document_recognition_fingerprints_v3.json'),
                runtime_catalog_fingerprints_unchanged=True, converted_outputs_deleted=True, summary_contract='valid'))
    historical = {}
    old = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', BASELINE,
                                  *[f'benchmarks/results/round{n}' for n in [6, 7, 8, 9, 10, 11]]], cwd=ROOT, text=True).splitlines()
    old += ['benchmarks/manifests/official_unknown_v1.json', 'benchmarks/manifests/official_unknown_v2.json',
            'benchmarks/manifests/official_unknown_master_v1.json', 'benchmarks/manifests/official_unknown_release_v1.json',
            'benchmarks/reference/reference_truth_v2.json', 'benchmarks/reference/reference_truth_v2_round10_addendum.json',
            'benchmarks/reference/reference_truth_v2_round11_addendum.json', 'data/recognition_profiles/fingerprint_decision_v5.json',
            'docs/ROUND11_REPORT.md', 'docs/ROUND11_BASELINE_AUDIT.md']
    for path in old:
        raw = subprocess.check_output(['git', 'show', BASELINE + ':' + path], cwd=ROOT)
        current = (ROOT / path).read_bytes()
        assert current == raw or current.replace(b'\r\n', b'\n') == raw, path
        historical[path] = hashlib.sha256(raw).hexdigest()
    paths = [p for p in OUT.iterdir() if p.suffix in {'.json', '.csv', '.md'} and p.name != 'evidence_locks.json']
    paths.extend(ROOT / p for p in ['docs/ROUND12_BASELINE_AUDIT.md', 'docs/ROUND12_REPORT.md', 'docs/BENCHMARK.md',
                                  'docs/FINGERPRINT_COVERAGE_AUDIT.md', 'docs/release_gates.json', 'benchmarks/latest_summary.json'])
    hashes = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}
    atomic_json(OUT / 'evidence_locks.json', dict(schema_version=1, status='NOT READY', baseline_commit=BASELINE,
                sha256=hashes, historical_original_git_sha256=historical,
                scope='Evidence locks only, not a freeze. R6-R11 raw, corpus, unknown manifest and prior fingerprint bytes preserved; no release prediction or v5 started.'))
    print('R12 evidence locked', len(hashes), 'historical', len(historical), flush=True)


if __name__ == '__main__':
    main()
