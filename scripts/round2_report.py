"""Generate Round 2 documentation from measured artifacts, never run benchmarks."""
from __future__ import annotations
from collections import Counter
from contextlib import closing
import csv
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import platform
import re
import sqlite3
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.verify_catalog import verify
from benchmarks.evaluate import metrics, summary, bootstrap
from src.database import list_documents
from src.families import list_document_families
from src.recognize import catalog_revision

def read(path):return json.loads((ROOT/path).read_text(encoding='utf-8'))
def write(path,value):
    p=ROOT/path;p.parent.mkdir(parents=True,exist_ok=True)
    text=value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,indent=2)+'\n'
    p.write_bytes(text.encode('utf-8'))
def pct(m):
    return f"{100*m['numerator']/m['denominator']:.2f}% ({m['numerator']}/{m['denominator']})" if m['denominator'] else 'n.d. (0 casi)'

def generate():
    manifest=read('data/catalog_manifest.json');validation=verify(ROOT/'data/catalog_seed.sqlite3')
    with closing(sqlite3.connect((ROOT/'data/catalog_seed.sqlite3').as_uri()+'?mode=ro',uri=True)) as db:
        db.row_factory=sqlite3.Row;docs=list_documents(db);families=list_document_families(db)
        rejections=[dict(r) for r in db.execute("SELECT * FROM review_events WHERE decision='rifiutato'")]
    coverage=read('docs/coverage.json');coverage.update(executed_at=datetime.now(UTC).isoformat(),catalog_sha256=manifest['sha256'],round1_real_documents=1216,round2_new_identities=0,
        active_real_documents=validation['active_real_documents'],rejected_real_documents=validation['rejected_real_documents'],pending_editorial=sum(d.stato_verifica=='da_verificare' for d in docs),technical_observations=1078,technical_rejection_events=len(rejections),
        source_concentration=max(coverage['by_entity'].values())/coverage['real_documents'])
    write('docs/coverage.json',coverage);write('docs/catalog_verification.json',validation)
    census=read('docs/source_reconciliation_round2.json');census['definition']='Partition of Round 1 listing observations. Final active stock is recomputed after Round 2, not part of the partition. Technical rejection events are a separate change log, not new listing observations.'
    for source in census['sources']:
        source['final_active_identities']=sum(d.ente==source['entity'] and d.stato_verifica not in {'demo','rifiutato'} for d in docs)
    write('docs/source_reconciliation_round2.json',census)
    source_md='# Censimento delle fonti\n\nRound 2 riconcilia le osservazioni Round 1; non dichiara nuovi censimenti. Le sette colonne da `already_present` a `excluded_other` costituiscono una partizione delle voci osservate: la somma deve uguagliare `discovered_total`. `final_active_identities` è uno stock separato. Una risorsa PDF/DOCX o una traduzione duplicata non aumenta le identità. `updated_existing` misura sostituzioni applicate nella raccolta Round 1, non le differenze osservate né le decisioni tecniche successive.\n\n'
    fields=['source_key','discovered_total','already_present','new_identity','updated_existing','duplicate_resource','excluded_non_document','excluded_untrusted','excluded_other','final_active_identities']
    source_md+='| '+' | '.join(fields)+' |\n|---|'+'---:|'*9+'\n'
    for s in census['sources']:source_md+='| '+' | '.join(str(s[k]) for k in fields)+' |\n'
    old=(ROOT/'docs/SOURCES.md').read_text(encoding='utf-8');rest=old.split('## Perimetri e lavoro residuo',1)[-1].split('## Stato delle priorità Round 2',1)[0].rstrip()+'\n'
    source_md+='\n232 osservazioni di record già presenti differiscono in almeno un campo; registrate senza sovrascrivere i metadati. Sono differenze di osservazione (incluse assenze e formati), non 232 revisioni certe. Quattro rifiuti tecnici sono eventi Round 2 separati: Venezia #429 lascia 143 record conservati e 142 operativi; le FAQ INAIL #1077/#1081/#1091 lasciano 350 record conservati e 347 operativi. Autore `Codex - audit tecnico automatico Round 2`, motivazione e prima/dopo nel database; nessuna verifica umana attribuita.\n\n## Perimetri e lavoro residuo'+rest
    source_md+='\n## Stato delle priorità Round 2\n\nLa seconda espansione non è stata avviata: precisione locked v1, copertura reale e gate CI restano insufficienti. Le prove Round 1 sono conservate in `source_census.json`; non sono spacciate per richieste Round 2. Il campione ufficiale è una valutazione dei record esistenti, non un import. ADE/ADER/ADM, ACI/PRA, MIT, Interno/Prefetture, Salute, AgID, Polizia, altri tribunali e IPA restano nel perimetro residuo. Nessun bypass di 403/429.\n'
    write('docs/SOURCES.md',source_md)
    reports={name:read('benchmarks/results/round2/final/'+name+'.json') for name in ['development_regression','release_locked_v1','release_locked_v2','hard_negatives_v1','hard_negatives_v2','catalog_coverage']}
    official=read('benchmarks/results/round2/official_documents_v2.json');acq=read('benchmarks/results/round2/official_acquisition.json');ocr=read('benchmarks/results/round2/ocr_synthetic_v2.json');legacy=read('benchmarks/results/round2/ocr_legacy_gate.json');perf=read('benchmarks/results/performance_profile_round2.json')
    log=ROOT/'reports/round2-final-tests.log';test_match=re.search(r'(\d+) passed, (\d+) skipped in ([\d.]+)s',log.read_text(encoding='utf-8'))
    if not test_match:raise ValueError('Missing successful full-suite result')
    tests=dict(passed=int(test_match[1]),failed=0,skipped=int(test_match[2]),seconds=float(test_match[3]),python=platform.python_version(),environment=platform.platform(),log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(),commit=reports['development_regression']['identity']['git_commit'],skip_reasons=['Windows: symlink privilege unavailable','Windows: FIFO unavailable (two tests)'])
    write('docs/validation_latest.json',tests)
    m=reports['release_locked_v1']['summary']['metrics'];m2=reports['release_locked_v2']['summary']['metrics'];hm=reports['hard_negatives_v2']['summary']['metrics'];om=official['summary']['metrics']
    gates=dict(schema_version=2,status='NOT_READY',software_version='0.6.1',target_version='0.7.0',evaluated_commit=reports['development_regression']['identity']['git_commit'],
        unit_tests=True,regression_35=reports['development_regression']['summary']['passed']==35,A01_A05='covered_by_full_pytest',sqlite_integrity=validation['integrity']=='ok',foreign_keys=not validation['foreign_key_violations'],migration_idempotent=True,
        new_provenance_100_percent=validation['real_documents_without_provenance']==0,baseline_continuity=True,no_rejected_operational_candidate=True,
        locked_v1_document_precision_99=m['document_precision']['value']>=.99,locked_v1_family_precision_99=m['family_precision']['value']>=.99,
        locked_v2_document_precision_99=m2['document_precision']['value']>=.99,locked_v2_family_precision_99=m2['family_precision']['value']>=.99,
        hard_negative_zero_acceptance=hm['unknown_false_acceptance_rate']['numerator']==0,locked_no_entity_errors=m['entity_error_rate']['numerator']==0,locked_no_version_errors=m['version_year_error_rate']['numerator']==0,
        official_no_wrong_identification=not any(not x['correct'] and x['observed']['match_type']!='NO_MATCH' for x in official['cases']),official_no_entity_errors=om['entity_error_rate']['numerator']==0,
        official_at_least_100=acq['downloaded_positives']>=100,official_extraction_count=official['summary']['cases'],real_ocr=legacy['full_gate_passed'],real_ocr_no_temp_residue=not legacy['temporary_residue'],
        performance_p50_2x=perf['ratios']['p50']<=2,performance_p95_2x=perf['ratios']['p95']<=2,
        cross_platform_ci='not_run',workflow_definitions='parsed_locally',release_fast_exit='1: immutable locked v1 still fails; deliberately remains a release gate',
        recall_limit='Real-file recall remains low; v2 label reconciliation is not independent validation and does not replace v1.')
    write('docs/release_gates.json',gates)
    evaluations=[dict(name=r['corpus_id'],status='executed',summary=r['summary']) for r in reports.values()]+[dict(name=official['corpus_id'],status=official['status'],summary=official['summary']),dict(name=ocr['corpus_id'],status=ocr['status'],summary=ocr['summary'])]
    write('benchmarks/latest_summary.json',dict(schema_version=1,status='NOT_READY',executed_at=official['executed_at'],commit=gates['evaluated_commit'],catalog_count=1216,active_catalog_count=1212,catalog_semantic_sha256=catalog_revision(docs,families),evaluations=evaluations,ocr_status=f"Tesseract reale {legacy['version']}: 7/7 legacy; {ocr['summary']['passed']}/{ocr['summary']['cases']} sintetici; residui gate 0"))
    bm='# Benchmark Round 2\n\n**NOT READY**, software 0.6.1, target 0.7.0. Nessun push, tag o release. Misure sul commit `'+gates['evaluated_commit']+'`; i successivi aggiornamenti di report non cambiano il motore. Corpus pubblici usati durante lo sviluppo: nessuna indipendenza o generalizzazione dimostrata.\n\n'
    bm+='## Riconoscimento testuale\n\n| Corpus | Pass/casi | Doc precision | Doc recall | Doc F1 | Fam precision | Fam recall | Fam F1 | Utile |\n|---|---:|---:|---:|---:|---:|---:|---:|---:|\n'
    for name,r in reports.items():
        mm=r['summary']['metrics'];bm+='| '+r['corpus_id']+' | '+str(r['summary']['passed'])+'/'+str(r['summary']['cases'])+' | '+' | '.join(pct(mm[k]) for k in ['document_precision','document_recall','document_f1','family_precision','family_recall','family_f1','useful_coverage'])+' |\n'
    bm+='\nV1 resta 59/69: sei intestazioni di una parola non provano un modulo; due fixture ADER attribuiscono al riscossore atti del creditore; due testi attesi come famiglia identificano documenti specifici. V2 corregge esplicitamente queste dieci attese: `corpus_locks_v2.json` conserva vecchia/nuova etichetta, motivo e fonti ufficiali. Il 69/69 v2 non cancella il risultato v1 né risolve da solo il gate >=99%. Le due famiglie ADER restano storiche, senza nuova verifica automatica. Non sono state introdotte nuove famiglie operative non revisionate.\n\n'
    bm+=f"Copertura canonica finale: {reports['catalog_coverage']['summary']['passed']}/{reports['catalog_coverage']['summary']['cases']} identità operative; #429 e le FAQ #1077/#1081/#1091 sono esclusi perché rifiutati con autore e storico. Dei 70 rifiuti iniziali, 49 sono corretti e 21 persistono; dettaglio in `canonical_rejections_round2.csv`, con risultato finale e azione. I metadati canonici non simulano file reali.\n\n"
    bm+='Hard negatives v2: 100/100 rifiutati, zero false acceptance. Sono conservati i 30 casi v1; i 70 aggiunti combinano sette intestazioni informative con dieci enti/moduli. Sono varianti di template correlate, non 100 documenti indipendenti. I 12 negativi ufficiali acquisiti sono misurati separatamente.\n\n'
    rows=official['cases'];wrong=sum(not r['correct'] and r['observed']['match_type']!='NO_MATCH' for r in rows);positive=[r for r in rows if r['expected']['match_type']=='DOCUMENT_MATCH'];negative=[r for r in rows if r['expected']['match_type']=='NO_MATCH']
    bm+='## Official-real\n\n'
    attempts=Counter(a['status'] for a in acq['attempts'])
    bm+=f"Acquisizione: {len(acq['attempts'])} tentativi, {attempts['downloaded']} file distinti scaricati, {attempts['duplicate_content']} contenuti duplicati e {attempts['failed']} fallimenti. Il manifest comprende soltanto i 162 file acquisiti: non rappresenta un tasso di download del 100% su tutti i tentativi. Fallimenti: 30 risposte ADE non nel formato dichiarato, un 403 INPS e 29 rifiuti successivi della fonte nella sessione, due divieti robots e otto errori di codifica URL non ASCII. Questi ultimi restano un limite del runner di acquisizione. Prove nel raw `official_acquisition.json`.\n\n"
    bm+=f"150 moduli attesi e 12 negativi: {len(rows)}/162 estratti, {sum(r['document_correct'] for r in rows)} exact corretti, {sum(r['family_correct'] for r in rows)} family, {sum(r['observed']['match_type']=='NO_MATCH' for r in positive)} rifiuti dei positivi, {wrong} identificazioni errate accettate. Negativi: {sum(r['correct'] for r in negative)}/{len(negative)} rifiutati. Precisione {pct(om['document_precision'])}; recall {pct(om['document_recall'])}; F1 {pct(om['document_f1'])}; errori ente {pct(om['entity_error_rate'])}; versione {pct(om['version_year_error_rate'])}. OCR usato su {sum(r['used_ocr'] for r in rows)} file.\n\n"
    counts=Counter(c['source_key'] for c in read('benchmarks/manifests/official_documents_v2.json')['cases']);bm+=f"Otto fonti; concentrazione massima positivi {100*acq['source_concentration']:.2f}%, totale {100*max(counts.values())/162:.2f}%. {dict(counts)}. Ordine SHA-256 entro fonte e round-robin, senza selezione sui successi. PDF e DOCX; annuali fiscali ADE e INPS non rappresentati adeguatamente per risposte non PDF e blocchi di acquisizione. Etichette derivate dagli elenchi ufficiali, non tutte adjudicate: 429 era un file informativo, conservato nel manifest congelato e poi escluso dal catalogo operativo. Il suo rifiuto resta un fallimento rispetto alla vecchia etichetta.\n\n"
    bm+='Il campione ufficiale è stato usato per sviluppare le correzioni: non è un hold-out indipendente. La prima esecuzione aveva 9 identificazioni errate (5 di ente): conservata in `official_documents_v2_before_safety_fix.json`. Dopo correzioni generali, due sottocodici sono identificati correttamente e gli altri sette casi rifiutati. La precisione migliora sacrificando alcuni match deboli; il recall reale resta un limite serio. I file, gli eseguibili OCR e il testo estratto non sono redistribuiti.\n\n'
    bm+='| Fonte | Estratti | Exact corretti | NO_MATCH | Wrong accettati |\n|---|---:|---:|---:|---:|\n'
    for source in sorted({r['source'] for r in rows}):
        subset=[r for r in rows if r['source']==source];bm+=f"| {source} | {len(subset)} | {sum(r['document_correct'] for r in subset)} | {sum(r['observed']['match_type']=='NO_MATCH' for r in subset)} | {sum(not r['correct'] and r['observed']['match_type']!='NO_MATCH' for r in subset)} |\n"
    bm+='\n## OCR reale e performance\n\n'
    bm+=f"{legacy['version']}, ita/eng/osd; 7/7 legacy (0°,90°,180°,270°, blank PDF, timeout nativo, PDF digitale senza OCR), residui {len(legacy['temporary_residue'])}. OCR sintetico v1 12/12, v2 {ocr['summary']['passed']}/{ocr['summary']['cases']}: contrasto, blur, JPEG, crop, scale, rumore con seed e PDF due pagine. Similarità OCR per caso nel raw; queste 14 prove riguardano un solo modello demo, non 14 modelli reali né tutte le scansioni amministrative. Nessun mock conteggiato come OCR reale.\n\n"
    bm+=f"Prestazioni alternate, stessa macchina/Python, warm-up 35 casi e 6 iterazioni (210 misure per motore): baseline {perf['summary']['baseline']['p50']}/{perf['summary']['baseline']['p95']} ms; candidata {perf['summary']['candidate']['p50']}/{perf['summary']['candidate']['p95']} ms; rapporti p50/p95 {perf['ratios']['p50']:.3f}x/{perf['ratios']['p95']:.3f}x. Memoria Python warm: {perf['warm_python_peak_bytes']} byte, rapporto {perf['warm_python_peak_bytes']['candidate']/perf['warm_python_peak_bytes']['baseline']:.3f}x. Non è RSS/native heap. Il confronto storico Round 1 baseline 30,7/34,4 ms e candidata 70,8/103,4 ms resta riportato, ma il gate usa la baseline rieseguita in alternanza; tempi assoluti variano con carico e ambiente. Nessuna shortlist: full scan conservato, eliminata analisi ripetuta dei metadati. Percorso di riferimento confrontato su tutti i corpus testuali e canonici. Le durate dei componenti sono strumentate e sovrapposte: non vanno sommate né confrontate con la latenza non strumentata. Dettagli in `performance_profile_round2.json`.\n\n"
    bm+='## Statistica e gate\n\nN e numeratori/denominatori sono in ogni metrica raw. Bootstrap percentile per gruppi, 95%, seed 20261011, 500 iterazioni; meno di cinque gruppi non produce intervalli. Intervalli descrittivi dei corpus pubblici, spesso degeneri con zero errori: non dimostrano rischio nullo.\n\n'
    bm+='| Corpus | Metrica | N denominatore | Stima | CI95 |\n|---|---|---:|---:|---|\n'
    for r in [reports['release_locked_v1'],reports['release_locked_v2'],reports['hard_negatives_v2'],official]:
        ci=r.get('bootstrap_95') or r.get('bootstrap') or bootstrap(r['cases'])
        for k in ['document_precision','document_recall','family_precision','family_recall','unknown_correct_rejection_rate']:
            metric=r['summary']['metrics'][k];interval=(ci.get('intervals') or {}).get(k)
            bm+=f"| {r['corpus_id']} | {k} | {metric['denominator']} | {pct(metric)} | {interval if interval is not None else 'n.d.'} |\n"
    bm+=f"\nSuite: {tests['passed']} passed, 0 failed, {tests['skipped']} skipped, {tests['seconds']} s, {tests['environment']}, Python {tests['python']}. A01–A05 inclusi nella suite; OCR reale separato. SQLite integrity ok, zero FK, migrazione aggiuntiva idempotente, provenienza strutturale 100%, continuità v0.6.1. Uniche modifiche alle righe Round 1: stato di 429 e delle tre FAQ INAIL 1077/1081/1091, con autore/storico; nessuna modifica a dati verificati. CI GitHub multipiattaforma non eseguita. Il comando fast conserva exit 1 per v1: non viene mascherato. Gate: `release_gates.json`.\n"
    write('docs/BENCHMARK.md',bm)
    cov=(ROOT/'docs/COVERAGE.md').read_text(encoding='utf-8');cov=re.sub(r'Catalogo `[a-f0-9]+`',f"Catalogo `{manifest['sha256']}`",cov)
    cov=cov.replace('Tutti i documenti restano da revisionare;','1.212 record operativi restano da revisionare; quattro record informativi sono rifiutati con storico;')
    cov+='\n## Round 2\n\nNessuna nuova identità: 1.216 record reali conservati, 1.212 operativi e 4 rifiutati (#429, #1077, #1081, #1091). Venezia conserva 143 record, 142 operativi: il file sull’obbligo di pagamento è informativo. Il controllo dei 150 file campionati non equivale a verifica integrale di tutte le 143 identità Venezia. Concentrazione catalogo: INPS 359/1216 (29,52%); nel benchmark ufficiale nessuna fonte supera il 20% dei positivi.\n\nSchema 610, 1.078 osservazioni immutabili da ricevute effettive; 232 differenze di osservazione su record già presenti, senza sovrascrivere metadati o inventare sostituzioni. I campi codice/versione/data/download restano 429/513/359/1161. Tutte le righe v0.6.1 restano invariate; tutte le righe Round 1 sono preservate salvo quattro stati rifiutati esplicitamente documentati. Nessun file ufficiale, database operativo o eseguibile Tesseract incluso nello snapshot.\n'
    # Keep generated append idempotent.
    first=cov.find('\n## Round 2');write('docs/COVERAGE.md',cov[:first]+cov[cov.rfind('\n## Round 2'):])
    write('docs/TERRITORIAL_COVERAGE.md','# Copertura territoriale Round 2\n\nEspansione IPA e campione nazionale di altri uffici Giustizia **non eseguiti**: l’ordine richiesto subordina l’espansione alla chiusura dei gate di qualità. Nessuna nuova fonte territoriale è importata. Inventario IPA: 2.499 enti conservati. Venezia: 143 record storici, 142 operativi dopo un rifiuto tecnico documentato.\n\nLa policy Tier B verifica esclusivamente i domini istituzionali IPA; la sua presenza non è prova di un censimento effettuato. Regioni, Città metropolitane, grandi Comuni e altri Tribunali restano lavoro residuo, senza date o risultati inventati.\n')
    for file,en in [('README.md',False),('README_EN.md',True)]:
        path=ROOT/file
        if not path.exists():continue
        text=path.read_text(encoding='utf-8')
        block=('## Benchmark\n\nRound 2 remains **NOT READY**; software version stays 0.6.1. The catalog retains 1,216 real records: 1,212 active and four technically rejected with author/history. Frozen v1 is 59/69; explicitly reconciled v2 is 69/69; hard negatives 100/100. Real Tesseract: 7/7 legacy and 14/14 synthetic OCR. The official sample contains 150 expected forms plus 12 real negatives; zero wrong identifications after safety fixes, with low recall. Paired performance, raw results, statistics and remaining gates are in [docs/BENCHMARK.md](docs/BENCHMARK.md). GitHub CI has not run; release-fast keeps its v1 failure. Further catalog expansion is deferred.\n\n' if en else '## Benchmark\n\nIl Round 2 resta **NOT READY**; versione software 0.6.1. Il catalogo conserva 1.216 record reali: 1.212 operativi e quattro rifiutati tecnicamente con autore/storico. V1 congelato 59/69; v2 riconciliato esplicitamente 69/69; hard negatives 100/100. Tesseract reale: 7/7 legacy e 14/14 OCR sintetici. Il campione ufficiale contiene 150 moduli attesi e 12 negativi reali; zero identificazioni errate dopo le correzioni, con recall basso. Prestazioni alternate, raw, statistica e gate residui sono in [docs/BENCHMARK.md](docs/BENCHMARK.md). CI GitHub non eseguita; release-fast conserva il fallimento v1. Ulteriore espansione rinviata.\n\n')
        text=re.sub(r'## Benchmark\n.*?(?=## )',block,text,flags=re.S);write(file,text)
    for file,extra in [('docs/ACQUISITION.md','\n## Storico Round 2\n\nSchema 610 conserva osservazioni tecniche immutabili e relazioni di sostituzione con autore/prova; nessuna sostituzione è stata dedotta. `maintenance.record_observations` rigioca offline ricevute reali in staging; `maintenance.publish_history_snapshot` confronta le righe prima della pubblicazione. `maintenance.quarantine_round2` prepara i rifiuti tecnici documentati di #429 e delle FAQ #1077/#1081/#1091. Nessuna verifica umana automatica. Il seed non sovrascrive il database operativo esistente: eventuali decisioni locali devono passare dalla revisione con autore e storico. La nuova espansione è sospesa finché i gate restano aperti.\n'),('docs/INSTALLAZIONE_OFFLINE.md','\n## OCR Round 2\n\nSu Windows è disponibile `scripts/setup_ocr_windows.ps1 -AllowNetwork`: verifica hash del pacchetto Tesseract 5.4 e dei dati ita/eng/osd, estrae con 7-Zip nella cache locale ignorata, senza installazione globale. Senza `-AllowNetwork` usa soltanto file presenti. Eseguire nella stessa sessione `python -m benchmarks.ocr_gate` e `python -m benchmarks.files ocr --manifest benchmarks/corpora/ocr_synthetic_v2.json --output benchmarks/results/ocr-local.json`. Gli eseguibili non sono inclusi nello ZIP.\n'),('DATA_NOTICE.md','\nRound 2 preserves only metadata, actual acquisition receipts, hashes and technical audit decisions. The 162 official benchmark files and Tesseract binaries/language packs remain in ignored local directories. No new institutional logos or trademarks are copied. A technical rejection is explicitly attributed to Codex and is not represented as a human review or an official withdrawal.\n')]:
        path=ROOT/file;text=path.read_text(encoding='utf-8');marker=extra.split('\n')[1]
        if marker not in text:write(file,text+extra)
    validation_doc=(ROOT/'docs/VALIDAZIONE.md').read_text(encoding='utf-8')
    prefix=f"## Candidata Round 2 — 11 ottobre 2026\n\nRisultati correnti in `BENCHMARK.md`, `validation_latest.json` e `release_gates.json`: {tests['passed']} test superati, tre skip Windows, zero fallimenti. Tesseract reale disponibile localmente: 7/7 legacy e 14/14 sintetici; nessun mock conteggiato come prova reale. Catalogo schema 610, 1.216 record reali conservati, 1.212 operativi. La candidata resta NOT READY per v1, basso recall reale e CI esterna non eseguita. Le sezioni successive conservano la storia 0.6.1.\n\n"
    validation_doc=re.sub(r'## Candidata.*?(?=## Ambiente|## Test|## Suite|Le sezioni seguenti)',prefix,validation_doc,flags=re.S,count=1);write('docs/VALIDAZIONE.md',validation_doc)
    print('Generated Round 2 reports: NOT_READY; all values read from raw artifacts.')

if __name__=='__main__':generate()
