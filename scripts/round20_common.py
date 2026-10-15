"""Round20 development evidence and immutable historical release results."""
import hashlib,json,subprocess,sys
from datetime import UTC,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from benchmarks.transactional_writer import atomic_json
BASE='7da8b10f3d7c8ea302d7a3dd565f265bf5c5f370'
OUT=ROOT/'benchmarks/results/round20'
WORK=ROOT/'benchmarks/work/round20'
SEED=2026101420
TRUTH='benchmarks/reference/reference_truth_v3.json'
POLICY='benchmarks/reference/release_truth_policy_v1.json'
ADDENDUM='benchmarks/reference/reference_truth_v3_round16_addendum.json'

def read(p):return json.loads((ROOT/p).read_bytes())
def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def save(n,v):return atomic_json(OUT/(n+'.json'),v)
def now():return datetime.now(UTC).isoformat()
def head():return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
def preserved():
    b=read(OUT/'baseline_audit.json')
    for p,h in b['historical_sha256'].items():
        if p=='benchmarks/results/round18/initial_validation_failure.json':
            # Preserve the original baseline hash; explicitly validate the new
            # portable operator-note version and all unaffected historical data.
            proof=next(r for r in read('benchmarks/reference/local_metadata_privacy_v1.json')['files'] if r['path']==p)
            assert proof['original_sha256']==h and sha(p)==proof['portable_sha256']
            value={k:v for k,v in read(p).items() if k!='temp_note'}
            assert hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()==proof['unaffected_fields_sha256']
        else:assert sha(p)==h,p
    for p,h in b['immutable_data_sha256'].items():assert sha(p)==h,p
    return b

def invariant_data():
    return {p.relative_to(ROOT).as_posix():sha(p) for p in sorted([ROOT/'data/catalog_seed.sqlite3',ROOT/'data/catalog_manifest.json',ROOT/'data/recognition_features.json',*ROOT.glob('data/document_recognition_fingerprints*.json'),*ROOT.glob('data/recognition_profiles/*.json'),*ROOT.glob('benchmarks/reference/reference_truth*.json'),ROOT/POLICY]) if p.name!='fingerprint_decision_v6.json'}
