"""Round17 archive evidence verification, called by the common packager."""
import hashlib,json,statistics,subprocess
from pathlib import Path
from scripts.round17_common import ROOT,BASE
from benchmarks.round9_performance import describe

def verify(archive,names,gates):
    prefix='BurOCRazia/'
    def raw(p):return archive.read(prefix+p)
    def digest(p):return hashlib.sha256(raw(p)).hexdigest()
    def evidence(n):return json.loads(raw('benchmarks/results/round17/'+n+'.json'))
    locks=evidence('evidence_locks')
    for p,h in locks['sha256'].items():assert digest(p)==h,p
    for p,h in locks['historical_original_git_sha256'].items():assert digest(p)==h,p
    preserved='benchmarks/reference/benchmark_contamination_registry_v3_round16_preserved.json'
    assert raw(preserved)==subprocess.check_output(['git','show',BASE+':benchmarks/reference/benchmark_contamination_registry_v3.json'],cwd=ROOT)
    assert json.loads(raw('benchmarks/reference/benchmark_contamination_registry_v3.json'))['round17_parent_registry_sha256']==digest(preserved)
    old=json.loads(raw('benchmarks/results/round16/freeze_manifest.json'))
    for p,h in old['engine_files_sha256'].items():
        if p=='data/catalog_manifest.json':
            assert raw(p)==subprocess.check_output(['git','show',BASE+':'+p],cwd=ROOT)
            physical=(ROOT/p).read_bytes()
            assert hashlib.sha256(physical).hexdigest()==h
            assert physical.replace(b'\r\n',b'\n')==raw(p) and json.loads(physical)==json.loads(raw(p))
        else:assert digest(p)==h,p
    perf=evidence('performance_stability')
    assert len(perf['runs'])==7 and perf['status']=='complete'
    for r in perf['runs']:
        assert r['sample_count']==len(r['samples'])==402
        assert describe([x['milliseconds'] for x in r['samples']])==r['latency_ms']
    assert statistics.median(r['latency_ms']['p95'] for r in perf['runs'])==perf['median_p95']
    assert perf['required_pass']==(perf['median_p95']<=250)
    eq=evidence('semantic_equivalence');assert eq['n']==1563 and eq['passed'] and not eq['differences']
    for before,after in [('semantic_before','semantic_after'),('semantic_supplement_before','semantic_supplement_after')]:
        a,b=evidence(before),evidence(after)
        assert len(a['cases'])==len(b['cases'])
        assert all(x['case_id']==y['case_id'] and x['signature']==y['signature'] for x,y in zip(a['cases'],b['cases']))
    assert evidence('canonical')['counts']['exact']==980 and evidence('canonical_legacy')['counts']['exact']==27
    assert evidence('historical_safety')['n']==241 and not evidence('historical_safety')['false_accepts']
    assert evidence('input_safety')['passed'] and all(not c['recognition_calls'] and not c['crash'] and not c['temp_residue'] for c in evidence('input_safety')['cases'])
    assert evidence('release_gate_fast')['passed'] and evidence('release_gate_fast')['n']==1258
    assert evidence('historical_regression_fast')['n']==1517 and len(evidence('historical_regression_fast')['mismatches'])==15
    pre=evidence('pre_freeze_gate');pool=evidence('unknown_v3_preflight');u=evidence('unknown_release_v3')
    test=evidence('final_tests') if prefix+'benchmarks/results/round17/final_tests.json' in names else evidence('tests')
    assert test['failed']==0 and test['passed']>=823 and gates['tests']==test
    audit=evidence('unknown_v3_truth_audit')
    assert len(audit['confirmed_cases'])==pool['total']>=95
    if gates['freeze']:
        f=evidence('freeze_manifest');assert f['freeze_git_commit']==gates['freeze'] and pre['ready_to_freeze'] and pool['passed'] and perf['required_pass']
        for n,h in f['prerequisite_evidence_sha256'].items():assert digest('benchmarks/results/round17/'+n+'.json')==h,n
        m=json.loads(raw('benchmarks/manifests/official_unknown_release_v3.json'))
        assert m['freeze_commit']==gates['freeze'] and m['registry_sha256']==digest('benchmarks/reference/benchmark_contamination_registry_v3.json')
        assert m['truth_audit_sha256']==digest('benchmarks/results/round17/unknown_v3_truth_audit.json')
        if u['status']=='complete':
            obs=evidence('unknown_release_v3_observations')
            from benchmarks.round17_unknown import metrics,validate_observations
            validate_observations(obs)
            assert len(obs['cases'])==len(m['cases'])==u['n']>=100
            assert u['observations_sha256']==digest('benchmarks/results/round17/unknown_release_v3_observations.json')
            assert all(u[k]==v for k,v in metrics(obs['cases']).items())
    else:
        assert not pre['ready_to_freeze'] and u['status']=='not_run' and u['recognition_calls']==0
        for p in ['freeze_manifest.json','unknown_v3_started.json','evaluation_v5_started.json']:
            assert prefix+'benchmarks/results/round17/'+p not in names
        assert prefix+'benchmarks/manifests/official_unknown_release_v3.json' not in names
    if prefix+'benchmarks/results/round17/evaluation_v5_gate.json' in names:
        assert u['passed']
        v=evidence('evaluation_v5_gate');o=evidence('evaluation_v5_observations')
        assert v['actual_count']==v['expected_count']==len(o['cases'])==len({x['id'] for x in o['cases']})
        assert v['final_observations_sha256']==digest('benchmarks/results/round17/evaluation_v5_observations.json')
        assert gates['local_gates_passed']==(pre['ready_to_freeze'] and u['passed'] and v['passed'])
    else:assert not gates['local_gates_passed']
    assert gates['status']==('READY LOCALLY' if gates['local_gates_passed'] else 'NOT READY')
    for n in ['docs/ROUND17_REPORT.md','docs/ROUND17_BASELINE_AUDIT.md']:assert raw(n)
    return len(locks['historical_original_git_sha256'])
