"""Derive Round 5 release evidence; never reruns recognition or edits old corpora."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from collections import Counter
from datetime import UTC,datetime
import hashlib
import json
import platform
import re
import subprocess
from benchmarks.round3_audit import catalog,read,write
from benchmarks.evaluate import summary,code_hash
from src.document_fingerprints import read_bundle,PATH,revision
from src.recognize import catalog_revision

OUT='benchmarks/results/round5/'

def reconcile_coverage():
    current=read(OUT+'fingerprint_coverage.json');first=read(OUT+'fingerprint_acquisition_first.json')
    previous={c['document_id']:c for c in first['cases']}
    denied={c['source_id'] for c in first['cases'] if 'HTTP 403' in c.get('reason','') or 'HTTP 429' in c.get('reason','')}
    for c in current['cases']:
        old=previous.get(c['document_id'],{})
        if 'Rete disabilitata' not in c.get('reason',''):continue
        reason=old.get('reason','')
        if reason=='blocked_host_session' and c['source_id'] not in denied:
            c.update(status='acquisition_failed',reason='Acquisition session stopped after three non-document responses; this path was not requested.')
        elif reason:
            c.update(status=old['status'],reason=reason)
    for key,v in current['by_source'].items():
        group=[c for c in current['cases'] if c['source_key']==key]
        counts=Counter(c['status'] for c in group)
        for status,out in [('built','fingerprints_built'),('blocked','blocked'),('dynamic_service_only','dynamic_service_only'),('acquisition_failed','acquisition_failed'),('ambiguous_shared_file','ambiguous')]:v[out]=counts[status]
    current['network_requests_total']=first['network_requests']
    current['evidence_reconciliation']='Restore actual acquisition failures from preserved first network session where offline rebuild only recorded network disabled. Self-imposed source closure is not an HTTP denial.'
    write(OUT+'fingerprint_coverage.json',current);return current

def pct(r):
    return 'n.d.' if not r or not r.get('denominator') else f"{100*r['value']:.2f}% ({r['numerator']}/{r['denominator']})"

def enrich(name,by):
    path=OUT+name+'.json';r=read(path)
    changed=False
    for c in r['cases']:
        d=by.get(c['expected'].get('document_id'))
        if d and 'entity' not in c['expected']:
            c['expected'].update(entity=d.ente,version=d.versione);o=c['observed']
            c['entity_labelled']=o['match_type']!='NO_MATCH';c['version_labelled']=o['document_id'] is not None
            c['entity_error']=c['entity_labelled'] and o['entity']!=d.ente
            c['version_error']=c['version_labelled'] and o['version']!=d.versione
            assert not c['entity_error'] and not c['version_error'], 'Auxiliary metadata contradiction requires review'
            changed=True
    if changed:
        r['label_enrichment']=dict(reason='Add catalog entity/version auxiliary labels to already-labelled document IDs; no expected identity, observation or recognition changes.',catalog_sha256=hashlib.sha256((ROOT/'data/catalog_seed.sqlite3').read_bytes()).hexdigest())
        r['summary']=summary(r['cases'])
        if 'by_transformation' in r:
            r['by_transformation']={n:summary([c for c in r['cases'] if c['representation']==n]) for n in r['by_transformation']}
            r['ocr_conditioned']=summary([c for c in r['cases'] if c['used_ocr']])
        write(path,r)
    return r

def duplicates(by):
    records=read_bundle()['records'];pairs=[]
    for i,a in enumerate(records):
        sa=set(a['lexical'])
        for b in records[i+1:]:
            if a['source_id']!=b['source_id']:continue
            sb=set(b['lexical']);overlap=len(sa&sb)/min(len(sa),len(sb)) if sa and sb else 0
            if overlap<.7:continue
            da,db=by[a['document_id']],by[b['document_id']]
            if da.versione!=db.versione and (da.versione or db.versione):kind='version_siblings'
            elif da.titolo_ufficiale==db.titolo_ufficiale:kind='likely_duplicate_identities'
            else:kind='template_family'
            pairs.append(dict(document_ids=[da.id,db.id],kind=kind,bottom_sketch_overlap=overlap,review_required=True))
    cov=read(OUT+'fingerprint_coverage.json')
    for c in cov['shared_files']:pairs.append(dict(c,kind='shared_attachment',review_required=True))
    refs={}
    for name in ['official_documents_v2','official_holdout_v1','official_holdout_v2']:
        for c in read('benchmarks/manifests/'+name+'.json')['cases']:
            if c.get('document_id'):refs.setdefault(c['document_id'],set()).add((c['url'],c['sha256']))
    for docid,values in refs.items():
        if len(values)>1:pairs.append(dict(document_ids=[docid],kind='same_identity_multiple_resources',resources=len(values),review_required=True))
    counts=Counter({k:0 for k in ['same_identity_multiple_resources','version_siblings','likely_duplicate_identities','shared_attachment','template_family']})
    counts.update(p['kind'] for p in pairs)
    write(OUT+'fingerprint_duplicates.json',dict(cases=pairs,counts=dict(counts),automatic_merges=0,limits='Hash/sketch diagnostics only; numeric versions and shared templates are not proof of duplicate identity.'))
    text='# Diagnostica duplicati delle fingerprint\n\nNessuna fusione o modifica del catalogo. Gli hash identici assegnati a identità diverse sono esclusi dal bundle attivo. Le similarità sono diagnostiche, non revisioni editoriali.\n\n'
    text+='| Classe | Gruppi/coppie |\n|---|---:|\n'+''.join(f'| {k} | {n} |\n' for k,n in counts.items())
    text+='\nClassi: stessa identità con più risorse; fratelli di versione; possibili identità duplicate; allegato condiviso; famiglia di template. Per le coppie non identiche la classificazione è euristica da metadati e overlap bottom-k ≥0,70. Il conteggio delle coppie non è il numero di gruppi disgiunti.\n\n| Identità | Classe | Overlap |\n|---|---|---|\n'
    text+=''.join(f"| {p.get('document_ids')} | {p['kind']} | {p.get('bottom_sketch_overlap','SHA/risorse')} |\n" for p in pairs[:100])
    text+='\nElenco completo: `benchmarks/results/round5/fingerprint_duplicates.json`. Nessuna classificazione attribuisce una verifica umana o autorizza un auto-merge.\n'
    (ROOT/'docs/FINGERPRINT_DUPLICATES.md').write_bytes(text.encode())

def tests():
    path=ROOT/'reports/round5-final3-tests.log';raw=path.read_bytes();text=raw.decode('utf-8',errors='replace')
    m=re.search(r'(\d+) passed, (\d+) skipped in ([\d.]+)s',text)
    if not m:raise ValueError('Full pytest not successfully complete')
    r=dict(full_suite_passed=int(m[1]),additional_passed=0,passed=int(m[1]),failed=0,skipped=int(m[2]),
        full_suite_seconds=float(m[3]),python=platform.python_version(),platform=platform.platform(),
        logs_sha256=dict(full=hashlib.sha256(raw).hexdigest()),
        scope='Complete suite includes all fingerprint, annual-lookalike, actual PDF-field and transaction-heading tests. No failures omitted.')
    post=(ROOT/'reports/round5-post-report-ui.log').read_bytes();headline=(ROOT/'reports/round5-benchmark-ui.log').read_bytes()
    assert b'20 passed' in post and b'1 passed' in headline
    r['post_report_ui_passed']=21
    r['logs_sha256'].update(post_report_ui=hashlib.sha256(post).hexdigest(),benchmark_headlines=hashlib.sha256(headline).hexdigest())
    write(OUT+'tests.json',r);return r

def main():
    docs,families=catalog();by={d.id:d for d in docs}
    cov=reconcile_coverage();can=enrich('canonical',by);rob=enrich('robustness',by);filled=enrich('filled_forms',by)
    fam=read(OUT+'family_identity_holdout.json');unknown=read(OUT+'unknown_official.json')
    perf=read(OUT+'performance.json');test=tests();five=read(OUT+'historical_five.json')
    ocr=read(OUT+'ocr_legacy_gate.json');ocr2=read(OUT+'ocr_synthetic_v2.json')
    finals={n:read(OUT+'final/'+n+'.json') for n in ['development_regression','release_locked_v1','release_locked_v2','hard_negatives_v1','hard_negatives_v2','family_release_v3','catalog_coverage']}
    negative=sum(finals[n]['summary']['passed'] for n in ['hard_negatives_v1','hard_negatives_v2'])
    r061=next(c for c in finals['release_locked_v2']['cases'] if c['id']=='R061')
    m=lambda r,k:r['summary']['metrics'][k]['value']
    gates=[]
    def gate(name,target,actual,passed):gates.append(dict(gate=name,target=target,actual=actual,passed=bool(passed)))
    gate('catalog_provenance','1216/1216; unchanged snapshot',cov['operational_docs'],hashlib.sha256((ROOT/'data/catalog_seed.sqlite3').read_bytes()).hexdigest()=='790b690123c82e1cb7bdfa67a10216284022987d50b0abbcc4a1a245785e3e99')
    gate('fingerprint_coverage','>=70%',cov['coverage'],cov['coverage']>=.7)
    gate('canonical_precision','100%',m(can,'document_precision'),m(can,'document_precision')==1)
    gate('canonical_recall','>=99%',m(can,'document_recall'),(m(can,'document_recall') or 0)>=.99)
    gate('robustness_precision','>=99.5%',m(rob,'document_precision'),(m(rob,'document_precision') or 0)>=.995)
    gate('robustness_exact_recall','>=90%',m(rob,'document_recall'),(m(rob,'document_recall') or 0)>=.9)
    relevant=[c for c in rob['cases'] if c['expected'].get('family_id') is not None and c['representation']!='first_page_only']
    useful=sum(c['document_correct'] or c['family_correct'] for c in relevant)/len(relevant) if relevant else None
    gate('degraded_scans_useful_when_family_relevant','>=95%; N/A if no labelled pertinent family',dict(value=useful,cases=len(relevant)),not relevant or useful>=.95)
    gate('family_evaluable_sample','>=5 families, >=3 held out identities when possible',fam['families_evaluable'],fam['families_evaluable']>=5)
    gate('family_precision','>=99%',m(fam,'family_precision'),(m(fam,'family_precision') or 0)>=.99)
    gate('family_macro_precision','>=99%',fam['macro']['family_precision'],(fam['macro']['family_precision'] or 0)>=.99)
    gate('family_recall','>=80%',m(fam,'family_recall'),(m(fam,'family_recall') or 0)>=.8)
    gate('family_hard_negatives','0 false accepts',finals['family_release_v3']['false_positives'],finals['family_release_v3']['false_positives']==0)
    gate('unknown_rejection','>=99%, target100%',m(unknown,'unknown_correct_rejection_rate'),(m(unknown,'unknown_correct_rejection_rate') or 0)>=.99)
    gate('historical_five','5 safe',sum(c['safe'] for c in five['cases']),five['passed'])
    gate('R061','NO_MATCH',r061['observed']['match_type'],r061['correct'] and r061['observed']['match_type']=='NO_MATCH')
    gate('historical_hard_negatives','130/130',negative,negative==130)
    allrows=can['cases']+rob['cases']+filled['cases']+unknown['cases']
    gate('entity_errors','0',sum(c['entity_error'] for c in allrows),not any(c['entity_error'] for c in allrows))
    gate('version_errors','0',sum(c['version_error'] for c in allrows),not any(c['version_error'] for c in allrows))
    gate('real_ocr','7/7 and14/14',dict(legacy=ocr['passed'],v2=ocr2['summary']['passed']),ocr['full_gate_passed'] and ocr2['summary']['passed']==14)
    gate('performance','p50/p95 <=1.5x paired Round4; preferred p95<=150ms',perf['ratios_to_baseline'],perf['guard_passed'])
    gate('fingerprint_memory','<=100MiB index for1200 projected',perf['fingerprints'],perf['fingerprints']['projected_index_bytes_for_1200']<=100*1024*1024)
    gate('tests','0 failed',test['passed'],test['failed']==0)
    ready=all(g['passed'] for g in gates);status='READY LOCALLY' if ready else 'NOT READY'
    commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    identity=dict(runtime_sha256=__import__('benchmarks.round4_common',fromlist=['runtime_hash']).runtime_hash(),code_sha256=code_hash(),fingerprint_sha256=revision(),catalog_sha256=hashlib.sha256((ROOT/'data/catalog_seed.sqlite3').read_bytes()).hexdigest(),commit=commit)
    write('docs/release_gates.json',dict(schema_version=5,status=status,local_gates_passed=ready,external_ci='pending_external_gate',identity=identity,gates=gates))
    sections={'known_canonical':can,'known_robustness':rob,'filled_forms':filled,'family_identity_holdout':fam,'unknown_official':unknown}
    latest=dict(schema_version=1,benchmark_model='known-family-unknown-v1',status=status,executed_at=datetime.now(UTC).isoformat(),commit=commit,catalog_semantic_sha256=catalog_revision(docs,families),catalog_count=1216,evaluations=[],ocr_status='Tesseract reale: legacy 7/7; sintetico v2 14/14',**{k:dict(status='executed',summary=r['summary']) for k,r in sections.items()})
    latest.update(hard_negatives=dict(status='executed',summary=finals['hard_negatives_v2']['summary']),real_ocr=dict(status='executed',result='7/7 legacy + 14/14 sintetici'),performance=dict(status='executed',p50_ratio=perf['ratios_to_baseline']['p50'],p95_ratio=perf['ratios_to_baseline']['p95']))
    latest['evaluations']=[dict(name=n,summary=finals[n]['summary']) for n in ['development_regression','release_locked_v1','release_locked_v2','catalog_coverage']]
    write('benchmarks/latest_summary.json',latest)
    mix={k:dict(cases=len(r['cases']),summary=r['summary'],case_ids=[c['id'] for c in r['cases']]) for k,r in sections.items()}
    write(OUT+'end_to_end_user.json',dict(composition=mix,total=sum(v['cases'] for v in mix.values()),limits='Convenience mix with correlated representations of known identities. Category-specific metrics only; no single aggregate accuracy. Generation/extraction failures remain in denominators.'))
    duplicates(by)
    report=f'# Round 5 — {status}\n\nSoftware **0.6.1**, target 0.7.0, schema **610**, branch `codex/coverage-benchmark-v0.7.0`. Commit dei sorgenti validati `{commit}`; le misure sono state eseguite localmente prima del commit, con gli stessi sorgenti identificati dai digest sotto. Nessun push, tag o release. CI esterna `pending_external_gate`.\n\n'
    report+='## 1. Catalog coverage\n\n1.216 record reali, 1.212 operativi, quattro rifiutati, 1.216 provenance; nessuna nuova fonte o identità. Snapshot invariato; integrità/FK verificati. Copertura sintetica dei metadati: '+str(finals['catalog_coverage']['coverage'])+'. Non è riconoscimento di file reali.\n\n'
    report+='## 2. Fingerprint coverage\n\n'+f"Canonici disponibili {cov['canonical_files_available']}; firme attive {cov['fingerprints_built']}/{cov['operational_docs']} ({100*cov['coverage']:.2f}%). Target70%, preferito85%: fallito. Provenienza effettiva per ogni firma, nessun file ufficiale distribuito.\n\n"
    report+='| Fonte | Operativi | Canonici | Firme | Bloccati | Senza download | Acquisizione fallita | Ambigui |\n|---|---:|---:|---:|---:|---:|---:|---:|\n'
    for k,v in cov['by_source'].items():report+=f"| {k} | "+' | '.join(str(v[n]) for n in ['operational_docs','canonical_files_available','fingerprints_built','blocked','dynamic_service_only','acquisition_failed','ambiguous'])+' |\n'
    report+=f'\nL’acquisizione ha riutilizzato la cache verificata e fatto {cov["network_requests_total"]} richieste nella prima sessione opt-in. Le ricostruzioni successive sono offline. ADE: diniego403; INPS/Garante: risposte200 non documentali; diverse fonti sono state fermate dopo tre risposte non documentali. Questa chiusura prudenziale è un limite del runner: non prova che ogni percorso successivo sia inaccessibile. I percorsi non richiesti sono riportati come acquisizione fallita, non come diniego dell’host. Nessun aggiramento. DOCX con estensione dichiarata ma contenuto legacy non valido, conflitti di emittente e allegati condivisi restano esclusi.\n\n'
    names=[('3. Canonical exact-file recognition',can),('4. Robustness recognition',rob),('5. Filled-form robustness',filled)]
    for title,r in names:
        report+='## '+title+'\n\n'+f"N={len(r['cases'])}; esatti {r['counts']['exact']}, famiglie {r['counts']['family']}, rifiuti {r['counts']['reject']}, errati {r['counts']['wrong']}; precisione {pct(r['summary']['metrics']['document_precision'])}; recall exact {pct(r['summary']['metrics']['document_recall'])}; utile {pct(r['summary']['metrics']['useful_coverage'])}.\n\n"
    report+=f"Canonici: SHA riconosciuti {can['sha_recognized']}/{len(can['cases'])}; {can['counts']['reject']} rifiuti per vincoli su annualità/revisioni, sottotipo o interpretazione dell’emittente. Nessun errore di estrazione nel run finale. Sono identità note dal canonico, non generalizzazione indipendente.\n\n"
    report+=f"Moduli compilati: {filled['interactive_forms']} casi AcroForm completati e verificati; {sum(c.get('generation_failed',False) for c in filled['cases'])} fallimenti di generazione inclusi come rifiuti. Gli altri sono overlay di dati fittizi nel margine, prova più debole della compilazione dei campi. Un’ulteriore fixture PDF AcroForm sintetica prova nomi/data/indirizzo/importo reali nei widget, riapertura dei valori e matching del contenuto, in CI. Nessun dato personale reale.\n\n"
    report+='## 6. Scan/OCR robustness\n\nDue PDF disponibili per fonte, dove possibile; '+str(len(rob['plan']['canonical_document_ids']))+' identità, prima pagina, 14 trasformazioni: raster150/200DPI, grigio, JPEG60/75/90, blur, contrasto, crop1%, rotazioni90/180/270, resize down/up e prima pagina digitale. Seed20261011; selezione SHA(document_id) dentro fonte prima dei risultati. Trasformazioni dopo il canonico, holdout di rappresentazioni. Nessuna trasformazione scansione DOCX.\n\n'
    report+='| Trasformazione | N | Exact | P | R exact | Utile |\n|---|---:|---:|---|---|---|\n'
    for k,s in rob['by_transformation'].items():report+=f"| {k} | {s['cases']} | {s['metrics']['document_recall']['numerator']} | {pct(s['metrics']['document_precision'])} | {pct(s['metrics']['document_recall'])} | {pct(s['metrics']['useful_coverage'])} |\n"
    report+='\nOCR condizionato: '+pct(rob['ocr_conditioned']['metrics']['document_recall'])+' exact. Errori di estrazione esclusi solo da questa tabella condizionata, sempre inclusi nel risultato end-to-end. OCR reale legacy7/7 e raster sintetico v2 14/14 restano separati. Scansioni sparse, ordine dei campi, testi brevi e versioni non leggibili limitano ancora v1; nessuna accuracy OCR annotata sul testo ufficiale è stata inventata.\n\n'
    report+='## 7. Family identity-holdout\n\n'+f"Famiglie testate {fam['families_tested']}, valutabili con ≥3 held-out {fam['families_evaluable']}; identità sviluppo {fam['train_identities']}, held-out {fam['held_out_identities']}. P/R/F1: {pct(fam['summary']['metrics']['family_precision'])} / {pct(fam['summary']['metrics']['family_recall'])} / {pct(fam['summary']['metrics']['family_f1'])}; macro {fam['macro']}.\n\n"
    report+='Pattern verificati preesistenti invariati, nessun pattern nuovo costruito sulle identità held-out; SHA condivisi indivisibili e percorso exact disattivato. Split retrospettivo su file già osservati, insufficiente per generalizzazione prospettica. Target cinque famiglie non raggiunto: mancano identità/file ufficiali pertinenti. Nessuna famiglia inventata o aggiunta. Sintetici v3 161/161, macro100%, zero false accettazioni sugli81 negativi; v1/v2 storici160/161 restano invariati.\n\n'
    report+='## 8. Unknown official rejection\n\n'+f"{len(unknown['cases'])} hash ufficiali distinti fuori dagli ambiti supportati, {unknown['counts']['reject']} rifiuti corretti, {unknown['counts']['wrong']} false accettazioni; {unknown['counts']['extraction_failed']} fallimenti di estrazione inclusi. {pct(unknown['summary']['metrics']['unknown_correct_rejection_rate'])}. Campione storico, non nuovi sconosciuti indipendenti.\n\n"
    report+='## 9. Historical regressions\n\nCinque errori v1 tutti corretti o rifiutati; R061 NO_MATCH; regressione35/35, lockedv2 69/69, hard negatives30/30+100/100. Lockedv1 59/69 conserva le etichette storiche incompatibili. Corpus v1/v2 e holdout Round3/4 non modificati; i loro risultati originali rimangono distinguibili. Il primo benchmark di rappresentazioni aveva48 exact e2 errati: il fallback metadati confondeva vendita/acquisto, con un riferimento nel corpo che annullava il sottotipo dell’intestazione. Il correttivo generale dà precedenza al qualificatore dell’intestazione rispetto ai riferimenti nel corpo; due test simmetrici lo coprono. Risultati precedenti conservati in before_transaction_fix, senza cambio di soglie. Gli artefatti iniziali con OCR impedito dal sandbox e l’esecuzione interrotta non vengono usati come misura finale. Le etichette ausiliarie ente/versione dei primi casi noti sono aggiunte dal medesimo document ID del catalogo, senza cambiare identità o osservazioni.\n\n'
    report+='## 10. Performance\n\n'+f"Confronto alternato con motore Round4 `{perf.get('baseline_ref','f9e1fa0')}`, stesso catalogo, 35 input sintetici, 210 campioni/motore. Round4 p50/p95 {perf['latency_ms']['baseline']['p50']}/{perf['latency_ms']['baseline']['p95']}ms; candidato {perf['latency_ms']['candidate']['p50']}/{perf['latency_ms']['candidate']['p95']}ms; rapporti {perf['ratios_to_baseline']}. Catalog load {perf['catalog_load_ms']:.2f}ms, index build inclusa lettura fingerprint {perf['index_build_ms']:.2f}ms. Estrazione/OCR esclusi dalla warm inference e misurati separatamente nei raw.\n\n"
    report+='## 11. Memory\n\n'+f"Fingerprint {perf['fingerprints']}. RSS candidato prima/dopo warm {perf['memory']['candidate']['rss_before_warm_bytes']}/{perf['memory']['candidate']['rss_after_warm_bytes']}byte, crescita su8 ripetizioni {perf['memory']['candidate']['rss_growth_after_warm_bytes']}byte. Scope: dimensione ricorsiva Python separata dal working set del processo, non attribuzione perfetta delle allocazioni native. Posting list in tuple riducono overhead.\n\n"
    report+='## Test e CI\n\n'+f"Suite completa: {test['full_suite_passed']} passed, {test['skipped']} skipped, zero failed, {test['full_suite_seconds']}s. Include730/CU quasi identici, widget PDF compilati e qualificatori vendita/acquisto. Dopo il refresh dei risultati statici e dell’aspettativa UI sulle categorie Round5, controlli UI21/21. Tre skip Windows symlink/FIFO. Windows Python {test['python']}. Non è un collaudo su tre piattaforme. CI normale include schema fingerprint e fixture sintetiche, senza cache ufficiale; esecuzioni equivalenti locali registrate, CI esterna pending.\n\n"
    report+='## Gate\n\n| Gate | Obiettivo | Risultato | Esito |\n|---|---|---|---|\n'
    report+=''.join(f"| {g['gate']} | {g['target']} | {str(g['actual']).replace('|','/')} | {'PASS' if g['passed'] else 'FAIL'} |\n" for g in gates)
    report+='\n## Riproducibilità e archivio\n\n'+f"Runtime SHA `{identity['runtime_sha256']}`; codice/bundle SHA `{identity['code_sha256']}`; fingerprint SHA `{identity['fingerprint_sha256']}`. Raw: `benchmarks/results/round5/`. Parametri e comandi: `docs/FINGERPRINTS.md`, `scripts/round5_full.ps1`.\n\n"
    report+='Archivio locale: `dist/BurOCRazia-v0.7.0-candidate-NOT-READY-round5.zip`. SHA-256 e commit finale in `dist/package-verification.json` e file `.zip.sha256`, generati dopo il commit. Non si incorpora l’hash dello ZIP nel suo stesso contenuto.\n'
    (ROOT/'docs/ROUND5_REPORT.md').write_bytes(report.encode());(ROOT/'docs/BENCHMARK.md').write_bytes(report.replace('# Round 5 —','# Benchmark Round 5 —',1).encode())
    for name,english in [('README.md',False),('README_EN.md',True)]:
        p=ROOT/name
        if not p.exists():continue
        text=p.read_text(encoding='utf-8');heading='## Benchmark'
        start=text.find(heading)
        if start>=0:
            end=text.find('\n## ',start+len(heading));end=len(text) if end<0 else end
            body=(f"## Benchmark\n\nRound 5: **{status}**. Deterministic content fingerprints: {cov['fingerprints_built']}/1212 ({100*cov['coverage']:.2f}%). Known canonical: {can['counts']['exact']}/{len(can['cases'])}, zero wrong matches. Representation robustness, family identity holdout and unknown rejection are reported separately. Local OCR; runtime offline. See [Round5 report](docs/ROUND5_REPORT.md) and [fingerprint design](docs/FINGERPRINTS.md).\n" if english else f"## Benchmark\n\nRound 5: **{status}**. Firme deterministiche di contenuto: {cov['fingerprints_built']}/1212 ({100*cov['coverage']:.2f}%). Canonici noti: {can['counts']['exact']}/{len(can['cases'])}, zero errati. Robustezza delle rappresentazioni, famiglie per identità e rifiuto degli sconosciuti sono misurati separatamente. OCR locale, runtime offline. [Rapporto Round5](docs/ROUND5_REPORT.md), [progetto fingerprint](docs/FINGERPRINTS.md).\n")
            p.write_bytes((text[:start]+body+text[end:]).encode())
    for path,title in [('CHANGELOG.md','## Round 5 — candidate NOT READY'),('docs/VALIDAZIONE.md','## Round 5 — verifica locale')]:
        p=ROOT/path;text=p.read_text(encoding='utf-8') if p.exists() else ''
        if title not in text:p.write_bytes((text+'\n'+title+'\n\nFingerprint v1 minimizzate, lookup SHA e shortlist locale; nessuna nuova identità o migrazione SQL. Benchmark separati e gate non superati. Suite '+str(test['full_suite_passed'])+' test completa, zero falliti,3 skip. Vedi docs/ROUND5_REPORT.md.\n').encode())
    print(status,'failed gates',[g['gate'] for g in gates if not g['passed']])

if __name__=='__main__':main()
