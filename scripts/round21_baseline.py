"""Audit the uncommitted Round20 snapshot before changing its semantics."""
import argparse,csv
from scripts.round21_common import *
from benchmarks.round4_common import runtime_hash
def initial():
    assert head()==BASE
    prior=read('benchmarks/results/round20/evidence_locks.json')
    for p,h in prior['sha256'].items():assert sha(p)==h,p
    paths=[*ROOT.glob('benchmarks/results/round20/*'),*ROOT.glob('docs/ROUND20*.md'),ROOT/'docs/DECISION_POLICY_V6.md',ROOT/'src/fingerprint_decision_v6.py',ROOT/'data/recognition_profiles/fingerprint_decision_v6.json',*ROOT.glob('benchmarks/reference/benchmark_contamination_registry_v*.json'),ROOT/'benchmarks/reference/v5_truth_adjudication_v1.json']
    protected={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(paths) if p.is_file()}
    csv_counts={p.name:len(list(csv.DictReader(p.open(encoding='utf8')))) for p in ROOT.glob('benchmarks/results/round20/*.csv')}
    assert csv_counts['v5_failure_audit.csv']==665 and csv_counts['v5_false_accepts.csv']==8 and csv_counts['v5_false_rejects.csv']==179 and csv_counts['v6_pool_audit.csv']==1019
    for n in ['v5_retrieval_diagnostics','v5_transform_breakdown','v5_source_breakdown']:assert isinstance(read('benchmarks/results/round20/'+n+'.json'),dict)
    raw=read('benchmarks/results/round20/development_observations_v6_safety_final.json');assert raw['complete'] and len(raw['cases'])==raw['expected_count']==3160
    cal=read('benchmarks/results/round20/calibration_v6.json');assert cal['identity']['runtime_sha256']==runtime_hash() and not cal['confirmed_false_accept_ids'] and cal['canonical_exact']==1007
    assert read('dist/package-verification-round20.json')['source_tree_sha256']==ROUND20_TREE
    assert sha('dist/BurOCRazia-v0.7.0-candidate-NOT-READY-round20.zip')==read('dist/package-verification-round20.json')['sha256']
    save('baseline_audit',dict(entry_commit=BASE,entry_source_tree=ROUND20_TREE,branch='codex/coverage-benchmark-v0.7.0',entry_modified=12,entry_untracked=65,protected_sha256=protected,runtime_sha256=runtime_hash(),csv_rows=csv_counts,development=cal['V5_development'],scan=cal['scan'],filled=cal['filled'],prior_tests=read('benchmarks/results/round20/final_tests.json'),prior_performance=read('benchmarks/results/round20/performance_stability.json')['median_p95'],baseline_status='running',checked_at=now()))
    checkpoint('Round21 baseline and non-predictive audits','Round20 snapshot, all artifact hashes/CSV counts and3160 original development cases verified.','Follow baseline pytest session17440; audit residual false rejects and source eligibility without recognition.',[dict(session_id=17440,command='python -m pytest -q -ra --basetemp unique native temp',log='reports/round21-baseline-tests.log',state='running at dispatch')])
    print('R21 initial baseline integrity PASS',len(protected),'protected files',flush=True)
def complete():
    from scripts.round14_baseline import tests
    b=preserved();assert runtime_hash()==b['runtime_sha256']
    t=tests('reports/round21-baseline-tests.log');assert t['passed']==856 and t['failed']==0
    b.update(baseline_status='passed',baseline_tests=t,completed_at=now());save('baseline_audit',b)
    (ROOT/'docs/ROUND21_BASELINE_AUDIT.md').write_text(f"# Round 21 — baseline verificata\n\nBranch `{b['branch']}`, HEAD `{BASE}`; snapshot non committato Round 20 `{ROUND20_TREE}`. All'ingresso12 file modificati/65 non tracciati conservati, indice originale e archivio integri. Software0.6.1/schema610.\n\nTutti gli artefatti richiesti letti e verificati:665 righe audit V5,8 false accept storici,179 false reject storici,1.019 righe pool V6 e3.160 osservazioni complete. V5 Round19 storica P98.2456/R70.5512/scan63.2937; Round20 development P100/R85.3543/scan81.9444/filled100,0 false accept,canonical1007/1007. Misure e raw separati e preservati.\n\nNuova suite completa prima di modifiche semantiche: **{t['passed']} passed/0 failed/{t['skipped']} skipped**, {t['seconds']}s, log SHA `{t['log_sha256']}`. Runtime `{b['runtime_sha256']}` invariato durante la baseline. Performance storica123.6941ms; pool316 identità/4 fonti e unknown fresco disponibile13/1 saranno riauditati, senza assumere una impossibilità definitiva. Ogni nuovo replay resta sviluppo; nessuna predizione di future identità riservate.\n",encoding='utf8',newline='\n')
    print('R21 baseline complete',t,flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['initial','complete']);a=p.parse_args();globals()[a.mode]()
