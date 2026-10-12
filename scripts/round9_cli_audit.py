"""Record actual CLI exit codes, including immutable historical contradictions."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from benchmarks.transactional_writer import atomic_json


def main():
    runs = []
    jobs = [
        ('historical_default', ['scripts/benchmark.py', '--output', 'reports/round9-cli-default.json'], 1),
        ('locked_v2', ['scripts/benchmark.py', '--corpus', 'benchmarks/corpora/release_locked_v2.json',
                       '--output', 'reports/round9-cli-locked-v2.json'], 0),
        ('compat_v2', ['scripts/benchmark.py', '--corpus', 'tests/fixtures/benchmark_v2.json',
                       '--output', 'reports/round9-cli-compat-v2.json'], 0),
        ('historical_fast', ['-m', 'benchmarks.evaluate', '--fast', '--output-dir',
                            'reports/round9-fast'], 1),
    ]
    for name, args, expected in jobs:
        result = subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True)
        assert result.returncode == expected, (name, result.returncode, result.stderr[-2000:])
        row = dict(name=name, command=['python', *args], exit_code=result.returncode,
                   stdout_sha256=hashlib.sha256(result.stdout).hexdigest(),
                   stderr_sha256=hashlib.sha256(result.stderr).hexdigest())
        if '--output' in args:
            report = json.loads((ROOT / args[args.index('--output') + 1]).read_bytes())
            row.update(summary=report['summary'], failed_case_ids=report['failed_case_ids'])
            if name == 'historical_default':
                assert set(report['failed_case_ids']) == {'EX02', 'EX03'}
                assert all(r['observed']['match_type'] == 'NO_MATCH'
                           for r in report['cases'] if not r['correct'])
        else:
            reports = sorted((ROOT / 'reports/round9-fast').glob('*.json'))
            row['corpora'] = {p.stem: json.loads(p.read_bytes()).get('summary') for p in reports}
            base = json.loads((ROOT / 'reports/round9-fast/development_regression.json').read_bytes())
            assert {r['id'] for r in base['cases'] if not r['correct']} == {'EX02', 'EX03'}
        runs.append(row)
        print(name, 'exit', result.returncode, flush=True)
    atomic_json(ROOT / 'benchmarks/results/round9/cli_local.json', dict(
        scope='Local Windows execution. Historical exit1 is retained and explained; '
              'it is not a green CI claim. No network, push or external CI execution.', runs=runs))


if __name__ == '__main__':
    main()
