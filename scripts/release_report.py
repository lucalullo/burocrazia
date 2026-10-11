"""Generate release coverage, source census, benchmark summary and honest gates."""
from collections import Counter, defaultdict
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import platform
import re
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.verify_catalog import verify
from maintenance.build_catalog import verify_continuity
from maintenance.policy import validate_url


def read(path):return json.loads((ROOT/path).read_text(encoding='utf-8'))
def write(path,value):
    p=ROOT/path;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def pct(metric):
    n,d=metric['numerator'],metric['denominator']
    return f'{100*n/d:.2f}% ({n}/{d})' if d else 'n.d. (0 casi)'


def generate():
    manifest=read('data/catalog_manifest.json');audit=read('maintenance/releases/2026-10-11/audit.json')
    observations=read('maintenance/releases/2026-10-11/resource_observations.json')
    with sqlite3.connect((ROOT/'data/catalog_seed.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row;verify_continuity(db,read('data/baseline_v061_rows.json'))
        docs=[dict(r) for r in db.execute("SELECT * FROM documents WHERE stato_verifica<>'demo'")]
        fields=['codice','categoria','descrizione_ufficiale','versione','data_pubblicazione','download_url','fonte_url']
        coverage=dict(schema_version=1,executed_at=datetime.now(UTC).isoformat(),catalog_sha256=manifest['sha256'],
            baseline_real_documents=389,real_documents=len(docs),new_documents=len(docs)-389,growth_percent=round(100*(len(docs)-389)/389,4),demo_documents=10,
            families=16,sources=manifest['tables']['sources'],covered_issuers=len({d['ente'] for d in docs}),ipa_entities=2499,
            by_entity=dict(sorted(Counter(d['ente'] for d in docs).items())),by_category=dict(sorted(Counter(d['categoria'] or '(assente)' for d in docs).items())),
            by_source={str(r['source_id']):r['n'] for r in db.execute("SELECT source_id,count(*) n FROM documents WHERE stato_verifica<>'demo' GROUP BY source_id")},
            fields={f:dict(present=sum(bool(d[f] and str(d[f]).strip()) for d in docs),missing=sum(not(d[f] and str(d[f]).strip()) for d in docs)) for f in fields},
            structural_provenance=db.execute('SELECT count(*) FROM document_provenance').fetchone()[0],
            pending_editorial=sum(d['stato_verifica']=='da_verificare' for d in docs),verified_documents=sum(d['stato_verifica']=='verificato' for d in docs),
            local_official_files=0,resource_observations=len(observations),distinct_observed_resource_urls=len({x['url'] for r in observations for x in r['observation']['resources']}),
            withdrawn_automatically=0,superseded_automatically=0,all_baseline_rows_unchanged=True)
        groups=defaultdict(list);urls=defaultdict(list)
        from src.recognize import normalize_text
        for d in docs:
            groups[(d['ente'],normalize_text(d['codice'] or d['titolo_ufficiale']),d['versione'])].append(d['id'])
            if d['download_url']:urls[(d['ente'],d['download_url'])].append(d['id'])
        coverage['duplicate_identity_groups']=[v for v in groups.values() if len(v)>1]
        coverage['shared_download_url_groups']=[v for v in urls.values() if len(v)>1]
    for r in observations:
        for f in ['fonte_url','download_url','detail_url']:
            if r['observation'].get(f):validate_url(r['observation'][f],r['source_key'])
    write('docs/coverage.json',coverage);write('docs/catalog_verification.json',verify(ROOT/'data/catalog_seed.sqlite3'))
    md=f"# Copertura della candidata\n\nGenerato da `python scripts/release_report.py`. Catalogo `{manifest['sha256']}`.\n\n"
    md+='| Misura | Baseline 0.6.1 | Candidata |\n|---|---:|---:|\n'
    for label,before,after in [('Documenti reali',389,len(docs)),('Demo',10,10),('Famiglie',16,16),('Fonti registrate',15,coverage['sources']),('Enti con documenti',6,coverage['covered_issuers']),('Inventario IPA',2499,2499),('Provenienza strutturale',389,coverage['structural_provenance'])]:md+=f'| {label} | {before} | {after} |\n'
    md+=f"\nCrescita: {coverage['new_documents']} identità (+{coverage['growth_percent']:.2f}%). Tutti i documenti restano da revisionare; nessuna spiegazione aggiunta, tre schede preesistenti conservate. Non si dichiara che ogni identità sia riconoscibile: la prova canonica è in `BENCHMARK.md`.\n\n| Ente | Record |\n|---|---:|\n"
    md+=''.join(f'| {k} | {v} |\n' for k,v in coverage['by_entity'].items())
    md+='\n| Campo | Presente | Assente |\n|---|---:|---:|\n'+''.join(f"| {f} | {v['present']} | {v['missing']} |\n" for f,v in coverage['fields'].items())
    md+=f"\nIdentità, risorse e famiglie sono conteggi distinti: {coverage['resource_observations']} osservazioni di risorsa; {coverage['distinct_observed_resource_urls']} URL di risorse distinti; zero file ufficiali redistribuiti. Gruppi di possibile identità duplicata: {len(coverage['duplicate_identity_groups'])}; gruppi con download condiviso: {len(coverage['shared_download_url_groups'])}. Questi segnali includono dati ereditati e non autorizzano cancellazioni. Nessuna revoca o sostituzione automatica.\n\nTutte le 399 righe documentali iniziali, le 15 fonti, le 16 famiglie, i 2.499 enti, le 389 provenienze e le tre spiegazioni hanno impronte immutate. Le quattro nuove fonti restano `da_verificare`; il dominio ufficiale è verificato tecnicamente, senza attribuire una revisione umana. Record per fonte/categoria e gruppi di duplicazione sono in `coverage.json`.\n"
    write('docs/COVERAGE.md',md)
    write('docs/source_census.json',dict(schema_version=1,package_sha256=audit['package_sha256'],sources=audit['sources']))
    sm='# Censimento delle fonti\n\nAcquisizione del 11/10/2026, sequenziale, senza bypass. Le date/URL/errori/tentativi e ricevute sono in `source_census.json` e nell’audit del pacchetto. I conteggi scoperti comprendono duplicati ed esclusioni. “Importati” significa nuovi record; “già presenti” conserva il record senza sostituzione. Aggiornamenti distruttivi: zero.\n\n| Fonte | Scoperti | Importati | Aggiornati | Già presenti | Duplicati | Esclusi | Stato |\n|---|---:|---:|---:|---:|---:|---:|---|\n'
    for s in audit['sources']:sm+=f"| {s['source_key']} | {s['discovered']} | {s['new']} | {s['updated']} | {s['existing']} | {s['duplicates']} | {len(s['excluded'])} | {s['coverage_status']} |\n"
    sm+='\n## Perimetri e lavoro residuo\n\n`complete_for_declared_collection` indica soltanto che la coda dichiarata è esaurita e i metadati classificati, non tutta la burocrazia dell’ente. Sono percorsi tutti i quattro batch INPS italiani (357 elementi), l’indice INAIL, le quattro pagine Lavoro, i servizi INL di entrambe le raccolte, l’elenco Garante, i 16 elenchi Venezia, le sezioni radio/servizi alle imprese MIMIT, i nove moduli commerciali/turistici FP, l’elenco RGS e le pagine accesso ANAC/Unioncamere. Per FP restano edilizia e altre raccolte; per MIMIT restano altri procedimenti; per Giustizia restano altri uffici.\n\nADE, ADER e ADM: 403 nell’ambiente, senza aggiramento. MIT: verifica TLS fallita; Portale Automobilista ha restituito errore del server. ACI: redirect ufficiale verificato, infrastruttura collegata irraggiungibile. Salute: challenge Gcore HTTP 200, classificata come blocco. AgID e Polizia: pagina pubblica leggibile ma nessun modulo identificabile dal parser nel perimetro; richiedono analisi/manuale. Registro Imprese: URL selezionato 404, non prova che l’intero ente sia inaccessibile. Interno: indice e procedura cittadinanza leggibili, senza file statici acquisibili; non è stata attraversata ogni Prefettura. Nessuna espansione IPA effettuata.\n\nIl Garante espone servizi online, pagine informative e download; dodici risorse non identificate come moduli sono escluse. Alcuni download condivisi nei dati preesistenti richiedono revisione, senza inventare revoche. Le risorse linguistiche INL sono unite per codice esplicito; PDF/DOCX non aumentano le identità. Le categorie HTML derivate restano nell’audit tecnico.\n'
    write('docs/SOURCES.md',sm)
    result_dir=ROOT/'benchmarks/results/candidate'
    names=['development_regression','release_locked_v1','hard_negatives_v1','catalog_coverage']
    reports=[read('benchmarks/results/candidate/'+n+'.json') for n in names if (result_dir/(n+'.json')).exists()]
    if len(reports)!=4:return
    development,locked,negative,canonical=reports
    official=read('benchmarks/results/official_documents_v1.json');ocr=read('benchmarks/results/ocr_synthetic_v1.json')
    test_log=ROOT/'reports/final-tests.log';log=test_log.read_text(encoding='utf-8',errors='replace') if test_log.exists() else ''
    match=re.search(r'(\d+) passed(?:, (\d+) skipped)? in ([\d.]+)s',log)
    tests=dict(passed=int(match[1]) if match else None,skipped=int(match[2] or 0) if match else None,seconds=float(match[3]) if match else None,
               failed=0 if match and 'FAILED ' not in log else None,environment=platform.platform(),python=platform.python_version(),
               log_sha256=hashlib.sha256(test_log.read_bytes()).hexdigest() if test_log.exists() else None,
               skip_reasons=['Windows: creazione symlink senza privilegio','Windows: FIFO non disponibile (due test)'])
    write('docs/validation_latest.json',tests)
    m=locked['summary']['metrics'];om=official['summary']['metrics']
    gates=dict(schema_version=1,status='NOT_READY',software_version='0.6.1',target_version='0.7.0',evaluated_commit=locked['identity']['git_commit'],
        regression_35=development['summary']['passed']==35,unit_tests=tests['failed']==0,sqlite_integrity=True,foreign_keys=True,new_provenance_100_percent=True,baseline_continuity=True,
        locked_document_precision_99=(m['document_precision']['value'] or 0)>=.99,locked_family_precision_99=(m['family_precision']['value'] or 0)>=.99,
        hard_negative_zero_acceptance=negative['summary']['metrics']['unknown_false_acceptance_rate']['value']==0,
        locked_no_entity_errors=m['entity_error_rate']['numerator']==0,locked_no_version_errors=m['version_year_error_rate']['numerator']==0,
        official_no_entity_errors=om['entity_error_rate']['numerator']==0,real_ocr=ocr['status']=='executed' and ocr['summary']['failed']==0,
        cross_platform_ci='not_run',release_fast_exit='1: frozen release cases fail; CI deliberately retains this failure')
    write('docs/release_gates.json',gates)
    bm='# Benchmark della candidata\n\nGenerato da `python scripts/release_report.py`. Stato: **NON PRONTO**. Versione software mantenuta a 0.6.1; obiettivo 0.7.0. Nessun tag/push/release. Il commit valutato e tutte le impronte sono nei risultati raw; il commit finale può aggiungere report/documentazione senza cambiare il codice misurato.\n\n'
    bm+='| Corpus | Casi | Passati | Precisione documento | Recall documento | F1 documento | Precisione famiglia | Recall famiglia | F1 famiglia | Copertura utile |\n|---|---:|---:|---|---|---|---|---|---|---|\n'
    for r in reports+[official]:
        ms=r['summary']['metrics'];bm+=f"| {r['corpus_id']} | {r['summary']['cases']} | {r['summary']['passed']} | "+' | '.join(pct(ms[k]) for k in ['document_precision','document_recall','document_f1','family_precision','family_recall','family_f1','useful_coverage'])+' |\n'
    bm+='\n## Rifiuti ed errori\n\n| Corpus | False accettazioni sconosciuti | Rifiuti corretti sconosciuti | Rifiuto supportati | Errori ente | Errori versione |\n|---|---|---|---|---|---|\n'
    for r in reports+[official]:bm+='| '+r['corpus_id']+' | '+' | '.join(pct(r['summary']['metrics'][k]) for k in ['unknown_false_acceptance_rate','unknown_correct_rejection_rate','supported_rejection_rate','entity_error_rate','version_year_error_rate'])+' |\n'
    bm+='\nCopertura canonica: `'+json.dumps(canonical['coverage'],ensure_ascii=False)+'`. Questa è autocopertura dei metadati, non qualità su scansioni. Le confusion matrix, il macro per fonte, i breakdown per categoria/rumore e gli intervalli bootstrap al 95% per gruppi sono nei JSON raw. Denominatore zero significa non definito.\n\n'
    bm+='Il locked v1 contiene sei casi con titoli generici senza evidenza distintiva, due famiglie con evidenza insufficiente e due attese di famiglia per testi che identificano documenti già censiti. Le etichette non sono cambiate per far passare il candidato. Il corpus è pubblico/sintetico, con possibile sovrapposizione fra famiglie di sviluppo e release: non è indipendente. Il vecchio motore passava 49/69 e accettava 11/30 negativi difficili; i dettagli restano in `benchmarks/results/baseline_v061/`.\n\n'
    bm+=f"Campione ufficiale: {len(official['attempts'])} file tentati, {official['summary']['cases']} estratti e valutati, {official['summary']['passed']} identificati correttamente. Non esiste una prova di generalizzazione ampia. Il PDF INPS non leggibile rimane un errore di estrazione, separato dal matching. Le etichette emittente FP descrivono il produttore del modello nazionale, che il file destinato al SUAP può non riportare; si preferisce il rifiuto. Nessun testo estratto o PDF entra nel repository.\n\nOCR reale: `{ocr['status']}`, {ocr['summary']['cases']}/{len(ocr['attempts'])} eseguiti. Tesseract assente in questo ambiente; i 12 raster sono generabili ma non costituiscono una prova OCR. Il precedente 7/7 della 0.6.1 è una misura storica, non una verifica corrente.\n\n"
    bm+='## Prestazioni\n\n| Corpus | p50 ms | p95 ms | p99 ms |\n|---|---:|---:|---:|\n'
    baseline=read('benchmarks/results/baseline_v061/development_regression.json')
    for r in [baseline]+reports:
        l=r['summary']['latency_ms'];bm+=f"| {r['corpus_id']} ({r['catalog']['real_documents']} reali) | {l['p50']} | {l['p95']} | {l['p99']} |\n"
    bm+='\nBaseline e candidata usano full scan; la candidata prepara/cachea solo metadati del catalogo, con limite 4.096 elementi. I 134 testi congelati hanno un test differenziale tra cache e preparazione senza cache. Nessun testo caricato viene cacheato. I tempi di preparazione, caricamento e picchi Python sono nei raw; la memoria candidata include una cache fredda, mentre la baseline originaria misurava la singola inferenza senza questa cache: non sono confronti di RSS/processo. Nessun prefiltraggio dei candidati, nessun indice semantico, nessuna prova di equivalenza con un motore indicizzato dichiarata. Il p99 è pubblicato soltanto con almeno 100 casi.\n\n'
    bm+=f"## Gate e verifiche\n\nSuite: {tests['passed']} passati, {tests['failed']} fallimenti, {tests['skipped']} skip; Python {tests['python']}, Windows locale. Integrità SQLite ok, FK zero, provenienza 100% delle aggiunte, continuità storica e runtime offline verificati dai test. Il comando release fast restituisce 1 per i casi locked non passati: la CI conserva questo fallimento. La matrice Linux/macOS/Windows remota non è stata eseguita. Il gate di precisione documentale >=99%, l'OCR reale e la CI multipiattaforma impediscono la promozione. Vedere `release_gates.json` e `validation_latest.json`.\n"
    write('docs/BENCHMARK.md',bm)
    write('benchmarks/latest_summary.json',dict(schema_version=1,status='NON PRONTO',executed_at=locked['executed_at'],commit=locked['identity']['git_commit'],
        catalog_semantic_sha256=locked['identity']['catalog_semantic_sha256'],ocr_status=ocr['status']+': Tesseract assente',
        evaluations=[dict(name=r['corpus_id'],summary=r['summary']) for r in reports+[official]]))
    update_readmes(coverage)


def update_readmes(coverage):
    for lang in ['','_EN']:
        p=ROOT/f'README{lang}.md';text=p.read_text(encoding='utf-8');en=bool(lang)
        replacements={'389/389':f"{coverage['real_documents']}/{coverage['real_documents']}",'389':str(coverage['real_documents']),
            ('| Registered and verified source records | 15 |' if en else '| Fonti registrate e verificate | 15 |'):('| Registered sources (15 legacy verified, 4 pending) | 19 |' if en else '| Fonti registrate (15 verificate pregresse, 4 da verificare) | 19 |'),
            ('| Authorities represented by real document records | 6 |' if en else '| Enti rappresentati dai documenti reali | 6 |'):('| Authorities represented by real document records | 12 |' if en else '| Enti rappresentati dai documenti reali | 12 |'),
            ('## What is included in v0.6.1' if en else '## Cosa contiene la v0.6.1'):('## What this candidate includes' if en else '## Cosa contiene questa candidata')}
        for a,b in replacements.items():text=text.replace(a,b)
        marker='## Tests' if en else '## Test'
        if '## Benchmark\n' not in text:
            block=('## Benchmark\n\nThe 11 October 2026 candidate is **not ready for release**; software version remains 0.6.1 pending the 0.7.0 gates. Separate frozen text regression, canonical coverage, hard negatives, real-file extraction and real OCR results are reported in [docs/BENCHMARK.md](docs/BENCHMARK.md). Counts are generated from the seed by `python scripts/release_report.py`; acquisition scope and remaining blocks are in [docs/SOURCES.md](docs/SOURCES.md). Tesseract is unavailable in the current environment; historical OCR results above have not been revalidated. The release-fast benchmark currently fails on the unchanged locked corpus, and remote cross-platform CI has not been run.\n\n' if en else '## Benchmark\n\nLa candidata del 11 ottobre 2026 è **non pronta per la release**; la versione software resta 0.6.1 in attesa dei gate 0.7.0. Regressione congelata, copertura canonica, negativi difficili, estrazione di file reali e OCR reale sono separati in [docs/BENCHMARK.md](docs/BENCHMARK.md). I conteggi sono generati dal seed con `python scripts/release_report.py`; perimetri e blocchi sono in [docs/SOURCES.md](docs/SOURCES.md). Tesseract non è disponibile nell’ambiente attuale: i risultati OCR storici sopra non sono stati riconfermati. Il benchmark release fast fallisce sul corpus locked invariato e la CI multipiattaforma remota non è stata eseguita.\n\n')
            text=text.replace(marker,block+marker,1)
        if '- **Benchmark**' not in text:
            text=text.replace('- **Editorial review** - maintain local content.','- **Editorial review** - maintain local content.\n- **Benchmark** - inspect static evaluation results.') if en else text.replace('- **Revisione editoriale** - strumenti per la manutenzione dei contenuti.','- **Revisione editoriale** - strumenti per la manutenzione dei contenuti.\n- **Benchmark** - consulta i risultati statici delle valutazioni.')
        text=text.replace('The real document records currently cover:','The six original issuers below are joined by MIMIT, the Department for Public Administration, Venice Court, MEF/RGS, ANAC and Unioncamere. The original issuers are:') if en else text.replace('Gli enti attualmente rappresentati dai record reali sono:','Ai sei enti originari elencati sotto si aggiungono MIMIT, Funzione Pubblica, Tribunale di Venezia, MEF/RGS, ANAC e Unioncamere. Gli enti originari sono:')
        p.write_text(text,encoding='utf-8')


if __name__=='__main__':generate()
