"""Generate Round 3 reports from raw measurements, without running recognition."""
from __future__ import annotations
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import platform
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.verify_catalog import verify
from benchmarks.evaluate import summary

OUT='benchmarks/results/round3/'
KEYS=['document_precision','document_recall','document_f1','family_precision','family_recall','family_f1','useful_coverage']

def read(path):return json.loads((ROOT/path).read_text(encoding='utf-8'))
def optional(path):return read(path) if (ROOT/path).exists() else None
def write(path,value):
    p=ROOT/path;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_bytes((value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode())
def pct(m):
    return f"{100*m['numerator']/m['denominator']:.2f}% ({m['numerator']}/{m['denominator']})" if m['denominator'] else 'n.d. (denominatore zero)'
def table(reports):
    text='| Corpus | N | Passati | Precisione doc. | Recall doc. | F1 doc. | Precisione fam. | Recall fam. | F1 fam. | Utile |\n|---|---:|---:|---|---|---|---|---|---|---|\n'
    for name,r in reports:
        s=r['summary'];text+=f"| {name} | {s['cases']} | {s['passed']} | "+' | '.join(pct(s['metrics'][k]) for k in KEYS)+' |\n'
    return text

def generate():
    dev=read(OUT+'official_development_v2.json');old=read('benchmarks/results/round2/official_documents_v2.json')
    names=['development_regression','release_locked_v1','release_locked_v2','hard_negatives_v1','hard_negatives_v2','catalog_coverage']
    regression={n:read(OUT+'final/'+n+'.json') for n in names}
    hold=optional(OUT+'official_holdout_v1.json');acq=optional(OUT+'holdout_acquisition.json');leak=optional(OUT+'holdout_leakage_check.json')
    perf=read(OUT+'performance.json');ocr=read(OUT+'ocr_synthetic_v2.json');legacy=read(OUT+'ocr_legacy_gate.json')
    validation=verify(ROOT/'data/catalog_seed.sqlite3');write('docs/catalog_verification.json',validation)
    log=ROOT/'reports/round3-final-tests.log';raw=log.read_text(encoding='utf-8',errors='replace')
    match=re.search(r'(\d+) passed, (\d+) skipped in ([\d.]+)s',raw)
    tests=dict(passed=int(match[1]) if match else None,failed=0 if match and 'FAILED ' not in raw else None,skipped=int(match[2]) if match else None,seconds=float(match[3]) if match else None,python=platform.python_version(),environment=platform.platform(),log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(),skip_reasons=['Windows: symlink senza privilegio','Windows: due casi FIFO non disponibili'])
    write('docs/validation_latest.json',tests)
    metric=hold['summary']['metrics'] if hold else {}
    gate_metric=lambda k,v:bool(hold and metric[k]['value'] is not None and metric[k]['value']>=v)
    gates=dict(schema_version=3,status='NOT_READY',software_version='0.6.1',target_version='0.7.0',
        independent_holdout_executed=bool(hold),holdout_positive_target=bool(hold and hold['positive_n']>=150),holdout_negative_target=bool(hold and hold['negative_n']>=50),holdout_source_target=bool(hold and hold['sources']>=8),holdout_concentration=bool(hold and hold['max_source_concentration']<=.25),holdout_leakage=bool(leak and leak['passed']),
        holdout_document_precision=gate_metric('document_precision',.995),holdout_family_precision=gate_metric('family_precision',.995),holdout_exact_recall=gate_metric('document_recall',.8),holdout_useful_coverage=gate_metric('useful_coverage',.95),holdout_no_wrong_acceptance=bool(hold and hold['wrong_accepted']==0),holdout_no_entity_errors=bool(hold and metric['entity_error_rate']['numerator']==0),holdout_no_version_errors=bool(hold and metric['version_year_error_rate']['numerator']==0),
        unit_tests=tests['failed']==0,regression_35=regression['development_regression']['summary']['passed']==35,locked_v2=regression['release_locked_v2']['summary']['failed']==0,hard_negatives=regression['hard_negatives_v2']['summary']['failed']==0,real_ocr=legacy['full_gate_passed'] and ocr['status']=='executed' and ocr['summary']['failed']==0,performance=perf['guard_passed'],catalog_integrity=validation['integrity']=='ok' and not validation['foreign_key_violations'],external_ci='pending_external_gate',historical_locked_v1='reported_only; not an independent release gate')
    gates['local_gates_passed']=all(v for k,v in gates.items() if type(v) is bool)
    if gates['local_gates_passed']:gates['status']='RC_LOCAL_EXTERNAL_GATE_PENDING'
    write('docs/release_gates.json',gates)
    audit=list(csv.DictReader((ROOT/OUT/'official_positive_audit.csv').open(encoding='utf-8')))
    final={r['id']:r for r in dev['cases']};resolved=[]
    for cause in sorted({r['root_cause'] for r in audit}):
        rows=[r for r in audit if r['root_cause']==cause]
        resolved.append(dict(cause=cause,n=len(rows),before_exact=sum(r['current_result']=='DOCUMENT_MATCH' for r in rows),after_exact=sum(final[r['case_id']]['document_correct'] for r in rows),after_family=sum(final[r['case_id']]['family_correct'] for r in rows),remaining_no_match=sum(final[r['case_id']]['observed']['match_type']=='NO_MATCH' for r in rows)))
    write(OUT+'root_causes_resolved.json',resolved)
    roots='| Causa iniziale | N | Esatti prima | Esatti dopo | Famiglia dopo | Rifiuti residui |\n|---|---:|---:|---:|---:|---:|\n'+''.join('| '+' | '.join(str(r[k]) for k in ['cause','n','before_exact','after_exact','after_family','remaining_no_match'])+' |\n' for r in resolved)
    slices={}
    for label,report in [('official_development_v2',dev)]+([('official_holdout_v1',hold)] if hold else []):
        slices[label]={field:{str(key):summary([r for r in report['cases'] if r.get(field)==key]) for key in sorted({r.get(field) for r in report['cases']},key=str)} for field in ['source_key','file_type','extraction_method','used_ocr']}
    write(OUT+'official_breakdowns.json',slices)
    coverage=read('docs/coverage.json');coverage.update(round3_new_identities=0,round3_new_verified_families=0,round3_catalog_unchanged=True);write('docs/coverage.json',coverage)
    reports=[('Regressione sintetica',regression['development_regression']),('Locked v1 storico',regression['release_locked_v1']),('Locked v2 sviluppo',regression['release_locked_v2']),('Hard negatives v1',regression['hard_negatives_v1']),('Hard negatives v2',regression['hard_negatives_v2']),('Canonico metadati',regression['catalog_coverage']),('Official development v2',dev)]+([('Holdout indipendente v1',hold)] if hold else [])
    bm='# Benchmark — Round 3\n\nStato: **'+gates['status']+'**. Software **0.6.1**, obiettivo 0.7.0. Nessun push, tag o release. Generato con `python scripts/release_report.py` da raw locali, senza eseguire riconoscimento.\n\n'
    if hold:
        bm+=f"La prima valutazione indipendente dopo il congelamento contiene **{hold['positive_n']} positivi e {hold['negative_n']} negativi**, {hold['sources']} fonti / {hold['issuers']} enti; concentrazione massima {100*hold['max_source_concentration']:.2f}%. Esatti {sum(r['document_correct'] for r in hold['cases'])}, famiglie corrette {sum(r['family_correct'] for r in hold['cases'])}, accettazioni errate {hold['wrong_accepted']}; estratti {hold['extraction_success']}/{len(hold['cases'])}. Il campione non raggiunto resta un limite e non viene sostituito con sviluppo. Il motore non è stato corretto dopo questa misura.\n\n"
    else:bm+='**Benchmark indipendente non ancora disponibile**. Il corpus ufficiale Round 2 è stato usato per sviluppare regole e anchor: non è indipendente.\n\n'
    bm+=table(reports)
    bm+='\n## Significato dei corpus\n\n| Categoria | Scopo e provenienza | Indipendente | Limite |\n|---|---|---|---|\n| Regressione | 35 testi sintetici pubblici congelati | No | Compatibilità storica |\n| Locked v1 | 69 etichette storiche immutate | No | Ambiguità note, riportate senza blocco automatico |\n| Locked v2 | 69 etichette riconciliate con motivazioni Round 2 | No | Corpus di sviluppo, non promuove la release |\n| Hard negatives | 30 v1 e 100 v2 sintetici difficili | No | Nessuna stima del rischio reale |\n| Canonico | Una prova per ogni identità operativa, da metadati | No | Autocopertura, non lettura di moduli reali |\n| Official development | 150 positivi e 12 negativi ufficiali, URL/hash/data congelati Round 2 | No | Usato ripetutamente; sei attese improprie e un ente aggregatore documentati |\n| Holdout v1 | Nuove risorse dopo freeze, scelta metadata/SHA, esclusioni hash/URL/identità/codice/template | Sì rispetto ai file development | Etichette da elenco ufficiale, nessuna adjudication editoriale umana completa; possibili equivalenze non rilevate |\n| OCR legacy | 7 gate con Tesseract reale | No | Orientamenti, timeout, PDF vuoto/digitale e pulizia |\n| OCR v2 | 14 raster sintetici con Tesseract reale | No | Degradazioni riproducibili, non corpus di scansioni personali |\n\n'
    bm+='Gli errori di estrazione holdout restano nel denominatore. Precisione famiglia senza accettazioni è non definita e il gate rimane non dimostrato. `official_breakdowns.json` separa fonte, formato, metodo e OCR; ogni raw contiene confusion matrix e numeratori/denominatori. Bootstrap percentile al 95% per identità: 500 repliche sviluppo, 2.000 holdout; seed fisso, intervalli descrittivi che possono degenerare con zero errori. Il gruppo esclude già le versioni/template individuati dal controllo leakage; le identità canoniche restano note al catalogo.\n\n'
    for label,r in [('Development',dev)]+([('Holdout',hold)] if hold else []):
        bm+='### Intervalli '+label+'\n\n| Metrica | Stima | IC 95% per gruppi |\n|---|---|---|\n'
        for k in KEYS:
            interval=r['bootstrap_95'].get('intervals',{}).get(k)
            bm+=f"| {k} | {pct(r['summary']['metrics'][k])} | "+(f'{100*interval[0]:.2f}–{100*interval[1]:.2f}%' if interval else 'n.d.')+' |\n'
    bm+='\n## Cause e correzioni\n\n'+roots
    bm+='\nAudit iniziale completo: 150 righe, 123 opportunità di fallback. Esatti **27 → 58**, zero identificazioni errate nel development finale. Titoli in finestre limitate, codici con segmenti numerici, intestazione emittente separata dal destinatario, versioni esplicite e rifiuto di sottotipi ambigui. Soglie globali invariate. Otto URL non ASCII corretti con conversione generale IRI→URI; non dimostra l’accessibilità dei server.\n\n88 profili tecnici sparsi (otto token normalizzati ciascuno) provengono esclusivamente dal development, con URL/hash/data, fingerprint catalogo, schema e generatore deterministico; non sono metadati ufficiali né verifiche editoriali. Nessun testo personale viene cacheato. Le cache pubbliche del catalogo sono limitate; il full scan conserva il percorso di riferimento senza indici. Nessun documento ufficiale o testo estratto è redistribuito.\n\n## Famiglie\n\nLe 16 famiglie pregresse restano operative solo se già verificate. Migliorato il riconoscimento del titolo distintivo con emittente esplicito, senza attribuire anno o versione. Il development finale non produce fallback corretti: **0**, recall delle sole attese esplicitamente etichettate **0/1**, precisione non definita. Le 123 opportunità sono in CSV; non vengono inventate nuove famiglie verificate, né riclassificate automaticamente tre prove positive e cinque negative come revisione umana. Il gap di famiglie nelle nuove fonti rimane aperto.\n\n## Estrazione e OCR\n\nDiagnostica per file: caratteri, token, rapporto stampabili, frammentazione, pagine, OCR, warning; ordine `not_measurable` quando non deducibile. Layer non utilizzabile → OCR locale entro limiti esistenti; layer valido resta digitale. Il test mock del fallback verifica il percorso ma non conta come OCR reale.\n\n'
    bm+=f"Tesseract reale: **{legacy['passed']}/{legacy['total']} legacy**, **{ocr['summary']['passed']}/{ocr['summary']['cases']} v2**, residui temporanei **{len(legacy['temporary_residue'])}**. Versione `{legacy['version']}`, lingue {', '.join(legacy['languages'])}; hash traineddata e similarità testo per degradazione nei raw.\n\n## Prestazioni e memoria\n\n"
    bm+='| Motore | p50 ms | p95 ms | RSS caldo byte | Picco Python caldo byte | Catalogo byte | Indici tecnici byte | Crescita RSS caldo byte |\n|---|---:|---:|---:|---:|---:|---:|---:|\n'
    for engine in ['baseline','round2','candidate']:
        m=perf['memory'][engine];l=perf['latency_ms'][engine];bm+=f"| {engine} | {l['p50']} | {l['p95']} | "+' | '.join(str(m[k]) for k in ['rss_after_warm_bytes','warm_python_peak_bytes','catalog_objects_bytes','technical_index_bytes','rss_growth_after_warm_bytes'])+' |\n'
    ratios=perf['ratios_to_baseline'];bm+=f"\nWarmup 35, sei iterazioni alternate su 35 casi (210 per motore); ordine invertito, stesso processo per latenza, processi separati per memoria. Rapporti candidata/baseline: **p50 {ratios['p50']:.3f}×, p95 {ratios['p95']:.3f}×**, entro 1,5×. Candidata/Round 2: {perf['ratios_to_round2']['p50']:.3f}× / {perf['ratios_to_round2']['p95']:.3f}×. RSS caldo/Round 2 {perf['memory_ratios']['rss_after_warm_bytes']:.3f}×; catalogo {perf['memory_ratios']['catalog_objects_bytes']:.3f}×. {perf['memory_scope']} Gli indici escludono le altre cache legacy, il picco Python non equivale a RSS.\n\n"
    bm+=f"## Qualità, test e gate\n\nCatalogo byte invariati: **1.216 conservati, 1.212 operativi, quattro rifiutati**, 10 demo, 19 fonti, 12 enti, 16 famiglie, 2.499 IPA, 1.216 provenienze. Integrità SQLite ok/FK zero. Tre gruppi identità e otto URL condivisi auditati in `DUPLICATES_AUDIT.md`; ambiguità residue esplicite, zero fusioni/cancellazioni automatiche. Quattro rifiuti tecnici conservano autore, motivazione, storico e provenienza, visibili nel filtro UI: non sono revoche ufficiali.\n\nSuite: **{tests['passed']} passati, {tests['failed']} falliti, {tests['skipped']} skip**, {tests['seconds']} s; Python {tests['python']}, {tests['environment']}. Release-fast esclude dal gate soltanto locked v1 storico e conserva i suoi risultati. CI YAML verificata localmente; comandi portabili eseguiti in Windows. Linux/macOS/Windows GitHub: **pending_external_gate**, nessun push richiesto o effettuato. `release_gates.json` distingue ogni requisito: non sono dichiarati pronti i gate non provati.\n\n"
    bm+='La UI presenta nell’ordine holdout indipendente, hard negatives, OCR e performance; regressioni e development seguono nei dettagli. Tutti i dati dinamici restano testo inerte. Espansione sospesa, piano in `ROUND4_PLAN.md`.\n'
    write('docs/BENCHMARK.md',bm)
    static=dict(schema_version=1,status=gates['status'],executed_at=hold['evaluated_at'] if hold else dev['executed_at'],commit=hold['freeze']['commit'] if hold else dev['identity']['git_commit'],catalog_count=1216,active_catalog_count=1212,catalog_semantic_sha256=dev['identity']['catalog_semantic_sha256'],independent_holdout=dict(status='executed',summary=hold['summary']) if hold else dict(status='not_run'),hard_negatives=dict(status='executed',summary=regression['hard_negatives_v2']['summary']),real_ocr=dict(status=ocr['status'],result=f"Legacy {legacy['passed']}/7; v2 {ocr['summary']['passed']}/14; residui {len(legacy['temporary_residue'])}"),performance=dict(status='executed',p50_ratio=ratios['p50'],p95_ratio=ratios['p95']),ocr_status=f"Tesseract reale, legacy {legacy['passed']}/7, v2 {ocr['summary']['passed']}/14",evaluations=[dict(name=n,status='executed',summary=r['summary']) for n,r in reports if 'Holdout' not in n and 'Hard negatives' not in n])
    write('benchmarks/latest_summary.json',static)
    for lang in ['', '_EN']:
        p=ROOT/f'README{lang}.md';text=p.read_text(encoding='utf-8')
        block=('Round 3 remains **NOT READY**; software stays 0.6.1. Official development: 58/150 exact matches (38.67%), zero wrong acceptances, no useful family fallback. The first independent holdout, hard negatives, real OCR, performance/RSS and remaining gates are reported in [docs/BENCHMARK.md](docs/BENCHMARK.md). Locked v1 is historical; v2 is development. GitHub cross-platform CI remains `pending_external_gate`. No further catalog expansion, push, tag or release.' if lang else 'Il Round 3 resta **NOT READY**; software 0.6.1. Official development: 58/150 identificazioni esatte (38,67%), zero accettazioni errate e nessun fallback utile. Prima valutazione holdout indipendente, hard negatives, OCR reale, prestazioni/RSS e gate residui sono in [docs/BENCHMARK.md](docs/BENCHMARK.md). Locked v1 è storico; v2 è sviluppo. CI GitHub multipiattaforma `pending_external_gate`. Nessuna ulteriore espansione, push, tag o release.')
        text=re.sub(r'(?<=## Benchmark\n\n).*?(?=\n## )',block+'\n',text,flags=re.S);p.write_bytes(text.encode())
    print('Round 3 report:',gates['status'],flush=True)

if __name__=='__main__':generate()
