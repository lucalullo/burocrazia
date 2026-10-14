"""Round22 generator-only boundary and append-only continuity helpers."""
import hashlib,json,sqlite3,subprocess,sys
from datetime import UTC,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from benchmarks.transactional_writer import atomic_json
OUT=ROOT/'benchmarks/results/round22'
WORK=ROOT/'benchmarks/work/round22'
BASE='7da8b10f3d7c8ea302d7a3dd565f265bf5c5f370'
ROUND21_TREE='88f5eb5e16068914dd179af1deb642b4c27a209e'
SEED=202610142106  # Same selected V6 representation seeds, never predicted.
REGISTRY='benchmarks/reference/benchmark_contamination_registry_v7.json'
RESERVED='benchmarks/manifests/v6_reserved_identity_pool.json'
UNKNOWN='benchmarks/manifests/official_unknown_release_v4.json'
POLICY='benchmarks/reference/filled_generation_policy_v2.json'
def read(p):return json.loads((ROOT/p).read_bytes())
def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def now():return datetime.now(UTC).isoformat()
def save(n,v):return atomic_json(OUT/(n+'.json'),v)
def head():return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
def catalog_semantic():
    from contextlib import closing
    with closing(sqlite3.connect((ROOT/'data/catalog_seed.sqlite3').as_uri()+'?mode=ro',uri=True)) as db:return hashlib.sha256('\n'.join(db.iterdump()).encode('utf8')).hexdigest()
def recognition_files():
    return {p.relative_to(ROOT).as_posix():sha(p) for p in sorted([*ROOT.glob('src/**/*.py'),*ROOT.glob('data/recognition_profiles/*.json'),*ROOT.glob('data/document_recognition_fingerprints*.json'),ROOT/'app.py',ROOT/'run.py',ROOT/'data/recognition_features.json',ROOT/'data/catalog_seed.sqlite3',ROOT/'data/catalog_manifest.json'])}
def boundary():
    from benchmarks.round4_common import runtime_hash
    f=read('benchmarks/results/round21/freeze_manifest.json');files=recognition_files()
    assert runtime_hash()==f['recognition_semantic_hash']
    assert all(f['frozen_files_sha256'][p]==h for p,h in files.items())
    assert catalog_semantic()==f['catalog_semantic_sha256']
    u=read('benchmarks/results/round21/unknown_release_v4.json')
    assert sha(UNKNOWN)==u['manifest_sha256'] and sha('benchmarks/results/round21/unknown_release_v4_observations.json')==u['observations_sha256']
    assert u['identity']['runtime_sha256']==runtime_hash() and u['n']==u['correct_no_match']==120 and u['passed']
    if (OUT/'baseline_audit.json').exists():
        for p,h in read(OUT/'baseline_audit.json')['protected_sha256'].items():assert sha(p)==h,p
    return f
def checkpoint(phase,completed,next_command,processes=()):
    private=ROOT/'.codex-context';private.mkdir(exist_ok=True);history=private/'history';history.mkdir(exist_ok=True)
    c=read(private/'CHECKPOINT.json');c.update(updated_at=now(),project='BurOCRazia',phase=phase,last_completed=completed,next_command=next_command,processes=list(processes),head=head(),branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),working_tree=subprocess.check_output(['git','status','--short','--untracked-files=all'],cwd=ROOT,text=True).splitlines(),goal=dict(status='active',scope='Round22'),automation=dict(state='NOT_PRESENT',action='Official Goal active; former heartbeat absent, no scheduled wakeup claimed.'),constraints=['Recognition runtime,decisionv7,ranking,thresholds,profiles,catalog,fingerprints and unknown4 are immutable.','Only generator/validation/runner/docs/new infrastructural tests may change.','Same V6 selected identities/case IDs/seeds; no easier replacement.','V6 single-shot only after generation90%/50valid + all preflights and artifact freeze.','No commit/push/tag/publication/destructive operations.'],remaining=['Round22 authorized generator correction and conditional V6/final verification/package'])
    c['frozen_protocol']=dict(round=22,recognition_sha256=read('benchmarks/results/round21/freeze_manifest.json')['recognition_semantic_hash'],V6_selection_sha256=sha('benchmarks/results/round21/evaluation_v6_plan.json'),unknown_v4_manifest_sha256=sha(UNKNOWN),unknown_v4_result_sha256=sha('benchmarks/results/round21/unknown_release_v4_observations.json'),unknown_recognition_calls_allowed=0,V6_predictions_started=(OUT/'evaluation_v6_started.json').exists(),evaluation_freeze_created=(OUT/'evaluation_freeze_manifest.json').exists(),seed=SEED)
    atomic_json(history/(datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')+'-round22.json'),c);atomic_json(private/'CHECKPOINT.json',c)
