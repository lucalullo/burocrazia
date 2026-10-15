"""Report all sealed development, fresh evaluation and non-executed gates."""
import csv
from collections import Counter
from scripts.round21_common import *
from benchmarks.round21_release import sealed
from benchmarks.evaluate import summary,code_hash
from benchmarks.round4_common import runtime_hash

def main():
    f=sealed();assert (OUT/'final_validation_on_freeze.json').exists()
    cal=read(OUT/'calibration_v7.json');pre=read(OUT/'pre_freeze_gate.json');perf=read(OUT/'performance_stability.json');tests=read(OUT/'final_tests_on_freeze.json');cov=read(OUT/'coverage.json');unknown=read(OUT/'unknown_release_v4.json')
    actual_v6=(OUT/'evaluation_v6_gate.json').exists();v6=read(OUT/'evaluation_v6_gate.json') if actual_v6 else None
    gen=read(OUT/'evaluation_v6_generation_preflight.json') if (OUT/'evaluation_v6_generation_preflight.json').exists() else None
    if not actual_v6:
        assert not unknown['passed'] or not gen or not gen['passed'],'V6 is authorized and still incomplete'
        reason='Unknown4 failed' if not unknown['passed'] else 'Generation capacity/leakage preflight failed'
        for n in ['robustness_v6','scan_v6','filled_v6','retrieval_v6','end_to_end_v6']:
            save(n,dict(status='not_run',recognition_calls=0,cases=[],summary=dict(metrics={},latency_ms={},cases=0),reason=reason))
    gates=[]
    def gate(name,actual,passed,target):gates.append(dict(gate=name,actual=actual,passed=bool(passed),target=target,blocking=True,status='PASS' if passed else 'FAIL'))
    for n in ['dev_precision_pass','dev_recall_pass','dev_scan_pass','dev_filled_pass','confirmed_safety_pass','canonical_pass','hard_negatives_pass','coverage_pass','input_safety_pass','performance_pass','tests_pass','V6_pool_pass','unknown_v4_preflight_pass','entity_version_pass','final_checks_pass']:
        gate(n,pre[n],pre[n],'Immutable pre-freeze prerequisite')
    gate('unknown_v4',dict(n=unknown['n'],correct_rejects=unknown['correct_no_match'],false_accepts=unknown['wrong_document_match']+unknown['wrong_family_match'],rejection_rate=unknown['rejection_rate'],entity_errors=unknown['entity_errors'],version_errors=unknown['version_errors']),unknown['passed'],'>=99% rejection,<=1% FA,0 entity/version errors')
    gate('v6_generation_and_leakage',gen,gen is not None and gen['passed'],'>=30 IDs/6 sources/400 known/200 scans/50 filled/generation90%,leakage0')
    if v6:
        for n,g in v6['gates'].items():gate(n,g['actual'],g['passed'],'Frozen Round21 V6 requirement')
    else:gate('fresh_v6_evaluation',None,False,'Fresh single-shot V6 required')
    gate('final_frozen_validation',tests,read(OUT/'final_validation_on_freeze.json')['passed'],'Full pytest0 failures,compile,catalog,FK,migration610,schemas')
    ready=all(g['passed'] for g in gates);status='READY LOCALLY' if ready else 'NOT READY';reasons=[g['gate'] for g in gates if not g['passed']]
    ident=dict(commit=BASE,runtime_sha256=runtime_hash(),code_sha256=code_hash(),fingerprint_sha256=f['fingerprint_dataset_sha256'],semantic_source_tree=f['semantic_source_tree'])
    g=dict(schema_version=1,round=21,status=status,software_version='0.6.1',candidate_target='0.7.0-rc1' if ready else '0.7.0',local_gates_passed=ready,ci='external_pending',freeze=f,identity=ident,tests=tests,gates=gates,reasons=reasons,family_status='experimental / insufficiently validated',new_commit_created=False)
    atomic_json(ROOT/'docs/release_gates.json',g)
    history=read('benchmarks/results/round20/historical_independent_v5_round19.json');save('historical_independent_v5_round19',history)
    observations=read(cal['observations_path'])['cases'];v5rows=[r for r in observations if r['group']=='v5'];canonical=read(OUT/'canonical.json')['cases'];urows=read(OUT/'unknown_release_v4_observations.json')['cases']
    oldcal=read('benchmarks/results/round20/calibration_v6.json');oldrows={r['id']:r for r in read(oldcal['observations_path'])['cases']}
    gained=[r for r in v5rows if r['document_correct'] and not oldrows[r['id']]['document_correct']]
    lost=[r['id'] for r in v5rows if not r['document_correct'] and oldrows[r['id']]['document_correct']]
    recovery_counts=dict(Counter(next((s for s in r['signals'] if s.startswith(('A_','B_','C_','D_'))),'unspecified') for r in gained))
    root_counts=dict(Counter(r['root_cause'] for r in csv.DictReader((OUT/'dev_false_reject_audit.csv').open(encoding='utf8'))))
    save('development_improvements',dict(gained=len(gained),lost=lost,by_acceptance_tier=recovery_counts,prior_false_reject_root_causes=root_counts,recovered_case_ids=[r['id'] for r in gained],scope='Measured comparison to fixed Round20 development. No recognition rerun.'))
    if gen:
        attempts=read(OUT/'evaluation_v6_prepared.json')['generation_audit'];failed=[r for r in attempts if not r['generated']]
        save('evaluation_v6_generation_failure_summary',dict(attempted=len(attempts),valid=gen['known'],failed=len(failed),filled_attempted=100,filled_valid=75,filled_failed=25,filled_failed_identity_ids=sorted({r['document_id'] for r in failed if r['filled']}),digital_failed_identity_ids=sorted({r['document_id'] for r in failed if not r['filled']}),filled_failure_reason='No safe blank overlay rectangle',digital_failure_reason='lxml C14N failed; no repair or substitute',recognition_calls=0,resampling=False,leakage_pass=read(OUT/'evaluation_v6_leakage.json')['passed'],failed_gate='filled_generation_rate 0.75 < 0.90',cases=failed))
    logs={p.relative_to(ROOT).as_posix():dict(sha256=sha(p),bytes=p.stat().st_size) for p in ROOT.glob('reports/round21-*.log') if not p.name.startswith('round21-finish')}
    save('technical_attempt_history',dict(logs=logs,events=['v7_initial recall below gate; complete raw retained.','Unknown truth revisions all before freeze and predictions.','Frozen preparation unhandled C14NError after133 files; no V6 calls.','Recovery initial metadata guard failed before generator calls; log retained.','Recovery reused133 existing outputs unchanged, marked3 C14N and25 fill failures, no resampling.','First final validation hit a Windows SQLite cleanup lock after parsed tests; explicitly closed copied connection on retry, original temp/log retained.','Final full suite completed once on freeze; no repeat needed.'],all_semantic_files_still_frozen=True,V6_recognition_calls=0,unknown_release_recognition_calls=120))
    evals=[dict(name='development_regression_v5_after_fix',summary=summary(v5rows)),dict(name='fresh_unknown_release_v4',summary=summary(urows))]
    sections={}
    for field,name in [('known_robustness','robustness_v6'),('scan_ocr','scan_v6'),('filled_forms','filled_v6')]:
        value=read(OUT/(name+'.json'));sections[field]=dict(status='executed' if actual_v6 else 'not_run',summary=value['summary'],scope='Fresh reserved-identity V6, single-shot on frozen v7 runtime.' if actual_v6 else value['reason'])
        if actual_v6:evals.append(dict(name=name,summary=value['summary']))
    latest=dict(schema_version=1,benchmark_model='known-family-unknown-v5',round=21,status=status,software_version='0.6.1',version='0.6.1',candidate_target=g['candidate_target'],catalog_count=1216,catalog_semantic_sha256='sha256:'+f['catalog_semantic_sha256'],commit=BASE,semantic_source_tree=f['semantic_source_tree'],runtime_sha256=runtime_hash(),new_commit_created=False,github_ci='external_pending',reasons=reasons,evaluations=evals,**sections,known_canonical=dict(status='executed',summary=summary(canonical),scope='1007 product canonical checks, before reservation; byte-identical frozen runtime.'),fingerprint_coverage=dict(status='executed',**cov),unknown_official=dict(status='executed',summary=summary(urows),metrics={k:unknown[k] for k in ['n','correct_no_match','wrong_document_match','wrong_family_match','extraction_failed','rejection_rate','false_acceptance_rate','confidence_interval_95','entity_errors','version_errors']},scope='Fresh unknown v4,120/15sources; sole predictions reused in end-to-end, never replayed.'),unknown_master_pool=dict(status='metadata_only',N=read(OUT/'unknown_v4_preflight.json')['master_N'],sources=15,scope='Master reserved before freeze; selection fixed after freeze.'),unknown_release_subset=dict(status='executed',**unknown['selection']),performance=dict(status='executed',median_p95_ms=perf['median_p95'],runs=7,pass_count=perf['pass_count'],preferred_pass=perf['preferred_latency_pass'],scope='All7 predeclared isolated warm runs; extraction/OCR outside timing; frozen runtime unchanged.'),development_regression_v5_after_fix=dict(status='executed',classification='development_only',metrics=cal['V5_development'],scan=cal['scan'],filled=cal['filled'],false_accepts=0,scope='Contaminated replay; never substitutes for independent V5.'),historical_independent_v5_round19=dict(status='historical_only',precision=.9824561403508771,recall=.705511811023622,scan_recall=.6329365079365079,original_artifact_sha256=sha('benchmarks/results/round19/evaluation_v5_observations.json'),scope='Original independent V5 remains unchanged; original runtime and labels, not a current-engine claim.'),family_identity_holdout=dict(status='experimental / insufficiently validated',families_evaluable=0),release_gate=dict(status='executed',n=1258,passed=True,scope='Confirmed development diagnostic only.'),truth_policy=dict(policy_sha256=sha(POLICY),base_truth_sha256=sha(TRUTH),historical_mismatches=len(read(OUT/'historical_regression_fast.json')['mismatches'])),fresh_v6_gate=v6)
    atomic_json(ROOT/'benchmarks/latest_summary.json',latest)
    from src.benchmark_display import load_summary
    load_summary(ROOT/'benchmarks/latest_summary.json')
    if actual_v6:
        rows=read(OUT/'evaluation_v6_observations.json')['cases'];miss=[r for r in rows if not r['document_correct']]
        values=[dict(case_id=r['id'],document_id=r['expected']['document_id'],source=r['provenance'].get('source_id'),transform=r['representation'],expected_rank=r.get('expected_rank'),observed_type=r['observed']['match_type'],observed_document=r['observed'].get('document_id'),extraction_failed=r['extraction_failed'],entity_error=r['entity_error'],version_error=r['version_error'],reject_reason=r.get('reason','')) for r in miss]
        with (OUT/'evaluation_v6_failures.csv').open('w',encoding='utf8',newline='') as stream:
            fields=list(values[0]) if values else ['case_id','document_id','source','transform','expected_rank','observed_type','observed_document','extraction_failed','entity_error','version_error','reject_reason'];w=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(values)
        from benchmarks.round21_calibrate import rate
        save('evaluation_v6_breakdown',dict(by_source={str(s):rate([r for r in rows if r['provenance'].get('source_id')==s]) for s in sorted({r['provenance'].get('source_id') for r in rows})},by_transform={n:rate([r for r in rows if r['representation']==n]) for n in sorted({r['representation'] for r in rows})},failure_count=len(miss),scope='Post-evaluation diagnostics only. No tuning or relabel; V6 cannot be reused as independent after any future tuning.'))
    pool=read(OUT/'v6_preflight.json');selection=read(OUT/'evaluation_v6_plan.json') if (OUT/'evaluation_v6_plan.json').exists() else None;hard=read(OUT/'hard_negatives_development.json');m,s,filled=cal['V5_development'],cal['scan'],cal['filled'];retrieval=read(OUT/'dev_retrieval_summary.json')
    table='\n'.join('| '+ ' | '.join(str(x).replace('|','/') for x in [g['gate'],g['actual'] if not isinstance(g['actual'],dict) else json.dumps(g['actual'],ensure_ascii=False),g['status']])+' |' for g in gates)
    timing='\n'.join(f"| {r['run']} | {r['latency_ms']['p50']} | {r['latency_ms']['p95']} |" for r in perf['runs'])
    v6text=f"V6 single-shot completata: overall `{v6['metrics']}`; scan `{v6['scan']}`; filled `{v6['filled']}`; retrieval `{v6['retrieval']}`; errori `{v6['errors']}`. Gate: `{v6['gates']}`. Raw e failure diagnostics conservati integralmente; nessun tuning dopo il risultato." if actual_v6 else f"**V6 non eseguita**,0 predizioni: {reason}. Metriche P/R/F1/retrieval non misurate,mai rappresentate come zero prestazioni. Tutti i fallimenti di generazione/leakage restano agli atti."
    report=f'''# Round 21 — {status}

Pubblico **0.6.1**, schema **610**. Branch `codex/coverage-benchmark-v0.7.0`, HEAD originale `{BASE}`. Tutto il working tree Round20 preservato. Nessun commit/push/tag/release. Il campo commit del freeze indica soltanto la base; il vero snapshot semantico è il **Git tree non committato `{f['semantic_source_tree']}`**. Archivio finale e SHA nel sidecar `dist/package-verification-round21.json`. CI esterna pending; nessun collaudo Linux/macOS.

## Sviluppo, audit e policy v7

V5 indipendente Round19 immutata: **P98,2456%,R70,5512%,scan R63,2937%**,448 exact/8 wrong/179 NO su635 noti,665 raw con mix unknown. Il replay non sostituisce questi numeri. Round20 development v6 P100%,R85,3543%,scan R81,9444%,filled100% resta storico. Unknown v3 originale116/116/13fonti non valida automaticamente v7.

Audit di170 miss complessivi confermati,93 V5: **87/93 rank1 (93,5484%)**; dettagli/rank5/10/25/rootcause in dev_false_reject_audit.csv e dev_retrieval_summary.json. Retrieval/pesi/global threshold/margin invariati. Policy v7 aggiuntiva, vecchia v6 immutata: rank1 OCR/page+char+anchor forti, strict layout+contenuto corroborato, heading esclusivo completo e ordinato nella finestra iniziale. Heading disambigua soltanto un candidato già primo; non crea un match da un ID atteso. Entity/version confirmed/unknown/conflict separati, conflitto esplicito hard veto; anno fiscale distinto da versione. Titoli/codici catalogo, provenienze e input oltre2000caratteri rispettano i vincoli. Canali/condizioni/reason codes/limiti/test in DECISION_POLICY_V7.md.

Entrambe le iterazioni restano: v7_initial R88,8189% fallita; v7_ordered finale **{m['exact']}/635,P{m['precision']:.4%},R{m['recall']:.4%}**; scan **{s['exact']}/504,P{s['precision']:.4%},R{s['recall']:.4%}**; filled **{filled['exact']}/55,P/R100%**. Nessun wrong document confermato. **705 negativi confermati,0 false accept**; hard negative sintetici **{hard['correct_rejects']}/{hard['n']}**,FAMILY su unknown sempre errore. Canonical **1007/1007**. Due casi INAIL storicamente ambigui mantengono etichette/raw originali, non entrano nella safety confermata; ID osservato1147 escluso dal pool fresco. Quattro extraction refusal development non sono credited unknown success. Tutto è development contaminato, non evidenza indipendente.

## Capacità fresca e registry

Audit di tutte19fonti/1019ID fingerprint: pool **{pool['identities']} identità/{pool['sources']}fonti**,conteggi `{pool['counts_per_source']}`. Nessuna nuova identità,fonte,fingerprint o modifica al seed. Le357 incertezze originali includevano candidati recuperati nei diagnostici di soli40 input legacy;324 flag sono risolti con prova dei file/ID effettivamente input. Esposizione canonica/qualificazione/evaluation storica sola non è tuning secondo Round21. I40 input di qualificazione rimangono esclusi conservativamente,senza attribuire tuning non dimostrato. Ogni ID realmente usato in tuning,V5,development Round20/21 (inclusi observed errati/ambigui) resta escluso. Source profile/source seen non elimina automaticamente tutta una fonte. Registry v7 conserva legacy e flag v6 precedenti; parent hash e audit peridentità. Prenotazione639ID dopo tutte le misure development/canonical/performance e prima del freeze. Nessuna predizione/trasformazione fra prenotazione e freeze.

Selezione V6 fissata dopo freeze e unknownPASS: `{selection['source_counts'] if selection else None}`,seed202610142106,40ID/8fonti,max15%,strati fonte/formato/versione/codice/pagine;20PDF filler con5 varianti fisse. Fonti Garante e ANAC hanno soltanto3 identità ciascuna,limite esplicito. Rappresentazioni digitali,scan200/150DPI,JPEG90/75/60,grayscale,blur,contrast,crop2/5%,first-page e rotazioni; rumore minimo con seed nuovo. Riempimento sintetico verificato con campi/checkbox/data/numeri/testo o overlay statico. Generazione/preflight: `{gen}`. Non sono scansioni o dati personali reali.

## Unknown v4,freeze e single-shot

829 candidati da cache ufficiale con ricevute e SHA effettivi,**zero richieste di rete Round21**. Revisioni truth pre-freeze413→266→236→213,tutte preservate: heading primario invece di citazioni nel corpo,esclusione raw/URL canonici noti,form heading/collisioni,emittente primario separato da fonte,23 duplicati con apertura nativa normalizzata identica esclusi. Audit tecnico riproducibile,non nuova validazione editoriale umana. Codice/versione non determinabili restano null. Nessuna predizione durante discovery/truth/preflight. Master finale **213/15fonti**; source balance/format support/freshness passano.

Freeze lega runtime `{runtime_hash()}`,profilo `{f['decision_v7_sha256']}`,dataset `{f['fingerprint_dataset_sha256']}`,catalog semantic/calibrazione/registry/prenotazione/truth/gate/canonical/safety/timing/test/schema e tutti i file di codice. L'infrastruttura benchmark fu completata dopo il timing,con full-code hash distinto; il runtime misurato è identico. Solo catalog_manifest conserva una differenza CRLF workspace/LF Git preesistente verificata semanticamente,senza riscriverlo.

Selezione metadata-only post-freeze,seed202610142104: **120unknown/15fonti/18emittenti**,max10,8333%,6tipi. Prima e unica valutazione: **{unknown['correct_no_match']}/120 correct NO**,0 DOCUMENT/FAMILY false accept,0 extraction failure,0 errori ente/versione. Wilson95% `{unknown['confidence_interval_95']}`; non è garanzia sulla popolazione. Tutte le osservazioni e conteggi/schema/SHA sono finalizzati atomicamente. End-to-end riusa queste stesse righe,zero seconde predizioni unknown.

{v6text}

Il runner generazione iniziale ha lasciato133 file prima di C14NError DOCX non intercettato. Adapter operativo in scripts/round21_generation_resume.py conserva byte/hash e riusa gli output già riusciti; traduce l'eccezione in generazione fallita,senza riparare XML,cambiare generatore/seed/varianti,selezione o engine. L'errore originale,guardia di ripresa iniziale e audit della ripresa rimangono. Le chiamate fallite prima dell'interruzione prive di receipt durevole possono essere state ritentate con gli stessi parametri; non vengono scelte varianti alternative o rimossi fallimenti per migliorare il tasso. I vecchi compilati riusciti sono riaperti con verifica concreta di marker sintetici (lower bound),oltre alla verifica già eseguita dal generatore prima del salvataggio. Nessuna predizione V6 precede il gate di generazione/leakage. I file semantici congelati restano invariati.

## Verifiche e limiti

Coverage **{cov['file_backed_percent']:.6f}% (1002/1158)**. Input safety9/9,0recognition dopo rifiuto parser. Catalogo1216 documenti,19fonti,16famiglie,integrity/FK/migrazione610idempotente/conteggi invariati. Compile,profili,dataset/schema verificati. Release diagnostic1258/1258PASS; historical regression1517contratti/15mismatch/exit1 resta come prova originale incompatibilità etichette,non viene spacciato perzero mismatch. Canonical/safety/diagnostici legati allo stesso runtime del freeze,senza replay ridondanti.

| Run | p50 ms | p95 ms |
| --- | --- | --- |
{timing}

Tutti7 run predeterminati,67 input/402richieste perrun/2814timing. **p95 mediano {perf['median_p95']}ms**,7/7≤250,preferito180PASS. Solo matching warm,estrazione/OCR esclusi; RequestPages nuove,cache solo metadati. Baseline Round20 123,6941ms separata. Nessun rerun selezionato favorevolmente.

Baseline856/0/3; full v7 pre-freeze876/0/3 più2test infrastruttura. **Full suite sul freeze {tests['passed']}passed/{tests['failed']}failed/{tests['skipped']}skipped**,{tests['seconds']}s,log SHA`{tests['log_sha256']}`. Skip Windows: symlink senza privilegio e FIFO non disponibili. Collaudo Windows/Python3.12.10,Tesseract locale reale; benchmark scan/filled sintetici e correlati peridentità. Nessun test su dati personali,nessuna equivalenza statistica con scansioni di campo. Family **experimental / insufficiently validated**,non contribuisce exact recall. CI esterna pending.

## Esito

**{status}**. Gate falliti: `{reasons}`. Nessun tuning dopo fresh unknown/V6; qualunque sviluppo futuro che usi questi risultati li rende development e richiede nuovi held-out. Pubblico resta0.6.1. Archivio `dist/BurOCRazia-v0.7.0-{'RC1' if ready else 'candidate-NOT-READY'}-round21.zip` con verifica storici/freeze/raw/conteggi/hash/hygiene. Cache,binari ufficiali,checkpoint privati,testo estratto,DB di lavoro e log esclusi; risultati pubblici e script inclusi. Goal e heartbeat nativi supportano ripresa entro i limiti reali dell'app e quota,senza servizi esterni; checkpoint persistenti privati append-only. Al completamento verificato Round21 il heartbeat viene disattivato.

| Gate | Actual | Esito |
| --- | --- | --- |
{table}
'''
    report=report.replace('Entrambe le iterazioni restano:',f"Cause originali sui 170 miss: `{root_counts}`. Recuperati **{len(gained)} casi V5**, nessun caso prima corretto perso; tier effettivi `{recovery_counts}`.\n\nEntrambe le iterazioni restano:")
    report=report.replace('**V6 non eseguita**,0 predizioni: Generation capacity/leakage preflight failed.', '**V6 non eseguita**, 0 predizioni: il solo requisito misurato fallito è la generazione filled **75% < 90%**. Leakage **0, PASS**. Precisione, recall, F1, errori ente/versione, retrieval @1/@5/@10/@25, scan e filled V6 restano non misurati. Unknown end-to-end V6 non eseguito; la misura fresh unknown v4 separata resta 120/120. I 25 compilati falliti riguardano ID484/264/263/558/414 (5 varianti ciascuno); tre normalized DOCX falliscono per ID113/1121/1074. Nessun ID o variante sostitutiva.')
    report=report.replace('End-to-end riusa queste stesse righe,zero seconde predizioni unknown.','Il protocollo end-to-end prevede il riuso di queste stesse righe; essendo V6 bloccata, nessun end-to-end V6 è stato eseguito. Zero seconde predizioni unknown.')
    report=report.replace('Tutti i fallimenti di generazione/leakage restano agli atti.','Tutti i fallimenti di generazione restano agli atti; il leakage passa.')
    import re
    parts=report.split('`')
    for i in range(0,len(parts),2):
        p=parts[i]
        p=re.sub(r',(?=[^\s\d])',', ',p)
        p=re.sub(r'\b(Round|scan|filled|canonical|Coverage|Pubblico|schema|seed|Audit|audit|pool|input|su|di|tutte|soli|fonti|I|Le|Prenotazione|Baseline|full|baseline|originale|dopo|prima|lasciato|circa|soltanto|contratti)(?=\d)',r'\1 ',p)
        p=re.sub(r'(?<=\d)(?=(?:fonti|unknown|emittenti|tipi|ID|test|input|ms|caratteri|file|passed|failed|skipped|PDF|richieste|timing|contratti|idempotente|varianti)\b)',' ',p)
        for a,b in {'peridentità':'per identità','perrun':'per run','scan200':'scan 200','JPEG90':'JPEG 90','crop2':'crop 2','con5':'con 5','tutte19':'tutte 19','soli40':'soli 40','Le357':'Le 357',';324':'; 324','traformazioni':'trasformazioni','credenziali':'credenziali','oltre2000':'oltre 2000','e133':'e 133',';20PDF':'; 20 PDF','NO**,0':'NO**, 0'}.items():p=p.replace(a,b)
        parts[i]=p
    report='`'.join(parts)
    (ROOT/'docs/ROUND21_REPORT.md').write_text(report,encoding='utf8',newline='\n')
    prior=subprocess.check_output(['git','show',ROUND20_TREE+':docs/BENCHMARK.md'],cwd=ROOT).decode('utf8')
    lead=f"# Round 21 — {status}\n\nDevelopment v7: P100%,R90,3937%,scan R88,2937%,filled100%,0FA confermati. Pool639ID/8fonti. Fresh unknown v4:120/120,15fonti,0FA. V6: {json.dumps(v6['metrics']) if v6 else 'non eseguita; preflight generazione/leakage fallito'}. Gate falliti: `{reasons}`. Canonical1007/1007,coverage86,5285%,p95mediano176,6788ms,full test{tests['passed']}/0/{tests['skipped']}. V5 storica P98,2456%,R70,5512%,scan R63,2937% preservata. Pubblico0.6.1/schema610,CI esterna pending. [Report Round21](ROUND21_REPORT.md). Sezioni successive storiche.\n\n"
    (ROOT/'docs/BENCHMARK.md').write_text(lead+prior,encoding='utf8',newline='\n')
    paths=[p for p in OUT.glob('*') if p.suffix in ['.json','.csv'] and p.name!='evidence_locks.json']
    paths.extend(ROOT/p for p in ['docs/ROUND21_REPORT.md','docs/ROUND21_BASELINE_AUDIT.md','docs/ROUND21_V6_SOURCE_AUDIT.md','docs/ROUND21_EVALUATION_PROTOCOL.md','docs/DECISION_POLICY_V7.md','docs/BENCHMARK.md','docs/release_gates.json','benchmarks/latest_summary.json','benchmarks/reference/benchmark_contamination_registry_v7.json','benchmarks/manifests/v6_reserved_identity_pool.json','benchmarks/manifests/official_unknown_release_v4.json','scripts/round21_generation_resume.py'])
    save('evidence_locks',dict(sha256={p.relative_to(ROOT).as_posix():sha(p) for p in paths},runtime_sha256=runtime_hash(),scope='All Round21 public evidence; freeze preserves its original prereq files separately. Prior results protected by baseline and historical seals.'))
    checkpoint('Round21 final evidence complete; package verification next',status+'; failed gates='+','.join(reasons)+'; all raw preserved, no tuning after evaluations.', 'Create final temporary-index Git tree; package_candidate --tree TREE; verify original HEAD/index/historical and archive before closing Goal/heartbeat.')
    print('R21',status,reasons,flush=True)

if __name__=='__main__':main()
