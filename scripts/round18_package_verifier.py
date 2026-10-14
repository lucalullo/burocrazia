"""Verify Round18 source, historical seals and conditional single-shot evidence."""
import hashlib,json,statistics,subprocess
from scripts.round18_common import ROOT,BASE
from benchmarks.round9_performance import describe

def verify(archive,names,gates):
    prefix='BurOCRazia/'
    def raw(p):return archive.read(prefix+p)
    def digest(p):return hashlib.sha256(raw(p)).hexdigest()
    def evidence(n):return json.loads(raw('benchmarks/results/round18/'+n+'.json'))
    locks=evidence('evidence_locks')
    for p,h in locks['sha256'].items():assert digest(p)==h,p
    for p,h in locks['historical_original_git_sha256'].items():assert digest(p)==h,p
    oldregistry='benchmarks/reference/benchmark_contamination_registry_v3_round17_preserved.json'
    assert raw(oldregistry)==subprocess.check_output(['git','show',BASE+':benchmarks/reference/benchmark_contamination_registry_v3.json'],cwd=ROOT)
    assert json.loads(raw('benchmarks/reference/benchmark_contamination_registry_v3.json'))['round18_parent_registry_sha256']==digest(oldregistry)
    old=json.loads(raw('benchmarks/results/round16/freeze_manifest.json'))
    for p,h in old['engine_files_sha256'].items():
        if p=='data/catalog_manifest.json':
            assert raw(p)==subprocess.check_output(['git','show',BASE+':'+p],cwd=ROOT)
            physical=(ROOT/p).read_bytes();assert hashlib.sha256(physical).hexdigest()==h and physical.replace(b'\r\n',b'\n')==raw(p)
        else:assert digest(p)==h,p
    perf=evidence('performance_stability');assert len(perf['runs'])==7 and perf['status']=='complete'
    for r in perf['runs']:assert len(r['samples'])==402 and describe([x['milliseconds'] for x in r['samples']])==r['latency_ms']
    assert statistics.median(r['latency_ms']['p95'] for r in perf['runs'])==perf['median_p95']
    eq=evidence('semantic_equivalence');assert eq['n']==1563 and eq['passed'] and not eq['differences']
    for x,y in [('semantic_before','semantic_after'),('semantic_supplement_before','semantic_supplement_after')]:
        a,b=evidence(x),evidence(y);assert len(a['cases'])==len(b['cases']) and all(c['case_id']==d['case_id'] and c['signature']==d['signature'] for c,d in zip(a['cases'],b['cases']))
    assert evidence('canonical')['counts']['exact']==980 and evidence('canonical_legacy')['counts']['exact']==27
    assert evidence('historical_safety')['n']==241 and not evidence('historical_safety')['false_accepts']
    assert evidence('input_safety')['passed'] and evidence('release_gate_fast')['n']==1258 and evidence('release_gate_fast')['passed']
    assert evidence('historical_regression_fast')['n']==1517 and len(evidence('historical_regression_fast')['mismatches'])==15
    from benchmarks.round18_sampling import sample
    from benchmarks.unknown_release import balance
    master=evidence('unknown_master_pool');m=json.loads(raw('benchmarks/manifests/official_unknown_release_v3.json'))
    chosen=sample(master['eligible_cases'],20261014);assert [c['case_id'] for c in chosen]==[c['case_id'] for c in m['cases']]
    assert len(chosen)==116 and balance(chosen)['max_concentration']==.25
    assert evidence('unknown_subset_feasibility')['capacity_at_100']==112 and evidence('no_prediction_before_selection')['score_or_prediction_used'] is False
    assert m['sampling_policy_sha256']==digest('benchmarks/reference/unknown_release_sampling_policy_v1.json')
    assert m['truth_audit_sha256']==digest('benchmarks/results/round18/unknown_master_pool.json')
    test=evidence('final_tests') if prefix+'benchmarks/results/round18/final_tests.json' in names else evidence('tests')
    assert test['failed']==0 and test['passed']>=829 and gates['tests']==test
    pre=evidence('pre_freeze_gate');u=evidence('unknown_release_v3')
    if gates['freeze']:
        f=evidence('freeze_manifest');assert pre['ready_to_freeze'] and f['freeze_git_commit']==gates['freeze'] and f['unknown_manifest_sha256']==digest('benchmarks/manifests/official_unknown_release_v3.json')
        from scripts.round18_common import infrastructure_sha256
        assert f['infrastructure_sha256']==infrastructure_sha256()
        for p in [ROOT/'scripts/round18_common.py',ROOT/'scripts/round18_freeze.py',ROOT/'scripts/round18_validate.py',ROOT/'tests/test_round18.py',*ROOT.glob('benchmarks/schemas/round18_*.json')]:assert raw(p.relative_to(ROOT).as_posix())==p.read_bytes()
        assert f['unknown_sampling_policy_sha256']==m['sampling_policy_sha256']==digest('benchmarks/reference/unknown_release_sampling_policy_v1.json')
        assert f['contamination_registry_sha256']==m['registry_sha256']==digest('benchmarks/reference/benchmark_contamination_registry_v3.json')
        assert f['runtime_sha256']==perf['identity']['runtime_sha256']==gates['identity']['runtime_sha256']
        for n,h in f['prerequisite_evidence_sha256'].items():assert digest('benchmarks/results/round18/'+n+'.json')==h,n
        if u['status']=='complete':
            from benchmarks.round18_unknown import metrics,validate_observations
            obs=evidence('unknown_release_v3_observations');validate_observations(obs)
            assert len(obs['cases'])==u['n']==116 and all(u[k]==v for k,v in metrics(obs['cases']).items())
            assert u['observations_sha256']==digest('benchmarks/results/round18/unknown_release_v3_observations.json')
    else:assert not pre['ready_to_freeze'] and u['status']=='not_run' and u['recognition_calls']==0
    if prefix+'benchmarks/results/round18/evaluation_v5_gate.json' in names:
        assert u['passed'];v=evidence('evaluation_v5_gate');o=evidence('evaluation_v5_observations')
        assert v['actual_count']==v['expected_count']==len(o['cases'])==len({x['id'] for x in o['cases']})
        assert v['final_observations_sha256']==digest('benchmarks/results/round18/evaluation_v5_observations.json')
        assert gates['local_gates_passed']==(pre['ready_to_freeze'] and u['passed'] and v['passed'])
    else:assert not gates['local_gates_passed']
    assert gates['status']==('READY LOCALLY' if gates['local_gates_passed'] else 'NOT READY')
    return len(locks['historical_original_git_sha256'])
