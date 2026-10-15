"""Report the corrected candidate without replaying the earlier release set."""
import csv
from datetime import UTC,datetime
import hashlib,json,platform,re,subprocess,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from benchmarks.round3_audit import read
from benchmarks.round8_common import identity
from benchmarks.transactional_writer import atomic_json
from benchmarks.evaluate import summary
from scripts.verify_catalog import verify
from scripts.round13_semantics import check

OUT=ROOT/'benchmarks/results/round13'


def sha(path):return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()


def main():
    cov=read('benchmarks/results/round13/coverage_final.json');unknown=read('benchmarks/results/round13/unknown_release_v1.json')
    invalid=read('benchmarks/results/round13/unknown_binding_invalidation.json');perf=read('benchmarks/results/round13/performance_confirmation.json')
    can=read('benchmarks/results/round13/canonical.json');legacy=read('benchmarks/results/round13/canonical_legacy.json')
    verification=read('benchmarks/results/round13/verification.json');adjud=read('benchmarks/results/round13/legacy_adjudication_observations.json')
    hist={n:read('benchmarks/results/round13/historical_'+n+'.json') for n in ['development_regression','release_locked_v1','release_locked_v2','hard_negatives_v1','hard_negatives_v2','family_release_v3','development_compat_v2','catalog_coverage']}
    no=[c for v in hist.values() for c in v['cases'] if c['expected']['match_type']=='NO_MATCH']
    fa=[c['id'] for c in no if c['observed']['match_type']!='NO_MATCH']
    log=(ROOT/'reports/round13-full-tests.log').read_bytes();m=re.search(rb'(\d+) passed(?:, (\d+) skipped)? in ([\d.]+)s',log)
    assert m and b' failed' not in log and b' error' not in log
    tests=dict(status='passed',passed=int(m[1]),failed=0,skipped=int(m[2] or 0),seconds=float(m[3]),
               python=platform.python_version(),os=platform.platform(),log_sha256=hashlib.sha256(log).hexdigest())
    atomic_json(OUT/'tests.json',tests)
    semantics=check();atomic_json(OUT/'semantic_invariance.json',semantics)
    catalog=verify(ROOT/'data/catalog_seed.sqlite3');assert catalog['integrity']=='ok' and not catalog['foreign_key_violations']
    atomic_json(OUT/'catalog_verification.json',catalog)
    from benchmarks import round8_common
    round8_common.SEED=2026101313;ident=identity()
    assert perf['status']=='complete' and len(perf['runs'])==5
    for artifact in [perf,can,legacy]:
        for key in ['runtime_sha256','code_sha256','fingerprint_sha256']:assert artifact['identity'][key]==ident[key],key
    assert not adjud['wrong_document_accepts']
    binding_current=unknown['identity']['fingerprint_sha256']==ident['fingerprint_sha256']
    assert not binding_current and invalid['release_replay'] is False
    r061=next(c for c in hist['release_locked_v2']['cases'] if c['id']=='R061')
    two=[c for c in hist['development_compat_v2']['cases'] if c['id'] in ['EX02MISSINGREV','EX03MISSINGREV']]
    safety=len(no)==241 and not fa and r061['observed']['match_type']=='NO_MATCH' and len(two)==2 and all(c['observed']['match_type']=='NO_MATCH' for c in two) and verification['historical_five_passed']
    canonical=can['counts']['exact']==len(can['cases'])==980 and legacy['counts']['exact']==len(legacy['cases'])==cov['legacy_eligible_count']
    checks=dict(coverage_definition=cov['coverage_definition'],coverage_percent=cov['runtime_usable_percent'],coverage_pass=cov['pass'],
                unknown_release_count=unknown['actual_count'],unknown_sources=unknown['selection']['sources'],
                unknown_max_concentration=unknown['selection']['max_concentration'],unknown_rejection_rate=unknown['rejection_rate'],
                unknown_pass=unknown['passed'] and binding_current,canonical_pass=canonical,historical_safety_pass=safety,
                performance_median_p95=perf['median_p95'],performance_pass=perf['required_pass'],tests_pass=True,ready_to_freeze=False)
    atomic_json(OUT/'prerequisite_gate.json',dict(**checks,identity=ident,unknown_measured_pass=unknown['passed'],unknown_binding_current=binding_current,
                unknown_current_candidate_rejection_rate=None,performance_four_of_five_mandatory=False,
                reason='Measured unknown result belongs to the pre-adjudication fingerprint bundle. No replay; corrected candidate lacks a valid bound unknown prerequisite.'))
    atomic_json(OUT/'historical_safety.json',dict(no_observations=len(no),false_accepts=fa,r061=r061['observed'],
                round8_two={c['id']:c['observed'] for c in two},old_five_passed=verification['historical_five_passed'],identity=ident))
    atomic_json(OUT/'freeze_not_created.json',dict(freeze=None,evaluation_v5='not_run',reason='Unknown result not bound to corrected dataset; no single-shot replay.',ready_to_freeze=False))
    gates=[]
    def gate(name,target,actual,passed,blocking=True,status=None):gates.append(dict(gate=name,target=target,actual=actual,passed=passed,blocking=blocking,status=status or ('PASS' if passed else 'NON MISURATO' if actual is None else 'FAIL')))
    gate('runtime_usable_coverage','>=85%',cov['runtime_usable_percent'],cov['pass'])
    gate('all_operational_coverage','>=70%',cov['all_operational_percent'],cov['all_operational_percent']>=70)
    gate('unknown_count','>=100',unknown['actual_count'],unknown['actual_count']>=100)
    gate('unknown_sources','>=8',unknown['selection']['sources'],unknown['selection']['sources']>=8)
    gate('unknown_concentration','<=25%',100*unknown['selection']['max_concentration'],unknown['selection']['max_concentration']<=.25)
    gate('unknown_measured_earlier_candidate','>=99%',100*unknown['rejection_rate'],unknown['passed'],False)
    gate('unknown_current_candidate','>=99%, exact dataset binding',None,False,status='BINDING INVALIDATED / NON MISURATO')
    gate('historical_safety','0 false accepts',len(fa),safety)
    gate('canonical_native','100%',f"{can['counts']['exact']}/980",can['counts']['exact']==980)
    gate('canonical_legacy','100% qualified',f"{legacy['counts']['exact']}/{cov['legacy_eligible_count']}",canonical)
    gate('performance_median_p95','<=250ms',perf['median_p95'],perf['required_pass'])
    gate('performance_four_of_five','preferred>=4/5',perf['pass_count'],perf['pass_count']>=4,False)
    gate('tests','0 failures',dict(passed=tests['passed'],failed=0,skipped=tests['skipped']),True)
    for name,target in [('v5_known_identities','>=30'),('v5_sources','>=6'),('v5_known_representations','>=400'),('v5_scans','>=200'),('v5_valid_fills','>=50'),('v5_unknown_mix','>=30'),('v5_leakage','0 prohibited'),('v5_validity','expected==actual==unique, atomic/schema/SHA'),('v5_precision','>=99.5%'),('v5_exact_recall','>=90%'),('v5_entity_errors','0'),('v5_version_errors','0'),('v5_scan','P>=99.5%,R>=85%'),('v5_filled','generation>=90%,P>=99.5%,R>=90%'),('v5_retrieval','@25=100%, @1 preferred99%'),('v5_unknown_end_to_end','rejection>=99%')]:gate(name,target,None,False)
    gate('family','>=5 qualified real families or experimental','experimental / insufficiently validated',False,False,status='INFO')
    gate('CI','external pending','external_pending',False,False,status='PENDING')
    result=dict(round=13,status='NOT READY',software_version='0.6.1',candidate_target='0.7.0',schema=610,identity=ident,
                freeze=None,local_gates_passed=False,gates=gates,tests=tests,ci='external_pending')
    atomic_json(ROOT/'docs/release_gates.json',result)
    latest=read('benchmarks/latest_summary.json');latest.update(round=13,status='NOT READY',commit=ident['commit'],executed_at=ident['executed_at'],release_gate=result)
    latest['fingerprint_coverage']=dict(status='executed',operational_docs_total=1212,file_backed_operational_docs=1158,
        fingerprinted_all_operational_docs=cov['runtime_usable_fingerprint_supported'],coverage_all=cov['all_operational_percent']/100,
        coverage_file_backed=cov['runtime_usable_percent']/100,native_coverage=cov['native_percent']/100,legacy_qualified=cov['legacy_eligible_count'],
        scope='Frozen definition v1, native plus runtime-usable legacy; shared resource support separated from exact identity accuracy.')
    latest['known_canonical']=dict(status='executed',summary=summary(can['cases']+legacy['cases']),native_resources=980,legacy_qualified_resources=len(legacy['cases']))
    latest['unknown_official']=dict(status='not_run',reason='Current candidate binding invalidated after known-source ambiguity adjudication; earlier result preserved, no replay.',
                                  historical_measurement=dict(n=105,rejection_rate=1.0,fingerprint_sha256=unknown['identity']['fingerprint_sha256']),
                                  summary=dict(cases=0,metrics={},latency_ms={}))
    latest['performance']=dict(status='executed',median_p95=perf['median_p95'],runs=[r['latency_ms'] for r in perf['runs']],pass_count=perf['pass_count'])
    latest['evaluations']=[dict(name=n,summary=v['summary']) for n,v in hist.items()]
    atomic_json(ROOT/'benchmarks/latest_summary.json',latest)
    def table(rows):return '\n'.join('| '+' | '.join(str(c).replace('|','/') for c in row)+' |' for row in rows)
    pt=table([['Run warm','p50 ms','p95 ms','Digital p95','Scan p95'],['---']*5]+[[r['run'],r['latency_ms']['p50'],r['latency_ms']['p95'],r['by_input_group']['representation:digital_pdf']['p95'],r['by_input_group']['historical_scans']['p95']] for r in perf['runs']])
    gt=table([['Gate','Target','Risultato','Esito'],['---']*4]+[[g['gate'],g['target'],'non misurato' if g['actual'] is None else json.dumps(g['actual'],ensure_ascii=False),g['status']] for g in gates])
    body=f'''# Round 13 — NOT READY

Software pubblico **0.6.1**, schema **610**, target candidata **0.7.0**. Branch `codex/coverage-benchmark-v0.7.0`, ingresso HEAD `77bbe149a52102d5ca42743702c5b39f5a475326`, working tree pulito. Commit finale e SHA ZIP sono in `dist/package-verification-round13.json`, esterni all'archivio per evitare autoreferenze. Nessun push, tag o release. CI external_pending.

## Audit legacy e semantica della coverage

40 tentativi su 40 identità e 40 originali distinti: 22 DOC, 1 RTF, 8 XLS, 9 XLSX. Tutte le conversioni sono state ripetute due volte. Normalizzazione di metadati, ID e ordine del grafo degli oggetti PDF; SHA normalizzati uguali nello stesso ambiente/converter/profilo. I PDF restano temporanei e non sono committati; original URL/SHA/MIME/data e derived SHA sono distinti nel manifest ufficiale legacy. Le fingerprint di massimo cinque pagine digital/layout sono persistite; OCR non richiesto e dichiarato come tale. Il runtime non importa il convertitore e non accetta nuovi formati di upload.

La sola validazione del contratto source/provenance v3 è estesa per gli originali legacy. MIME e SHA restano quelli originali, non quelli di un falso PDF ufficiale. Il PDF di test ha SHA derivato diverso: nessun caso legacy passa con `official_file_sha256_exact`. Feature, indice, scoring, ranking, soglie, pesi, fusion, veti e parametri hanno AST/byte invariati rispetto al Round 12, come verificato in `semantic_invariance.json`. Il digest runtime dei byte cambia per il validatore; non si dichiara identità byte del modulo modificato.

Definizione **fissata prima dell'aggregato**: SHA `{cov['definition_sha256']}`. I report Round 5–12 parlano di firme attive/supporto, senza una definizione fondante native-only. Round 10–12 escludevano derivati non indicizzati: limite implementativo, distinto dal supporto upload. Decisione e prove sono in `FINGERPRINT_COVERAGE_SEMANTICS.md`; nessun denominatore ridotto e nessun cambio della definizione dopo i risultati.

Qualificazione iniziale: 28/40. L'adjudicazione incrociata ha poi rilevato due exact errati: 617 e 619 riconosciuti come 618 tramite pagina canonica 2, con canali digital/char/anchor saturati. Sono tre domande diverse con pagina comune; tutti i tre binding sono ora **shared/ambiguous**. Le osservazioni iniziali, CSV iniziale e bundle precedente sono preservati (ricostruzione byte-esatta dai tre record originali). Dopo la correzione: **{cov['legacy_eligible_count']} legacy runtime-usable**, **{cov['legacy_ineligible_count']} esclusi**, zero wrong document nei 40 controlli finali. I casi riconosciuti soltanto dal fallback metadati non sono contati come fingerprint support. Ambiguità irrisolte restano escluse.

Native coverage: **975/1158 = {cov['native_percent']:.6f}%**. Runtime-usable coverage: **{cov['runtime_usable_fingerprint_supported']}/1158 = {cov['runtime_usable_percent']:.6f}%**, incluse 33 associazioni shared storiche di solo supporto risorsa e {cov['legacy_eligible_count']} nuove identità legacy qualificate. Sul totale operativo: {cov['all_operational_percent']:.6f}%. Minimo 985, deficit {cov['exact_shortfall_to_85']}. Gate coverage PASS; native-only resta separato e sotto 85%. Nessun nuovo crawling necessario: `final_recovery.csv` conserva il solo schema perché il deficit è zero. Nessuna nuova fonte o identità di catalogo.

## Unknown release e motivo dello STOP

Manifest immutato SHA `{unknown['manifest_sha256']}`, seed 2026101311: 105 confirmed unknown, 10 fonti, max 23.809524%, 12 categorie. 55 erano già osservati nei round precedenti, 50 non lo erano; nessuna falsa indipendenza rivendicata. Primo single-shot R13 sul bundle **prima** dell'adjudicazione: **105/105 NO_MATCH**, 0 DOCUMENT_MATCH errati, 0 FAMILY_MATCH errati, 0 errori di estrazione, 0 errori ente; rejection 100%, false acceptance 0%. Wilson 95% **96.470592–100%**. Metriche per fonte/categoria nei raw; l'intervallo è descrittivo del set, non una garanzia di popolazione.

Errore nell'ordine del lavoro: il single-shot è stato avviato prima di chiudere il controllo incrociato delle ambiguità legacy. La correzione, motivata esclusivamente dai casi legacy e non dagli esiti unknown, cambia il dataset fingerprint. Bundle misurato `{unknown['identity']['fingerprint_sha256']}`; bundle corretto `{ident['fingerprint_sha256']}`. Il risultato resta valido per il primo bundle e viene conservato integralmente. **Non è stato ripetuto né trasferito al bundle corretto.** Il prerequisito unknown per la candidata corrente è quindi non misurato, `unknown_pass=false`, pur con il precedente rate osservato del 100%. Questo è il blocco del freeze.

Writer transazionale: expected=actual=unique=105, export atomico e SHA `{unknown['observations_sha256']}`. Zero duplicati; journal ignorato da Git. Il risultato e il manifest non sono stati modificati dopo l'apertura degli esiti. Nessuna modifica al motore, alle etichette o alla selezione unknown.

## Safety, canonical e performance

Rerun sulla candidata corretta: **241 NO storici, false accept {len(fa)}**; R061 NO, due casi Round 8 NO, cinque vecchi critici sicuri. Canonical native **{can['counts']['exact']}/980**, legacy qualificati **{legacy['counts']['exact']}/{cov['legacy_eligible_count']}**; shared separate. Le etichette ambigue storiche v1 restano visibili: base 33/35, locked v1 59/69; locked v2 69/69. Nessuna nuova etichetta inventata o promozione editoriale.

Gate storico performance: **mediana p95<=250 ms** obbligatoria; 4/5 run<=250 è preferito, non trasformato in blocker. Cinque run warm confermati sulla candidata corretta, 67 input e 402 richieste per run, passaggi accoppiati avanti/indietro, nuovi RequestPages e feature per richiesta. Stesso corpus/hardware, OCR escluso dal gate.

{pt}

Mediana p95 **{perf['median_p95']:.4f} ms**, massimo **{perf['max_p95']:.4f} ms**, {perf['pass_count']}/5 sotto 250; gate obbligatorio **{'PASS' if perf['required_pass'] else 'FAIL'}**. Nessun run favorevole selezionato, nessun tuning. OCR end-to-end separato sui 14 input sintetici, in ms: `{json.dumps(perf['ocr_end_to_end_ms'])}`. Nessun collaudo su scansioni personali o altre piattaforme rivendicato. Stabilità RSS non dimostrata; limite precedente ancora aperto.

## Prerequisiti, freeze ed evaluation

`{json.dumps(checks)}`. `unknown_binding_current=false`: rate storico misurato e requisito corrente sono distinti. **Nessun freeze, nessun commit freeze, nessuna RC.** Evaluation v5 non selezionata, costruita o eseguita; preflight pool/identità/fonti/rappresentazioni/scansioni/filled/unknown mix non misurati. Exact/family/reject/wrong/P/R, errori ente/versione, retrieval @1/@5/@10/@25, scan, filled generation/recognition e unknown end-to-end non misurati. Nessun valore assente trattato come zero/PASS. Family **experimental / insufficiently validated**, meno di 5 famiglie reali qualificate; non usata per useful recall.

{gt}

## Test, integrità, archivio e limiti

Pytest completo: **{tests['passed']} passed, {tests['failed']} failed, {tests['skipped']} skipped**, {tests['seconds']}s; Python {tests['python']}, {tests['os']}. Log SHA `{tests['log_sha256']}`. Skip Windows: symlink senza privilegio e due FIFO. Test di provenance, input legacy ancora rifiutato, normalizzazione PDF, invarianza scoring e controllo shared; writer interruption/resume/dedupe/count/atomic/SHA coperti dalla suite. Solo verifiche locali; CI external_pending.

Catalog integrity/FK OK, provenance complete; seed SHA `{catalog['sha256']}` invariato, 1216 reali/1212 operativi, 19 fonti, 16 famiglie. I 1028 record fingerprint pre-R13 sono intatti. Corpus e raw storici preservati, archivi Round 8–12 conservati e verificati. Nessun file personale, convertito, database di lavoro o credenziale in Git.

ZIP: `dist/BurOCRazia-v0.7.0-candidate-NOT-READY-round13.zip`. Commit finale/SHA256 nel verificatore esterno e `.zip.sha256`. Limiti effettivi: 13 legacy non qualificati, gruppo Unioncamere ambiguo, unknown corrente senza misura valida legata al dataset, nessuna evaluation v5, family sperimentale, RSS non stabilizzata, CI pending. La coverage metodologicamente corretta passa; la validazione congiunta della candidata resta **NOT READY**.
'''
    (ROOT/'docs/ROUND13_REPORT.md').write_text(body,encoding='utf8',newline='\n')
    intro=f'Round 13 **NOT READY**, versione pubblica 0.6.1, schema 610. Runtime-usable {cov["runtime_usable_fingerprint_supported"]}/1158 = {cov["runtime_usable_percent"]:.6f}%, native 975/1158 = 84.196891%; legacy qualificati {cov["legacy_eligible_count"]}/40. Unknown 105/105 sul bundle precedente, non trasferito alla candidata corretta e non ripetuto; freeze/v5 assenti. p95 mediano {perf["median_p95"]:.4f} ms; test {tests["passed"]} passed, {tests["skipped"]} skipped. [Report Round 13](ROUND13_REPORT.md).'
    for name in ['BENCHMARK.md','FINGERPRINT_COVERAGE_AUDIT.md']:
        p=ROOT/'docs'/name;old=p.read_text(encoding='utf8');start='<!-- round13-current -->';end='<!-- /round13-current -->'
        if start in old:old=old[old.index(end)+len(end):].lstrip()
        p.write_text(start+'\n# Round 13\n\n'+intro+' Le sezioni successive restano storiche.\n'+end+'\n\n'+old,encoding='utf8',newline='\n')
    print('R13 final prerequisites',checks,flush=True)


if __name__=='__main__':main()
