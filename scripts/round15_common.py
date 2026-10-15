"""Round15 additive evidence and immutable engine seal."""
import hashlib,json,subprocess,sys
from datetime import UTC,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from benchmarks.transactional_writer import atomic_json
BASE='425fa010063692d5d8ed090431068ad014d86ee6'
OUT=ROOT/'benchmarks/results/round15'
REGISTRY='benchmarks/reference/benchmark_contamination_registry_v2.json'
SEED=2026101315
def read(p):return json.loads((ROOT/p).read_bytes())
def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def now():return datetime.now(UTC).isoformat()
def head():return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
def save(n,v):return atomic_json(OUT/(n+'.json'),v)
def engine_files():
    from scripts.round14_common import engine_files as files
    return files()
def historical():
    locks=read('benchmarks/results/round14/evidence_locks.json')
    # Live summary/gates/docs will get a new version; every historical source stays locked.
    paths=set(locks['historical_original_git_sha256'])|{p for p in locks['sha256'] if p not in ['benchmarks/latest_summary.json','docs/BENCHMARK.md','docs/release_gates.json']}
    result={}
    for p in sorted(paths):
        old=subprocess.check_output(['git','show',BASE+':'+p],cwd=ROOT);current=(ROOT/p).read_bytes()
        assert current==old or current.replace(b'\r\n',b'\n')==old,p
        result[p]=hashlib.sha256(old).hexdigest()
    return result
def sealed():
    f=read(OUT/'freeze_manifest.json');assert engine_files()==f['engine_files_sha256']
    for p,k in [(REGISTRY,'contamination_registry_sha256'),('benchmarks/reference/reference_truth_v3.json','truth_v3_sha256'),('benchmarks/results/round15/page_limit_audit.json','page_limit_contract_sha256')]:assert sha(p)==f[k],p
    subprocess.run(['git','merge-base','--is-ancestor',f['freeze_git_commit'],'HEAD'],cwd=ROOT,check=True)
    return f
