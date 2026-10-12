"""Aggregate frozen observations without recognition or post-evaluation tuning."""
import csv,hashlib,json,platform,re,subprocess,sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from benchmarks.round8_common import read,write,catalog,OUT,checked,identity
from benchmarks.evaluate import summary,quantile
from src.recognize import catalog_revision

def metric(r,key):return r['summary']['metrics'][key]['value']
def display(v):return 'non misurato' if v is None else f'{v:.2%}'
def table(rows):return '\n'.join('| '+' | '.join(str(x).replace('|','/') for x in row)+' |' for row in rows)
def preface(path,body):
    p=ROOT/path;s=p.read_text(encoding='utf8');marker='<!-- round8-current -->'
    if marker in s:s=s[s.index('<!-- /round8-current -->')+len('<!-- /round8-current -->'):].lstrip()
    p.write_bytes((marker+'\n'+body+'\n<!-- /round8-current -->\n\n'+s).encode())

def main():
    frozen=checked();docs,families=catalog();names=['canonical','robustness_v4','scan_v4','filled_v4','unknown_v4','family_release','performance','fingerprint_coverage','calibration_v4','ci_local','reconciled_truth']
    data={n:read(OUT+n+'.json') for n in names};can,rob,scan,filled,unknown,fam,perf,cov,cal,ci,reconciled=[data[n] for n in names]
    for name in ['canonical','robustness_v4','scan_v4','filled_v4','unknown_v4']:assert summary(data[name]['cases'])['metrics']==data[name]['summary']['metrics'],name
    log=(ROOT/'reports/round8-full-final-tests.log').read_bytes();m=re.search(r'(\d+) passed, (\d+) skipped in ([\d.]+)s',log.decode('utf8',errors='replace'));assert m and not re.search(rb'\b[1-9]\d* failed\b',log)
    tests=dict(passed=int(m[1]),skipped=int(m[2]),failed=0,seconds=float(m[3]),log_sha256=hashlib.sha256(log).hexdigest(),platform=platform.platform(),python=platform.python_version())
    post=ROOT/'reports/round8-post-report-tests.log'
    if post.exists():
        raw=post.read_bytes();pm=re.search(rb'(\d+) passed in ([\d.]+)s',raw);assert pm and not re.search(rb'\b[1-9]\d* failed\b',raw)
        tests['post_report_checks']=dict(passed=int(pm[1]),failed=0,seconds=float(pm[2]),log_sha256=hashlib.sha256(raw).hexdigest(),scope='Targeted UI/static-summary checks after reporting; not additional distinct tests.')
    write(OUT+'tests.json',tests)
    historical={p.stem.removeprefix('historical_'):read(p.relative_to(ROOT)) for p in (ROOT/OUT).glob('historical_*.json') if p.stem!='historical_five'}
    five=read(OUT+'historical_five.json');ocr=read(OUT+'ocr_legacy_gate.json');ocr2=read(OUT+'ocr_synthetic_v2.json');truth=read('benchmarks/reference/reference_truth_v1.json');prepared=read(OUT+'evaluation_prepared.json');plan=rob['plan'];shared=read(OUT+'shared_resource_audit.json');resource_lookup=read(OUT+'canonical_resource_lookup.json')
    generation=[r for r in prepared['generation_audit'] if '-filled_' in r['case_id']];success=sum(r['generated'] and r['reopened'] and r['synthetic_verified'] for r in generation);genrate=success/len(generation) if generation else 0
    completion=rob.get('completion',dict(complete=True));evaluation_complete=bool(completion['complete']) and len(rob['cases'])==len(prepared['representations'])
    evaluated_ids={r['expected']['document_id'] for r in rob['cases']}
    evaluated_id_sources={r['expected']['document_id']:str(r['provenance']['source_id']) for r in rob['cases']};evaluated_sources=Counter(evaluated_id_sources.values())
    evaluated_concentration=max(evaluated_sources.values())/len(evaluated_ids) if evaluated_ids else None
    gates=[]
    def gate(name,target,actual,passed,blocking=True):gates.append(dict(gate=name,target=target,actual=actual,passed=bool(passed),blocking=blocking))
    gate('truth_classified','0 unclassified',truth['unclassified_contradictions'],truth['unclassified_contradictions']==0)
    gate('canonical_resource_lookup','100% bytes lookup',resource_lookup['matched_bindings'],resource_lookup['matched_bindings']==resource_lookup['bindings'])
    gate('reconciled_confirmed_truth','all confirmed correct',reconciled['summary']['passed'],reconciled['summary']['failed']==0)
    gate('coverage_file_backed','>=85%',cov['coverage_file_backed'],cov['coverage_file_backed']>=.85);gate('coverage_all','>=70%',cov['coverage_all'],cov['coverage_all']>=.70)
    gate('evaluation_complete','all prepared observations persisted',dict(prepared=len(prepared['representations']),persisted=len(rob['cases']),complete=evaluation_complete),evaluation_complete)
    gate('evaluation_identities','>=25, target40',len(evaluated_ids),len(evaluated_ids)>=25);gate('evaluation_sources','>=5, target8',len(evaluated_sources),len(evaluated_sources)>=5);gate('source_concentration','<=30%',evaluated_concentration,evaluated_concentration is not None and evaluated_concentration<=.30)
    gate('evaluation_representations','>=350',len(rob['cases']),len(rob['cases'])>=350);gate('scan_representations','>=200',len(scan['cases']),len(scan['cases'])>=200);gate('filled_valid','>=30, target50',len(filled['cases']),len(filled['cases'])>=30)
    for name,r,recall in [('canonical',can,1),('robustness',rob,.90),('scan',scan,.85),('filled',filled,.90)]:
        for key,target in [('document_precision',1 if name=='canonical' else .995),('document_recall',recall)]:
            val=metric(r,key);qualified=name=='canonical' or evaluation_complete
            gate(name+'_'+key,'>='+display(target),val if qualified else dict(partial_observed=val,qualified=False),qualified and val is not None and val>=target)
    wrong_rate=rob['counts']['wrong']/len(rob['cases']) if rob['cases'] else None
    gate('wrong_accepted','<=0.5%',wrong_rate if evaluation_complete else dict(partial_observed=wrong_rate,qualified=False),evaluation_complete and wrong_rate is not None and wrong_rate<=.005)
    for key in ['entity_error_rate','version_year_error_rate']:gate(key,'0',rob['summary']['metrics'][key]['numerator'] if evaluation_complete else dict(partial_numerator=rob['summary']['metrics'][key]['numerator'],qualified=False),evaluation_complete and rob['summary']['metrics'][key]['numerator']==0)
    gate('filled_generation','>=90%',genrate,genrate>=.90)
    gate('unknown_confirmed_main','>=99%, confirmed labels',None,False)
    gate('unknown_historical_rejection','>=99% diagnostic',metric(unknown,'unknown_correct_rejection_rate'),metric(unknown,'unknown_correct_rejection_rate') is not None and metric(unknown,'unknown_correct_rejection_rate')>=.99,False)
    safety=[r for value in historical.values() for r in value['cases'] if r['expected']['match_type']=='NO_MATCH'];fp=[r['id'] for r in safety if r['observed']['match_type']!='NO_MATCH']
    wronghist=[r['id'] for value in historical.values() for r in value['cases'] if r['expected']['match_type']=='DOCUMENT_MATCH' and r['observed']['match_type']=='DOCUMENT_MATCH' and not r['document_correct']]
    gate('historical_safety','zero historical NO false accepts and wrong identities',dict(false_accepts=fp,wrong_identities=wronghist),not fp and not wronghist)
    gate('historical_five','5 safe',sum(r['safe'] for r in five['cases']),five['passed']);r061=next(r for r in historical['release_locked_v2']['cases'] if r['id']=='R061');gate('R061','NO_MATCH',r061['observed']['match_type'],r061['observed']['match_type']=='NO_MATCH')
    gate('real_ocr','7/7 +14/14',dict(legacy=ocr['passed'],synthetic=ocr2['summary']['passed']),ocr['full_gate_passed'] and ocr2['summary']['passed']==14)
    gate('performance_p50','<=150ms',perf['latency_ms']['p50'],perf['latency_ms']['p50']<=150);gate('performance_p95','<=250ms',perf['latency_ms']['p95'],perf['latency_ms']['p95']<=250);gate('index_memory','<=100000000 bytes',perf['index']['bytes'],perf['index']['bytes']<=100000000)
    gate('tests','all green',tests,tests['failed']==0);gate('external_ci','pending -> local RC only','pending_external_gate',False,False)
    if fam['families_evaluable']>=5:gate('family','P>=99%,R>=80%,FP=0',fam['summary']['metrics'],(metric(fam,'family_precision') or 0)>=.99 and (metric(fam,'family_recall') or 0)>=.80 and fam['false_accepts']==0)
    else:gate('family_validation','>=5 evaluable; otherwise exact useful gate',fam['families_evaluable'],False,False)
    passed=all(g['passed'] for g in gates if g['blocking']);status='READY LOCALLY' if passed else 'NOT READY';ident=identity()
    write('docs/release_gates.json',dict(round=8,status=status,software_version='0.6.1',candidate_target='0.7.0',schema=610,identity=ident,freeze=frozen,local_gates_passed=passed,gates=gates,tests=tests,ci='pending_external_gate'))
    evaluation_summaries=[dict(name=n,summary=v['summary']) for n,v in historical.items()]
    latest=dict(schema_version=1,benchmark_model='known-family-unknown-v4',status=status,software_version='0.6.1',candidate_target='0.7.0',catalog_semantic_sha256=catalog_revision(docs,families),release_gate=read('docs/release_gates.json'),fingerprint_coverage=dict(status='executed',**cov),known_canonical=dict(status='executed',summary=can['summary']),known_robustness=dict(status='executed',summary=rob['summary']),scan_ocr=dict(status='executed',summary=scan['summary']),filled_forms=dict(status='executed',summary=filled['summary'],generated=success,attempted=len(generation)),unknown_official=dict(status='executed',summary=unknown['summary'],scope=unknown['scope'],release_gate_status=unknown['release_gate_status']),family_identity_holdout=dict(status='executed',summary=fam['summary'],families_evaluable=fam['families_evaluable'],capability_status=fam['capability_status']),performance=dict(status='executed',latency_ms=perf['latency_ms'],index_bytes=perf['index']['bytes']),ocr_status=f"Tesseract reale {ocr['passed']}/7 + {ocr2['summary']['passed']}/14",evaluations=evaluation_summaries)
    latest.update(executed_at=ident['executed_at'],commit=frozen['commit'],catalog_count=1216,operational_count=1212)
    if fam['families_evaluable']<5:
        for name in ['known_canonical','known_robustness','scan_ocr','filled_forms']:
            section=latest[name];section['summary']=json.loads(json.dumps(section['summary']))
            section['summary']['metrics']['useful_coverage']=dict(section['summary']['metrics']['document_recall'])
            section['useful_coverage_scope']='Exact document recall only; family capability insufficiently validated. Original raw benchmark metrics remain separately preserved.'
    if not evaluation_complete:
        for key,value in [('known_robustness',rob),('scan_ocr',scan),('filled_forms',filled)]:
            section=latest[key];section.update(status='incomplete',completion=completion,partial_summary=section['summary'])
            section['summary']=dict(cases=f"{len(value['cases'])} osservazioni parziali — evaluation INCOMPLETA; metriche principali non disponibili",metrics={},latency_ms={})
            latest['evaluations'].append(dict(name='Evaluation v4 INCOMPLETA — '+key+'; sole righe salvate, non rappresentative',summary=section['partial_summary']))
        latest['evaluation_completion']=completion
    write('benchmarks/latest_summary.json',latest)
    failures=[]
    for r in scan['cases']:
        if r['document_correct']:continue
        diag=r['decision_diagnostics'];candidate=diag.get('expected_candidate',{});rank=r.get('candidate_rank');veto=diag.get('expected_veto') or diag.get('reason_code') or diag.get('tier') or 'not_available'
        cause='extraction failure' if r['extraction_failed'] else 'retrieval failure' if rank is None else 'decision failure'
        failures.append(dict(case_id=r['id'],expected_id=r['expected']['document_id'],expected_rank=rank,candidate_score=candidate.get('score'),OCR_score=candidate.get('ocr'),char_score=candidate.get('chars'),visual_score=candidate.get('visual'),anchors=candidate.get('anchors'),entity_evidence=json.dumps(diag.get('entity_evidence',[])),version_evidence=json.dumps(diag.get('version_evidence',[])),veto=veto,threshold=json.dumps(diag.get('thresholds',{}),sort_keys=True),margin=diag.get('margin'),transform_type=r['representation'],root_cause=cause))
    fields=['case_id','expected_id','expected_rank','candidate_score','OCR_score','char_score','visual_score','anchors','entity_evidence','version_evidence','veto','threshold','margin','transform_type','root_cause']
    with (ROOT/OUT/'scan_failure_decomposition.csv').open('w',newline='',encoding='utf8') as f:w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(failures)
    write(OUT+'scan_failure_decomposition.json',dict(counts=dict(Counter(r['root_cause'] for r in failures)),failures=len(failures),evaluation_complete=evaluation_complete,coverage=dict(persisted=len(scan['cases']),prepared=sum(r['scan_like'] for r in prepared['representations'])),scope='Numeric evidence from saved partial rows of the same single-shot run only. Unavailable observations are not recognition failures. visual=0 means channel not evaluated when an earlier prerequisite failed, not a measured zero similarity; blank margin means not computed.'))
    representation_sources=Counter(str(r['provenance']['source_id']) for r in rob['cases']);e2e=[r['end_to_end_ms'] for r in scan['cases']];decomp=Counter(r['root_cause'] for r in failures)
    components_table=table([['Componente (non additivo)','p50 ms','p95 ms'],['---']*3]+[[k,v['p50'],v['p95']] for k,v in perf['components'].items()])
    summary_table=[['Misura','N','Exact','Family','Rifiuti','Errati','Precisione','Richiamo'],['---']*8]
    for name,r in [('Canonical unambiguous',can),('Evaluation v4 PARZIALE',rob),('Scan v4 PARZIALE',scan),('Filled v4 PARZIALE',filled)]:summary_table.append([name,len(r['cases']),r['counts']['exact'],r['counts']['family'],r['counts']['reject'],r['counts']['wrong'],display(metric(r,'document_precision')),display(metric(r,'document_recall'))])
    hist_table=[['Corpus storico invariato','Casi','Corretti','Falliti'],['---']*4]+[[n,len(v['cases']),v['summary']['passed'],v['summary']['failed']] for n,v in historical.items()]
    gate_table=[['Gate','Target','Risultato','Esito'],['---']*4]+[[g['gate'],g['target'],json.dumps(g['actual'],ensure_ascii=False) if isinstance(g['actual'],(dict,list)) else g['actual'],'PASS' if g['passed'] else 'FAIL' if g['blocking'] else 'INFO/PENDING'] for g in gates]
    archive=f'BurOCRazia-v0.7.0-RC1-round8.zip' if passed else 'BurOCRazia-v0.7.0-candidate-NOT-READY-round8.zip'
    body=f'''# Round 8 — {status}

Software pubblico 0.6.1; candidata 0.7.0; schema 610. Branch `codex/coverage-benchmark-v0.7.0`. Freeze `{frozen['commit']}`. Il commit finale è quello contenente questo rapporto; il suo SHA e quello dello ZIP sono in `dist/package-verification.json` e nella consegna. Nessun push, tag o release pubblicata. Catalogo invariato: 1.216 identità reali, 1.212 operative, 19 fonti, 16 famiglie. SHA seed `{ci['catalog']['sha256']}`.

**Evaluation v4 INCOMPLETA:** una sola invocazione, terminata con `OSError [Errno 22]` durante la scrittura del checkpoint. Salvate {len(rob['cases'])}/{len(prepared['representations'])} osservazioni; {len(prepared['representations'])-len(rob['cases'])} esiti non disponibili. Nessun riavvio o ritocco del codice congelato. Le metriche del sottoinsieme salvato descrivono soltanto quelle righe e non sono una prova rappresentativa né qualificata di release. Il Round 8 si chiude come candidata NOT READY con requisito di evaluation completa non soddisfatto.

## Verità e limiti delle etichette

9 gruppi contraddittori, 29 occorrenze: {json.dumps(truth['counts'],ensure_ascii=False)}; zero non classificate. Registro creato prima del tuning. Le due righe confermate passano {reconciled['summary']['passed']}/2. I corpus locked e i 110 raw R6/R7 sono immutati. Le ambiguità restano fuori dai gate principali; i loro NO storici restano vincoli di sicurezza. R6/R7 sono sviluppo. Le etichette dei nuovi casi v4 sono confirmed dalla risorsa canonica ufficiale e dal binding pubblico preesistente; non costituiscono verifica editoriale.

## Implementazione e calibrazione

Stati delle 29 label nel registro: {json.dumps({s:sum(c['label_status']==s for c in truth['cases']) for s in ['confirmed','historical_only','ambiguous','excluded_from_release_gate']})}. Soltanto le label confirmed alimentano il gate riconciliato; i risultati storici restano diagnostici e i loro NO conservano il contratto di sicurezza.

Fingerprint v1/v2 conservate. V3: 1.027 binding, 1.003 SHA, 3.476 pagine; OCR locale reale su 3.426 pagine PDF, 50 pagine logiche DOCX senza OCR/layout inventati. Hash token stabili, char 3/4/5 con IDF canonico deterministico, ancore e 24 hash visuali per pagina (quattro rotazioni, crop e tile 2x2). Allineamento greedy di massimo due pagine, input fino a cinque pagine. Containment è una stima da sketch campionati, dichiarata nei parametri, non un confronto integrale. Nessuna immagine o testo ufficiale incluso nei dati redistribuiti.

Calibrazione di sviluppo su {len(cal['identity_ids'])} identità riservate, tipi {json.dumps(cal['representation_types'])}. Griglia di 18 configurazioni, priorità a zero false accept e zero identità errate. Scelta char {cal['char_ngram']}, aggregazione {cal['page_aggregation']}, containment {cal['containment']}; soglie {json.dumps(cal['thresholds'])}. Pesi contenuto .50, char .35, ancore .15; visual come canale indipendente condizionale. Criteri SHA univoco, testo+char+identità, OCR+char+visual+ancore, oppure field-set univoco con testo compatibile. Ente/versione espliciti, binding obsoleto e stato non operativo restano veti. Nessuna taratura dopo il freeze.

Il profilo selezionato ottiene 428/532 exact di sviluppo, zero identità errate e 267/267 rifiuti dei negativi. Una verifica finale su tutti i 799 casi prima del freeze conferma zero differenze negli esiti; griglia originale, tentativi falliti e verifica restano separati nei raw.

Memo soltanto nella singola richiesta per sketch e rendering. Cache globali soltanto per dati del catalogo pubblico. Retrieval economico per hash, confronto testuale sui candidati, visual lazy su massimo 25 identità incerte. La normalizzazione del confronto metadati è preparata una volta dal batch RapidFuzz e confrontata con il full scan indipendente nei test. I contatori misurano pagine per initial/text e identità per visual: non sono la stessa unità.

Normalizzazione e segnali di ente sono memoizzati nella richiesta per ciascuna distinta policy (fingerprint e metadati hanno regole di intestazione diverse). Anche i confronti puri per pagina sono memoizzati per parametri e indice; le righe di fusione sono copie, senza trasferire esiti visuali tra configurazioni. Il shortlist limita il visual; il confronto testuale può ancora esaminare molte pagine recuperate. Questo resta un limite reale dell'ottimizzazione, visibile nei contatori, senza cache globale dei testi caricati.

Contatori finali p95: initial {perf['counters']['candidates_initial']['p95']} pagine canoniche distinte recuperate nell'unione delle query; text {perf['counters']['candidates_text']['p95']} coppie pagina input/canonica confrontate; visual {perf['counters']['candidates_visual']['p95']} identità. Le pagine canoniche possono essere confrontate con più pagine dell'input. Totale rendering visuali nei 390 riconoscimenti temporizzati: {perf['counters']['page_renders']}. Il top-K limita il canale visuale, mentre il confronto testuale resta il limite principale indicato dal profilo.

Il primo grid completo aveva zero false accept sui negativi ma un'identità errata in tutte le configurazioni: crop 5% del template ANAC 614. La firma testuale dominante indicava 614, il visual sotto soglia impediva il match, e il fallback lessicale sceglieva 612. La correzione aggiunge un veto generale contro l'identificazione contraria a una firma dominante sicura, senza abbassare la soglia visuale né promuovere automaticamente la firma rifiutata. Tentativo fallito e diagnosi conservati; calibrazione completa ripetuta sul codice corretto prima del freeze.

## Copertura e canonical

{cov['fingerprinted_all_operational_docs']}/1212 firme operative ({cov['coverage_all']:.2%}); {cov['fingerprinted_file_backed_docs']}/1158 con file ({cov['coverage_file_backed']:.2%}); {cov['recovered']} nuove identità effettivamente recuperate. 33 richieste di rete autorizzate nel solo manutentore hanno recuperato byte per otto ID, senza sufficiente prova per renderli active. Nessun denominatore cambiato. Risorse legacy non supportate, robots e conflitti di identità restano limiti reali. {shared['shared_bindings']} binding condivisi, {len(shared['groups'])} gruppi classificati in audit; nessuna identità esatta ottenuta dal solo SHA condiviso. Le 979 risorse active unambiguous sono il denominatore canonical; i 1.027 binding complessivi non sono 1.027 identità certe.

Exact-resource lookup: {resource_lookup['matched_bindings']}/{resource_lookup['bindings']} binding, {resource_lookup['unique_resources']} SHA distinti, byte della cache verificati prima del lookup. Questa misura include risorse condivise e prova soltanto l'identità dei byte, separatamente dal riconoscimento dell'identità documentale.

## Generazione compilati

Sviluppo: 50/50 generati, riaperti e verificati prima del riconoscimento; QA visiva su dieci template, approfondita sui tre problematici. Campi reali, checkbox Unicode e font automatici corretti; overlay statici in spazi liberi con widget appiattiti, titoli/codici/enti preservati. Solo valori chiaramente fittizi, CF invalido ed email `.invalid`. Non viene rivendicata compilazione completa o validità amministrativa.

Evaluation: {len(generation)} tentativi, {success} generati/riaperti/verificati ({genrate:.2%}); metodi {dict(Counter(r['generation_method'] for r in generation if r['generated']))}. I fallimenti di generazione sono separati dal richiamo di riconoscimento, come richiesto per Round 8. Le vecchie metriche R7 restano 9/50 e 41 fallimenti sul piano storico.

La validità dei compilati è meccanica: persistenza di valori sintetici dopo riapertura, non completezza o correttezza amministrativa. QA visuale aggiuntiva prima del riconoscimento sulle prime pagine dei dieci template nuovi (variante 1), approfondita su 360 e 1133; intestazioni e codici conservati. Nel template 1133 una data compare anche nel campo del luogo di nascita; alcuni campi generici comune/indirizzo ripetono una via fittizia. Campi non riconosciuti e controlli radio possono restare vuoti. Limiti registrati in `evaluation_filled_visual_qa.json`, senza cambiare generatore, casi, etichette o denominatori dopo il freeze.

## Nuova evaluation v4 single-shot

Piano: {len(plan['evaluation_identities'])} identità, {len(plan['source_counts'])} fonti, concentrazione massima per ID {plan['source_concentration']:.2%}; distribuzione ID {plan['source_counts']}. Generati tutti i {len(prepared['representations'])} input, incluse {sum(r['scan_like'] for r in prepared['representations'])} scansioni e {success} compilati. Piano, leakage, generazione e unica invocazione sono registrati separatamente con orari e SHA. Controlli di overlap su ID, SHA, URL, titolo/codice/versione, field-set e sketch quasi duplicati: zero leakage proibito secondo le regole dichiarate. Sono trasformazioni sintetiche di file noti, non scansioni di utenti reali. Le varianti sono correlate per template.

Risultati persistiti: {len(evaluated_ids)} identità, {len(evaluated_sources)} fonti, distribuzione ID {dict(evaluated_sources)}, concentrazione per ID {display(evaluated_concentration)}; distribuzione delle {len(rob['cases'])} rappresentazioni salvate {dict(representation_sources)}. Il sottoinsieme dipende dall'ordine di completamento dei worker e non rappresenta il piano. Il pool ha atteso il lavoro già inviato prima dell'uscita, ma gli esiti assenti dal checkpoint non sono recuperabili: non vengono inventati né classificati come rifiuti o errori di riconoscimento. `evaluation_interruption.json` contiene audit, SHA del log e del checkpoint e gli ID senza osservazioni. Copia byte-identica del checkpoint conservata. Adeguatezza e precisione/richiamo principali restano non qualificati; tabella seguente soltanto descrittiva.

{table(summary_table)}

Richiamo utile di gate = exact recall: {fam['families_evaluable']}/16 famiglie valutabili, capacità `{fam['capability_status']}`. Le osservazioni esplorative non aumentano il richiamo utile.

Retrieval @1/@5/@10/@25: `{json.dumps(rob['candidate_recall_at_k'])}`. Il lookup SHA dei file canonici identici conta come rank 1; per le rappresentazioni trasformate il rango proviene dal retrieval per pagina prima della fusione. Fallimenti scan: `{dict(decomp)}`. CSV con score atteso, OCR, char, visual, ancore, rango, ente/versione, veto, soglie e margine. Un visual non attivato è indicato 0 nella riga numerica e non equivale a uno score visuale misurato.

## Unknown e regressioni

Unknown storici: {len(unknown['cases'])}, rifiuti corretti {unknown['counts']['reject']}, false accept {len(unknown['cases'])-unknown['counts']['reject']}; {unknown['counts']['extraction_failed']} errori di estrazione inclusi come rifiuti prudenziali. Zero nuovi unknown indipendenti. Le label sono historical_only: il gate unknown principale confirmed resta non misurato e blocca la promozione. Il rifiuto storico è una metrica diagnostica separata.

{table(hist_table)}

R061: {r061['observed']['match_type']}; cinque casi critici {sum(r['safe'] for r in five['cases'])}/5 safe. Tutti gli expected originali sono conservati; discrepanze positive e contraddizioni rimangono visibili. OCR reale: {ocr['passed']}/7 storico e {ocr2['summary']['passed']}/14 sintetico, separato da validazione editoriale e da collaudo su altri sistemi.

La compatibilità sintetica v2 conserva due NO storici accettati come documento: EX02MISSINGREV e EX03MISSINGREV, entrambi `ambiguous` nel registro, osservati rispettivamente come ID 13 e 12. Restano false accettazioni rispetto al contratto storico e fanno fallire il gate di sicurezza, anche se le etichette ambigue sono escluse dalla precisione principale. Nessuna correzione dopo l'evaluation. La CLI compatibilità esce con codice 1, come documentato in `ci_local.json`.

## Prestazioni e memoria

Riconoscimento warm in processo isolato: p50 {perf['latency_ms']['p50']:.2f} ms, p95 {perf['latency_ms']['p95']:.2f} ms. Gruppi `{json.dumps(perf['by_input_group'])}`. OCR escluso dal gate, generazione sketch e rendering visuale lazy inclusi. Stessi 35 testi sintetici+16 file del profilo storico, più 14 scansioni di sviluppo fissate prima della nuova evaluation. Tempi componenti non additivi in `performance_profile_components.json` e cProfile. E2E scan con OCR sull'unica evaluation: p50 {quantile(e2e,.5):.2f} ms, p95 {quantile(e2e,.95):.2f} ms; misura durante tre worker, distinta dalla latenza isolata del motore.

I tempi end-to-end v4 riguardano soltanto le {len(scan['cases'])} scansioni con osservazioni salvate, con tre worker e regressioni diagnostiche concorrenti: non rappresentano tutte le 266 scansioni preparate. Il profilo isolato usa esclusivamente gli input di sviluppo fissati prima dell'evaluation e non ripete i casi v4.

Nel profilo prestazionale il lookup SHA del file è disattivato, come nella misura R7, per misurare il lavoro effettivo di riconoscimento anche sugli originali. L'estrazione e l'enumerazione preliminare dei campi sono fuori dal cronometro; ogni ripetizione crea una richiesta nuova, senza riuso di firme o rendering dell'input tra ripetizioni.

{components_table}

Indice V3 {perf['index']['bytes']} byte; disco {perf['index']['disk_bytes']} byte; RSS `{json.dumps(perf['rss'])}`. Il limite di 100 MB si riferisce al deep size dell'indice canonico, non alla RSS dell'interprete o al JSON temporaneo di caricamento. Il profilo iniziale pre-ottimizzazione p95 345,30 ms è conservato. La baseline R7 misurata nuovamente prima dei cambiamenti era p95 281,51 ms; l'orfano diagnostico R7 rilevato all'inizio era stato fermato prima di queste misure.

## Test e CI

{tests['passed']} passed, {tests['skipped']} skipped, zero failed; Windows Python {tests['python']}. Catalogo, bootstrap separato, hash storici e compileall verificati localmente. CI Ubuntu/macOS/Windows Python3.12 configurata, non eseguita esternamente: `pending_external_gate`. Nessun push. I test normali non richiedono cache ufficiali, Tesseract remoto, dati personali o rete.

Controlli mirati successivi al riepilogo UI: {tests.get('post_report_checks',{}).get('passed','pending')} passed; sono un sottoinsieme della suite, non ulteriori test distinti. Le validazioni diagnostiche unknown e family erano rimaste senza artefatto dopo l'interruzione manuale della sessione e sono state completate alla ripresa. La nuova evaluation v4 non è stata riavviata.

## Gate

{table(gate_table)}

## Archivio

`dist/{archive}`. SHA256 e commit finale in `dist/package-verification.json` e nel file `.zip.sha256`, prodotti dopo il commit del rapporto. Git archive include soltanto i file tracciati. Esclusi PDF/DOCX ufficiali o compilati, cache, binari OCR, database personali, temporanei e credenziali. Stato **{status}**: nessun requisito senza prova viene dichiarato completato.
'''
    (ROOT/'docs/ROUND8_REPORT.md').write_bytes(body.encode())
    brief=f"Round 8 **{status}**, software 0.6.1: copertura file {cov['coverage_file_backed']:.2%}; canonical {can['counts']['exact']}/{len(can['cases'])}. **Evaluation v4 INCOMPLETA: {len(rob['cases'])}/{len(prepared['representations'])} osservazioni salvate dopo errore di scrittura; nessuna ripetizione.** Sole metriche descrittive parziali: exact {rob['counts']['exact']}/{len(rob['cases'])}, scan {scan['counts']['exact']}/{len(scan['cases'])}, compilati {filled['counts']['exact']}/{len(filled['cases'])}; non qualificano i gate principali. Generazione compilati {success}/{len(generation)}. p95 {perf['latency_ms']['p95']:.2f} ms. Truth e gate nel [rapporto Round 8](docs/ROUND8_REPORT.md). Due accettazioni contro NO storici ambigui restano bloccanti. R6/R7 sono sviluppo; family insufficiently validated; unknown soltanto storico; CI esterna pending."
    preface('README.md',brief);preface('docs/BENCHMARK.md','# Benchmark Round 8 — '+status+'\n\n'+brief.replace('(docs/ROUND8_REPORT.md)','(ROUND8_REPORT.md)')+'\n\nLe sezioni successive conservano le misure storiche e i loro denominatori; non descrivono la release corrente.');preface('DATA_NOTICE.md','Round 8 conserva il catalogo e la provenienza. Redistribuisce soltanto firme hash e risultati numerici di dati pubblici; nessun file ufficiale, immagine, testo OCR o compilato sintetico incluso. Nessuna verifica editoriale attribuita automaticamente.')
    locks={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/OUT).glob('*.json') if p.name!='evaluation_locks.json'}
    locks.update({p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/OUT).glob('*.csv')});write(OUT+'evaluation_locks.json',dict(sha256=locks,freeze_commit=frozen['commit'],scope='Final serialized evidence, immutable after packaging; old raw hashes additionally locked in baseline.'))
    print(status,'blocking failures',[g['gate'] for g in gates if g['blocking'] and not g['passed']],flush=True)
if __name__=='__main__':main()
