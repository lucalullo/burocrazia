"""Round18 inherited evidence recomputation and acquisition-free feasibility."""
import statistics
from scripts.round18_common import *
from benchmarks.unknown_release import balance
from benchmarks.round9_performance import describe
from benchmarks.release_truth import load_release

def main():
    invariant();assert head()==BASE
    cases=read('benchmarks/results/round17/unknown_v3_truth_audit.json')['confirmed_cases'];b=balance(cases)
    assert b['total']==129 and b['counts_per_source']['inl']==42
    r=read(REGISTRY);assert not {c['SHA256'] for c in cases}&set(r['observed_resource_sha256'])
    for c in cases:assert sha('benchmarks/cache/'+c['SHA256']+'.body')==c['SHA256'] and not c['previously_seen']
    for round in [16,17]:
        for name in ['unknown_v3_started.json','evaluation_v5_started.json']:assert not (ROOT/f'benchmarks/results/round{round}'/name).exists()
        for name in ['unknown-release-v3.sqlite','evaluation-v5/evaluation.sqlite']:assert not (ROOT/f'benchmarks/work/round{round}'/name).exists()
    assert not (ROOT/'benchmarks/manifests/official_unknown_release_v3.json').exists()
    p=read('benchmarks/results/round17/performance_stability.json')
    for run in p['runs']:assert describe([c['milliseconds'] for c in run['samples']])==run['latency_ms']
    assert statistics.median(x['latency_ms']['p95'] for x in p['runs'])==231.5144
    count=0
    for before,after in [('semantic_before','semantic_after'),('semantic_supplement_before','semantic_supplement_after')]:
        a=read('benchmarks/results/round17/'+before+'.json')['cases'];z=read('benchmarks/results/round17/'+after+'.json')['cases']
        assert len(a)==len(z) and all(x['case_id']==y['case_id'] and x['signature']==y['signature'] for x,y in zip(a,z));count+=len(a)
    assert count==1563
    for name in ['canonical','canonical_legacy']:assert all(c['document_correct'] for c in read('benchmarks/results/round17/'+name+'.json')['cases'])
    t=read('benchmarks/results/round17/final_tests.json');assert (t['passed'],t['failed'],t['skipped'])==(823,0,3) and sha('reports/round17-prefreeze-tests.log')==t['log_sha256']
    load_release()
    save('baseline_audit',dict(entry_commit=BASE,branch='codex/coverage-benchmark-v0.7.0',working_tree_at_entry='clean',software_version='0.6.1',schema=610,master=b,performance_median_p95=231.5144,canonical_exact=1007,semantic_cases=1563,semantic_differences=0,tests=t,registry_sha256=sha(REGISTRY),master_audit_sha256=sha('benchmarks/results/round17/unknown_v3_truth_audit.json'),unknown_prediction_calls=0,evaluation_prediction_calls=0,checked_at=now()))
    (ROOT/'docs/ROUND18_BASELINE_AUDIT.md').write_text(f'''# Round18 — baseline verificata

Branch `codex/coverage-benchmark-v0.7.0`, HEAD `{BASE}`, working tree pulito all'ingresso. Software0.6.1/schema610. Motore, catalogo, dataset e truth identici al freeze Round16.

Raw Round17 ricalcolati: sette run/2814 tempi, mediana p95 231.5144ms; canonici1007/1007;1563 firme complete senza differenze; test823 passed/0 failed/3 skipped, hash log verificato. Nessun manifest/prediction marker/journal v3 o v5 Round16/17. Tutti i129 SHA disponibili verificati sui byte ufficiali locali e senza overlap nel registry.

Master129,13 fonti,19 enti; INL42/129=32.5581%. Capacità per N100 con cap25:112. Il master può essere sbilanciato: il limite25% riguarda il subset release. La massima dimensione sostenibile è116 (cap29,87 altri casi). Nessuna acquisizione necessaria o autorizzata dal ramo fattibile. Selezione prospettica con soli metadata/seed; nessuna predizione/score fresh disponibile. Artifact storici e fallimento metodologico Round17 restano immutati.
''',encoding='utf8',newline='\n')
    print('R18 baseline verified',b,flush=True)

if __name__=='__main__':main()
