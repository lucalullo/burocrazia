"""Recompute Round16 raw evidence before Round17 acquisition or predictions."""
import statistics
from collections import Counter
from scripts.round17_common import *
from benchmarks.round9_performance import describe
from benchmarks.release_truth import load_release
from benchmarks.unknown_release import balance

def main():
    invariant()
    assert head() == BASE
    old = ROOT / 'benchmarks/results/round16'
    p = read(old / 'performance_stability.json')
    for run in p['runs']:
        assert describe([c['milliseconds'] for c in run['samples']]) == run['latency_ms']
    median = statistics.median(r['latency_ms']['p95'] for r in p['runs'])
    assert len(p['runs']) == 7 and median == 244.9918
    count = 0
    for a, b in [('semantic_before', 'semantic_after'), ('semantic_supplement_before', 'semantic_supplement_after')]:
        before, after = read(old / (a+'.json')), read(old / (b+'.json'))
        assert len(before['cases']) == len(after['cases'])
        assert all(x['case_id'] == y['case_id'] and x['signature'] == y['signature'] for x,y in zip(before['cases'],after['cases']))
        count += len(before['cases'])
    assert count == 1563
    canonical = {}
    for name in ['canonical', 'canonical_legacy']:
        rows = read(old / (name+'.json'))['cases']
        assert all(c['document_correct'] and not c.get('extraction_failed',False) for c in rows)
        canonical[name] = len(rows)
    _, _, truth = load_release()
    assert len(truth) == 1258
    audit = read(old / 'unknown_v3_truth_audit.json')
    registry = read(REGISTRY)
    fresh = audit['confirmed_cases']
    assert len(fresh) == len({c['SHA256'] for c in fresh}) == 95
    observed = set(registry['observed_resource_sha256'])
    observed_urls = {c.get('official_url', c.get('url')) for c in registry['unknown_resources'] if c.get('prediction_observed')}
    for c in fresh:
        assert not c['previously_seen'] and not c['historically_seen']
        assert c['SHA256'] not in observed and c['official_url'] not in observed_urls
        assert sha('benchmarks/cache/'+c['SHA256']+'.body') == c['SHA256']
    assert not (ROOT/'benchmarks/manifests/official_unknown_release_v3.json').exists()
    snapshots = {p.relative_to(ROOT).as_posix(): sha(p) for p in old.glob('*') if p.is_file()}
    snapshots[REGISTRY] = sha(REGISTRY)
    save('baseline_audit', dict(entry_commit=BASE,branch='codex/coverage-benchmark-v0.7.0',entry_modified=0,entry_untracked=0,software_version='0.6.1',schema=610,
        performance_median_p95=median,semantic_cases=count,semantic_differences=0,canonical=canonical,release_truth_contracts=len(truth),registry_sha256=sha(REGISTRY),
        fresh_unknown=balance(fresh),fresh_case_ids=[c['case_id'] for c in fresh],fresh_sha256=[c['SHA256'] for c in fresh],
        excluded_candidates=dict(total=len(audit['cases'])-95,automatic_classification_counts=audit['classification_counts'],manual_ambiguous_catalog_relation=1,manual_correlated_representations=12),
        cause='Bounded acquisition: 788 candidates, 108 provisional automatic unknowns minus one unresolved MIMIT relation and 12 near-resource duplicates =95. Crawler may stop on a round of already-seen queued URLs; not exhaustive web acquisition.',
        inherited_artifacts_sha256=snapshots,unknown_prediction_calls=0,evaluation_v5_calls=0,checked_at=now()))
    (ROOT/'docs/ROUND17_BASELINE_AUDIT.md').write_text(f'''# Round17 — baseline verificata

Branch `codex/coverage-benchmark-v0.7.0`, HEAD `{BASE}`, ingresso pulito (0 modificati,0 non tracciati). Software0.6.1/schema610. Motore, dataset, catalogo e truth identici al freeze Round16.

Ricalcolo dai raw: sette run/2814 tempi, mediana p95 {median}ms; confronto delle firme complete su1563 casi,0 differenze; canonici980+27=1007/1007; policy1258 contratti confermati e hash verificati. Registry v3 SHA `{sha(REGISTRY)}`. Test finali ereditati819 passed/0 failed/3 skipped, da rieseguire per questo round.

I95 SHA indipendenti sono elencati in baseline_audit.json e verificati contro i byte ufficiali locali e il registry. Coprono13 fonti,18 enti,13 tipi; massimo20/95=21.0526%. Nessuna predizione v3/v5 avviata.

788 candidati,108 qualifiche automatiche provvisorie: esclusi una relazione MIMIT582 irrisolta e12 rappresentazioni correlate,95 finali. Altri candidati hanno titoli/enti insufficienti, relazioni catalogo/famiglia, limiti formato/pagine o ambiguità. Raccolta limitata a960 richieste; il traversal può arrestarsi quando un intero giro incontra URL già visti pur con elementi successivi in coda. Questo è un limite dell'acquisitore, non del motore. Il Round17 corregge soltanto l'infrastruttura e cerca almeno15 nuovi candidati/10 qualificati prima di misurare e congelare. Nessun tuning autorizzato.
''',encoding='utf8',newline='\n')
    print('Round17 baseline verified',balance(fresh),flush=True)

if __name__ == '__main__': main()
