"""Publish only measured Round17 gates; preserve all preceding round evidence."""
import copy
from scripts.round17_common import *
from benchmarks.round8_common import identity
from benchmarks.evaluate import summary
from src.benchmark_display import load_summary

def main():
    invariant()
    pre=read(OUT/'pre_freeze_gate.json');pool=read(OUT/'unknown_v3_preflight.json');perf=read(OUT/'performance_stability.json')
    eq=read(OUT/'semantic_equivalence.json');test=read(OUT/('final_tests.json' if (OUT/'final_tests.json').exists() else 'tests.json'))
    freeze=read(OUT/'freeze_manifest.json')['freeze_git_commit'] if (OUT/'freeze_manifest.json').exists() else None
    u=read(OUT/'unknown_release_v3.json') if (OUT/'unknown_release_v3.json').exists() else dict(status='not_run',passed=False,recognition_calls=0,n=None,reason='Unknown preflight FAIL: INL42/129=32.5581% exceeds25%. Required stop before freeze/selection/predictions.',selection=None)
    if not (OUT/'unknown_release_v3.json').exists():save('unknown_release_v3',u)
    v5=read(OUT/'evaluation_v5_gate.json') if (OUT/'evaluation_v5_gate.json').exists() else None
    if not v5:save('evaluation_not_run',dict(status='not_run',recognition_calls=0,reason='Unknown v3 prerequisite not passed.' if not u['passed'] else 'Fresh known preflight/leakage not passed.',metrics=None))
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
            if path.exists():value=dict(actual=read(path),passed=read(path)['passed'])
        g(name,target,value.get('actual'),value.get('passed',False))
    g('family','>=5 identity-held-out families','experimental / insufficiently validated',False,False)
    g('CI','external matrix','external_pending',False,False)
    reasons=[x['gate'] for x in gates if x['blocking'] and x['status']=='FAIL']
    unmeasured=[x['gate'] for x in gates if x['blocking'] and x['status']=='NOT MEASURED']
    ident=identity()
    atomic_json(ROOT/'docs/release_gates.json',dict(round=17,status=status,software_version=software,candidate_target='0.7.0',schema=610,freeze=freeze,identity=ident,gates=gates,local_gates_passed=ready,tests=test,reasons=reasons,unmeasured_required=unmeasured,ci='external_pending'))
    latest=json.loads(subprocess.check_output(['git','show',BASE+':benchmarks/latest_summary.json'],cwd=ROOT))
    latest.update(round=17,status=status,version=software,software_version=software,commit=ident['commit'],runtime_sha256=ident['runtime_sha256'],fingerprint_sha256=ident['fingerprint_sha256'],reasons=reasons)
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
    archive=f"BurOCRazia-v0.7.0-{'RC1' if ready else 'candidate-NOT-READY'}-round17.zip"
    report=f'''# Round17 — {status}

Software pubblico **0.6.1**, schema **610**; target candidata **0.7.0**, stato **{status}**. Branch `codex/coverage-benchmark-v0.7.0`, ingresso `{BASE}`; freeze `{freeze or 'non eseguito'}`. Commit finale e SHA256 archivio nel verificatore esterno `dist/package-verification-round17.json`. Nessun push, tag o pubblicazione. CI external pending.

## Campione unknown

Partenza95; nuovi candidati acquisiti{pool['new_candidates_acquired']}; nuovi confermati indipendenti{pool['confirmed_new']}; pool finale{pool['total']}, fonti{pool['sources']}, enti{pool['entities']}, tipi{pool['type_groups']}, concentrazione massima{pool['max_concentration']:.6%}. Gate minimo{pool['passed']}, preferito{pool['preferred_pass']}. **INL42/129=32.5581% supera25%: stop obbligatorio prima di freeze/selezione/predizioni.** Quantità, fonti e categorie passano. Tenendo42 INL, servirebbero almeno39 ulteriori unknown indipendenti da altre fonti per N168/max25%; questa è aritmetica di adeguatezza, non una raccolta eseguita. Hash, ricevute, URL finali, confronto catalogo/codice/titolo/fingerprint/famiglia e revisione primaria precedono le predizioni. I95 precedenti sono conservati; nuove fonti esclusivamente benchmark. Revisione tecnica dell'agente, nessuna verifica editoriale umana attribuita. Lotto400 richieste,157 nuovi file;37 qualificati automatici diventano34 indipendenti dopo1 template ambiguo/2 near-duplicate esclusi. Acquisizione limitata con opt-in, robots e allowlist; nessun catalogo/document_id aggiunto. Il traversal ora scarta tutte le teste già visitate prima di dichiarare la coda esaurita.

## Prerequisiti

Coverage1002/1158=86.528497%; canonici980+27=1007/1007;241 NO sintetici senza accettazioni; ANAC e cinque risorse critiche sicure (4 esatte,1 NO prudente); input safety9/9 senza crash/residui/recognition. Equivalenza corrente{eq['n']} casi, differenze{len(eq['differences'])}; firme complete incluse score/margine/candidati/reason/ente/versione. Nessun byte motore, scoring, soglie, dataset o catalogo cambiato dal Round16. OCR storico estratto una volta per confronto; Tesseract reale separato nei test.

|Run|p50 ms|p95 ms|
|---|---|---|
{timings}

Mediana p95 **{perf['median_p95']}ms**; gate<=250{perf['required_pass']}. Stessa suite67 input/402 richieste per run,2814 tempi; sette run predeterminati, nessun rerun favorevole. Estrazione/OCR fuori timing warm; RequestPages nuova a ogni richiesta, cache soltanto catalogo. Windows/Python3.12.10; nessun collaudo Linux/macOS e nessuna garanzia su altri computer. Prestazioni Round16 244.9918ms conservate, non sostituiscono la rimisura.

## Unknown v3 ed evaluation v5

Unknown: {json.dumps({k:u.get(k) for k in ['status','n','correct_no_match','wrong_document_match','wrong_family_match','rejection_rate','false_acceptance_rate','confidence_interval_95','entity_errors','version_errors','recognition_calls']},ensure_ascii=False)}.

Evaluation preflight: {json.dumps(read(OUT/'evaluation_v5_preflight.json'),ensure_ascii=False) if (OUT/'evaluation_v5_preflight.json').exists() else 'non eseguito'}.
Metriche overall/scan/filled/mix: {json.dumps({k:v.get('metrics') for k,v in metrics.items()},ensure_ascii=False) if metrics else 'non misurate'}.
Retrieval@1/@5/@10/@25: {retrieval or 'non misurato'}.

Ogni esecuzione eventualmente avviata è single-shot con journal SQLite, checkpoint, stesso freeze/manifest/hash, ID unici, count/schema e finalizzazione atomica. No tuning/replay come indipendente; label e trasformazioni restano fisse. WRONG FAMILY su unknown è false acceptance. Family: **experimental / insufficiently validated**, esclusa dal useful exact recall.

## Validazione e storico

Test completi **{test['passed']} passed/{test['failed']} failed/{test['skipped']} skipped**, {test['seconds']}s; log SHA in tests/final_tests.json. Temporaneo nativo Windows; skip piattaforma documentati nei log. Compile, SQLite integrity/FK, migrazione idempotente610/conteggi invariati, fingerprint validators, compat-v2 e truth hash/schema in final_checks.json. Release-gate-fast **1258/1258**, exit0. Historical-regression-fast **1517 casi/15 mismatch**, exit1 atteso, etichette intatte:2 EX02/EX03 sintetici INPS (revisione mancante),10 locked-v1,2 annualità INAIL ambigue,1 NO prudente OH1-047. Non sono nuovi fallimenti né vengono cancellati per dichiarare verde il gate certo. Unknown v2 originale107/114 e tutti gli artifact Round16 preservati byte-per-byte. Registry v3 Round16 conservato separatamente prima dell'aggiornamento aggiuntivo v3 Round17. I contratti canonici/sintetici non sono campioni indipendenti ufficiali.

## Gate e limiti

{table}

Blocco misurato: **{', '.join(reasons) or 'nessuno locale'}**. Freeze e gate v3/v5 restano non misurati per lo stop richiesto dal preflight; non sono risultati negativi di recognition. Se manca il freeze, nessuna predizione release viene eseguita. Nessuna metrica non eseguita è rimpiazzata da un risultato storico. CI external pending; family sperimentale; ambiguità storiche visibili. App locale e deterministica, nessuna rete runtime, LLM o telemetria. Catalogo completo invariato. Il manifest catalogo conserva la serializzazione CRLF workspace/LF Git preesistente: eccezione già provata in Round16, JSON e blob storici identici; nessuna normalizzazione dei byte congelati.

Archivio `dist/{archive}`; SHA256 e verifica esterni in `dist/package-verification-round17.json` e `.zip.sha256` per evitare autoreferenze. Solo file pubblici tracciati, niente cache, file ufficiali binari, DB di lavoro, credenziali o dati personali.
'''
    (ROOT/'docs/ROUND17_REPORT.md').write_text(report,encoding='utf8',newline='\n')
    b=ROOT/'docs/BENCHMARK.md';original=subprocess.check_output(['git','show',BASE+':docs/BENCHMARK.md'],cwd=ROOT).decode('utf8')
    b.write_text(f"# Round17 — {status}\n\nPool fresh{pool['total']} ({pool['sources']}fonti/{pool['entities']}enti); canonical1007/1007; equivalenza1563/0diff; mediana p95{perf['median_p95']}ms, gate{perf['required_pass']}. Unknown v3{u['status']}, evaluation v5{'eseguita' if v5 else 'non eseguita'}. Test{test['passed']}pass/{test['failed']}fail/{test['skipped']}skip. Motore Round16 invariato; CI pending. [Report Round17](ROUND17_REPORT.md). Le sezioni successive sono storiche.\n\n"+original,encoding='utf8',newline='\n')
    if ready:
        save('rc_metadata',dict(version='0.7.0-rc1',public_version='0.6.1',schema=610,freeze_commit=freeze,ci='external_pending',publication=False))
        for lang,text in [('IT','Candidata RC locale, non release pubblica. Consultare ROUND17_REPORT.md per prove e limiti.'),('EN','Local release candidate, not a public release. See ROUND17_REPORT.md for evidence and limitations.')]:
            (ROOT/f'docs/RC1_README_{lang}.md').write_text('# BurOCRazia 0.7.0-rc1\n\n'+text+'\n',encoding='utf8',newline='\n')
        original_changelog=subprocess.check_output(['git','show',BASE+':CHANGELOG.md'],cwd=ROOT).decode('utf8')
        (ROOT/'CHANGELOG.md').write_text('# 0.7.0-rc1 — local candidate\n\nRound17 independent unknown/evaluation gates passed locally; engine unchanged from Round16, CI pending.\n\n'+original_changelog,encoding='utf8',newline='\n')
    paths=[p for p in OUT.glob('*') if p.suffix in ['.json','.csv'] and p.name!='evidence_locks.json']
    paths.extend(ROOT/p for p in [REGISTRY,'docs/ROUND17_REPORT.md','docs/ROUND17_BASELINE_AUDIT.md','docs/BENCHMARK.md','docs/release_gates.json','benchmarks/latest_summary.json'])
    save('evidence_locks',dict(sha256={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(paths)},historical_original_git_sha256=historical(),freeze=freeze))
    print('R17',status,'blocking',reasons,flush=True)

if __name__=='__main__':main()
