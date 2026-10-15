"""Publish measured R11 prerequisites; no freeze/evaluation on failed coverage."""
import hashlib,json,platform,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from benchmarks.round3_audit import read,catalog
from benchmarks import round8_common as common
from benchmarks.transactional_writer import atomic_json
from benchmarks.unknown_release import validate,SEED
from benchmarks.evaluate import summary
from src.recognize import catalog_revision
OUT=ROOT/'benchmarks/results/round11'

def main():
 common.SEED=SEED;ident=common.identity();cov=read('benchmarks/results/round11/coverage_final.json');balance=read('benchmarks/results/round11/unknown_balance_final.json');master=validate(read('benchmarks/manifests/official_unknown_master_v1.json'));release=validate(read('benchmarks/manifests/official_unknown_release_v1.json'));can=read('benchmarks/results/round11/canonical.json');perf=read('benchmarks/results/round11/performance.json');dev=read('benchmarks/results/round11/unknown_development.json');verify=read('benchmarks/results/round11/verification.json');baseline=read('benchmarks/results/round11/baseline_audit.json')
 bm=balance['master'];br=balance['release'];fresh=br['total']-br['previously_recognized']
 hist={n:read('benchmarks/results/round11/historical_'+n+'.json') for n in ['development_regression','release_locked_v1','release_locked_v2','hard_negatives_v1','hard_negatives_v2','family_release_v3','development_compat_v2','catalog_coverage']}
 no=[r for v in hist.values() for r in v['cases'] if r['expected']['match_type']=='NO_MATCH'];fa=[r['id'] for r in no if r['observed']['match_type']!='NO_MATCH'];two=[r for r in hist['development_compat_v2']['cases'] if r['id'] in ['EX02MISSINGREV','EX03MISSINGREV']];r061=next(r for r in hist['release_locked_v2']['cases'] if r['id']=='R061')
 log=(ROOT/'reports/round11-full-tests.log').read_bytes();m=re.search(rb'(\d+) passed(?:, (\d+) skipped)? in ([\d.]+)s',log);assert m and b' failed' not in log and b' error' not in log
 tests=dict(status='passed',passed=int(m[1]),skipped=int(m[2] or 0),failed=0,seconds=float(m[3]),log_sha256=hashlib.sha256(log).hexdigest(),python=platform.python_version(),platform=platform.platform(),scope='Full local Windows pytest, real local Tesseract where required; one symlink-privilege and two FIFO skips. No external CI claim.')
 targeted=(ROOT/'reports/round11-targeted-final.log').read_bytes();assert re.search(rb'4 passed in',targeted) and b'failed' not in targeted
 tests['targeted_final']=dict(passed=4,failed=0,log_sha256=hashlib.sha256(targeted).hexdigest(),scope='Resolver, attachment role, quota invariance, domain and negative-manifest guards; not added twice to the suite count.')
 atomic_json(OUT/'tests.json',tests)
 from benchmarks.truth_v2 import validate_registry
 truth_base=read('benchmarks/reference/reference_truth_v2.json');new_truth=[]
 for c in master['cases']:
  if not c['case_id'].startswith('U11-'):continue
  new_truth.append(dict(case_id=c['case_id'],corpus='official_unknown_master_v1_round11',expected_status='NO_MATCH',expected_document_id=None,expected_family_id=None,source_evidence=[dict(sha256=c['SHA256'],receipt=c['receipt'],audit=c['audit_evidence'])],source_url=c['official_url'],evidence_date=c['acquisition_date'],confidence_status='confirmed',notes='New official attachment-context evidence, audited before predictions; no catalog/editorial promotion.'))
 for c in read('benchmarks/results/round11/fingerprint_build.json')['added']:
  new_truth.append(dict(case_id='CANONICAL-R11-'+str(c['document_id']),corpus='official_unambiguous_canonical_round11',expected_status='DOCUMENT_MATCH',expected_document_id=c['document_id'],expected_family_id=None,source_evidence=[dict(sha256=c['sha256'],receipt=c['receipt'],association=c['association'])],source_url=c['receipt']['requested_url'],evidence_date=c['receipt']['acquired_at'],confidence_status='confirmed',notes='Original official bytes; full catalog title and unchanged entity/version guards, no editorial verification.'))
 addendum=dict(schema_version=2,registry_id='reference-truth-v2-round11-addendum',base_registry_sha256=hashlib.sha256((ROOT/'benchmarks/reference/reference_truth_v2.json').read_bytes()).hexdigest(),cases=new_truth,historical_locks=truth_base['historical_locks'],unclassified_contradictions=0)
 validate_registry(addendum);atomic_json(ROOT/'benchmarks/reference/reference_truth_v2_round11_addendum.json',addendum)
 for measured in [perf,dev]:
  for k in ['runtime_sha256','code_sha256','fingerprint_sha256']:assert measured['identity'][k]==ident[k],k
 assert not subprocess.check_output(['git','diff','--name-only',baseline['commit'],'--','src','app.py','run.py','data/recognition_profiles','data/catalog_seed.sqlite3','data/recognition_features.json'],cwd=ROOT,text=True).strip(),'Semantic/runtime code or catalog changed'
 checks=dict(coverage_file_backed_percent=cov['file_backed_percent'],coverage_file_backed_pass=cov['file_backed_percent']>=85,coverage_all_percent=cov['all_operational_percent'],coverage_all_pass=cov['all_operational_percent']>=70,unknown_master_count=balance['master']['total'],unknown_release_count=balance['release']['total'],unknown_release_sources=balance['release']['sources'],unknown_release_max_concentration=balance['release']['max_concentration'],unknown_count_pass=balance['release']['total']>=100,unknown_sources_pass=balance['release']['sources']>=8,unknown_balance_pass=balance['release']['max_concentration']<=.25,unknown_types_pass=balance['release']['type_groups']>=5,historical_safety_pass=not fa and len(two)==2 and all(r['observed']['match_type']=='NO_MATCH' for r in two) and r061['observed']['match_type']=='NO_MATCH' and verify['historical_five_passed'] and dev['false_accepts']==0,canonical_pass=can['counts']['exact']==len(can['cases'])==980 and can['counts']['wrong']==0 and can['counts']['extraction_failed']==0,performance_pass=perf['latency_ms']['p95']<=250,tests_pass=True)
 checks['ready_to_freeze']=all(v for k,v in checks.items() if k.endswith('_pass'));assert not checks['ready_to_freeze'],'Green prerequisites require actual freeze and single-shot v5'
 atomic_json(OUT/'prerequisite_gate.json',dict(**checks,identity=ident,scope='Shared eligibility audited separately from exact canonical identity. Release selected without predictions; no R11 release recognition before freeze.'))
 atomic_json(OUT/'freeze_not_created.json',dict(status='not_created',reason='Coverage975/1158 below85%; minimum985, shortfall10.',freeze=None,evaluation_v5='not_run',release_recognition_calls=0))
 safety=dict(historical_no_observations=len(no),false_accepts=fa,r061=r061['observed'],round8_two={r['id']:r['observed'] for r in two},old_five_passed=verify['historical_five_passed'],unknown_dev_false_accepts=dev['false_accepts'],scope='Historical expectations and ambiguous v1 labels unchanged; source-confirmed NO and historical NO contracts kept distinct.')
 atomic_json(OUT/'historical_safety.json',safety)
 gates=[]
 def gate(name,target,actual,passed,blocking=True):gates.append(dict(gate=name,target=target,actual=actual,passed=bool(passed),blocking=blocking,status='PASS' if passed else 'NON MISURATO' if actual is None else 'FAIL' if blocking else 'INFO/PENDING'))
 for name,target,actual in [('coverage_file_backed','>=85%',cov['file_backed_percent']),('coverage_all','>=70%',cov['all_operational_percent']),('unknown_count','>=100',balance['release']['total']),('unknown_sources','>=8',balance['release']['sources']),('unknown_balance','<=25%',balance['release']['max_concentration']),('unknown_types','>=5',balance['release']['type_groups']),('historical_safety','0 false accepts',fa),('canonical','100% unambiguous',can['counts']),('performance','p95<=250ms',perf['latency_ms'])]:gate(name,target,actual,checks[name+'_pass'])
 gate('master_pool','>=120 preferred',balance['master']['total'],balance['master']['total']>=120,False);gate('tests','0 failures',tests,True)
 for name,target in [('v5_known_identities','>=30'),('v5_known_sources','>=6'),('v5_representations','>=400'),('v5_scan_count','>=200'),('v5_valid_fills','>=50'),('v5_unknown_mix','>=30'),('v5_validity','count==unique==expected; schema/atomic/SHA'),('v5_precision','>=99.5%'),('v5_exact_recall','>=90%'),('v5_entity_errors','0'),('v5_version_errors','0'),('v5_scan_recall','>=85%,P>=99.5%'),('v5_filled_recall','>=90%,P>=99.5%'),('unknown_release_rejection','>=99%'),('v5_retrieval_at25','100%;@1 target99%')]:gate(name,target,None,False)
 gate('family','>=5 real families or experimental','experimental / insufficiently validated',False,False);gate('CI','external_pending','external_pending',False,False)
 result=dict(round=11,status='NOT READY',software_version='0.6.1',candidate_target='0.7.0',schema=610,identity=ident,freeze=None,freeze_status='not_created',local_gates_passed=False,gates=gates,tests=tests,ci='external_pending')
 atomic_json(ROOT/'docs/release_gates.json',result)
 empty=dict(status='not_run',reason='Coverage below85%; freeze/evaluationv5 prohibited.',freeze=None,recognition_calls=0,cases=[],summary=dict(cases=0,metrics={},latency_ms={}))
 docs,families=catalog();latest=dict(schema_version=1,benchmark_model='known-family-unknown-v5',round=11,status='NOT READY',software_version='0.6.1',candidate_target='0.7.0',catalog_count=1216,catalog_semantic_sha256=catalog_revision(docs,families),commit=ident['commit'],executed_at=ident['executed_at'],release_gate=result,fingerprint_coverage=dict(status='executed',operational_docs_total=1212,file_backed_operational_docs=1158,fingerprinted_all_operational_docs=cov['fingerprinted_file_backed'],coverage_all=cov['all_operational_percent']/100,coverage_file_backed=cov['file_backed_percent']/100,unambiguous_identities=cov['unambiguous_identities'],shared_only_supported=cov['shared_only_supported'],scope=cov['scope']),known_canonical=dict(status='executed',summary=can['summary']),known_robustness=empty,scan_ocr=empty,filled_forms=empty,unknown_official=dict(empty,reason=f'Release subset{br["total"]}/{br["sources"]}sources, max{br["max_concentration"]:.2%}, selected but not recognized in R11. Prior exposure{br["previously_recognized"]} cases retained; no independent rejection estimate.'),unknown_master_pool=bm,unknown_release_subset=br,unknown_development=dict(status='executed',summary=summary(dev['cases']),scope=dev['scope']),family_identity_holdout=dict(status='experimental',families_evaluable=0,capability_status='insufficiently_validated'),performance=dict(status='executed',latency_ms=perf['latency_ms'],index_bytes=perf['index']['bytes']),evaluations=[dict(name=n,summary=v['summary']) for n,v in hist.items()])
 atomic_json(ROOT/'benchmarks/latest_summary.json',latest)
 def table(rows):return '\n'.join('| '+' | '.join(str(c).replace('|','/') for c in row)+' |' for row in rows)
 actual_display={
  'coverage_file_backed':f"{cov['file_backed_percent']:.6f}%",
  'coverage_all':f"{cov['all_operational_percent']:.6f}%",
  'unknown_balance':f"{br['max_concentration']:.6%}",
  'historical_safety':f'{len(fa)} false accept / {len(no)} NO storici',
  'canonical':f"{can['counts']['exact']}/980; wrong {can['counts']['wrong']}",
  'performance':f"p50 {perf['latency_ms']['p50']:.4f} ms; p95 {perf['latency_ms']['p95']:.4f} ms",
  'tests':f"{tests['passed']} passed / {tests['failed']} failed / {tests['skipped']} skipped",
 }
 gt=table([['Gate','Target','Risultato','Esito'],['---']*4]+[[g['gate'],g['target'],actual_display.get(g['gate'],'non misurato' if g['actual'] is None else str(g['actual'])),g['status']] for g in gates])
 ht=table([['Corpus','Corretti','Totale'],['---']*3]+[[k,v['summary']['passed'],len(v['cases'])] for k,v in hist.items()])
 per=table([['Fonte','Operative','File-backed','Supportate','Univoche','Shared-only','Residue'],['---']*7]+[[k,*[v[x] for x in ['operational_total','file_backed_total','fingerprinted','unambiguous','shared_only','remaining']]] for k,v in cov['per_source'].items()])
 body=f'''# Round 11 — NOT READY

Software pubblico **0.6.1**, target **0.7.0**, schema **610**. Branch `codex/coverage-benchmark-v0.7.0`. All'ingresso HEAD era `{baseline['commit']}` e il working tree era pulito. HEAD durante la generazione del report: `{ident['commit']}`. Commit finale e SHA dell'archivio sono registrati dopo il commit in `dist/package-verification-round11.json` e nella consegna, per evitare autoreferenze. Nessun push, tag, release o freeze. CI `external_pending`.

## Decisione

Il benchmark unknown supera i minimi per conteggio, fonti, bilanciamento e tipi. La copertura file-backed resta **{cov['file_backed_percent']:.6f}%**, inferiore all'85%: `ready_to_freeze=false`. Per questo non sono stati eseguiti freeze, evaluation v5 o preparazione RC.

Motore, soglie, pesi, tier, veti ente/versione, family e profili restano invariati. È stata aggiunta una sola fingerprint ufficiale, per l'ID 178. Tutti i 1027 record v3 originari sono conservati; la serializzazione del loro prefisso ricostruisce esattamente il bundle Round 10. Il nuovo dataset ha un proprio SHA, distinto da quello dei byte semantici del motore.

## Coverage: target e risultato

Baseline ricalcolata: **1158 file-backed**, **941 identità con supporto univoco**, minimo **985** per l'85%, deficit iniziale **44**. Il target prudenziale era di 49–54 recuperi, se disponibili. Il denominatore R6 include ancora l'ID 166, anche senza `download_url`; non è stato ridotto per blocchi, formati o errori. Baseline: 758 test passati e 3 skipped, canonical 979/979, 241 NO storici correttamente rifiutati, p95 Round 10 di 146.0866 ms.

Risultato: **{cov['fingerprinted_file_backed']}/1158 = {cov['file_backed_percent']:.6f}%**; sul totale operativo, **{cov['fingerprinted_file_backed']}/1212 = {cov['all_operational_percent']:.6f}%**. Il recupero rispetto alla metrica iniziale è di {cov['recovered_round11']}: una nuova firma e 33 identità già associate a risorse condivise, dichiarate eleggibili dopo audit. Il totale comprende **942 identità con supporto univoco** e **33 con solo supporto condiviso**. La copertura univoca da sola è {100*cov['unambiguous_identities']/1158:.6f}%. Restano 183 record senza supporto eleggibile e **10 identità mancanti** rispetto al minimo di 985.

Round 11 autorizza esplicitamente il supporto da risorsa condivisa. Questa metrica è separata dalle serie unambiguous R6–10, che restano immutate. Il risultato non rappresenta 34 nuove fingerprint o 34 nuove identità esatte. Nessuna risorsa condivisa entra nella canonical accuracy univoca.

{per}

Pass finale sui 217 residui delle fonti catalogate: 21 richieste maintenance, con robots, allowlist, URL finale e SHA verificati; nessun nuovo tentativo sui blocchi 403/429/404/robots già noti, né aumento dei limiti. MEF e ANAC non hanno residui file-backed da riprovare. Il resolver segue soltanto pagine Garante con etichetta correlata e relativi allegati ufficiali; i test offline escludono navigazione generica e domini estranei.

I record 174 e 177 hanno byte già associati ad altre identità: le nuove associazioni richiederebbero una nuova valutazione del gruppo e non sono contate senza integrazione shared sicura. Il record 178 ha titolo completo e guardie d'identità esistenti compatibili ed è aggiunto come DOCX originale ufficiale.

Audit manuale delle 48 associazioni shared storiche: URL, SHA, binding e scopo effettivo. Sono escluse dalla nuova copertura le associazioni 176 (TFTP rispetto alla scheda Segnalazione), 583 (Allegato 2 rispetto all'Allegato 3), 921 (lista nazionale rispetto alla domanda regionale), 983 (Libro unico rispetto a Stati paga), 1151 (allegato rispetto alla domanda principale). Il binding 1186 ai parametri statistici è escluso; altri modelli 20SM pertinenti restano resource-only. L'ID 166 è soltanto una scheda informativa associata alla procedura Segnalazione, non un modulo univoco. Nessuna correzione retroattiva della provenienza storica o modifica automatica del catalogo.

Il runtime mantiene `status=shared`, gruppi per SHA e requisiti di codice univoco, ente/versione e margine. Il test diretto della fingerprint policy sulle risorse condivise non osserva alcun tier `A_exact_sha`. Gli input senza disambiguazione restano ambigui; non si attribuisce capacità di identificazione univoca a questi 33 ID.

Legacy: 63 risorse già esaminate nel Round 10, con tentativi deduplicati. Sono stati riprovati solo i due candidati utili 422/1101 con il profilo corretto LibreOffice: conversioni e fingerprint di contenuto restano maintenance-only, con SHA originale e derivato separati e output temporanei eliminati. Nessun file convertito è in Git. Il contratto MIME del runtime non ammette gli originali RTF/XLSX; nessuna firma derivata è presentata come PDF ufficiale, né si rivendica supporto per upload legacy.

## Unknown: master e release

Matematica iniziale: 107 casi, 7 fonti, 45 MIMIT e 62 da altre fonti. Con N=100 il cap MIMIT è 25: servivano almeno 13 nuovi non dominanti e una nuova fonte. Master finale: **{bm['total']} casi, {bm['sources']} fonti e {bm['entities']} enti/autorità ospitanti**, concentrazione massima **{bm['max_concentration']:.2%}**. Tutti i 107 precedenti sono conservati. Le {balance['new_confirmed']} nuove conferme provengono da Interno ({bm['counts_per_source'].get('interno',0)}), Giustizia (2) e Piemonte (2). Nessun documento o fonte è stato aggiunto al catalogo.

Conteggi master per fonte: `{json.dumps(bm['counts_per_source'],ensure_ascii=False)}`. Tipi: `{json.dumps(bm['document_types'],ensure_ascii=False)}`. Con codice: {bm['with_code']}; senza codice: {bm['without_code']}; con versione: {bm['versioned']}; senza versione: {bm['unversioned']}.

Release: **{br['total']} casi, {br['sources']} fonti, {br['entities']} enti, concentrazione massima {br['max_concentration']:.6%}, {br['type_groups']} categorie**. Seed `{SEED}`, cap di 25 per fonte, gruppi near interi ordinati per SHA256(seed:group); nessuna selezione per score, facilità o esito. Tutti i minimi sono superati; i target preferiti di 120 casi release e concentrazione al 20% non sono raggiunti. I 20 MIMIT esclusi dal subset restano nel master come unknown_dev, senza cancellazioni.

Conteggi release per fonte: `{json.dumps(br['counts_per_source'],ensure_ascii=False)}`. Tipi: `{json.dumps(br['document_types'],ensure_ascii=False)}`. Con codice: {br['with_code']}; senza codice: {br['without_code']}; con versione: {br['versioned']}; senza versione: {br['unversioned']}.

Acquisizione: 109 richieste maintenance entro un budget di 140; nuove fonti verificate live e contesto delle pagine già in cache. Etichette generiche come «La circolare» sono integrate con titolo della pagina dettaglio e ricevuta HTML; un modulo allegato conserva il proprio tipo, senza ereditare automaticamente «circolare». Regione Piemonte è ammessa solo nella policy maintenance, con prove primarie in SOURCES.md.

L'audit confronta SHA, titoli, codici, ente/fonte, anno/versione, URL finale, near-duplicate, fingerprint e famiglie prima delle predizioni. Le date provengono dalle ricevute. Nessun anno di legge è trasformato in versione documentale. Il corpus contiene moduli, circolari e istruzioni; non garantisce rappresentatività di ogni unknown reale.

Registro truth v2 base e addendum R10 immutati. Addendum R11 separato con {len(new_truth)} prove motivate (nuovi unknown e nuova risorsa canonica), hash del registro base, ricevute effettive e nessuna promozione editoriale. Le vecchie classificazioni R10 restano disponibili nel loro audit; il nuovo contesto documenta perché alcuni candidati prima ambigui sono confermati ora.

SHA e gruppi near release/dev sono disgiunti. Esposizione storica: **{br['previously_recognized']} casi release già riconosciuti in round precedenti, {fresh} mai riconosciuti prima**; nessuno è stato riconosciuto nel Round 11. La selezione non rende indipendenti i casi già visti. In un eventuale futuro mix end-to-end si dovrebbero usare almeno 30 dei {fresh} casi freschi, senza tuning. La rejection release resta **non misurata**.

Sono stati rieseguiti soltanto i {dev['actual_count']} development: false accept {dev['false_accepts']}, errori di estrazione {dev['extraction_failed']}. È stato usato il writer transazionale R9, con count, unique IDs, SHA e journal escluso da Git; export SHA `{dev['observations_sha256']}`.

## Safety, canonical e performance

NO storici: **{len(no)} osservazioni, zero false accept**. R061 e i due casi Round 8 sono NO; i cinque vecchi casi ufficiali critici sono correttamente gestiti. Canonical: **980/980** (979 originari più il nuovo 178), zero wrong e zero estrazioni fallite, su 942 identità unambiguous. Le label v1 ambigue restano visibili: base 33/35 e locked v1 59/69. Nessun tuning per migliorarle.

{ht}

Recognition-only: 402 richieste nel medesimo protocollo isolato R9/R10. **p50 {perf['latency_ms']['p50']:.4f} ms; p95 {perf['latency_ms']['p95']:.4f} ms**, gate 250 ms {'PASS' if checks['performance_pass'] else 'FAIL'}. PDF digitali: p95 {perf['by_input_group']['representation:digital_pdf']['p95']:.4f} ms; scansioni con testo OCR già disponibile: {perf['by_input_group']['historical_scans']['p95']:.4f} ms. Tempi dell'estrazione OCR separata, in ms: `{json.dumps(perf['ocr_end_to_end_extraction_ms'])}`. Sono scansioni sintetiche, non un collaudo generalizzato su acquisizioni personali. Nessuna ottimizzazione o cache globale degli input aggiunta.

Il p95 è superiore ai 146.09 ms del Round 10 e il margine sul gate è soltanto **{250-perf['latency_ms']['p95']:.4f} ms**. Non è stata isolata la causa della variazione tra esecuzioni; non si attribuisce un cambiamento semantico al motore né si sostituisce la misura finale con una ripetizione più favorevole.

Indice: {perf['index']['bytes']} bytes. RSS dopo il warm-up: {perf['rss']['after_warm_bytes']} bytes, crescita {perf['rss']['growth_after_warm_bytes']} bytes; stabilità della memoria di processo ancora non dimostrata. Il gate aggregato non implica che ogni formato sia sotto 250 ms.

## Prerequisiti, freeze ed evaluation

Il file `benchmarks/results/round11/prerequisite_gate.json` registra tutti i campi del gate. Solo `coverage_file_backed_pass` è false tra i prerequisiti; `ready_to_freeze=false`. Freeze non eseguito, commit freeze assente.

Evaluation v5 non costruita né eseguita: identità note non selezionate; rappresentazioni, scansioni, compilazioni valide, unknown mix e retrieval @1/@5/@10/@25 non misurati. Nessun risultato mancante è trattato come zero o PASS. I raw interrotti Round 8 e tutti gli storici sono conservati. Family: **experimental / insufficiently validated**, zero famiglie reali identity-held-out qualificabili nella misura R9 invariata; non usata per useful recall.

Suite finale: **{tests['passed']} passed, {tests['failed']} failed, {tests['skipped']} skipped**, {tests['seconds']:.2f} secondi, Python {tests['python']} su {tests['platform']}. I tre skip riguardano il privilegio Windows per symlink e due test FIFO. SHA del log: `{tests['log_sha256']}`. I 4 test infrastrutturali finali sono passati anche separatamente, senza sommarli due volte. Baseline 758/3 e suite finale restano distinte. Test offline di resolver, quote, titoli e writer R9 (interruzione, resume, dedupe, schema, count, SHA) rieseguiti.

Seed immutato: 1216 record reali, 1212 operativi, 19 fonti, 16 famiglie; integrità e provenance verificate. La verifica riguarda Windows locale; non si rivendicano validazione editoriale o collaudi su altre piattaforme. CI **external_pending**: i comandi legacy v1 conservano le divergenze note dalle label positive ambigue, quindi non si dichiara CI verde.

{gt}

## Archivio e limiti

Archivio: `dist/BurOCRazia-v0.7.0-candidate-NOT-READY-round11.zip`, prodotto da HEAD committato. Commit finale e SHA256 sono in `dist/package-verification-round11.json` e `.zip.sha256`, esterni al proprio contenuto per evitare autoreferenze. Verifica del package: seed, corpus, byte sorgenti, raw storici, record fingerprint precedenti e igiene. Archivi Round 8/9/10 conservati.

Unico prerequisito rimasto insufficiente: copertura 84.20%, deficit di 10 identità. Ulteriori limiti: nessuna v5 indipendente, {br['previously_recognized']} unknown release già visti, family sperimentale, legacy non integrati, RSS non stabilizzata, margine prestazionale ridotto e CI pending. Software pubblico invariato a **0.6.1**.
'''
 (ROOT/'docs/ROUND11_REPORT.md').write_bytes(body.encode())
 intro=f'Round 11 **NOT READY**, pubblico 0.6.1/schema 610. Coverage supporto risorsa 975/1158=84.196891%, di cui 942 unambiguous e 33 shared-only; non confondere con canonical 980/980. Master unknown {bm["total"]}, release {br["total"]}/{br["sources"]} fonti/max {br["max_concentration"]:.6%}, senza predizioni release R11. p95 {perf["latency_ms"]["p95"]:.2f}ms; tests {tests["passed"]} passati/{tests["skipped"]} skip. Nessun freeze/v5. Dettagli: [rapporto Round 11](ROUND11_REPORT.md).'
 for name in ['BENCHMARK.md','FINGERPRINT_COVERAGE_AUDIT.md']:
  path=ROOT/'docs'/name;old=path.read_text(encoding='utf8');start='<!-- round11-current -->';end='<!-- /round11-current -->'
  if start in old:old=old[old.index(end)+len(end):].lstrip()
  path.write_bytes((start+'\n# Round 11\n\n'+intro+' Le sezioni successive restano storiche.\n'+end+'\n\n'+old).encode())
 print('R11 final gates',checks,flush=True)

if __name__=='__main__':main()
