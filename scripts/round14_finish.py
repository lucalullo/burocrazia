"""Failure audit and truthful NOT READY reporting; no recognition calls."""
import argparse,csv,copy,platform
from scripts.round14_common import *
from scripts.round14_baseline import tests
from benchmarks.round3_audit import catalog
from benchmarks.evaluate import summary,ratio
from benchmarks.round14_unknown import validate_release,validate_observations,metrics

def failure():
    freeze=sealed();u=read('benchmarks/results/round14/unknown_release_v2.json');assert u['passed'] is False
    rows=validate_observations(read('benchmarks/results/round14/unknown_release_v2_observations.json'))['cases']
    manifest=validate_release(read('benchmarks/manifests/official_unknown_release_v2.json'));bycase={c['case_id']:c for c in manifest['cases']};bydoc={d.id:d for d in catalog()[0]}
    wrong=[];errors=[]
    for r in rows:
        c=bycase[r['id']]
        if r['observed']['match_type']!='NO_MATCH':
            d=bydoc.get(r['observed']['document_id']);p=r['decision_diagnostics']
            wrong.append(dict(case_id=r['id'],source=c['source'],official_url=c['official_url'],official_title=c['title'],unknown_sha256=c['SHA256'],truth_version=c['version'],
                              observed=r['observed'],catalog_title=d.titolo_ufficiale if d else None,catalog_version=d.versione if d else None,catalog_url=d.download_url if d else None,
                              signals=r['signals'],diagnostics=p))
        if r['extraction_failed']:errors.append(dict(case_id=r['id'],source=c['source'],official_url=c['official_url'],error=r['extraction_error'],pages=c['audit_evidence']['page_count']))
    assert len(wrong)==3 and len(errors)==4 and all('100 pagine' in c['error'] for c in errors)
    import pymupdf,re
    source=next(r for r in read('data/document_recognition_fingerprints_v3.json')['records'] if r['document_id']==1147)
    with pymupdf.open(stream=(ROOT/'benchmarks/cache'/(source['canonical_file_sha256']+'.body')).read_bytes(),filetype='pdf') as pdf:canonical_opening=pdf[0].get_text()[:2000]
    canonical_fact=dict(document_id=1147,canonical_sha256=source['canonical_file_sha256'],official_url=source['url'],catalog_version_field=bydoc[1147].versione,
                        opening_sha256=hashlib.sha256(canonical_opening.encode()).hexdigest(),literal_annual_heading=re.findall(r'Anno\s+20\d{2}',canonical_opening),
                        basis='Literal canonical first-page text; additional official fact, not an automatic catalog version correction.')
    concerns=[dict(case_id=r['case_id'],status='post_result_reference_ambiguity',reason='Same INAIL form subtype as catalog1147; official candidate opening says Anno2024/2025, canonical opening says Anno2023, catalog version field is null. Prior truth audit should have conservatively flagged possible_document_match/annual-version ambiguity. Frozen NO_MATCH label and all results retained; no post-hoc exclusion or PASS recalculation.') for r in wrong if r['observed']['document_id']==1147]
    save('failure_audit',dict(status='NOT READY',freeze_commit=freeze['freeze_git_commit'],manifest_sha256=sha('benchmarks/manifests/official_unknown_release_v2.json'),
        result_sha256=sha('benchmarks/results/round14/unknown_release_v2.json'),observations_sha256=u['observations_sha256'],wrong_accepts=wrong,extraction_errors=errors,reference_concerns=concerns,inail_canonical_official_fact=canonical_fact,
        frozen_label_metrics=metrics(rows),conditional_extraction_success_rejection_rate=107/110,labels_changed=False,engine_changed=False,replay=False,
        v5='not_run',plan_round15=['Resolve unversioned catalog binding versus annual INAIL source editions with official provenance; keep catalog metadata and canonical facts distinct.',
        'Investigate common-page identity evidence and metadata fallback on informational ANAC acts using development cases only.',
        'Preflight official file limits independently before future release selection; oversized input errors remain distinct from NO_MATCH.',
        'All114 R14 predictions are now observed. Any future tuning requires new independent release corpora, not replaying v2 as fresh.'],audited_at=now()))
    save('evaluation_not_run',dict(status='not_run',reason='Fresh unknown v2 failed; stop before known v5 selection/preflight/generation/recognition.',
        pool_audit=None,preflight=None,known_identities=None,sources=None,representations=None,scan_count=None,filled_count=None,retrieval=None,recognition_calls=0))
    print('R14 failure audit: labels and predictions preserved, no tuning/replay/v5',flush=True)

def final():
    freeze=sealed();u=read('benchmarks/results/round14/unknown_release_v2.json');cov=read('benchmarks/results/round14/coverage.json');pre=read('benchmarks/results/round14/pre_freeze_gate.json')
    registry=read(REGISTRY);selection=read('benchmarks/results/round14/unknown_v2_selection.json');checks=read('benchmarks/results/round14/final_checks.json')
    audit=read('benchmarks/results/round14/failure_audit.json');test=tests('reports/round14-final-tests.log');test.update(status='passed',python=platform.python_version(),os=platform.platform());save('tests',test)
    gates=[]
    def gate(name,target,actual,passed,blocking=True):gates.append(dict(gate=name,target=target,actual=actual,passed=passed,blocking=blocking,status='PASS' if passed else 'NON MISURATO' if actual is None else 'FAIL'))
    gate('fingerprint_coverage','>=85%',cov['file_backed_percent'],cov['passed']);gate('all_operational','>=70%',cov['all_operational_percent'],cov['all_operational_percent']>=70)
    gate('pre_freeze_canonical_native','100%','980/980',True);gate('pre_freeze_canonical_legacy','100%','27/27',True);gate('historical_safety','241 NO, 0 false accepts',0,pre['historical_safety_pass'])
    gate('performance_median_p95','<=250ms',pre['performance']['median_p95'],pre['performance_pass']);gate('performance_four_of_five','preferred >=4/5',pre['performance']['pass_count'],pre['performance']['preferred_four_of_five'],False)
    gate('unknown_v2_count','>=100',u['n'],u['n']>=100);gate('unknown_v2_sources','>=8',u['selection']['sources'],u['selection']['sources']>=8)
    gate('unknown_v2_max_concentration','<=25%',100*u['selection']['max_concentration'],u['selection']['max_concentration']<=.25)
    gate('unknown_v2_rejection','>=99%',100*u['rejection_rate'],u['passed']);gate('unknown_v2_entity_errors','0',u['entity_errors'],u['entity_errors']==0);gate('unknown_v2_version_errors','0',u['version_errors'],u['version_errors']==0)
    gate('unknown_v2_reference_qualification','confirmed unknown without unresolved catalog identity overlap',len(audit['reference_concerns']),not audit['reference_concerns'])
    for name,target in [('v5_preflight','>=30 IDs,6sources,400known,200scan,50filled'),('v5_leakage','0 prohibited'),('v5_precision','>=99.5%'),('v5_exact_recall','>=90%'),('v5_wrong_accepted','<=0.5%'),('v5_entity_errors','0'),('v5_version_errors','0'),('v5_scan_precision','>=99.5%'),('v5_scan_recall','>=85%'),('v5_filled_generation','>=90%'),('v5_filled_precision','>=99.5%'),('v5_filled_recall','>=90%'),('v5_retrieval_at25','100%'),('v5_unknown_mix','>=30fresh, rejection>=99%')]:gate(name,target,None,False)
    gate('pytest','0 failures',dict(passed=test['passed'],failed=0,skipped=test['skipped']),True)
    gate('compile_integrity_FK_migration_schema','0 failures',True,True)
    gate('release_fast_cli','exit0',checks['release_fast_exit'],checks['release_fast_exit']==0)
    gate('CI','external pending','external_pending',False,False)
    result=dict(round=14,status='NOT READY',software_version='0.6.1',candidate_target='0.7.0',schema=610,freeze=freeze['freeze_git_commit'],
                identity=read('benchmarks/results/round14/unknown_release_v2.json')['identity'],gates=gates,local_gates_passed=False,tests=test,ci='external_pending',reason='Unknown v2 failed; reference qualification concerns retained; no tuning or v5.')
    atomic_json(ROOT/'docs/release_gates.json',result)
    latest=read('benchmarks/latest_summary.json');latest.update(round=14,status='NOT READY',commit=head(),executed_at=now(),release_gate=result)
    latest['fingerprint_coverage']=dict(status='executed',operational_docs_total=1212,file_backed_operational_docs=1158,fingerprinted_all_operational_docs=1002,
        coverage_all=1002/1212,coverage_file_backed=1002/1158,native_coverage=975/1158,legacy_qualified=27,scope='Frozen support definition v1; shared resource support separated from exact identity accuracy.')
    # Display derives end-to-end rates explicitly: extraction failures are not
    # successful rejections. The immutable observation rows are not rewritten.
    rows=read('benchmarks/results/round14/unknown_release_v2_observations.json')['cases'];display=summary(rows);display.update(passed=107,failed=7)
    display['metrics']['unknown_correct_rejection_rate']=ratio(107,114);display['metrics']['unknown_false_acceptance_rate']=ratio(3,114)
    display['metrics']['unknown_extraction_failure_rate']=ratio(4,114)
    latest['unknown_official']=dict(status='executed',gate_passed=False,summary=display,rejection_rate=u['rejection_rate'],false_accepts=3,extraction_failed=4,
        reference_concerns=2,scope='Fresh v2 single-shot, frozen labels retained. Main end-to-end correct rejection excludes four extraction errors. Two INAIL annual identity reference concerns identified after results, never removed or relabelled.')
    for name in ['known_robustness','scan_ocr','filled_forms']:
        latest[name]=dict(status='not_run',reason='Stopped after unknown v2 failure; evaluation v5 not built or run.',summary=dict(cases=0,metrics={},latency_ms={}))
    latest['known_canonical']=dict(status='executed',summary=summary(read('benchmarks/results/round14/canonical.json')['cases']+read('benchmarks/results/round14/canonical_legacy.json')['cases']),native_resources=980,legacy_qualified_resources=27,scope='Pre-freeze run, identical sealed recognition bytes; no post-STOP rerun claimed.')
    latest['performance']=dict(status='executed',scope='Five pre-freeze warm runs, sealed identical engine; no favorable rerun after STOP.',**pre['performance'])
    latest['evaluations']=[dict(name=p.stem,summary=json.loads(p.read_bytes())['summary']) for p in sorted(OUT.glob('historical_*.json')) if 'summary' in json.loads(p.read_bytes())]
    atomic_json(ROOT/'benchmarks/latest_summary.json',latest)
    def table(rows):return '\n'.join('| '+' | '.join(str(v).replace('|','/') for v in r)+' |' for r in rows)
    gt=table([['Gate','Target','Risultato','Esito'],['---']*4]+[[g['gate'],g['target'],'non misurato' if g['actual'] is None else g['actual'],g['status']] for g in gates])
    pt=table([['Run warm','p50 ms','p95 ms'],['---']*3]+[[i+1,a,b] for i,(a,b) in enumerate(zip(pre['performance']['p50'],pre['performance']['p95']))])
    failures=table([['Caso','Fonte','Esito','Nota'],['---']*4]+[[r['case_id'],r['source'],r['observed']['document_id'],'Annualità INAIL / riferimento ambiguo' if r['observed']['document_id']==1147 else 'Regolamento ANAC emesso come modulo A.7'] for r in audit['wrong_accepts']])
    text=f'''# Round 14 — NOT READY

Software pubblico **0.6.1**, schema **610**, candidata 0.7.0. Branch `codex/coverage-benchmark-v0.7.0`. Ingresso `19883ba6a1e0e7360716aa0d9bba5ecb52a569eb`, working tree pulito. Prove pre-freeze committate in `5d659d1`; freeze dedicato **`{freeze['freeze_git_commit']}`**, creato prima di costruire unknown v2. Manifest registrato subito dopo il commit per evitare autoreferenze. Commit finale e SHA ZIP nel verificatore esterno `dist/package-verification-round14.json`. Nessun push, tag, pubblicazione o RC; README stable e versione pubblica invariati. CI **external_pending**.

## Pre-freeze e invarianti

Tutti i prerequisiti richiesti PASS prima del freeze. Coverage ricalcolata **1002/1158 = 86.528497%**, totale operativo **1002/1212 = 82.673267%**. Native support **975/1158 = 84.196891%**, 27/40 legacy qualificate; 33 associazioni shared storiche di solo supporto risorsa. Definizione SHA `{cov['definition_sha256']}` invariata. Canonici **980/980 nativi, 27/27 legacy**, zero errori. Shared ambiguities separati; Unioncamere 617/618/619 ancora shared/ambiguous. Safety **241 NO**, zero false accettazioni; R061, cinque casi ufficiali critici, due casi Round 8 e hard negatives confermati.

Baseline pytest **772 passed, 0 failed, 3 skipped**, 627.20 s. Cinque misure warm pre-freeze: mediana p95 **247.1435 ms**, gate obbligatorio <=250 PASS; **3/5** sotto 250, due run sopra 300, stabilità preferita non raggiunta e policy prudente segnala fragilità. Non si cambia la soglia né si selezionano rerun favorevoli. Il manifest sigilla runtime, catalogo semantic/file hash, dataset fingerprint, definizione, profili, reference truth, registry e hash dei risultati. Nessun byte del motore, scoring, indice, ranking, soglia, peso, veto, family, catalogo o fingerprint modificato. La differenza CRLF/LF preesistente del solo catalog_manifest è registrata separatamente; nessuna variazione di contenuto.

Unknown v1 conserva **105/105** e lo stato **historical_pre_unioncamere_fix**. Il bundle misurato era `d10650139b16d9809f3a08d7065572e4536e4a1094a710039de0ae1888ea423c`, quello corretto `{freeze['fingerprint_dataset_sha256']}`. Delta byte ricostruito dai tre record 617/618/619: soltanto status/shared_kind/ocr_metadata. V1 non è stato rieseguito, trasferito o usato per tuning.

## Registro di contaminazione e selezione fresca

Registry v1 SHA `{freeze['contamination_registry_sha256']}`, creato prima del freeze: **{registry['counts']['known_contaminated']} known contaminate**, **{registry['counts']['known_eligible']} potenzialmente eleggibili**, {registry['counts']['unknown_previously_seen']} unknown con predizione osservata, 105 in release v1, {registry['counts']['all_previously_observed_resource_shas']} SHA osservati complessivi e 16 family. Evidenze per identità/caso e hash di tutti gli input storici. La sola verifica canonica/SHA catalog-wide è distinta dal tuning; calibration, development, precedenti robustness/filled/scan/holdout e qualificazione legacy escludono conservativamente. Le 416 identità non sono una preflight v5: leakage ulteriore, capacità di trasformazione e filler non sono stati misurati.

Dopo freeze: 147 allegati in cache mai osservati, prima truth 44. Raccolta maintenance benchmark-only con **400 richieste HTTPS**, robots, allowlist, ricevute, limiti e nessun bypass di blocchi. Nessuna fonte o identità aggiunta al prodotto. Pool finale **348 candidati**: 127 confirmed_unknown, 122 unsupported_truth, 85 ambiguous, 8 possible_family_match, 6 possible_document_match. Criteri di truth invariati: URL/SHA/receipt, entity letterale nell'opening2000, titolo/codice/anno/versione, compatibilità family e overlap tecnico fingerprint; nessuna decisione/confidence di recognition usata per selezionare.

Quota preferita 20/source, seed {SEED}, gruppi near-resource indivisibili: primo subset 97 insufficiente, preservato. Prima di qualsiasi predizione si è applicato il limite obbligatorio consentito di 25/source, senza cambiare truth o seed: **114 casi**, **12 fonti**, **14 enti**, **12 tipi**, massima concentrazione **21.929825%** (preferito <=20 non raggiunto), 10 coded/104 non-coded, 40 versioned/74 unversioned. SHA v2 `{sha('benchmarks/manifests/official_unknown_release_v2.json')}`. Intersezione SHA con v1/development/predizioni osservate: **zero**. Fresco significa nuova predizione: alcune ricevute ufficiali in cache precedono il freeze, altre sono state acquisite dopo; nessuna falsa data o indipendenza dal catalogo dei metadati rivendicata.

## Unknown v2 single-shot e STOP

Eseguito **una sola volta**, checkout HEAD uguale al freeze, runtime/dataset sigillati identici. Writer transazionale: expected=actual=unique=114, checkpoint SQLite ignorato, export atomico, schema validato e SHA `{u['observations_sha256']}`. **107 correct NO_MATCH /114 = 93.859649%**, **3 wrong DOCUMENT_MATCH**, **0 wrong FAMILY_MATCH**, false acceptance **2.631579%**, **4 extraction errors**, entity errors **0**, explicit version/year contradiction errors **0**. Versione emessa nei tre exact: null; non si inventa una versione nel catalogo. Wilson 95% rejection **87.865706–96.994072%**, descrittivo del set e delle label congelate. Per fonte/ente/tipo nei raw. Escludendo soltanto gli errori di estrazione, 107/110 = **97.272727%**, comunque sotto 99; il gate usa il denominatore integrale 114.

{failures}

I due INAIL sono annualità 2024/2025 dello stesso sottotipo società partecipata pubblica; il canonico 1147 apre con Anno2023 ma il campo versione catalogo è null. La pipeline li ha emessi tramite pagina canonica2, digital0.9293/char0.8600, non tramite SHA. **Limite dell'audit truth:** questa relazione con l'identità già presente richiedeva la classificazione prudente possible_document_match/ambiguous prima della selezione. Dopo i risultati non si correggono label, non si tolgono casi e non si ricalcola un PASS. Sono dubbi di qualificazione del riferimento, oltre al gate osservato fallito. ANAC è una bozza di regolamento su accesso civico, emessa come A.7 modulo richiesta accesso documenti amministrativi l.241/1990 tramite fallback metadati, senza fingerprint sufficiente. I quattro errori sono PDF ufficiali oltre il limite runtime di 100 pagine: rifiuti leggibili per limite, **non** correct NO_MATCH; nessun limite rilassato.

STOP applicato: **NOT READY**, nessun tuning, replay o modifica delle label/fingerprint. Le114 predizioni sono ormai osservate e non potranno diventare un nuovo set indipendente dopo tuning. `failure_audit.json` conserva prove e piano Round15: chiarire annualità/binding con provenance ufficiale, studiare pagine comuni e fallback metadati su development, preflight dei limiti file, nuovi corpus indipendenti. Nessuna correzione del motore effettuata in Round14.

## Evaluation v5, retrieval, scan, filled e family

**Non avviata** perché unknown v2 FAIL. Nessuna selezione known v5, pool audit v5, preflight, generazione, leakage check o prediction. Identità/fonti/rappresentazioni, exact/family/reject/wrong, precision/recall/F1/CI, errori ente/versione, retrieval @1/@5/@10/@25: **non misurati**. Scan N/P/R e transform breakdown non misurati; filled generation/valid N/recognition/end-to-end non misurati; mix unknown v2 end-to-end v5 non costruito. Nessun dato assente trattato come zero/PASS. Family **experimental / insufficiently validated**, non usata per gonfiare useful recall; i test family storici restano verdi e un FAMILY_MATCH errato sarebbe falsa accettazione.

## Performance, canonici e test finali

{pt}

Mediana p95 **247.1435 ms**, massimo **303.6369 ms**. 67 input, 402 richieste/run, 5 run/2010 tempi; OCR escluso dal gate warm, estrazione/OCR end-to-end separati nei raw. Questi sono i run pre-freeze che hanno autorizzato il freeze dello stesso identico motore, non una nuova misura dopo lo STOP. Dopo il fallimento non si rieseguono i release benchmark; canonici e performance post-evaluation v5 non eseguiti perché v5 non è iniziata. Verificata invece l'integrità hash/binding dei risultati canonici già eseguiti e dei byte sigillati.

Pytest finale **{test['passed']} passed, 0 failed, {test['skipped']} skipped**, {test['seconds']} s, Python {test['python']}, {test['os']}; SHA log `{test['log_sha256']}`. Skip: symlink senza privilegio Windows e due FIFO. Compile, SQLite integrity, FK, copia/migrazione schema610 con conteggi invariati, tre validator fingerprint, schema/count/SHA del benchmark PASS. Release-fast eseguito offline: **exit{checks['release_fast_exit']}**, contraddizioni storiche EX02/EX03 preservate; v1 non riscritto e nessuna falsa dichiarazione di CLI/CI tutta verde. Compat v2 CLI exit0. Tutti i dettagli in `final_checks.json`. Test sintetici, Tesseract locale, integrità, qualificazione truth e CI restano ambiti distinti.

## Gate table

{gt}

## Limiti e archivio

Limiti reali: unknown v2 fallito, due riferimenti INAIL da adjudicare, quattro PDF oltre 100 pagine, performance fragile (3/5 sotto 250 ms), release-fast storico exit 1, v5 non misurata, family sperimentale, nessuna nuova dimostrazione RSS, CI esterna pending. Catalogo completo e provenienza conservati; corpus, reference truth, raw e archivi precedenti intatti. Nessun file personale, database di lavoro, convertito o credenziale in Git.

Archivio: `dist/BurOCRazia-v0.7.0-candidate-NOT-READY-round14.zip`, prodotto da HEAD finale. SHA256 e commit finale in `.zip.sha256` e `dist/package-verification-round14.json`, esterni allo ZIP per evitare autoreferenze. Stato locale **NOT READY**, nessuna RC o release pubblicata.
'''
    (ROOT/'docs/ROUND14_REPORT.md').write_text(text,encoding='utf8',newline='\n')
    p=ROOT/'docs/BENCHMARK.md';old=p.read_text(encoding='utf8');start='<!-- round14-current -->';end='<!-- /round14-current -->'
    if start in old:old=old[old.index(end)+len(end):].lstrip()
    intro=f'Round 14 **NOT READY**. Freeze `{freeze["freeze_git_commit"]}`; coverage 1002/1158 = 86.53%, canonici 980/980 + 27/27, safety 241 NO / 0 FA. Unknown v2 fresco: 114 casi / 12 fonti, 107 rifiuti corretti, 3 DOCUMENT_MATCH sulle label congelate, 4 errori di estrazione; 93.86%, gate FAIL. Due annualità INAIL richiedono adjudicazione truth, senza correzioni post-hoc. Nessun tuning/replay/v5. Performance pre-freeze: mediana p95 247.1435 ms, solo 3/5 sotto 250 ms; pytest finale {test["passed"]} passed / {test["skipped"]} skipped. [Report Round 14](ROUND14_REPORT.md).'
    p.write_text(start+'\n# Round 14\n\n'+intro+' Le sezioni successive restano storiche.\n'+end+'\n\n'+old,encoding='utf8',newline='\n')
    print('R14 final report NOT READY',test,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['failure','final']);a=p.parse_args();globals()[a.mode]()
