"""Verify historical V5 on its original freeze; never rewrite or replay it."""
from scripts.round20_common import *
from collections import Counter

def initial():
    from scripts.round19_seal import verify_benchmark_seal
    from benchmarks.evaluate import summary
    s=verify_benchmark_seal();assert head()==BASE
    paths=subprocess.check_output(['git','ls-tree','-r','--name-only',BASE,'benchmarks/results/round19','benchmarks/reference','docs/ROUND19_REPORT.md','benchmarks/manifests/official_unknown_release_v3.json','benchmarks/results/round18'],cwd=ROOT,text=True).splitlines()
    historical={p:sha(p) for p in paths}
    for p in paths:
        actual=(ROOT/p).read_bytes();old=subprocess.check_output(['git','show',BASE+':'+p],cwd=ROOT)
        assert actual==old or actual.replace(b'\r\n',b'\n')==old,p
    r19=ROOT/'benchmarks/results/round19';o=read(r19/'evaluation_v5_observations.json');v=read(r19/'evaluation_v5_gate.json');rows=o['cases']
    assert len(rows)==len({r['id'] for r in rows})==v['actual_count']==v['expected_count']==665
    assert sha(r19/'evaluation_v5_observations.json')==v['final_observations_sha256']
    for name,group in [('robustness_v5',[r for r in rows if not r['unknown']]),('scan_v5',[r for r in rows if r['scan_like']]),('filled_v5',[r for r in rows if r['filled']]),('end_to_end_v5',rows)]:
        artifact=read(r19/(name+'.json'));assert artifact['cases']==group and artifact['summary']==summary(group)
    assert read(r19/'evaluation_v5_leakage.json')['prohibited_leakage']==0
    p=read(r19/'evaluation_v5_plan.json');assert len(p['selected'])==38 and len(p['source_counts'])==6
    failed=[k for k,g in v['gates'].items() if not g['passed']]
    assert set(failed)=={'v5_precision','v5_exact_recall','v5_scan_precision','v5_scan_recall','v5_retrieval_at25'}
    save('baseline_audit',dict(entry_commit=BASE,branch='codex/coverage-benchmark-v0.7.0',entry_working_tree='clean',entry_modified=0,entry_untracked=0,
         historical_freeze_commit=s['semantic_freeze_commit'],recognition_semantic_sha256=s['recognition_semantic_sha256'],historical_sha256=historical,immutable_data_sha256=invariant_data(),
         v5=dict(classification='historical_independent_v5_round19',expected_count=665,actual_count=665,known=635,scans=504,filled=55,unknown_mix=30,identities=38,sources=6,failed_gates=failed,
             hashes={n:sha(r19/(n+'.json')) for n in ['evaluation_v5_plan','evaluation_v5_leakage','evaluation_v5_observations','evaluation_v5_gate','evaluation_v5_representation_audit','failure_diagnostics']},metrics=v['gates']),
         previous_tests=read(r19/'final_tests.json'),previous_performance_median_p95=read(r19/'performance_stability.json')['median_p95'],full_baseline_status='running',checked_at=now()))
    save('historical_independent_v5_round19',dict(classification='historical_independent_v5_round19',freeze_commit=s['semantic_freeze_commit'],artifacts_sha256={p:historical[p] for p in historical if p.startswith('benchmarks/results/round19/')},scope='Original independent single-shot outcome preserved. Any new replay is development_regression_v5_after_fix; unknown v3 becomes historical after semantic changes.'))
    print('R20 original V5 integrity PASS;665 cases;failed',failed,flush=True)

def complete():
    from scripts.round14_baseline import tests
    b=preserved();t=tests('reports/round20-baseline-tests.log');assert t['passed']==834 and t['failed']==0
    from benchmarks.round4_common import runtime_hash
    assert runtime_hash()==b['recognition_semantic_sha256'],'Engine changed before baseline completion'
    b.update(full_baseline_status='passed',baseline_tests=t,baseline_complete_at=now());save('baseline_audit',b)
    (ROOT/'docs/ROUND20_BASELINE_AUDIT.md').write_text(f'''# Round 20 — baseline verificata

Branch `codex/coverage-benchmark-v0.7.0`, HEAD `{BASE}`, working tree pulito all'ingresso:0 modificati/0 non tracciati. Software pubblico0.6.1, schema610.

Freeze storico V5 `{b['historical_freeze_commit']}`, runtime `{b['recognition_semantic_sha256']}`. Tutti i raw V5 caricati, count665/665/665 ID unici,635 noti/504 scan/55 compilati/30 unknown mix;38 identità/6 fonti. SHA selection/leakage/raw/gate/matrice trasformazioni verificati e preservati. Leakage0. Metriche originali ricalcolate sui raw prima delle modifiche e classificate historical_independent_v5_round19: P98.2456%, R70.5512%, scan R63.2937%. Gate falliti:{', '.join(b['v5']['failed_gates'])}.

Suite completa nuova prima delle modifiche semantiche:834 passed/0 failed/3 skipped,{t['seconds']}s; log SHA `{t['log_sha256']}`. Dati/catalogo/schema/profili/truth congelati integri; prove canoniche1007/1007,coverage1002/1158,safety9/9,release-fast1258/1258,equivalenza1563/0diff e sette timing raw Round19 verificati sul medesimo runtime. Mediana p95 storica198.6201ms. Nuova validazione dopo eventuali modifiche rimane obbligatoria e separata.

Unknown v3 originale116/116,13 fonti,0 false accept viene preservato come storico: dopo tuning non valida il nuovo motore. Nessun replay è presentato come indipendente. I successivi registry v5/v6 escluderanno le38 identità V5,635 rappresentazioni e tutte le risorse unknown v1-v3.
''',encoding='utf8',newline='\n')
    print('R20 baseline complete',t,flush=True)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['initial','complete']);a=p.parse_args();dict(initial=initial,complete=complete)[a.mode]()
