"""Truthful stopped-round report; no recognition and no release freeze."""
import copy,platform,statistics
from scripts.round15_common import *
from scripts.round14_baseline import perf_check
from benchmarks.evaluate import summary
from benchmarks import round8_common as common
from src.benchmark_display import load_summary

def main():
    cov=read(OUT/'coverage.json');perf=perf_check(read(OUT/'performance_pre_freeze.json'));tests=read(OUT/'tests.json');checks=read(OUT/'final_checks.json')
    native=read(OUT/'canonical.json');legacy=read(OUT/'canonical_legacy.json');safety=read(OUT/'historical_safety.json');inputs=read(OUT/'input_safety.json');dev=read(OUT/'development_regression_after_round15_fix.json');reg=read(REGISTRY)
    assert perf['passed'] is False,'This reporting path preserves a failed prerequisite'
    assert not (OUT/'freeze_manifest.json').exists() and not (ROOT/'benchmarks/manifests/official_unknown_release_v3.json').exists()
    common.SEED=SEED;ident=common.identity()
    reasons=['Performance prerequisite failed: median p95 263.0707ms exceeds250ms, five predetermined runs retained.','Actual release-fast CLI exit1 with unchanged historical EX02/EX03; zero-failure final gate not met.']
    prereq=dict(coverage_pass=cov['passed'],canonical_native_pass=native['counts']['exact']==len(native['cases'])==980,canonical_legacy_pass=legacy['counts']['exact']==len(legacy['cases'])==27,
        historical_safety_pass=safety['passed'],input_safety_pass=inputs['passed'],performance_pass=perf['passed'],tests_pass=tests['failed']==0)
    save('pre_freeze_gate',dict(**prereq,passed=all(prereq.values()),performance=perf,created_at=now(),identity=ident,recognition_semantic_sha256=ident['runtime_sha256'],freeze_allowed=False))
    save('freeze_not_created',dict(status='not_created',freeze_commit=None,reason=reasons[0],performance_sha256=sha(OUT/'performance_pre_freeze.json'),no_semantic_changes_after_failed_prerequisite=True,recognition_semantic_sha256=ident['runtime_sha256']))
    save('unknown_release_v3',dict(status='not_run',passed=False,reason='Stopped before freeze and final corpus selection because mandatory performance prerequisite failed.',freeze_commit=None,selection=None,n=None,sources=None,max_concentration=None,rejection_rate=None,confidence_interval_95=None,wrong_document_match=None,wrong_family_match=None,recognition_calls=0,independent_replays=0))
    save('evaluation_not_run',dict(status='not_run',reason='Unknown v3 not selected or run; v5 is authorized only after a passing fresh unknown gate.',identities=None,sources=None,representations=None,scans=None,filled=None,leakage=None,precision=None,exact_recall=None,retrieval=None,recognition_calls=0))
    gates=[]
    def gate(name,target,actual,passed,blocking=True):gates.append(dict(gate=name,target=target,actual=actual,passed=passed,blocking=blocking,status='PASS' if passed else 'NON MISURATO' if actual is None else 'FAIL'))
    gate('truth_adjudication','3 official decisions before engine edit; ambiguous excluded',dict(confirmed_unknown=1,actual_catalog_document=0,ambiguous=2,release_eligible=0),True)
    gate('fingerprint_coverage','>=85%',cov['file_backed_percent'],cov['passed']);gate('all_operational','>=70%',cov['all_operational_percent'],cov['all_operational_percent']>=70)
    gate('canonical_native','100%',f"{native['counts']['exact']}/{len(native['cases'])}",prereq['canonical_native_pass']);gate('canonical_legacy','100%',f"{legacy['counts']['exact']}/{len(legacy['cases'])}",prereq['canonical_legacy_pass'])
    gate('historical_safety','241 NO; 0 false accepts',dict(n=safety['n'],false_accepts=len(safety['false_accepts'])),safety['passed'])
    gate('confirmed_ANAC_regression','NO_MATCH',dev['confirmed_anac_after']['match_type'],dev['confirmed_anac_after']['match_type']=='NO_MATCH')
    gate('input_safety','all safe rejects/no crash/no residue',f"{inputs['safe_rejects']}/{inputs['n']}",inputs['passed'])
    gate('performance_median_p95','<=250ms',perf['median_p95'],perf['passed']);gate('performance_four_of_five','preferred>=4/5',perf['pass_count'],perf['pass_count']>=4,False)
    for name,target in [('unknown_v3_sample','>=100 confirmed unknown,8sources,max25%'),('unknown_v3_rejection','>=99%'),('unknown_v3_wrong_document','<=1%'),('unknown_v3_entity_version','0'),('v5_preflight','>=30IDs,6sources,400reps,200scan,50filled,30unknown'),('v5_leakage','0 prohibited'),('v5_precision','>=99.5%'),('v5_exact_recall','>=90%'),('v5_entity_version','0'),('v5_scan_precision','>=99.5%'),('v5_scan_recall','>=85%'),('v5_filled_generation','>=90%'),('v5_filled_precision','>=99.5%'),('v5_filled_recall','>=90%'),('v5_retrieval_at25','100%'),('v5_retrieval_at1','target>=99%'),('v5_unknown_mix','>=99% rejection')]:gate(name,target,None,False)
    for name,target in [('release_freeze','Dedicated commit after all prerequisites'),('unknown_v3_freshness','0 prior SHA or obvious near-resource reuse'),('unknown_v3_supported_truth','Confirmed unknown, supported input only'),('unknown_v3_types','>=5 types'),('unknown_v3_family_acceptance','Counts as false acceptance')]:gate(name,target,None,False)
    gate('pytest','0 failures',dict(passed=tests['passed'],failed=tests['failed'],skipped=tests['skipped']),tests['failed']==0)
    gate('compile_integrity_FK_migrations_schema','0 failures',True,True);gate('release_fast_cli','exit0',checks['release_fast_exit'],checks['release_fast_exit']==0)
    gate('family_identity_holdout','>=5 real families','experimental / insufficiently validated',False,False);gate('CI','external pending','external_pending',False,False)
    atomic_json(ROOT/'docs/release_gates.json',dict(round=15,status='NOT READY',software_version='0.6.1',candidate_target='0.7.0',schema=610,freeze=None,identity=ident,gates=gates,local_gates_passed=False,tests=tests,ci='external_pending',reasons=reasons,
        unknown_v3='not_run',evaluation_v5='not_run',historical_unknown_v2='historical_unknown_release_v2_round14',adjudication_sha256=sha('benchmarks/reference/round15_truth_adjudication.json')))
    latest=copy.deepcopy(read('benchmarks/latest_summary.json'));latest.update(round=15,status='NOT READY',software_version='0.6.1',version='0.6.1',commit=ident['commit'],runtime_sha256=ident['runtime_sha256'],fingerprint_sha256=ident['fingerprint_sha256'],reasons=reasons)
    latest['historical_unknown_release_v2_round14']=dict(status='historical_unknown_release_v2_round14',n=114,correct_no_match=107,wrong_document_match=3,wrong_family_match=0,extraction_failed=4,
        original_manifest_sha256=sha('benchmarks/manifests/official_unknown_release_v2.json'),original_raw_sha256=sha('benchmarks/results/round14/unknown_release_v2_observations.json'),adjudicated_confirmed_false_accepts=1,adjudicated_ambiguous=2)
    for name in ['known_robustness','scan_ocr','filled_forms','unknown_official']:
        latest[name]=dict(status='not_run',reason='Round 15 fermato prima del freeze: prerequisito di performance fallito; valutazione indipendente non eseguita.',summary=dict(cases=0,metrics={},latency_ms={}))
    latest['fingerprint_coverage']=dict(status='executed',operational_docs_total=cov['operational_total'],file_backed_operational_docs=cov['file_backed_total'],fingerprinted_all_operational_docs=cov['runtime_usable_supported'],coverage_all=cov['all_operational_percent']/100,coverage_file_backed=cov['file_backed_percent']/100,native_coverage=cov['native_supported']/cov['file_backed_total'],legacy_qualified=cov['legacy_qualified'],scope='Frozen support definition v1; shared resource support is distinct from exact identity accuracy.')
    latest['known_canonical']=dict(status='executed',summary=summary(native['cases']+legacy['cases']),native_resources=980,legacy_qualified_resources=27,scope='Fix validation on current runtime; no Round15 release freeze or independent evaluation claimed.')
    latest['performance']=dict(status='executed',scope='Five predetermined runs retained, failed mandatory median gate; no rerun.',reason='Mediane dei percentili dei cinque run warm; p95 oltre il limite di 250 ms. Memoria dell’indice non rimisurata in questo round.',latency_ms=dict(p50=statistics.median(perf['p50']),p95=perf['median_p95']),**perf)
    latest['input_safety']=dict(status='executed',n=inputs['n'],safe_rejects=inputs['safe_rejects'],passed=inputs['passed'])
    latest['truth_adjudication']=dict(confirmed_false_accepts=1,ambiguous=2,actual_catalog_document=0,completed_before_fix=True)
    latest['evaluations']=[dict(name=p.stem,summary=read(p)['summary']) for p in sorted(OUT.glob('historical_*.json')) if 'summary' in read(p)]
    atomic_json(ROOT/'benchmarks/latest_summary.json',latest);load_summary(ROOT/'benchmarks/latest_summary.json')
    table='\n'.join('| '+' | '.join(str(v).replace('|','/') for v in row)+' |' for row in [['Gate','Target','Actual','Esito'],['---']*4]+[[g['gate'],g['target'],'non misurato' if g['actual'] is None else g['actual'],g['status']] for g in gates])
    timing='\n'.join(f"| {i+1} | {a} | {b} |" for i,(a,b) in enumerate(zip(perf['p50'],perf['p95'])))
    report=f'''# Round15 — NOT READY

Software pubblico **0.6.1**, schema **610**, branch `codex/coverage-benchmark-v0.7.0`. Ingresso `{BASE}`, working tree pulito. **Nessun freeze Round15**: il prerequisito performance è fallito. Il freeze Round14 `37a9d1f3125b9e0480d2592f479554fe5ea40a0a` resta storico. Commit finale e SHA dell'archivio nel verificatore esterno `dist/package-verification-round15.json`, per evitare autoreferenze. Nessun push, tag, pubblicazione o RC. CI **external_pending**.

## Adjudication ufficiale

Tre DOCUMENT_MATCH storici, con i due INAIL inclusi nelle tre risorse. **1 confirmed_unknown / falso positivo confermato** (ANAC), **0 actually_catalog_document confermati**, **2 ambiguous_truth** (INAIL), 0 errori di truth esatta dichiarati dimostrati. Per INAIL è dimostrata la qualificazione storica insufficiente come confirmed_unknown: stesso sottotipo di domanda del fondo amianto, annualità2024/2025 diverse dal canonico2023, versione catalogo nulla. Non è dimostrata l'equivalenza di identità tra anni, né una sostituzione ufficiale. Nessuna regola del motore è stata modificata sulla base dei due dubbi. Il fingerprint della pagina condivisa spiega il match, non decide la truth.

La fonte ANAC distingue la bozza normativa di17 pagine dal modulo individuale A.7: nessuna identità/famiglia del catalogo rappresenta la bozza. Fonti, titoli, codici assenti, anni, URL, ricevute SHA e date effettive in `round15_truth_adjudication.json`, `reference_truth_v3.json`, `official_truth_evidence.json`; [adjudication dettagliata](ROUND15_TRUTH_ADJUDICATION.md). ANAC cache HTTP200 del12 ottobre; nessun bypass del403 web o nuova data di download inventata. INAIL pagina moduli acquisita il13 ottobre. Decisioni completate prima del fix, hash del motore di partenza registrato. Tutte le risorse osservate/ambigue escluse dai futuri gate indipendenti.

## Contratto pagine e input-safety

Limite100 pagine preesistente dal commit `059c3168041dbd0fb33a7fba89dee22f4d0b1968`, 6 settembre2026, antenato del freeze Round14; documentato da README/ESTRAZIONE. Rifiuto ExtractionError prima di OCR/riconoscimento. I quattro file Round14 di218/275/217/166 pagine restano nel risultato storico114. Solo nei futuri benchmark si separano classificazione entro i limiti e input-safety fuori limite. L'assenza di preflight adeguato Round14 non viene cancellata.

Input-safety v1: **{inputs['safe_rejects']}/{inputs['n']}**, PASS. Quattro PDF ufficiali oltre100 pagine; upload oltre20MiB; formato non supportato; testo oltre1M caratteri; MIME incompatibile; percorso ZIP/DOCX non valido. **0 crash, 0 residui nella directory temporanea isolata, 0 risultati documento, 0 chiamate recognition**. Ricevute o generatori deterministici e SHA nel manifest; raw degli errori distinti dai NO_MATCH di classificazione. Non è una dimostrazione esaustiva di ogni combinazione dei parser; gli altri limiti restano coperti dai test automatici.

## Fix e regressione

Unica modifica runtime: `_informational_heading` riconosce gli introduttori bozza/schema/proposta, con di facoltativo, prima di un'intestazione informativa esplicita. Risolve la bozza di regolamento accettata tramite fallback titolo/ente. Finestre800 caratteri/prime6 righe, fingerprint, soglie, pesi, ranking, catalogo, fonti, dataset e policy invariati. Nessuna blacklist ID/URL. [Root cause](../benchmarks/results/round15/false_acceptance_root_causes.md). Test del testo ufficiale sul percorso normale/full scan e controesempi di modulo che cita una bozza nel corpo; test mirati16/16.

V2 resta **historical_unknown_release_v2_round14**: **107/114**, 3 DOCUMENT_MATCH, 0 FAMILY_MATCH, 4 errori, con manifest/raw/label/metriche originali intatti. Replay autorizzato separato **development_regression_after_round15_fix**: **{dev['correct_no_match']}/114** sulle label storiche, **{dev['wrong_document_match']} DOCUMENT_MATCH** (due INAIL ambigui), 0 FAMILY_MATCH, 4 errori; ANAC ora NO_MATCH. Non è un release gate, non corregge il107/114 e non trasforma i due ambigui in errori confermati del motore.

Historical safety: **{safety['n']} NO, 0 false acceptance**, R061, cinque ufficiali critici, due casi Round8 e hard negatives PASS. V1/v2 storici distinti, inclusi development33/35 e locked v1 59/69; nessuna etichetta riscritta per ottenere un PASS. Compat v2 37/37; hard negatives30/30 e100/100; family storico161/161.

## Coverage e canonici

Coverage **{cov['runtime_usable_supported']}/{cov['file_backed_total']} = {cov['file_backed_percent']:.6f}%**, PASS>=85. Totale operativo **1002/1212 = {cov['all_operational_percent']:.6f}%**, PASS>=70. Denominatori e definizione congelati. 975 supporti nativi/associazioni storiche più27 legacy qualificate; 33 shared di solo supporto risorsa, non nuova accuratezza di identità. Bundle e catalogo byte-identici all'ingresso. Canonici rieseguiti dopo il fix: **{native['counts']['exact']}/980 nativi, {legacy['counts']['exact']}/27 legacy**, PASS100%, binding e derivazioni verificati.

## Performance e arresto prima del freeze

| Run | p50 ms | p95 ms |
|---|---|---|
{timing}

Mediana p95 **{perf['median_p95']}ms**, FAIL<=250. **{perf['pass_count']}/5** run sotto250; due oltre275, fragilità prudente segnalata. Cinque run prefissati, 402 richieste ciascuno, 67 input/2010 tempi. Warm recognition con contesti nuovi per richiesta, OCR/estrazione separati nei raw; processo isolato durante la misura. Nessun campione eliminato, ottimizzazione o rerun favorevole. Runtime del risultato verificato contro quello finale. Il fallimento impedisce il freeze: la misura non viene sostituita dai247.14ms storici Round14.

## Unknown v3 ed evaluation v5

**Non selezionati e non eseguiti**: stop prima del freeze per prerequisito performance FAIL. Unknown v3 N/fonti/concentrazione/correctreject/falseDOC/falseFAMILY/rate/CI **non misurati**, 0 chiamate release, nessun manifest finale o freeze fittizio. Non si usa v2 development come benchmark indipendente. Registro contaminazione v2 aggiuntivo: {reg['counts']['known_contaminated']} identità known escluse, {reg['counts']['known_eligible']} potenzialmente eleggibili, {reg['counts']['unknown_release_v2']} SHA v2 storici, {reg['counts']['all_previously_observed_resource_shas']} SHA osservati complessivi. Le potenzialmente eleggibili non sono una preflight v5: non ne dimostrano fonti, trasformazioni o validità dei filled.

V5 preflight identità/fonti/rappresentazioni/scans/filled **non misurata**; nessuna selezione/generazione/leakage check/predizione. V5 exact/family/reject/wrong/P/R/errori ente/versione, retrieval@1/@5/@10/@25, scan, filled generation/P/R e unknown end-to-end **non misurati**. Family **experimental / insufficiently validated**: nessuna nuova dimostrazione su>=5 famiglie reali identity-held-out, nessun useful recall gonfiato. Condizione “unknown v3 passa” non soddisfatta; output v5 condizionali non fabbricati.

## Verifiche finali

Baseline pytest **777 passed, 0 failed, 3 skipped**; finale **{tests['passed']} passed, {tests['failed']} failed, {tests['skipped']} skipped**, {tests['seconds']}s. Il primo run completo (784 passed, 1 failed, 3 skipped) è preservato in initial_validation_failure.json: il test Round13 applicava ancora il vincolo dei byte storici al motore corrente. Ora verifica esattamente il commit finale Round13, senza checkout, e un nuovo test AST/byte verifica che il motore corrente differisca soltanto nella funzione di intestazione autorizzata. Nessun cambiamento runtime o di performance per risolvere il test. Un successivo comando mirato ometteva PYTHONPATH dei tool QA (pypdf assente nel solo venv): log preservato, ambiente completo ripristinato per la suite finale. Skip Windows: symlink senza privilegio e due FIFO. SHA log nel test report; Python {platform.python_version()}. Test sintetici, Tesseract locale, integrità e adjudication editoriale distinti; nessun nuovo collaudo Linux/macOS o CI esterna rivendicato.

Compile, SQLite integrity/FK, copia/migrazione schema610 con conteggi invariati, binding, tre validator fingerprint, compat-v2 CLI, schema truth v3 e count/SHA input-safety PASS. Riepilogo finale verificato anche con AppTest: navigazione Benchmark/Catalogo e storico rifiutati, 1/1 PASS. Release-fast effettivo **exit{checks['release_fast_exit']}**, storici EX02/EX03 invariati: **FAIL del requisito zero failures**, nessuna dichiarazione di CLI tutta verde. Verificati {checks['historical_git_blobs_verified']} blob storici e gli archivi Round8–14. Package verification separata controlla ZIP, sorgenti misurati, catalogo, lock storici, nuovi artifact e assenza di file personali/cache/DB di lavoro. I risultati finali sono sul candidato corrente; un freeze Round15 non è stato autorizzato.

## Gate table

{table}

## Limiti e archivio

Limiti reali: performance mandatory FAIL e fragilità, release-fast storico nonzero, due annualità INAIL irrisolte/escluse dai gate, unknown v3 e v5 non misurati, family sperimentale, CI pending. Nessun nuovo catalog record/fonte, nessuna data editoriale inventata; applicazione locale e deterministica, rete confinata al collector maintenance esplicito. Per proseguire in un round successivo servono nuova validazione dei prerequisiti e nuovi corpus indipendenti; il presente round non nasconde il fallimento.

Archivio **dist/BurOCRazia-v0.7.0-candidate-NOT-READY-round15.zip**. SHA256, commit finale e verifica in **dist/package-verification-round15.json** e **.zip.sha256**, esterni al contenuto per evitare autoreferenze. Versione pubblica0.6.1 conservata. Nessuna RC.
'''
    (ROOT/'docs/ROUND15_REPORT.md').write_text(report,encoding='utf8',newline='\n')
    p=ROOT/'docs/BENCHMARK.md';old=p.read_text(encoding='utf8');marker='<!-- round15-current -->';end='<!-- /round15-current -->'
    if marker in old:old=old[old.index(end)+len(end):].lstrip()
    intro=f'''{marker}
# Round15 — NOT READY

Adjudication prima del fix: 1 falso positivo ANAC confermato, 2 annualità INAIL ambigue. Unico fix generale sull'intestazione bozza/schema/proposta; nessun tuning dai dubbi. V2 storico **107/114 immutabile**; replay separato development **108/114**, non release. Limite100 pagine preesistente; input-safety **9/9**. Coverage **86.53%**, canonici **980/980+27/27**, safety **241 NO/0FA**. Cinque run warm: mediana p95 **263.0707ms**, **FAIL**; nessun freeze, unknown v3 o evaluation v5. Pytest **{tests['passed']} passed,0 failed,{tests['skipped']} skipped**; release-fast exit1 storico, CI pending. Software pubblico0.6.1, schema610. [Report Round15](ROUND15_REPORT.md). Le sezioni successive conservano i risultati storici, incluso Round14.
{end}

'''
    p.write_text(intro+old,encoding='utf8',newline='\n')
    save('prepackage_audit',dict(status='NOT READY',identity=ident,freeze=None,independent_release_calls=0,unknown_v2_original_manifest_sha256=sha('benchmarks/manifests/official_unknown_release_v2.json'),unknown_v2_original_observations_sha256=sha('benchmarks/results/round14/unknown_release_v2_observations.json'),historical_unknown_v2_preserved=True,engine_change='General draft informational-heading wrapper only, after official adjudication.',performance_replays=0,checked_at=now()))
    paths=[p for p in OUT.glob('*') if p.suffix in ['.json','.csv','.md'] and p.name!='evidence_locks.json']
    paths.extend(ROOT/p for p in [REGISTRY,'benchmarks/reference/reference_truth_v3.json','benchmarks/reference/round15_truth_adjudication.json','benchmarks/manifests/input_safety_v1.json','benchmarks/schemas/reference_truth_v3.schema.json','docs/ROUND15_BASELINE_AUDIT.md','docs/ROUND15_TRUTH_ADJUDICATION.md','docs/ROUND15_REPORT.md','docs/BENCHMARK.md','docs/release_gates.json','benchmarks/latest_summary.json'])
    save('evidence_locks',dict(baseline_commit=BASE,freeze=None,sha256={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(paths)},historical_original_git_sha256=read(OUT/'historical_locks.json')['historical_original_git_sha256']))
    print('Round15 NOT READY: performance and actual release-fast FAIL; no release freeze/benchmarks',flush=True)

if __name__=='__main__':main()
