"""Prescribed post-V6 canonical/safety replay on unchanged frozen semantics."""
from concurrent.futures import ProcessPoolExecutor,as_completed
from scripts.round22_common import *
from benchmarks.round22_release import sealed
from benchmarks.round20_calibrate import worker
from benchmarks.transactional_writer import CaseJournal
from benchmarks.release_truth import load_release

def main():
    f=sealed();assert (OUT/'evaluation_v6_gate.json').exists();assert not (OUT/'post_v6_checks.json').exists()
    import csv
    wrong={r['case_id'] for r in csv.DictReader((ROOT/'benchmarks/results/round20/v5_false_accepts.csv').open(encoding='utf8'))}
    prepared=read('benchmarks/work/round20/development-inputs.json')['rows']
    selected=[c for c in prepared if c['group'] in ['canonical','historical'] or (c.get('expected') or {}).get('match_type')=='NO_MATCH' or c['id'].removeprefix('DEV5:') in wrong]
    key=dict(freeze_manifest_sha256=sha(OUT/'evaluation_freeze_manifest.json'),runtime_sha256=f['working_tree_recognition_hash'],prepared_sha256=sha('benchmarks/work/round20/development-inputs.json'),selected_ids_sha256=hashlib.sha256(json.dumps(sorted(c['id'] for c in selected)).encode()).hexdigest())
    journal=CaseJournal(WORK/'post-v6-validation.sqlite',identity=key,expected_ids=[c['id'] for c in selected]);pending=set(journal.pending());done=len(selected)-len(pending)
    checkpoint('Round22 post-V6 canonical/safety active','Independent V6 closed; recognition and generator unchanged. Canonical/historical NO/old false accepts/hardneg/ANAC/R061/EX policy replay is validation only.', 'Complete post-validation journal without tuning;follow reports/round22-post-v6.log.',[dict(command='python -m benchmarks.round22_post',log='reports/round22-post-v6.log',state='running')])
    with ProcessPoolExecutor(max_workers=3) as pool:
        jobs={pool.submit(worker,c):c['id'] for c in selected if c['id'] in pending}
        for future in as_completed(jobs):
            r=future.result();assert r['id']==jobs[future];journal.append(r);done+=1
            if done%100==0:print('R22 post-V6 persisted',done,'/',len(selected),flush=True)
    target=OUT/'post_v6_observations.json';journal.export(target,complete=True);rows=journal.rows();qualified={c['input_key'] for c in load_release()[2] if c['truth_domain']!='parser_limit_contract'}
    certain=[r for r in rows if r.get('expected') and (r['group']!='historical' or r['original_id'] in qualified)]
    canonical=[r for r in rows if r['group']=='canonical'];neg=[r for r in certain if r['expected']['match_type']=='NO_MATCH' and not r['extraction_failed']];known=[r for r in certain if r['expected']['match_type']=='DOCUMENT_MATCH'];hard=[r for r in neg if 'hard_negative' in r['category'] or 'hard_negative' in r['id']]
    fa=[r['id'] for r in neg if r['observed']['match_type']!='NO_MATCH']+[r['id'] for r in known if r['observed']['match_type']=='DOCUMENT_MATCH' and not r['document_correct']]
    save('canonical_post_v6',dict(n=len(canonical),exact=sum(r['document_correct'] for r in canonical),passed=len(canonical)==1007 and all(r['document_correct'] for r in canonical),cases=canonical,runtime_sha256=f['working_tree_recognition_hash']))
    oldfa=[r for r in rows if r['id'].removeprefix('DEV5:') in wrong]
    save('safety_post_v6',dict(n=len(neg),false_accepts=fa,passed=not fa,old_false_accept_cases=len(oldfa),old_false_accept_exact=sum(r['document_correct'] for r in oldfa),hard_negatives=len(hard),hard_correct_rejects=sum(r['observed']['match_type']=='NO_MATCH' for r in hard),cases=neg,unsupported_not_credited=sum(r['extraction_failed'] for r in rows),scope='Confirmed truth policy only. Historical ambiguous labels remain in raw and historical mismatch gate. No unknown4 replay or V6 replay.'))
    save('post_v6_checks',dict(passed=not fa and read(OUT/'canonical_post_v6.json')['passed'],expected_count=len(selected),actual_count=len(rows),observations_sha256=sha(target),identity=key,recognition_semantics_changed=False))
    sealed();print('R22 post-V6 canonical',len(canonical),'exact',sum(r['document_correct'] for r in canonical),'negative',len(neg),'FA',fa,'oldFA',len(oldfa),flush=True)

if __name__=='__main__':main()
