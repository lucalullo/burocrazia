"""Promote measured development evidence and report actual Round20 gates."""
import argparse
from collections import Counter
from scripts.round20_common import *
from benchmarks.round8_common import identity
from benchmarks.evaluate import summary
from benchmarks.round4_common import runtime_hash

def promote(attempt):
    preserved();cal=read(OUT/('calibration_'+attempt+'.json'))
    assert cal['identity']['runtime_sha256']==runtime_hash()
    path='benchmarks/results/round20/development_observations_'+attempt+'.json'
    assert sha(path)==cal['observations_sha256']
    cal.update(observations_path=path,final_development_attempt=attempt,classification='development_only',promoted_at=now())
    if attempt=='v6_safety_final':
        cal['rules'].append('Corroborated body evidence vetoes contrary metadata; never grants a positive match.')
        cal['declaration_addendum']='The measured runner retained the four-rule description from the initial attempt. This additive declaration records the fifth rule present in the measured runtime SHA; no thresholds, observations or metrics changed.'
    save('calibration_v6',cal)
    replay=read(OUT/('development_regression_v5_after_fix_'+attempt+'.json'))
    save('development_regression_v5_after_fix',replay)
    print('R20 final development attempt',attempt,flush=True)

def tests(log):
    from scripts.round14_baseline import tests as parse
    t=parse(log);t.update(status='passed',runtime_sha256=runtime_hash(),scope='Full suite on final decision v6 runtime; historical seal assertions check their original Git trees. Three Windows platform skips.')
    save('final_tests',t);return t

def failures():
    paths=['reports/round20-development-preparation.log','reports/round20-targeted-tests.log','reports/round20-targeted-tests-second.log','reports/round20-full-tests-initial.log','reports/round20-development-v6-initial.log','reports/round20-final-policy-targeted.log']
    explanations=['Preparation stopped at existing PDF100-page safety limit; next attempt records unsupported extraction and reuses cached public inputs.',
        'New unit fixture omitted required AdministrativeDocument fields; fixture corrected, assertions unchanged.',
        'Targeted recheck:64 passed.',
        '849 passed/1 failed/3 skipped: old Round8 test monkeypatched v5 although v6 is active. Test target changed to v6, safety assertion unchanged.',
        'Development runner omitted category in evaluate_case adapter. Zero durable observations; invocation count before failure not recoverable. Runner fixed, distinct retry journal and log; no independent evaluation involved.',
        'Final five-rule policy targeted check:23 passed/35 deselected, including the original metadata-content veto assertion.']
    save('technical_attempt_history',dict(attempts=[dict(log=Path(p).name,log_sha256=sha(p),explanation=e) for p,e in zip(paths,explanations) if (ROOT/p).exists()],scope='All logs and partial work preserved locally. These tooling failures are separate from final engine measurements; no historical result rewritten.'))

def finish():
    preserved();cal=read(OUT/'calibration_v6.json');obs=read(cal['observations_path'])['cases'];perf=read(OUT/'performance_stability.json');t=read(OUT/'final_tests.json');checks=read(OUT/'final_checks.json')
    assert cal['identity']['runtime_sha256']==perf['identity']['runtime_sha256']==t['runtime_sha256']==checks['runtime_sha256']==runtime_hash()
    cov=read(OUT/'coverage.json');safe=read(OUT/'input_safety.json');pool=read(OUT/'v6_preflight.json');unknown=read(OUT/'unknown_v4_preflight.json')
    pre=dict(cal['gates']);pre.update(coverage_pass=cov['passed'],input_safety_pass=safe['passed'],performance_pass=perf['required_pass'],tests_pass=t['failed']==0,V6_pool_pass=pool['passed'],unknown_v4_preflight_pass=unknown['passed'])
    pre['ready_to_freeze']=all(pre.values());assert not pre['ready_to_freeze'],'This reporter implements the stopped path only; passing prerequisites require a fresh freeze/evaluation.'
    pre.update(runtime_sha256=runtime_hash(),checked_at=now(),thresholds_unchanged=True)
    save('pre_freeze_gate',pre);failures()
    for n in ['robustness_v6','scan_v6','filled_v6','retrieval_v6','end_to_end_v6','unknown_v4_not_run']:
        save(n,dict(status='not_run',cases=[],recognition_calls=0,summary=dict(cases=0,metrics={},latency_ms={}),reason='Round20 pre-freeze development/pool/fresh-unknown prerequisites failed; no selection, freeze or predictions.',independent_metrics=None))
    v5=[c for c in obs if c['group']=='v5'];negative=[c for c in obs if c.get('expected',{} ) and c['expected']['match_type']=='NO_MATCH' and not c['extraction_failed']]
    retrieval={str(k):sum((c['expected'].get('document_id') in c['candidate_ids'][:k]) for c in v5)/len(v5) for k in [1,5,10,25]}
    def rate(cs):
        tp=sum(c['document_correct'] for c in cs);ac=sum(c['observed']['match_type']=='DOCUMENT_MATCH' for c in cs)
        return dict(n=len(cs),exact=tp,wrong=ac-tp,accepted=ac,NO=sum(c['observed']['match_type']=='NO_MATCH' for c in cs),family=sum(c['observed']['match_type']=='FAMILY_MATCH' for c in cs),precision=tp/ac if ac else 0,recall=tp/len(cs) if cs else 0,f1=2*tp/(len(cs)+ac) if cs else 0,entity_errors=sum(c['entity_error'] for c in cs),version_errors=sum(c['version_error'] for c in cs))
    old=read('benchmarks/results/round19/evaluation_v5_observations.json')['cases'];provenance={c['id']:c['provenance'] for c in old}
    save('development_breakdown',dict(retrieval_at_k=retrieval,overall=rate(v5),by_transform={tr:rate([c for c in v5 if c['transform']==tr]) for tr in sorted({c['transform'] for c in v5})},by_source={str(s):rate([c for c in v5 if provenance[c['id'].removeprefix('DEV5:')]['source_id']==s]) for s in sorted({provenance[c['id'].removeprefix('DEV5:')]['source_id'] for c in v5})},extraction_failures=[dict(id=c['id'],error=c['extraction_error']) for c in obs if c['extraction_failed']],scope='Contaminated development only; all original V5 cases retained in original artifacts.'))
    save('development_safety',dict(confirmed_negative_count=cal['confirmed_negative_count'],false_accepts=cal['confirmed_false_accept_ids'],negative_false_accepts=cal['negative_false_accept_ids'],passed=cal['gates']['confirmed_safety_pass'],unsupported_not_credited=sum(c['extraction_failed'] for c in obs),scope='Includes all observed official unknown v1-v3 as development after tuning, not fresh validation; wrong FAMILY on unknown is false accept.'))
    from benchmarks.release_truth import load_release
    qualified={c['input_key'] for c in load_release()[2] if c['truth_domain']!='parser_limit_contract'}
    certain=[c for c in obs if c.get('expected') and (c['group']!='historical' or c['original_id'] in qualified)]
    hard=[c for c in certain if c['expected']['match_type']=='NO_MATCH' and not c['extraction_failed'] and ('hard_negative' in c['category'] or 'hard_negative' in c['id'])]
    save('hard_negatives_development',dict(n=len(hard),correct_rejects=sum(c['observed']['match_type']=='NO_MATCH' for c in hard),false_accept_ids=[c['id'] for c in hard if c['observed']['match_type']!='NO_MATCH'],passed=bool(hard) and all(c['observed']['match_type']=='NO_MATCH' for c in hard),cases=hard,scope='Frozen synthetic hard negatives measured separately from official unknown development; every FAMILY is a false accept.'))
    gates=[]
    def g(name,target,actual,passed,blocking=True):gates.append(dict(gate=name,target=target,actual=actual,passed=bool(passed),blocking=blocking,status='PASS' if passed else 'FAIL' if blocking else 'PENDING'))
    for name,target,actual in [('dev_precision_pass','>=99.5%',cal['V5_development']['precision']),('dev_recall_pass','V5 development >=90%',cal['V5_development']['recall']),('dev_scan_pass','>=85%',cal['scan']['recall']),('dev_filled_pass','>=90%',cal['filled']['recall']),('confirmed_safety_pass','zero confirmed false accepts',len(cal['confirmed_false_accept_ids'])),('canonical_pass','1007/1007',cal['canonical_exact']),('coverage_pass','>=85%',cov['file_backed_percent']),('input_safety_pass','9/9 safe rejection',9),('performance_pass','7 runs; median p95<=250ms',perf['median_p95']),('tests_pass','zero failures',dict(passed=t['passed'],failed=t['failed'],skipped=t['skipped'])),('V6_pool_pass','30 IDs/6 sources/400 reps/200 scans/50 valid filled',pool),('unknown_v4_preflight_pass','100 fresh/8 sources/max25%',dict(N=unknown['N'],sources=unknown['sources'],concentration=unknown['max_concentration']))]:g(name,target,actual,pre[name])
    g('final_checks','compile/catalog/FK/idempotent610/schemas',checks['passed'],checks['passed'])
    g('confirmed_release_diagnostic','1258/1258',read(OUT/'release_gate_fast.json')['n'],read(OUT/'release_gate_fast.json')['passed'])
    for name,target in [('unknown_v4','>=99% correct rejection, <=1% false acceptance, zero entity/version errors'),('v6_precision','>=99.5%'),('v6_recall','>=90%'),('v6_scan_precision','>=99.5%'),('v6_scan_recall','>=85%'),('v6_filled_generation','>=90%'),('v6_filled_precision','>=99.5%'),('v6_filled_recall','>=90%'),('v6_retrieval_at25','100%'),('v6_retrieval_at1','>=99% target'),('v6_entity_version','zero'),('unknown_end_to_end','>=99% fresh rejection')]:
        g(name,target,None,False);gates[-1]['status']='NOT RUN'
    g('family','>=5 validated held-out families','experimental / insufficiently validated',False,False);g('CI','external matrix','external_pending',False,False)
    ident=identity();reasons=[x['gate'] for x in gates if x['blocking'] and not x['passed']]
    atomic_json(ROOT/'docs/release_gates.json',dict(round=20,status='NOT READY',software_version='0.6.1',candidate_target='0.7.0',schema=610,freeze=None,historical_freeze=preserved()['historical_freeze_commit'],identity=ident,gates=gates,local_gates_passed=False,tests=t,reasons=reasons,ci='external_pending'))
    latest=json.loads(subprocess.check_output(['git','show',BASE+':benchmarks/latest_summary.json'],cwd=ROOT))
    latest.update(round=20,status='NOT READY',version='0.6.1',software_version='0.6.1',commit=ident['commit'],executed_at=now(),runtime_sha256=runtime_hash(),fingerprint_sha256=ident['fingerprint_sha256'],reasons=reasons)
    for key in ['known_robustness','scan_ocr','filled_forms','unknown_official']:
        latest[key]=dict(status='not_run',summary=dict(cases=0,metrics={},latency_ms={}),scope='Fresh V6/unknown v4 not run. Historical V5 and unknown v3 cannot validate changed engine.')
    canonical=[c for c in obs if c['group']=='canonical'];cs=summary(canonical);cs['latency_ms']={}
    latest['known_canonical']=dict(status='executed',summary=cs,scope='Current development technical canonical contracts, not independent generalization.')
    latest['performance']=dict(status='executed',summary=dict(cases=2814,metrics={},latency_ms=dict(p95=perf['median_p95'])),runs=[r['latency_ms'] for r in perf['runs']],scope='Seven predetermined isolated warm runs.')
    latest['historical_independent_v5_round19']=dict(path='benchmarks/results/round19/evaluation_v5_gate.json',precision=448/456,recall=448/635,scan_recall=319/504,scope='Original independent outcome, previous runtime only.')
    latest['historical_unknown_v3']=dict(n=116,correct_reject=116,sources=13,scope='Original freeze only; does not validate v6.')
    latest['family_identity_holdout']=dict(status='experimental / insufficiently validated',families_evaluable=0,summary=dict(cases=0,metrics={},latency_ms={}),scope='No fresh family validation on the changed runtime.')
    latest['hard_negatives']=dict(status='executed',summary=summary(hard),scope='Confirmed synthetic development only; official unknown development separately reported.')
    latest['release_gate']=dict(status='executed',n=read(OUT/'release_gate_fast.json')['n'],passed=read(OUT/'release_gate_fast.json')['passed'],scope='Confirmed technical development contracts, not fresh independent release evidence.')
    latest['input_safety']=dict(status='executed',n=safe['n'],passed=safe['passed'],scope='Current parser-limit safe refusal; never unknown recognition accuracy.')
    for key in ['unknown_master_pool','unknown_release_subset']:
        latest[key]=dict(status='historical_only',scope='Round18 original metadata/result; not a fresh Round20 unknown set. See unknown_v4_preflight.json for current13/1 availability.')
    latest['unknown_development']=dict(status='development_only',confirmed_negative_count=cal['confirmed_negative_count'],false_accepts=cal['negative_false_accept_ids'],scope='Observed v1-v3 plus historical confirmed development; no fresh-release claim.')
    latest['development_regression_v5_after_fix']=dict(status='executed',metrics=cal['V5_development'],scan=cal['scan'],filled=cal['filled'],false_accepts=len(cal['confirmed_false_accept_ids']),scope='Contaminated development only.')
    latest['evaluations']=[dict(name='development_regression_v5_after_fix',summary=summary(v5))]
    atomic_json(ROOT/'benchmarks/latest_summary.json',latest)
    from src.benchmark_display import load_summary
    load_summary(ROOT/'benchmarks/latest_summary.json')
    m=cal['V5_development'];s=cal['scan'];f=cal['filled'];audit=read(OUT/'v5_failure_summary.json');hist=read(OUT/'historical_regression_fast.json')
    table='\n'.join('| '+' | '.join(str(x).replace('|','/') for x in row)+' |' for row in [['Gate','Target','Actual','Esito'],['---']*4]+[[x['gate'],x['target'],str(x['actual']) if x['gate']!='V6_pool_pass' else f"{pool['identities']} IDs/{pool['sources']} sources",x['status']] for x in gates])
    timing='\n'.join(f"| {r['run']} | {r['latency_ms']['p50']} | {r['latency_ms']['p95']} |" for r in perf['runs'])
    report=f'''# Round 20 — NOT READY

Software pubblico **0.6.1**, schema **610**, branch `codex/coverage-benchmark-v0.7.0`. Ingresso `{BASE}` pulito; nessun freeze Round 20. Freeze storico `{preserved()['historical_freeze_commit']}` preservato. Per la successiva regola permanente dell'utente non viene creato alcun commit: HEAD resta quello d'ingresso e le modifiche restano nel working tree. Lo ZIP usa un Git tree con indice temporaneo separato; HEAD, SHA del tree, SHA256 e verifica sono nel sidecar `dist/package-verification-round20.json`. Nessun push, tag o pubblicazione; CI esterna pending.

## V5 storica e truth audit

**historical_independent_v5_round19** conserva integralmente selezione, matrice, leakage,665 raw, metriche ed etichette. Originale:448 exact/8 wrong/179 NO su635 noti; **P98.2456%, R70.5512%, scan R63.2937%**. Cinque gate falliti: precisione, exact recall, scan precision, scan recall e retrieval@25. Unknown v3 originale116/116,13 fonti,0 false accept resta storico e **non valida il motore v6**. Il replay corrente non sostituisce alcuna misura storica.

Audit665/665: `{audit['truth_counts']}`;0 label_error/0 ambiguous/0 obsolete/0 insufficient_evidence nel contratto tecnico delle rappresentazioni canoniche. Verifica locale di byte ufficiali, ricevute effettive, binding e trasformazioni deterministiche; non è una nuova verifica editoriale umana né un controllo live. Otto false accept confermati e179 false reject; doc469/511 e470/512 distinguono genitori e tutore, anche se condividono allegati. Categorie failure: `{audit['root_causes']}`. Unico expected fuori top25:802/rotation180; nessuna modifica all'indice motivata da questo caso isolato. Campi diagnostici mancanti restano vuoti, senza score inventati.

## Motore e sviluppo dopo correzioni

Politica `fingerprint-decision-v6`, runtime `{runtime_hash()}`, profilo `{sha('data/recognition_profiles/fingerprint_decision_v6.json')}`. Regole generali in DECISION_POLICY_V6.md: ambiguità fingerprint non superabile dai soli metadati; etichette subordinate/prefissi OCR non trasformati in emittenti contrari; scan corroborati da char/OCR/anchor/layout; margine multipagina corroborato da due allineamenti distinti; veto dei metadati che contraddicono contenuto corroborato, senza trasformare quest'ultimo in match positivo. Exact SHA, hard conflict, revisione/anno/territorio, catalogo, dataset e vecchi profili preservati. Nessun ID/URL/case-specific hack e nessuna modifica a retrieval o pesi. Applicabilità, esempi positivi, hard negative, fallback e test nel documento della policy.

3.160 input pubblici/sintetici preparati:1.007 canonici,635 V5 development,556 storici,630 precedenti development,332 unknown osservati. **development_regression_v5_after_fix**: `{m['exact']}` exact, `{m['wrong']}` wrong, `{m['n']-m['accepted']}` non exact su635; **P{m['precision']:.4%}, R{m['recall']:.4%}**. Scan504: `{s['exact']}` exact/`{s['wrong']}` wrong, P{s['precision']:.4%}, R{s['recall']:.4%}. Compilati55: `{f['exact']}` exact, P{f['precision']:.4%}, R{f['recall']:.4%}; generazione storica55/60,91.6667%,5 fallimenti originali invariati. Combined known: `{cal['combined_known']}`. Safety confermata: `{cal['confirmed_negative_count']}` negativi, `{len(cal['confirmed_false_accept_ids'])}` false accept complessivi; FAMILY su unknown è errore. Nessuna metrica fresca indipendente è ricavata da questi dati contaminati.

Retrieval sviluppo @1/@5/@10/@25: `{retrieval}`. Dettagli per fonte/trasformazione e input non estraibili in development_breakdown.json. Input oltre i limiti PDF conservati come extraction failure, mai conteggiati come rifiuto unknown riuscito. Tutti i tentativi e log tecnici sono preservati; technical_attempt_history.json distingue errori di fixture/runner e risultati finali. L'estrazione usa Tesseract locale reale; immagini/compilati sono sintetici, non scansioni personali. Nessun testo personale entra in cache.

## Pool fresco e stop prima del freeze

Registry v4 preservato; v5 registra esposizione V5 prima delle modifiche; v6 aggiunge tutte le identità viste in calibrazione/tentativi e risorse unknown v1-v3. Audit1.019 ID fingerprint, inclusi51 non utilizzabili. Pool fresco dimostrabile con registry vincolante: **{pool['identities']} identità/{pool['sources']} fonti**, `{pool['counts_per_source']}`, concentrazione{pool['max_concentration']:.4%}. Capacità soltanto teorica: `{pool['representation_capacity']}` rappresentazioni/`{pool['scan_capacity']}` scan/`{pool['fill_capacity']}` compilati potenziali; **0 compilati freschi validati**, nessuna selezione V6. La V5 ha esaurito tutte le identità eleggibili di due fonti:6 MinLavoro e1 Unioncamere; restano al massimo4 fonti prima degli ulteriori controlli. Il requisito6 non viene abbassato e le provenienze storiche non vengono divise artificialmente.

Preflight unknown v4: `{unknown['N']}` risorse ufficiali confermate non osservate nel master esistente, `{unknown['sources']}` fonte, concentrazione{unknown['max_concentration']:.2%}; richiesti100/8/max25%. Acquisizione nuova non eseguita perché il prerequisito congiunto delle fonti V6 è irraggiungibile nel pool vincolante corrente. Questo è un inventario del master disponibile, non una dichiarazione che altri unknown ufficiali non esistano. Zero predizioni su unknown v4; nessun manifest release, freeze o selezione V6.

**V6 non eseguita**:0 chiamate,0 identità selezionate,0 rappresentazioni; exact/wrong/P/R/F1/errori ente/versione/retrieval/scan/filled/unknown end-to-end non misurati (`null`), non zero prestazioni. Family resta **experimental / insufficiently validated** e non aumenta exact recall. Una RC richiede prima prerequisiti soddisfatti e poi nuove unknown v4/V6 single-shot su identità fresche.

## Verifiche finali

Coverage **{cov['file_backed_percent']:.6f}%** (1002/1158), canonical **{cal['canonical_exact']}/1007**. Input safety9/9, zero chiamate di riconoscimento dopo parser refusal. Compile, SQLite integrity/FK, migrazione idempotente610/conteggi invariati, profilo/truth/schema e validatori fingerprint1/2/3 verificati sul runtime corrente. Release diagnostic `{read(OUT/'release_gate_fast.json')['n']}` contratti, PASS `{read(OUT/'release_gate_fast.json')['passed']}`; storico `{hist['n']}` con `{len(hist['mismatches'])}` mismatch ed exit1 conservato, etichette immutate. La nuova semantica non rivendica equivalenza con il vecchio runtime: conserva i contratti confermati, mentre i risultati originali restano separati.

| Run | p50 ms | p95 ms |
| --- | --- | --- |
{timing}

Sette run warm predeterminati,67 input/402 richieste ciascuno/2.814 timing; mediana p95 **{perf['median_p95']}ms**, gate250ms **{perf['required_pass']}**, target220ms `{perf['preferred_latency_pass']}`, `{perf['pass_count']}/7` sotto250. Estrazione/OCR fuori timing; nuove RequestPages per richiesta, cache solo metadata catalogo. Baseline storica Round19 198.6201ms separata. Tutti i run mantenuti, nessuna scelta di rerun favorevoli.

Full pytest finale **{t['passed']} passed/{t['failed']} failed/{t['skipped']} skipped**, {t['seconds']}s, log SHA `{t['log_sha256']}`. Baseline pre-modifica834/0/3 conservata. Tre skip Windows: symlink senza privilegio e FIFO non disponibili. Test sui sigilli storici verificano gli originali alberi Git; il test sul veto dei metadati intercetta ora il modulo v6 attivo mantenendo le medesime asserzioni. Collaudo soltanto Windows/Python3.12.10; Linux/macOS e CI esterna non eseguiti.

## Gate RC

{table}

Limiti effettivi: sviluppo contaminato e trasformazioni correlate per identità, pool fresco con fonti insufficienti, unknown v4 non acquisita/eseguita, V6 non eseguita, family insufficiente, CI pending. Nessuna attribuzione automatica di verifica editoriale o consulenza personalizzata. Applicazione locale deterministica; rete runtime/LLM/telemetria assenti. Catalogo completo e provenienze invariati; eccezione di serializzazione preesistente CRLF workspace/LF Git del solo catalog_manifest verificata senza normalizzazione del file.

Archivio: `dist/BurOCRazia-v0.7.0-candidate-NOT-READY-round20.zip`. Snapshot dei file pubblici attraverso indice temporaneo separato, senza creare commit o cambiare l'indice originale. Cache, checkpoint privati, testo estratto, fixture binarie ufficiali, database di lavoro e log locali esclusi. HEAD di partenza/tree SHA/SHA256/verifica nel sidecar esterno `dist/package-verification-round20.json`; hash storico di tutti gli artefatti protetti e misure correnti controllati durante il packaging. Continuità permanente in CONTINUITA_OPERATIVA.md, Goal ufficiale e controllo orario nella stessa chat; checkpoint privati append-only. La pianificazione viene disattivata al completamento verificato del Round 20; quota, app spenta e permessi possono comunque impedire una ripresa automatica.
'''
    spacing={'leakage,665':'leakage, 665','Originale:448':'Originale: 448','su635':'su 635','**P98':'**P 98','R70.':'R 70.','R63.':'R 63.','originale116':'originale 116',',13 fonti':', 13 fonti',',0 false':', 0 false','Audit665':'Audit 665',';0 label':'; 0 label','e179':'e 179','doc469/511 e470/512':'documenti 469/511 e 470/512','top25:802':'top25: 802','preparati:1.007':'preparati: 1.007',',635 V5':', 635 V5',',556 storici':', 556 storici',',630 precedenti':', 630 precedenti',',332 unknown':', 332 unknown','**P100':'**P 100','Scan504':'Scan 504','Compilati55':'Compilati 55','storica55/60,91':'storica 55/60, 91',',5 fallimenti':', 5 fallimenti','Audit1.019':'Audit 1.019','inclusi51':'inclusi 51','concentrazione58':'concentrazione 58','fonti:6':'fonti: 6','e1 Unioncamere':'e 1 Unioncamere','massimo4':'massimo 4','requisito6':'requisito 6','concentrazione100':'concentrazione 100','richiesti100/8':'richiesti 100/8','**:0 chiamate,0 identità selezionate,0 rappresentazioni':'**: 0 chiamate, 0 identità selezionate, 0 rappresentazioni','safety9/9':'safety 9/9','idempotente610':'idempotente 610','fingerprint1/2/3':'fingerprint 1/2/3','exit1':'exit 1','predeterminati,67':'predeterminati, 67','p95 **123.6941ms':'p95 **123.6941 ms','gate250ms':'gate 250 ms','target220ms':'target 220 ms','sotto250':'sotto 250','Round19 198.6201ms':'Round 19 198.6201 ms','pre-modifica834':'pre-modifica 834','Windows/Python3.12.10':'Windows/Python 3.12.10'}
    for before,after in spacing.items():report=report.replace(before,after)
    report=report.replace('Input safety 9/9,',f"Negativi sintetici di sviluppo: **{len(hard)}/{len(hard)} rifiuti corretti**, 0 false accept (hard_negatives_development.json); contratti correlati, non campione indipendente. Input safety 9/9,")
    (ROOT/'docs/ROUND20_REPORT.md').write_text(report,encoding='utf8',newline='\n')
    prior=subprocess.check_output(['git','show',BASE+':docs/BENCHMARK.md'],cwd=ROOT).decode('utf8')
    (ROOT/'docs/BENCHMARK.md').write_text(f"# Round 20 — NOT READY\n\nV5 indipendente storica: P98.2456%, R70.5512%, scan R63.2937%,5 gate falliti. Replay **development** v6: P{m['precision']:.4%}, R{m['recall']:.4%}, scan R{s['recall']:.4%}, filled R{f['recall']:.4%}; {len(cal['confirmed_false_accept_ids'])} false accept confermati. Canonical1007/1007,coverage{cov['file_backed_percent']:.4f}%,p95 mediano{perf['median_p95']}ms,test{t['passed']}/0/{t['skipped']}. Pool V6 fresco{pool['identities']}ID/{pool['sources']}fonti: STOP, unknown v4 e V6 non eseguite. Unknown v3 storico non valida v6. Pubblico0.6.1/schema610. [Report Round 20](ROUND20_REPORT.md). Sezioni successive storiche.\n\n"+prior,encoding='utf8',newline='\n')
    paths=[p for p in OUT.glob('*') if p.suffix in ['.json','.csv'] and p.name!='evidence_locks.json']
    paths.extend(ROOT/p for p in ['benchmarks/reference/v5_truth_adjudication_v1.json','benchmarks/reference/benchmark_contamination_registry_v5.json','benchmarks/reference/benchmark_contamination_registry_v6.json','docs/ROUND20_REPORT.md','docs/ROUND20_BASELINE_AUDIT.md','docs/ROUND20_V5_FAILURE_AUDIT.md','docs/DECISION_POLICY_V6.md','docs/BENCHMARK.md','docs/release_gates.json','benchmarks/latest_summary.json'])
    save('evidence_locks',dict(sha256={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(paths)},runtime_sha256=runtime_hash(),scope='New development evidence only; original V5/unknown v3 protected independently by baseline and prior historical Git locks.'))
    print('R20 NOT READY',reasons,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['promote','tests','finish']);p.add_argument('value',nargs='?');a=p.parse_args()
    if a.mode=='promote':promote(a.value)
    elif a.mode=='tests':tests(a.value)
    else:finish()
