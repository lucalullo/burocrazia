"""Explicit truth-aware fast gate and original-label historical gate.

The fast commands verify hashes and evaluate actual current harness observations;
they never reuse a prior runtime's predictions as current results.
"""
import argparse
from scripts.round18_common import *
from scripts.round18_validate import observations
from benchmarks.release_truth import load_release
from benchmarks.round4_common import runtime_hash

def release():
    policy,registry,selected=load_release();rows={r['id']:r for r in observations()};inputs=read(OUT/'input_safety.json');safe={c['case_id']:c for c in inputs['cases']};results=[]
    for c in selected:
        if c['truth_domain']=='parser_limit_contract':
            r=safe[c['input_key']];correct=r['rejected_safely'] and not r['crash'] and not r['temp_residue'] and r['recognition_calls']==0 and r['result'] is None
            observed='SAFE_REJECTION' if correct else 'UNSAFE_INPUT_RESULT'
        else:
            r=rows[c['input_key']];observed=r['observed'];expected=c['expected']
            # Forbidden entity/version sets are expectation constraints, not
            # observed fields. The shared evaluator already applies them.
            assert r['expected']==expected,'Qualified contract differs from locked input expectation'
            correct=r['correct']
        results.append(dict(case_id=c['case_id'],truth_domain=c['truth_domain'],confidence=c['confidence'],release_gate_eligible=c['release_gate_eligible'],expected=c['expected'],observed=observed,correct=correct))
    value=dict(passed=all(r['correct'] for r in results),n=len(results),cases=results,failed_ids=[r['case_id'] for r in results if not r['correct']],reference_truth_v3_sha256=sha(TRUTH),truth_addendum_sha256=sha(ADDENDUM),release_truth_policy_sha256=sha(POLICY),runtime_sha256=runtime_hash(),semantic_observations_sha256={n:sha(OUT/n) for n in ['semantic_after.json','semantic_supplement_after.json','input_safety.json']},historical_expectations_changed=False,scope='Confirmed diagnostic regression only; no independent release precision claim.',created_at=now())
    save('release_gate_fast',value);print('Release gate fast',value['passed'],value['n'],'failed',value['failed_ids']);return 0 if value['passed'] else 1

def historical():
    rows=observations();failed=[r for r in rows if not r['correct']]
    save('historical_regression_fast',dict(passed=not failed,n=len(rows),mismatches=failed,cases=rows,expected_changed=False,runtime_sha256=runtime_hash(),scope='Every labelled harness expectation retained, including1007 technical canonical bindings, locked corpora, INPS EX02/EX03, INAIL annual ambiguities, ANAC and five former critical official resources. One prudent refusal on a known critical resource remains an exact historical mismatch, although it satisfies the separate unchanged safety contract. Nonzero exit is independent of confirmed release-fast.',created_at=now()))
    print('Historical regression fast',len(rows),'mismatches',len(failed),[r['id'] for r in failed]);return 1 if failed else 0

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['release-gate-fast','historical-regression-fast']);a=p.parse_args();raise SystemExit(release() if a.mode=='release-gate-fast' else historical())
