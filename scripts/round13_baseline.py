"""Capture R12 evidence and lock support semantics before new recognition."""
from collections import Counter
from datetime import UTC, datetime
import hashlib
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from benchmarks.round3_audit import read
from benchmarks.transactional_writer import atomic_json
from benchmarks.unknown_release import select, validate, balance

BASELINE = '77bbe149a52102d5ca42743702c5b39f5a475326'
OUT = ROOT / 'benchmarks/results/round13'
DEFINITION = ROOT / 'benchmarks/reference/fingerprint_support_definition_v1.json'


def main():
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == BASELINE
    locks = read('benchmarks/results/round12/evidence_locks.json')['sha256']
    for path, sha in locks.items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == sha, path
    bundle = read('data/document_recognition_fingerprints_v3.json')
    native = {r['document_id'] for r in bundle['records'] if r['status'] == 'active'}
    native |= {r['document_id'] for r in read('benchmarks/results/round12/shared_eligibility_audit.json')['cases'] if r['eligible']}
    fixed = {c['document_id'] for c in read('benchmarks/results/round6/resource_audit.json')['cases'] if c['expected_resource_type'] == 'file_backed_document'}
    assert len(native & fixed) == 975 and len(fixed) == 1158
    legacy = read('benchmarks/results/round12/recovery_attempts.json')['derived_legacy_bindings']
    assert len(legacy) == len({c['document_id'] for c in legacy}) == len({c['original_sha256'] for c in legacy}) == 40
    for c in legacy:
        assert c['success'] and c['content_fingerprints'] and not c['runtime_supported']
        assert hashlib.sha256((ROOT / 'benchmarks/cache' / (c['original_sha256'] + '.body')).read_bytes()).hexdigest() == c['original_sha256']
    indexed = {(r['document_id'], r['canonical_file_sha256']) for r in bundle['records'] if r['status'] in ['active', 'shared']}
    assert not any((c['document_id'], c['original_sha256']) in indexed for c in legacy)
    master = validate(read('benchmarks/manifests/official_unknown_master_v1.json'))
    release = validate(read('benchmarks/manifests/official_unknown_release_v1.json'))
    assert [c['case_id'] for c in select(master['cases'])] == [c['case_id'] for c in release['cases']]
    perf = read('benchmarks/results/round12/performance_stability.json')
    assert len(perf['runs']) == 5 and statistics.median(c['latency_ms']['p95'] for c in perf['runs']) == perf['median_p95']
    OUT.mkdir(parents=True, exist_ok=True)
    value = dict(commit=BASELINE, branch='codex/coverage-benchmark-v0.7.0', entry_working_tree='clean, captured before this script',
                 software_version='0.6.1', schema=610, file_backed_total=1158, fingerprint_supported=975,
                 minimum_required=math.ceil(.85 * 1158), shortfall=10,
                 legacy_conversions=40, legacy_distinct_identities=40, legacy_distinct_original_sha256=40,
                 legacy_formats=dict(Counter(c['original_format'] for c in legacy)), technical_sketches_persisted=40,
                 runtime_indexed_legacy=0, legacy_exclusion='R12 sketches persisted only in maintenance evidence; original MIME rejected by v3 source contract. Input support alone is not the correct methodological exclusion.',
                 unknown=balance(release['cases']), unknown_manifest_sha256=hashlib.sha256((ROOT / 'benchmarks/manifests/official_unknown_release_v1.json').read_bytes()).hexdigest(),
                 unknown_selection_seed=release['selection_seed'], unknown_recognition_calls_round12=0,
                 performance_p95=[r['latency_ms']['p95'] for r in perf['runs']], performance_median_p95=perf['median_p95'],
                 performance_preferred_pass_count=perf['pass_count'], performance_required='median p95<=250ms; 4/5 preferred, not mandatory',
                 prior_tests=read('benchmarks/results/round12/tests.json'), locks_verified=len(locks))
    atomic_json(OUT / 'baseline_audit.json', value)
    definition = dict(schema_version=1, definition_id='fingerprint-support-definition-v1',
        file_backed_identity='Operational identity in the immutable R6 file-backed ID set; failures, original legacy MIME and ambiguity do not remove it.',
        fingerprint_supported_identity='Verified source, current binding and persisted indexed technical fingerprint usable on a supported runtime representation. No runtime converter dependency. New legacy eligibility requires deterministic derivation and a correct normal end-to-end fingerprint-channel DOCUMENT_MATCH.',
        shared_resource_supported='Positively adjudicated official resource association, indexed with shared status and conservative identity disambiguation. Resource support is separate from unique identity accuracy. Existing R11/R12 adjudicated shared support is preserved separately; unresolved legacy ambiguity is not newly eligible.',
        runtime_input_format_supported='An input accepted by the unchanged local extraction pipeline (PDF/JPG/PNG/DOCX/TXT and existing aliases); canonical-source format does not imply upload-format support.',
        legacy_canonical_resource='Verified official original DOC/RTF/XLS/XLSX/ODT, original URL/SHA/MIME/date kept. Maintenance-derived PDF statistics are separate from original bytes; no claim that derived PDF is an official exact byte identity.',
        eligible_for_coverage='Native historically audited support UNION distinct qualified legacy IDs. Legacy requires receipt/hash/source association, two equal normalized conversions, persisted index record, current non-rejected/non-shared binding, and correct supported-format end-to-end fingerprint-channel result. Mere conversion, fallback-only match or unresolved ambiguity is insufficient.',
        metric='runtime_usable_fingerprint_supported', native_metric_reported_separately=True,
        denominator_reference='benchmarks/results/round6/resource_audit.json', denominator=1158, operational_denominator=1212,
        gate_percent=85, all_operational_gate_percent=70,
        historical_interpretation='R5 active signatures; R6 introduced >=85% file-backed, not explicit native-only. R10-R12 excluded unindexed legacy candidates operationally, not as a founding native-only metric definition. R11 permitted audited shared resource support.',
        legacy_test='Normal extract_document -> prepare -> recognize_catalog on temporary deterministic PDF; file_sha256 is derived input SHA, different from original canonical SHA. Exact original-SHA shortcut cannot establish the legacy result.',
        performance_gate='Median p95<=250ms mandatory; 4/5 warm runs<=250ms preferred as explicitly specified in R12. No retrospective blocker.',
        immutable_after='Declared before R13 legacy result aggregation; do not change based on measured totals.')
    if DEFINITION.exists():
        assert json.loads(DEFINITION.read_bytes()) == definition, 'Support definition already locked'
    else:
        atomic_json(DEFINITION, definition)
    digest = hashlib.sha256(DEFINITION.read_bytes()).hexdigest()
    lock = OUT / 'support_definition_lock.json'
    if not lock.exists():
        atomic_json(lock, dict(sha256=digest, declared_at=datetime.now(UTC).isoformat(), before_legacy_recognition=True, before_aggregate=True))
    assert read('benchmarks/results/round13/support_definition_lock.json')['sha256'] == digest
    paths = [f'docs/ROUND{n}_REPORT.md' for n in range(5, 13)]
    evidence = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}
    atomic_json(OUT / 'historical_semantics_sources.json', dict(sha256=evidence, definition_sha256=digest))
    (ROOT / 'docs/ROUND13_BASELINE_AUDIT.md').write_text(f'''# Round 13 baseline audit

Branch `codex/coverage-benchmark-v0.7.0`, HEAD `{BASELINE}`, working tree pulito all'ingresso. Pubblico 0.6.1/schema 610. Verificati {len(locks)} lock R12 prima delle modifiche.

Coverage ricalcolata: 975/1158 = 84.196891%, minimo 985, deficit 10. Le 40 conversioni R12 corrispondono a **40 identità distinte e 40 SHA originali distinti**. Formati: `{json.dumps(value['legacy_formats'])}`. Tutte hanno sketch tecnici persistiti nei raw maintenance, ma **zero sono nel dataset/indice runtime**. Il limite non è equivalente a un divieto metodologico di derivare fingerprint da legacy.

Manifest release invariato SHA `{value['unknown_manifest_sha256']}`, seed {value['unknown_selection_seed']}, 105 casi/10 fonti/max 23.809524%. Nessuna predizione R12. Performance R12 verificata: cinque p95 {value['performance_p95']}, mediana 217.8340 ms, 3/5 sotto soglia; 4/5 è preferito. Test precedenti 767 passed/0 failed/3 skipped, senza presentarli come rerun R13.

Definizione fissata prima dei nuovi risultati: `{digest}`. Ogni nuovo supporto legacy dovrà superare l'intero audit e una prova runtime normale su formato supportato; conversione e persistenza da sole non bastano.
''', encoding='utf8', newline='\n')
    (ROOT / 'docs/FINGERPRINT_COVERAGE_SEMANTICS.md').write_text(f'''# Semantica della fingerprint coverage

La metrica di gate Round 13 è **runtime-usable fingerprint support**. Non è supporto upload legacy. Il denominatore rimane 1158 file-backed operative, totale operativo 1212. La metrica canonical-native viene riportata a parte, senza riscrivere le serie storiche.

## Evidenza storica, esaminata prima dei nuovi risultati

- Round 5, sezione 2: «firme attive 369/1212», target 70%, preferito 85%. Non definisce native-only.
- Round 6, sezione 2 e gate: «firme attive per 948 identità», file-backed >=85%. Il denominatore include gli originali .doc non supportati.
- Round 7, sezione Recupero e copertura: mantiene 1158 e il gate 85%, vietando un denominatore opportunistico delle sole risorse recuperabili.
- Round 8/9 mantengono firme attive e shared separate; nessuna formulazione fondante native-only.
- Round 10, sezione recovery: i derivati sono esclusi perché il bundle v3 allora ammetteva solo PDF/DOCX ufficiali e i candidati non erano attivi. È un limite dell'implementazione, non la definizione iniziale del gate.
- Round 11 autorizza supporto di risorsa shared positivamente associata, separato dall'accuracy univoca.
- Round 12 conserva l'esclusione dei derivati non indicizzati e dichiara 4/5 performance preferito. Il requisito obbligatorio è la mediana p95 <=250 ms.

I documenti Round 5–12 restano intatti; i loro SHA sono in `historical_semantics_sources.json`. Non è stata trovata una definizione storica esplicita «native canonical only». La scelta applica la formulazione funzionale del gate e la precisazione richiesta dal prompt Round 13, senza cambiare soglie o denominatore.

## Definizione bloccata

`benchmarks/reference/fingerprint_support_definition_v1.json`, SHA `{digest}`, bloccata prima della prima prova legacy R13. Native support e supporto runtime usabile sono conteggi separati. Le 33 associazioni shared storiche già adjudicate restano resource-level; nessuna viene spacciata per exact identity. Nuove ambiguità legacy irrisolte restano escluse.

L'originale legacy conserva URL/SHA/MIME/data. Il PDF derivato è solo una rappresentazione di benchmark e una fonte di statistiche tecniche. La normale pipeline runtime deve riconoscere l'identità tramite fingerprint, senza convertitore e senza attribuire al derivato lo SHA di file ufficiale. Nessuna promozione editoriale. Nessun cambiamento della definizione dopo il totale aggregato.
''', encoding='utf8', newline='\n')
    print('R13 baseline and definition locked', digest, value['legacy_formats'], flush=True)


if __name__ == '__main__':
    main()
