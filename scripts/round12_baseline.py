"""Verify the Round 11 entry state and retain the pre-change performance run."""
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from benchmarks.round3_audit import read
from benchmarks.transactional_writer import atomic_json
from benchmarks.unknown_release import balance, select, validate
from benchmarks.round4_common import runtime_hash
from benchmarks.evaluate import code_hash

BASELINE = 'd911fccae4042c5c720a22d9e8767793a9aec61d'
OUT = ROOT / 'benchmarks/results/round12'


def main():
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    assert head == BASELINE
    branch = subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, text=True).strip()
    locks = read('benchmarks/results/round11/evidence_locks.json')['sha256']
    for path, sha in locks.items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == sha, path
    fixed = {c['document_id'] for c in read('benchmarks/results/round6/resource_audit.json')['cases']
             if c['expected_resource_type'] == 'file_backed_document'}
    bundle = read('data/document_recognition_fingerprints_v3.json')
    active = {r['document_id'] for r in bundle['records'] if r['status'] == 'active'}
    from scripts.round11_coverage import EVIDENCE, REJECT
    shared = {r['document_id'] for r in bundle['records'] if r['status'] == 'shared'
              and r['document_id'] in EVIDENCE and r['document_id'] not in REJECT
              and not (r['document_id'] == 1186 and r['canonical_file_sha256'].startswith('319b1ad8773f'))}
    eligible = (active | shared) & fixed
    prior = read('benchmarks/results/round11/coverage_final.json')
    assert sorted(eligible) == prior['eligible_ids']
    target = dict(file_backed_total=len(fixed), current_fingerprinted=len(eligible),
                  minimum_required=math.ceil(.85 * len(fixed)),
                  shortfall=math.ceil(.85 * len(fixed)) - len(eligible),
                  operational_total=1212, initial_file_backed_percent=100 * len(eligible) / len(fixed),
                  unambiguous_identities=len(active), shared_only_supported=len(shared - active),
                  scope='Same fixed R6 denominator and adjudicated R11 resource-support definition.')
    assert (target['file_backed_total'], target['current_fingerprinted'], target['minimum_required'], target['shortfall']) == (1158, 975, 985, 10)
    master = validate(read('benchmarks/manifests/official_unknown_master_v1.json'))
    release = validate(read('benchmarks/manifests/official_unknown_release_v1.json'))
    assert [c['case_id'] for c in select(master['cases'])] == [c['case_id'] for c in release['cases']]
    unknown = balance(release['cases'])
    canonical = read('benchmarks/results/round11/canonical.json')
    assert len(canonical['cases']) == canonical['counts']['exact'] == 980
    hist = [read('benchmarks/results/round11/historical_' + n + '.json') for n in
            ['development_regression', 'release_locked_v1', 'release_locked_v2', 'hard_negatives_v1',
             'hard_negatives_v2', 'family_release_v3', 'development_compat_v2', 'catalog_coverage']]
    no = [c for v in hist for c in v['cases'] if c['expected']['match_type'] == 'NO_MATCH']
    assert len(no) == 241 and all(c['observed']['match_type'] == 'NO_MATCH' for c in no)
    log = (ROOT / 'reports/round12-baseline-performance.log').read_bytes()
    lines = [l for l in log.decode('utf-8-sig').splitlines() if l.startswith('{')]
    assert len(lines) == 1
    perf = json.loads(lines[0])
    assert perf['identity']['runtime_sha256'] == runtime_hash()
    assert perf['identity']['code_sha256'] == code_hash()
    assert perf['identity']['fingerprint_sha256'] == hashlib.sha256((ROOT / 'data/document_recognition_fingerprints_v3.json').read_bytes()).hexdigest()
    perf['phase'] = 'baseline_before_round12_changes'
    perf['stdout_sha256'] = hashlib.sha256(log).hexdigest()
    OUT.mkdir(parents=True, exist_ok=True)
    atomic_json(OUT / 'baseline_performance.json', perf)
    atomic_json(OUT / 'coverage_target.json', target)
    value = dict(branch=branch, commit=head, entry_working_tree='clean; captured before baseline run and script creation',
                 software_version='0.6.1', schema=610, coverage=target, unknown_release=unknown,
                 unknown_master_count=len(master['cases']), unknown_selection_seed=release['selection_seed'],
                 unknown_release_manifest_sha256=hashlib.sha256((ROOT / 'benchmarks/manifests/official_unknown_release_v1.json').read_bytes()).hexdigest(),
                 canonical_counts=canonical['counts'], historical_no=len(no), historical_false_accepts=0,
                 performance=perf['latency_ms'], baseline_performance_identity=perf['identity'],
                 prior_tests=read('benchmarks/results/round11/tests.json'), r11_evidence_locks_verified=len(locks),
                 freeze=None, evaluation_v5='not_run', ci='external_pending')
    atomic_json(OUT / 'baseline_audit.json', value)
    (ROOT / 'docs/ROUND12_BASELINE_AUDIT.md').write_text(f'''# Round 12 baseline audit

Branch `{branch}`, HEAD `{head}`, working tree pulito all'ingresso, prima della misura e della creazione di questo script. Pubblico 0.6.1, schema 610. Verificati {len(locks)} lock delle prove Round 11.

Denominatore ricalcolato dai raw R6: {len(fixed)}. Supportate {len(eligible)} (942 univoche e 33 shared-only); minimo `ceil(0.85 * 1158)` = 985, deficit 10. Nessuna riclassificazione del denominatore.

Master unknown 125, release {unknown['total']}, {unknown['sources']} fonti, concentrazione massima {unknown['max_concentration']:.6%}. Seed {value['unknown_selection_seed']}; selezione ricalcolata identica, manifest SHA `{value['unknown_release_manifest_sha256']}`. Tutti confirmed_unknown; audit preesistente e esposizione storica conservati. Nessuna predizione release eseguita.

Canonical raw 980/980; 241 NO storici, zero false accept. R061, i due NO Round 8 e i cinque critici sono documentati nei raw Round 11. Suite precedente 762 passed / 0 failed / 3 skipped: è una misura storica, non il rerun Round 12.

Baseline performance ripetuta **prima delle modifiche** con il worker isolato R9 invariato: {perf['latency_ms']['n']} richieste warm, p50 {perf['latency_ms']['p50']:.4f} ms, p95 {perf['latency_ms']['p95']:.4f} ms. OCR separato, stesso corpus storico e stesso hardware. I dettagli e gli hash di motore/dataset sono in `baseline_performance.json`; la stabilità su cinque run richiede una misura ulteriore e non è dedotta da questo singolo valore.

Nessun freeze o evaluation v5. CI external_pending. Le successive attività rispettano l'ordine coverage → unknown single-shot → safety → prerequisiti.
''', encoding='utf-8', newline='\n')
    print(json.dumps(dict(coverage=target, unknown=unknown, performance=perf['latency_ms']), ensure_ascii=False))


if __name__ == '__main__':
    main()
