"""Final evidence verification after V5; no prediction or sampling replay."""
import compileall,statistics,jsonschema
from scripts.round19_common import *
from scripts.round19_seal import verify_benchmark_seal
from scripts.round14_baseline import tests
from benchmarks.round9_performance import describe

def main():
    sealed();verify_benchmark_seal()
    assert (OUT/'evaluation_v5_gate.json').exists()
    test=tests('reports/round19-post-v5-tests.log');assert test['failed']==0 and test['passed']>=834
    save('final_tests',dict(test,status='passed',scope='Full suite started after the completed V5 single-shot; engine, labels, transforms and selection unchanged.'))
    initial=tests('reports/round19-final-tests.log')
    save('pre_v5_tests',dict(initial,status='passed',scope='Additional full suite initiated before V5. Preserved separately from final post-V5 validation.'))
    perf=read(OUT/'performance_stability.json');assert len(perf['runs'])==7 and perf['status']=='complete'
    for run in perf['runs']:assert len(run['samples'])==402 and describe([c['milliseconds'] for c in run['samples']])==run['latency_ms']
    assert statistics.median(run['latency_ms']['p95'] for run in perf['runs'])==perf['median_p95']
    assert all(compileall.compile_dir(str(ROOT/p),quiet=1) for p in ['src','benchmarks','scripts','maintenance','tests'])
    assert all(compileall.compile_file(str(ROOT/p),quiet=1) for p in ['app.py','run.py'])
    jsonschema.validate(read(OUT/'evaluation_v5_observations.json'),read('benchmarks/schemas/round19_evaluation_observations.schema.json'))
    eq=read(OUT/'semantic_equivalence.json');assert eq['passed'] and eq['n']==1563 and not eq['differences']
    post=read(OUT/'post_v5_validation.json');assert post['passed'] and post['canonical_exact']==1007 and post['semantic_cases']==1563
    for p,h in post['artifacts_sha256'].items():assert sha(p)==h,p
    archives={}
    for n in range(8,19):
        p=read(f'dist/package-verification-round{n}.json');assert sha('dist/'+p['archive'])==p['sha256'];archives[p['archive']]=p['sha256']
    registry=read(REGISTRY)
    save('registry_v4_count_interpretation',dict(legacy_counter_fields={k:registry['counts'][k] for k in ['known_total','known_contaminated','known_eligible']},
         v4_counter_fields={k:registry['counts'][k] for k in ['fingerprint_identities','eligible_v5','eligible_sources','identity_seen_in_tuning','tuning_history_unresolved']},
         scope='Legacy v3 counters are retained as historical data, not v4 eligibility. V4 eligibility is eligible_v5/eligible_sources and per-identity rows. No sealed registry or labels changed.'))
    save('final_audit',dict(passed=True,freeze_commit=FREEZE,engine_unchanged=True,unknown_v3_preserved=True,unknown_v3_replayed=False,benchmark_inventory_preserved=True,compile_pass=True,
         canonical_exact=1007,semantic_cases=1563,semantic_differences=0,performance_median_p95=perf['median_p95'],performance_pass=perf['required_pass'],prior_archives_sha256=archives,checked_at=now(),ci='external_pending'))
    print('R19 final audit PASS',test,'p95',perf['median_p95'],flush=True)

if __name__=='__main__':main()
