"""Verify the candidate archive, original freeze, raw V5 and audit semantics."""
import csv,hashlib,json,statistics,subprocess
from collections import Counter
from scripts.round19_common import ROOT,BASE,FREEZE
from benchmarks.round9_performance import describe

def verify(archive,names,gates):
    prefix='BurOCRazia/'
    def raw(p):return archive.read(prefix+p)
    def digest(p):return hashlib.sha256(raw(p)).hexdigest()
    def data(p):return json.loads(raw(p))
    def r(n):return data('benchmarks/results/round19/'+n+'.json')
    baseline=r('baseline_audit');locks=r('evidence_locks')
    for p,h in locks['sha256'].items():assert digest(p)==h,p
    for p,h in locks['historical_original_git_sha256'].items():assert digest(p)==h,p
    for p,h in baseline['preserved_sha256'].items():
        original=subprocess.check_output(['git','show',BASE+':'+p],cwd=ROOT)
        assert raw(p)==original,p
        actual=(ROOT/p).read_bytes();assert hashlib.sha256(actual).hexdigest()==h,p
    f=data('benchmarks/results/round18/freeze_manifest.json');assert gates['freeze']==f['freeze_git_commit']==FREEZE
    for p,h in f['engine_files_sha256'].items():
        if p=='data/catalog_manifest.json':
            actual=(ROOT/p).read_bytes();assert hashlib.sha256(actual).hexdigest()==h and actual.replace(b'\r\n',b'\n')==raw(p)
        else:assert digest(p)==h,p
    assert f['runtime_sha256']==gates['identity']['runtime_sha256']
    assert f['fingerprint_dataset_sha256']==digest('data/document_recognition_fingerprints_v3.json')
    for n,h in f['prerequisite_evidence_sha256'].items():assert digest('benchmarks/results/round18/'+n+'.json')==h,n
    seal=r('benchmark_seal');assert seal['semantic_freeze_commit']==FREEZE
    for p,h in {**seal['files_sha256'],**seal['inputs_sha256']}.items():assert digest(p)==h,p
    assert seal['full_code_sha256']==gates['identity']['code_sha256']
    v4=data('benchmarks/reference/benchmark_contamination_registry_v4.json')
    assert v4['parent_registry_sha256']==digest('benchmarks/reference/benchmark_contamination_registry_v3.json')
    old={k['document_id']:k for k in data('benchmarks/reference/benchmark_contamination_registry_v3.json')['known_identities']}
    assert all(k['legacy_v3']==old[k['document_id']] for k in v4['known_identities'])
    source_policy=data('benchmarks/reference/v5_source_counting_policy_v1.json');assert source_policy['minimum_sources']==6
    audit=list(csv.DictReader(raw('benchmarks/results/round19/v5_identity_eligibility_audit.csv').decode('utf8').splitlines()))
    assert len(audit)==len({a['document_id'] for a in audit})==1019
    eligible=[a for a in audit if a['eligible_v5']=='True'];assert len(eligible)==359 and len({a['source_id'] for a in eligible})==6
    assert all(a['identity_seen_in_tuning']=='False' and a['canonical_verified']=='True' for a in eligible)
    pool=r('evaluation_v5_preflight');assert pool['passed'] and pool['sources_total']==6
    plan=r('evaluation_v5_plan');selected={c['document_id'] for c in plan['selected']}
    assert len(selected)==38 and len(plan['source_counts'])==6 and max(plan['source_counts'].values())/len(selected)<=.35
    by={k['document_id']:k for k in v4['known_identities']};assert all(by[i]['eligible_v5'] and not by[i]['identity_seen_in_tuning'] for i in selected)
    prepared=r('evaluation_v5_prepared');known=[c for c in prepared['representations'] if not c['unknown']]
    generated=r('evaluation_v5_generation_preflight');assert generated['passed']
    assert len(known)==generated['known']==635 and sum(c['scan_like'] for c in known)==generated['scans']==504
    assert sum(c['filled'] for c in known)==generated['valid_filled']==55 and generated['attempted_filled']==60
    assert generated['filled_generation_rate']==55/60>=.9
    rep=r('evaluation_v5_representation_audit');assert len(rep['cases'])==635 and rep['all_fresh']
    assert all(c['fresh_representation'] and not c['prior_SHA_seen'] and not c['prior_case_equivalent'] for c in rep['cases'])
    leak=r('evaluation_v5_leakage');assert leak['passed'] and leak['prohibited_leakage']==0
    o=r('evaluation_v5_observations');v=r('evaluation_v5_gate');rows=o['cases']
    import jsonschema
    jsonschema.validate(o,data('benchmarks/schemas/round19_evaluation_observations.schema.json'))
    assert o['complete'] and len(rows)==len({c['id'] for c in rows})==v['expected_count']==v['actual_count']==665
    assert v['final_observations_sha256']==digest('benchmarks/results/round19/evaluation_v5_observations.json')
    assert o['identity']==r('evaluation_v5_started')['identity']
    assert {c['id']:c['input_sha256'] for c in rows}=={c['case']['id']:c['sha256'] for c in prepared['representations']}
    unknown=[c for c in rows if c['unknown']];assert len(unknown)==30
    allowed={c['SHA256'] for c in data('benchmarks/manifests/official_unknown_release_v3.json')['cases']}
    assert {c['input_sha256'] for c in unknown}<=allowed
    groups={'robustness_v5':[c for c in rows if not c['unknown']], 'scan_v5':[c for c in rows if c['scan_like']], 'filled_v5':[c for c in rows if c['filled']], 'end_to_end_v5':rows}
    from benchmarks.evaluate import summary
    for n,cs in groups.items():assert r(n)['cases']==cs and r(n)['summary']==summary(cs)
    def rates(cs):
        correct=sum(c['document_correct'] for c in cs);accepted=sum(c['observed']['match_type']=='DOCUMENT_MATCH' for c in cs)
        return correct/accepted if accepted else 0,correct/len(cs)
    kp,kr=rates(groups['robustness_v5']);sp,sr=rates(groups['scan_v5']);fp,fr=rates(groups['filled_v5'])
    measured={'v5_precision':kp,'v5_exact_recall':kr,'v5_scan_precision':sp,'v5_scan_recall':sr,'v5_filled_precision':fp,'v5_filled_recall':fr,'v5_filled_generation':55/60,
              'v5_unknown_mix':sum(c['observed']['match_type']=='NO_MATCH' and not c['extraction_failed'] for c in unknown)/30}
    for name,value in measured.items():assert v['gates'][name]['actual']==value,name
    retrieval={str(k):sum(c['candidate_recall_at_k'][str(k)] for c in groups['robustness_v5'])/635 for k in [1,5,10,25]}
    assert r('retrieval_v5')['recall_at_k']==retrieval
    assert v['gates']['v5_retrieval_at25']['actual']==retrieval['25'] and v['gates']['v5_retrieval_at1']['actual']==retrieval['1']
    thresholds={'v5_precision':.995,'v5_exact_recall':.9,'v5_scan_precision':.995,'v5_scan_recall':.85,'v5_filled_precision':.995,'v5_filled_recall':.9,'v5_filled_generation':.9,'v5_unknown_mix':.99,'v5_retrieval_at25':1.,'v5_retrieval_at1':.99}
    for name,t in thresholds.items():assert v['gates'][name]['passed']==(v['gates'][name]['actual']>=t),name
    assert v['passed']==all(c['passed'] for c in v['gates'].values())
    perf=r('performance_stability');assert perf['status']=='complete' and len(perf['runs'])==7
    for run in perf['runs']:assert len(run['samples'])==402 and describe([c['milliseconds'] for c in run['samples']])==run['latency_ms']
    assert statistics.median(run['latency_ms']['p95'] for run in perf['runs'])==perf['median_p95']
    eq=r('semantic_equivalence');assert eq['passed'] and eq['n']==1563 and not eq['differences']
    post=r('post_v5_validation');assert post['passed'] and post['canonical_exact']==1007 and post['semantic_cases']==1563 and post['unknown_v3_calls']==0
    for p,h in post['artifacts_sha256'].items():assert digest(p)==h,p
    for a,b in [('semantic_before','semantic_after'),('semantic_supplement_before','semantic_supplement_after')]:assert all(x['signature']==y['signature'] for x,y in zip(r(a)['cases'],r(b)['cases']))
    assert r('canonical')['counts']['exact']+r('canonical_legacy')['counts']['exact']==1007
    assert r('release_gate_fast')['passed'] and r('release_gate_fast')['n']==1258 and len(r('historical_regression_fast')['mismatches'])==15
    test=r('final_tests');assert test['failed']==0 and test['passed']>=834 and gates['tests']==test
    ready=all(x['passed'] for x in gates['gates'] if x['blocking'])
    assert gates['local_gates_passed']==ready and gates['status']==('READY LOCALLY' if ready else 'NOT READY')
    latest=data('benchmarks/latest_summary.json');assert latest['round']==19 and latest['status']==gates['status']
    return len(set(locks['historical_original_git_sha256'])|set(baseline['preserved_sha256']))
