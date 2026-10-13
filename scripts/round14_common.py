"""Round 14 evidence/seal utilities. No recognition behavior is changed."""
import hashlib,json,subprocess,sys
from datetime import UTC,datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from benchmarks.transactional_writer import atomic_json

OUT=ROOT/'benchmarks/results/round14'
BASE='19883ba6a1e0e7360716aa0d9bba5ecb52a569eb'
SEED=2026101314
REGISTRY='benchmarks/reference/benchmark_contamination_registry_v1.json'

def read(path):return json.loads((ROOT/path).read_bytes())
def sha(path):return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
def now():return datetime.now(UTC).isoformat()
def head():return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
def save(name,value):return atomic_json(OUT/(name+'.json'),value)

def engine_files():
    files=[*ROOT.glob('src/**/*.py'),ROOT/'app.py',ROOT/'run.py',ROOT/'data/catalog_seed.sqlite3',ROOT/'data/catalog_manifest.json',
           ROOT/'data/recognition_features.json',*ROOT.glob('data/recognition_profiles/*.json'),
           *ROOT.glob('data/document_recognition_fingerprints*.json'),ROOT/'benchmarks/reference/fingerprint_support_definition_v1.json',
           *ROOT.glob('benchmarks/reference/reference_truth*.json')]
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(files))}

def assert_baseline_engine():
    serialization={}
    for p in engine_files():
        old=subprocess.check_output(['git','show',BASE+':'+p],cwd=ROOT)
        current=(ROOT/p).read_bytes()
        if current!=old:
            assert current.replace(b'\r\n',b'\n')==old,'Round14 forbids engine/data changes: '+p
            subprocess.run(['git','diff','--quiet',BASE,'--',p],cwd=ROOT,check=True)
            serialization[p]=dict(workspace_sha256=hashlib.sha256(current).hexdigest(),git_blob_sha256=hashlib.sha256(old).hexdigest(),difference='Preexisting CRLF workspace / LF Git bytes only; Git path unchanged')
    return serialization

def sealed():
    f=read('benchmarks/results/round14/freeze_manifest.json')
    assert engine_files()==f['engine_files_sha256'],'Frozen engine/data changed'
    assert sha(REGISTRY)==f['contamination_registry_sha256'],'Frozen registry changed'
    assert subprocess.check_output(['git','merge-base','--is-ancestor',f['freeze_git_commit'],'HEAD'],cwd=ROOT)==b''
    return f
