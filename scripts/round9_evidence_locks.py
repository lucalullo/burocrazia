"""Lock the final R9 evidence and unchanged historical Git blobs before archive."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from benchmarks.transactional_writer import atomic_json

BASELINE = 'fa2a307fbbb4721ecafa93e6920c909526e00a25'
OUT = ROOT / 'benchmarks/results/round9'


def main():
    gates = json.loads((ROOT / 'docs/release_gates.json').read_bytes())
    assert gates['round'] == 9 and gates['tests']['status'] == 'passed'
    assert gates['freeze'] is None and gates['status'] == 'NOT READY'
    paths = [p for p in OUT.iterdir()
             if p.suffix in {'.json', '.csv', '.md'} and p.name != 'evidence_locks.json']
    paths.extend(ROOT / p for p in [
        'benchmarks/manifests/official_fingerprint_cache_v5.json',
        'benchmarks/manifests/official_unknown_v1.json',
        'benchmarks/reference/reference_truth_v2.json',
        'data/recognition_profiles/fingerprint_decision_v5.json',
        'docs/ROUND9_BASELINE_AUDIT.md', 'docs/REFERENCE_TRUTH_V2.md',
        'docs/ROUND9_REPORT.md', 'docs/BENCHMARK.md', 'docs/release_gates.json',
        'benchmarks/latest_summary.json', 'README.md', 'README_EN.md', 'DATA_NOTICE.md'])
    hashes = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(paths)}
    old_paths = subprocess.check_output([
        'git', 'ls-tree', '-r', '--name-only', BASELINE,
        'benchmarks/results/round6', 'benchmarks/results/round7',
        'benchmarks/results/round8'], cwd=ROOT, text=True).splitlines()
    historical = {}
    for path in old_paths:
        original = subprocess.check_output(['git', 'show', BASELINE + ':' + path], cwd=ROOT)
        current = (ROOT / path).read_bytes()
        assert current == original or current.replace(b'\r\n', b'\n') == original, path
        historical[path] = hashlib.sha256(original).hexdigest()
    atomic_json(OUT / 'evidence_locks.json', dict(
        schema_version=1, status='NOT READY', baseline_commit=BASELINE,
        sha256=hashes, historical_original_git_sha256=historical,
        scope='Final R9 evidence byte hashes. Historical Git bytes are locked separately; '
              'preexisting workspace CRLF differences are audited in verification.json. '
              'This manifest does not hash itself and does not constitute an engine freeze.'))
    print('Locked R9 evidence:', len(hashes), 'historical Git blobs:', len(historical))


if __name__ == '__main__':
    main()
