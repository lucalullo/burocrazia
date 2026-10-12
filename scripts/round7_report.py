"""Derive release status from frozen Round7 observations without retuning."""
import csv,hashlib,json,platform,re,subprocess,sys
from collections import Counter,defaultdict
from pathlib import Path
from datetime import UTC,datetime
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from benchmarks.round3_audit import read,write,catalog
from benchmarks.round7_recognition import checked,identity
from benchmarks.evaluate import summary
from src.recognize import catalog_revision

OUT='benchmarks/results/round7/'
def pct(m):return 'n.d.' if not m.get('denominator') else f"{100*m['value']:.2f}% ({m['numerator']}/{m['denominator']})"
def append(path,text):
    p=ROOT/path;s=p.read_text(encoding='utf8');marker='## Round 7'
    if marker in s:s=s[:s.index(marker)].rstrip()+'\n'
    p.write_bytes((s+'\n'+text.rstrip()+'\n').encode())

def main():
    frozen=checked();docs,families=catalog()
    data={n:read(OUT+n+'.json') for n in ['canonical','robustness_v3','scan_v3','filled_v3','retrieval_v3','unknown_v3','family_release','performance','fingerprint_coverage','decision_calibration','ci_local']}
    can,rob,scan,filled,retr,unknown,fam,perf,cov,cal,ci=[data[n] for n in data]
    for n in ['canonical','robustness_v3','scan_v3','filled_v3','unknown_v3']:
        assert summary(data[n]['cases'])['metrics']==data[n]['summary']['metrics'],n
    raw=(ROOT/'reports/round7-full-tests.log').read_bytes();log=raw.decode('utf8',errors='replace')
    m=re.search(r'(\d+) passed, (\d+) skipped in ([\d.]+)s',log)
    assert m and not re.search(r'\b[1-9]\d* failed\b',log),'Full suite incomplete or failed'
    tests=dict(passed=int(m[1]),failed=0,skipped=int(m[2]),seconds=float(m[3]),python=platform.python_version(),platform=platform.platform(),log_sha256=hashlib.sha256(raw).hexdigest())
    write(OUT+'tests.json',tests)
    finals={n:read(OUT+'final/'+n+'.json') for n in ['development_regression','release_locked_v1','release_locked_v2','hard_negatives_v1','hard_negatives_v2','family_release_v3','catalog_coverage']}
    compat=read(OUT+'development_compat_v2.json');ocr=read(OUT+'ocr_legacy_gate.json');ocr2=read(OUT+'ocr_synthetic_v2.json');five=read(OUT+'historical_five.json')
    gates=[]
    def gate(name,target,actual,passed,blocking=True):gates.append(dict(gate=name,target=target,actual=actual,passed=bool(passed),blocking=blocking))
    def value(r,k):return r['summary']['metrics'][k]['value'] or 0
    gate('coverage_file_backed','>=85%',cov['coverage_file_backed'],cov['coverage_file_backed']>=.85)
    gate('coverage_all','>=70%',cov['coverage_all'],cov['coverage_all']>=.70)
    for key in ['document_precision','document_recall']:gate('canonical_'+key,'100%',value(can,key),value(can,key)==1)
    gate('canonical_wrong','0',can['counts']['wrong'],can['counts']['wrong']==0)
    for n,r,target in [('robustness',rob,.9),('scan',scan,.85),('filled',filled,.9)]:
        gate(n+'_precision','>=99.5%',value(r,'document_precision'),value(r,'document_precision')>=.995)
        gate(n+'_exact_recall',f'>={target:.0%}',value(r,'document_recall'),value(r,'document_recall')>=target)
    gate('scan_useful_recall','>=95% (conservative section17 gate retained)',value(scan,'useful_coverage'),value(scan,'useful_coverage')>=.95)
    for k,target in [('1',.99),('25',1)]:
        r=retr['candidate_recall_at_k'][k];v=r['numerator']/r['denominator'] if r['denominator'] else 0;gate('retrieval_at_'+k,f'>={target:.0%}',v,v>=target)
    gate('unknown_historical_rejection','>=99%',value(unknown,'unknown_correct_rejection_rate'),value(unknown,'unknown_correct_rejection_rate')>=.99)
    gate('family_capability_validation','>=5 evaluable families',fam['families_evaluable'],fam['families_evaluable']>=5,False)
    r061=next(r for r in finals['release_locked_v2']['cases'] if r['id']=='R061');gate('R061','NO_MATCH',r061['observed']['match_type'],r061['correct'])
    gate('historical_five','5 safe',sum(r['safe'] for r in five['cases']),five['passed'])
    neg=sum(finals[n]['summary']['passed'] for n in ['hard_negatives_v1','hard_negatives_v2']);gate('historical_negatives','130/130',neg,neg==130)
    gate('historical_family_negatives','0 false accepts',finals['family_release_v3']['false_positives'],finals['family_release_v3']['false_positives']==0)
    gate('historical_development','35/35 unchanged labels',finals['development_regression']['summary']['passed'],finals['development_regression']['summary']['failed']==0)
    gate('historical_locked_v2','69/69',finals['release_locked_v2']['summary']['passed'],finals['release_locked_v2']['summary']['failed']==0)
    gate('historical_all_frozen_expectations','All historical expectations green, including contradictory v2 fixture',dict(locked_v1=finals['release_locked_v1']['summary']['passed'],compat_v2=compat['summary']['passed']),finals['release_locked_v1']['summary']['failed']==0 and compat['summary']['failed']==0)
    gate('real_ocr','7/7 +14/14',dict(legacy=ocr['passed'],synthetic=ocr2['summary']['passed']),ocr['full_gate_passed'] and ocr2['summary']['passed']==14)
    for k,limit in [('p50',150),('p95',250)]:gate('warm_'+k,f'<={limit}ms',perf['latency_ms'][k],perf['latency_ms'][k]<=limit)
    gate('index_memory','<=100MB',perf['fingerprints']['index_bytes'],perf['fingerprints']['index_bytes']<=100_000_000)
    gate('tests','0 failures',tests['passed'],tests['failed']==0)
    gate('catalog_unchanged','Original seed/schema610',ci['catalog']['sha256'],ci['catalog']['sha256']=='790b690123c82e1cb7bdfa67a10216284022987d50b0abbcc4a1a245785e3e99')
    ready=all(g['passed'] for g in gates if g['blocking']);status='READY LOCALLY' if ready else 'NOT READY';ident=identity()
    ident['catalog_sha256']=ci['catalog']['sha256']
    write('docs/release_gates.json',dict(schema_version=7,round=7,status=status,local_gates_passed=ready,external_ci='pending_external_gate',final_release_allowed=False,identity=ident,freeze_commit=frozen['commit'],gates=gates))
    latest=dict(schema_version=1,benchmark_model='known-family-unknown-v3',status=status,executed_at=ident['executed_at'],commit=frozen['commit'],catalog_semantic_sha256=catalog_revision(docs,families),catalog_count=1216,operational_count=1212,
        fingerprint_coverage=dict(status='executed',**cov),known_canonical=dict(status='executed',summary=can['summary']),known_robustness=dict(status='executed',summary=rob['summary']),filled_forms=dict(status='executed',summary=filled['summary'],interactive_cases=len(filled['cases']),templates=len(rob['plan']['filled_identities'])),scan_ocr=dict(status='executed',summary=scan['summary']),unknown_official=dict(status='executed',summary=unknown['summary'],scope=unknown['scope']),family_identity_holdout=dict(status='executed',summary=fam['summary'],families_evaluable=fam['families_evaluable'],capability_status=fam['capability_status']),hard_negatives=dict(status='executed',correct=neg,total=130),real_ocr=dict(status='executed',result=f"{ocr['passed']}/7 + {ocr2['summary']['passed']}/14"),performance=dict(status='executed',latency_ms=perf['latency_ms'],index_bytes=perf['fingerprints']['index_bytes'],startup_ms=perf['startup_ms']),ocr_status=f"Tesseract reale: {ocr['passed']}/7 storico, {ocr2['summary']['passed']}/14 sintetico",evaluations=[dict(name=n,summary=r['summary']) for n,r in [('Development historical35',finals['development_regression']),('Frozen compatibility37 conflict retained',compat),('Locked v1 historical',finals['release_locked_v1']),('Locked v2',finals['release_locked_v2']),('Negatives v1',finals['hard_negatives_v1']),('Negatives v2',finals['hard_negatives_v2']),('Family synthetic',finals['family_release_v3']),('Metadata canonical coverage',finals['catalog_coverage'])]])
    write('benchmarks/latest_summary.json',latest)
    # Before/after is development only, never a second fresh evaluation.
    verified=read(OUT+'calibration_runtime_verified.json')['cases'];old=read('benchmarks/results/round6/robustness_v2.json')['cases'];lookup={(r['expected']['document_id'],r['representation']):r for r in verified}
    after=[]
    for r in old:
        a=lookup[(r['expected']['document_id'],r['representation'])];after.append(dict(case_id=r['id'],document_id=r['expected']['document_id'],transform=r['representation'],before=r['observed']['match_type'],after=a['observed']['match_type'],correct_before=r['correct'],correct_after=a['correct'],reason_after=a['reason']))
    write(OUT+'decision_audit_after.json',dict(cases=after,correct_before=sum(r['correct_before'] for r in after),correct_after=sum(r['correct_after'] for r in after),scope='Round6 development replay; active-resource changes and safety quarantine included. Not independent.'))
    append('docs/ROUND7_DECISION_AUDIT.md',f"## Round 7 — esito sviluppo\n\nReplay effettivo: {sum(r['correct_after'] for r in after)}/{len(after)} contro {sum(r['correct_before'] for r in after)}/{len(after)}. Decision policy v3, retrieval v2 con identica formula; il bundle attivo cambia per recuperi/quarantene. Campione R6 riclassificato development. Dettaglio per caso in `decision_audit_after.json`.\n\nA: SHA identico e vincoli; B: testo con visual o caratteri/anchor; C: contenuto eccezionale e anchor d'identità; D: family già supportata o NO. Nessuna accettazione visual-only, soglie globali prossime a zero o margine nullo. I conflitti espliciti restano veto. SUAP destinatario e sottodipartimento MIMIT sono distinti dall'emittente. La revisione mancante può essere sostenuta da codice, titolo completo nella lingua iniziale e ente, soltanto per un'unica identità/revisione.\n\nEX02/EX03 e EX02MISSINGREV/EX03MISSINGREV hanno testi identici ma expected opposti: gli hash e le etichette di entrambe le fixture restano invariati. Default CLI usa i 35 originali; la fixture37 resta visibile con i suoi fallimenti. Non esiste una decisione deterministica che soddisfi entrambe le etichette.\n")
    rows=[]
    for n,r in [('Canonical',can),('Robustness v3',rob),('Scan v3',scan),('Filled v3',filled),('Unknown storico',unknown)]:
        c=r['counts'];rows.append(f"| {n} | {len(r['cases'])} | {c['exact']} | {c['family']} | {c['reject']} | {c['wrong']} | {pct(r['summary']['metrics']['document_precision'])} | {pct(r['summary']['metrics']['document_recall'])} |")
    gate_table='\n'.join(f"| {g['gate']} | {g['target']} | {g['actual']} | {'PASS' if g['passed'] else 'FAIL'} | {'sì' if g['blocking'] else 'no'} |" for g in gates)
    groups=defaultdict(list)
    for r in rob['cases']:groups[r['representation']].append(r)
    transformation='\n'.join(f"| {n} | {len(rr)} | {sum(r['correct'] for r in rr)} | {pct(summary(rr)['metrics']['document_recall'])} |" for n,rr in sorted(groups.items()))
    sources='\n'.join(f"| {n} | {v['operational_docs_total']} | {v['file_backed_operational_docs']} | {v['fingerprinted_all_operational_docs']} |" for n,v in cov['by_source'].items())
    report=f"""# Round 7 — {status}

## Stato e provenienza

Software pubblico 0.6.1, candidata 0.7.0; schema 610. Nessun push, tag o release.
Ingresso d3dd53bbc2e97047d7eadbe379c31bb920929c7b; codice sorgente sviluppo {cal['commit']}; freeze effettivo {frozen['commit']}.
Runtime SHA `{frozen['runtime_sha256']}`; codice/runner SHA `{frozen['code_sha256']}`; bundle SHA `{frozen['fingerprint_sha256']}`.
Il commit nell'artefatto di calibrazione identifica HEAD durante lo sviluppo; profilo e runtime sono identificati dai rispettivi byte/hash, inclusi poi nel freeze.
Il commit di distribuzione include anche i report; ZIP/hash in `dist/package-verification.json`, prodotti dopo il commit per evitare riferimenti circolari.

## Baseline e decisione

Baseline R6: canonical987/987, robustness150/192, scan128/168, retrieval100%, unknown137/137; full suite655+3skip.
EX02/EX03 erano i due rifiuti che lasciavano33/35; ora {finals['development_regression']['summary']['passed']}/35.
Tutti i50 raw JSON R6 sono conservati e verificati per hash, oltre ai corpus v1/v2 immutati.
Audit dei42 NO rank1 in `docs/ROUND7_DECISION_AUDIT.md` e CSV R6 dedicato:28 ruoli ente,13 OCR score,1 canali.
R6 ora development: replay {sum(r['correct_after'] for r in after)}/192; nessuna pretesa di indipendenza dopo il tuning.
Calibrazione320 rappresentazioni note e {cal['results']['negative_cases']} negativi storici; obiettivo zero false accept e massimo richiamo.
Profilo congelato `{frozen['profile_sha256']}`: `{json.dumps(cal['thresholds'],sort_keys=True)}`.
Tier A/B/C/D e diagnostica sono request-local; nessun testo caricato, sketch o risultato personale entra nelle cache pubbliche.

## Recupero e copertura

Zero nuove identità/fonti. {read(OUT+'recovery_attempts.json')['network_requests']} richieste di rete nel solo strumento maintenance opt-in, con robots, allowlist e limiti;403/429 non aggirati.
14 identità hanno ulteriori byte ufficiali; solo {cov['added_active_identities']} aggiungono un'identità attiva.
Quarantena delle identità prima attive {cov['lost_active_identities']}: risorse con SHA condiviso fra identità; nessuna scelta arbitraria.
{cov['fingerprinted_all_operational_docs']}/1212 attive, totale {cov['coverage_all']:.2%}; {cov['fingerprinted_file_backed_docs']}/{cov['file_backed_operational_docs']} con file, {cov['coverage_file_backed']:.2%}; metadata-only {cov['metadata_only_docs']}.
Il denominatore1158 resta invariato. Il gate85% resta FAIL. Un eventuale futuro gate sulle sole risorse recuperabili richiede una decisione esplicita e non è applicato.
DOC/DOCX senza renderer, XLSX/ZIP/PPTX reali, blocchi ufficiali e conflitti canonici sono limiti distinti; nessuna conversione non sicura.
Il riconoscimento MIME ZIP ora distingue Word/Excel/PowerPoint;36 etichette MIME precedenti erano errate. Non si eseguono macro/formule.
Resolver con fixture per le12 fonti, meta-refresh ufficiali e attachment senza estensione; final URL validato. Tutti i264 missing iniziali più9 nuove quarantene sono nel CSV di recupero.

| Fonte | Operativi | Con file | Firme attive |
|---|---:|---:|---:|
{sources}

## Valutazione nuova, una sola esecuzione

Piano generato dopo freeze, seed2026101207; {len(rob['plan']['evaluation_identities'])} identità nuove rispetto alla calibrazione, {len(rob['cases'])} rappresentazioni, {len(scan['cases'])} scan-like, {len(filled['cases'])} compilate su {len(rob['plan']['filled_identities'])} template.
Nessun overlap ID/SHA/URL/titolo-codice-versione né quasi duplicati secondo la regola pubblicata; `evaluation_v3_leakage.json` zero leakage proibito.
Firme canoniche note presenti per le identità evaluation: si misura generalizzazione alle rappresentazioni, non a identità sconosciute.
Nessuna modifica del runtime, soglie, template selection o etichette dopo risultati. Piano/started/freeze e raw conservati.
Scansioni generate dalla prima pagina, DPI150/200, JPEG90/75/60, contrasto, blur, crop, resize e rotazioni; non scansioni reali di utenti.
Compilazione interattiva con dati fittizi: /AcroForm/Fields, /V, widget e /AP/N verificati, checkbox variate; ambiguità/fallimenti inclusi nel denominatore.
L'associazione semantica dei campi con etichette vicine è euristica (es. luogo di nascita può ricevere data): prova di perturbazione del riconoscimento, senza validità amministrativa.

| Misura | Casi | Exact | Family | NO | Wrong | Precisione exact | Recall exact |
|---|---:|---:|---:|---:|---:|---|---|
{chr(10).join(rows)}

| Trasformazione | Casi | Corretti | Recall exact |
|---|---:|---:|---|
{transformation}

Retrieval @1/5/10/25: `{json.dumps(retr['candidate_recall_at_k'],sort_keys=True)}`.
Wrong/NO, enti/versioni, tempi estrazione/visual/matching/end-to-end sono nelle osservazioni; extraction/generation failed restano nel denominatore.

## Family, unknown e regressioni

16 famiglie, {fam['families_evaluable']} valutabili con almeno2 identità sviluppo e3 holdout; `not_sufficiently_validated`, non bloccante per RC documenti noti. Dettaglio per famiglia nel CSV e JSON.
Unknown:137 file ufficiali storici distinti, usati anche nella calibrazione di sicurezza;0 nuovi unknown adjudicati indipendentemente. Tasso {pct(unknown['summary']['metrics']['unknown_correct_rejection_rate'])}, nessuna pretesa di test unknown nuovo.
Storici v1/v2 preservati:35 originali {finals['development_regression']['summary']['passed']}/35; locked v1 {finals['release_locked_v1']['summary']['passed']}/69; locked v2 {finals['release_locked_v2']['summary']['passed']}/69;130 negativi {neg}/130; family sintetico {finals['family_release_v3']['summary']['passed']}/161.
R061 {r061['observed']['match_type']}; cinque casi critici {sum(r['safe'] for r in five['cases'])}/5 safe.
Fixture37 immutata {compat['summary']['passed']}/37: expected opposti per due testi identici ai35 originali. Il gate storico stretto resta FAIL, senza cambiare etichette per farlo passare.
OCR locale reale: {ocr['passed']}/7 storico + {ocr2['summary']['passed']}/14 sintetico. Non sono validazione editoriale o collaudo multipiattaforma.

## Performance e memoria

Baseline p50/p95 112.9562/799.1129ms; configurazione finale {perf['latency_ms']['p50']}/{perf['latency_ms']['p95']}ms, p99 {perf['latency_ms']['p99']}ms,306 osservazioni su35 sintetici e gli stessi16 file ufficiali.
Processo nuovo, warmup51; esclusi estrazione, OCR e visual, separati nei raw v3. Nessuna cache di input.
Profilo baseline e sviluppo per fase/funzione conservato. Denominatori IDF precomputati su solo catalogo; fuzzy title saltato soltanto quando il coverage cap garantisce contributo zero; conflitti per ente riusati nella singola richiesta. Full scan resta disponibile.
Equivalenza testata su score/ranking e risultati completi document/entity/version/family/NO; nessuna potatura rischiosa dei candidati metadata.
Bundle {perf['fingerprints']['disk_bytes']}byte; indice ricorsivo {perf['fingerprints']['index_bytes']}byte; load catalogo {perf['catalog_load_ms']:.3f}ms, build indice {perf['index_build_ms']:.3f}ms.
RSS dopo warm {perf['rss']['after_warm_bytes']}byte; crescita successiva {perf['rss']['growth_after_warm_bytes']}byte, separata dalla misura indice.

## Test, piattaforme e gate

Full suite: {tests['passed']} passed,0 failed,{tests['skipped']} skip Windows,{tests['seconds']}s. Log SHA `{tests['log_sha256']}`.
Bootstrap su database temporaneo separato, integrity/FK, snapshot/migrazioni storiche e lock verificati; seed pubblico invariato, database personale non modificato.
CI Python3.12 Linux/Windows/macOS configurata; solo Windows eseguito localmente. Stato esterno pending_external_gate fino al push dell'utente.

| Gate | Target | Risultato | Esito | Bloccante |
|---|---|---|---|---|
{gate_table}

## Distribuzione e limiti residui

Verdetto locale **{status}**. Software/versione pubblica invariati; nessuna pubblicazione.
Archivio `dist/BurOCRazia-v0.7.0-{'RC1' if ready else 'candidate-NOT-READY'}-round7.zip`; verifica hash/byte/lock/hygiene in dist.
Nessun file ufficiale, PDF compilato, testo OCR, cache, binario Tesseract, credenziale o database personale redistribuito.
Un Round8 deve usare nuove identità evaluation dopo un nuovo freeze, senza riutilizzare v3 per rivendicare indipendenza; risolvere copertura, gate falliti e contraddizioni delle etichette con una nuova versione motivata, senza alterare lo storico.
"""
    (ROOT/'docs/ROUND7_REPORT.md').write_bytes(report.encode())
    brief=f"""## Round 7 — {status}

Decision policy v3, retrieval v2 e nuova evaluation dopo freeze: {len(rob['cases'])} rappresentazioni/{len(rob['plan']['evaluation_identities'])} identità, {len(scan['cases'])} scan-like, {len(filled['cases'])} AcroForm sintetici. Coverage {cov['coverage_all']:.2%} totale e {cov['coverage_file_backed']:.2%} con file; canonical {can['counts']['exact']}/{len(can['cases'])}; robustness recall {value(rob,'document_recall'):.2%}; scan recall {value(scan,'document_recall'):.2%}; filled recall {value(filled,'document_recall'):.2%}; unknown storico {value(unknown,'unknown_correct_rejection_rate'):.2%}; family {fam['families_evaluable']}/16 valutabili (non sufficientemente validata). p95 {perf['latency_ms']['p95']:.2f}ms; indice {perf['fingerprints']['index_bytes']}byte.
R6 ora development; v3 una sola esecuzione, senza retuning. {tests['passed']} test passati, {tests['skipped']} skip. CI esterna pending_external_gate. Software0.6.1/schema610/catalogo1216 preservati. Report e limiti: [ROUND7_REPORT.md](docs/ROUND7_REPORT.md).
"""
    append('README.md',brief);append('README_EN.md',brief)
    append('docs/BENCHMARK.md',brief.replace('(docs/ROUND7_REPORT.md)','(ROUND7_REPORT.md)')+'\n\nCoverage, canonical, robustness, filled, scan/OCR, family, unknown e regressioni sono metriche separate. V1/v2 raw e label restano visibili; R6 evaluation è development, v3 è il solo nuovo test di rappresentazioni. Unknown è storico/calibrato, non indipendente. I gate non vengono ridefiniti quando falliscono.\n')
    append('docs/COVERAGE.md',brief.replace('(docs/ROUND7_REPORT.md)','(ROUND7_REPORT.md)')+'\n\nDenominatore con file invariato1158; tutte le acquisizioni fallite restano.14 identità con byte aggiuntivi,2 attive recuperate,9 quarantene per SHA condiviso. Unsupported reale, conflitto canonico e fonti bloccate sono distinguibili negli audit.\n')
    append('DATA_NOTICE.md','## Round 7\n\nOnly hashes, public catalog metadata, real acquisition receipts and numeric/evidence benchmark outcomes are redistributed. Official files, OCR text and filled synthetic PDFs remain ignored. No identity, source, editorial verification or historical event is invented. No private upload is cached. Runtime stays local/offline/deterministic.\n')
    locked={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/OUT).rglob('*.json')) if not p.name.endswith('checkpoint.json') and p.name!='evaluation_locks.json'}
    write(OUT+'evaluation_locks.json',dict(runtime_sha256=frozen['runtime_sha256'],code_sha256=frozen['code_sha256'],sha256=locked,scope='Hashes attest immutable evidence bytes; not retrospective proof of independent selection. Prospective selection is freeze+started+plan chronology.'))
    print(status,'failed gates',[g['gate'] for g in gates if g['blocking'] and not g['passed']])

if __name__=='__main__':main()
