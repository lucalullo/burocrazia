"""Keep legacy observations visible and fail on any deviation from frozen rows.

The legacy CLI intentionally exits 1 on known ambiguous historical labels.
Compare every outcome, not only the exit status. No V6/unknown v4 replay.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ['id', 'expected', 'observed', 'correct', 'entity_error', 'version_error']

def outcomes(data):
    return [{k: row.get(k) for k in FIELDS} for row in data['cases']]

def main():
    target = ROOT / 'benchmark-release-results'
    target.mkdir(exist_ok=True)
    reference = json.loads((ROOT / 'benchmarks/results/round23/legacy_ci_reference.json').read_bytes())
    process = subprocess.run([sys.executable, '-m', 'benchmarks.evaluate', '--fast', '--output-dir', str(target)], cwd=ROOT)
    assert process.returncode == reference['expected_exit_code'], process.returncode
    observed = {}
    for name, expected in reference['reports'].items():
        data = json.loads((target / name).read_bytes())
        rows = outcomes(data)
        assert rows == expected['outcomes'], name
        observed[name] = dict(cases=len(rows), historical_mismatches=sum(not r['correct'] for r in rows), unchanged=True)
    # Frozen release observations are validated as files, never predicted again.
    freeze = json.loads((ROOT / 'benchmarks/results/round23/recognition_freeze_verification.json').read_bytes())
    for p, h in freeze['verified_files'].items():
        raw = (ROOT / p).read_bytes()
        if hashlib.sha256(raw).hexdigest() != h:
            # The pre-existing catalog-manifest CRLF representation has a
            # separately proved Git/archive hash; allow only that exact hash.
            assert p == 'data/catalog_manifest.json', p
            serialization = json.loads((ROOT / 'benchmarks/results/round22/archive_serialization_audit.json').read_bytes())
            proof = next(c for c in serialization['differences'] if c['path'] == p)
            assert hashlib.sha256(raw).hexdigest() == proof['archive_sha256'], p
    for p, h in [('benchmarks/results/round22/evaluation_v6_observations.json', freeze['V6_sha256']),
                 ('benchmarks/results/round21/unknown_release_v4_observations.json', freeze['unknown4_sha256'])]:
        assert hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h, p
    (target / 'round23-ci-validation.json').write_text(json.dumps(dict(passed=True, legacy_exit=process.returncode,
        reports=observed, recognition_freeze=True, new_V6_calls=0, new_unknown4_calls=0), indent=2) + '\n', encoding='utf8')
    print('PASS: all legacy outcomes unchanged; historical mismatches retained; freeze intact')

if __name__ == '__main__':
    main()
