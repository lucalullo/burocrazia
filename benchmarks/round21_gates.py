"""Truth-qualified release diagnostic and original-label historical fast gate."""
import argparse
from scripts.round21_common import *
from benchmarks.release_truth import load_release
from benchmarks.round4_common import runtime_hash

def observations():
    cal=read(OUT/'calibration_v7.json');raw=read(cal['observations_path'])
    assert raw['identity']['runtime_sha256']==runtime_hash()
    return [r for r in raw['cases'] if r['id'].startswith('HIST:') and r.get('expected')]

def release():
    _,_,contracts=load_release();rows={r['original_id']:r for r in observations()};inputs={c['case_id']:c for c in read(OUT/'input_safety.json')['cases']};actual=[]
    for c in contracts:
        if c['truth_domain']=='parser_limit_contract':
            r=inputs[c['input_key']];correct=r['rejected_safely'] and not r['crash'] and not r['temp_residue'] and r['recognition_calls']==0 and r['result'] is None;observed='SAFE_REJECTION' if correct else 'UNSAFE'
        else:
            r=rows[c['input_key']];assert r['expected']==c['expected'];correct=r['correct'];observed=r['observed']
        actual.append(dict(case_id=c['case_id'],expected=c['expected'],observed=observed,correct=correct,truth_domain=c['truth_domain']))
    save('release_gate_fast',dict(passed=all(r['correct'] for r in actual),n=len(actual),failed_ids=[r['case_id'] for r in actual if not r['correct']],cases=actual,runtime_sha256=runtime_hash(),truth_policy_sha256=sha(POLICY),scope='Confirmed development diagnostic contracts, not independent release evidence.'))
    print('R20 release-fast',len(actual),'failed',sum(not r['correct'] for r in actual));return 0 if all(r['correct'] for r in actual) else 1

def historical():
    rows=observations();bad=[r for r in rows if not r['correct']]
    save('historical_regression_fast',dict(n=len(rows),mismatches=bad,cases=rows,expected_changed=False,passed=not bad,runtime_sha256=runtime_hash(),scope='Original labels preserved; ambiguous historical contracts remain visible.'))
    print('R20 historical-fast',len(rows),'mismatches',len(bad));return 1 if bad else 0

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['release-gate-fast','historical-regression-fast']);a=p.parse_args();raise SystemExit(release() if a.mode=='release-gate-fast' else historical())
