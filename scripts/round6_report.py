"""Derive Round 6 reports and release gates from measured raw artifacts."""
from pathlib import Path
import hashlib,json,platform,re,subprocess,sys
from datetime import UTC,datetime
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from benchmarks.round3_audit import catalog,read,write
from benchmarks.evaluate import code_hash,summary
from benchmarks.round4_common import runtime_hash
from src.fingerprint_v2 import revision,PATH,PARAMETERS
from src.recognize import catalog_revision
from scripts.verify_catalog import verify

OUT='benchmarks/results/round6/'
def pct(metric):
    return 'n.d.' if not metric or not metric.get('denominator') else f"{100*metric['value']:.2f}% ({metric['numerator']}/{metric['denominator']})"

def tests():
    raw=(ROOT/'reports/round6-final-tests.log').read_bytes();text=raw.decode('utf8',errors='replace')
    m=re.search(r'(\d+) passed, (\d+) skipped in ([\d.]+)s',text)
    if not m or re.search(r'\b[1-9]\d* failed\b',text) or int(m[1])<655:
        raise ValueError('Full suite not successfully complete')
    r=dict(passed=int(m[1]),failed=0,skipped=int(m[2]),seconds=float(m[3]),python=platform.python_version(),
        platform=platform.platform(),log_sha256=hashlib.sha256(raw).hexdigest())
    initial=(ROOT/'reports/round6-final-initial-failed.log').read_bytes()
    r['initial_attempt']=dict(passed=650,failed=4,skipped=3,seconds=613.79,log_sha256=hashlib.sha256(initial).hexdigest(),
        resolution='Versioned development fixture adds explicit revisions to two positives and their original inputs as prudent negatives. SR211 review-history test now supplies the actual revision. No runtime, profile, frozen historical corpus or evaluation observation changed.')
    for key,filename in [('post_guard','round6-postguard-tests.log'),('post_report','round6-postreport-tests.log')]:
        raw_check=(ROOT/'reports'/filename).read_bytes()
        check=re.search(r'(\d+) passed in ([\d.]+)s',raw_check.decode('utf8'))
        if not check or re.search(rb'\b[1-9]\d* failed\b',raw_check):raise ValueError('Post-check not passed: '+key)
        r[key]=dict(passed=int(check[1]),seconds=float(check[2]),log_sha256=hashlib.sha256(raw_check).hexdigest(),repeated_subset=True)
    write(OUT+'tests.json',r);return r

def main():
    docs,families=catalog();cov=read(OUT+'fingerprint_coverage.json');can=read(OUT+'canonical_v2.json')
    rob=read(OUT+'robustness_v2.json');filled=read(OUT+'filled_forms_v2.json');scan=read(OUT+'scan_ocr_v2.json')
    fam=read(OUT+'family_release.json');unknown=read(OUT+'unknown_official.json');perf=read(OUT+'performance.json')
    acro=read(OUT+'filled_acroform_v2.json');overlay=read(OUT+'filled_static_overlays_v2.json')
    compat=read(OUT+'development_compat_v2.json');cross=read(OUT+'cross_format_same_identity.json')
    # The inherited R5 case helper attached its historical seed to deterministic
    # transforms. Selection actually used the frozen R6 plan; preserve both.
    for name,r in [('canonical_v2',can),('robustness_v2',rob),('filled_forms_v2',filled),('scan_ocr_v2',scan),('filled_acroform_v2',acro),('filled_static_overlays_v2',overlay),('cross_format_same_identity',cross)]:
        for row in r['cases']:
            p=row.get('provenance',{})
            if p.get('seed')==20261011:
                p['legacy_helper_seed']=p['seed'];p['seed']=20261012
        r['technical_metadata_reconciliation']='Case-helper seed corrected to frozen Round6 selection seed 20261012; original helper value retained. No identity label, representation, observation, score or metric changed.'
        write(OUT+name+'.json',r)
    test=tests();five=read(OUT+'historical_five.json');ocr=read(OUT+'ocr_legacy_gate.json');ocr2=read(OUT+'ocr_synthetic_v2.json')
    finals={n:read(OUT+'final/'+n+'.json') for n in ['development_regression','release_locked_v1','release_locked_v2','hard_negatives_v1','hard_negatives_v2','family_release_v3','catalog_coverage']}
    for name,r in [('canonical',can),('robustness',rob),('filled',filled),('scan',scan),('family',fam),('unknown',unknown)]:
        assert summary(r['cases'])['metrics']==r['summary']['metrics'],name
    m=lambda r,k:r['summary']['metrics'][k]['value']
    gates=[]
    def gate(name,target,result,passed,blocking=True):gates.append(dict(gate=name,target=target,actual=result,passed=bool(passed),blocking=blocking))
    gate('coverage_file_backed','>=85%',cov['coverage_file_backed'],cov['coverage_file_backed']>=.85)
    gate('coverage_all','>=70%',cov['coverage_all'],cov['coverage_all']>=.70)
    gate('canonical_precision','100%',m(can,'document_precision'),m(can,'document_precision')==1)
    gate('canonical_recall','100%',m(can,'document_recall'),m(can,'document_recall')==1)
    gate('canonical_wrong','0',can['counts']['wrong'],can['counts']['wrong']==0)
    for name,r,target in [('robustness',rob,.90),('filled_acroform',acro,.90),('scan',scan,.85)]:
        gate(name+'_precision','>=99.5%',m(r,'document_precision'),(m(r,'document_precision') or 0)>=.995)
        gate(name+'_exact_recall',f'>={target:.0%}',m(r,'document_recall'),(m(r,'document_recall') or 0)>=target)
    gate('scan_useful_recall','>=95%',m(scan,'useful_coverage'),(m(scan,'useful_coverage') or 0)>=.95)
    evaluable=fam['families_evaluable']
    if evaluable:
        gate('family_precision','>=99%',m(fam,'family_precision'),(m(fam,'family_precision') or 0)>=.99)
        gate('family_recall','>=80%',m(fam,'family_recall'),(m(fam,'family_recall') or 0)>=.80)
        gate('family_false_accepts','0',fam['false_accepts'],fam['false_accepts']==0)
    gate('family_capability_validation','>=5 evaluable families',evaluable,evaluable>=5,False)
    gate('unknown_rejection','>=99%',m(unknown,'unknown_correct_rejection_rate'),(m(unknown,'unknown_correct_rejection_rate') or 0)>=.99)
    r061=next(r for r in finals['release_locked_v2']['cases'] if r['id']=='R061')
    gate('R061','NO_MATCH',r061['observed']['match_type'],r061['correct'] and r061['observed']['match_type']=='NO_MATCH')
    gate('historical_five','5 safe',sum(r['safe'] for r in five['cases']),five['passed'])
    negatives=sum(finals[n]['summary']['passed'] for n in ['hard_negatives_v1','hard_negatives_v2'])
    gate('historical_negatives','130/130',negatives,negatives==130)
    gate('historical_family_negatives','0 false accepts',finals['family_release_v3']['false_positives'],finals['family_release_v3']['false_positives']==0)
    gate('historical_development_regression','35/35 unchanged labels',finals['development_regression']['summary']['passed'],finals['development_regression']['summary']['failed']==0)
    gate('development_compat_v2','37/37 new representations',compat['summary']['passed'],compat['summary']['failed']==0)
    gate('real_ocr','7/7 +14/14',dict(legacy=ocr['passed'],synthetic=ocr2['summary']['passed']),ocr['full_gate_passed'] and ocr2['summary']['passed']==14)
    gate('warm_p95','<=250ms',perf['latency_ms']['p95'],perf['latency_ms']['p95']<=250)
    gate('warm_p50','<=150ms',perf['latency_ms']['p50'],perf['latency_ms']['p50']<=150)
    gate('index_memory','<=100MB',perf['fingerprints']['index_bytes'],perf['fingerprints']['index_bytes']<=100_000_000)
    gate('tests','0 failures',test['passed'],test['failed']==0)
    catalog_verify=verify(ROOT/'data/catalog_seed.sqlite3')
    gate('unchanged_catalog','1216 identities, same seed SHA',catalog_verify['sha256'],catalog_verify['sha256']=='790b690123c82e1cb7bdfa67a10216284022987d50b0abbcc4a1a245785e3e99')
    ready=all(g['passed'] for g in gates if g['blocking']);status='READY LOCALLY' if ready else 'NOT READY'
    commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    ident=dict(commit=commit,runtime_sha256=runtime_hash(),code_sha256=code_hash(),fingerprint_sha256=revision(),catalog_sha256=catalog_verify['sha256'])
    write('docs/release_gates.json',dict(schema_version=6,round=6,status=status,local_gates_passed=ready,external_ci='pending_external_gate',final_release_allowed=False,identity=ident,gates=gates))
    latest=dict(schema_version=1,benchmark_model='known-family-unknown-v2',status=status,executed_at=datetime.now(UTC).isoformat(),
        commit=commit,catalog_semantic_sha256=catalog_revision(docs,families),catalog_count=1216,operational_count=1212,
        fingerprint_coverage=dict(status='executed',**cov),known_canonical=dict(status='executed',summary=can['summary']),
        known_robustness=dict(status='executed',summary=rob['summary']),filled_forms=dict(status='executed',summary=acro['summary'],interactive_cases=100,templates=5),
        scan_ocr=dict(status='executed',summary=scan['summary']),unknown_official=dict(status='executed',summary=unknown['summary']),
        family_identity_holdout=dict(status='executed',summary=fam['summary'],families_evaluable=evaluable,capability_status=fam['capability_status']),
        hard_negatives=dict(status='executed',correct=negatives,total=130),
        real_ocr=dict(status='executed',result=f"{ocr['passed']}/7 + {ocr2['summary']['passed']}/14"),
        performance=dict(status='executed',latency_ms=perf['latency_ms'],index_bytes=perf['fingerprints']['index_bytes'],startup_ms=perf['startup_ms']),
        ocr_status=f"Tesseract reale: {ocr['passed']}/7 storico, {ocr2['summary']['passed']}/14 sintetico",
        evaluations=[dict(name=name,summary=r['summary']) for name,r in [('Canonical exact-file',can),('Interactive AcroForms',acro),('Static overlays',overlay),('Historical regression',finals['development_regression']),('Development compatibility v2',compat),('Historical locked v1',finals['release_locked_v1']),('Historical locked v2',finals['release_locked_v2']),('Historical negatives v1',finals['hard_negatives_v1']),('Historical negatives v2',finals['hard_negatives_v2']),('Canonical metadata coverage',finals['catalog_coverage'])]])
    write('benchmarks/latest_summary.json',latest)
    metric_rows=[]
    for name,r in [('Canonical exact-file',can),('Robustness evaluation',rob),('Interactive AcroForms (5 templates)',acro),('Static overlays (weaker perturbation)',overlay),('Scan/OCR',scan)]:
        c=r['counts'];metric_rows.append(f"| {name} | {r['summary']['cases']} | {c['exact']} | {c['family']} | {c['reject']} | {c['wrong']} | {pct(r['summary']['metrics']['document_precision'])} | {pct(r['summary']['metrics']['document_recall'])} |")
    plan=rob['plan'];gate_lines='\n'.join(f"| {g['gate']} | {g['target']} | {g['actual']} | {'PASS' if g['passed'] else 'FAIL'} | {'sì' if g['blocking'] else 'no'} |" for g in gates)
    transform_lines='\n'.join(f"| {name} | {s['cases']} | {s['passed']} | {pct(s['metrics']['document_precision'])} | {pct(s['metrics']['document_recall'])} |" for name,s in rob['by_transformation'].items())
    source_lines='\n'.join(f"| {name} | {r['operational_docs_total']} | {r['file_backed_operational_docs']} | {r['fingerprinted_all_operational_docs']} |" for name,r in cov['by_source'].items())
    report=f"""# Round 6 — {status}

## Stato, versione e prove

Software **0.6.1**, target **0.7.0**, schema **610**. Branch `{subprocess.check_output(['git','branch','--show-current'],text=True).strip()}`.
Commit di congelamento runtime/calibrazione **`ce6fa61f432c204e3d4c8029ef370ff27e429455`**; HEAD alla generazione `{commit}`.
Il runtime e il profilo sono invariati dopo l'apertura dell'evaluation. Gli hash dei byte identificano ciascuna misura;
nessun push, tag o rilascio. Runtime SHA `{ident['runtime_sha256']}`; bundle v2 SHA `{ident['fingerprint_sha256']}`.
Baseline: 615 passed, 3 skip; dati storici v1 e Round 5 conservati, senza sostituire metriche o etichette.

## 1. Catalog coverage

1.216 reali, 1.212 operativi, quattro rifiutati; **zero nuove identità**. Seed SHA `{catalog_verify['sha256']}`,
integrity/FK OK e provenienze 1.216/1.216. Nessuna nuova verifica editoriale.
Copertura da soli metadati: {finals['catalog_coverage']['summary']['passed']}/1212, distinta dal riconoscimento di file reali.

## 2. Fingerprint coverage

File-backed {cov['file_backed_operational_docs']}; firme attive per {cov['fingerprinted_all_operational_docs']} identità;
copertura totale {cov['coverage_all']:.2%}, file-backed {cov['coverage_file_backed']:.2%}.
Risorse canoniche {cov['canonical_resources']}, attive {cov['active_resources']}, in quarantena {cov['quarantined_resources']}.
Servizi dinamici {cov['dynamic_service_docs']}; metadata-only {cov['metadata_only_docs']}.
Denominatore: {cov['denominator_policy']}

| Fonte | Operativi | File-backed | Fingerprinted identities |
|---|---:|---:|---:|
{source_lines}

Assenze: `{json.dumps(cov['missing_reason_breakdown'],ensure_ascii=False)}`.
I CSV contengono le 843 assenze iniziali, le assenze finali e tutti gli stati tecnici.
Nuove firme tra le assenze v1: {cov['newly_fingerprinted_missing_v1']}; firme v1 conservate attive anche in v2: {cov['retained_v1_identities']}.
Identità v1 escluse dalla v2 attiva: `{cov['v1_ids_without_active_v2']}`; motivi tecnici nel CSV final. Il bundle v1 resta invariato.
{cov['network_requests']} richieste sequenziali complessive, robots/allowlist/redirect verificati; nessun bypass.
Multipart INPS: derivazione MIME tracciata con hash del contenitore e del payload.
Formati e lingue alternativi provengono dalle osservazioni immutabili già associate alle identità.

## 3. Canonical exact-file recognition

| Prova | N | Exact | Family | NO | Wrong | Precision | Exact recall |
|---|---:|---:|---:|---:|---:|---|---|
{chr(10).join(metric_rows)}

Canonical misura ogni risorsa attiva, comprese alternative della stessa identità; non generalizzazione a identità sconosciute.
Subset cross-format: {cross['summary']['passed']}/{cross['summary']['cases']} risorse PDF/DOCX di 11 identità;
prova SHA dei file canonici, senza claim di generalizzazione scan cross-format DOCX.
I sette NO Round 5 hanno cause contestuali documentate in `canonical_failures.csv`:
anno del comunicato/competenza, anno della delibera/contributo, data di revisione, COMUNE come campo e qualificatori nel corpo.
Le correzioni sono generali; nessuna whitelist di ID o bypass di conflitti espliciti di ente/versione.
Risorse in conflitto sono escluse tecnicamente e conservate nell'audit, senza revoche editoriali.

## 4. Robustness recognition

Calibration identities: `{plan['calibration_identities']}`. Evaluation identities: `{plan['evaluation_identities']}`.
Split e SHA delle risorse congelati prima delle rappresentazioni. Soglie/pesi tarati solo sulle identità di calibration;
il profilo congelato e lo SHA runtime sono verificati prima dell'evaluation. Nessuna ritara dopo i risultati.
La prima taratura e il relativo profilo sono conservati in `calibration_initial/`:
prima di aprire evaluation sono state ampliate le soglie di containment caratteri (pagina singola contro documento intero)
e corretto il veto della revisione mancante nel fallback metadata. La revisione finale usa ancora soltanto gli otto ID calibration.
Soglie finali: text 0,75, char containment 0,15, anchors 0,60, visual 0,88, margine 0,02,
almeno 20 sovrapposizioni. Pesi 0,50/0,25/0,15/0,10. L'obiettivo della griglia dà 116/128 corretti
e zero wrong **prima dei veto di sicurezza**; non è un richiamo osservato end-to-end di 116/128.
Le fingerprints delle identità evaluation esistono: prova di rappresentazione dello stesso documento, non identity holdout.

| Trasformazione | N | Exact correct | Precision | Recall |
|---|---:|---:|---|---|
{transform_lines}

Candidate retrieval@K: `{json.dumps(rob['candidate_recall_at_k'])}`.
Il ranking diagnostico non applica SHA né veto; il runtime conserva tutti i candidati con evidenza minima.
`rejection_diagnostics.json` distingue fusion insufficiente da candidati eleggibili poi rifiutati;
un motivo generico non viene attribuito arbitrariamente a un particolare veto.
`evaluation_locks.json` verifica a posteriori l'uguaglianza dei byte col commit di congelamento,
senza inventare un evento di lock precedente. Il pacchetto controlla anche questi hash.
Expected fuori top25 indica un problema di recupero; dentro top25 e NO indica scoring/veto/margine.
Righe di scoring diagnostico limitate a top25, rank atteso calcolato sull'intera lista.
Il seed del helper storico nei metadati dei casi è riconciliato con il piano Round6 (20261012);
il valore ereditato 20261011 è conservato separatamente. Nessuna osservazione, etichetta o metrica è cambiata.
Runner scansioni con tre worker disgiunti e `OMP_THREAD_LIMIT=1`; ordine finale deterministico.

## 5. Filled-form robustness

{filled['summary']['cases']} casi totali: **100 AcroForm reali su cinque template**, venti varianti ciascuno;
**70 overlay statici**, dieci varianti su sette risorse. Gli overlay includono documenti non compilabili e sono
perturbazioni di contenuto più deboli: non costituiscono 70 moduli compilati. Il gate usa separatamente i 100 AcroForm.
La matrice originale 120 casi è conservata; un supplemento di 50 AcroForm è pianificato prima della generazione,
selezionando tutti i cinque template evaluation con campi presenti, senza cambiare soglie o consultare esiti per selezionarli.
Il generatore usa nomi, CF non validi, indirizzi, date, importi, testo e checkbox sintetici quando i campi sono identificabili.
Casi correlati entro template.
Le verifiche richiedono `/V` nel field tree, valore del widget e appearance riaperta;
ambiguità/orfani non riparati automaticamente. Campi sintetici non costituiscono compilazione legale.
Quando il nome del campo è generico, il filler usa `EsempioN`: la prova dimostra la modifica di campi reali,
senza garantire plausibilità semantica o correttezza di date/CF in tutti i campi. Questo limite resta aperto.
Dipendenza facoltativa del benchmark: `pypdf==6.10.0` in `benchmarks/requirements-round6.txt`, non importata dal runtime.

## 6. Scan/OCR robustness

{scan['summary']['cases']} scansioni generate; OCR estratto con successo {scan['ocr_extraction_success']}.
Exact recall {pct(scan['summary']['metrics']['document_recall'])}; useful recall {pct(scan['summary']['metrics']['useful_coverage'])}.
Ogni errore di estrazione resta nel denominatore. Prime pagine PDF a 150/200 dpi, JPEG, crop, blur,
contrasto, resize e rotazioni. Non sono scansioni reali di utenti, manoscritti o foto da telefono.
OCR canonico: prima pagina PDF 144 dpi, stesso Tesseract/lingue del runtime, senza persistere testo o immagini.
DOCX: canale digitale; renderer locale non disponibile, nessun claim OCR/visual o scan cross-format per DOCX.

## 7. Family identity-holdout

16 famiglie totali; {evaluable} valutabili. Held-out reali osservati in via esplorativa:
{len(fam['exploratory_cases'])}; casi con numerosità release-grade {fam['summary']['cases']}.
Identità held-out esplorative: `{[c['provenance']['document_id'] for c in fam['exploratory_cases']]}`;
split per tutte le 16 famiglie in `family_evaluability.csv` e `family_release.json`.
Nel solo subset esplorativo: {fam['exploratory_summary']['passed']}/{fam['exploratory_summary']['cases']} corretti,
recall {pct(fam['exploratory_summary']['metrics']['family_recall'])}; non confluisce nelle macro release-grade.
Precision {pct(fam['summary']['metrics']['family_precision'])}, recall {pct(fam['summary']['metrics']['family_recall'])},
macro `{fam['macro']}`, false accepts {fam['false_accepts']}.
Capability `{fam['capability_status']}`; meno di cinque famiglie non blocca la RC known-document, ma non valida family.
Nessuna nuova frase imparata dalle identità held-out. Hard negatives sintetici famiglia separati: 81,
{finals['family_release_v3']['false_positives']} false accept; non sostituiscono file ufficiali di identità nuove.

## 8. Unknown official rejection

{unknown['summary']['cases']} SHA ufficiali storici distinti, {unknown['counts']['reject']} NO,
{unknown['counts']['wrong']} accettazioni erronee; rifiuto corretto {pct(unknown['summary']['metrics']['unknown_correct_rejection_rate'])}.
Tutti i negativi storici conservati. Zero ulteriori unknown non visti: la cache aggiuntiva contiene risorse di identità note
o file privi di etichette unknown adjudicate; non si assegnano etichette negative automaticamente dal titolo.

## 9. Historical regressions

Regressione storica immutata **{finals['development_regression']['summary']['passed']}/35**: EX02/EX03 ora NO perché
non esplicitano revisione 1.1; il gate storico stretto resta FAIL. Nuova fixture di sviluppo `tests/fixtures/benchmark_v2.json`
**{compat['summary']['passed']}/37**: revisioni aggiunte a due nuovi input positivi, testi originali mantenuti in due nuovi negativi,
parent SHA e motivazioni nel file. Non sostituisce il 33/35 storico e non è evaluation indipendente.
Locked v2 {finals['release_locked_v2']['summary']['passed']}/69;
locked v1 storico {finals['release_locked_v1']['summary']['passed']}/69, senza sostituzione delle etichette.
Negativi storici {negatives}/130; R061 {r061['observed']['match_type']}; cinque false accettazioni storiche sicure {sum(r['safe'] for r in five['cases'])}/5.
OCR reale storico {ocr['passed']}/7 e sintetico {ocr2['summary']['passed']}/14; test mock, OCR reale ed editoria restano distinti.

## 10. Performance

Startup catalogo {perf['catalog_load_ms']:.2f} ms, indice {perf['index_build_ms']:.2f} ms;
warm p50 {perf['latency_ms']['p50']:.2f} ms, p95 {perf['latency_ms']['p95']:.2f} ms,
{perf['latency_ms']['n']} campioni, {perf['synthetic_cases']} sintetici + {perf['official_known_cases']} file ufficiali.
Inferenza warm esclude estrazione/OCR e generazione visual, misurati separatamente per caso.
Il p95 Round 5 era 128,16 ms: il nuovo indice aumenta copertura ma questa misura Round 6 peggiora la coda
oltre il limite. Non viene presentato come ottimizzazione prestazionale conclusa.
Ambiente {test['platform']}, Python {test['python']}; nessuna certificazione Linux/macOS.

## 11. Memory, test, CI e gate

Bundle v2 {perf['fingerprints']['disk_bytes']} byte; indice {perf['fingerprints']['index_bytes']} byte.
RSS dopo warm {perf['rss']['after_warm_bytes']} byte; crescita warm {perf['rss']['growth_after_warm_bytes']} byte.
Array, posting e pesi IDF sono nella misura ricorsiva Python; RSS dell'intero processo è separato.
V1 resta su disco per compatibilità/storico e non viene caricata nel percorso v2 operativo.
Nessun upload o suo sketch viene conservato in cache.

Test completi: {test['passed']} passed, {test['failed']} failed, {test['skipped']} skip Windows,
{test['seconds']} s. Migrazioni ripetute su copie di v0.6.1, Round4 e Round5, integrity/FK;
Primo tentativo finale: 650 passed, quattro failed, tre skip (613,79 s), log/hash conservati.
Le quattro asserzioni dipendevano dai due input storici senza revisione e dal test storico SR211;
risolte con fixture v2 e revisione esplicita nel test dello storico editoriale, senza indebolire il runtime congelato.
schema invariato 610. Bootstrap/CLI/benchmark locali documentati in `ci_local.json`.
Sottoinsiemi ripetuti dopo gli ultimi aggiornamenti: {test['post_guard']['passed']} test CLI/protezione fixture;
{test['post_report']['passed']} test UI/fingerprint dopo il nuovo riepilogo statico. Non sono nuovi test aggiunti al totale 655.
CI esterna **pending_external_gate**: anche READY LOCALLY consentirebbe solo RC locale.
Il comando storico `benchmarks.evaluate --fast` termina con codice 1 per EX02/EX03;
il wrapper di riproduzione conserva quel FAIL e verifica che siano gli unici due rifiuti aggiunti prima delle altre prove.
La CLI corrente sulla fixture di sviluppo v2 passa; non rende verde il gate storico.
Il primo lancio del wrapper performance non ha scritto risultati perché un avviso PDF nativo contaminava stdout;
è stata corretta soltanto la lettura della singola riga JSON e ripetuta la misura isolata, senza cambiare il protocollo.

| Gate | Target | Risultato | Esito | Bloccante |
|---|---|---|---|---|
{gate_lines}

Limiti: OCR/visual solo prima pagina PDF; DOCX senza renderer; scansioni e dati compilati sintetici;
unknown e family non sono una nuova prova prospettica; fonti bloccate/legacy non aggirate;
nessuna nuova revisione editoriale o nuova spiegazione. Le metriche non sono una probabilità né un consiglio personalizzato.

Archivio locale: `dist/BurOCRazia-v0.7.0-{'RC1' if ready else 'candidate-NOT-READY'}-round6.zip`.
SHA256 e verifica byte/lock/hygiene in `dist/package-verification.json` e nel file `.zip.sha256`,
generati dopo il commit per evitare riferimenti circolari. Nessun cache ufficiale, database personale o documento di terzi nello ZIP.
"""
    (ROOT/'docs/ROUND6_REPORT.md').write_bytes(report.encode())
    (ROOT/'docs/BENCHMARK.md').write_bytes(report.replace('# Round 6 —','# Benchmark Round 6 —',1).encode())
    fp=f"""# Deterministic content fingerprints

Software 0.6.1; candidata Round 6 {status}. V1 è preservata in `data/document_recognition_fingerprints.json`.
V2 separata in `data/document_recognition_fingerprints_v2.json`, schema JSON dedicato;
nessuna migrazione SQL aggiuntiva (610). Schema rigido, limiti, scrittura atomica e idempotente.

Canali: SHA file esatto, token trigrams digitali e OCR canonico, char 4/5/6-gram,
containment pesato, etichette stabili nei primi 2.000 caratteri, struttura diagnostica,
dHash 256 bit in quattro orientamenti. Struttura non usata come prova autonoma.
IDF deterministico `log((N+1)/(df+1))+1`, snapshot corrispondente allo SHA bundle `{revision()}`.
N e df contano risorse canoniche attive; il ranking viene poi aggregato per identità.
Hash SHA256 separati per dominio, troncati a 64 bit, >=20 sovrapposizioni e corroborazioni;
collisioni isolate non autorizzano accettazione. Nessuna probabilità associata allo score.

Fusion: SHA unico + veto; altrimenti testo/OCR + char + etichette oppure layout,
o testo moderato + char + layout molto vicino + etichette, con margine tra identità.
I segnali complementari non sono dichiarati statisticamente indipendenti.
Conflitti espliciti ente, annualità/modello, revisione, allegato e sottotipo prevalgono sulla somiglianza.
Anno di competenza, citazioni legali e date di revisione non sono automaticamente la versione del modello.
Titoli/emittenti oltre i primi 2.000 caratteri non forniscono prove forti di identità.

OCR canonico PDF: prima pagina a 144 dpi, stesso `src.ocr` del runtime, Tesseract locale.
Solo gli sketch e metadati del motore/lingue/traineddata sono conservati; immagini e testo sono temporanei in memoria.
DOCX: digitale disponibile, OCR/visual indisponibili senza renderer. Nessun download del runtime.
Multiple risorse possono appartenere a un'identità; il ranking aggrega per identità.
Stale e quarantined esclusi; SHA condiviso tra identità non seleziona arbitrariamente un record.
Un aggiornamento necessita nuova acquisizione e riconciliazione; la data di cache non prova attualità sul sito.

Build solo `maintenance/`, rete esplicita `--allow-network`, URL ufficiali/robots/redirect/rate limit.
Runtime offline; nessun import maintenance o benchmark, nessun fetch, API o aggiornamento implicito.
Cache solo di firme canoniche pubbliche; upload features, pixel e testi sono request-local.
Riavviare `run.py` dopo una build: il processo carica una sola versione del bundle pubblico in cache.
Calibrazione congelata: `benchmarks/results/round6/fingerprint_calibration.json`; split per identità separato.
Copertura e limiti misurati: `FINGERPRINT_COVERAGE_AUDIT.md`, `BENCHMARK.md`.
Stati tecnici nel CSV `operational_support.csv` separati da revisione e provenienza storica.
"""
    (ROOT/'docs/FINGERPRINTS.md').write_bytes(fp.encode())
    readme=ROOT/'README.md';text=readme.read_text(encoding='utf8')
    text=re.sub(r'## Benchmark\n.*?(?=\n## |\Z)',f"## Benchmark\n\nCandidata Round 6 **{status}**, software pubblico 0.6.1. Catalogo: 1.216 identità reali, 1.212 operative, zero nuove identità nel Round 6. Copertura firme: {cov['fingerprinted_all_operational_docs']}/1212 ({cov['coverage_all']:.2%}); canonical {can['counts']['exact']}/{can['summary']['cases']}; robustness {rob['counts']['exact']}/{rob['summary']['cases']}. Gate, denominatori e limiti in [BENCHMARK.md](docs/BENCHMARK.md) e [ROUND6_REPORT.md](docs/ROUND6_REPORT.md). CI esterna non eseguita.\n",text,flags=re.S)
    readme.write_bytes(text.encode())
    english=ROOT/'README_EN.md';text=english.read_text(encoding='utf8')
    text=re.sub(r'## Benchmark\n.*?(?=\n## |\Z)',f"## Benchmark\n\nRound 6 candidate **{status}**; public software remains 0.6.1. Catalog: 1,216 real identities, 1,212 operational; no new identities in this round. Fingerprint coverage: {cov['fingerprinted_all_operational_docs']}/1212 ({cov['coverage_all']:.2%}); canonical {can['counts']['exact']}/{can['summary']['cases']}; robustness {rob['counts']['exact']}/{rob['summary']['cases']}. Denominators, gates and limits: [BENCHMARK.md](docs/BENCHMARK.md), [ROUND6_REPORT.md](docs/ROUND6_REPORT.md). External CI is pending.\n",text,flags=re.S)
    english.write_bytes(text.encode())
    for filename in ['CHANGELOG.md','docs/VALIDAZIONE.md','DATA_NOTICE.md']:
        path=ROOT/filename
        if not path.exists():continue
        text=path.read_text(encoding='utf8');marker='\n## Round 6'
        if marker in text:text=text[:text.index(marker)]
        text+=f"\n## Round 6 — {status}\n\nFirme v2 e benchmark separati per copertura, canonical, robustezza, compilazione, OCR, family, unknown, regressioni, memoria e latenza. Zero nuove identità; seed/schema 610 invariati. V1 e corpus storici conservati. Tutti i dati sintetici compilati sono fittizi; nessun file ufficiale o testo OCR redistribuito. Dettagli e limiti in `docs/ROUND6_REPORT.md`.\n"
        path.write_bytes(text.encode())
    print(status,'failed blocking gates:',[g['gate'] for g in gates if g['blocking'] and not g['passed']])

if __name__=='__main__':main()
