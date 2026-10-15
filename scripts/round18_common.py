"""Round18 seals: immutable Round16 engine, separately frozen benchmark code."""
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from benchmarks.transactional_writer import atomic_json
from scripts.round16_common import engine_files

BASE = '19807fabafcfe186f14a87f659adb77478e0bcdb'
OUT = ROOT / 'benchmarks/results/round18'
SEED = 20261014
REGISTRY = 'benchmarks/reference/benchmark_contamination_registry_v3.json'
TRUTH = 'benchmarks/reference/reference_truth_v3.json'
POLICY = 'benchmarks/reference/release_truth_policy_v1.json'
ADDENDUM = 'benchmarks/reference/reference_truth_v3_round16_addendum.json'

def read(p): return json.loads((ROOT / p).read_bytes())
def sha(p): return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
def save(n, v): return atomic_json(OUT / (n + '.json'), v)
def now(): return datetime.now(UTC).isoformat()
def head(): return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()

def infrastructure_sha256():
    paths=sorted([ROOT/'scripts/round18_common.py',ROOT/'scripts/round18_freeze.py',ROOT/'scripts/round18_validate.py',ROOT/'tests/test_round18.py',
                  *ROOT.glob('benchmarks/schemas/round18_*.json')])
    return hashlib.sha256(b''.join(p.relative_to(ROOT).as_posix().encode()+b'\0'+p.read_bytes()+b'\0' for p in paths)).hexdigest()

def invariant():
    old = read('benchmarks/results/round16/freeze_manifest.json')
    assert engine_files() == old['engine_files_sha256'], 'Round16 engine/data/truth changed'
    return old

def sealed():
    from benchmarks.evaluate import code_hash
    invariant()
    f = read(OUT / 'freeze_manifest.json')
    assert engine_files() == f['engine_files_sha256']
    assert code_hash() == f['benchmark_runner_code_sha256']
    assert sha(REGISTRY) == f['contamination_registry_sha256']
    assert sha('benchmarks/reference/unknown_release_sampling_policy_v1.json')==f['unknown_sampling_policy_sha256']
    assert sha('benchmarks/manifests/official_unknown_release_v3.json')==f['unknown_manifest_sha256']
    assert infrastructure_sha256() == f['infrastructure_sha256']
    subprocess.run(['git', 'merge-base', '--is-ancestor', f['freeze_git_commit'], 'HEAD'], cwd=ROOT, check=True)
    return f

def historical():
    locks=read('benchmarks/results/round17/historical_locks.json')['historical_original_git_sha256']
    paths=set(locks)|{p.relative_to(ROOT).as_posix() for p in (ROOT/'benchmarks/results/round16').glob('*') if p.is_file()}
    paths|={p.relative_to(ROOT).as_posix() for p in (ROOT/'benchmarks/results/round17').glob('*') if p.is_file()}
    paths|={'docs/ROUND16_REPORT.md','docs/ROUND16_BASELINE_AUDIT.md','docs/ROUND17_REPORT.md','docs/ROUND17_BASELINE_AUDIT.md'}
    result={}
    for p in sorted(paths):
        raw=subprocess.check_output(['git','show',BASE+':'+p],cwd=ROOT)
        actual=(ROOT/p).read_bytes()
        assert actual==raw or actual.replace(b'\r\n',b'\n')==raw,p
        result[p]=hashlib.sha256(raw).hexdigest()
    return result
