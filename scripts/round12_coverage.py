"""Fixed-denominator checkpoint and explicit stop before unknown release."""
import csv
from collections import Counter
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from benchmarks.round3_audit import read, catalog
from benchmarks.transactional_writer import atomic_json
from benchmarks.unknown_release import validate, balance, select
from maintenance.resolve_resources import SOURCES
from scripts.round11_coverage import EVIDENCE, REJECT
from src.fingerprint_v3 import read_bundle, public_index
from src.fingerprint_decision_v5 import match
from src.fingerprint_pages import prepare
from src.extract import extract_document
from src.document_fingerprints import binding

OUT = ROOT / 'benchmarks/results/round12'


def release_allowed(coverage):
    return coverage['file_backed_percent'] >= 85 and coverage['all_operational_percent'] >= 70


def main():
    docs, _ = catalog()
    by = {d.id: d for d in docs}
    bundle = read_bundle()
    active = {r['document_id'] for r in bundle['records'] if r['status'] == 'active'}
    supported, audit, tested = set(), [], {}
    public_index()
    for r in bundle['records']:
        if r['status'] != 'shared':
            continue
        did, sha = r['document_id'], r['canonical_file_sha256']
        assert r['catalog_binding_sha256'] == binding(by[did])
        allowed = did in EVIDENCE and did not in REJECT and not (did == 1186 and sha.startswith('319b1ad8773f'))
        if allowed:
            supported.add(did)
        if sha not in tested:
            raw = (ROOT / 'benchmarks/cache' / (sha + '.body')).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == sha
            name = 'shared.pdf' if r['mime_type'] == 'application/pdf' else 'shared.docx'
            ex = extract_document(raw, name)
            result = match(ex.text, docs, file_sha256=sha, pages=prepare(raw, name, ex))
            tested[sha] = dict(sha256=sha, opening_sha256=hashlib.sha256(ex.text[:2000].encode()).hexdigest(),
                               exact_sha_tier=bool(result and 'A_exact_sha' in result.matched_signals),
                               observed_document_id=result.document.id if result and result.recognized else None)
        audit.append(dict(document_id=did, sha256=sha, eligible=allowed, shared_resource=True,
                          ambiguity_group='RESOURCE-' + sha[:16], runtime_status=r['status'],
                          reason=EVIDENCE.get(did) if allowed else REJECT.get(did, 'No eligible association claimed'),
                          additional_signals_required='Unique explicit code, compatible entity/version and sufficient margin; no exact SHA identity.'))
    assert not any(r['exact_sha_tier'] for r in tested.values())
    atomic_json(OUT / 'shared_eligibility_audit.json', dict(cases=audit, fingerprint_policy_observations=list(tested.values()),
                eligibility_ids=sorted(supported),
                scope='R11 eligibility reconstructed from the published policy and checked again. R11 canonical runner overwrote its generic shared_resource_audit.json; that historical file is retained unchanged. This separately named artifact preserves both eligibility and direct policy checks.'))
    fixed = {c['document_id'] for c in read('benchmarks/results/round6/resource_audit.json')['cases']
             if c['expected_resource_type'] == 'file_backed_document'}
    eligible = (active | supported) & fixed
    prior = read('benchmarks/results/round11/coverage_final.json')
    rows = list(csv.DictReader((OUT / 'fingerprint_recovery.csv').open(encoding='utf8')))
    per = {}
    for sid, key in SOURCES.items():
        ids = {d.id for d in docs if d.source_id == sid and d.stato_verifica not in ['demo', 'rifiutato']}
        per[key] = dict(operational_total=len(ids), file_backed_total=len(ids & fixed),
                        fingerprinted=len(ids & eligible), unambiguous=len(ids & active),
                        shared_only=len(ids & (supported - active)), remaining=len(ids & (fixed - eligible)))
    cov = dict(operational_total=1212, file_backed_total=len(fixed), initial_fingerprinted=prior['fingerprinted_file_backed'],
               fingerprinted_file_backed=len(eligible), file_backed_percent=100 * len(eligible) / len(fixed),
               all_operational_percent=100 * len(eligible) / 1212,
               recovered_round12=len(eligible - set(prior['eligible_ids'])),
               unambiguous_identities=len(active & fixed), shared_only_supported=len((supported - active) & fixed),
               per_source=per, remaining_by_reason=dict(Counter(r['final_reason'] for r in rows if int(r['document_id']) not in eligible)),
               eligible_ids=sorted(eligible), derived_legacy_runtime_supported=0,
               scope='Unchanged R6 denominator and R11 support definition. Legacy sketches outside native runtime contract excluded.')
    atomic_json(OUT / 'coverage_final.json', cov)
    if not release_allowed(cov):
        release = validate(read('benchmarks/manifests/official_unknown_release_v1.json'))
        master = validate(read('benchmarks/manifests/official_unknown_master_v1.json'))
        assert {c['case_id'] for c in select(master['cases'])} == {c['case_id'] for c in release['cases']}
        stats = balance(release['cases'])
        atomic_json(OUT / 'unknown_release_v1.json', dict(schema_version=1, status='not_run',
                    reason='Coverage below85%; Round12 section7 prohibits starting the unknown release single-shot.',
                    manifest_sha256=hashlib.sha256((ROOT / 'benchmarks/manifests/official_unknown_release_v1.json').read_bytes()).hexdigest(),
                    selected_count=stats['total'], sources=stats['sources'], max_source_concentration=stats['max_concentration'],
                    selection_seed=release['selection_seed'], previously_recognized=stats['previously_recognized'],
                    actual_count=0, recognition_calls=0, cases=[], correct_no_match=None, wrong_document_match=None,
                    wrong_family_match=None, false_acceptance_rate=None, rejection_rate=None, confidence_interval_95=None,
                    per_source={}, per_document_type={}, scope='No missing metric is represented as zero or PASS; prior exposure retained.'))
    print('R12 coverage', len(eligible), '/', len(fixed), 'unknown release allowed', release_allowed(cov), flush=True)


if __name__ == '__main__':
    main()
