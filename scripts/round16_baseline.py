"""Recompute inherited measurements and document the prompt's identifier error."""
import statistics
from collections import Counter
from scripts.round16_common import *
from scripts.round14_baseline import tests
from benchmarks.round9_performance import describe
from benchmarks.round14_unknown import metrics

def main():
    assert head()==BASE
    locks=read('benchmarks/results/round15/evidence_locks.json')
    for p,h in locks['sha256'].items():assert sha(p)==h,p
    old=historical();test=tests('reports/round16-baseline-tests.log');save('baseline_tests',test)
    counts={}
    for name in ['canonical','canonical_legacy']:
        r=read('benchmarks/results/round15/'+name+'.json');rows=r['cases']
        counts[name]=dict(n=len(rows),exact=sum(c['observed']['match_type']=='DOCUMENT_MATCH' and c['observed']['document_id']==c['expected']['document_id'] and not c['extraction_failed'] for c in rows),extraction_failed=sum(c['extraction_failed'] for c in rows))
        assert counts[name]['exact']==len(rows)
    hist=[c for p in (ROOT/'benchmarks/results/round15').glob('historical_*.json') for c in read(p).get('cases',[])]
    no=[c for c in hist if c['expected']['match_type']=='NO_MATCH'];assert len(no)==241 and all(c['observed']['match_type']=='NO_MATCH' for c in no)
    p=read('benchmarks/results/round15/performance_pre_freeze.json')
    for run in p['runs']:assert describe([c['milliseconds'] for c in run['samples']])==run['latency_ms']
    median=statistics.median(run['latency_ms']['p95'] for run in p['runs']);assert median==263.0707
    u=read('benchmarks/results/round14/unknown_release_v2.json');raw=read('benchmarks/results/round14/unknown_release_v2_observations.json')
    recomputed=metrics(raw['cases']);assert all(u[k]==v for k,v in recomputed.items()) and recomputed['correct_no_match']==107
    v3=read(TRUTH);ambiguous=[c['case_id'] for c in v3['cases'] if c['confidence']=='ambiguous'];assert len(ambiguous)==2
    v2=read('benchmarks/reference/reference_truth_v2.json');legacy=[c for c in v2['cases'] if c['corpus']=='benchmarks/corpora/development_regression.json' and c['case_id'] in ['EX02','EX03']]
    assert len(legacy)==2 and all(c['confidence_status']=='ambiguous' and c['source_evidence'][0]['entity']=='INPS' for c in legacy)
    fast={p.stem:read(p) for p in (ROOT/'reports/round15-fast').glob('*.json')};failed=[dict(corpus=k,case_id=c['id']) for k,v in fast.items() for c in v.get('cases',[]) if not c['correct'] and k!='release_locked_v1']
    assert {c['case_id'] for c in failed}=={'EX02','EX03'}
    profile=read(OUT/'performance_profile.json');assert profile['identity']['runtime_sha256']==p['identity']['runtime_sha256']
    save('baseline_audit',dict(entry_commit=BASE,branch='codex/coverage-benchmark-v0.7.0',entry_working_tree='clean',software_version='0.6.1',schema=610,canonical=counts,confirmed_NO=dict(rows=241,false_accepts=0),
        historical_unknown_v2=recomputed,input_safety=read('benchmarks/results/round15/input_safety.json'),coverage=read('benchmarks/results/round15/coverage.json'),
        performance=dict(p95=[r['latency_ms']['p95'] for r in p['runs']],median_p95=median),legacy_fast_mismatches=failed,
        prompt_identifier_correction=dict(EX02_EX03='INPS CI543/CI544, omitted1.1 revision, ambiguous in truth v2',INAIL=ambiguous,distinct_groups=True),
        reference_truth_v3_sha256=sha(TRUTH),reference_truth_v2_sha256=sha('benchmarks/reference/reference_truth_v2.json'),baseline_tests=test,historical_git_blobs_verified=len(old),profile_sha256=sha(OUT/'performance_profile.json'),created_at=now()))
    (ROOT/'docs/ROUND16_BASELINE_AUDIT.md').write_text(f'''# Round 16 — baseline

Branch `codex/coverage-benchmark-v0.7.0`, HEAD `{BASE}`, working tree pulito all'ingresso. Software0.6.1/schema610. {len(old)} blob storici e tutti i lock Round15 verificati prima delle modifiche al motore.

Metriche ricalcolate dai raw: canonici980/980+27/27;241 righe NO storiche senza accettazioni; input-safety9/9; coverage1002/1158=86.528497%. Cinque run/2010 tempi: mediana p95 {median}ms. V2 storico107/114,3 DOCUMENT_MATCH,0 FAMILY_MATCH,4 errori, denominatore e label intatti. Nessun freeze/v3 indipendente/v5 Round15.

**Correzione fattuale del prompt:** EX02/EX03 sono INPS CI543/CI544 (record13/12), input sintetici privi della revisione1.1, già ambiguous in reference_truth_v2. I due INAIL ambigui sono U14-5f0c017c3d56e6c5 e U14-c1fc4765c01dcd62, record1147, annualità2025/2024 rispetto al canonico2023. Sono quattro risorse/casi distinti. Non vengono equiparati né usati per tuning. La release-fast preesistente ha soltanto EX02/EX03 come mismatch obbligatori; locked-v1 conserva separatamente i suoi10 mismatch storici.

Baseline completa: {test['passed']} passed,0 failed,{test['skipped']} skipped. Profilo reale dei67 input storici in performance_profile.json, prima di ogni ottimizzazione; misure cProfile/tracing diagnostiche, non sostituiscono i sette run warm finali. Nessun cambio a scoring, tiers, soglie, pesi, veto, famiglie, dataset o catalogo autorizzato. La release truth verrà estesa tramite addendum motivato, preservando v1/v2/v3 e distinguendo prove ufficiali, binding canonici tecnici e contratti sintetici di sicurezza.
''',encoding='utf8',newline='\n')
    print('Round16 baseline complete',test,flush=True)
if __name__=='__main__':main()
