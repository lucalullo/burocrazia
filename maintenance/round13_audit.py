"""Persist and qualify legacy signatures with normal supported-format recognition."""
from collections import Counter, defaultdict
import csv
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path

from benchmarks.round3_audit import ROOT, read, catalog
from benchmarks.transactional_writer import atomic_json
from benchmarks.round8_common import case_result
from maintenance.round13_legacy import derive_twice, fingerprint_pdf
from maintenance.policy import validate_url
from maintenance.iri import iri_to_uri
from maintenance.resolve_resources import SOURCES
from maintenance.build_fingerprints_v3 import atomic
from src.document_fingerprints import binding
from src.fingerprint_v3 import read_bundle, public_index, revision, PATH
from src.fingerprint_match_v2 import safety_reason
from src.extract import extract_document

OUT = ROOT / 'benchmarks/results/round13'
DEFINITION = ROOT / 'benchmarks/reference/fingerprint_support_definition_v1.json'
FIELDS = ['document_id','source','entity','original_format','original_url','original_sha256','conversion_method',
          'conversion_success','converted_temp_format','converted_sha256','extraction_success','fingerprint_version',
          'fingerprint_persisted','runtime_indexed','stale','rejected','shared_resource','ambiguity_group','provenance_ok',
          'supported_representation_tested','supported_representation_result','eligible_for_fingerprint_coverage','exclusion_reason']


def main():
    definition_sha = hashlib.sha256(DEFINITION.read_bytes()).hexdigest()
    assert read('benchmarks/results/round13/support_definition_lock.json')['sha256'] == definition_sha
    assert not (OUT / 'legacy_fingerprint_audit.csv').exists(), 'Preserve the completed audit'
    original = read_bundle()
    assert len(original['records']) == 1028 and hashlib.sha256(PATH.read_bytes()).hexdigest() == '064b69aea6180ad1a696dc32a65cc3597a5540fefc136a0f8f77e4b665ed3152'
    docs, families = catalog()
    by = {d.id:d for d in docs}
    old = read('benchmarks/results/round12/recovery_attempts.json')['derived_legacy_bindings']
    work = ROOT / 'benchmarks/work/round13-legacy'
    work.mkdir(parents=True, exist_ok=True)
    converted, sources, rows, observations = {}, [], {}, []
    try:
        for number, c in enumerate(old, 1):
            did = c['document_id']
            d = by[did]
            receipt = c['official_receipt']
            row = dict(document_id=did, source=SOURCES[d.source_id], entity=d.ente, original_format=c['original_format'],
                       original_url=receipt['requested_url'], original_sha256=c['original_sha256'],
                       conversion_method='libreoffice-pdf-normalized-v1', conversion_success=False,
                       converted_temp_format='PDF', converted_sha256='', extraction_success=False,
                       fingerprint_version='fingerprint-v3', fingerprint_persisted=False, runtime_indexed=False,
                       stale=False, rejected=False, shared_resource=False, ambiguity_group='', provenance_ok=False,
                       supported_representation_tested=False, supported_representation_result='not_tested',
                       eligible_for_fingerprint_coverage=False, exclusion_reason='')
            rows[did] = row
            try:
                raw = (ROOT / 'benchmarks/cache' / (c['original_sha256'] + '.body')).read_bytes()
                assert hashlib.sha256(raw).hexdigest() == c['original_sha256'] == receipt['sha256']
                assert receipt['status'] == 200 and iri_to_uri(d.download_url) == iri_to_uri(receipt['requested_url'])
                validate_url(iri_to_uri(receipt['requested_url']), row['source'])
                validate_url(receipt['final_url'], row['source'])
                for url in receipt['redirects']: validate_url(url, row['source'])
                row['provenance_ok'] = True
                pdf, meta = derive_twice(raw, c['original_format'], work)
                if len(pdf) > 8 * 1024 * 1024: raise ValueError('normalized_pdf_over_limit')
                ex = extract_document(pdf, 'legacy-derived.pdf')
                reason = safety_reason(ex.text, d, docs, exact=True)
                fp = fingerprint_pdf(pdf)
                path = work / (str(did) + '-supported.pdf')
                path.write_bytes(pdf)
                converted[did] = path
                source = dict(document_id=did, source_id=d.source_id, receipt=receipt, original_size_bytes=len(raw),
                              opening_sha256=hashlib.sha256(ex.text[:2000].encode()).hexdigest(),
                              initial_identity_veto=reason, **meta)
                sources.append(source)
                source['_fingerprint'] = fp
                row.update(conversion_success=True, extraction_success=True, converted_sha256=meta['derived_sha256'],
                           rejected=bool(reason), exclusion_reason=reason or '')
            except (ValueError, OSError, RuntimeError) as exc:
                row['exclusion_reason'] = str(exc)
            print('R13 deterministic conversion', number, '/40', 'ID', did, rows[did]['conversion_success'], flush=True)
        manifest = dict(schema_version=1, manifest_id='official-legacy-fingerprints-v1', definition_sha256=definition_sha,
                        files=[{k:v for k,v in s.items() if k!='_fingerprint'} for s in sources],
                        scope='Verified official original bytes plus deterministic maintenance PDF derivation. No converted bytes distributed. First five digital/layout pages, OCR not requested, unchanged runtime query bound and feature parameters.')
        manifest_path = ROOT / 'benchmarks/manifests/official_legacy_fingerprints_v1.json'
        atomic_json(manifest_path, manifest)
        manifest_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        groups = defaultdict(list)
        for s in sources: groups[s['derived_sha256']].append(s['document_id'])
        bundle = json.loads(json.dumps(original))
        for s in sources:
            did, d = s['document_id'], by[s['document_id']]
            shared = len(groups[s['derived_sha256']]) > 1
            meta = {k:s[k] for k in ['original_format','original_sha256','derived_sha256','derived_mime_type',
                                   'conversion_method','deterministic_conversion','converter_sha256','profile_sha256']}
            meta.update(source_kind='maintenance_derived_legacy', provenance_manifest_sha256=manifest_sha,
                        representation_byte_identity='derived_not_official', full_derived_pages=s['full_derived_pages'],
                        indexed_pages=len(s['_fingerprint']['pages']), status='digital_layout_only_no_ocr')
            record = dict(document_id=did, source_id=d.source_id, catalog_binding_sha256=binding(d),
                          canonical_file_sha256=s['original_sha256'], mime_type=s['original_mime_type'],
                          url=s['receipt']['requested_url'], final_url=s['receipt']['final_url'],
                          acquisition_date=s['receipt']['acquired_at'], generated_at=datetime.now(UTC).isoformat(),
                          size_bytes=s['original_size_bytes'], status='quarantined' if rows[did]['rejected'] else 'shared' if shared else 'active',
                          shared_kind='shared_attachment' if shared else 'unambiguous', ocr_metadata=meta, **s['_fingerprint'])
            bundle['records'].append(record)
            rows[did].update(fingerprint_persisted=True, shared_resource=shared,
                             ambiguity_group='DERIVED-'+s['derived_sha256'][:16] if shared else '')
        # Qualification only removes failed known-source bindings. It never
        # changes scoring or re-enables an excluded case to improve the total.
        for qualification_round in range(1, 42):
            assert bundle['records'][:1028] == original['records']
            atomic(bundle)
            public_index.cache_clear(); revision.cache_clear()
            newly_rejected = []
            for s in sources:
                did = s['document_id']
                record = next(r for r in bundle['records'][1028:] if r['document_id']==did)
                cc = dict(id='L13-'+str(did)+'-supported-pdf', group='document:'+str(did), category='legacy_qualification',
                          expected=dict(match_type='DOCUMENT_MATCH',document_id=did,entity=by[did].ente,version=by[did].versione),
                          label_status='source_association_audited', representation='deterministic_derived_pdf',
                          provenance=dict(document_id=did, original_sha256=s['original_sha256'], derived_sha256=s['derived_sha256'], source_id=s['source_id']))
                observed = case_result(cc, converted[did].read_bytes(), 'legacy-derived.pdf', docs, families)
                assert 'official_file_sha256_exact' not in observed['signals'], 'Derived bytes falsely treated as official original'
                fp_used = 'content_fingerprint_match' in observed['signals'] and 'fingerprint_v3' in observed['signals']
                usable = record['status']=='active' and observed['document_correct'] and fp_used and not observed['extraction_failed']
                observed.update(qualification_round=qualification_round, fingerprint_channel_used=fp_used, eligible=usable,
                                runtime_record_status=record['status'])
                observations.append(observed)
                rows[did].update(runtime_indexed=record['status'] in ['active','shared'], supported_representation_tested=True,
                                 supported_representation_result=observed['observed']['match_type']+':'+str(observed['observed'].get('document_id')),
                                 eligible_for_fingerprint_coverage=usable)
                if record['status']=='active' and not usable:
                    record['status']='quarantined'; rows[did]['rejected']=True
                    rows[did]['exclusion_reason']='normal_supported_representation_not_correct_fingerprint_match'
                    newly_rejected.append(did)
                elif record['status']=='shared': rows[did]['exclusion_reason']='unresolved_legacy_resource_ambiguity'
                elif usable: rows[did]['exclusion_reason']=''
            print('R13 qualification round', qualification_round, 'removed bindings', newly_rejected, flush=True)
            if not newly_rejected: break
        else: raise ValueError('Qualification did not converge')
        assert hashlib.sha256(DEFINITION.read_bytes()).hexdigest() == definition_sha
        with (OUT/'legacy_fingerprint_audit.csv').open('w',encoding='utf8',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=FIELDS,lineterminator='\n');writer.writeheader();writer.writerows(rows.values())
        atomic_json(OUT/'legacy_supported_observations.json',dict(cases=observations, qualification_rounds=qualification_round,
                    final_cases=[c for c in observations if c['qualification_round']==qualification_round],
                    definition_sha256=definition_sha, provenance_manifest_sha256=manifest_sha,
                    bundle_sha256=hashlib.sha256(PATH.read_bytes()).hexdigest(), original_records_preserved=1028,
                    scope='Known-source qualification/development only, not evaluation v5. Normal extraction/recognition, no original-SHA fast path; no scoring, thresholds or truth changes. Failed bindings quarantined monotonically before any release predictions.'))
    finally:
        for path in converted.values():
            if path.exists(): path.unlink()
    atomic_json(OUT/'legacy_temporary_cleanup.json',dict(converted_outputs_deleted=not list(work.iterdir()),temporary_representations_committed=False))
    print('R13 legacy audit finished; per-case evidence persisted', flush=True)


if __name__=='__main__': main()
