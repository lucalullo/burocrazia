"""Complete contaminated development replay; no reserved evaluation inputs."""
import argparse
from concurrent.futures import ProcessPoolExecutor,as_completed
from scripts.round21_common import *
from benchmarks.round20_calibrate import worker
from benchmarks.transactional_writer import CaseJournal
from benchmarks.evaluate import code_hash
from benchmarks.round4_common import runtime_hash
from benchmarks.release_truth import load_release
from src.fingerprint_decision_v7 import profile,revision

def rate(rs):
    tp=sum(r['document_correct'] for r in rs);accepted=sum(r['observed']['match_type']=='DOCUMENT_MATCH' for r in rs)
    return dict(n=len(rs),exact=tp,accepted=accepted,wrong=accepted-tp,precision=tp/accepted if accepted else 0,recall=tp/len(rs) if rs else 0)
def run(attempt):
    preserved();prepared=read('benchmarks/work/round20/development-inputs.json');rows=prepared['rows']
    assert not (ROOT/'benchmarks/manifests/v6_reserved_identity_pool.json').exists(),'No development predictions after final reservation'
    ident=dict(runtime_sha256=runtime_hash(),fingerprint_sha256=sha('data/document_recognition_fingerprints_v3.json'),profile_sha256=revision(),prepared_sha256=sha('benchmarks/work/round20/development-inputs.json'),runner_code_sha256=code_hash(),attempt=attempt)
    target=OUT/('development_observations_'+attempt+'.json');assert not target.exists()
    journal=CaseJournal(WORK/('development-'+attempt+'-'+ident['runtime_sha256'][:12]+'.sqlite'),identity=ident,expected_ids=[c['id'] for c in rows]);pending=set(journal.pending())
    checkpoint('Round21 full development replay',f'Policy v7 attempt{attempt}; original V5/Round20 and old profiles protected. Prospective source pool640/8; no final reservation yet.',f'Resume only same journal identity; follow log for{attempt}, inspect all confirmed false accepts before any next experiment.',[dict(command='python -m benchmarks.round21_calibrate '+attempt,log='reports/round21-development-'+attempt+'.log',state='running; journal identity bound')])
    with ProcessPoolExecutor(max_workers=3) as pool:
        jobs={pool.submit(worker,c):c['id'] for c in rows if c['id'] in pending}
        done=len(rows)-len(pending)
        for f in as_completed(jobs):
            r=f.result();assert r['id']==jobs[f];journal.append(r);done+=1
            if done%100==0:print('R21 development',attempt,done,'/',len(rows),flush=True)
    actual=journal.rows();journal.export(target,complete=True);assert len(actual)==3160
    qualified={c['input_key'] for c in load_release()[2] if c['truth_domain']!='parser_limit_contract'}
    certain=[r for r in actual if r.get('expected') and (r['group']!='historical' or r['original_id'] in qualified)]
    known=[r for r in certain if r['expected']['match_type']=='DOCUMENT_MATCH'];negative=[r for r in certain if r['expected']['match_type']=='NO_MATCH' and not r['extraction_failed']]
    v5=[r for r in actual if r['group']=='v5'];scan=[r for r in v5 if r['scan_like']];filled=[r for r in v5 if r['filled']];canonical=[r for r in actual if r['group']=='canonical']
    fa=[r['id'] for r in negative if r['observed']['match_type']!='NO_MATCH']+[r['id'] for r in known if r['observed']['match_type']=='DOCUMENT_MATCH' and not r['document_correct']]
    m,s,f,combined=map(rate,[v5,scan,filled,known]);entities=sum(r['entity_error'] for r in v5);versions=sum(r['version_error'] for r in v5)
    gates=dict(dev_precision_pass=m['precision']>=.995 and combined['precision']>=.995,dev_recall_pass=m['recall']>=.9,dev_scan_pass=s['recall']>=.85,dev_filled_pass=f['recall']>=.9,confirmed_safety_pass=not fa,canonical_pass=len(canonical)==1007 and all(r['document_correct'] for r in canonical),entity_version_pass=entities==versions==0)
    used={r['expected']['document_id'] for r in certain if r['expected'].get('document_id') and (r['group']!='canonical' or not r['correct'])}
    used|={r['observed']['document_id'] for r in certain if r['observed'].get('document_id') and not r['correct']}
    cal=dict(identity=ident,parameters=profile(),thresholds=profile()['thresholds'],conditional=profile()['conditional'],rules=['Existing v6 rules and global thresholds retained','Rank1 strong OCR/page + char + anchors','Complete exclusive heading disambiguates only already-leading page; unchanged margin','Rank1 strict layout plus complete long heading or text/char corroboration','Unknown issuer/version is not explicit conflict; old hard vetoes retained'],identity_ids=sorted(used),V5_development=m,scan=s,filled=f,combined_known=combined,confirmed_negative_count=len(negative),confirmed_false_accept_ids=fa,negative_false_accept_ids=[r['id'] for r in negative if r['observed']['match_type']!='NO_MATCH'],canonical_exact=sum(r['document_correct'] for r in canonical),entity_errors=entities,version_errors=versions,gates=gates,passed=all(gates.values()),actual_count=len(actual),recognition_calls=sum(r['recognition_calls'] for r in actual),observations_path=target.relative_to(ROOT).as_posix(),observations_sha256=sha(target),classification='development_only',scope='Existing contaminated V5/R6/R7/R8/hard negatives/unknown v1-v3 only. Canonical validation is product verification before final reservation, not fitting future identities; failures inspected for fixes must be contaminated.')
    save('calibration_'+attempt,cal);save('development_regression_v5_after_fix_'+attempt,dict(classification='development_regression_v5_after_fix',identity=ident,metrics=m,scan=s,filled=f,cases=v5,observations_sha256=sha(target),historical_original_unchanged=True))
    print('R21 complete',attempt,m,s,f,'FA',fa,'gates',gates,flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('attempt');run(p.parse_args().attempt)
