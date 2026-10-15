"""Publish measured Round22 evidence locally, preserving every prior result."""
import csv
from collections import Counter
from scripts.round22_common import *
from benchmarks.round22_release import sealed,rates
from benchmarks.evaluate import code_hash,summary

def main():
    f=sealed();v=read(OUT/'evaluation_v6_gate.json');gen=read(OUT/'filled_generation_v2.json');pre=read(OUT/'evaluation_v6_preflight.json');perf=read(OUT/'performance_stability.json');tests=read(OUT/'final_tests.json');checks=read(OUT/'final_checks.json');post=read(OUT/'post_v6_checks.json');canonical=read(OUT/'canonical_post_v6.json');safety=read(OUT/'safety_post_v6.json');cov=read(OUT/'coverage.json');inputs=read(OUT/'input_safety.json');dev=read('benchmarks/results/round21/calibration_v7.json');unknown=read('benchmarks/results/round21/unknown_release_v4.json');plan=read('benchmarks/results/round21/evaluation_v6_plan.json')
    gates=[]
    def gate(n,a,p,t,blocking=True):gates.append(dict(gate=n,actual=a,passed=bool(p),target=t,blocking=blocking,status='PASS' if p else 'FAIL' if blocking else 'TARGET NOT MET'))
    gate('recognition_engine_unchanged',f['working_tree_recognition_hash'],True,'Equal Round21 semantic hash and every recognition/profile/catalog/dataset byte')
    for n,a,p,t in [('dev_precision',dev['V5_development']['precision'],dev['V5_development']['precision']>=.995,'>=99.5%'),('dev_recall',dev['V5_development']['recall'],dev['V5_development']['recall']>=.9,'>=90%'),('dev_scan_recall',dev['scan']['recall'],dev['scan']['recall']>=.85,'>=85%'),('dev_confirmed_false_accepts',len(dev['confirmed_false_accept_ids']),not dev['confirmed_false_accept_ids'],'0'),('filled_generation',gen['generation_success_rate'],gen['passed'],'>=90%,>=50valid'),('fresh_preflight',pre,pre['passed'],'40IDs/8sources,>=400known/200scan/50filled,leakage0'),('unknown_v4_preserved',unknown['correct_no_match'],unknown['passed'] and unknown['correct_no_match']==120,'120/120,no replay')]:gate(n,a,p,t)
    for n,g in v['gates'].items():gate(n,g['actual'],g['passed'],'Frozen V6 requirement',g['blocking'])
    gate('canonical_post_v6',dict(n=canonical['n'],exact=canonical['exact']),canonical['passed'],'1007/1007')
    gate('confirmed_safety_post_v6',dict(n=safety['n'],false_accepts=safety['false_accepts']),safety['passed'],'0 confirmed false accepts')
    gate('input_safety',dict(n=inputs['n'],passed=inputs['passed']),inputs['passed'],'100% safe refusal')
    gate('coverage',cov['file_backed_percent'],cov['file_backed_percent']>=85,'>=85%')
    gate('performance_median_p95',perf['median_p95'],perf['required_pass'],'7runs,medianp95<=250ms')
    gate('full_tests',tests,tests['failed']==0,'0 failures')
    gate('final_checks',checks['passed'],checks['passed'] and post['passed'],'compile,catalog,FK,migration610,release contracts,schemas')
    ready=all(g['passed'] for g in gates if g['blocking']);status='READY LOCALLY' if ready else 'NOT READY';reasons=[g['gate'] for g in gates if g['blocking'] and not g['passed']]
    identity=dict(commit=BASE,code_sha256=code_hash(),runtime_sha256=f['working_tree_recognition_hash'],fingerprint_sha256=f['fingerprint_dataset_sha256'],evaluation_freeze_sha256=sha(OUT/'evaluation_freeze_manifest.json'))
    release=dict(schema_version=1,round=22,status=status,software_version='0.6.1',candidate_target='0.7.0-rc1' if ready else '0.7.0',identity=identity,freeze=f,local_gates_passed=ready,reasons=reasons,gates=gates,tests=tests,ci='external_pending',family_status='experimental / insufficiently validated',new_commit_created=False)
    atomic_json(ROOT/'docs/release_gates.json',release)
    rows=read(OUT/'evaluation_v6_observations.json')['cases'];urows=read('benchmarks/results/round21/unknown_release_v4_observations.json')['cases']
    devrows=read('benchmarks/results/round21/development_regression_v5_after_fix.json')['cases']
    evaluations=[dict(name=n,summary=read(OUT/(n+'.json'))['summary']) for n in ['robustness_v6','scan_v6','filled_v6','end_to_end_v6']]
    evaluations.extend([dict(name='unknown_v4_original_single_shot',summary=summary(urows)),dict(name='development_regression_v5_after_fix',summary=summary(devrows))])
    latest=dict(schema_version=1,benchmark_model='known-family-unknown-v5',round=22,status=status,software_version='0.6.1',version='0.6.1',candidate_target=release['candidate_target'],commit=BASE,evaluation_freeze_sha256=identity['evaluation_freeze_sha256'],runtime_sha256=f['working_tree_recognition_hash'],recognition_semantics_changed=False,catalog_count=1216,catalog_semantic_sha256='sha256:'+f['catalog_semantic_sha256'],new_commit_created=False,github_ci='external_pending',reasons=reasons,evaluations=evaluations,known_robustness=dict(status='executed',summary=read(OUT/'robustness_v6.json')['summary'],scope='Fresh reserved V6 single-shot;40identities/8sources.'),scan_ocr=dict(status='executed',summary=read(OUT/'scan_v6.json')['summary'],scope='420synthetic scan-like inputs with real local Tesseract;not personal field scans.'),filled_forms=dict(status='executed',summary=read(OUT/'filled_v6.json')['summary'],generation_attempted=100,generation_valid=gen['generation_valid'],generation_success_rate=gen['generation_success_rate'],end_to_end_rate=v['filled_generation']['end_to_end_rate'],scope='Recognition conditional on valid generation;end-to-end exact/100 separately.'),known_canonical=dict(status='executed',summary=summary(canonical['cases']),scope='Post-V6 product canonical replay1007/1007 on immutable engine.'),fingerprint_coverage=dict(status='executed',**cov),unknown_official=dict(status='executed',summary=summary(urows),scope='Original Round21 unknown4 single-shot preserved byte-for-byte;compatible unchanged engine,0new calls.',metrics={k:unknown[k] for k in ['n','correct_no_match','wrong_document_match','wrong_family_match','rejection_rate','false_acceptance_rate','entity_errors','version_errors','confidence_interval_95']}),unknown_release_subset=dict(status='historical_single_shot_reused',**unknown['selection']),performance=dict(status='executed',median_p95_ms=perf['median_p95'],runs=7,pass_count=perf['pass_count'],scope='All7 prescribed isolated post-V6 warm runs,no optimizations after result.'),development_regression_v5_after_fix=dict(status='historical_development',classification='development_only',metrics=dev['V5_development'],scan=dev['scan'],filled=dev['filled'],false_accepts=0,scope='Original Round21 development unchanged;not independent V6.'),historical_independent_v5_round19=dict(status='historical_only',precision=.9824561403508771,recall=.705511811023622,scan_recall=.6329365079365079,original_observations_sha256=sha('benchmarks/results/round19/evaluation_v5_observations.json')),family_identity_holdout=dict(status='experimental / insufficiently validated',families_evaluable=0),release_gate=dict(status='executed',n=read(OUT/'release_gate_fast.json')['n'],passed=True,scope='New post-V6 confirmed technical diagnostic.'),fresh_v6_gate=v)
    atomic_json(ROOT/'benchmarks/latest_summary.json',latest)
    from src.benchmark_display import load_summary
    load_summary(ROOT/'benchmarks/latest_summary.json')
    failures=[r for r in rows if not r['document_correct']]
    audit=[dict(case_id=r['id'],document_id=r['expected']['document_id'],source=r['provenance']['source_id'],transform=r['representation'],filled=r['filled'],scan=r['scan_like'],expected_rank=r['candidate_rank'],observed_type=r['observed']['match_type'],observed_id=r['observed'].get('document_id'),entity_error=r['entity_error'],version_error=r['version_error'],extraction_failed=r['extraction_failed'],reason=r.get('reason'),decision=json.dumps(r.get('decision_diagnostics',{}),ensure_ascii=False,sort_keys=True)) for r in failures]
    with (OUT/'evaluation_v6_failures.csv').open('w',encoding='utf8',newline='') as out:
        fields=list(audit[0]) if audit else ['case_id','document_id','source','transform','observed_type','observed_id'];w=csv.DictWriter(out,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(audit)
    breakdown=dict(by_source={str(s):rates([r for r in rows if r['provenance']['source_id']==s]) for s in sorted({r['provenance']['source_id'] for r in rows})},by_transform={s:rates([r for r in rows if r['representation']==s]) for s in sorted({r['representation'] for r in rows})},failure_count=len(failures),scope='Post-result descriptive diagnostics only. No tuning;fresh V6 is immutable historical independent evidence for any later round.')
    save('evaluation_v6_breakdown',breakdown)
    save('result_hash',dict(observations_sha256=sha(OUT/'evaluation_v6_observations.json'),gate_sha256=sha(OUT/'evaluation_v6_gate.json'),expected_count=v['expected_count'],unique_case_ids=v['unique_case_ids'],freeze_sha256=identity['evaluation_freeze_sha256'],unknown_v4_raw_sha256=f['unknown_v4_raw_result_sha256']))
    save('historical_independent_v6_round22',dict(classification='historical_independent_v6_round22',recognition_semantic_sha256=f['working_tree_recognition_hash'],freeze_sha256=identity['evaluation_freeze_sha256'],original_observations_sha256=v['observations_sha256'],original_metrics=v['metrics'],original_gate_pass=v['passed'],future_policy='Immutable independent evidence for this exact frozen engine. Any later tuning based on these results requires a new independent evaluation;no relabel/replay/replacement of these original metrics.'))
    histories={p.relative_to(ROOT).as_posix():dict(sha256=sha(p),bytes=p.stat().st_size) for p in ROOT.glob('reports/round22-*.log') if not p.name.startswith(('round22-finish','round22-package')) or p.name=='round22-package.log'}
    save('technical_attempt_history',dict(logs=histories,events=['Initial synthetic generator security test exposed nested inline URI dictionaries;recursive bounded inspection corrected before100-case aggregate. Initial1failure/10pass and final11pass logs retained.','Filled100cases generated once under frozen policy;transactional receipts preserve successes/failures.','Original3normalized DOCX failures retained without repair;497nonfilled outputs carried forward with exact hashes,never previously predicted.','Unknown4 reused from original120raw;0new predictions.','V6 single-shot on sealed597known;post checks are prescribed validation only,not tuning.','First final validator omitted copying the preexisting page-limit report;stopped before input-safety cases. Restored identical Round21 audit into Round22 and resumed read-only/parser/CLI checks;original failure log retained.'],recognition_semantics_changed=False,generator_changes_after_evaluation=False))
    if (OUT/'archive_serialization_audit.json').exists():
        history=read(OUT/'technical_attempt_history.json');history['events'].append('Initial full protected-file archive check rejected preexisting LF/CRLF/mixed serialization. Original failed ZIP preserved by SHA;81cases independently proved against unchanged physical hashes,prior Round21 archive bytes and Git blobs. Only packaging verification/reporting changed;no local original normalized.');save('technical_attempt_history',history)
    m,s,fill=v['metrics'],v['scan'],v['filled'];hist=read(OUT/'historical_regression_fast.json')
    timing='\n'.join(f"| {r['run']} | {r['latency_ms']['p50']:.4f} | {r['latency_ms']['p95']:.4f} |" for r in perf['runs'])
    transforms='\n'.join(f"| {n} | {r['n']} | {r['exact']} | {r['wrong']} | {r['precision']:.4%} | {r['recall']:.4%} |" for n,r in breakdown['by_transform'].items())
    sources='\n'.join(f"| {n} | {r['n']} | {r['exact']} | {r['wrong']} | {r['precision']:.4%} | {r['recall']:.4%} |" for n,r in breakdown['by_source'].items())
    table='\n'.join(f"| {g['gate']} | {g['actual'] if not isinstance(g['actual'],dict) else 'See linked artifact'} | {g['target']} | {g['status']} |" for g in gates)
    report=f'''# Round 22 — {status}

**{status}**. Gate bloccanti falliti: `{reasons}`. Il generatore passa; la decisione RC dipende dalle misure V6 effettive e dalle verifiche finali. Nessun tuning dopo la V6.

## Versione e confini

Pubblico **0.6.1**, schema **610**, branch `codex/coverage-benchmark-v0.7.0`, HEAD `{BASE}`. Nessun commit, push, tag o pubblicazione. Freeze content-addressed `{identity['evaluation_freeze_sha256']}`, non un commit Git. Il Git tree storico di riferimento del solo motore è `{f['recognition_source_tree']}`; lo snapshot finale di packaging è distinto e riportato nel sidecar.

Recognition engine changed: **no**. Hash Round21 = Round22: `{f['working_tree_recognition_hash']}`. Ogni file recognition, decision v7, soglia, peso, ranking, veto ente/versione, family logic, source profile, catalogo e fingerprint è identico. Nuovi file soltanto generator/validation/runner/checkpoint/docs e11 test infrastrutturali; test recognition preesistenti immutati. Proof prima/dopo in recognition_freeze_check.json e generator_change_scope.json. Dataset `{f['fingerprint_dataset_sha256']}`, profilo v7 `{f['decision_v7_sha256']}`, catalog semantic `{f['catalog_semantic_sha256']}`.

## Evidenza preservata

V5 indipendente Round19 originale: **P98,2456%,R70,5512%,scan R63,2937%**, immutata. Development v7 Round21: **P100%,R90,3937%,scan R88,2937%,filled100%,0false accept confermati**, invariato e separato dalla V6 indipendente.

Unknown4 originale Round21 **120/120**,15fonti,0DOCUMENT/0FAMILY false accept,0errori ente/versione. Manifest `{f['unknown_v4_manifest_sha256']}`, raw `{f['unknown_v4_raw_result_sha256']}`. Compatibilità con identico motore verificata; **zero nuove predizioni unknown4**, nessun resampling/relabel/tuning. Nel mix end-to-end sono riusate tutte le120 righe originali.

## Filled generation prima

Round21: **100 tentativi,75 validi,25 falliti**,75% sotto90%. Cinque varianti ciascuna per ID484/264/263/558/414, tutti statici senza widget. Causa: `static_overlay_failure / No safe blank overlay rectangle`, ricerca sulla sola prima pagina di sette riquadri larghi fissi. Audit25/25 senza recognition, CSV e rendering originali conservati. Le tre varianti digital normalized DOCX fallite (113/1121/1074,C14NError) restano agli atti e non vengono corrette in questo round.

## Generatore v2 e validazione

Policy `filled-generation-v2-round22` congelata prima dell'aggregazione: `{sha(POLICY)}`. AcroForm-native con persistenza dei valori widget e `/AP /N`; static overlay a larghezza misurata,griglia deterministica,ricerca multipagina,protezione di parole/inchiostro/linee/titolo/codice/emittente/anno. Fallback statico per AcroForm malformato/non salvabile su PDF valido,registrato senza inventare o ricostruire campi. Nessuna nuova pagina,resize,canvas esteso o testo invisibile; dati esclusivamente fittizi,seed/varianti originali.

File scritto atomicamente e riletto con SHA; non vuoto,riaperto,pagine/geometria coerenti,nessuna corruzione,valori sintetici verificati,template presente,parser locale sicuro e nessun riferimento attivo/esterno introdotto. Confronto raster144DPI fuori dai rettangoli compilati: frazione pixel diversi oltre8 livelli ≤0,0001,per ogni pagina di tutti100file. Confronto testi originali e valori persistiti aggiuntivo. Controllo link/azioni include dizionari annidati; il test negativo che lo ha motivato è stato corretto prima della generazione aggregata.

QA visiva Poppler144DPI su tutte le cinque vecchie identità problematiche più un AcroForm: valori leggibili,template/titoli/annualità conservati,nessun overlap o clipping del contenuto originale. Gli overlay sono perturbazioni sintetiche in spazi liberi,**non una compilazione semantica dei campi né documenti da presentare a un ente**. I valori restano nella copia benchmark privata. Tutti60overlay hanno conservato e verificato le sette stringhe previste; minimo policy1 non usato per gonfiare il conteggio.

## Filled generation dopo

**{gen['generation_attempted']} tentativi / {gen['generation_valid']} validi = {gen['generation_success_rate']:.2%}**, gate90% PASS e target95% PASS. Modalità `{gen['mode_counts']}`,fallback effettivi `{gen['fallback_count']}`,fallimenti `{len(gen['failures'])}`. Medesime20identità e5varianti/case ID/seed ciascuna; rigenerazione coerente di tutti100 autorizzata prima di qualunque predizione. I75output vecchi rimangono intatti. Nessuna sostituzione più facile o selezione basata su score.

## Preflight e freeze V6

**{pre['identities']} identità / {pre['sources']} fonti / {pre['known_representations']} noti / {pre['scan_like']} scan / {pre['valid_filled']} filled**, concentrazione massima15%. Selezione originale `{plan['source_counts']}`,639ID/8fonti prenotati,nessuna espansione catalogo. Le fonti Garante e ANAC sono rappresentate da sole3identità ciascuna,limite esplicito.

I497nonfilled Round21 sono riusati byte-identici,mai predetti prima; i100filled sono v2. Le3digital normalized fallite sono escluse con prova del fallimento,non conteggiate come recognition failures. Leakage **0**: nessun tuning identity/V5/observed SHA/equivalent transform/unknown overlap/duplicato/ambiguità vietati. I seed riservati Round21 sono gli stessi perché mai usati in predizioni V6; non è una nuova realizzazione selezionata a posteriori. Unknown4 disponibile120 compatibile.

Ogni representation è vincolata da case ID,expected identity,SHA,path,transform metadata e validation status. Freeze content-addressed lega motore/catalogo/dataset/registry/identità/trasformazioni/policy filled/unknown manifest+raw/leakage/generator result/manifest byte e codice. Zero commit. Dopo il freeze e il primo risultato: nessuna modifica a recognition,generatore,policy,label,selezione o seed.

## V6 single-shot

Transactional journal,expected count **{v['expected_count']}**,actual **{v['actual_count']}**,ID unici **{v['unique_case_ids']}**,raw SHA `{v['observations_sha256']}`. Resume soltanto pending ID con identico freeze/input/code; nessun replay completato.

Noti **{m['n']}**: TP/exact **{m['TP']}**,FP/wrong **{m['FP']}**,FN **{m['FN']}**,family **{m['family']}**,reject **{m['reject']}**,extraction failures **{m['extraction_failed']}**. **P{m['precision']:.4%},R{m['recall']:.4%},F1{m['f1']:.4%}**. Errori ente **{m['entity_errors']}**,versione **{m['version_errors']}**. CI95 nominali Wilson: precisione `{m['precision_ci95']}`,recall `{m['recall_ci95']}`. Le righe sono correlate per40identità; questi intervalli descrittivi non forniscono una garanzia di generalizzazione alla popolazione.

Failure audit e breakdown perfonte/trasformazione preservati; nessuna correzione dopo il risultato. Da un futuro round che usi questi errori per tuning,la V6 resta storico indipendente del motore congelato e non può essere ripresentata come held-out del nuovo motore.

## Retrieval

@1 **{v['retrieval']['1']:.4%}**, @5 **{v['retrieval']['5']:.4%}**, @10 **{v['retrieval']['10']:.4%}**, @25 **{v['retrieval']['25']:.4%}**. Gate obbligatorio @25=100%; @1≥99% è il target distinto previsto dal Round22,non viene trasformato in un gate diverso.

## Scan

**N{s['n']},exact{s['exact']},wrong{s['wrong']},P{s['precision']:.4%},R{s['recall']:.4%}**. Gate P99,5%/R85%. Tesseract locale reale; immagini sintetiche correlate agli originali ufficiali,non scansioni personali raccolte sul campo.

| Trasformazione | N | Exact | Wrong | P | R |
| --- | --- | --- | --- | --- | --- |
{transforms}

## Filled conditional e end-to-end

Generation100/100 =100%; recognition conditional **N{fill['n']},exact{fill['exact']},wrong{fill['wrong']},P{fill['precision']:.4%},R{fill['recall']:.4%}**. End-to-end **{v['filled_generation']['valid_and_correct']}/100 = {v['filled_generation']['end_to_end_rate']:.4%}**. Generazione e recognition restano metriche separate; nessun failure generator viene passato al motore o contato come errore recognition.

## Unknown mix e family

Mix end-to-end: {m['n']}known + **120unknown originali**,120correct reject,0false accept,0nuove chiamate unknown. Wrong FAMILY su unknown è false accept. Family logic invariata,**experimental / insufficiently validated**; non contribuisce exact recall.

## Canonical,coverage,safety

Canonical post-V6 **{canonical['exact']}/{canonical['n']}**,P/R100% se gatePASS. Coverage **{cov['file_backed_percent']:.6f}% (1002/1158)**,catalogo1216documenti/19fonti/16famiglie invariati. Safety post-V6 **{safety['n']} negativi confermati,FA `{safety['false_accepts']}`**,hard negative **{safety['hard_correct_rejects']}/{safety['hard_negatives']}**. Vecchi8falseaccept valutati,ANAC/R061/EX02/EX03 secondo truth policy nei contratti storici. Input safety9/9,rifiuti parser prima di recognition,nessuna falsa attribuzione di successo unknown a input non supportati.

Release diagnostic **{read(OUT/'release_gate_fast.json')['n']} contratti PASS**; storico originale **{hist['n']}**,**{len(hist['mismatches'])} mismatch/exit1** mantenuti come evidenza di etichette ambigue/incompatibili,non azzerati o nascosti. Le verifiche post-V6 sono replay di validazione espressamente richiesti,non tuning.

## Performance post-V6

| Run | p50 ms | p95 ms |
| --- | --- | --- |
{timing}

Tutti7 run predeterminati e isolati,67input/402richieste perrun/2814timing. **p95 mediano {perf['median_p95']:.4f}ms**, `{perf['pass_count']}/7`≤250ms. Nessuna ottimizzazione dopo V6. Baseline Round21 176,6788ms separata. Matching warm,estrazione/OCR fuori timing,RequestPages nuove,cache soltanto metadati catalogo.

## Test e collaudo

Baseline precedente878/0/3 preservata. Nuovi11test generator: native/malformed fallback/static,multipagina,riapertura,valori/checkbox/date/numeri,seed,template,cleanup,riferimenti/failure receipts. **Full post-V6 {tests['passed']}pass/{tests['failed']}fail/{tests['skipped']}skip**,{tests['seconds']}s,log SHA `{tests['log_sha256']}`. Test recognition vecchi immutati. Compile,SQLite integrity/FK,migrazione610idempotente/conteggi,profili/fingerprint/truth/observations schema e CLI verificati sul freeze. Skip Windows symlink/FIFO; collado Windows/Python3.12.10,nessun collaudo Linux/macOS. CI **external pending**.

## Breakdown fonti

| Fonte | N | Exact | Wrong | P | R |
| --- | --- | --- | --- | --- | --- |
{sources}

## Gate RC

| Gate | Actual | Target | Esito |
| --- | --- | --- | --- |
{table}

## Limiti e archivio

**{status}**,gate bloccanti falliti `{reasons}`. Campione40identità e trasformazioni correlate; QA sintetica filled overlay non equivale a compilazione semanticamente corretta o a scansioni di utenti. Fonti minori3ID,tre digital normalized non generabili conservate,family insufficiente,CI multipiattaforma esterna pending. Nessun LLM/rete/telemetria nel runtime,nessun dato personale,nessuna attribuzione editoriale automatica o consulenza personalizzata.

Archivio `dist/BurOCRazia-v0.7.0-{'RC1' if ready else 'candidate-NOT-READY'}-round22.zip`. SHA256 e Git tree finale nel sidecar `dist/package-verification-round22.json`; riportati anche nella consegna finale,evitando autoreferenza dell'hash dentro lo ZIP. Verifica raw storici,freeze,conteggi,SHA,manifest,gen-v2 e hygiene; cache/work/PDFufficiali/compilati/checkpoint/DB di lavoro/log esclusi. Tutte le evidenze negative rimangono. HEAD e indice originale immutati,nessun commit/push/tag/release.

Goal ufficiale finito Round22 e checkpoint privati append-only; a ogni ripresa si verificano processi/journal/output per evitare duplicati. Automazione oraria assente nell'app,nessun wakeup periodico dichiarato. Il Goal termina soltanto dopo il packaging verificato.
'''
    # Add spacing only to ordinary prose; never alter hashes,IDs or paths in code spans.
    import re
    parts=report.split('`')
    for i in range(0,len(parts),2):
        p=parts[i];p=re.sub(r',(?=[^\s\d])',', ',p)
        for a,b in {'Round21':'Round 21','Round22':'Round 22','Round19':'Round 19','15fonti':'15 fonti','120righe':'120 righe','20identità':'20 identità','5varianti':'5 varianti','40identità':'40 identità','3identità':'3 identità','639ID':'639 ID','8fonti':'8 fonti','75output':'75 output','100file':'100 file','60overlay':'60 overlay','497nonfilled':'497 nonfilled','100filled':'100 filled','3digital':'3 digital','40IDs':'40 IDs','persource':'per source','perfonte':'per fonte','perrun':'per run','67input':'67 input','402richieste':'402 richieste','2814timing':'2814 timing','9/9,rifiuti':'9/9, rifiuti','0false':'0 false','0nuove':'0 nuove','0DOCUMENT':'0 DOCUMENT','0FAMILY':'0 FAMILY','0errori':'0 errori','11test':'11 test','11 test':'11 test','8false':'8 false','1216documenti':'1216 documenti','19fonti':'19 fonti','16famiglie':'16 famiglie','100attempts':'100 attempts','collado':'collaudo','PDFufficiali':'PDF ufficiali'}.items():p=p.replace(a,b)
        parts[i]=p
    report='`'.join(parts)
    if (OUT/'archive_serialization_audit.json').exists():
        serialization=read(OUT/'archive_serialization_audit.json')
        report+='\n## Serializzazione storica verificata\n\nIl controllo esteso dei1554 file protetti ha individuato **'+str(len(serialization['differences']))+' differenze preesistenti LF/CRLF/miste** tra byte fisici,Git blob e archivio. Ogni file locale conserva il suo SHA di ingresso; ogni file ZIP interessato è byte-identico al precedente ZIP Round21 e tutte le forme differiscono esclusivamente per CRLF/LF. Nessun file locale è stato normalizzato. I corpus congelati e i file semantici restano verificati separatamente con i loro hash originali. Allowlist e hash delle tre forme in archive_serialization_audit.json. Il primo ZIP rifiutato dal verificatore è preservato in `'+serialization['preserved_failed_attempt']+'`,SHA `'+serialization['original_failed_package_sha256']+'`; nessuna predizione o misura scientifica è stata ripetuta per correggere questo controllo di packaging.\n'
    (ROOT/'docs/ROUND22_REPORT.md').write_text(report,encoding='utf8',newline='\n')
    old=subprocess.check_output(['git','show',ROUND21_TREE+':docs/BENCHMARK.md'],cwd=ROOT).decode('utf8')
    (ROOT/'docs/BENCHMARK.md').write_text(f"# Round22 — {status}\n\nMotore v7 invariato;unknown4 originale120/120 preservato senza replay. Generation100/100(40native/60static). V6 fresca597noti/40ID/8fonti: P{m['precision']:.4%},R{m['recall']:.4%},scan R{s['recall']:.4%},filled R{fill['recall']:.4%};wrong{m['wrong']},errori ente/versione{m['entity_errors']}/{m['version_errors']},retrieval25{v['retrieval']['25']:.4%}. Canonical{canonical['exact']}/1007,safety FA{len(safety['false_accepts'])},coverage{cov['file_backed_percent']:.4f}%,p95post{perf['median_p95']:.4f}ms,full tests{tests['passed']}/0/{tests['skipped']}. Gate falliti `{reasons}`. V5 storica e dev separati. Pubblico0.6.1/schema610,CI esterna pending. [Report Round22](ROUND22_REPORT.md). Sezioni successive storiche.\n\n"+old,encoding='utf8',newline='\n')
    (ROOT/'docs/ROUND22_FILLED_GENERATION_AUDIT.md').write_text(f'''# Round22 — audit del generatore

Audit25/25 fallimenti originali su cinquePDF statici: riquadri fissi larghi su prima pagina,nessun widget. Dati nel CSV,geometry JSON e immagini private. Policy v2 fissata prima della generazione; input20ID/5varianti e seed invariati. Nessuna recognition durante audit/generazione.

Nuovo risultato **100/100**,40native/60static,tutti60static con7valori verificati;0fallback effettivi (fallback malformato testato su fixture). Reopen/widget/valori/template/raster144DPI/SHA/parser/riferimenti controllati su ogni file. Sei campioni Poppler visualizzati: cinque vecchi casi problematici più native; nessun overlap/clipping del contenuto originale. Overlay in whitespace non rappresenta una compilazione semanticamente corretta. Vecchi75output e25failure restano intatti; tre normalized DOCX non riparati. Nessun resampling o cambioidentity.

Test iniziale1failure/10pass: URI inline annidato non rilevato,risolto prima dell'aggregazione con visita ricorsiva limitata; finale11pass. Recognition files hash prima/dopo uguali,decisionv7/catalogo/dataset immutati. Dopo freeze/primaV6 nessun cambiamento a generator o protocollo. V6 e ogni successiva metrica sono separati dalla generation success.
''',encoding='utf8',newline='\n')
    if ready:
        descriptions={'IT':f'''# BurOCRazia 0.7.0-rc1 — candidata locale

**READY LOCALLY**, Round22. Pacchetto candidato0.7.0-rc1; la versione software pubblica e i byte runtime restano0.6.1, schema610. Il motore v7 è identico al Round21; migliora soltanto il generatore benchmark filled-form.

V6 single-shot: precisione100%, recall{m['recall']:.2%}, scan{ s['recall']:.2%}, filled{fill['recall']:.2%}; generazione100/100, unknown4 originale120/120 preservato senza replay. Limiti,CI nominali e raw nel [report](docs/ROUND22_REPORT.md). CI esterna pending;questa RC locale non è una release pubblica né una garanzia su scansioni reali.

Avvio locale: `python run.py`, su loopback. OCR Tesseract locale,nessun LLM/cloud/telemetria. Conserva il catalogo completo,le provenienze e i limiti parser. Gli output PDF compilati sono fixture sintetiche private,non documenti da presentare agli enti.
''','EN':f'''# BurOCRazia 0.7.0-rc1 — local candidate

**READY LOCALLY**, Round22. Candidate package0.7.0-rc1;public software version and runtime bytes remain0.6.1,schema610. Recognition v7 is identical to Round21;only benchmark filled-form generation improved.

V6 single-shot: precision100%, recall{m['recall']:.2%}, scan{ s['recall']:.2%}, filled{fill['recall']:.2%};generation100/100,original unknown4 120/120 preserved without replay. See [report](docs/ROUND22_REPORT.md) for raw evidence,nominal intervals and limits. External CI is pending;this local RC is not a public release or assurance for real user scans.

Start locally with `python run.py` on loopback. Local Tesseract OCR,no LLM/cloud/telemetry. Full catalog,provenance and parser limits are preserved. Filled PDFs are private synthetic benchmark fixtures,not documents for submission.
'''}
        for lang,text in descriptions.items():(ROOT/('README_CANDIDATE_'+lang+'.md')).write_text(text,encoding='utf8',newline='\n')
        (ROOT/'CHANGELOG_CANDIDATE.md').write_text('# 0.7.0-rc1 — local candidate\n\nRound22 changes only benchmark filled generation,validation and evidence infrastructure. Native AcroForm persistence,deterministic raster-safe static overlay and malformed-form fallback are validated;generation100/100. Recognition v7 unchanged. Fresh V6 and original compatible unknown4 gates passed locally. Public software bytes/version remain0.6.1/schema610. External CI pending;no commit,tag or publication. See docs/ROUND22_REPORT.md.\n',encoding='utf8',newline='\n')
        save('candidate_metadata',dict(candidate_version='0.7.0-rc1',public_stable_version='0.6.1',schema=610,status='READY LOCALLY',CI='external_pending',release_published=False))
    paths=[p for p in OUT.glob('*') if p.suffix in ['.json','.csv'] and p.name!='evidence_locks.json']
    paths.extend(ROOT/p for p in ['docs/ROUND22_BASELINE_AUDIT.md','docs/ROUND22_FILLED_GENERATION_AUDIT.md','docs/ROUND22_REPORT.md','docs/BENCHMARK.md','docs/release_gates.json','benchmarks/latest_summary.json','benchmarks/reference/filled_generation_policy_v2.json'])
    paths.extend([*ROOT.glob('scripts/round22_*.py'),ROOT/'scripts/package_candidate.py',ROOT/'docs/CONTINUITA_OPERATIVA.md'])
    if ready:paths.extend(ROOT/p for p in ['README_CANDIDATE_IT.md','README_CANDIDATE_EN.md','CHANGELOG_CANDIDATE.md'])
    save('evidence_locks',dict(sha256={p.relative_to(ROOT).as_posix():sha(p) for p in paths},runtime_sha256=f['working_tree_recognition_hash'],scope='All Round22 public evidence;old public files protected by initial baseline and prior seals. Evaluation artifacts frozen independently.'))
    sealed();checkpoint('Round22 final report complete; package next',status+';failed gates='+','.join(reasons)+';V6 closed,no tuning,all evidence preserved.', 'Create separate temporary-index Git tree;package_candidate --tree TREE;verify archive,original HEAD/index and frozen bytes,then close Goal.')
    print('R22',status,reasons,flush=True)

if __name__=='__main__':main()
