"""Round16 evidence and performance-only source seals."""
import hashlib,json,subprocess,sys
from pathlib import Path
from datetime import UTC,datetime
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from benchmarks.transactional_writer import atomic_json
BASE='d39103d0673b8690816df1f9a3a4499a46f94f45'
OUT=ROOT/'benchmarks/results/round16'
SEED=2026101316
REGISTRY='benchmarks/reference/benchmark_contamination_registry_v3.json'
TRUTH='benchmarks/reference/reference_truth_v3.json'
POLICY='benchmarks/reference/release_truth_policy_v1.json'
ADDENDUM='benchmarks/reference/reference_truth_v3_round16_addendum.json'
def read(p):return json.loads((ROOT/p).read_bytes())
def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def save(n,v):return atomic_json(OUT/(n+'.json'),v)
def now():return datetime.now(UTC).isoformat()
def head():return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
def historical():
    old=read('benchmarks/results/round15/evidence_locks.json')
    paths=set(old['historical_original_git_sha256'])|{p for p in old['sha256'] if p not in ['docs/BENCHMARK.md','docs/release_gates.json','benchmarks/latest_summary.json']}
    result={}
    for p in sorted(paths):
        original=subprocess.check_output(['git','show',BASE+':'+p],cwd=ROOT)
        current=(ROOT/p).read_bytes();assert current==original or current.replace(b'\r\n',b'\n')==original,p
        result[p]=hashlib.sha256(original).hexdigest()
    return result
def engine_files():
    from scripts.round14_common import engine_files as old
    return dict(old(),**{POLICY:sha(POLICY),ADDENDUM:sha(ADDENDUM)})
def sealed():
    from benchmarks.evaluate import code_hash
    f=read(OUT/'freeze_manifest.json');assert engine_files()==f['engine_files_sha256']
    assert code_hash()==f['benchmark_runner_code_sha256'],'Frozen benchmark/acquisition runner source changed'
    assert sha(REGISTRY)==f['contamination_registry_sha256']
    subprocess.run(['git','merge-base','--is-ancestor',f['freeze_git_commit'],'HEAD'],cwd=ROOT,check=True)
    return f
