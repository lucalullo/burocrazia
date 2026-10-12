"""Publish qualified evidence only; missing independent evaluation stays empty."""
import argparse,csv,hashlib,json,platform,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from benchmarks.round8_common import read,catalog,identity
from benchmarks.transactional_writer import atomic_json
from benchmarks.round9_freeze import prerequisites
from benchmarks.evaluate import summary
from src.recognize import catalog_revision
OUT='benchmarks/results/round9/'

def table(rows):return '\n'.join('| '+' | '.join(str(c).replace('|','/') for c in row)+' |' for row in rows)
def main():
    p=argparse.ArgumentParser();p.add_argument('--preliminary',action='store_true');args=p.parse_args()
    can=read(OUT+'canonical.json');cov=read(OUT+'fingerprint_coverage.json');perf=read(OUT+'performance.json');unknown=read(OUT+'unknown_v1.json');manifest=read('benchmarks/manifests/official_unknown_v1.json');truth=read('benchmarks/reference/reference_truth_v2.json');family=read(OUT+'family_release.json');baseline=read(OUT+'baseline_audit.json')
    cal=read(OUT+'calibration_v5.json') if (ROOT/OUT/'calibration_v5.json').exists() else dict(status='running',false_accepts=None,wrong_known=None,identity_ids=[],known_metrics={})
    if not args.preliminary:assert cal['status']=='development_replay_complete'
    checks=prerequisites(coverage=cov,performance=perf,unknown=manifest,canonical=can,calibration=cal)
    assert not all(checks.values()),'Prerequisites green: run actual frozen v5 instead of a NOT READY report'
    ident=identity();blocked=[k for k,v in checks.items() if not v];reason='Freeze v5 non creato: '+', '.join(blocked)+'. Nessuna identità v5 selezionata e nessun riconoscimento v5 eseguito.'
    notrun=dict(status='not_run',reason=reason,independent=None,freeze=None,identities=[],sources=[],cases=[],expected_count=0,completed=0,summary=dict(cases=0,metrics={},latency_ms={}),recognition_calls=0)
    for name in ['robustness_v5','scan_v5','filled_v5','retrieval_v5','evaluation_v5_leakage']:atomic_json(ROOT/OUT/(name+'.json'),dict(notrun,kind=name))
    evidence_paths=['benchmarks/reference/reference_truth_v2.json','benchmarks/manifests/official_unknown_v1.json',OUT+'calibration_v5.json',OUT+'performance.json','data/recognition_profiles/fingerprint_decision_v5.json']
    evidence_hashes={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in evidence_paths if (ROOT/p).exists()}
    if not args.preliminary:
        for value in [cal,unknown,perf]:
            for key in ['runtime_sha256','code_sha256','fingerprint_sha256']:assert value['identity'][key]==ident[key],key
    atomic_json(ROOT/OUT/'freeze_not_created.json',dict(status='not_created',prerequisites=checks,reason=reason,engine_identity=ident,fingerprint_version='fingerprint-v3',decision_version='fingerprint-decision-v5',evidence_sha256=evidence_hashes))
    development=read(OUT+'calibration_observations_v5.json')
    filled=[r for r in development['cases'] if r['representation']=='valid_filled']
    filled_summary=summary(filled)
    atomic_json(ROOT/OUT/'development_summary.json',dict(status=cal['status'],identity=cal['identity'],independent=False,completed=development['completed'],expected_count=development['expected_count'],known=cal['known_metrics'],negative=cal['negative_metrics'],valid_filled=filled_summary,source='Retrospective development replay only; no v5 evaluation.'))
    historical={n:read(OUT+'historical_'+n+'.json') for n in ['development_regression','release_locked_v1','release_locked_v2','development_compat_v2','hard_negatives_v1','hard_negatives_v2','family_release_v3','catalog_coverage']}
    no=[r for v in historical.values() for r in v['cases'] if r['expected']['match_type']=='NO_MATCH'];fa=[r['id'] for r in no if r['observed']['match_type']!='NO_MATCH'];r061=next(r for r in historical['release_locked_v2']['cases'] if r['id']=='R061')
    after={r['id']:r for r in historical['development_compat_v2']['cases'] if r['id'] in ['EX02MISSINGREV','EX03MISSINGREV']}
    audit='# Historical false acceptance audit — Round 9\n\nContratto storico NO; truth degli input senza revisione ambigua. Non vengono promossi a confirmed NO per migliorare i gate.\n\n'
    for before in baseline['false_accepts']:
        audit+='## '+before['case_id']+'\n\n```json\n'+json.dumps(before,ensure_ascii=False,indent=2)+'\n```\n\n'
        audit+='Veto mancato: `missing_model_revision` aggirato da `metadata_revision_supported`. Correzione generale del fallback metadata: titolo/codice/ente unici non provano una revisione decimale; occorre revisione esplicita nei primi2000 caratteri. Le firme forti v5 mantengono i criteri R8 multicanale, ancore di identità e margine; conflitti espliciti e risorse condivise conservano i veti. Nessuna blacklist. Dopo: `'+after[before['case_id']]['observed']['match_type']+'`. Test: `tests/test_round9_engine.py::test_historical_missing_revision_is_conservative_for_any_id` include ID sintetico differente e controllo positivo con revisione esplicita. Canonical:979/979; hard negatives:130/130; nessuna nuova accettazione sui NO storici.\n\n'
    (ROOT/OUT/'historical_false_acceptance_audit.md').write_bytes((audit.rstrip()+'\n').encode())
    tests=dict(status='pending',passed=None,failed=None,skipped=None)
    log=ROOT/'reports/round9-full-tests.log'
    if log.exists():
        raw=log.read_bytes();text=raw.decode('utf8',errors='replace');m=re.search(r'(\d+) passed(?:, (\d+) skipped)? in ([\d.]+)s',text)
        if m and not re.search(r'\b[1-9]\d* (?:failed|errors?)\b',text):tests=dict(status='passed',passed=int(m[1]),skipped=int(m[2] or 0),failed=0,seconds=float(m[3]),log_sha256=hashlib.sha256(raw).hexdigest(),python=platform.python_version(),platform=platform.platform())
    if not args.preliminary:assert tests['status']=='passed','Full tests not green'
    atomic_json(ROOT/OUT/'tests.json',tests)
    gates=[]
    def gate(name,target,actual,passed,blocking=True):gates.append(dict(gate=name,target=target,actual=actual,passed=bool(passed),blocking=blocking))
    gate('historical_safety','0 false accepts on historical NO',fa,not fa)
    gate('round8_two_false_accepts','0/2 accepted',sum(r['observed']['match_type']!='NO_MATCH' for r in after.values()),len(after)==2 and all(r['observed']['match_type']=='NO_MATCH' for r in after.values()))
    gate('R061','NO_MATCH',r061['observed']['match_type'],r061['observed']['match_type']=='NO_MATCH')
    gate('truth_v2_complete','0 unclassified',truth['unclassified_contradictions'],truth['unclassified_contradictions']==0)
    gate('unknown_confirmed_count','>=100,target150',len(manifest['cases']),len(manifest['cases'])>=100)
    gate('unknown_sources','>=8',len(manifest['sources']),len(manifest['sources'])>=8)
    gate('unknown_concentration','<=25%',manifest['source_concentration'],manifest['source_concentration']<=.25)
    gate('unknown_rejection','>=99%, no DOCUMENT/FAMILY accept',dict(correct=unknown['correct_rejection_count'],total=len(unknown['cases']),false_accepts=unknown['false_accepts']),unknown['false_accepts']==0 and unknown['correct_rejection_count']/len(unknown['cases'])>=.99)
    gate('coverage_file_backed','>=85%',cov['coverage_file_backed'],cov['coverage_file_backed']>=.85);gate('coverage_all','>=70%',cov['coverage_all'],cov['coverage_all']>=.70)
    gate('canonical','100% P/R',can['counts'],can['counts']['exact']==979 and can['counts']['wrong']==0)
    for name,target in [('v5_identities','>=30'),('v5_sources','>=6'),('v5_representations','>=400'),('v5_scans','>=200'),('v5_valid_fills','>=50'),('v5_overall','P>=99.5%,R>=90%,entity/version errors0'),('v5_scan','P>=99.5%,R>=85%'),('v5_filled','generation>=90%,P>=99.5%,R>=90%'),('v5_retrieval_at25','100%')]:gate(name,target,None,False)
    gate('performance_p50','<=150ms',perf['latency_ms']['p50'],perf['latency_ms']['p50']<=150);gate('performance_p95','<=250ms',perf['latency_ms']['p95'],perf['latency_ms']['p95']<=250);gate('index_memory','<=100000000bytes',perf['index']['bytes'],perf['index']['bytes']<=100000000)
    gate('process_memory_stability','measurement only; stability not established',perf['rss'],False,False)
    gate('tests','all green',tests,tests['status']=='passed');gate('family','>=5 evaluable or experimental',family['families_evaluable'],False,False);gate('CI','external_pending','external_pending',False,False)
    result=dict(round=9,status='NOT READY',software_version='0.6.1',candidate_target='0.7.0',schema=610,identity=ident,freeze=None,freeze_status='not_created',local_gates_passed=False,gates=gates,tests=tests,ci='external_pending')
    atomic_json(ROOT/'docs/release_gates.json',result)
    docs,families=catalog();empty=dict(notrun)
    latest=dict(schema_version=1,benchmark_model='known-family-unknown-v5',status='NOT READY',software_version='0.6.1',candidate_target='0.7.0',catalog_semantic_sha256=catalog_revision(docs,families),catalog_count=1216,commit=ident['commit'],executed_at=ident['executed_at'],release_gate=result,fingerprint_coverage=dict(status='executed',operational_docs_total=1212,file_backed_operational_docs=1158,fingerprinted_all_operational_docs=941,coverage_all=cov['coverage_all'],coverage_file_backed=cov['coverage_file_backed']),known_canonical=dict(status='executed',summary=can['summary']),known_robustness=empty,scan_ocr=empty,filled_forms=empty,unknown_official=dict(status='measured_inadequate',summary=unknown['summary'],reason=f"{len(manifest['cases'])}/100 unknown confermati; {len(manifest['sources'])}/8 fonti; concentrazione {manifest['source_concentration']:.2%}. Corpus retrospettivo, insufficiente per release."),family_identity_holdout=dict(status='executed',summary=family['summary'],families_evaluable=family['families_evaluable'],capability_status='insufficiently_validated'),performance=dict(status='executed',latency_ms=perf['latency_ms'],index_bytes=perf['index']['bytes']),ocr_status='OCR locale reale nei test e nel development; v5 non eseguita.',evaluations=[dict(name=n,summary=v['summary']) for n,v in historical.items()])
    atomic_json(ROOT/'benchmarks/latest_summary.json',latest)
    hist=table([['Corpus storico','Corretti','Totale'],['---']*3]+[[n,v['summary']['passed'],len(v['cases'])] for n,v in historical.items()])
    gt=table([['Gate','Target','Risultato','Esito'],['---']*4]+[[g['gate'],g['target'],json.dumps(g['actual'],ensure_ascii=False),'PASS' if g['passed'] else 'FAIL' if g['blocking'] else 'INFO/PENDING'] for g in gates])
    components=table([['Componente (probe non additivo)','p50ms','p95ms'],['---']*3]+[[k,v['p50'],v['p95']] for k,v in perf['components'].items()])
    frozen_fill=hashlib.sha256((ROOT/'benchmarks/round8_fill.py').read_bytes()).hexdigest();assert (ROOT/'benchmarks/round8_fill.py').read_bytes()==subprocess.check_output(['git','show','fa2a307:benchmarks/round8_fill.py'],cwd=ROOT)
    body=f'''# Round 9 — NOT READY

Software pubblico 0.6.1, target 0.7.0, schema 610. Branch `codex/coverage-benchmark-v0.7.0`. HEAD al momento della misura/report: `{ident['commit']}`; le modifiche R9 sono identificate anche dai loro hash, non ancora da quel commit. Il commit finale archiviato e lo SHA dello ZIP sono registrati dopo il commit in `dist/package-verification.json` e nella consegna. Nessun freeze R9: prerequisiti non raggiunti. Nessun push, tag o pubblicazione. Catalogo e seed immutati: 1216 reali, 1212 operative, 19 fonti, 16 famiglie.

Round 8: freeze effettivo `{baseline['freeze']['commit']}`, seguito soltanto da report/package. V4 originale 50/356: 36 exact, 14 rifiuti, 0 wrong, 306 esiti indisponibili. Caso A tecnicamente compatibile col completamento storico facoltativo: non effettuato. Originali preservati, nessuna v4 spacciata per nuova prova. Log: errno 22 in Path.open(wb) del checkpoint; causa OS esatta non determinabile dai dati registrati. Corretto il difetto accertato di persistenza, senza inventare lock/antivirus.

## Safety e truth

Due falsi accept storici riparati: EX02MISSINGREV e EX03MISSINGREV, prima documenti 13/12 con score 100, ora NO. Causa: inferenza della revisione 1.1 dalla sola unicità di codice/titolo/ente nel fallback metadata. Correzione v5 generale del fallback metadata: revisione decimale esplicita nei primi 2000 caratteri, senza dedurla dall’unicità. Le firme forti mantengono criteri R8 multicanale, identità e margine; conflitti ente/versione, binding/stato e SHA condivisi mantengono i veti. Test su ID differente esclude blacklist. Audit numerico completo in `historical_false_acceptance_audit.md`.

Truth v2: `{json.dumps(truth['counts'])}`, zero contraddizioni non classificate. Include tutte le etichette testuali, le 979 risorse canoniche unambiguous e gli unknown confermati. Solo confirmed entra nei gate di release; i contratti storici sono controllati separatamente e ambigui/esclusi conservano lo storico. Le vecchie label positive EX02/03 prive di revisione ora sono rifiutate: base 33/35, nessun tentativo di nascondere la regressione storica. R061 resta NO. Cinque vecchi casi critici: rifiuto o identità propria corretta, verificati separatamente. Nessuna nuova verifica editoriale.

{hist}

## Unknown ufficiali

{manifest['candidates_audited']} candidati auditati, classificazioni `{json.dumps(manifest['classification_counts'])}`. Confermati {len(manifest['cases'])}; fonti {len(manifest['sources'])}, distribuzione `{json.dumps(manifest['sources'])}`, concentrazione {manifest['source_concentration']:.2%}. Discovery: 45 richieste nella seconda acquisizione (9 nella prima), esclusivamente maintenance con --allow-network/robots/allowlist e fonti esistenti. Non raggiunti i minimi di 100 file, 8 fonti e massimo 25% di concentrazione.

Rifiuti corretti {unknown['correct_rejection_count']}/{len(unknown['cases'])}; false DOCUMENT/FAMILY accept {unknown['wrong_document']}/{unknown['wrong_family']}; errori estrazione {unknown['extraction_failed']}. FAR {unknown['false_acceptance_rate']:.2%}, CI 95% Wilson `{unknown['false_acceptance_ci95']}`. Per-source/per-entity/per-type nei raw. L’ente del manifest deriva dall’autorità che ospita la fonte: non certifica l’emittente storico di ogni decreto o atto UE; nessuna pretesa di 8 emittenti indipendenti. I file storici restano contaminati anche dopo conferma truth; i nuovi candidati sono indicati separatamente. Classificazione fondata su ricevuta/SHA, intestazione informativa, titolo completo, near-duplicate e famiglie, prima delle predizioni. I 91 dubbi sono esclusi, senza convertirli in unknown per migliorare i numeri.

## Coverage e legacy

941/1158 file-backed ({cov['coverage_file_backed']:.2%}); 941/1212 operative ({cov['coverage_all']:.2%}); 0 recuperate. Tutti i 217 residui sono censiti in `fingerprint_recovery_v2.csv`. I 1158 ID provengono dall’audit congelato R6, incluso 166 SEGNALAZIONE privo di download_url: il classificatore corrente ne conterebbe 1157, ma il denominatore congelato resta 1158. Recupero: 29 richieste, nessun nuovo binding certo. I formati legacy sono esaminati sui byte cached; nessun convertitore locale sicuro disponibile, nessuna conversione o installazione rivendicata. 403/429/robots rispettati. 1027 binding di risorsa, 979 active unambiguous, 48 condivisi: riconoscimento risorsa separato dall’identità. SHA comune non produce exact univoco.

Canonical 979/979 exact, 0 wrong, P/R 100%; 941 identità distinte. Byte e binding ufficiali già censiti, non una prova di scansioni nuove. Nessun documento o fonte aggiunto.

## Development e evaluation

Decisione `fingerprint-decision-v5`; dati fingerprint-v3 invariati, v1/v2 conservate. Soglie R8 mantenute, nessuna promozione basata sulla v5. Stato calibrazione `{cal['status']}`: {development['completed']}/{development['expected_count']} casi completati, {len(cal['identity_ids'])} identità riservate al development. Noti: {cal['known_metrics']['passed']}/{cal['known_metrics']['cases']} exact, recall {cal['known_metrics']['metrics']['document_recall']['value']:.2%}, precision {cal['known_metrics']['metrics']['document_precision']['value']:.2%}; false accept {cal['false_accepts']}, wrong known {cal['wrong_known']}. Compilati validi R8 nel replay finale: {filled_summary['passed']}/{filled_summary['cases']} exact. Queste misure sono retrospettive e non soddisfano il gate di robustezza indipendente. Dati integrali in `calibration_v5.json`, `calibration_observations_v5.json` e `development_summary.json`. R6/R7, compilati validi R8, sole 50 osservazioni R8 salvate ora development, negativi storici e subset unknown confermato. Nessun tuning su nuove identità v5.

Primo tentativo development con veto di revisione mancante anche sulle firme forti: 325/582 exact, 184 rifiuti per revisione, 20/50 filled, 0 wrong. È conservato in `calibration_strict_veto_development_attempt.json` e `calibration_strict_veto_observations.json`. La regola era troppo ampia rispetto alla causa auditata: affinata sul solo fallback metadata prima di qualunque freeze/evaluation, poi replay completo ripetuto. Non si attribuisce indipendenza a nessuno dei due replay.

Generatore filled R8 immutato SHA `{frozen_fill}`. La precedente prova development 50/50 resta storica; nessuna nuova generation success v5 rivendicata. Validità dei valori fittizi meccanica, non amministrativa.

**Evaluation v5 NON ESEGUITA.** {reason} Zero identità, fonti, rappresentazioni, scansioni, compilati e chiamate. P/R, entity/version errors e retrieval@1/@5/@10/@25 non misurati, non zero e non passati. File richiesti presenti con `status=not_run` e metriche vuote. Nessuna selezione anticipata o leakage check fittizio. Family: 0/16 valutabili, experimental/insufficiently validated; utile di release = exact soltanto.

Writer realmente usato per development/unknown: journal SQLite con transazioni FULL e case_id univoco, identità byte motore/input vincolata, ripresa soltanto dei mancanti; export temp+flush/fsync+replace atomico, conteggio completo e SHA finale. I JSON parziali non sono fonti di resume. Test crash forzato, duplicati conflittuali, conteggio, corruzione, concorrenza Windows e sharing violation. Nessun testo personale nei journal.

## Performance e memoria

Warm recognition p50 {perf['latency_ms']['p50']:.2f} ms, p95 {perf['latency_ms']['p95']:.2f} ms, p99 {perf['latency_ms']['p99']:.2f} ms. Baseline R9 p95 {baseline['performance']['latency_ms']['p95']:.2f} ms, R8 finale 350.13 ms. La prima misura R9 dopo l'ottimizzazione delle intersezioni (p95 266.81 ms) è conservata in `performance_initial_optimization.json` e nel relativo profilo. Tra quella misura e la finale sono cambiati sia le regex preparate per richiesta sia l'ambito del veto di revisione: il confronto non è un'ablation pura della sola ottimizzazione. Ogni misura conserva gli hash effettivi del proprio motore.

{perf['latency_ms']['n']} richieste con nuovi contesti, senza cache globale degli input e senza shortcut SHA. Dataset fixed51 conservato, 14 scansioni storiche e 2 immagini incapsulate in PDF con OCR già disponibile; gruppi separati nei raw. OCR end-to-end estrazione `{json.dumps(perf['ocr_end_to_end_extraction_ms'])}` ms separato dal recognition; queste scansioni sintetiche non rappresentano acquisizioni personali reali.

Il dataset fixed51 ha p95 {perf['by_input_group']['historical_fixed51']['p95']:.2f} ms, con margine molto piccolo sul target. I gruppi digital PDF (p95 {perf['by_input_group']['representation:digital_pdf']['p95']:.2f} ms) e filled AcroForm (p95 {perf['by_input_group']['representation:filled_acroform']['p95']:.2f} ms) superano 250 ms; il pass del gate aggregato non equivale a un pass di ogni formato.

Per gruppi `{json.dumps(perf['by_input_group'])}`. Intersezioni native e tuple canoniche evitano boxing/ripetizioni, somma IDF nello stesso ordine del riferimento; regex anno/revisione preparate una volta per richiesta. Nessun pruning semantico: molte pagine restano candidate. Equivalence tests contro percorso indipendente e query dense; niente topK arbitrario che nasconda candidati. Normalizzazione e feature input solo nella richiesta.

Indice {perf['index']['bytes']} bytes, 3476 pagine, disco {perf['index']['disk_bytes']} bytes. RSS `{json.dumps(perf['rss'])}`. Il costo memoria delle tuple è dichiarato e resta sotto 100 MB. Component probes non additivi, fusion include altri componenti; entity/version probe su cinque candidati, non misura integrale di tutti i veti.

RSS dopo warm {perf['rss']['after_warm_bytes']} bytes, poi crescita di {perf['rss']['growth_after_warm_bytes']} bytes nei sei cicli. La stabilità della memoria di processo non è dimostrata; la causa della crescita non è stata isolata. Il gate dei 100 MB riguarda l'indice, non l'intero processo. Questo limite resta esplicito anche con il gate di latenza aggregato superato.

{components}

## Test, CI e gate

Test `{json.dumps(tests)}`. Verifica seed, hash corpus/raw storici, dichiarazioni del workflow offline Ubuntu/macOS/Windows e cinque critical cases in `verification.json`. CLI locale locked-v2 69/69 e compat-v2 37/37. I comandi storici senza corpus v2 (`scripts/benchmark.py` e `benchmarks.evaluate --fast`) continuano a segnalare i due rifiuti EX02/EX03 rispetto alle label v1: non sono presentati come green. Il workflow esistente li include; la sola verifica sintattica non prova quindi un'esecuzione CI riuscita. CI GitHub `external_pending`, nessun push. Collaudo locale Windows soltanto, nessuna validazione editoriale generale o collaudo su altre piattaforme rivendicato.

{gt}

## Archivio

`dist/BurOCRazia-v0.7.0-candidate-NOT-READY-round9.zip`, creato dal HEAD committato e verificato con hash/igiene/lock. SHA256 e commit esatti in `dist/package-verification.json` e `.zip.sha256`; non inseriti nel proprio contenuto per evitare riferimenti circolari. `evidence_locks.json` vincola le prove R9 e i blob Git storici R6/R7/R8, senza essere un freeze del motore. La versione pubblica rimane 0.6.1. Limiti bloccanti reali: coverage <85%, unknown insufficienti/sbilanciati e nessuna evaluation v5 qualificata; performance giudicata rispetto al gate 250 ms nella tabella, senza modificarlo.
'''
    (ROOT/'docs/ROUND9_REPORT.md').write_bytes(body.encode())
    path=ROOT/'docs/BENCHMARK.md';old=path.read_text(encoding='utf8');start='<!-- round9-current -->';end='<!-- /round9-current -->'
    if start in old:old=old[old.index(end)+len(end):].lstrip()
    overview=f'Software 0.6.1/schema 610. Canonical 979/979, due falsi accept riparati; {len(manifest["cases"])} unknown confermati, corpus insufficiente. Copertura file 81.26%; warm recognition p95 {perf["latency_ms"]["p95"]:.2f} ms (target 250 ms). V5 non selezionata/eseguita: prerequisiti freeze non raggiunti. R8 v4 originale 50/356 immutata, solo diagnostica storica.'
    path.write_bytes((start+'\n# Round 9 — NOT READY\n\n'+overview+' Dettagli e gate: `docs/ROUND9_REPORT.md`.\n'+end+'\n\n'+old).encode())
    for name,content in [
        ('README.md',overview+' Dettagli nel [rapporto Round 9](docs/ROUND9_REPORT.md). Le sezioni Round 8 seguenti sono storiche.'),
        ('README_EN.md',f'Round 9 **NOT READY**; public version remains 0.6.1, schema 610. Two historical false accepts repaired; canonical 979/979. File coverage 81.26%; {len(manifest["cases"])} confirmed unknowns from four sources, below the required size/diversity. Warm recognition p95 {perf["latency_ms"]["p95"]:.2f} ms (250 ms target). No engine freeze or independent v5 evaluation. See the [Round 9 report](docs/ROUND9_REPORT.md).'),
    ]:
        p=ROOT/name;previous=p.read_text(encoding='utf8')
        if start in previous:previous=previous[previous.index(end)+len(end):].lstrip()
        p.write_bytes((start+'\n'+content+'\n'+end+'\n\n'+previous).encode())
    print('Round9 report NOT READY; prerequisites',checks,flush=True)
if __name__=='__main__':main()
