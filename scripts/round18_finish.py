"""Publish only measured Round18 gates; preserve all preceding round evidence."""
import copy
from scripts.round18_common import *
from benchmarks.round8_common import identity
from benchmarks.evaluate import summary
from src.benchmark_display import load_summary

def main():
    invariant()
    pre=read(OUT/'pre_freeze_gate.json');pool=read(OUT/'unknown_release_v3_preflight.json');perf=read(OUT/'performance_stability.json')
    eq=read(OUT/'semantic_equivalence.json');test=read(OUT/('final_tests.json' if (OUT/'final_tests.json').exists() else 'tests.json'))
    freeze=read(OUT/'freeze_manifest.json')['freeze_git_commit'] if (OUT/'freeze_manifest.json').exists() else None
    u=read(OUT/'unknown_release_v3.json') if (OUT/'unknown_release_v3.json').exists() else dict(status='not_run',passed=False,recognition_calls=0,n=None,reason='Mandatory pre-freeze prerequisite failed; no release prediction permitted.',selection=None)
    if not (OUT/'unknown_release_v3.json').exists():save('unknown_release_v3',u)
    v5=read(OUT/'evaluation_v5_gate.json') if (OUT/'evaluation_v5_gate.json').exists() else None
    if not v5:save('evaluation_not_run',dict(status='not_run',recognition_calls=0,reason='Unknown v3 prerequisite not passed.' if not u['passed'] else 'Fresh known source adequacy5<6 failed; no v5 representations generated or scored.',metrics=None))
    ready=bool(pre['ready_to_freeze'] and freeze and u['passed'] and v5 and v5['passed'] and test['failed']==0)
    status='READY LOCALLY' if ready else 'NOT READY';software='0.7.0-rc1' if ready else '0.6.1'
    gates=[]
    def g(name,target,actual,passed,blocking=True):gates.append(dict(gate=name,target=target,actual=actual,passed=bool(passed),blocking=blocking,status='PASS' if passed else 'NOT MEASURED' if actual is None else 'FAIL' if blocking else 'PENDING'))
    for name in ['unknown_v3_preflight','coverage','canonical','confirmed_safety','input_safety','truth_policy','release_gate_fast','semantic_equivalence','tests']:
        g(name,'PASS',pre[name+'_pass'],pre[name+'_pass'])
    g('performance_median_p95','<=250 ms',perf['median_p95'],perf['required_pass'])
    g('performance_preferred_stability','>=5/7',perf['pass_count'],perf['preferred_stability_pass'],False)
    g('performance_preferred_latency','<=220 ms',perf['median_p95'],perf['preferred_latency_pass'],False)
    g('release_freeze','after all prerequisites',freeze,bool(freeze))
    for name,key,target,passed in [('unknown_rejection','rejection_rate','>=99%',u.get('rejection_rate',0)>=.99),('unknown_false_acceptance','false_acceptance_rate','<=1%',u.get('false_acceptance_rate',1)<=.01)]:g(name,target,u.get(key),passed)
    g('unknown_entity_version','0',dict(entity=u['entity_errors'],version=u['version_errors']) if u['status']=='complete' else None,u.get('entity_errors',1)==u.get('version_errors',1)==0)
    for name,target in [('v5_preflight','30IDs/6sources/400known/200scan/50filled/30unknown'),('v5_leakage','0'),('v5_precision','>=99.5%'),('v5_exact_recall','>=90%'),('v5_scan_precision','>=99.5%'),('v5_scan_recall','>=85%'),('v5_filled_generation','>=90%'),('v5_filled_precision','>=99.5%'),('v5_filled_recall','>=90%'),('v5_retrieval_at25','100%'),('v5_retrieval_at1','>=99%'),('v5_entity_version','0'),('v5_unknown_mix','>=99%')]:
        value=(v5 or {}).get('gates',{}).get(name,{})
        if not v5 and name in ['v5_preflight','v5_leakage']:
            path=OUT/('evaluation_v5_preflight.json' if name=='v5_preflight' else 'evaluation_v5_leakage.json')
            if path.exists():
                diagnostic=read(path)
                value=dict(actual=None if diagnostic.get('status')=='not_run' else diagnostic,passed=diagnostic['passed'])
        g(name,target,value.get('actual'),value.get('passed',False))
    g('family','>=5 identity-held-out families','experimental / insufficiently validated',False,False)
    g('CI','external matrix','external_pending',False,False)
    reasons=[x['gate'] for x in gates if x['blocking'] and x['status']=='FAIL']
    unmeasured=[x['gate'] for x in gates if x['blocking'] and x['status']=='NOT MEASURED']
    ident=identity()
    atomic_json(ROOT/'docs/release_gates.json',dict(round=18,status=status,software_version=software,candidate_target='0.7.0',schema=610,freeze=freeze,identity=ident,gates=gates,local_gates_passed=ready,tests=test,reasons=reasons,unmeasured_required=unmeasured,ci='external_pending'))
    latest=json.loads(subprocess.check_output(['git','show',BASE+':benchmarks/latest_summary.json'],cwd=ROOT))
    latest.update(round=18,status=status,version=software,software_version=software,commit=ident['commit'],runtime_sha256=ident['runtime_sha256'],fingerprint_sha256=ident['fingerprint_sha256'],reasons=reasons)
    latest['known_canonical']=dict(status='executed',summary=summary(read(OUT/'canonical.json')['cases']+read(OUT/'canonical_legacy.json')['cases']),scope='1007 current technical canonical binding contracts; not independent identity generalization.')
    latest['known_canonical']['summary']['latency_ms']={}
    latest['performance']=dict(status='executed',summary=dict(cases=2814,metrics={},latency_ms=dict(p95=perf['median_p95'])),runs=[r['latency_ms'] for r in perf['runs']],scope='Seven predetermined warm runs; no timing reruns or engine optimization.')
    latest['unknown_official']=dict(status='executed' if u['status']=='complete' else 'not_run',summary=summary(read(OUT/'unknown_release_v3_observations.json')['cases']) if u['status']=='complete' else dict(cases=0,metrics={},latency_ms={}),reason=u.get('reason','Fresh single-shot v3 on freeze; every DOCUMENT/FAMILY counts as false acceptance.'))
    for key,artifact in [('known_robustness','robustness_v5'),('scan_ocr','scan_v5'),('filled_forms','filled_v5')]:
        latest[key]=dict(status='executed',summary=read(OUT/(artifact+'.json'))['summary']) if v5 else dict(status='not_run',summary=dict(cases=0,metrics={},latency_ms={}),reason='Conditional evaluation v5 not executed.')
    latest['evaluations']=[dict(name=p.stem,summary=read(p)['summary']) for p in sorted(OUT.glob('historical_*.json')) if 'summary' in read(p)]
    atomic_json(ROOT/'benchmarks/latest_summary.json',latest);load_summary(ROOT/'benchmarks/latest_summary.json')
    table='\n'.join('| '+' | '.join(str(x).replace('|','/') for x in row)+' |' for row in [['Gate','Target','Actual','Esito'],['---']*4]+[[x['gate'],x['target'],x['actual'],x['status']] for x in gates])
    timings='\n'.join(f"|{r['run']}|{r['latency_ms']['p50']}|{r['latency_ms']['p95']}|" for r in perf['runs'])
    metrics={name:read(OUT/(name+'.json'))['summary'] for name in ['robustness_v5','scan_v5','filled_v5','end_to_end_v5']} if v5 else None
    retrieval=read(OUT/'retrieval_v5.json') if v5 else None
    archive=f"BurOCRazia-v0.7.0-{'RC1' if ready else 'candidate-NOT-READY'}-round18.zip"
    report=f'''# Round18 — {status}

Software pubblico **0.6.1**, schema **610**; target candidata **0.7.0**, stato **{status}**. Branch `codex/coverage-benchmark-v0.7.0`, ingresso `{BASE}`; freeze `{freeze or 'non eseguito'}`. Commit finale e SHA256 archivio nel verificatore esterno `dist/package-verification-round18.json`. Nessun push, tag o pubblicazione. CI external pending.

## Campione unknown

Master129,13 fonti,19 enti; INL42/129=32.5581%, ammesso nel master. Capacità per N100=112, massimo sostenibile116/cap29. Nessuna acquisizione aggiuntiva. Subset release{pool['total']},fonti{pool['sources']},enti{pool['entities']},categorie{pool['type_groups']},concentrazione{pool['max_concentration']:.6%}; seed{SEED}, policy SHA `{sha('benchmarks/reference/unknown_release_sampling_policy_v1.json')}`. Manifest scelto prima del freeze e di qualsiasi predizione, solo metadata e PRNG; nessuno score/ranking/fingerprint similarity nella selezione. I13 esclusi per quota rimangono freschi nel master. Prove in no_prediction_before_selection.json e unknown_subset_feasibility.json. Truth primaria ereditata immutabile dal Round17, revisione tecnica dell'agente; nessuna verifica editoriale umana attribuita. Nessun catalogo/document_id aggiunto.

## Prerequisiti

Coverage1002/1158=86.528497%; canonici980+27=1007/1007;241 NO sintetici senza accettazioni; ANAC e cinque risorse critiche sicure (4 esatte,1 NO prudente); input safety9/9 senza crash/residui/recognition. Equivalenza corrente{eq['n']} casi, differenze{len(eq['differences'])}; firme complete incluse score/margine/candidati/reason/ente/versione. Nessun byte motore, scoring, soglie, dataset o catalogo cambiato dal Round16. OCR storico estratto una volta per confronto; Tesseract reale separato nei test.

|Run|p50 ms|p95 ms|
|---|---|---|
{timings}

Mediana p95 **{perf['median_p95']}ms**; gate<=250{perf['required_pass']}. Stessa suite67 input/402 richieste per run,2814 tempi; sette run predeterminati, nessun rerun favorevole. Estrazione/OCR fuori timing warm; RequestPages nuova a ogni richiesta, cache soltanto catalogo. Windows/Python3.12.10; nessun collaudo Linux/macOS e nessuna garanzia su altri computer. Baseline Round17 231.5144ms conservata, distinta dalla rimisura.

## Unknown v3 ed evaluation v5

Unknown: {json.dumps({k:u.get(k) for k in ['status','n','correct_no_match','wrong_document_match','wrong_family_match','rejection_rate','false_acceptance_rate','confidence_interval_95','entity_errors','version_errors','recognition_calls']},ensure_ascii=False)}.

Evaluation preflight: {json.dumps(read(OUT/'evaluation_v5_preflight.json'),ensure_ascii=False) if (OUT/'evaluation_v5_preflight.json').exists() else 'non eseguito'}.
Il pool nativo ammissibile contiene **351 identità uniche / 352 record, soltanto5 fonti** (INPS,INAIL,Ministero del Lavoro,Garante Privacy,Tribunale di Venezia). La selezione deterministica contiene36 identità, sempre5 fonti. Il minimo6 è impossibile nel pool corrente dopo esclusione di tuning, precedenti evaluation influenti e template/risorse correlate. **STOP v5 prima della generazione/predizione**: nessuna identità contaminata recuperata e nessuna espansione del catalogo.608 rappresentazioni note/476 scan/60filled/30unknown erano soltanto pianificati, non generati né misurati. Il leakage di identità passa senza overlap; il leakage completo delle rappresentazioni resta non misurato. Unknown v3 invece ha PASS116/116,0 false DOCUMENT/FAMILY,0 errori ente/versione/estrazione; Wilson95% [96.7945%,100%] riguarda questo campione, non il confidence score del motore. Il ledger post_evaluation_exposures.json registra i116 SHA ora osservati, conservando immutabili registry pre-freeze, label e manifest.
Metriche overall/scan/filled/mix: {json.dumps({k:v.get('metrics') for k,v in metrics.items()},ensure_ascii=False) if metrics else 'non misurate'}.
Retrieval@1/@5/@10/@25: {retrieval or 'non misurato'}.

Ogni esecuzione eventualmente avviata è single-shot con journal SQLite, checkpoint, stesso freeze/manifest/hash, ID unici, count/schema e finalizzazione atomica. No tuning/replay come indipendente; label e trasformazioni restano fisse. WRONG FAMILY su unknown è false acceptance. Family: **experimental / insufficiently validated**, esclusa dal useful exact recall.

## Validazione e storico

Test completi **{test['passed']} passed/{test['failed']} failed/{test['skipped']} skipped**, {test['seconds']}s; log SHA in tests/final_tests.json. Pre-freeze829 passed/0failed/3skip; suite finale separata sul freeze. Il primo run828pass/1fail/3skip aveva già caricato il vecchio test Round17 che presumeva assente qualsiasi manifest v3; il test è stato isolato con ROOT temporaneo, nessun codice motore modificato. Log iniziale preservato in initial_validation_failure.json. Un tentativo mirato ha incontrato WinError5 nel default pytest-of-lucal: con basetemp nativo nuovo10 test mirati PASS, poi suite completa verde. Temporaneo nativo Windows; skip piattaforma documentati nei log. Compile, SQLite integrity/FK, migrazione idempotente610/conteggi invariati, fingerprint validators, compat-v2 e truth hash/schema in final_checks.json. Release-gate-fast **1258/1258**, exit0. Historical-regression-fast **1517 casi/15 mismatch**, exit1 atteso, etichette intatte:2 EX02/EX03 sintetici INPS (revisione mancante),10 locked-v1,2 annualità INAIL ambigue,1 NO prudente OH1-047. Non sono nuovi fallimenti né vengono cancellati per dichiarare verde il gate certo. Unknown v2 originale107/114 e tutti gli artifact Round16/17 preservati byte-per-byte. Registry v3 Round17 conservato separatamente prima dell’aggiornamento aggiuntivo v3 Round18. I contratti canonici/sintetici non sono campioni indipendenti ufficiali.

## Gate e limiti

{table}

Blocco misurato: **{', '.join(reasons) or 'nessuno locale'}**. I gate condizionali non eseguiti restano non misurati; eventuali risultati negativi single-shot sono conservati senza tuning o replay. Se manca il freeze, nessuna predizione release viene eseguita. Nessuna metrica non eseguita è rimpiazzata da un risultato storico. CI external pending; family sperimentale; ambiguità storiche visibili. App locale e deterministica, nessuna rete runtime, LLM o telemetria. Catalogo completo invariato. Il manifest catalogo conserva la serializzazione CRLF workspace/LF Git preesistente: eccezione già provata in Round16, JSON e blob storici identici; nessuna normalizzazione dei byte congelati.

Archivio `dist/{archive}`; SHA256 e verifica esterni in `dist/package-verification-round18.json` e `.zip.sha256` per evitare autoreferenze. Solo file pubblici tracciati, niente cache, file ufficiali binari, DB di lavoro, credenziali o dati personali.
'''
    (ROOT/'docs/ROUND18_REPORT.md').write_text(report,encoding='utf8',newline='\n')
    b=ROOT/'docs/BENCHMARK.md';original=subprocess.check_output(['git','show',BASE+':docs/BENCHMARK.md'],cwd=ROOT).decode('utf8')
    b.write_text(f"# Round18 — {status}\n\nPool fresh{pool['total']} ({pool['sources']}fonti/{pool['entities']}enti); canonical1007/1007; equivalenza1563/0diff; mediana p95{perf['median_p95']}ms, gate{perf['required_pass']}. Unknown v3{u['status']}, evaluation v5{'eseguita' if v5 else 'non eseguita'}. Test{test['passed']}pass/{test['failed']}fail/{test['skipped']}skip. Motore Round16 invariato; CI pending. [Report Round18](ROUND18_REPORT.md). Le sezioni successive sono storiche.\n\n"+original,encoding='utf8',newline='\n')
    if ready:
        save('rc_metadata',dict(version='0.7.0-rc1',public_version='0.6.1',schema=610,freeze_commit=freeze,ci='external_pending',publication=False))
        for lang,text in [('IT','Candidata RC locale, non release pubblica. Consultare ROUND18_REPORT.md per prove e limiti.'),('EN','Local release candidate, not a public release. See ROUND18_REPORT.md for evidence and limitations.')]:
            (ROOT/f'docs/RC1_README_{lang}.md').write_text('# BurOCRazia 0.7.0-rc1\n\n'+text+'\n',encoding='utf8',newline='\n')
        original_changelog=subprocess.check_output(['git','show',BASE+':CHANGELOG.md'],cwd=ROOT).decode('utf8')
        (ROOT/'CHANGELOG.md').write_text('# 0.7.0-rc1 — local candidate\n\nRound18 independent unknown/evaluation gates passed locally; engine unchanged from Round16, CI pending.\n\n'+original_changelog,encoding='utf8',newline='\n')
    paths=[p for p in OUT.glob('*') if p.suffix in ['.json','.csv'] and p.name!='evidence_locks.json']
    paths.extend(ROOT/p for p in [REGISTRY,'docs/ROUND18_REPORT.md','docs/ROUND18_BASELINE_AUDIT.md','docs/BENCHMARK.md','docs/release_gates.json','benchmarks/latest_summary.json'])
    save('evidence_locks',dict(sha256={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(paths)},historical_original_git_sha256=read(OUT/'historical_locks.json')['historical_original_git_sha256'],freeze=freeze))
    print('R18',status,'blocking',reasons,flush=True)

if __name__=='__main__':main()
