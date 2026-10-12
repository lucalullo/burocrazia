"""Publish R10 prerequisite evidence; never manufacture a v5 evaluation."""
import argparse,csv,hashlib,json,platform,re,subprocess,sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from benchmarks.round3_audit import read,catalog
from benchmarks.round8_common import identity
from benchmarks.transactional_writer import atomic_json
from benchmarks.unknown_v2 import validate
from benchmarks.truth_v2 import validate_registry
OUT=ROOT/'benchmarks/results/round10'

def main():
 p=argparse.ArgumentParser();p.add_argument('--preliminary',action='store_true');a=p.parse_args()
 can=read('benchmarks/results/round10/canonical.json');legacy=read('benchmarks/results/round10/legacy_resource_fingerprints.json');perf=read('benchmarks/results/round10/performance.json');dev=read('benchmarks/results/round10/unknown_development.json');balance=read('benchmarks/results/round10/unknown_balance.json');manifest=validate(read('benchmarks/manifests/official_unknown_v2.json'));verification=read('benchmarks/results/round10/verification.json')
 for resource in legacy['resources']:
  receipt=json.loads((ROOT/'benchmarks/cache'/(resource['original_sha256']+'.json')).read_bytes())
  assert receipt['sha256']==resource['original_sha256']
  resource['official_source_receipt']=receipt
  for page in resource.get('pages_sketches',[]):page['ocr_status']='not_requested_maintenance_digital_only'
 atomic_json(OUT/'legacy_resource_fingerprints.json',legacy)
 plan=list(csv.DictReader((OUT/'fingerprint_recovery_plan.csv').open(encoding='utf8')))
 derived_ids=sorted({c['document_id'] for c in legacy['bindings'] if c['identity_supported'] and not c['shared_resource']})
 cov=dict(operational=1212,file_backed=1158,fingerprinted=941,coverage_all=941/1212,coverage_file_backed=941/1158,recovered=0,minimum_needed_for_85=985,additional_required=44,residual_audited=len(plan),derived_resource_count=sum(r['success'] for r in legacy['resources']),derived_unique_identity_candidates=derived_ids,derived_fingerprints_active=0,remaining_reasons=dict(Counter(r['final_reason'] for r in plan)),tiers=dict(Counter(r['tier'] for r in plan)),scope='Fixed R6 denominator; 941 active unique IDs, 979 active resources. Derived-only and shared candidates excluded. No original legacy bytes represented as official PDF SHA. Runtime bundle and seed unchanged.')
 atomic_json(OUT/'fingerprint_coverage.json',cov)
 historical={n:read('benchmarks/results/round10/historical_'+n+'.json') for n in ['development_regression','release_locked_v1','release_locked_v2','hard_negatives_v1','hard_negatives_v2','family_release_v3','development_compat_v2','catalog_coverage']}
 negatives=[r for v in historical.values() for r in v['cases'] if r['expected']['match_type']=='NO_MATCH']
 fa=[r['id'] for r in negatives if r['observed']['match_type']!='NO_MATCH']
 two=[r for r in historical['development_compat_v2']['cases'] if r['id'] in ['EX02MISSINGREV','EX03MISSINGREV']]
 r061=next(r for r in historical['release_locked_v2']['cases'] if r['id']=='R061')
 safety=dict(historical_no_count=len(negatives),historical_false_accepts=fa,round8_two={r['id']:r['observed'] for r in two},r061=r061['observed'],old_five_passed=verification['historical_five_passed'],scope='Historical NO contracts preserved separately from confirmed truth. Ambiguous v1 positive labels are not relabelled or hidden.')
 atomic_json(OUT/'historical_safety.json',safety)
 tests=dict(status='pending',passed=None,skipped=None,failed=None)
 log=ROOT/'reports/round10-full-tests.log'
 if log.exists():
  raw=log.read_bytes();text=raw.decode('utf8',errors='replace');m=re.search(r'(\d+) passed(?:, (\d+) skipped)? in ([\d.]+)s',text)
  if m and not re.search(r'\b[1-9]\d* (?:failed|errors?)\b',text):tests=dict(status='passed',passed=int(m[1]),skipped=int(m[2] or 0),failed=0,seconds=float(m[3]),log_sha256=hashlib.sha256(raw).hexdigest(),python=platform.python_version(),platform=platform.platform(),skip_reasons='Windows: one symlink privilege and two FIFO unsupported cases; see preserved local pytest log.')
 if not a.preliminary:assert tests['status']=='passed','Full pytest must pass'
 targeted=ROOT/'reports/round10-targeted-final.log'
 if targeted.exists():
  targeted_raw=targeted.read_bytes();match=re.search(rb'(\d+) passed in ([\d.]+)s',targeted_raw)
  assert match and int(match[1])==9 and b'failed' not in targeted_raw
  tests['post_correction_targeted']=dict(passed=9,failed=0,seconds=float(match[2]),log_sha256=hashlib.sha256(targeted_raw).hexdigest(),scope='Profile values and timeout/provenance contracts retested after maintenance profile correction; not added a second time to full-suite count.')
 atomic_json(OUT/'tests.json',tests)
 checks=dict(coverage_file_backed_pass=cov['coverage_file_backed']>=.85,coverage_all_pass=cov['coverage_all']>=.70,unknown_count_pass=balance['total_confirmed']>=100,unknown_sources_pass=balance['sources']>=8,unknown_balance_pass=balance['max_concentration']<=.25,historical_safety_pass=not fa and len(two)==2 and all(r['observed']['match_type']=='NO_MATCH' for r in two) and r061['observed']['match_type']=='NO_MATCH' and verification['historical_five_passed'],canonical_pass=can['counts']['exact']==979 and can['counts']['wrong']==0 and can['counts']['extraction_failed']==0,performance_pass=perf['latency_ms']['p95']<=250)
 checks['ready_to_freeze']=all(checks.values());assert not checks['ready_to_freeze'],'Green prerequisites require the real frozen single-shot workflow'
 from benchmarks import round8_common
 round8_common.SEED=2026101210;ident=identity()
 for value in [dev,perf]:
  for key in ['code_sha256','runtime_sha256','fingerprint_sha256']:assert value['identity'][key]==ident[key],key
 atomic_json(OUT/'prerequisite_gate.json',dict(**checks,identity=ident,blocked=[k for k,v in checks.items() if not v and k!='ready_to_freeze'],tests=tests['status'],scope='No freeze, no v5 evaluation identity selection, no recognition on unknown_eval. Gates unchanged.'))
 atomic_json(OUT/'freeze_not_created.json',dict(status='not_created',prerequisites=checks,freeze=None,evaluation_v5='not_run',unknown_eval_recognition_calls=0))
 # Immutable v2 base plus an additive, separately identified evidence file.
 prior=read('benchmarks/reference/reference_truth_v2.json');new=[]
 for c in manifest['cases']:
  if c['historically_seen']:continue
  new.append(dict(case_id=c['case_id'],corpus='official_unknown_v2_round10',expected_status='NO_MATCH',expected_document_id=None,expected_family_id=None,source_evidence=[dict(sha256=c['SHA256'],receipt=c['receipt'],audit=c['audit_evidence'])],source_url=c['official_url'],evidence_date=c['acquisition_date'],confidence_status='confirmed',notes='Additive official unknown confirmation before recognition; no catalog/editorial promotion. Split is development or reserved, not a frozen evaluation.'))
 addendum=dict(schema_version=2,registry_id='reference-truth-v2-round10-addendum',base_registry_sha256=hashlib.sha256((ROOT/'benchmarks/reference/reference_truth_v2.json').read_bytes()).hexdigest(),cases=new,historical_locks=prior['historical_locks'],counts=dict(Counter(c['confidence_status'] for c in new)),unclassified_contradictions=0)
 validate_registry(addendum);atomic_json(ROOT/'benchmarks/reference/reference_truth_v2_round10_addendum.json',addendum)
 gates=[]
 def gate(name,target,actual,passed,blocking=True):gates.append(dict(gate=name,target=target,actual=actual,passed=bool(passed),blocking=blocking))
 for name,target,actual in [('coverage_file_backed','>=85%',cov['coverage_file_backed']),('coverage_all','>=70%',cov['coverage_all']),('unknown_count','>=100,target150',balance['total_confirmed']),('unknown_sources','>=8,target10+',balance['sources']),('unknown_balance','<=25%',balance['max_concentration']),('historical_safety','0 historical NO accepts',fa),('canonical','100% unambiguous',can['counts']),('performance','p95<=250ms',perf['latency_ms'])]:gate(name,target,actual,checks[name+'_pass'])
 gate('unknown_development','observed separately',dict(total=dev['actual_count'],false_accepts=dev['false_accepts'],extraction_failed=dev['extraction_failed']),dev['false_accepts']==0,False)
 for name,target in [('v5_identities','>=30'),('v5_sources','>=6'),('v5_concentration','<=30%'),('v5_representations','>=400'),('v5_scans','>=200'),('v5_fills','>=50 valid'),('v5_unknown_eval','>=30'),('v5_precision','>=99.5%'),('v5_exact_recall','>=90%'),('v5_entity_version_errors','0'),('v5_scan','P>=99.5%,R>=85%'),('v5_filled','P>=99.5%,R>=90%'),('v5_unknown_rejection','>=99%'),('v5_retrieval_at25','100%')]:gate(name,target,None,False)
 gate('tests','all pass',tests,tests['status']=='passed');gate('family','>=5 real evaluable families','experimental / insufficiently validated',False,False);gate('CI','external_pending','external_pending',False,False)
 result=dict(round=10,status='NOT READY',software_version='0.6.1',candidate_target='0.7.0',schema=610,identity=ident,freeze=None,freeze_status='not_created',local_gates_passed=False,gates=gates,tests=tests,ci='external_pending')
 atomic_json(ROOT/'docs/release_gates.json',result)
 empty=dict(status='not_run',reason='Prerequisites failed: coverage, source diversity and balance.',freeze=None,recognition_calls=0,cases=[],summary=dict(cases=0,metrics={},latency_ms={}))
 docs,families=catalog()
 from src.recognize import catalog_revision
 latest=dict(schema_version=1,benchmark_model='known-family-unknown-v5',round=10,status='NOT READY',software_version='0.6.1',candidate_target='0.7.0',catalog_count=1216,catalog_semantic_sha256=catalog_revision(docs,families),commit=ident['commit'],executed_at=ident['executed_at'],release_gate=result,fingerprint_coverage=dict(status='executed',operational_docs_total=1212,file_backed_operational_docs=1158,fingerprinted_all_operational_docs=941,fingerprinted_file_backed_docs=941,**cov),known_canonical=dict(status='executed',summary=can['summary']),known_robustness=empty,scan_ocr=empty,filled_forms=empty,unknown_official=dict(status='development_only',summary=dev['summary'],confirmed_corpus=balance,reason='Reserved unknown_eval unmeasured; no independent rejection estimate.'),family_identity_holdout=dict(status='experimental',families_evaluable=0,capability_status='insufficiently_validated'),performance=dict(status='executed',latency_ms=perf['latency_ms'],index_bytes=perf['index']['bytes']),evaluations=[dict(name=k,summary=v['summary']) for k,v in historical.items()])
 atomic_json(ROOT/'benchmarks/latest_summary.json',latest)
 def table(rows):return '\n'.join('| '+' | '.join(str(c).replace('|','/') for c in row)+' |' for row in rows)
 gt=table([['Gate','Target','Actual','Esito'],['---']*4]+[[g['gate'],g['target'],json.dumps(g['actual'],ensure_ascii=False),'PASS' if g['passed'] else 'FAIL / non misurato' if g['blocking'] else 'INFO / PENDING'] for g in gates])
 hist=table([['Corpus','Corretti','Totale'],['---']*3]+[[k,v['summary']['passed'],len(v['cases'])] for k,v in historical.items()])
 body=f'''# Round 10 — NOT READY

Software pubblico 0.6.1, target 0.7.0, schema 610. Branch `codex/coverage-benchmark-v0.7.0`; ingresso HEAD `8c13da270fe2c4db212ca3611fb5ce0ddef7b0d8`, working tree pulito. HEAD durante il report `{ident['commit']}`; commit finale e SHA archivio sono registrati dopo il commit in `dist/package-verification-round10.json` e nella consegna. Nessun push, tag o release. CI `external_pending`.

## Decisione e prerequisiti

`ready_to_freeze=false`. Coverage file-backed 941/1158 = 81.260794%, target 85%: necessari 985, mancano ancora 44. Coverage operative 941/1212 = 77.640264%, target70% superato. Unknown {balance['total_confirmed']} confermati, {balance['sources']} fonti e {balance['entities']} autorità ospitanti; concentrazione massima {balance['max_concentration']:.2%}. Conteggio minimo superato, diversità e bilanciamento insufficienti. Nessun freeze e nessuna evaluation v5, come richiesto quando A o B fallisce. Nessuna modifica a motore, pesi, soglie, fusion tiers, scoring, decision policy o fingerprint attive.

## Recovery

Piano completo dei 217 residui in `fingerprint_recovery_plan.csv`: tier `{json.dumps(cov['tiers'])}`. Fonti, ente, URL primario/alternativo, stato precedente, formato, azione ed esito per ogni ID. Alternative wrapper/multipart/redirect/IRI e osservazioni già esplorate R8/R9 riesaminate dai byte e dalle ricevute cached; nessun retry di 403/429 o aggiramento robots. Il limite8MiB non è stato aumentato per recuperare il file INL29-3 da8.42MB. Risorse con conflitto ente, apertura insufficiente o identità condivisa restano escluse dal conteggio univoco.

Il controllo PATH del Round9 non trovava LibreOffice, ma l’installazione standard esiste: probe reale LibreOffice26.8.0.3. Correzione della diagnosi, senza riscrivere il raw storico. Nuovo convertitore maintenance-only: preflight contenuti attivi/relazioni esterne, profilo temporaneo senza macro/aggiornamento link, processo headless nascosto senza shell, timeout45s, byte8MiB, pagine100, testo1M. Profilo separato non equivale a sandbox OS; non si dichiara una garanzia contro documenti ostili arbitrari. Nessuna installazione e nessuna conversione nel runtime.

Analizzate {len(legacy['resources'])} risorse legacy distinte, {cov['derived_resource_count']} conversioni PDF valide; contenuto rappresentato da sketch digitali pubblici in `legacy_resource_fingerprints.json`, senza OCR dei derivati e senza PDF temporanei in Git. {len(derived_ids)} candidati univoci superano il controllo d’identità d’apertura invariato: ID `{derived_ids}`. I restanti hanno prove insufficienti/conflitti/condivisioni o sono rifiutati dal preflight/limiti/conversione. Original SHA, derived SHA, ricevuta effettiva e SHA convertitore restano distinti. Il bundlev3 ammette soltanto PDF/DOCX ufficiali: nessun PDF derivato presentato come byte ufficiale. Questi candidati non sono attivi e non aumentano la coverage; anche tutti i {len(derived_ids)} candidati non colmerebbero il delta44. Non sono state allentate le prove d’identità per trasformare nomi di file in titoli forti.

L’audit iniziale del profilo maintenance è conservato in `legacy_resource_fingerprints_initial_profile.json`. Nel controllo finale i tipi del registro installato hanno mostrato Writer/Link booleano errato, Calc/Link=0 (always) e una proprietà Common/Load non dichiarata: correzione motivata in `legacy_profile_correction.json`, con fonti primarie LibreOffice. Profilo finale con blocco esplicito macro/OLE/DDE/referer e valori tipizzati never; conversioni ripetute, nessun dato promosso da quel tentativo iniziale. Anche performance e osservazioni development antecedenti alla correzione maintenance sono conservate con i propri hash; i risultati principali sono quelli finali rieseguiti. Nessuna modifica al runtime.

Restano1027 binding di risorsa:979 active unambiguous per941 identità e48 condivisi. Canonical resource e identity recognition distinti; SHA comune non dà identità univoca. Native upload DOC/RTF/XLS/XLSX/ODT resta unsupported. Seed invariato,1216 reali/1212 operative/19 fonti/16 famiglie. Nessun nuovo document_id, fonte del catalogo o stato editoriale.

## Unknown e truth

Acquisizione separata nel solo maintenance con --allow-network, HTTPS/robots/allowlist, budget300 richieste iniziali più7 effettive nel tentativo di bilanciamento (budget60). {len(read('benchmarks/results/round10/unknown_candidates.json')['candidates'])} candidati acquisiti da nuove fonti istituzionali fuori dal catalogo; {balance['new_candidates_audited']} nuovi SHA auditati, uno già nel manifestv1. Classificazioni `{json.dumps(balance['classification_counts'])}`. Nessuna promozione automatica da discovery a truth.

Distribuzione confermati `{json.dumps(balance['counts_per_source'])}`. Tipi `{json.dumps(balance['document_types'])}`. Con codice/numero documento o protocollo esplicito {balance['with_code']}, senza {balance['without_code']}; con versione/revisione/edizione/anno esplicito {balance['versioned']}, senza {balance['unversioned']}. Un anno citato in una legge non rende versionato il documento; il primo audit lessicale è conservato separatamente, nessuna truth label cambiata. `entity` indica l’autorità che ospita la fonte e non certifica ogni emittente storico: nessuna pretesa di8 emittenti indipendenti. I corpus comprendono circolari, istruzioni, guide e moduli veri; non si dichiara una copertura rappresentativa di tutti gli hard unknown.

Audit prima delle predizioni: titolo e tipo sostenuti dall’apertura2000 caratteri, codice, ente/fonte, revisione/anno osservato, URL/final URL/ricevute/date effettive, SHA, full catalog titles/codes, contenuto near-duplicate e alias delle16 famiglie. Dubbi esclusi. Tutti68 unknownR9 conservati nello sviluppo, compresi quelli nominalmente evaluation nel vecchio manifest, perché già riconosciuti. Split corrente `{json.dumps(balance['split'])}`; SHA e gruppi near disgiunti. Due coppie near trattate come componenti con lo stesso split; audit separato `unknown_resource_split_audit.json`. È una prova del resource split, non un certificato leakage di evaluation congelata; duplicati semantici fuori dagli sketch restano un limite.

V2 base del reference truth e manifestunknownv1 immutati; nuovo addendum motivato con {len(new)} conferme e SHA del registro base. Le vecchie etichette locked/v1, ambiguità e motivazioni restano disponibili. Manifestunknownv2 contiene ricevute e prove, nessun percorso locale assoluto. Non sono stati eliminati i45MIMIT per abbassare artificialmente la concentrazione. Dopo il primo audit è stato tentato Salute/PNES/PNRR con7 richieste ulteriori: risposte senza file acquisibili, non contate come unknown. L’aggiunta necessaria a una concentrazione25% con45MIMIT richiede almeno180 confermati, quindi altri73 rispetto ai107 attuali.

Development misurato {dev['actual_count']}/{dev['expected_count']}, ID univoci {dev['unique_case_ids']}, rifiuti corretti {dev['correct_rejections']}, false accept {dev['false_accepts']}, errori estrazione {dev['extraction_failed']}. WriterR9 transazionale realmente usato, journalignored, finalexport SHA `{dev['observations_sha256']}`. Nessun tuning. Unknown_eval {balance['split'].get('unknown_eval',0)} riservati, zero chiamate di riconoscimento e nessuna stima della loro rejection. Selezione delle identità note v5 mai avvenuta.

## Safety e canonical

NO storici {len(negatives)} osservazioni, false accept0. R061 NO; EX02MISSINGREV/EX03MISSINGREV NO; cinque vecchi falsi accept ufficiali verdi (rifiuto o propria identità corretta). Canonical979/979, wrong0, estrazioni fallite0. Nessuna label ambigua v1 promossa per migliorare i gate. Base33/35 e lockedv1 59/69 restano visibili; v2 69/69, compat37/37. Canonical è verifica delle risorse censite, non generalizzazione.

{hist}

## Performance

Protocollo R9 rieseguito in processo isolato: {perf['latency_ms']['n']} richieste warm con nuovi contesti, p50 {perf['latency_ms']['p50']:.2f}ms, p95 {perf['latency_ms']['p95']:.2f}ms, p99 {perf['latency_ms']['p99']:.2f}ms, gatep95≤250ms {'PASS' if checks['performance_pass'] else 'FAIL'}. Digital PDF p95 {perf['by_input_group']['representation:digital_pdf']['p95']:.2f}ms; scan con OCR già disponibile p95 {perf['by_input_group']['historical_scans']['p95']:.2f}ms; scannedPDF wrapper p95 {perf['by_input_group']['historical_scans_wrapped_pdf']['p95']:.2f}ms. OCR estrazione14 input sintetici misurato separatamente: `{json.dumps(perf['ocr_end_to_end_extraction_ms'])}`ms. Nessuna cache globale degli input e nessun shortcutSHA nella misura.

Indice {perf['index']['bytes']}bytes; RSS afterwarm {perf['rss']['after_warm_bytes']}bytes, crescita successiva {perf['rss']['growth_after_warm_bytes']}bytes. Il gate aggregato non garantisce ogni formato; vedere distribuzioni e componenti non additivi nei raw. La stabilità RSS non è dimostrata, causa non isolata. Nessuna ulteriore ottimizzazione del motore effettuata.

## Freeze, evaluation, family, test e CI

Freeze no; commit freeze assente. Evaluationv5, retrieval@1/@5/@10/@25, robustezza scansioni/compilati e unknown_eval non misurati; nessun file di evaluationv5 fabbricato. Generator filledR8 e50/356 rawv4 interrotti preservati. Family experimental/insufficiently validated (0 famiglie reali valutabili nella misuraR9 invariata); non entra nel useful recall. Test writerR9 interruption/resume/dedupe/finalizzazione atomica/count/SHA conservati e rieseguiti nella suite.

Suite locale `{json.dumps(tests)}`. Test offline aggiunti per contenuti attivi, relazioni esterne, traversal, profilo/timeout/provenance e unknownv2; Tesseract reale ita+eng nei controlli esistenti. Catalogo, corpus/hash, cinque casi critici e workflow verificati. Solo collaudo Windows, nessuna validazione editoriale o di altre piattaforme rivendicata. CI esterna pending; comandi legacyv1 del workflow conservano i due rifiuti rispetto alle labelpositive ambigue e non vengono presentati come greenCI.

{gt}

## Archivio

`dist/BurOCRazia-v0.7.0-candidate-NOT-READY-round10.zip`, da HEAD committato con verifica seed/corpus/hash byte sorgenti, raw storici e igiene. Commit e SHA256 finali in `dist/package-verification-round10.json` e `.zip.sha256`, fuori dal proprio contenuto per evitare autoreferenze. ArchiviR8/R9 e checksum conservati. Limiti bloccanti: coverage81.26%,7fontiunknown,concentrazione42.06%,nessuna evaluation indipendente. Versione pubblica0.6.1.
'''
 for before,after in [('Round9','Round 9'),('Round8','Round 8'),('Round10','Round 10'),('limite8MiB','limite 8 MiB'),('da8.42MB','da 8.42 MB'),('LibreOffice26.8.0.3','LibreOffice 26.8.0.3'),('timeout45s','timeout 45 s'),('byte8MiB','byte 8 MiB'),('pagine100','pagine 100'),('testo1M','testo 1M'),('bundlev3','bundle v3'),('delta44','delta 44'),('Restano1027','Restano 1027'),(':979',': 979'),('per941','per 941'),('e48','e 48'),('invariato,1216','invariato, 1216'),('budget300','budget 300'),('più7','più 7'),('budget60','budget 60'),('di8','di 8'),('apertura2000','apertura 2000'),('delle16','delle 16'),('Tutti68','Tutti 68'),('manifestunknownv1','manifest unknown v1'),('Manifestunknownv2','Manifest unknown v2'),('i45MIMIT','i 45 MIMIT'),('con7','con 7'),('concentrazione25%','concentrazione 25%'),('con45MIMIT','con 45 MIMIT'),('almeno180','almeno 180'),('altri73','altri 73'),('ai107','ai 107'),('WriterR9','Writer R9'),('journalignored','journal ignorato'),('finalexport','export finale'),('accept0','accept 0'),('Canonical979','Canonical 979'),('wrong0','wrong 0'),('fallite0','fallite 0'),('Base33','Base 33'),('lockedv1','locked v1'),('compat37','compat 37'),('gatep95','gate p95'),('estrazione14','estrazione 14'),('shortcutSHA','shortcut SHA'),('Evaluationv5','Evaluation v5'),('filledR8','filled R8'),('e50/356','e 50/356'),('rawv4','raw v4'),('writerR9','writer R9'),('budget300','budget 300'),('ArchiviR8/R9','Archivi R8/R9'),('coverage81.26%','coverage 81.26%'),('7fontiunknown','7 fonti unknown'),('concentrazione42.06%','concentrazione 42.06%'),('pubblica0.6.1','pubblica 0.6.1')]:body=body.replace(before,after)
 (ROOT/'docs/ROUND10_REPORT.md').write_bytes(body.encode())
 overview=f'Round10 NOT READY. Pubblico0.6.1/schema610. Canonical979/979, NO storici verdi. Coverage941/1158=81.26%, delta44; {balance["total_confirmed"]}unknown/{balance["sources"]}fonti, concentrazione{balance["max_concentration"]:.2%}. Recognitionp95 {perf["latency_ms"]["p95"]:.2f}ms. Nessun freeze/evaluationv5. Dettagli nel [rapporto Round10](ROUND10_REPORT.md).'
 for name,title,extra in [('BENCHMARK.md','Round10',overview),('FINGERPRINT_COVERAGE_AUDIT.md','Coverage Round10',f'Coverage attuale941/1158=81.26% e941/1212=77.64%. Minimo985, delta44. 217residui auditati,47derivazioni temporanee,2candidati univoci non attivi; PDF derivati e risorse condivise esclusi dal conteggio. Dati nel pianoR10 e rapporto. Le misure Round6 seguenti restano storiche.'),('REFERENCE_TRUTH_V2.md','Addendum Round10',f'Registrov2 base e v1 immutati; addendum `benchmarks/reference/reference_truth_v2_round10_addendum.json` con39nuove conferme motivate e hash base. Unknownv2:107confermati/7fonti,42.06% concentrazione. 75development/32riservati,0chiamate su unknown_eval. Le 68vecchie osservazioni sono tutte development. Prove in `benchmarks/results/round10/unknown_truth_audit.csv` e split audit; date delle ricevute effettive, nessuna promozione editoriale. Le cifreR9 seguenti restano storiche.')]:
  path=ROOT/'docs'/name;old=path.read_text(encoding='utf8');start='<!-- round10-current -->';end='<!-- /round10-current -->'
  if start in old:old=old[old.index(end)+len(end):].lstrip()
  path.write_bytes((start+'\n# '+title+'\n\n'+extra+'\n'+end+'\n\n'+old).encode())
 print('Round10 NOT READY',checks,flush=True)

if __name__=='__main__':main()
