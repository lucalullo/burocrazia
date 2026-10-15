"""Post-measurement byte locks and diagnostic aggregation; no retuning."""
import hashlib,json,subprocess,sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from benchmarks.round4_common import runtime_hash
from src.fingerprint_v2 import fused,thresholds

FREEZE='ce6fa61f432c204e3d4c8029ef370ff27e429455'
OUT=ROOT/'benchmarks/results/round6'

def main():
    paths=subprocess.check_output(['git','ls-tree','-r','--name-only',FREEZE,'src','data/recognition_profiles'],cwd=ROOT,text=True).splitlines()
    paths=[p for p in paths if p.endswith(('.py','.json'))]
    paths+=['app.py','run.py','data/recognition_features.json','data/document_recognition_fingerprints.json',
        'data/document_recognition_fingerprints_v2.json','benchmarks/round6_recognition.py',
        'benchmarks/results/round6/robustness_v2_plan.json','benchmarks/results/round6/fingerprint_calibration.json']
    hashes={}
    for p in sorted(paths):
        original=subprocess.check_output(['git','show',FREEZE+':'+p],cwd=ROOT)
        assert (ROOT/p).read_bytes()==original,p
        hashes[p]=hashlib.sha256(original).hexdigest()
    locked=dict(schema_version=1,freeze_commit=FREEZE,runtime_sha256=runtime_hash(),sha256=hashes,
        scope='Byte equality against the commit made before evaluation opened. Posthoc verification, not a newly invented earlier event. Report scripts, fixture v2 and performance JSON parsing are outside the recognition runtime.')
    (OUT/'evaluation_locks.json').write_text(json.dumps(locked,indent=2)+'\n',encoding='utf8')
    audit={}
    for name in ['robustness_v2','scan_ocr_v2']:
        r=json.loads((OUT/(name+'.json')).read_text(encoding='utf8'));rows=[]
        for c in r['cases']:
            if c['correct']:continue
            expected=next((s for s in c['retrieval_scores'] if s['document_id']==c['expected']['document_id']),None)
            category='retrieval_outside_top25' if expected is None else 'insufficient_fusion' if not fused(expected,thresholds()) else 'fusion_passed_but_not_accepted'
            rows.append(dict(case_id=c['id'],expected_id=c['expected']['document_id'],observed=c['observed'],candidate_rank=c['candidate_rank'],
                diagnostic_category=category,expected_scores=expected,reason=c['reason'],conflicts=c['conflicts']))
        audit[name]=dict(counts=dict(Counter(c['diagnostic_category'] for c in rows)),cases=rows)
    audit['scope']='Diagnostic aggregation of frozen evaluation only. Fusion eligibility is necessary, not sufficient: safety and margin may still veto. Generic runtime reasons do not prove a particular hidden veto. No thresholds or observations changed.'
    (OUT/'rejection_diagnostics.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Frozen bytes verified:',len(hashes));print({n:r['counts'] for n,r in audit.items() if isinstance(r,dict)})

if __name__=='__main__':main()
