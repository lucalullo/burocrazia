"""Publish measured Round 12 NOT READY evidence without starting blocked stages."""
from collections import Counter
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import platform
import re
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from benchmarks.round3_audit import read
from benchmarks.transactional_writer import atomic_json
from benchmarks.round4_common import runtime_hash
from benchmarks.evaluate import code_hash
from scripts.round12_coverage import release_allowed
from scripts.verify_catalog import verify

OUT = ROOT / 'benchmarks/results/round12'
BASELINE = 'd911fccae4042c5c720a22d9e8767793a9aec61d'


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def main():
    cov = read('benchmarks/results/round12/coverage_final.json')
    assert not release_allowed(cov), 'Passed coverage requires the real unknown single-shot and subsequent stages'
    perf = read('benchmarks/results/round12/performance_stability.json')
    assert perf['status'] == 'complete' and perf['completed_runs'] == 5
    assert perf['identity']['code_sha256'] == code_hash()
    assert perf['identity']['runtime_sha256'] == runtime_hash()
    assert perf['identity']['fingerprint_sha256'] == sha('data/document_recognition_fingerprints_v3.json')
    assert not subprocess.check_output(['git', 'diff', BASELINE, '--', 'src', 'app.py', 'run.py', 'data'], cwd=ROOT).strip(), 'Runtime or dataset changed'
    unknown = read('benchmarks/results/round12/unknown_release_v1.json')
    assert unknown['status'] == 'not_run' and unknown['recognition_calls'] == 0
    baseline = read('benchmarks/results/round12/baseline_audit.json')
    recovery = read('benchmarks/results/round12/recovery_attempts.json')
    log = (ROOT / 'reports/round12-full-tests.log').read_bytes()
    match = re.search(rb'(\d+) passed(?:, (\d+) skipped)? in ([\d.]+)s', log)
    assert match and b' failed' not in log and b' error' not in log
    tests = dict(status='passed', passed=int(match[1]), failed=0, skipped=int(match[2] or 0), seconds=float(match[3]),
                 python=platform.python_version(), os=platform.platform(), log_sha256=hashlib.sha256(log).hexdigest(),
                 scope='Full local Windows pytest; real local Tesseract where required; symlink privilege and two FIFO skips. No external CI claim.')
    atomic_json(OUT / 'tests.json', tests)
    catalog = verify(ROOT / 'data/catalog_seed.sqlite3')
    assert catalog['integrity'] == 'ok' and not catalog['foreign_key_violations'] and catalog['real_documents_without_provenance'] == 0
    assert catalog['sha256'] == '790b690123c82e1cb7bdfa67a10216284022987d50b0abbcc4a1a245785e3e99'
    atomic_json(OUT / 'catalog_verification.json', catalog)
    safety = read('benchmarks/results/round11/historical_safety.json')
    canonical = read('benchmarks/results/round11/canonical.json')
    assert not safety['false_accepts'] and safety['historical_no_observations'] == 241
    assert canonical['counts']['exact'] == len(canonical['cases']) == 980
    ident = dict(commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                 code_sha256=code_hash(), runtime_sha256=runtime_hash(), fingerprint_sha256=sha('data/document_recognition_fingerprints_v3.json'),
                 seed=2026101312, executed_at=datetime.now(UTC).isoformat())
    retained = dict(status='retained_round11_unchanged_runtime_and_data', post_unknown_rerun=False,
                    historical_no=241, false_accepts=0, r061=safety['r061'], round8_two=safety['round8_two'],
                    old_five_passed=safety['old_five_passed'], canonical_counts=canonical['counts'],
                    historical_safety_sha256=sha('benchmarks/results/round11/historical_safety.json'),
                    canonical_sha256=sha('benchmarks/results/round11/canonical.json'),
                    runtime_sha256=ident['runtime_sha256'], fingerprint_sha256=ident['fingerprint_sha256'],
                    scope='No post-unknown rerun: coverage failed before unknown execution. Prior measured evidence retained only because catalog, runtime and fingerprint bytes are identical. Infrastructure code hash differs and is reported separately.')
    atomic_json(OUT / 'retained_safety_canonical.json', retained)
    checks = dict(coverage_file_backed_percent=cov['file_backed_percent'], coverage_file_backed_pass=cov['file_backed_percent'] >= 85,
                  coverage_all_percent=cov['all_operational_percent'], coverage_all_pass=cov['all_operational_percent'] >= 70,
                  unknown_release_count=unknown['selected_count'], unknown_release_sources=unknown['sources'],
                  unknown_release_max_concentration=unknown['max_source_concentration'],
                  unknown_rejection_rate=None, unknown_rejection_pass=False,
                  historical_safety_pass=True, canonical_pass=True,
                  performance_median_p95=perf['median_p95'], performance_pass=perf['required_pass'],
                  performance_stability_pass=perf['preferred_stability_pass'], tests_pass=True, ready_to_freeze=False)
    atomic_json(OUT / 'prerequisite_gate.json', dict(**checks, identity=ident,
                unknown_status='not_run_coverage_stop', safety_canonical_status=retained['status'],
                performance_stability_required=False, performance_prudent_fragile=perf['prudent_fragile'],
                scope='Unknown pass false means unmeasured, not an observed failed rejection rate. Stability4/5 is preferred; median is mandatory. Coverage independently prohibits freeze.'))
    atomic_json(OUT / 'freeze_not_created.json', dict(status='not_created', freeze=None, evaluation_v5='not_run',
                reason='Coverage below85%; unknown release not started. Performance measurements and tests reported independently.',
                unknown_release_recognition_calls=0))
    gates = []
    def gate(name, target, actual, passed, *, status=None, blocking=True):
        gates.append(dict(gate=name, target=target, actual=actual, passed=passed, blocking=blocking,
                          status=status or ('PASS' if passed else 'NON MISURATO' if actual is None else 'FAIL')))
    gate('coverage_file_backed', '>=85%', cov['file_backed_percent'], checks['coverage_file_backed_pass'])
    gate('coverage_all', '>=70%', cov['all_operational_percent'], checks['coverage_all_pass'])
    gate('unknown_release_count', '>=100 selected', unknown['selected_count'], unknown['selected_count'] >= 100)
    gate('unknown_release_sources', '>=8', unknown['sources'], unknown['sources'] >= 8)
    gate('unknown_release_concentration', '<=25%', unknown['max_source_concentration'], unknown['max_source_concentration'] <= .25)
    gate('unknown_rejection', '>=99%', None, False)
    gate('historical_safety', '0 confirmed false accepts', 0, True, status='PASS R11 / BYTE INVARIATI')
    gate('canonical', '100% unambiguous', '980/980', True, status='PASS R11 / BYTE INVARIATI')
    gate('performance_median_p95', '<=250 ms', perf['median_p95'], perf['required_pass'])
    gate('performance_stability', '>=4/5 p95<=250 ms preferred', perf['pass_count'], perf['preferred_stability_pass'], blocking=False)
    gate('tests', '0 failures', dict(passed=tests['passed'], failed=0, skipped=tests['skipped']), True)
    for name, target in [('v5_known_identities', '>=30'), ('v5_sources', '>=6'), ('v5_representations', '>=400'),
                         ('v5_scans', '>=200'), ('v5_valid_fills', '>=50'), ('v5_unknown_mix', '>=30'),
                         ('v5_leakage', '0 prohibited'), ('v5_validity', 'expected==actual==unique; atomic/schema/SHA'),
                         ('v5_precision', '>=99.5%'), ('v5_exact_recall', '>=90%'), ('v5_wrong_accepted', '<=0.5%'),
                         ('v5_entity_errors', '0'), ('v5_version_errors', '0'), ('v5_scan', 'precision>=99.5%, recall>=85%'),
                         ('v5_filled_generation', '>=90%'), ('v5_filled_recognition', 'precision>=99.5%, recall>=90%'),
                         ('v5_retrieval_at25', '100%; @1 preferred99%'), ('v5_unknown_end_to_end', '>=99% rejection')]:
        gate(name, target, None, False)
    gate('family', '>=5 real identity-held-out families or experimental', 'experimental / insufficiently validated', False, status='INFO', blocking=False)
    gate('CI', 'external pending', 'external_pending', False, status='PENDING', blocking=False)
    release_gates = dict(round=12, status='NOT READY', software_version='0.6.1', candidate_target='0.7.0', schema=610,
                         identity=ident, freeze=None, local_gates_passed=False, gates=gates, tests=tests, ci='external_pending')
    atomic_json(ROOT / 'docs/release_gates.json', release_gates)
    latest = read('benchmarks/latest_summary.json')
    latest.update(round=12, status='NOT READY', commit=ident['commit'], executed_at=ident['executed_at'], release_gate=release_gates)
    latest['fingerprint_coverage'].update(coverage_all=cov['all_operational_percent'] / 100, coverage_file_backed=cov['file_backed_percent'] / 100,
                                        scope=cov['scope'], recovered_round12=cov['recovered_round12'])
    latest['known_canonical'].update(status='retained_round11', scope=retained['scope'])
    for evaluation in latest['evaluations']:
        evaluation['scope'] = 'Retained Round11 evidence; runtime/catalog/fingerprints unchanged; no R12 post-unknown rerun.'
    latest['unknown_official'] = dict(status='not_run', reason=unknown['reason'], selected_count=unknown['selected_count'],
                                      prior_exposure=unknown['previously_recognized'], recognition_calls=0,
                                      summary=dict(cases=0, metrics={}, latency_ms={}))
    latest['performance'] = dict(status='executed', median_p95=perf['median_p95'], pass_count=perf['pass_count'],
                                runs=[r['latency_ms'] for r in perf['runs']], required_pass=perf['required_pass'],
                                preferred_stability_pass=perf['preferred_stability_pass'],
                                scope='Five paired warm runs; median of run p95, not a pooled quantile. OCR separately measured.')
    latest['unknown_development']['status'] = 'retained_round11'
    atomic_json(ROOT / 'benchmarks/latest_summary.json', latest)
    def table(rows):
        return '\n'.join('| ' + ' | '.join(str(cell).replace('|', '/') for cell in row) + ' |' for row in rows)
    pt = table([['Run warm', 'N', 'p50 ms', 'p95 ms', 'Digital p95 ms', 'Scan p95 ms', '<=250 ms'], ['---'] * 7] +
               [[r['run'], r['sample_count'], r['latency_ms']['p50'], r['latency_ms']['p95'],
                 r['by_input_group']['representation:digital_pdf']['p95'], r['by_input_group']['historical_scans']['p95'],
                 'PASS' if r['latency_ms']['p95'] <= 250 else 'FAIL'] for r in perf['runs']])
    def display(g):
        if g['actual'] is None:
            return 'non misurato'
        if g['gate'] in ['coverage_file_backed', 'coverage_all']:
            return f"{g['actual']:.6f}%"
        if g['gate'] == 'unknown_release_concentration':
            return f"{g['actual']:.6%}"
        if g['gate'] == 'performance_median_p95':
            return f"{g['actual']:.4f} ms"
        return json.dumps(g['actual'], ensure_ascii=False) if isinstance(g['actual'], dict) else str(g['actual'])
    gt = table([['Gate', 'Target', 'Risultato', 'Esito'], ['---'] * 4] +
               [[g['gate'], g['target'], display(g), g['status']] for g in gates])
    st = table([['Fonte', 'File-backed', 'Supportate', 'Residue'], ['---'] * 4] +
               [[key, value['file_backed_total'], value['fingerprinted'], value['remaining']] for key, value in cov['per_source'].items()])
    legacy = recovery['derived_legacy_bindings']
    conversions = len({r['original_sha256'] for r in legacy if r.get('success')})
    body = f'''# Round 12 — NOT READY

Software pubblico **0.6.1**, schema **610**, target candidata **0.7.0**. Branch `codex/coverage-benchmark-v0.7.0`. HEAD iniziale `{BASELINE}`, working tree pulito. Commit finale e SHA dell'archivio sono registrati dopo il commit in `dist/package-verification-round12.json`, evitando autoreferenze. Nessun push, tag o release. CI external_pending.

## Decisione e coverage

La copertura resta **{cov['fingerprinted_file_backed']}/1158 = {cov['file_backed_percent']:.6f}%**, inferiore all'85%. Minimo matematico 985, iniziali 975, recuperati **{cov['recovered_round12']}**, deficit **10**. Sul totale operativo: 975/1212 = {cov['all_operational_percent']:.6f}%. Il denominatore R6 è invariato; 942 identità univoche e 33 shared-only, separate dalla canonical accuracy.

Il pass ha esaminato tutti i 183 residui, riusando cache, osservazioni e audit R6–11. Le {recovery['network_requests']} richieste maintenance restano entro il budget di {recovery['budget']}, con allowlist, robots e URL finali verificati. Due osservazioni di URL alternativi INAIL sono state rifiutate dai robots; nessun aggiramento. I formati ZIP sono ammessi solo come contenitore limitato con un unico documento nativo, senza percorsi pericolosi o payload aggiuntivi. Nessun nuovo PDF/DOCX ufficiale ha superato tutte le guardie d'identità.

Sono riuscite {conversions} conversioni locali di legacy primari già acquisiti. Le fingerprint di contenuto derivate sono registrate separatamente con SHA originale, derivato e ricevuta ufficiale; OCR non richiesto per questi sketch digitali. I file convertiti temporanei sono stati eliminati: `{recovery['temporary_converted_outputs_deleted']}`. Nessun testo integrale o file convertito è in Git. Queste conversioni non rendono il MIME originale supportato dal runtime congelato. Il contratto v3 non rappresenta una derivazione come byte canonici ufficiali nativi: non si etichetta il PDF derivato come file ufficiale, né si aggiungono questi sketch al numeratore.

Le nuove associazioni Garante 174/177 richiederebbero una valutazione completa dei gruppi già associati a 175/1213; non sono state promosse soltanto per aumentare il conteggio. Le associazioni shared non pertinenti restano escluse. Il controllo diretto Round 12 sulle risorse shared non osserva tier `A_exact_sha`.

Nel Round 11 il runner canonical aveva riscritto `shared_resource_audit.json` con l'audit generico dei gruppi. Tale raw storico è conservato. Il nuovo `shared_eligibility_audit.json`, con nome distinto, conserva regole pubblicate, binding, gruppi, motivazioni e prove dirette senza essere sovrascritto dal runner.

{st}

## Unknown release

Master **125**, release **105**, **10 fonti**, concentrazione massima **23.809524%**, 12 tipi. Manifest immutato SHA `{unknown['manifest_sha256']}`; seed di selezione **2026101311**. Selezione deterministica per quote e gruppi, ricalcolata identica, indipendente da score o predizioni. Audit confirmed_unknown e relazioni catalogo/famiglie conservati; nessuna risorsa usata per tuning Round 12. L'esposizione storica resta esplicita: **55 già riconosciuti nei round precedenti, 50 mai riconosciuti**.

**Non eseguito**: il punto 7 del prompt vieta di iniziare il single-shot con coverage sotto l'85%. `unknown_release_v1.json` registra status not_run, zero chiamate e metriche null. N selezionato 105, N eseguito 0; correct NO_MATCH, wrong DOCUMENT_MATCH, wrong FAMILY_MATCH, false acceptance rate, rejection rate, CI 95%, metriche per fonte e tipo **non misurate**. Non si usa il risultato development per riempire questo vuoto.

## Historical safety e canonical

Prove misurate Round 11 conservate: **241 NO storici, zero false accept**, R061 e i due NO Round 8 corretti, cinque vecchi casi critici sicuri; canonical **980/980**. Non sono presentate come nuovo rerun post-unknown Round 12: quello stadio non è stato aperto. Runtime, catalogo, fingerprint, soglie, pesi, scoring, ranking, tier, veti e family restano identici byte per byte al Round 11. I nuovi test infrastrutturali e il rerun pytest sono misure separate. Le divergenze storiche delle label v1 rimangono visibili (base 33/35, locked v1 59/69; locked v2 69/69), senza tuning.

## Stabilità performance

Baseline prima delle modifiche: p50 {baseline['performance']['p50']:.4f} ms, p95 **{baseline['performance']['p95']:.4f} ms**, N=402, worker R9 invariato. Seguono esattamente cinque run warm predeterminati nello stesso processo isolato, stesso hardware/corpus: 67 input, sei passaggi accoppiati avanti/indietro per run. Nessuna selezione dei run favorevoli o ottimizzazione del motore. Ogni richiesta ricrea RequestPages, feature e memo locali; solo indice/catalogo pubblici restano warm.

{pt}

**Median p95: {perf['median_p95']:.4f} ms**; gate obbligatorio <=250 ms: **{'PASS' if perf['required_pass'] else 'FAIL'}**. Run sotto soglia: **{perf['pass_count']}/5**; stabilità preferita >=4/5: **{'PASS' if perf['preferred_stability_pass'] else 'FAIL'}**. Run oltre 275 ms: {perf['substantially_over_count']}; fragilità prudenziale dichiarata prima della misura: {perf['prudent_fragile']}. Il valore mediano è la mediana dei cinque p95, non un quantile pooled. Tutti i 2010 tempi individuali, ambiente CPU/processo e marker warm sono nel raw.

Recognition-only esclude estrazione/OCR e include fingerprint dell'input e rendering visuale lazy. Digital e scan recognition-only sono separati nei gruppi di ogni run. OCR end-to-end sui 14 input sintetici storici, in ms: `{json.dumps(perf['ocr_end_to_end_ms'])}`. Il tempo Tesseract non entra nel gate dei 250 ms. Il cambiamento rispetto al p95 Round 11 di 248.23 ms non è attribuito a modifiche semantiche; le condizioni di scheduling e la variazione non sono state isolate sperimentalmente. Nessun collaudo su scansioni personali o altre piattaforme rivendicato.

## Prerequisiti, freeze ed evaluation v5

Tutti i campi richiesti sono in `prerequisite_gate.json`: `{json.dumps(checks)}`. Il gate unknown è non misurato; il suo pass=false non indica una rejection osservata insufficiente. Safety/canonical sono prove conservate su byte invariati. La stabilità 4/5 è preferita, la mediana è obbligatoria. `ready_to_freeze=false`.

Freeze **non eseguito**, commit freeze assente. Evaluation v5 **non costruita né eseguita**: adeguatezza del pool, known identities/fonti/rappresentazioni/scansioni/compilazioni valide/unknown mix non misurati. Exact, family, reject, wrong, precision, recall, errori ente/versione, retrieval @1/@5/@10/@25, scan e filled generation/recognition, unknown end-to-end non misurati. Nessun risultato assente trattato come zero o PASS. Nessuna RC. Family: **experimental / insufficiently validated**, zero famiglie reali identity-held-out qualificabili nel benchmark R9 conservato; non usata per useful recall.

{gt}

## Test e integrità

Suite completa: **{tests['passed']} passed, {tests['failed']} failed, {tests['skipped']} skipped**, {tests['seconds']:.2f} s; Python {tests['python']}, {tests['os']}. Skip: privilegio symlink Windows e due FIFO. Log SHA `{tests['log_sha256']}`. Cinque nuovi test coprono archivi pericolosi, fallimenti permanenti, isolamento delle feature per richiesta, mediana/stabilità e blocco unknown prima del gate coverage. Il writer transazionale già presente è rieseguito nella suite (interruzione, resume, duplicati, count, rename atomico e SHA), senza iniziare evaluation.

Catalog integrity OK, zero violazioni FK, zero documenti reali senza provenance; seed SHA `{catalog['sha256']}`. 1216 reali, 1212 operativi, 19 fonti, 16 famiglie. Nessuna nuova identità/fonte o versione pubblica. CI **external_pending**; soltanto Windows locale verificato. Nessuna validazione editoriale o verifica automatica attribuita ai record.

## Archivio e limiti residui

`dist/BurOCRazia-v0.7.0-candidate-NOT-READY-round12.zip`, da commit locale. Commit finale e SHA256 in `dist/package-verification-round12.json` e `.zip.sha256`, esterni al proprio contenuto. Verifica per byte sorgenti misurati, catalogo, corpus congelati, raw storici, manifest unknown, fingerprint e igiene; archivi Round 8–11 conservati e verificati.

Limiti effettivi: deficit di 10 supporti file-backed; nessuna nuova fingerprint nativa valida; legacy fuori dal contratto runtime; rejection release non misurata per STOP coverage; performance come riportata nei cinque run, senza margine presunto; stabilità RSS non rimisurata e limite Round 11 ancora aperto; nessuna evaluation v5; family sperimentale; CI pending. Il Round 12 non ha chiuso i prerequisiti e conserva lo stato **NOT READY**.
'''
    (ROOT / 'docs/ROUND12_REPORT.md').write_text(body, encoding='utf8', newline='\n')
    intro = f'Round 12 **NOT READY**, pubblico 0.6.1/schema 610. Coverage 975/1158 = {cov["file_backed_percent"]:.6f}%, recuperi 0, deficit 10. Unknown release: 105 selezionati e immutati, zero chiamate per STOP coverage. Median p95 {perf["median_p95"]:.4f} ms, {perf["pass_count"]}/5 run <=250 ms. Test {tests["passed"]} passed/{tests["skipped"]} skipped. Safety/canonical R11 conservati su byte invariati; nessun freeze/v5. Dettagli: [report Round 12](ROUND12_REPORT.md).'
    for name in ['BENCHMARK.md', 'FINGERPRINT_COVERAGE_AUDIT.md']:
        path = ROOT / 'docs' / name
        old = path.read_text(encoding='utf8')
        start, end = '<!-- round12-current -->', '<!-- /round12-current -->'
        if start in old:
            old = old[old.index(end) + len(end):].lstrip()
        path.write_text(start + '\n# Round 12\n\n' + intro + ' Le sezioni successive restano storiche.\n' + end + '\n\n' + old,
                        encoding='utf8', newline='\n')
    print('R12 final gates', checks, flush=True)


if __name__ == '__main__':
    main()
