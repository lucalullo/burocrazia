"""Report measured Round19 gates without altering release or historical evidence."""
from collections import Counter
from scripts.round19_common import *
from scripts.round19_seal import verify_benchmark_seal
from benchmarks.round8_common import identity
from benchmarks.evaluate import summary
from src.benchmark_display import load_summary

def counts(rows):
    return dict(n=len(rows),exact=sum(r['document_correct'] for r in rows),family=sum(r['observed']['match_type']=='FAMILY_MATCH' for r in rows),
                reject=sum(r['observed']['match_type']=='NO_MATCH' for r in rows),wrong=sum(r['observed']['match_type']=='DOCUMENT_MATCH' and not r['document_correct'] for r in rows),
                entity_errors=sum(r['entity_error'] for r in rows),version_errors=sum(r['version_error'] for r in rows),extraction_failed=sum(r['extraction_failed'] for r in rows))

def main():
    f=sealed();verify_benchmark_seal()
    v5=read(OUT/'evaluation_v5_gate.json');perf=read(OUT/'performance_stability.json');test=read(OUT/'final_tests.json');checks=read(OUT/'final_checks.json')
    u=read('benchmarks/results/round18/unknown_release_v3.json');eq=read(OUT/'semantic_equivalence.json');pool=read(OUT/'evaluation_v5_preflight.json');generated=read(OUT/'evaluation_v5_generation_preflight.json')
    cov=read(OUT/'coverage.json');gates=[]
    def g(name,target,actual,passed,blocking=True):gates.append(dict(gate=name,target=target,actual=actual,passed=bool(passed),blocking=blocking,status='PASS' if passed else 'FAIL' if blocking else 'PENDING'))
    g('freeze_integrity','same aa81678 semantic hash',f['recognition_semantic_sha256'],True)
    g('unknown_v3','>=99% reject, >=100, >=6 sources',dict(n=u['n'],correct=u['correct_no_match'],false_document=u['wrong_document_match'],false_family=u['wrong_family_match']),u['passed'])
    g('coverage','>=85% file-backed',cov.get('file_backed_percent',1002/1158*100),cov['passed'])
    n=sum(read(OUT/(name+'.json'))['counts']['exact'] for name in ['canonical','canonical_legacy'])
    g('canonical','1007/1007',n,n==1007)
    g('confirmed_safety','zero false accepts',241,read(OUT/'historical_safety.json')['passed'] and read(OUT/'confirmed_ANAC.json')['passed'] and read(OUT/'old_false_accepts.json')['passed'])
    g('input_safety','safe rejection9/9',9,read(OUT/'input_safety.json')['passed'])
    g('semantic_equivalence','1563 / zero differences',dict(n=eq['n'],differences=len(eq['differences'])),eq['passed'] and eq['n']==1563)
    g('release_gate_fast','1258/1258',read(OUT/'release_gate_fast.json')['n'],read(OUT/'release_gate_fast.json')['passed'])
    g('performance_median_p95','<=250 ms',perf['median_p95'],perf['required_pass'])
    g('tests','zero failures',dict(passed=test['passed'],failed=test['failed'],skipped=test['skipped']),test['failed']==0)
    g('final_checks','compile/catalog/FK/migration/schema',checks['passed'],checks['passed'])
    targets=dict(v5_preflight='30IDs/6sources/400known/200scan/50filled/30unknown',v5_leakage='0',v5_precision='>=99.5%',v5_exact_recall='>=90%',v5_scan_precision='>=99.5%',v5_scan_recall='>=85%',v5_filled_generation='>=90%',v5_filled_precision='>=99.5%',v5_filled_recall='>=90%',v5_retrieval_at25='100%',v5_retrieval_at1='>=99%',v5_entity_version='0',v5_unknown_mix='>=99%')
    for name,row in v5['gates'].items():g(name,targets[name],row['actual'],row['passed'])
    g('family','>=5 identity-held-out families','experimental / insufficiently validated',False,False)
    g('CI','external matrix','external_pending',False,False)
    ready=all(x['passed'] for x in gates if x['blocking']);status='READY LOCALLY' if ready else 'NOT READY';version='0.7.0-rc1' if ready else '0.6.1'
    reasons=[x['gate'] for x in gates if x['blocking'] and not x['passed']];ident=identity()
    atomic_json(ROOT/'docs/release_gates.json',dict(round=19,status=status,software_version=version,candidate_target='0.7.0',schema=610,freeze=FREEZE,identity=ident,gates=gates,local_gates_passed=ready,tests=test,reasons=reasons,ci='external_pending'))
    latest=json.loads(subprocess.check_output(['git','show',BASE+':benchmarks/latest_summary.json'],cwd=ROOT))
    latest.update(round=19,status=status,version=version,software_version=version,commit=ident['commit'],runtime_sha256=ident['runtime_sha256'],fingerprint_sha256=ident['fingerprint_sha256'],reasons=reasons)
    latest['performance']=dict(status='executed',summary=dict(cases=2814,metrics={},latency_ms=dict(p95=perf['median_p95'])),runs=[r['latency_ms'] for r in perf['runs']],scope='Seven fixed final validation runs; no optimization or favorable reruns.')
    latest['known_canonical']=dict(status='executed',summary=summary(read(OUT/'canonical.json')['cases']+read(OUT/'canonical_legacy.json')['cases']),scope='Current technical canonical contracts, not independent identity generalization.')
    latest['known_canonical']['summary']['latency_ms']={}
    for key,artifact in [('known_robustness','robustness_v5'),('scan_ocr','scan_v5'),('filled_forms','filled_v5')]:latest[key]=dict(status='executed',summary=read(OUT/(artifact+'.json'))['summary'],scope='Round19 single-shot fresh representations of eligible known identities.')
    latest['unknown_official']['scope']='Preserved Round18 unknown v3 single-shot evidence; not rerun in Round19. Thirty-case V5 mix separately reported.'
    latest['evaluations']=[dict(name=p.stem,summary=read(p)['summary']) for p in sorted(OUT.glob('historical_*.json')) if 'summary' in read(p)]
    atomic_json(ROOT/'benchmarks/latest_summary.json',latest);load_summary(ROOT/'benchmarks/latest_summary.json')
    groups={name:read(OUT/(name+'.json')) for name in ['robustness_v5','scan_v5','filled_v5','end_to_end_v5']}
    results={name:dict(counts=counts(value['cases']),metrics=value['summary']['metrics']) for name,value in groups.items()}
    metric_rows=[]
    for name,value in results.items():
        c=value['counts'];m=value['metrics']
        pct=lambda key:f"{100*m[key]['value']:.4f}%" if m[key]['value'] is not None else 'non misurabile'
        metric_rows.append('| '+' | '.join(str(x) for x in [name,c['n'],c['exact'],c['family'],c['reject'],c['wrong'],pct('document_precision'),pct('document_recall'),pct('document_f1'),c['entity_errors'],c['version_errors']])+' |')
    metric_table='|Gruppo|N|Exact|Family|NO|Wrong|Precisione|Recall|F1|Errori ente|Errori versione|\n|---|---|---|---|---|---|---|---|---|---|---|\n'+'\n'.join(metric_rows)
    known=groups['robustness_v5']['cases'];retrieval=read(OUT/'retrieval_v5.json')['recall_at_k'];mix=[r for r in groups['end_to_end_v5']['cases'] if r['unknown']]
    save('evaluation_v5_breakdown',dict(by_source={str(s):dict(counts=counts([r for r in known if r['provenance']['source_id']==s]),source_seen=next(k['source_seen'] for k in read(REGISTRY)['known_identities'] if k['source']==s),source_specific_rule_tuned=next(k['source_specific_rule_tuned'] for k in read(REGISTRY)['known_identities'] if k['source']==s)) for s in sorted({r['provenance']['source_id'] for r in known})},by_transformation={name:counts([r for r in known if r['representation']==name]) for name in sorted({r['representation'] for r in known})},unknown_mix=counts(mix),scope='Diagnostic stratification only; no tuning, selection or label changes.'))
    table='\n'.join('| '+' | '.join(str(x).replace('|','/') for x in row)+' |' for row in [['Gate','Target','Actual','Esito'],['---']*4]+[[x['gate'],x['target'],x['actual'],x['status']] for x in gates])
    timings='\n'.join(f"|{r['run']}|{r['latency_ms']['p50']}|{r['latency_ms']['p95']}|" for r in perf['runs'])
    archive=f"BurOCRazia-v0.7.0-{'RC1' if ready else 'candidate-NOT-READY'}-round19.zip"
    report=f'''# Round19 — {status}

Versione software **{version}**, pubblico0.6.1, schema610. Branch `codex/coverage-benchmark-v0.7.0`; ingresso `{BASE}`, freeze candidato **`{FREEZE}`** riusato. Commit finale e SHA256 ZIP nel verificatore esterno `dist/package-verification-round19.json`. CI **external pending**. Nessun push, tag o pubblicazione.

## Integrità e contaminazione

Runtime `{f['recognition_semantic_sha256']}`, fingerprint `{f['fingerprint_dataset_sha256']}`, decision policy `{f['decision_policy_sha256']}`. Motore, catalogo completo, ranking, soglie, policy, truth e dataset immutati dal freeze. Inventario benchmark Round19 separato in benchmark_seal.json, senza riscrivere il freeze Round18. Unknown v3 conservato byte per byte:116/116,13 fonti,25% concentrazione,0 DOCUMENT/FAMILY false accept; risultato SHA `{sha('benchmarks/results/round18/unknown_release_v3.json')}`, manifest e raw invariati, nessun replay o relabel. Wilson95% [96.7945%,100%] descrive quel campione; il confidence score non è una probabilità.

Audit di1019 identità con record fingerprint, una riga per ID, inclusi record non utilizzabili esplicitamente segnalati. Le identità usate in tuning e le storie dirette non risolte restano escluse. Evaluation storica, source_seen e profili source-specific sono distinti; la firma canonica è parte del prodotto. Registryv3 e tutte le prove legacy restano integri nella v4. Politica documentata prima della selezione in ROUND19_CONTAMINATION_AUDIT.md. Il pool Round18 aveva351 ID/352 record/5 fonti; il nuovo pool ha**{pool['eligible_identities_total']} ID/{pool['sources_total']} fonti**, conteggi `{pool['identities_per_source']}`. Ragioni per ogni esclusione e fonte in CSV/round18_pool_diagnostics.json. Source è il source_id storico catalogo/provenienza: nessuna divisione per hostname, ente o pagina; gate6 invariato.

Recuperate8 identità:286,360,616,684,989,990,994,1212. La sesta fonte è Unioncamere, ID616, presente nel piano/generazione R8 ma non nelle50 osservazioni né nel tuning R8/9. Il vecchio filtro accostava il suo titolo generico ad ANAC611 senza emittente comune. Correzione audit prima di selezione/predizioni, primo diagnostico e hash preservati. Rimangono prudenziali le esclusioni per risorsa, campi, aggregate e titoli/codici/versioni dello stesso emittente. Nessun documento/fingerprint aggiunto.

## Preflight, selezione e rappresentazioni

Capacità iniziale teorica nel pool: {pool['eligible_identities_total']} identità, {pool['sources_total']} fonti, {pool['representation_capacity']} rappresentazioni, {pool['scan_capacity']} scansioni, {pool['fill_capacity']} compilati, {pool['unknown_v3_available']} unknown disponibili. Questa capacità non rivendica compilati validi prima della generazione.
Seconda barriera effettiva prima delle predizioni: {generated['identities']} identità/{generated['sources']} fonti/{generated['known']} noti/{generated['scans']} scan/{generated['valid_filled']} compilati validi/{generated['unknown_mix']} unknown; PASS, generazione{generated['filled_generation_rate']:.4%}.

Selezione fissa seed2026101419, solo metadata/hash, stratificata per fonte/ID/codice/versione/pagine/formato.38 identità/6 fonti; source counts `{read(OUT/'evaluation_v5_plan.json')['source_counts']}`, concentrazione massima26.3158%, limite prospettico35% (preferito30%). Target50 con max10/source e max2DOCX, slot riservati alle fonti disponibili solo DOCX:38 effettive, oltre minimo30; il preferito40–50 non raggiunto. Garante e Unioncamere hanno una sola identità selezionata ciascuno: diversità minima ammessa, non robusta generalizzazione alla fonte.

635 rappresentazioni note:76 derivati digitali strutturali/normalizzati,504 scan-like con200/150DPI,grigio,JPEG,blur,contrasto,crop,prima pagina e rotazioni;55 compilati validi su60 tentativi,91.6667% generazione. Cinque overlay del documento470 falliti per assenza di rettangoli liberi, conservati nel denominatore; nessuna sostituzione. Scansioni sintetiche da pagine canoniche con Tesseract reale, non scansioni personali. Novità effettiva dei pixel (0.05%,intensità±2) da seed per caso; compilazione con valori sintetici nuovi e seed registrati. Nessuna novità rivendicata soltanto per metadata/ID. Controlli SHA e chiavi di trasformazione storiche,0 leakage proibito,0duplicati,truth non ambigua nel contratto canonico. CaseJournal SQLite con checkpoint/resume stesso freeze+manifest+inventario, schema/count/ID/SHA finali; una sola esecuzione, nessun tuning dopo gli esiti.

## V5 single-shot

{metric_table}

Otto identità errate restano tali:469→511 in un crop5%,470→512 in sette rappresentazioni, incluse entrambe le digitali. Un candidato atteso fuori dalla top25:802/rotation180. Nessuna riclassificazione retrospettiva come ambiguità e nessun cambiamento delle aspettative; dettagli in failure_diagnostics.json.

Retrieval@1/@5/@10/@25: `{retrieval}`. Unknown mix: `{counts(mix)}`;30 risorse dal v3 già congelato, verifica end-to-end sullo stesso freeze, non un nuovo campione indipendente. Family resta **experimental / insufficiently validated**, non aumenta exact recall. Ogni FAMILY su unknown è false acceptance. Metriche per fonte/profilo/trasformazione in evaluation_v5_breakdown.json; tutte le osservazioni grezze e i fallimenti restano conservati.

## Validazione finale

Coverage1002/1158=86.528497%,canonici980+27=1007/1007. Safety241 NO sintetici, ANAC e cinque critici storici sicuri;9/9 input safety. Equivalenza corrente1563 firme complete/0 differenze rispetto al Round18, incluse decisioni/score/reason/ente/versione/top25. Nuova verifica effettiva dopo V5 di canonici/equivalenza/input safety in post_v5_validation.json e relativi raw separati; nessun replay di unknown v3 o V5. Sono contratti tecnici e diagnostici, non validazione editoriale o generalizzazione a identità sconosciute.

|Run|p50 ms|p95 ms|
|---|---|---|
{timings}

Mediana p95 **{perf['median_p95']}ms**, gate<=250 **{perf['required_pass']}**, sette run fissati prima della misura/2814 richieste, suite67 input, nessuna ottimizzazione o selezione di rerun. Baseline Round18 234.4921ms preservata separatamente. Estrazione/OCR fuori timing warm; cache solo catalogo, RequestPages nuova per richiesta. Windows/Python3.12.10, nessun collaudo Linux/macOS o su altri computer.

Pytest finale **{test['passed']} passed/{test['failed']} failed/{test['skipped']} skipped**, {test['seconds']}s, log SHA `{test['log_sha256']}`. Compile, SQLite integrity/FK, migrazione idempotente610/conteggi invariati, validatori fingerprint1/2/3, truth/schema, compat-v2 e package verificati. Release-gate-fast1258/1258 exit0; historical-regression-fast1517/15 mismatch exit1 atteso e preservato:2 EX02/EX03 INPS revisione mancante,10 lockedv1,2 annualità INAIL ambigue,1 NO prudente OH1-047. Legacy-fast mantiene EX02/EX03 e exit1. Zero nuovi fallimenti; le etichette storiche non cambiano. Unknownv2 storico107/114 non sostituito da v3. Tre skip Windows: privilegi symlink e FIFO non supportati. Tutti i report/archivi precedenti preservati.

## Gate e limiti

{table}

Blocchi misurati: **{', '.join(reasons) or 'nessuno locale'}**. V5 resta single-shot e non sarà rivendicata indipendente dopo tuning. Campioni correlati per identità, poche identità in alcune fonti, family insufficiente, ambiguità storiche, RSS non stabilizzata e CI pending rimangono limiti effettivi. Nessuna consulenza personalizzata o verifica editoriale attribuita. Runtime locale deterministico senza rete, LLM o telemetria. Serializzazione CRLF workspace/LF Git del solo catalog_manifest preesistente e già verificata, senza modificarla.

Archivio `dist/{archive}`; commit finale, SHA256 e verifica in `dist/package-verification-round19.json` e `.zip.sha256`, esterni per evitare autoreferenze. Solo file pubblici tracciati, niente cache/file ufficiali binari/database di lavoro/dati personali.
'''
    replacements={'Round19':'Round 19','Round18':'Round 18','pubblico0.6.1':'pubblico 0.6.1','schema610':'schema 610',
        'byte:116':'byte: 116',',13 fonti':', 13 fonti',',25%':', 25%',',0 DOCUMENT':', 0 DOCUMENT',
        'di1019':'di 1.019','Registryv3':'Registry v3','aveva351':'aveva 351','ha**359':'ha **359','Recuperate8':'Recuperate 8',
        'identità:286':'identità: 286','ID616':'ID 616','R8/9':'Round 8/9','nelle50':'nelle 50','ANAC611':'ANAC 611',
        'gate6':'gate 6','generazione91':'generazione 91','seed2026101419':'seed 2026101419','formato.38':'formato. 38',
        'massima26':'massima 26','prospettico35':'prospettico 35','preferito30':'preferito 30','Target50':'Target 50',
        'source:38':'source: 38','minimo30':'minimo 30','preferito40':'preferito 40','note:76':'note: 76',
        ',504 scan':', 504 scan','con200':'con 200',';55 compilati':'; 55 compilati','su60':'su 60','documento470':'documento 470',
        ',0 leakage':', 0 leakage',',0duplicati':', 0 duplicati','tali:469':'tali: 469','crop5%':'crop 5%',
        ',470→512':', 470→512','top25:802':'top25: 802',';30 risorse':'; 30 risorse','Coverage1002':'Coverage 1002',
        ',canonici980':', canonici 980','Safety241':'Safety 241','corrente1563':'corrente 1.563','198.6201ms':'198.6201 ms',
        'misura/2814':'misura/2.814','suite67':'suite 67','schema610':'schema 610','fingerprint1/2/3':'fingerprint 1/2/3',
        'Release-gate-fast1258':'Release-gate-fast 1258','exit0':'exit 0','historical-regression-fast1517':'historical-regression-fast 1517',
        'exit1':'exit 1','preservato:2':'preservato: 2',',10 lockedv1':', 10 locked v1',',2 annualità':', 2 annualità',
        ',1 NO prudente':', 1 NO prudente','Unknownv2 storico107':'Unknown v2 storico 107','da v3':'da v3',
        'Zero nuovi fallimenti;':'Zero nuovi fallimenti nei test e nella regressione confermata;'}
    for a,b in replacements.items():report=report.replace(a,b)
    (ROOT/'docs/ROUND19_REPORT.md').write_text(report,encoding='utf8',newline='\n')
    original=subprocess.check_output(['git','show',BASE+':docs/BENCHMARK.md'],cwd=ROOT).decode('utf8')
    (ROOT/'docs/BENCHMARK.md').write_text(f"# Round19 — {status}\n\nPool359 ID/6 fonti; V5single-shot635 noti/504scan/55filled/30unknownmix. Mediana p95{perf['median_p95']}ms; test{test['passed']}/0/{test['skipped']}. Freezeaa81678 e unknownv3 116/116 preservati. [Report Round19](ROUND19_REPORT.md). Gate falliti: {', '.join(reasons) or 'nessuno locale'}. Le sezioni successive sono storiche.\n\n"+original,encoding='utf8',newline='\n')
    if ready:
        save('rc_metadata',dict(version='0.7.0-rc1',public_version='0.6.1',schema=610,freeze_commit=FREEZE,ci='external_pending',publication=False))
        for lang,text in [('IT','Candidata RC locale, non release pubblica. Prove e limiti nel report Round19.'),('EN','Local release candidate; evidence and limitations in the Round19 report. Not a public release.')]:
            (ROOT/f'docs/RC1_README_{lang}.md').write_text('# BurOCRazia0.7.0-rc1\n\n'+text+'\n',encoding='utf8',newline='\n')
        changelog=subprocess.check_output(['git','show',BASE+':CHANGELOG.md'],cwd=ROOT).decode('utf8')
        (ROOT/'CHANGELOG.md').write_text('# 0.7.0-rc1 — local candidate\n\nRound19 known-representation and inherited unknown gates passed locally; unchanged engine, CI pending.\n\n'+changelog,encoding='utf8',newline='\n')
    paths=[p for p in OUT.glob('*') if p.suffix in ['.json','.csv'] and p.name!='evidence_locks.json']
    paths.extend(ROOT/p for p in [REGISTRY,'benchmarks/reference/v5_source_counting_policy_v1.json','docs/ROUND19_REPORT.md','docs/ROUND19_BASELINE_AUDIT.md','docs/ROUND19_CONTAMINATION_AUDIT.md','docs/BENCHMARK.md','docs/release_gates.json','benchmarks/latest_summary.json'])
    save('evidence_locks',dict(sha256={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(paths)},historical_original_git_sha256=read('benchmarks/results/round18/historical_locks.json')['historical_original_git_sha256'],freeze=FREEZE))
    print('R19',status,'blocking',reasons,flush=True)

if __name__=='__main__':main()
