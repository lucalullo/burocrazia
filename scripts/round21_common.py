"""Round21 append-only evidence; public inputs and immutable prior results."""
import hashlib,json,subprocess,sys
from datetime import UTC,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from benchmarks.transactional_writer import atomic_json
OUT=ROOT/'benchmarks/results/round21'
WORK=ROOT/'benchmarks/work/round21'
BASE='7da8b10f3d7c8ea302d7a3dd565f265bf5c5f370'
ROUND20_TREE='6418922b81883f55885ee294c3dbb30bd3a96e56'
SEED=2026101421
TRUTH='benchmarks/reference/reference_truth_v3.json'
POLICY='benchmarks/reference/release_truth_policy_v1.json'
def read(p):return json.loads((ROOT/p).read_bytes())
def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def save(n,v):return atomic_json(OUT/(n+'.json'),v)
def now():return datetime.now(UTC).isoformat()
def head():return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
def preserved():
    from scripts.round20_common import preserved as previous
    previous();b=read(OUT/'baseline_audit.json')
    for p,h in b['protected_sha256'].items():assert sha(p)==h,p
    return b

def checkpoint(phase,completed,next_command,processes=()):
    private=ROOT/'.codex-context';private.mkdir(exist_ok=True);history=private/'history';history.mkdir(exist_ok=True)
    old=read(private/'CHECKPOINT.json') if (private/'CHECKPOINT.json').exists() else {}
    value=dict(old,updated_at=now(),project='BurOCRazia',phase=phase,last_completed=completed,next_command=next_command,processes=list(processes),head=head(),branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),working_tree=subprocess.check_output(['git','status','--short','--untracked-files=all'],cwd=ROOT,text=True).splitlines(),goal=dict(status='active',scope='Round21',thread='01a12a5d-17e8-78a3-8330-f5bb4f59f842'),constraints=['Preserve all previous experiments, source tree and original index; no commit/push/tag/release.','No predictions or transformations of reserved V6 inputs before freeze.','Unknown v4 and V6 single-shot only when every immutable prerequisite passes.','No global threshold/margin reduction; explicit entity/version conflicts remain hard veto.'],remaining=['Round21 authorized outputs and conditional evaluation gates'])
    from benchmarks.round4_common import runtime_hash
    value['frozen_protocol']=dict(round=21,seed=SEED,runtime_sha256=runtime_hash(),profile_sha256=sha('data/recognition_profiles/fingerprint_decision_v7.json') if (ROOT/'data/recognition_profiles/fingerprint_decision_v7.json').exists() else None,dataset_sha256=sha('data/document_recognition_fingerprints_v3.json'),freeze_created=(OUT/'freeze_manifest.json').exists(),historical_round20_source_tree=ROUND20_TREE,original_V5_freeze='aa816782b075c8a27eabb7492d080d1c26fa3119',single_shot_policy='No unknown4/V6 prediction before freeze and prerequisite gates; no post-evaluation tuning.')
    value['automation']=dict(id='continuit-burocrazia-round-20',scope='Round21',state='ACTIVE',cadence='hourly')
    atomic_json(history/(datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')+'.json'),value);atomic_json(private/'CHECKPOINT.json',value)
