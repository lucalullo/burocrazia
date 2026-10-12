"""Derive release status from frozen Round7 observations without retuning."""
import csv,hashlib,json,platform,re,subprocess,sys
from collections import Counter,defaultdict
from pathlib import Path
from datetime import UTC,datetime
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from benchmarks.round3_audit import read,write,catalog
from benchmarks.round7_recognition import checked,identity
from benchmarks.evaluate import summary,quantile
from src.recognize import catalog_revision

OUT='benchmarks/results/round7/'
def pct(m):return 'n.d.' if not m.get('denominator') else f"{100*m['value']:.2f}% ({m['numerator']}/{m['denominator']})"
def append(path,text):
    p=ROOT/path;s=p.read_text(encoding='utf8');marker='## Round 7'
    if marker in s:s=s[:s.index(marker)].rstrip()+'\n'
    p.write_bytes((s+'\n'+text.rstrip()+'\n').encode())

def current_banner(path,title,body):
    p=ROOT/path;s=p.read_text(encoding='utf8')
    start='<!-- round7-current-start -->';end='<!-- round7-current-end -->'
    if start in s:
        a=s.index(start);b=s.index(end,a)+len(end)
        s=s[:a]+s[b:].lstrip('\n')
    _,rest=s.split('\n',1)
    p.write_bytes((title+'\n\n'+start+'\n'+body.rstrip()+'\n'+end+'\n\n'+rest.lstrip('\n')).encode())

def benchmark_paragraph(path,text):
    p=ROOT/path;s=p.read_text(encoding='utf8')
    s,n=re.subn(r'(?<=## Benchmark\n\n)[^\n]+',lambda _:text,s,count=1)
    assert n==1,path
    p.write_bytes(s.encode())

def main():
    frozen=checked();docs,families=catalog()
    data={n:read(OUT+n+'.json') for n in ['canonical','robustness_v3','scan_v3','filled_v3','retrieval_v3','unknown_v3','family_release','performance','fingerprint_coverage','decision_calibration','ci_local']}
    can,rob,scan,filled,retr,unknown,fam,perf,cov,cal,ci=[data[n] for n in data]
    available=[r for r in rob['cases'] if not r.get('generation_failed')]
    filled_generated=sum(not r.get('generation_failed') for r in filled['cases']);generation_failed=len(rob['cases'])-len(available)
    for n in ['canonical','robustness_v3','scan_v3','filled_v3','unknown_v3']:
        assert summary(data[n]['cases'])['metrics']==data[n]['summary']['metrics'],n
    raw=(ROOT/'reports/round7-full-tests.log').read_bytes();log=raw.decode('utf8',errors='replace')
    m=re.search(r'(\d+) passed, (\d+) skipped in ([\d.]+)s',log)
    assert m and not re.search(r'\b[1-9]\d* failed\b',log),'Full suite incomplete or failed'
    tests=dict(passed=int(m[1]),failed=0,skipped=int(m[2]),seconds=float(m[3]),python=platform.python_version(),platform=platform.platform(),log_sha256=hashlib.sha256(raw).hexdigest())
    initial=(ROOT/'reports/round7-full-initial-failed.log').read_bytes()
    tests['initial_attempt']=dict(passed=687,failed=3,skipped=3,seconds=151.36,log_sha256=hashlib.sha256(initial).hexdigest(),resolution='Only full-scan reference diagnostics differed. Runtime production outcomes unchanged; append-only reference fix proof and complete successful rerun retained.')
    post=(ROOT/'reports/round7-postreport-tests.log').read_bytes()
    post_log=post.decode('utf8',errors='replace')
    post_match=re.search(r'(\d+) passed in ([\d.]+)s',post_log)
    assert post_match and not re.search(r'\b[1-9]\d* failed\b',post_log)
    tests['post_report_checks']=dict(passed=int(post_match[1]),failed=0,seconds=float(post_match[2]),log_sha256=hashlib.sha256(post).hexdigest(),scope='Repeated targeted UI/benchmark/fingerprint/round7 checks after static result update; not additional distinct tests.')
    write(OUT+'tests.json',tests)
    finals={n:read(OUT+'final/'+n+'.json') for n in ['development_regression','release_locked_v1','release_locked_v2','hard_negatives_v1','hard_negatives_v2','family_release_v3','catalog_coverage']}
    compat=read(OUT+'development_compat_v2.json');ocr=read(OUT+'ocr_legacy_gate.json');ocr2=read(OUT+'ocr_synthetic_v2.json');five=read(OUT+'historical_five.json')
    gates=[]
    def gate(name,target,actual,passed,blocking=True):gates.append(dict(gate=name,target=target,actual=actual,passed=bool(passed),blocking=blocking))
    def value(r,k):return r['summary']['metrics'][k]['value'] or 0
    gate('coverage_file_backed','>=85%',cov['coverage_file_backed'],cov['coverage_file_backed']>=.85)
    gate('coverage_all','>=70%',cov['coverage_all'],cov['coverage_all']>=.70)
    gate('evaluation_minimum_generated_representations','>=300',len(available),len(available)>=300)
    gate('scan_minimum_cases','>=200',len(scan['cases']),len(scan['cases'])>=200)
    gate('filled_minimum_actual_generated','>=50',filled_generated,filled_generated>=50)
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
    latest['filled_forms'].update(interactive_cases=filled_generated,attempted_cases=len(filled['cases']),generation_failed=len(filled['cases'])-filled_generated)
    latest['evaluations']=[dict(name=f'AcroForm: {filled_generated} generati, {len(filled["cases"])-filled_generated} falliti su {len(filled["cases"])} tentativi',summary=filled['summary']),dict(name=f'Robustness: {len(available)} rappresentazioni disponibili e {generation_failed} generazioni fallite',summary=rob['summary']),*latest['evaluations']]
    write('benchmarks/latest_summary.json',latest)
    # Before/after is development only, never a second fresh evaluation.
    verified=read(OUT+'calibration_runtime_verified.json')['cases'];old=read('benchmarks/results/round6/robustness_v2.json')['cases'];lookup={(r['expected']['document_id'],r['representation']):r for r in verified}
    after=[]
    for r in old:
        a=lookup[(r['expected']['document_id'],r['representation'])];after.append(dict(case_id=r['id'],document_id=r['expected']['document_id'],transform=r['representation'],before=r['observed']['match_type'],after=a['observed']['match_type'],correct_before=r['correct'],correct_after=a['correct'],reason_after=a['reason']))
    write(OUT+'decision_audit_after.json',dict(cases=after,correct_before=sum(r['correct_before'] for r in after),correct_after=sum(r['correct_after'] for r in after),scope='Round6 development replay; active-resource changes and safety quarantine included. Not independent.'))
    rejection_counts=dict(Counter('generation_failed' if r.get('generation_failed') else 'missing_model_revision' if 'missing_model_revision' in r['conflicts'] else r['reason'].split(' [')[0] for r in rob['cases'] if r['observed']['match_type']=='NO_MATCH'))
    write(OUT+'evaluation_diagnostics.json',dict(rejection_counts=rejection_counts,planned_cases=len(rob['cases']),actual_generated=len(available),filled_actual_generated=filled_generated,generation_failed=generation_failed,retrieval_on_available={str(k):dict(numerator=sum(r.get('candidate_recall_at_k',{}).get(str(k),False) for r in available),denominator=len(available)) for k in [1,5,10,25]},scope='Read-only post-evaluation aggregation. Frozen planned-denominator gates unchanged; available-only retrieval is diagnostic, never substituted for the declared gate. No runtime/generator correction or retry.'))
    append('docs/ROUND7_DECISION_AUDIT.md',f"## Round 7 — esito sviluppo\n\nReplay effettivo: {sum(r['correct_after'] for r in after)}/{len(after)} contro {sum(r['correct_before'] for r in after)}/{len(after)}. Decision policy v3, retrieval v2 con identica formula; il bundle attivo cambia per recuperi/quarantene. Campione R6 riclassificato development. Dettaglio per caso in `decision_audit_after.json`.\n\nA: SHA identico e vincoli; B: testo con visual o caratteri/anchor; C: contenuto eccezionale e anchor d'identità; D: family già supportata o NO. Nessuna accettazione visual-only, soglie globali prossime a zero o margine nullo. I conflitti espliciti restano veto. SUAP destinatario e sottodipartimento MIMIT sono distinti dall'emittente. La revisione mancante può essere sostenuta da codice, titolo completo nella lingua iniziale e ente, soltanto per un'unica identità/revisione.\n\nEX02/EX03 e EX02MISSINGREV/EX03MISSINGREV hanno testi identici ma expected opposti: gli hash e le etichette di entrambe le fixture restano invariati. Default CLI usa i 35 originali; la fixture37 resta visibile con i suoi fallimenti. Non esiste una decisione deterministica che soddisfi entrambe le etichette.\n")
    rows=[]
    for n,r in [('Canonical',can),('Robustness v3',rob),('Scan v3',scan),('Filled v3',filled),('Unknown storico',unknown)]:
        c=r['counts'];rows.append(f"| {n} | {len(r['cases'])} | {c['exact']} | {c['family']} | {c['reject']} | {c['wrong']} | {pct(r['summary']['metrics']['document_precision'])} | {pct(r['summary']['metrics']['document_recall'])} |")
    gate_table='\n'.join(f"| {g['gate']} | {g['target']} | {g['actual']} | {'PASS' if g['passed'] else 'FAIL'} | {'sì' if g['blocking'] else 'no'} |" for g in gates)
    groups=defaultdict(list)
    for r in rob['cases']:groups[r['representation']].append(r)
    timing={}
    for name,rr in [('digital',[r for r in rob['cases'] if r['representation']=='digital_exact']),('scan_like',scan['cases']),('filled',filled['cases'])]:
        timing[name]={key:dict(n=len(values),p50=quantile(values,.5),p95=quantile(values,.95),p99=quantile(values,.99)) for key in ['extraction_ms','visual_ms','matching_ms','end_to_end_ms'] for values in [[r[key] for r in rr if key in r]]}
    write(OUT+'phase_timings.json',dict(scope='One-shot representation run, including actual OCR. Parallel workers; diagnostic end-to-end times, separate from isolated warm performance gate.',groups=timing))
    transformation='\n'.join(f"| {n} | {len(rr)} | {sum(r['correct'] for r in rr)} | {pct(summary(rr)['metrics']['document_recall'])} |" for n,rr in sorted(groups.items()))
    sources='\n'.join(f"| {n} | {v['operational_docs_total']} | {v['file_backed_operational_docs']} | {v['fingerprinted_all_operational_docs']} |" for n,v in cov['by_source'].items())
    report=f"""# Round 7 — {status}

## Stato e provenienza

Software pubblico 0.6.1, candidata 0.7.0; schema 610. Nessun push, tag o release.
Ingresso d3dd53bbc2e97047d7eadbe379c31bb920929c7b; codice sorgente sviluppo {cal['commit']}; freeze effettivo {frozen['commit']}.
Runtime SHA `{frozen['runtime_sha256']}`; codice/runner SHA `{frozen['code_sha256']}`; bundle SHA `{frozen['fingerprint_sha256']}`.
La calibrazione originale è immutata. `decision_calibration_reference_fix.json` attesta l'unica correzione successiva, limitata alla diagnostica full scan: ricostruisce l'hash originale dai byte Git e verifica tutti gli altri byte runtime/profilo. Nessun esito, soglia o vincolo produttivo è cambiato. Il freeze comprende anche l'hash di questa prova.
Il commit nell'artefatto di calibrazione identifica HEAD durante lo sviluppo; profilo e runtime sono identificati dai rispettivi byte/hash, inclusi poi nel freeze.
Il commit di distribuzione include anche i report; ZIP/hash in `dist/package-verification.json`, prodotti dopo il commit per evitare riferimenti circolari.

## Baseline e decisione

Baseline R6: canonical987/987, robustness150/192, scan128/168, retrieval100%, unknown137/137; full suite655+3skip.
EX02/EX03 erano i due rifiuti che lasciavano33/35; ora {finals['development_regression']['summary']['passed']}/35.
Tutti i50 raw JSON R6 sono conservati e verificati per hash, oltre ai corpus v1/v2 immutati.
Audit dei42 NO rank1 in `docs/ROUND7_DECISION_AUDIT.md` e CSV R6 dedicato:28 ruoli ente,13 OCR score,1 canali.
R6 ora development: replay {sum(r['correct_after'] for r in after)}/192; nessuna pretesa di indipendenza dopo il tuning.
Calibrazione320 rappresentazioni note e {cal['results']['negative_cases']} controlli negativi storici:130 hard negatives e137 unknown nel motore completo,81 controlli nel solo fallback family secondo il contratto originale del corpus. Obiettivo zero false accept nell'ambito corretto e massimo richiamo exact.
Il primo tentativo development era fallito perché trattava gli81 controlli family come negativi del motore completo e conteggiava FAMILY_MATCH come identità sbagliata. FR10-N4/FR12-N4 identificano documenti143/167 nel motore completo, ma restano NO nel fallback family. L'audit iniziale resta conservato; nessuna soglia del runtime è stata modificata per eliminare questi due esiti. La calibrazione finale verifica ogni configurazione con il runtime effettivo, riusando solo l'estrazione storica degli unknown development; la misura finale unknown riestrae i file.
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

Piano generato dopo freeze, seed2026101207; {len(rob['plan']['evaluation_identities'])} identità nuove rispetto alla calibrazione, {len(rob['cases'])} tentativi pianificati, {len(available)} rappresentazioni effettivamente generate, {len(scan['cases'])} scan-like. Compilazione: {filled_generated}/{len(filled['cases'])} PDF realmente generati su {len(rob['plan']['filled_identities'])} template; {generation_failed} fallimenti mantenuti nel denominatore. Il minimo50 compilati non è raggiunto: FAIL esplicito, senza correggere il generatore dopo l'evaluation.
Nessun overlap ID/SHA/URL/titolo-codice-versione né quasi duplicati secondo la regola pubblicata; `evaluation_v3_leakage.json` zero leakage proibito.
Firme canoniche note presenti per le identità evaluation: si misura generalizzazione alle rappresentazioni, non a identità sconosciute.
Nessuna modifica del runtime, soglie, template selection o etichette dopo risultati. Piano/started/freeze e raw conservati.
La prima preparazione del piano era terminata prima di plan/start/casi per backend AES mancante; `evaluation_environment_preflight.json` conserva la prova. Dipendenze locali già disponibili cryptography50.0.2/cffi2.1.1 aggiunte solo al benchmark ignorato; codice/seed invariati. Requisiti riproducibili in `benchmarks/requirements-round7.txt`.
Scansioni generate dalla prima pagina, DPI150/200, JPEG90/75/60, contrasto, blur, crop, resize e rotazioni; non scansioni reali di utenti.
Compilazione interattiva con dati fittizi: /AcroForm/Fields, /V, widget e /AP/N verificati, checkbox variate; ambiguità/fallimenti inclusi nel denominatore.
L'associazione semantica dei campi con etichette vicine è euristica (es. luogo di nascita può ricevere data): prova di perturbazione del riconoscimento, senza validità amministrativa.
La QA visiva di tre PDF generati, ricostruiti con SHA identico senza nuovo riconoscimento, mostra anche campi assegnati in modo errato e testo tagliato nei segmenti data. /V, widget e /AP/N coerenti non equivalgono a compilazione semanticamente o graficamente valida. Nessun PDF viene consegnato o incluso nello ZIP; limite da correggere prima di un nuovo freeze Round8.

| Misura | Casi | Exact | Family | NO | Wrong | Precisione exact | Recall exact |
|---|---:|---:|---:|---:|---:|---|---|
{chr(10).join(rows)}

| Trasformazione | Casi | Corretti | Recall exact |
|---|---:|---:|---|
{transformation}

Retrieval @1/5/10/25: `{json.dumps(retr['candidate_recall_at_k'],sort_keys=True)}`.
Sulle sole331 rappresentazioni disponibili retrieval100% (331/331 anche@1); gli stessi risultati raw restano immutati. Il gate conservativo pianificato resta331/372 per i41 input non generati: non viene sostituito con il denominatore favorevole. I280 scan-like hanno retrieval@1/25 100%, ma soltanto134 exact; il problema decisionale resta distinto dal fallimento del generatore filled.
Cause NO aggregate dai raw: `{json.dumps(rejection_counts,ensure_ascii=False,sort_keys=True)}`. Nessun tuning dopo questa lettura.
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

I tempi end-to-end scan-like, comprensivi di OCR reale, sono p50 {timing['scan_like']['end_to_end_ms']['p50']:.2f} ms e p95 {timing['scan_like']['end_to_end_ms']['p95']:.2f} ms su 280 casi. Provengono dai worker paralleli della singola evaluation e sono diagnostici; il gate di riconoscimento usa la misura isolata precedente. Dettaglio di estrazione, visual e matching in `phase_timings.json`.

## Test, piattaforme e gate

Full suite: {tests['passed']} passed,0 failed,{tests['skipped']} skip Windows,{tests['seconds']}s. Log SHA `{tests['log_sha256']}`.
Controllo mirato dopo aggiornamento dei riepiloghi: {tests['post_report_checks']['passed']} test passati, 0 falliti. Sono ripetizioni della suite, non test aggiuntivi da sommare ai 690.
Il primo tentativo completo aveva687 passed,3 failed,3 skip (151.36s): soltanto stringhe diagnostiche diverse fra indice e full scan. Log/hash conservati e correzione prima della nuova evaluation; nessun expected o corpus cambiato.
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
    # Readability changes apply only to prose; hashes and evidence bytes stay intact.
    for old,new in {
        'canonical987':'canonical 987','robustness150':'robustness 150','scan128':'scan 128','retrieval100%':'retrieval 100%','unknown137':'unknown 137','suite655':'suite 655',
        'lasciavano33':'lasciavano 33','i50 raw':'i 50 raw','dei42':'dei 42','dedicato:28':'dedicato: 28','ente,13':'ente, 13','score,1':'score, 1',
        'Calibrazione320':'Calibrazione 320','storici:130':'storici: 130','hard negatives e137':'hard negatives e 137','unknown nel motore completo,81':'unknown nel motore completo, 81',
        'gli81':'gli 81','documenti143/167':'documenti 143/167','limiti;403/429':'limiti; 403/429','denominatore1158':'denominatore 1158','gate85%':'gate 85%',
        'ZIP;36':'ZIP; 36','PowerPoint;36':'PowerPoint; 36','le12':'le 12','i264':'i 264','più9':'più 9','seed2026101207':'seed 2026101207','minimo50':'minimo 50',
        'cryptography50.0.2/cffi2.1.1':'cryptography 50.0.2 / cffi 2.1.1','DPI150/200':'DPI 150/200','JPEG90/75/60':'JPEG 90/75/60',
        'sole331':'sole 331','resta331':'resta 331','i41':'i 41','I280':'I 280','soltanto134':'soltanto 134','almeno2':'almeno 2','e3 holdout':'e 3 holdout',
        'Unknown:137':'Unknown: 137','sicurezza;0':'sicurezza; 0','preservati:35':'preservati: 35',';130 negativi':'; 130 negativi','Fixture37':'Fixture 37','ai35':'ai 35',
        '799.1129ms':'799.1129 ms','444.6542ms':'444.6542 ms','525.8341ms':'525.8341 ms',',306':', 306','su35':'su 35','stessi16':'stessi 16','warmup51':'warmup 51',
        '27493120byte':'27493120 byte','39832045byte':'39832045 byte','11.883ms':'11.883 ms','1517.722ms':'1517.722 ms','267243520byte':'267243520 byte','12288byte':'12288 byte',
        'passed,0':'passed, 0','failed,3':'failed, 3','Windows,337':'Windows, 337','337.74s':'337.74 s','aveva687':'aveva 687','passed,3':'passed, 3','failed,3':'failed, 3','151.36s':'151.36 s',
        'Python3.12':'Python 3.12','Round8':'Round 8',
    }.items():report=report.replace(old,new)
    (ROOT/'docs/ROUND7_REPORT.md').write_bytes(report.encode())
    brief=f"""## Round 7 — {status}

Decision policy v3, retrieval v2 e nuova evaluation dopo freeze: {len(rob['cases'])} tentativi, {len(available)} rappresentazioni generate su {len(rob['plan']['evaluation_identities'])} identità, {len(scan['cases'])} scan-like, {filled_generated}/{len(filled['cases'])} AcroForm generati ({generation_failed} fallimenti). Copertura {cov['coverage_all']:.2%} totale e {cov['coverage_file_backed']:.2%} con file; canonical {can['counts']['exact']}/{len(can['cases'])}; richiamo robustness {value(rob,'document_recall'):.2%}, scansioni {value(scan,'document_recall'):.2%}, compilati {value(filled,'document_recall'):.2%} sul piano completo. Rifiuto unknown storico {value(unknown,'unknown_correct_rejection_rate'):.2%}; famiglie {fam['families_evaluable']}/16 valutabili, capacità non sufficientemente validata. p95 {perf['latency_ms']['p95']:.2f} ms; indice {perf['fingerprints']['index_bytes']} byte. Precisione exact 100% sui match emessi. La QA dei compilati mostra errori semantici e testo tagliato: nessuna validità amministrativa o qualità finale dei moduli rivendicata.

R6 ora development; v3 una sola esecuzione, senza retuning. {tests['passed']} test passati, {tests['skipped']} saltati. CI esterna pending_external_gate. Software 0.6.1, schema 610 e catalogo di 1216 documenti preservati. Report e limiti: [ROUND7_REPORT.md](docs/ROUND7_REPORT.md).
"""
    append('README.md',brief)
    brief_en=f"""## Round 7 — {status}

Decision policy v3 and retrieval v2 were frozen before the fresh evaluation: {len(rob['cases'])} planned attempts, {len(available)} generated representations across {len(rob['plan']['evaluation_identities'])} identities, {len(scan['cases'])} scan-like cases, and {filled_generated}/{len(filled['cases'])} generated AcroForms ({generation_failed} generation failures). Coverage is {cov['coverage_all']:.2%} overall and {cov['coverage_file_backed']:.2%} for documents with files. Canonical recognition is {can['counts']['exact']}/{len(can['cases'])}; exact recall is {value(rob,'document_recall'):.2%} for robustness, {value(scan,'document_recall'):.2%} for scans, and {value(filled,'document_recall'):.2%} for filled attempts. Failures stay in the planned denominator. Exact precision is 100% on emitted matches. Historical unknown rejection is {value(unknown,'unknown_correct_rejection_rate'):.2%}, using previously calibrated cases. Family recognition remains insufficiently validated ({fam['families_evaluable']}/16 evaluable families). Recognition p95 is {perf['latency_ms']['p95']:.2f} ms; index size is {perf['fingerprints']['index_bytes']} bytes.

Filled-form visual QA found incorrect field assignments and clipped text; administrative validity and final form quality are not claimed. R6 is now development data; v3 ran once, with no subsequent tuning. {tests['passed']} tests passed and {tests['skipped']} were skipped. External CI is pending. Public software 0.6.1, schema 610, and the 1216-document catalog are preserved. See the [full Round 7 report](docs/ROUND7_REPORT.md) for gates and limitations. No push, tag, or public release.
"""
    append('README_EN.md',brief_en)
    benchmark_paragraph('README.md',f"Candidata Round 7 **{status}**, software pubblico 0.6.1. Catalogo: 1.216 identità reali, 1.212 operative, zero nuove identità. Copertura firme: 941/1212 ({cov['coverage_all']:.2%}), con file 941/1158 ({cov['coverage_file_backed']:.2%}); canonical 979/979; robustness 183/372 e scansioni 134/280. AcroForm generati 9/50, 41 fallimenti di generazione inclusi. p95 {perf['latency_ms']['p95']:.2f} ms. R6 è ora development. Gate, denominatori e limiti in [BENCHMARK.md](docs/BENCHMARK.md) e [ROUND7_REPORT.md](docs/ROUND7_REPORT.md). CI esterna non eseguita.")
    benchmark_paragraph('README_EN.md',f"Round 7 candidate **{status}**; public software remains 0.6.1. Catalog: 1,216 real identities, 1,212 operational, with no new identities. Fingerprint coverage is 941/1212 ({cov['coverage_all']:.2%}) overall and 941/1158 ({cov['coverage_file_backed']:.2%}) for documents with files. Canonical recognition is 979/979; robustness is 183/372 and scans are 134/280. Only 9/50 AcroForms were generated; all 41 generation failures remain in the denominator. Recognition p95 is {perf['latency_ms']['p95']:.2f} ms. R6 is now development data. See [BENCHMARK.md](docs/BENCHMARK.md) and [ROUND7_REPORT.md](docs/ROUND7_REPORT.md) for gates and limitations. External CI is pending.")
    append('docs/BENCHMARK.md',brief.replace('(docs/ROUND7_REPORT.md)','(ROUND7_REPORT.md)')+'\n\nCoverage, canonical, robustness, filled, scan/OCR, family, unknown e regressioni sono metriche separate. V1/v2 raw e label restano visibili; R6 evaluation è development, v3 è il solo nuovo test di rappresentazioni. Unknown è storico/calibrato, non indipendente. I gate non vengono ridefiniti quando falliscono.\n')
    append('docs/COVERAGE.md',brief.replace('(docs/ROUND7_REPORT.md)','(ROUND7_REPORT.md)')+'\n\nDenominatore con file invariato1158; tutte le acquisizioni fallite restano.14 identità con byte aggiuntivi,2 attive recuperate,9 quarantene per SHA condiviso. Unsupported reale, conflitto canonico e fonti bloccate sono distinguibili negli audit.\n')
    current_banner('docs/BENCHMARK.md',f'# Benchmark Round 7 — {status}',f"Stato corrente: **{status}**. Copertura con file {cov['coverage_file_backed']:.2%}; canonical 979/979; nuova robustness 183/372 ({value(rob,'document_recall'):.2%}), scansioni 134/280 ({value(scan,'document_recall'):.2%}), AcroForm generati 9/50 (41 fallimenti). p95 {perf['latency_ms']['p95']:.2f} ms; 690 test passati e 3 saltati. Il [rapporto Round 7](ROUND7_REPORT.md) contiene i gate correnti, i raw v3 e i limiti. CI esterna pending_external_gate.\n\n## Archivio Round 6 — ora development\n\nLe sezioni numerate seguenti conservano la misura storica Round 6, con i suoi hash e denominatori. Non descrivono il comportamento corrente; il riepilogo Round 7 è anche in fondo a questo documento.")
    current_banner('docs/COVERAGE.md',f'# Copertura della candidata — Round 7 {status}',f"Stato corrente: 1216 record reali, 1212 operativi e 4 rifiutati; seed e provenienze invariati. Firme attive per 941 identità: {cov['coverage_all']:.2%} sul totale e {cov['coverage_file_backed']:.2%} sui 1158 documenti con file. Il gate dell'85% con file fallisce. Canonical su file 979/979; autocopertura dei metadati 1169/1212, misura distinta. Dettagli nel [rapporto Round 7](ROUND7_REPORT.md) e nel riepilogo in fondo.\n\n## Archivio delle misure precedenti\n\nLe sezioni seguenti conservano i risultati Round 3 e Round 2 e non costituiscono la copertura corrente.")
    append('DATA_NOTICE.md','## Round 7\n\nOnly hashes, public catalog metadata, real acquisition receipts and numeric/evidence benchmark outcomes are redistributed. Official files, OCR text and filled synthetic PDFs remain ignored. No identity, source, editorial verification or historical event is invented. No private upload is cached. Runtime stays local/offline/deterministic.\n')
    locked={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/OUT).rglob('*.json')) if not p.name.endswith('checkpoint.json') and p.name!='evaluation_locks.json'}
    write(OUT+'evaluation_locks.json',dict(runtime_sha256=frozen['runtime_sha256'],code_sha256=frozen['code_sha256'],sha256=locked,scope='Hashes attest immutable evidence bytes; not retrospective proof of independent selection. Prospective selection is freeze+started+plan chronology.'))
    print(status,'failed gates',[g['gate'] for g in gates if g['blocking'] and not g['passed']])

if __name__=='__main__':main()
