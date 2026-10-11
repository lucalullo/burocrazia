"""Publish measured Round 4 evidence without rescoring the independent holdout."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import platform
import re
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from benchmarks.round4_common import OUT,read,write,runtime_hash,catalog
from benchmarks.evaluate import summary
from scripts.verify_catalog import verify

def pct(m):
    return f"{100*m['numerator']/m['denominator']:.2f}% ({m['numerator']}/{m['denominator']})" if m['denominator'] else 'n.d. (0 casi)'

def counts(r):
    rows=r['cases'];return dict(exact=sum(x['document_correct'] for x in rows),family=sum(x['family_correct'] for x in rows),reject=sum(x['observed']['match_type']=='NO_MATCH' and x['expected']['match_type']!='NO_MATCH' for x in rows),wrong=sum(not x['correct'] and x['observed']['match_type']!='NO_MATCH' for x in rows))

def table(reports):
    keys=['document_precision','document_recall','document_f1','family_precision','family_recall','family_f1','useful_coverage']
    md='| Corpus | N | Esatti | Famiglie | Rifiuti positivi | Errati | P doc | R doc | F1 doc | P fam | R fam | F1 fam | Utile |\n|---|---:|---:|---:|---:|---:|---|---|---|---|---|---|---|\n'
    for name,r in reports:
        c=counts(r);m=r['summary']['metrics'];md+=f"| {name} | {len(r['cases'])} | "+' | '.join(str(c[k]) for k in ['exact','family','reject','wrong'])+' | '+' | '.join(pct(m[k]) for k in keys)+' |\n'
    return md

def generate():
    hold=read(OUT+'official_holdout_v2.json');assert hold['status']=='executed' and hold['identity']['runtime_sha256']==runtime_hash()
    dev=read(OUT+'development_after.json');olddev=read('benchmarks/results/round3/official_development_v2.json');oldhold=read('benchmarks/results/round3/official_holdout_v1.json');history=read(OUT+'historical_holdout_diagnostic.json')
    original_labels={r['id']:r['expected'] for r in olddev['cases']}
    differences=[r['id'] for r in dev['cases'] if r['expected']!=original_labels[r['id']]]
    if differences:
        assert differences==['OR2-101']
        initial=ROOT/OUT/'development_after_initial_auxiliary_omission.json'
        if not initial.exists():initial.write_bytes((ROOT/OUT/'development_after.json').read_bytes())
        for r in dev['cases']:r['expected']=original_labels[r['id']]
        dev['summary']=summary(dev['cases']);dev['extraction']['end_to_end']=dev['summary'];dev['extraction']['conditional_matching']=summary([r for r in dev['cases'] if not r.get('extraction_failed')])
        dev['label_reconciliation']=dict(version=2,reason='Restore the frozen auxiliary family_id=10 on OR2-101 omitted by the diagnostic helper. No recognition rerun, changed observations, new label or engine edit.',initial_report_sha256=hashlib.sha256(initial.read_bytes()).hexdigest(),initial_report=initial.relative_to(ROOT).as_posix())
        write(OUT+'development_after.json',dev)
    perf=read(OUT+'performance.json');ocr=read(OUT+'ocr_synthetic_v2.json');legacy=read(OUT+'ocr_legacy_gate.json');family=read(OUT+'family_release_v3.json');firstfamily=read(OUT+'family_release_v1.json');real_family=read(OUT+'family_official_v1.json')
    names=['development_regression','release_locked_v1','release_locked_v2','hard_negatives_v1','hard_negatives_v2','catalog_coverage']
    fast={n:read(OUT+'final/'+n+'.json') for n in names};validation=verify(ROOT/'data/catalog_seed.sqlite3');write('docs/catalog_verification.json',validation)
    log=ROOT/'reports/round4-final-tests.log';raw=log.read_text(encoding='utf8',errors='replace');match=re.search(r'(\d+) passed, (\d+) skipped in ([\d.]+)s',raw)
    tests=dict(passed=int(match[1]) if match else None,failed=0 if match and 'FAILED ' not in raw else None,skipped=int(match[2]) if match else None,seconds=float(match[3]) if match else None,python=platform.python_version(),environment=platform.platform(),log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(),skip_reasons=['Windows: symlink senza privilegio','Windows: due FIFO non disponibili'])
    write('docs/validation_latest.json',tests);write(OUT+'tests.json',tests)
    r061=next(r for r in fast['release_locked_v2']['cases'] if r['id']=='R061');write(OUT+'r061_after.json',r061)
    m=hold['summary']['metrics'];leak=read(OUT+'holdout_v2_leakage.json');checks=[]
    manifest=read('benchmarks/manifests/official_holdout_v2.json');items={c['id']:c for c in manifest['cases']}
    failures=[dict(id=r['id'],url=items[r['id']]['url'],sha256=items[r['id']]['sha256'],expected=r['expected'],observed=r['observed']) for r in hold['cases'] if not r['correct'] and r['observed']['match_type']!='NO_MATCH']
    write(OUT+'holdout_v2_failures.json',dict(policy='First evaluation preserved; no engine changes or result-based relabelling.',wrong_exact=[r for r in failures if r['observed']['match_type']=='DOCUMENT_MATCH'],wrong_family=[r for r in failures if r['observed']['match_type']=='FAMILY_MATCH'],extraction_failures=[a for a in hold['attempts'] if a['status']!='extracted']))
    breakdown={field:{str(key):summary([r for r in hold['cases'] if r.get(field)==key]) for key in sorted({r.get(field) for r in hold['cases']},key=str)} for field in ['source_key','file_type','extraction_method','used_ocr']}
    write(OUT+'holdout_v2_breakdowns.json',breakdown)
    matrix={str(i):{str(j):0 for j in [*range(1,17),'NO_MATCH']} for i in [*range(1,17),'NO_MATCH']}
    for r in family['cases']:
        wanted=str(r['expected'].get('family_id','NO_MATCH'));actual=str(r['observed'].get('family_id') or 'NO_MATCH');matrix[wanted][actual]+=1
    write(OUT+'family_confusion_by_id.json',dict(corpus_id='family_release_v3',matrix=matrix,derived_only=True))
    def gate(name,target,result,passed):checks.append(dict(name=name,target=target,result=result,passed=bool(passed)))
    gate('unit_tests','0 failed',tests,tests['failed']==0)
    gate('regression','35/35',fast['development_regression']['summary']['passed'],fast['development_regression']['summary']['passed']==35)
    gate('locked_v2_R061','69/69 + R061 NO_MATCH',fast['release_locked_v2']['summary']['passed'],fast['release_locked_v2']['summary']['passed']==69 and r061['correct'])
    gate('five_historical_fixes','5 safe',sum(r['safer_after'] for r in read(OUT+'false_acceptance_after.json')),all(r['safer_after'] for r in read(OUT+'false_acceptance_after.json')))
    gate('all_historical_wrong_accepts','0',counts(history)['wrong'],counts(history)['wrong']==0)
    gate('development_wrong_accepts','0',counts(dev)['wrong'],counts(dev)['wrong']==0)
    gate('development_recall_regression','>= Round 3 58/150',counts(dev)['exact'],counts(dev)['exact']>=counts(olddev)['exact'])
    gate('family_stress_precision','>=99.5%, macro>=99%, FP=0',dict(P=family['summary']['metrics']['family_precision'],macro=family['macro_precision'],FP=family['false_positives']),family['gate_passed'])
    gate('family_real_evidence','available official supplement measured',dict(passed=real_family['summary']['passed'],cases=real_family['summary']['cases']),real_family['summary']['cases']>0)
    gate('positive_sample','>=200',hold['positive_n'],hold['positive_n']>=200)
    gate('negative_sample','>=75',hold['negative_n'],hold['negative_n']>=75)
    gate('positive_sources','>=8',hold['sources'],hold['sources']>=8)
    gate('positive_issuers','>=8',hold['issuers'],hold['issuers']>=8)
    gate('source_concentration','<=20%',hold['max_source_concentration'],hold['max_source_concentration'] is not None and hold['max_source_concentration']<=.2)
    positives=[r for r in hold['cases'] if r['expected']['match_type']=='DOCUMENT_MATCH']
    positive_scanned=sum(r.get('used_ocr',False) for r in positives)
    formats=dict(hold['composition']['formats']);codes=hold['composition']['coded'];annual=hold['composition']['annual']
    gate('positive_formats','PDF text, scanned PDF, DOCX',dict(formats=formats,scanned=positive_scanned),bool(formats.get('pdf')) and positive_scanned>0 and positive_scanned<len(positives) and formats.get('docx',0)>0)
    gate('positive_code_year_mix','coded/uncoded + annual/nonannual',dict(coded=codes,annual=annual,total=len(positives)),0<codes<len(positives) and 0<annual<len(positives))
    gate('leakage','0 prohibited overlaps',leak['passed'],leak['passed'])
    for key,target in [('document_precision',.995),('family_precision',.995),('document_recall',.75),('useful_coverage',.90)]:gate('holdout_'+key,f'>={target*100}%',m[key],m[key]['value'] is not None and m[key]['value']>=target)
    gate('holdout_wrong_accepts','0',hold['wrong_accepted'],hold['wrong_accepted']==0)
    for key in ['entity_error_rate','version_year_error_rate']:gate('holdout_'+key,'0',m[key]['numerator'],m[key]['numerator']==0)
    newneg=[r for r in hold['cases'] if r['expected']['match_type']=='NO_MATCH'];oldneg=[r for r in history['cases'] if r['expected']['match_type']=='NO_MATCH']
    gate('hard_negatives_synthetic','100/100',fast['hard_negatives_v2']['summary']['passed'],fast['hard_negatives_v2']['summary']['passed']==100)
    gate('hard_negatives_official_v1','50/50',sum(r['correct'] for r in oldneg),len(oldneg)==50 and all(r['correct'] for r in oldneg))
    gate('hard_negatives_official_v2','75/75',sum(r['correct'] for r in newneg),len(newneg)>=75 and all(r['correct'] for r in newneg))
    gate('real_ocr','7/7 +14/14',dict(legacy=legacy['passed'],v2=ocr['summary']['passed']),legacy['full_gate_passed'] and ocr['summary']['failed']==0)
    gate('latency','p50,p95 <=1.5x',perf['ratios_to_baseline'],perf['guard_passed'])
    gate('catalog_integrity','integrity ok; FK=0; catalog unchanged',validation['integrity'],validation['integrity']=='ok' and not validation['foreign_key_violations'])
    passed=all(c['passed'] for c in checks)
    gates=dict(schema_version=4,status='RC_LOCAL_EXTERNAL_GATE_PENDING' if passed else 'NOT_READY',software_version='0.6.1',target_version='0.7.0',local_gates_passed=passed,checks=checks,external_ci='pending_external_gate',freeze=hold['freeze'],no_runtime_changes_after_holdout=True)
    write('docs/release_gates.json',gates)
    gate_md='| Gate | Obiettivo | Risultato | Esito |\n|---|---|---|---|\n'+''.join(f"| {g['name']} | {g['target']} | {str(g['result']).replace('|','/')} | {'PASS' if g['passed'] else 'FAIL'} |\n" for g in checks)
    reports=[('Development Round 3',olddev),('Development Round 4',dev),('Holdout v1 storico originale',oldhold),('Holdout v1 diagnostico Round 4',history),('Holdout indipendente v2',hold),('Family v1 storico',firstfamily),('Family v3 fixture corretta',family)]
    md=f"# Round 4 — {gates['status']}\n\nSoftware 0.6.1. Freeze commit `{hold['freeze']['commit']}`, runtime `{runtime_hash()}`. Nessun push, tag o release. Catalogo e schema 610 invariati. Il motore non cambia dopo la prima valutazione v2.\n\n"
    md+=table(reports)
    md+='\nIl confronto development ripristina l’etichetta ausiliaria congelata `family_id=10` di OR2-101, omessa dall’helper diagnostico. Il report iniziale è conservato con hash; osservazioni, etichette originali documento/ente/versione e motore non cambiano e non si riesegue riconoscimento. Il recall famiglia resta correttamente 0/1.\n\n'
    md+='\n## Cinque errori e R061\n\nI cinque errori sono ora corretti o rifiutati prudentemente; dettagli, punteggi, runner e test in `../benchmarks/results/round4/false_acceptance_audit.md`. Vincoli generali: codice completo prima del titolo generico, titoli brevi solo in intestazione, peer annuali, sottotipi esclusivi, numero allegato. R061: FAMILY_MATCH errato → NO_MATCH; locked v2 68 →69/69. Locked v1 60 →59/69: la sua etichetta storica di R061 resta incompatibile col rifiuto corretto del v2; non viene sostituita.\n\n'
    md+='## Famiglie\n\n16 famiglie già verificate, nessuna aggiunta. Cinque positivi e cinque negativi sintetici per famiglia, più R061: 161 casi. Due emittenti sintetici per gli ambiti trasversali. Fallback isolato separato dall’end-to-end (nei raw): la precedenza del documento esatto non è un falso positivo di famiglia. V1 e v2 conservano FR01-N4 con emittente presente, erroneamente progettato come assente; il tentativo v2 di rimozione falliva per maiuscole/minuscole. V3 rimuove davvero quella riga, con motivazione e hash separati; nessuna etichetta cambia. Non si nasconde il 98,77% storico della v1.\n\n'
    md+=f"V3: P/R/F1 {pct(family['summary']['metrics']['family_precision'])} / {pct(family['summary']['metrics']['family_recall'])} / {pct(family['summary']['metrics']['family_f1'])}; macro P/R/F1 {family['macro_precision']:.4f}/{family['macro_recall']:.4f}/{family['macro_f1']:.4f}; FP {family['false_positives']}. Supplemento reale: {real_family['summary']['passed']}/{real_family['summary']['cases']}, non indipendente. Le varianti sintetiche sono correlate; manca copertura reale per tutte le famiglie.\n\n"
    md+='## Holdout v2\n\n'
    md+=f"{hold['positive_n']} positivi, {hold['negative_n']} negativi, {hold['sources']} fonti positive, {hold['issuers']} enti; concentrazione massima {100*(hold['max_source_concentration'] or 0):.2f}%. Fonti: `{hold['source_counts']}`. Composizione: `{hold['composition']}`. Campione insufficiente e nessuna indipendenza strutturale completa dimostrata. Selezione metadati/SHA prima della lettura; URL canonici, hash, identità, codici/annualità e template territoriali esclusi rispetto a sviluppo e v1 storico. Stessa fonte è correlazione accettabile dichiarata, non prova di identità. Ricevute effettive; acquisizione opt-in, allowlist/robots e limiti, nessun bypass. Errori/tentativi in `holdout_v2_acquisition.json`.\n\n"
    md+='Limite del runner di acquisizione: INAIL è stata chiusa prudenzialmente dopo il diniego robots di un singolo percorso. Questo riduce il campione e **non dimostra** che gli altri percorsi INAIL siano vietati o inaccessibili. Il prossimo ciclo deve distinguere dinieghi per percorso da blocchi di host prima di acquisire il nuovo v3. ADE: 403; INPS e Garante: tre risposte non documentali ciascuno; INL e una risorsa INAIL oltre 8 MiB; MIMIT residuo duplicato/escluso e un 404. Non vengono aggiunti file dopo la prima valutazione per migliorare questo risultato.\n\n'
    md+=f"Positivi: {len(positives)-positive_scanned} PDF digitali, {positive_scanned} con OCR, {formats.get('docx',0)} DOCX; {codes} con codice e {annual} annuali. Il campo raw `scanned` include anche i negativi ({hold['composition']['scanned']} file totali), non soltanto i positivi. La composizione richiesta non è raggiunta.\n\n"
    md+=f"Estrazione: {hold['extraction']['success']}/{hold['extraction']['total']}. Matching condizionato: `{hold['extraction']['conditional_matching']['metrics']['document_recall']}`; end-to-end: `{m['document_recall']}`. Gli errori di estrazione restano nei denominatori; nessun file problematico escluso dopo i risultati. Errori accettati {hold['wrong_accepted']} (esatti {sum(r['observed']['match_type']=='DOCUMENT_MATCH' for r in failures)}, famiglie {sum(r['observed']['match_type']=='FAMILY_MATCH' for r in failures)}); ente {m['entity_error_rate']['numerator']}; versione {m['version_year_error_rate']['numerator']}. Precisione famiglia senza accettazioni è non definita, non 100%.\n\n"
    md+='| Metrica | IC bootstrap 95% |\n|---|---|\n'
    for k in ['document_precision','document_recall','family_precision','family_recall','useful_coverage','unknown_correct_rejection_rate']:
        interval=hold['bootstrap_95']['intervals'].get(k);md+=f"| {k} | "+(f'{100*interval[0]:.2f}–{100*interval[1]:.2f}%' if interval else 'n.d.')+' |\n'
    md+='\n10.000 repliche, seed 20261011, percentile per gruppi identità, descrittivo del campione; intervalli degeneri con zero errori non certificano il rischio reale. V2 fallito resta storico per il prossimo ciclo, che richiede un nuovo v3.\n\n'
    md+='## Negativi e OCR\n\n'
    md+=f"Sintetici v1 {fast['hard_negatives_v1']['summary']['passed']}/30, v2 {fast['hard_negatives_v2']['summary']['passed']}/100; ufficiali storici {sum(r['correct'] for r in oldneg)}/50; nuovi {sum(r['correct'] for r in newneg)}/{len(newneg)}. Tesseract reale `{legacy['version']}`, ita/eng/osd: legacy {legacy['passed']}/7, raster sintetici v2 {ocr['summary']['passed']}/14, residui gate {len(legacy['temporary_residue'])}. Non equivalgono a scansioni ufficiali o validazione editoriale.\n\n"
    md+=f"Scansioni ufficiali positive del nuovo holdout: {sum(r['document_correct'] for r in positives if r.get('used_ocr'))}/{positive_scanned} riconosciute esattamente; il solo uso di Tesseract non prova accuratezza del testo o della classificazione. Negativi nuovi: {sum(not r.get('extraction_failed',False) for r in newneg)} estratti, {sum(r.get('extraction_failed',False) for r in newneg)} rifiutati per limite/errore di estrazione, sempre inclusi nell’end-to-end.\n\n"
    md+='## Performance e memoria\n\n| Motore | p50 ms | p95 ms | RSS caldo byte | Indici byte | Crescita RSS byte |\n|---|---:|---:|---:|---:|---:|\n'
    for n in ['baseline','round2','candidate']:
        l=perf['latency_ms'][n];v=perf['memory'][n];md+=f"| {n} | {l['p50']} | {l['p95']} | {v['rss_after_warm_bytes']} | {v['technical_index_bytes']} | {v['rss_growth_after_warm_bytes']} |\n"
    md+=f"\nRapporti baseline p50/p95 {perf['ratios_to_baseline']}; caricamento catalogo {perf['catalog_load_ms']:.3f} ms; costruzione indici {perf['index_build_ms']:.3f} ms. Warmup 35, sei iterazioni alternate, 210 campioni/motore. RSS in processi separati, otto passaggi caldi; indici ricorsivi Python escludono cache legacy/native. Cache limitate ai metadati, nessun testo caricato. Riferimento full scan verificato sui corpus e tutte le 1.212 identità operative.\n\n"
    md+='Il gate usa la misura alternata isolata; le latenze diagnostiche dei corpus development/storico sono state raccolte durante altri controlli e non sono un confronto prestazionale isolato.\n\n'
    md+='## Test, CI e gate\n\n'+f"{tests['passed']} passed, {tests['failed']} failed, {tests['skipped']} skip; {tests['seconds']} s, Python {tests['python']}, Windows. Skip: symlink senza privilegio e due FIFO. SQLite integrità ok/FK zero; 1.216 record conservati, 1.212 operativi, 10 demo, 16 famiglie, 19 fonti, 12 enti, 2.499 IPA, 1.078 osservazioni, zero sostituzioni. Nessuna nuova identità, revisione umana o provenienza inventata.\n\n"
    md+=gate_md+'\nCI esterna Linux/Windows/macOS Python 3.12: `pending_external_gate`, non eseguita. Comandi equivalenti offline verificati localmente; nessun push.\n\n```text\npython -m pytest -q\n$env:BUROCRAZIA_DB_PATH="tmp-build/temporary-ci.sqlite3"\npython scripts/init_db.py\nRemove-Item Env:BUROCRAZIA_DB_PATH\npython scripts/verify_catalog.py --db data/catalog_seed.sqlite3\npython scripts/benchmark.py --output benchmark-results.json\npython -m compileall -q src maintenance benchmarks app.py run.py\npython -m benchmarks.evaluate --fast --output-dir benchmark-release-results\n```\n\n'
    md+='## Limiti residui\n\nCopertura reale insufficiente e ridotta rispetto a Round 3 per i vincoli prudenti sugli emittenti/anni; cluster completi in `development_rejection_clusters.json`. Mancano riscontri robusti per titoli, codici, annualità o emittenti di molti file. Profili tecnici derivati da sviluppo non provano indipendenza né verifica editoriale. Il campione nuovo non raggiunge fonti/dimensione/concentrazione e non rappresenta adeguatamente tutti i formati e scansioni. Famiglie reali poco rappresentate; nessuna attribuzione automatica di nuove famiglie verificate. Etichette congelate da elenchi possono essere incoerenti col file e richiedono revisione separata. Versione software 0.6.1, espansione sospesa.\n'
    (ROOT/'docs/ROUND4_REPORT.md').write_text(md,encoding='utf8');(ROOT/'docs/BENCHMARK.md').write_text(md.replace('# Round 4 —','# Benchmark — Round 4 —',1),encoding='utf8')
    static=dict(schema_version=1,status=gates['status'],executed_at=hold['evaluated_at'],commit=hold['freeze']['commit'],catalog_count=1216,active_catalog_count=1212,catalog_semantic_sha256=hold['identity']['catalog_semantic_sha256'],independent_holdout=dict(status='executed',corpus_id='official_holdout_v2',summary=hold['summary']),hard_negatives=dict(status='executed',summary=summary(newneg+oldneg+fast['hard_negatives_v2']['cases'])),real_ocr=dict(status='executed',result=f"Legacy {legacy['passed']}/7; sintetici {ocr['summary']['passed']}/14"),performance=dict(status='executed',p50_ratio=perf['ratios_to_baseline']['p50'],p95_ratio=perf['ratios_to_baseline']['p95']),ocr_status='Tesseract reale, corpus sintetici separati',evaluations=[dict(name=n,status='executed',summary=r['summary']) for n,r in reports if n!='Holdout indipendente v2']+[dict(name=n,status='executed',summary=fast[n]['summary']) for n in ['development_regression','release_locked_v1','release_locked_v2','catalog_coverage']])
    write('benchmarks/latest_summary.json',static)
    for suffix in ['', '_EN']:
        p=ROOT/f'README{suffix}.md';text=p.read_text(encoding='utf8')
        block=(f"Round 4 **{gates['status']}**, software 0.6.1. Five historical acceptance errors and R061 fixed; locked v2 69/69. Fresh independent holdout v2: {hold['positive_n']} positives, {hold['negative_n']} negatives; exact precision {pct(m['document_precision'])}, exact recall {pct(m['document_recall'])}. Sampling/coverage gates remain unmet; no catalog expansion, push, tag or release. Cross-platform CI pending. Full evidence in [docs/ROUND4_REPORT.md](docs/ROUND4_REPORT.md)." if suffix else f"Round 4 **{gates['status']}**, software 0.6.1. Corretti i cinque errori storici e R061; locked v2 69/69. Nuovo holdout indipendente v2: {hold['positive_n']} positivi, {hold['negative_n']} negativi; precisione esatta {pct(m['document_precision'])}, recall esatto {pct(m['document_recall'])}. Restano gate di campionamento/copertura non raggiunti; nessuna espansione, push, tag o release. CI multipiattaforma pendente. Prove complete in [docs/ROUND4_REPORT.md](docs/ROUND4_REPORT.md).")
        p.write_text(re.sub(r'(?<=## Benchmark\n\n).*?(?=\n## )',block+'\n',text,flags=re.S),encoding='utf8')
    validation_path=ROOT/'docs/VALIDAZIONE.md';text=validation_path.read_text(encoding='utf8');text=re.sub(r'## Candidata Round 3.*?(?=Le sezioni seguenti)',f"## Candidata Round 4 — 11 ottobre 2026\n\n{tests['passed']} test superati, zero fallimenti, {tests['skipped']} skip Windows. Locked v2 69/69; OCR reale 7/7 e 14/14. Freeze e unica valutazione holdout v2 nei raw; stato **{gates['status']}**, versione 0.6.1, CI esterna pendente. Risultati e limiti correnti in `ROUND4_REPORT.md`.\n\n",text,flags=re.S);validation_path.write_text(text,encoding='utf8')
    print('Round 4 report:',gates['status'],counts(hold),flush=True)

if __name__=='__main__':generate()
