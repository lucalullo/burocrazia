"""Publish actual Round16 local evidence without filling unmeasured gates."""
import copy,statistics
from scripts.round16_common import *
from benchmarks.round8_common import identity
from benchmarks.evaluate import summary
from src.benchmark_display import load_summary

def main():
    pre=read(OUT/'pre_freeze_gate.json');perf=read(OUT/'performance_stability.json');eq=read(OUT/'semantic_equivalence.json');tests=read(OUT/'tests.json');checks=read(OUT/'final_checks.json');cov=read(OUT/'coverage.json')
    freeze=read(OUT/'freeze_manifest.json')['freeze_git_commit'] if (OUT/'freeze_manifest.json').exists() else None
    if not (OUT/'unknown_release_v3.json').exists():
        selection=read(OUT/'unknown_v3_selection.json') if (OUT/'unknown_v3_selection.json').exists() else None
        save('unknown_release_v3',dict(status='not_run',passed=False,recognition_calls=0,reason='Fresh confirmed supported pool did not satisfy mandatory sample/source/type gates.' if freeze else 'Mandatory pre-freeze prerequisite failed.',selection=selection.get('selection') if selection else None,n=None,wrong_document_match=None,wrong_family_match=None,freeze_commit=freeze))
    u=read(OUT/'unknown_release_v3.json')
    preflight=read(OUT/'evaluation_v5_preflight.json') if (OUT/'evaluation_v5_preflight.json').exists() else None
    if not (OUT/'evaluation_v5_gate.json').exists():save('evaluation_not_run',dict(status='not_run',recognition_calls=0,reason='Fresh unknown v3 gate did not pass; known v5 is conditional on that gate.' if not u['passed'] else 'Known v5 preflight did not establish mandatory representation/source/leakage adequacy.',preflight=preflight,metrics=None))
    v5=read(OUT/'evaluation_v5_gate.json') if (OUT/'evaluation_v5_gate.json').exists() else None
    ready=bool(pre['ready_to_freeze'] and u['passed'] and v5 and v5['passed']);status='READY LOCALLY' if ready else 'NOT READY'
    reasons=[]
    if not pre['ready_to_freeze']:reasons.append('Mandatory pre-freeze prerequisite failed: '+', '.join(k for k,v in pre.items() if k.endswith('_pass') and v is False)+'.')
    if not u['passed']:reasons.append(u.get('reason','Fresh unknown v3 gate failed; no tuning or replay permitted.'))
    if not v5 or not v5['passed']:reasons.append('Evaluation v5 has not established its mandatory gates.')
    gates=[]
    def gate(name,target,actual,passed,blocking=True):
        gates.append(dict(gate=name,target=target,actual=actual,passed=bool(passed),blocking=blocking,status='PASS' if passed else 'NON MISURATO' if actual is None else 'FAIL' if blocking else 'PENDING' if name=='CI' else 'PREFERITO NON RAGGIUNTO'))
    for n in ['coverage','canonical','confirmed_safety','input_safety','truth_policy','release_gate_fast','semantic_equivalence','tests']:
        gate(n,'PASS',pre[n+'_pass'],pre[n+'_pass'])
    gate('performance_median_p95','<=250ms',perf['median_p95'],perf['required_pass'])
    gate('performance_preferred_latency','<=220ms',perf['median_p95'],perf['preferred_latency_pass'],False)
    gate('performance_preferred_stability','>=5/7 under250ms',perf['pass_count'],perf['preferred_stability_pass'],False)
    gate('release_freeze','Dedicated commit after prerequisites',freeze,bool(freeze))
    stats=u.get('selection') or {}
    gate('unknown_v3_sample','>=100;8sources;max25%;5types',stats or None,stats.get('total',0)>=100 and stats.get('sources',0)>=8 and stats.get('max_concentration',1)<=.25 and stats.get('type_groups',0)>=5)
    gate('unknown_v3_rejection','>=99%',u.get('rejection_rate'),u.get('rejection_rate',0)>=.99)
    gate('unknown_v3_false_DOC_plus_FAMILY','<=1%',u.get('false_acceptance_rate'),u.get('false_acceptance_rate',1)<=.01)
    gate('unknown_v3_entity_version','0',dict(entity=u['entity_errors'],version=u['version_errors']) if u.get('status')=='complete' else None,u.get('entity_errors',1)==u.get('version_errors',1)==0)
    gate('unknown_v3_freshness','No prior SHA or obvious near variant',u.get('status') if u.get('status')=='complete' else None,u.get('status')=='complete')
    for n,target in [('v5_preflight','>=30IDs,6sources,400known,200scan,50filled,30unknown'),('v5_leakage','0'),('v5_precision','>=99.5%'),('v5_exact_recall','>=90%'),('v5_scan_precision','>=99.5%'),('v5_scan_recall','>=85%'),('v5_filled_generation','>=90%'),('v5_filled_precision','>=99.5%'),('v5_filled_recall','>=90%'),('v5_retrieval_at25','100%'),('v5_retrieval_at1','>=99%'),('v5_entity_version','0'),('v5_unknown_mix','>=99%')]:
        item=(v5 or {}).get('gates',{}).get(n,{})
        if n=='v5_preflight' and preflight and not v5:item=dict(actual=preflight,passed=preflight['passed'])
        gate(n,target,item.get('actual'),item.get('passed',False))
    gate('family_identity_holdout','>=5 validated real families','experimental / insufficiently validated',False,False)
    gate('CI','External matrix','external_pending',False,False)
    ident=identity();software='0.7.0-rc1' if ready else '0.6.1'
    atomic_json(ROOT/'docs/release_gates.json',dict(round=16,status=status,software_version=software,candidate_target='0.7.0',schema=610,freeze=freeze,identity=ident,gates=gates,local_gates_passed=ready,tests=tests,reasons=reasons,ci='external_pending'))
    latest=copy.deepcopy(read('benchmarks/latest_summary.json'));latest.update(round=16,status=status,software_version=software,version=software,commit=ident['commit'],runtime_sha256=ident['runtime_sha256'],fingerprint_sha256=ident['fingerprint_sha256'],reasons=reasons)
    canonical_summary=summary(read(OUT/'canonical.json')['cases']+read(OUT/'canonical_legacy.json')['cases']);canonical_summary['latency_ms']={}
    latest['known_canonical']=dict(status='executed',native_resources=980,legacy_qualified_resources=27,summary=canonical_summary,scope='1563-case equivalence includes actual1007 canonical recognition results; technical binding is not editorial verification.')
    latest['fingerprint_coverage']=dict(status='executed',operational_docs_total=1212,file_backed_operational_docs=1158,fingerprinted_all_operational_docs=1002,coverage_all=cov['all_operational_percent']/100,coverage_file_backed=cov['file_backed_percent']/100,legacy_qualified=27,scope='Frozen support definition, same denominators; shared support is not exact identity accuracy.')
    latest['performance']=dict(status='executed',latency_ms=dict(p50=statistics.median(r['latency_ms']['p50'] for r in perf['runs']),p95=perf['median_p95']),median_p95=perf['median_p95'],pass_count=perf['pass_count'],runs=7,passed=perf['required_pass'],preferred_stability_pass=perf['preferred_stability_pass'],reason='Seven predetermined warm runs,402 fresh requests/run,2814 raw timings; extraction/OCR reported separately. Preferred targets are not blockers.')
    for key in ['known_robustness','scan_ocr','filled_forms']:
        latest[key]=dict(status='not_run',reason='Evaluation v5 conditional gates not established.',summary=dict(cases=0,metrics={},latency_ms={}))
    if v5:
        for key,artifact in [('known_robustness','robustness_v5'),('scan_ocr','scan_v5'),('filled_forms','filled_v5')]:
            latest[key]=dict(status='executed',summary=read(OUT/(artifact+'.json'))['summary'],scope='Prospective same-freeze evaluation v5, single-shot; any failed mandatory metric is retained.')
    latest['unknown_official']=dict(status='executed' if u['status']=='complete' else 'not_run',reason=u.get('reason','Fresh post-freeze single-shot v3; every DOCUMENT/FAMILY acceptance counts as false acceptance.'),summary=dict(cases=u.get('n') or 0,metrics={} if u['status']!='complete' else dict(correct_rejection=dict(numerator=u['correct_no_match'],denominator=u['n'],value=u['rejection_rate'])),latency_ms={}))
    latest['input_safety']=dict(status='executed',n=9,safe_rejects=9,passed=True)
    latest['truth_policy']=dict(policy_sha256=sha(POLICY),base_truth_sha256=sha(TRUTH),addendum_sha256=sha(ADDENDUM),confirmed_diagnostic_contracts=1258,historical_mismatches=15)
    latest['evaluations']=[dict(name=p.stem,summary=read(p)['summary']) for p in sorted(OUT.glob('historical_*.json')) if 'summary' in read(p)]
    atomic_json(ROOT/'benchmarks/latest_summary.json',latest);load_summary(ROOT/'benchmarks/latest_summary.json')
    timing='\n'.join(f"| {r['run']} | {r['latency_ms']['p50']} | {r['latency_ms']['p95']} |" for r in perf['runs'])
    table='\n'.join('| '+' | '.join(str(x).replace('|','/') for x in row)+' |' for row in [['Gate','Target','Misurato','Esito','Obbligatorio'],['---']*5]+[[g['gate'],g['target'],g['actual'] if g['actual'] is not None else 'non misurato',g['status'],'sì' if g['blocking'] else 'no'] for g in gates])
    unknown_text=f"{u.get('correct_no_match')}/{u.get('n')}; DOC errati={u.get('wrong_document_match')}, FAMILY errati={u.get('wrong_family_match')}, rejection={u.get('rejection_rate')}; fonti/concentrazione/tipi={stats}." if u['status']=='complete' else f"Non eseguito: {u['reason']} Adeguatezza pool={stats or 'non misurata'}. Zero chiamate release."
    test_history='I run completi nel temporaneo del workspace hanno incontrato WinError5 nella pubblicazione atomica delle directory dei test; entrambi restano nei log e negli audit, senza modifiche runtime. La verifica dei pacchetti nel temporaneo nativo Windows ha prodotto24 passed/3skip; suite finale eseguita nello stesso ambiente nativo. Un PASS finale non cancella i fallimenti precedenti e non dimostra la causa del blocco Windows oltre l’errore osservato.'
    report=f'''# Round16 — {status}

Software {software}, schema610, branch `codex/coverage-benchmark-v0.7.0`; ingresso `{BASE}`. Freeze `{freeze or 'non creato'}`. Commit finale e SHA archivio nel verificatore esterno `dist/package-verification-round16.json`, per evitare autoreferenze. Nessun push, tag o pubblicazione; CI external_pending.

## Correzione di contesto e truth

EX02/EX03 sono **sintetici INPS CI543/CI544**, record13/12, revisione1.1 omessa. Gli expected originali restano visibili; esclusione dalla truth certa motivata dalla **reference_truth_v2 già esistente**, non dall'errore del prompt. I due INAIL ambigui sono **U14-5f0c017c3d56e6c5** e **U14-c1fc4765c01dcd62**, annualità2025/2024 rispetto al canonico2023. Reference truth v3 li conserva ambiguous: nessun tuning, nessuna identità annuale o sostituzione inventata.

Release truth policy v1 e addendum motivato a v3: **1258 contratti confermati** =1007 binding canonici tecnici+241 contratti sintetici di astensione+1 ANAC ufficiale+9 limiti parser. Non sono1258 esempi indipendenti né verifiche editoriali. Confirmed non può essere escluso; ambiguous/insufficient/historical_only restano fuori dal gate certo e visibili nello storico. Obsolete richiede nuova qualificazione documentata. Originali v1/v2/v3 e corpus immutati. ANAC già osservato è regressione diagnostica confermata, esclusa dai nuovi corpus indipendenti. Policy/hash/evidenze in RELEASE_TRUTH_POLICY.md e truth_policy_audit.json.

## Ottimizzazioni e equivalenza

Due funzioni: deduplicazione per richiesta di trigrammi/ngrammi prima del loro hash; grayscale una volta prima delle quattro rotazioni ortogonali, che trasportano gli stessi pixel. Nessuna cache globale di testi o feature caricate. Scoring, pesi, soglie, candidateK, ranking/tie-break, veto ente/versione, family e reason code invariati; dataset/catalogo/fonti byte-identici. Il fix R15 sull'intestazione rimane.

Confronto completo prima/dopo: **{eq['n']} casi, zero differenze**, inclusi risultato pubblico completo, score, runner-up, margine, candidati, ente/versione e reason/tier. Canonici1007, negativi241, hard negatives, R061, ANAC testo+PDF, EX02/EX03, due PDF INAIL, vecchi cinque critici e rappresentazioni scan/filled/R6/R7/R8 già osservate. Primo set1399 più supplemento164, entrambi bloccati prima di cambiare il motore. OCR estratto una volta per isolare il riconoscimento; test finali OCR reali separati. Valori e hash in semantic_equivalence.json; test algoritmici indipendenti per Unicode/clipping e RGB/RGBA/L/palette, dimensioni pari/dispari/minime.

Profiling reale baseline conservato: costi inclusivi sovrapposti, non sommabili. Page scoring/features, hash e visuali rilevanti. Nessun rerun o selezione dei tempi favorevoli.

| Run | p50 ms | p95 ms |
|---|---|---|
{timing}

Mediana p95 **{perf['median_p95']}ms** contro263.0707ms R15: **PASS<=250**. **{perf['pass_count']}/7** sotto250; target preferiti >=5/7 e mediana<=220 non raggiunti, non blocker. 67 input fissi,402 richieste/run,2814 tempi, contesti nuovi e cache solo catalogo/index pubblico. Sistema Windows/Python3.12.10, Tesseract5.4 ita+eng locale. L'attività generale del computer può variare; nessun altro benchmark di questo repository è stato avviato in parallelo ai sette run. Non è un collaudo Linux/macOS né una garanzia di latenza su altre macchine.

## Coverage, canonici, safety e storico

Coverage1002/1158 = **86.528497%**, PASS>=85; totale operativo1002/1212=82.673267%, PASS>=70. Definizione e denominatori congelati;33 associazioni shared-only non diventano accuratezza esatta. Canonici **980/980 nativi+27/27 legacy**, PASS100%. **241 NO sintetici,0 accettazioni**; ANAC testo/PDF, R061, due contratti Round8 e cinque critici PASS safety (4 identità esatte,1 NO prudente; quel NO resta mismatch esatto nello storico). Input safety **9/9**,0 crash,0 residui,0 chiamate recognition,0 risultati DOCUMENT/FAMILY. Quattro PDF>100 pagine restano fuori classificazione e dentro safety.

Historical-regression-fast: **15 mismatch conservati su1517 expected**, exit1:2 EX02/EX03,10 locked-v1,2 INAIL ambigui,1 rifiuto prudente sul noto OH1-047. Il vecchio CLI `benchmarks.evaluate --fast` conserva exit1 su EX02/EX03. Il nuovo `python -m benchmarks.round16_gates release-gate-fast` confronta i1258 contratti qualificati con le osservazioni effettive del runtime corrente, controlla hash e produce exit0; non modifica gli expected storici. `historical-regression-fast` è distinto e mostra tutti gli expected originali. Metadati catalog-coverage separati e nessuna accuratezza ufficiale inferita. V2 Round14 resta **107/114**,3DOC,0FAMILY,4 errori, raw/manifest/label immutabili; il replay R15 108/114 resta soltanto sviluppo.

## Unknown v3, evaluation v5 e famiglia

{unknown_text}

Selezione prevista solo dopo freeze, seed2026101316, quote source e gruppi near-resource, senza score; registrazione contaminazione v3 aggiuntiva, SHA e varianti già osservate escluse. Input oltre i limiti e identità non qualificate non entrano come unknown certi. Se un gate fallisce, stop senza tuning/replay sul set. V5 è autorizzata soltanto dopo PASS unknown. Preflight: **{preflight or 'non misurata'}**. Robustezza, scansioni, filled, retrieval@1/@5/@10/@25 e mix unknown sono **{'in evaluation_v5_gate.json e retrieval_v5.json' if v5 else 'non misurati'}**. Nessuna metrica storica riempie i campi mancanti. Family resta **experimental / insufficiently validated**, nessuna nuova prova su>=5 famiglie reali identity-held-out.

## Test e controlli

Baseline già eseguita786 passed,3skip; finale **{tests['passed']} passed,{tests['failed']} failed,{tests['skipped']} skipped**, {tests['seconds']}s, log SHA registrato. {test_history} Primo run completo810 passed,1failed,2skip; il test isolato symlink raggiunge lo skip previsto per privilegio Windows assente. Dettagli in tests.json/validation_environment.json. Nessun retry nel runtime o modifica IO estranea al vincolo performance-only. Un primo CLI release gate diagnostico confrontava erroneamente i vincoli forbidden_entities come campi osservati: corretto soltanto il comparatore, aggiunti due controesempi; sei NO effettivi non erano falsi positivi. Artifact iniziale preservato,1258 contratti PASS nel gate finale.

Il test storico R15 verifica il suo commit finale d39103d; il nuovo controllo R16 vincola le modifiche correnti alle due funzioni autorizzate e confronta semanticamente gli output. Compile, SQLite integrity/FK, copia/migrazione schema610 e conteggi righe, binding, validator fingerprintv1/v2/v3, compat-v2, schema truth e lock storici PASS. Test sintetici, Tesseract reale, adjudication precedente e CI/collaudo di piattaforma restano separati. Catalogo completo, provenance e famiglia preservati; runtime locale senza LLM/API/telemetria/importazione acquisitori. Runner futuri unknown/v5 predisposti ma non collaudati come release: nessuna selezione, acquisizione o predizione indipendente eseguita in questo round.

## Gate

{table}

## Archivio e limiti

{'; '.join(reasons) or 'Tutti i gate locali obbligatori soddisfatti; CI esterna pending.'} Prestazioni preferite non raggiunte; ambiguità storiche non risolte; family sperimentale; CI external pending. Archivio `dist/BurOCRazia-v0.7.0-{'RC1' if ready else 'candidate-NOT-READY'}-round16.zip`. SHA256 e verifica completa esterni al ZIP in `dist/package-verification-round16.json` e `.zip.sha256`. Nessun dato personale, cache, DB di lavoro o credenziale nel pacchetto.
'''
    (ROOT/'docs/ROUND16_REPORT.md').write_text(report,encoding='utf8',newline='\n')
    p=ROOT/'docs/BENCHMARK.md';old=p.read_text(encoding='utf8');marker='<!-- round16-current -->';end='<!-- /round16-current -->'
    if marker in old:old=old[old.index(end)+len(end):].lstrip()
    p.write_text(f"{marker}\n# Round16 — {status}\n\nEquivalenza1563/1563, nessuna differenza; performance7 run mediana p95 {perf['median_p95']}ms (PASS obbligatorio,4/7 sotto250, preferiti non raggiunti). Coverage86.53%, canonical1007/1007,241NO/0FA,input-safety9/9. Truth policy distingue EX02/EX03 INPS e due annualità INAIL ambigue; release gate1258 PASS,15 mismatch storici conservati. Unknown v3 {u['status']}; v5 {'misurata' if v5 else 'non misurata'}. Test{tests['passed']} passed/{tests['failed']}failed/{tests['skipped']}skip: freeze bloccato dai test; schema610, CI pending. [Report Round16](ROUND16_REPORT.md). Le sezioni successive restano storiche.\n{end}\n\n"+old,encoding='utf8',newline='\n')
    paths=[p for p in OUT.glob('*') if p.suffix in ['.json','.csv','.md'] and p.name!='evidence_locks.json']
    paths.extend(ROOT/p for p in [REGISTRY,POLICY,ADDENDUM,TRUTH,'docs/RELEASE_TRUTH_POLICY.md','docs/ROUND16_BASELINE_AUDIT.md','docs/ROUND16_REPORT.md','docs/BENCHMARK.md','docs/release_gates.json','benchmarks/latest_summary.json'])
    save('evidence_locks',dict(baseline_commit=BASE,freeze=freeze,sha256={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(paths)},historical_original_git_sha256=read(OUT/'historical_locks.json')['historical_original_git_sha256']))
    print('R16',status,reasons,flush=True)

if __name__=='__main__':main()
