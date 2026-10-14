"""Verify immutable history, sealed bytes, fresh unknown and stopped V6 gates."""
import csv,hashlib,json,statistics,subprocess
from collections import Counter
from scripts.round21_common import ROOT,BASE,ROUND20_TREE
from benchmarks.round9_performance import describe
from benchmarks.round17_unknown import metrics as unknown_metrics

def verify(archive,names,gates):
    def raw(p):return archive.read('BurOCRazia/'+p)
    def digest(p):return hashlib.sha256(raw(p)).hexdigest()
    def data(p):return json.loads(raw(p))
    def r(n):return data('benchmarks/results/round21/'+n+'.json')
    b=r('baseline_audit');old=data('benchmarks/results/round20/baseline_audit.json');locks=data('benchmarks/results/round19/evidence_locks.json')
    history={**locks['historical_original_git_sha256'],**old['historical_sha256'],**b['protected_sha256']}
    for p,h in history.items():assert digest(p)==h,p
    for p,h in old['immutable_data_sha256'].items():
        actual=(ROOT/p).read_bytes();assert hashlib.sha256(actual).hexdigest()==h
        assert raw(p)==actual or (p=='data/catalog_manifest.json' and raw(p)==actual.replace(b'\r\n',b'\n')),p
    assert b['baseline_tests']['passed']==856 and b['baseline_tests']['failed']==0
    for p,h in r('evidence_locks')['sha256'].items():assert digest(p)==h,p
    f=r('freeze_manifest');assert f==gates['freeze'] and f['commit']==BASE and not f['new_commit_created']
    assert f['semantic_source_tree']!=BASE and f['recognition_semantic_hash']==gates['identity']['runtime_sha256']
    for p,h in f['frozen_files_sha256'].items():
        git=subprocess.check_output(['git','show',f['semantic_source_tree']+':'+p],cwd=ROOT)
        assert raw(p)==git,p
        assert digest(p)==h or (p=='data/catalog_manifest.json' and any(x['path']==p and x['tree_sha256']==digest(p) and x['workspace_sha256']==h for x in f['serialization_differences'])),p
    cal=r('calibration_v7');obs=data(cal['observations_path']);assert digest(cal['observations_path'])==cal['observations_sha256']
    assert obs['complete'] and obs['expected_count']==len(obs['cases'])==cal['actual_count']==3160
    assert len({c['id'] for c in obs['cases']})==3160
    def rates(cs):
        tp=sum(c['document_correct'] for c in cs);ac=sum(c['observed']['match_type']=='DOCUMENT_MATCH' for c in cs)
        return dict(n=len(cs),exact=tp,accepted=ac,wrong=ac-tp,precision=tp/ac if ac else 0,recall=tp/len(cs) if cs else 0)
    v5=[c for c in obs['cases'] if c['group']=='v5'];assert rates(v5)==cal['V5_development']
    assert rates([c for c in v5 if c['scan_like']])==cal['scan'] and rates([c for c in v5 if c['filled']])==cal['filled']
    assert cal['identity']['runtime_sha256']==f['recognition_semantic_hash'] and all(cal['gates'].values())
    canonical=r('canonical');assert canonical['n']==canonical['exact']==len(canonical['cases'])==1007 and all(c['document_correct'] for c in canonical['cases'])
    safety=r('development_safety');assert safety['confirmed_negative_count']==len(safety['cases'])==705 and not safety['false_accepts']
    assert all(c['observed']['match_type']=='NO_MATCH' and not c['extraction_failed'] for c in safety['cases'])
    hard=r('hard_negatives_development');assert hard['n']==len(hard['cases'])==hard['correct_rejects'] and hard['passed']
    registry=data('benchmarks/reference/benchmark_contamination_registry_v7.json');pool=data('benchmarks/manifests/v6_reserved_identity_pool.json')
    assert registry['parent_registry_sha256']==digest('benchmarks/reference/benchmark_contamination_registry_v6.json')
    ids={c['document_id'] for c in pool['cases']};assert len(ids)==639 and len({c['source_id'] for c in pool['cases']})==8
    assert not ids&set(registry['round21']['development_identity_ids']) and not ids&set(registry['round20']['V5_identity_ids'])
    assert all(c['reserved_for_v6'] and not c['prior_tuning_seen'] for c in pool['cases'])
    assert all(not k['tuning_seen'] and not k['tuning_history_unresolved'] for k in registry['known_identities'] if k['document_id'] in ids)
    rows=list(csv.DictReader(raw('benchmarks/results/round21/v6_source_eligibility.csv').decode('utf8').splitlines()));assert len(rows)==19 and sum(int(c['fresh_eligible_identities']) for c in rows)==639
    perf=r('performance_stability');assert perf['completed_runs']==len(perf['runs'])==7 and perf['identity']['runtime_sha256']==f['recognition_semantic_hash']
    for run in perf['runs']:
        assert len(run['samples'])==402 and len({c['case_id'] for c in run['samples']})==67
        assert describe([c['milliseconds'] for c in run['samples']])==run['latency_ms']
    assert perf['median_p95']==statistics.median(run['latency_ms']['p95'] for run in perf['runs'])<=180
    assert perf['required_pass'] and perf['pass_count']==7
    pre=r('pre_freeze_gate');assert pre['ready_to_freeze'] and all(pre[k] for k in ['dev_precision_pass','dev_recall_pass','dev_scan_pass','dev_filled_pass','confirmed_safety_pass','canonical_pass','coverage_pass','input_safety_pass','performance_pass','tests_pass','V6_pool_pass','unknown_v4_preflight_pass'])
    unknown=r('unknown_release_v4');uobs=r('unknown_release_v4_observations');um=data('benchmarks/manifests/official_unknown_release_v4.json')
    assert unknown['passed'] and unknown['expected_count']==unknown['actual_count']==unknown['unique_case_ids']==unknown['recognition_calls']==len(uobs['cases'])==120
    assert uobs['complete'] and len({c['id'] for c in uobs['cases']})==120
    assert {c['id']:c['input_sha256'] for c in uobs['cases']}=={c['case_id']:c['SHA256'] for c in um['cases']}
    assert unknown['observations_sha256']==digest('benchmarks/results/round21/unknown_release_v4_observations.json')
    assert unknown['manifest_sha256']==digest('benchmarks/manifests/official_unknown_release_v4.json') and um['freeze_manifest_sha256']==digest('benchmarks/results/round21/freeze_manifest.json')
    assert all(unknown[k]==v for k,v in unknown_metrics(uobs['cases']).items())
    assert unknown['correct_no_match']==120 and unknown['selection']['sources']==15
    assert not {c['SHA256'] for c in um['cases']}&set(registry['observed_resource_sha256'])
    gen=r('evaluation_v6_generation_preflight');prepared=r('evaluation_v6_prepared');attempts=prepared['generation_audit'];reps=prepared['representations'];leak=r('evaluation_v6_leakage');plan=r('evaluation_v6_plan')
    assert {c['document_id'] for c in plan['selected']}<=ids and len(plan['selected'])==40 and len(plan['source_counts'])==8
    assert len(attempts)==600 and len(reps)==gen['known']==572 and len({c['sha256'] for c in reps})==572
    assert gen['valid_filled']==sum(c['filled'] for c in reps)==75 and gen['attempted_filled']==sum(c['filled'] for c in attempts)==100
    assert gen['filled_generation_rate']==75/100 and not gen['passed']
    assert gen['scans']==sum(c['scan_like'] for c in reps)==420 and gen['recognition_calls']==0
    assert sum(not c['generated'] for c in attempts)==28 and sum(c['filled'] and not c['generated'] for c in attempts)==25
    assert leak['passed'] and leak['prohibited_leakage']==0 and not any(leak[k] for k in ['identity_tuning_overlap','V5_overlap','representation_overlap','duplicate_SHA','duplicate_case_ids','truth_ambiguity','seed_reuse'])
    assert all(not c['prior_SHA_seen'] and not c['prior_equivalent'] and c['fresh'] for c in r('evaluation_v6_representation_audit')['cases'])
    for c in reps:assert hashlib.sha256((ROOT/c['path']).read_bytes()).hexdigest()==c['sha256']
    recovery=r('evaluation_v6_generation_recovery');assert recovery['recognition_calls']==0 and recovery['preexisting_outputs_unchanged'] and len(recovery['preexisting_outputs'])==133
    for name,h in recovery['preexisting_outputs'].items():assert hashlib.sha256((ROOT/'benchmarks/work/round21/evaluation-v6'/name).read_bytes()).hexdigest()==h
    assert recovery['operator_adapter_sha256']==digest('scripts/round21_generation_resume.py')
    for n in ['robustness_v6','scan_v6','filled_v6','retrieval_v6','end_to_end_v6']:
        value=r(n);assert value['status']=='not_run' and value['recognition_calls']==0 and not value['cases'] and not value['summary']['metrics']
    for n in ['evaluation_v6_started','evaluation_v6_observations','evaluation_v6_gate']:assert 'BurOCRazia/benchmarks/results/round21/'+n+'.json' not in names
    tests=r('final_tests_on_freeze');assert tests==gates['tests'] and tests['passed']==878 and tests['failed']==0 and tests['skipped']==3 and r('final_validation_on_freeze')['passed']
    assert gates['status']=='NOT READY' and not gates['local_gates_passed']
    assert set(gates['reasons'])=={'v6_generation_and_leakage','fresh_v6_evaluation'}
    latest=data('benchmarks/latest_summary.json');assert latest['round']==21 and latest['status']=='NOT READY' and latest['unknown_official']['status']=='executed'
    assert all(latest[n]['status']=='not_run' and not latest[n]['summary']['metrics'] for n in ['known_robustness','scan_ocr','filled_forms'])
    assert not any('evaluation-v6/' in p for p in names),'No raw synthetic binaries in public archive'
    return len(history)
