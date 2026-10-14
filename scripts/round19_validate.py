"""Current-candidate prerequisites derived from actual sealed observations."""
import argparse,shutil
from types import SimpleNamespace
from collections import defaultdict
from scripts.round19_common import *
from benchmarks.evaluate import summary
from benchmarks.round4_common import runtime_hash
from benchmarks.round8_common import identity
from scripts.benchmark import evaluate_case

def former_false_accept_safe(row):
    """Existing R15 safety contract: abstain or emit the correct identity."""
    o=row['observed'];return o['match_type']=='NO_MATCH' or o['match_type']=='DOCUMENT_MATCH' and o['document_id']==row['expected'].get('document_id')

def observations():
    equivalence=read(OUT/'semantic_equivalence.json');assert equivalence['passed'] and not equivalence['differences']
    rows=[]
    for source,artifact in [('semantic-inputs.json','semantic_after.json'),('semantic-supplement.json','semantic_supplement_after.json')]:
        prepared=read('benchmarks/work/round16/'+source);actual=read(OUT/artifact)
        assert actual['prepared_sha256']==sha('benchmarks/work/round16/'+source)
        assert actual['identity']['runtime_sha256']==runtime_hash()
        assert actual['identity']['fingerprint_sha256']==sha('data/document_recognition_fingerprints_v3.json')
        assert len(actual['cases'])==len(prepared['rows'])
        for c,r in zip(prepared['rows'],actual['cases']):
            assert c['id']==r['case_id']
            if not c.get('expected'):continue
            v=dict(r['signature']['result'])
            for key in ['document','family']:
                if v[key] is not None:v[key]=SimpleNamespace(**v[key])
            case=dict(c,id=c['id'],group=c['id'])
            row=evaluate_case(case,SimpleNamespace(**v));row.update(category=c['category'],input_sha256=c['sha256'],signature_sha256=hashlib.sha256(json.dumps(r['signature'],sort_keys=True).encode()).hexdigest(),timing_measured=False)
            rows.append(row)
    return rows

def measure():
    from scripts import round15_validate as prior
    prior.OUT=OUT;prior.save=save
    prior.coverage()
    # The page-limit audit is historical evidence of the same unchanged parser
    # contract. Its bytes are copied, not represented as a new adjudication.
    shutil.copyfile(ROOT/'benchmarks/results/round15/page_limit_audit.json',OUT/'page_limit_audit.json')
    prior.input_safety()
    safety=read(OUT/'input_safety.json')
    safety['no_false_family_result']=all(c['result']!='FAMILY_MATCH' for c in safety['cases'])
    safety['passed'] &= safety['no_false_family_result'] and all(c['recognition_calls']==0 for c in safety['cases'])
    save('input_safety',safety)
    rows=observations();groups=defaultdict(list)
    for r in rows:groups[r['category']].append(r)
    for category,name in [('canonical','canonical'),('canonical_legacy','canonical_legacy')]:
        cases=groups[category];s=summary(cases);s['latency_ms']={}
        save(name,dict(cases=cases,counts=dict(exact=sum(c['document_correct'] for c in cases)),summary=s,identity=identity(),scope='Actual current recognition observations in semantic harness; original files extracted before optimization. No timing inferred from this projection.',semantic_observations_sha256=sha(OUT/'semantic_after.json')))
    negatives=[r for r in rows if r['expected']['match_type']=='NO_MATCH' and r['category'] in ['development_regression','release_locked_v1','release_locked_v2','hard_negatives_v1','hard_negatives_v2','development_compat_v2','family_release_v3']]
    assert len(negatives)==241
    save('historical_safety',dict(n=len(negatives),false_accepts=[r['id'] for r in negatives if r['observed']['match_type']!='NO_MATCH'],passed=all(r['observed']['match_type']=='NO_MATCH' for r in negatives),cases=negatives,scope='Locked synthetic abstention contracts, with isolated family recognition for family_release_v3. Counts overlap corpora and are not independent unknown samples.'))
    historical=[]
    for category in ['development_regression','release_locked_v1','release_locked_v2','hard_negatives_v1','hard_negatives_v2','development_compat_v2','family_release_v3','INAIL_ambiguous']:
        cases=groups[category];s=summary(cases);s['latency_ms']={}
        save('historical_'+category,dict(cases=cases,summary=s,identity=identity(),scope='Frozen original expectations retained; uncertain mismatches are not confirmed identity errors.'))
        historical.extend(cases)
    historical=rows
    save('historical_regression',dict(status='mismatches_retained' if any(not c['correct'] for c in historical) else 'passed',cases=historical,mismatches=[c for c in historical if not c['correct']],expected_changed=False,identity=identity(),historical_unknown_v2=dict(n=114,correct_no_match=107,wrong_document_match=3,wrong_family_match=0,extraction_failed=4,raw_sha256=sha('benchmarks/results/round14/unknown_release_v2_observations.json')),scope='Every labelled harness expectation; original exact expectations on former false accepts remain visible separately from their conservative safety contract. Canonical metadata-coverage and old release-fast CLI separately retained in final checks.'))
    save('confirmed_ANAC',dict(cases=groups['ANAC']+groups['ANAC_full_pdf'],passed=all(c['correct'] for c in groups['ANAC']+groups['ANAC_full_pdf'])))
    critical=[dict(c,safe=former_false_accept_safe(c)) for c in groups['old_false_accept']]
    save('old_false_accepts',dict(cases=critical,passed=all(c['safe'] for c in critical),exact=sum(c['correct'] for c in critical),prudent_refusals=sum(c['observed']['match_type']=='NO_MATCH' for c in critical),scope='Unchanged R15 historical_five safe contract: NO_MATCH or correct document identity. Original exact expectations retained and reported separately; abstention is safe, not an exact true positive.'))
    print('R19 measured canonical/safety/coverage; historical mismatches',sum(not c['correct'] for c in historical),flush=True)

def gate():
    from benchmarks.release_truth import load_release
    from benchmarks.round9_performance import describe
    import statistics
    cov=read(OUT/'coverage.json');native=read(OUT/'canonical.json');legacy=read(OUT/'canonical_legacy.json');safety=read(OUT/'historical_safety.json');inputs=read(OUT/'input_safety.json');perf=read(OUT/'performance_stability.json')
    assert perf['status']=='complete' and len(perf['runs'])==7
    assert perf['identity']['runtime_sha256']==runtime_hash()
    for r in perf['runs']:assert r['sample_count']==len(r['samples'])==402 and describe([c['milliseconds'] for c in r['samples']])==r['latency_ms']
    assert perf['median_p95']==statistics.median(r['latency_ms']['p95'] for r in perf['runs'])
    _,_,selected=load_release()
    test=read(OUT/'tests.json') if (OUT/'tests.json').exists() else None
    fast=read(OUT/'release_gate_fast.json') if (OUT/'release_gate_fast.json').exists() else None
    prerequisites=dict(unknown_v3_preflight_pass=read(OUT/'unknown_release_v3_preflight.json')['passed'],coverage_pass=cov['passed'],canonical_pass=native['counts']['exact']==980 and legacy['counts']['exact']==27,confirmed_safety_pass=safety['passed'] and read(OUT/'confirmed_ANAC.json')['passed'] and read(OUT/'old_false_accepts.json')['passed'],input_safety_pass=inputs['passed'],truth_policy_pass=len(selected)==1258,performance_pass=perf['required_pass'],semantic_equivalence_pass=read(OUT/'semantic_equivalence.json')['passed'],tests_pass=bool(test and test['failed']==0),release_gate_fast_pass=bool(fast and fast['passed']))
    save('pre_freeze_gate',dict(**prerequisites,ready_to_freeze=all(prerequisites.values()),passed=all(prerequisites.values()),performance_median_p95=perf['median_p95'],historical_regression_status=read(OUT/'historical_regression.json')['status'],ambiguous_historical_cases=['development_regression:EX02','development_regression:EX03','U14-5f0c017c3d56e6c5','U14-c1fc4765c01dcd62'],identity_correction='EX02/EX03: INPS CI543/CI544 synthetic omitted revision, ambiguity established by truth v2. INAIL: two distinct annual resources, ambiguity established by truth v3.',identity=identity(),created_at=now()))
    print('R19 pre-freeze',prerequisites,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['measure','gate']);globals()[p.parse_args().mode]()
