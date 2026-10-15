"""Check historical bytes, current development measurements and stopped gates."""
import csv,hashlib,json,statistics,subprocess
from scripts.round20_common import ROOT,BASE
from benchmarks.round9_performance import describe

def verify(archive,names,gates):
    prefix='BurOCRazia/'
    def raw(p):return archive.read(prefix+p)
    def digest(p):return hashlib.sha256(raw(p)).hexdigest()
    def data(p):return json.loads(raw(p))
    def r(n):return data('benchmarks/results/round20/'+n+'.json')
    b=r('baseline_audit');assert b['entry_commit']==BASE and b['baseline_tests']['passed']==834 and b['baseline_tests']['failed']==0
    old=data('benchmarks/results/round19/evidence_locks.json')
    preserved=set(old['historical_original_git_sha256'])|set(b['historical_sha256'])
    for p,h in old['historical_original_git_sha256'].items():assert digest(p)==h,p
    for p,h in b['historical_sha256'].items():
        assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,p
        assert raw(p)==subprocess.check_output(['git','show',BASE+':'+p],cwd=ROOT),p
    for p,h in b['immutable_data_sha256'].items():
        actual=(ROOT/p).read_bytes();assert hashlib.sha256(actual).hexdigest()==h,p
        assert raw(p)==actual or (p=='data/catalog_manifest.json' and raw(p)==actual.replace(b'\r\n',b'\n')),p
    locks=r('evidence_locks')
    for p,h in locks['sha256'].items():assert digest(p)==h,p
    cal=r('calibration_v6');observations=data(cal['observations_path'])
    assert digest(cal['observations_path'])==cal['observations_sha256']
    assert observations['complete'] and len(observations['cases'])==len({c['id'] for c in observations['cases']})==observations['expected_count']==cal['actual_count']
    assert cal['identity']['runtime_sha256']==gates['identity']['runtime_sha256']
    assert cal['identity']['profile_sha256']==digest('data/recognition_profiles/fingerprint_decision_v6.json')
    rows=[c for c in observations['cases'] if c['group']=='v5'];assert len(rows)==635
    def rates(cs):
        tp=sum(c['document_correct'] for c in cs);ac=sum(c['observed']['match_type']=='DOCUMENT_MATCH' for c in cs)
        return dict(n=len(cs),exact=tp,accepted=ac,wrong=ac-tp,precision=tp/ac if ac else 0,recall=tp/len(cs) if cs else 0)
    assert rates(rows)==cal['V5_development']
    assert rates([c for c in rows if c['scan_like']])==cal['scan']
    assert rates([c for c in rows if c['filled']])==cal['filled']
    assert sum(c['document_correct'] for c in observations['cases'] if c['group']=='canonical')==cal['canonical_exact']==1007
    audit=list(csv.DictReader(raw('benchmarks/results/round20/v5_failure_audit.csv').decode('utf8').splitlines()))
    assert len(audit)==665 and len({a['case_id'] for a in audit})==665
    v5=r('historical_independent_v5_round19');assert v5['classification']=='historical_independent_v5_round19' and v5['freeze_commit']==b['historical_freeze_commit']
    v6=data('benchmarks/reference/benchmark_contamination_registry_v6.json');v4=data('benchmarks/reference/benchmark_contamination_registry_v4.json')
    v5reg=data('benchmarks/reference/benchmark_contamination_registry_v5.json')
    assert v6['parent_registry_sha256']==digest('benchmarks/reference/benchmark_contamination_registry_v5.json')
    assert v5reg['parent_registry_sha256']==digest('benchmarks/reference/benchmark_contamination_registry_v4.json')
    by4={k['document_id']:k for k in v4['known_identities']}
    assert all(k['legacy_v3']==by4[k['document_id']]['legacy_v3'] for k in v6['known_identities'])
    assert set(cal['identity_ids'])<=set(v6['round20']['calibration_identity_ids'])
    pool=list(csv.DictReader(raw('benchmarks/results/round20/v6_pool_audit.csv').decode('utf8').splitlines()))
    eligible=[a for a in pool if a['eligible_v6']=='True'];pre=r('v6_preflight')
    assert len(pool)==1019 and len({a['document_id'] for a in pool})==1019
    assert pre['identities']==len(eligible) and pre['sources']==len({a['source'] for a in eligible})
    assert all(a['tuning_seen']=='False' and a['V5_seen']=='False' and a['development_seen']=='False' for a in eligible)
    perf=r('performance_stability');assert perf['status']=='complete' and len(perf['runs'])==7
    for run in perf['runs']:
        assert len(run['samples'])==402 and len({c['case_id'] for c in run['samples']})==67
        assert describe([c['milliseconds'] for c in run['samples']])==run['latency_ms']
    assert perf['median_p95']==statistics.median(run['latency_ms']['p95'] for run in perf['runs'])
    assert perf['required_pass']==(perf['median_p95']<=250) and perf['identity']['runtime_sha256']==gates['identity']['runtime_sha256']
    test=r('final_tests');assert test['failed']==0 and test['passed']>=850 and gates['tests']==test
    assert r('final_checks')['runtime_sha256']==gates['identity']['runtime_sha256']
    prefreeze=r('pre_freeze_gate');assert not prefreeze['ready_to_freeze'] and gates['status']=='NOT READY' and gates['freeze'] is None
    assert all(prefreeze[k]==v for k,v in cal['gates'].items())
    assert prefreeze['performance_pass']==perf['required_pass']
    assert prefreeze['tests_pass']==(test['failed']==0)
    assert prefreeze['V6_pool_pass']==pre['passed']
    assert prefreeze['unknown_v4_preflight_pass']==r('unknown_v4_preflight')['passed']
    assert not cal['confirmed_false_accept_ids'] and not cal['negative_false_accept_ids']
    hard=r('hard_negatives_development');assert hard['n']==len(hard['cases'])==hard['correct_rejects'] and not hard['false_accept_ids'] and hard['passed']
    assert all(c['observed']['match_type']=='NO_MATCH' for c in hard['cases'])
    for p in ['benchmarks/results/round20/freeze_manifest.json','benchmarks/manifests/official_unknown_release_v4.json','benchmarks/results/round20/unknown_release_v4.json','benchmarks/results/round20/evaluation_v6_observations.json']:
        assert prefix+p not in names,p
    for n in ['robustness_v6','scan_v6','filled_v6','retrieval_v6','end_to_end_v6','unknown_v4_not_run']:
        value=r(n);assert value['status']=='not_run' and value['recognition_calls']==0 and not value['cases'] and value['summary']['metrics']=={}
    latest=data('benchmarks/latest_summary.json');assert latest['round']==20 and latest['status']==gates['status']
    for key in ['known_robustness','scan_ocr','filled_forms','unknown_official']:
        assert latest[key]['status']=='not_run' and latest[key]['summary']['metrics']=={}
    return len(preserved)
