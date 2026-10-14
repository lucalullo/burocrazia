"""Round19 evidence uses the existing semantic freeze, never a new freeze."""
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from benchmarks.transactional_writer import atomic_json
from scripts.round18_common import invariant, engine_files

BASE = 'b3bd9cc61c6af15e8b3ad9958d6e40dcf34a683b'
FREEZE = 'aa816782b075c8a27eabb7492d080d1c26fa3119'
OUT = ROOT / 'benchmarks/results/round19'
SEED = 2026101419
REGISTRY = 'benchmarks/reference/benchmark_contamination_registry_v4.json'
TRUTH = 'benchmarks/reference/reference_truth_v3.json'
POLICY = 'benchmarks/reference/release_truth_policy_v1.json'
ADDENDUM = 'benchmarks/reference/reference_truth_v3_round16_addendum.json'

def read(p): return json.loads((ROOT / p).read_bytes())
def sha(p): return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
def save(n, v): return atomic_json(OUT / (n + '.json'), v)
def now(): return datetime.now(UTC).isoformat()
def head(): return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()

def sealed():
    invariant()
    f = read('benchmarks/results/round18/freeze_manifest.json')
    assert f['freeze_git_commit'] == FREEZE
    assert engine_files() == f['engine_files_sha256']
    subprocess.run(['git', 'merge-base', '--is-ancestor', FREEZE, 'HEAD'], cwd=ROOT, check=True)
    # The R18 inventory includes benchmark code. R19 has a separate inventory;
    # preserve the original seal and every original release/prerequisite byte.
    baseline = read(OUT / 'baseline_audit.json')
    for p, h in baseline['preserved_sha256'].items(): assert sha(p) == h, p
    return f

def benchmark_inventory():
    from benchmarks.evaluate import code_hash
    paths = sorted([*ROOT.glob('scripts/round19_*.py'), *ROOT.glob('benchmarks/round19_*.py'),
                    *ROOT.glob('benchmarks/schemas/round19_*.json'), ROOT/'tests/test_round19.py'])
    return dict(full_code_sha256=code_hash(), files_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in paths if p.exists()})
