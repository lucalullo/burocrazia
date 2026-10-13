"""Conservative residual recovery: cached alternatives, containers and legacy audit.

Only native official PDF/DOCX bytes can enter the unchanged v3 contract.
Converted legacy content remains separate when that contract cannot truthfully
represent its original MIME and derived-byte provenance. No engine changes.
"""
import argparse
import csv
from dataclasses import asdict
from datetime import UTC, datetime
import hashlib
from io import BytesIO
import json
from pathlib import Path
import sqlite3
from urllib.parse import unquote, urlsplit
import zipfile

from benchmarks.round3_audit import ROOT, catalog, read
from benchmarks.transactional_writer import atomic_json
from maintenance.fetch import Fetcher
from maintenance.iri import iri_to_uri
from maintenance.policy import validate_url
from maintenance.resolve_resources import SOURCES, sniff, unwrap_multipart, words
from maintenance.round11_resolver import resolve_detail_links
from maintenance.legacy_convert import convert_official
from maintenance.build_fingerprints_v3 import atomic, resource_pages
from src.document_fingerprints import binding
from src.extract import extract_document
from src.fingerprint_v3 import read_bundle, PATH, sketch, page_record
from src.fingerprint_match_v2 import safety_reason
from src.recognize import normalize_text
from src.title_evidence import exact_code_candidates

OUT = ROOT / 'benchmarks/results/round12'
NATIVE = {'application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'}
FIELDS = ['document_id', 'source', 'previous_reason', 'tier', 'action', 'resolver',
          'resource_url', 'final_url', 'mime', 'sha256', 'success', 'fingerprint_built',
          'shared_resource', 'ambiguity_group', 'final_reason']


def single_native_archive(raw):
    """A bounded flat archive with exactly one native document, no active extras."""
    with zipfile.ZipFile(BytesIO(raw)) as z:
        files = [i for i in z.infolist() if not i.is_dir()]
        if len(files) != 1:
            raise ValueError('archive_not_single_native_document')
        info = files[0]
        name = info.filename
        if (name.startswith(('/', '\\')) or '\\' in name or ':' in name
                or '..' in Path(name).parts or info.flag_bits & 1
                or info.file_size > 8 * 1024 * 1024
                or info.compress_size and info.file_size / info.compress_size > 1000
                or (info.external_attr >> 16) & 0o170000 == 0o120000):
            raise ValueError('unsafe_archive_member')
        if Path(name).suffix.lower() not in {'.pdf', '.docx'}:
            raise ValueError('archive_member_not_native')
        body = z.read(info)
        if sniff(body) not in NATIVE:
            raise ValueError('archive_member_magic_mismatch')
        return body, name


def permanent(row):
    text = (row['final_reason'] + ' ' + row['previous_reason']).lower()
    return any(s in text for s in ['permanent', 'robots', 'http_403', 'http_404', 'http_410', 'http_429', 'policy_block'])


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--allow-network', action='store_true')
    p.add_argument('--max-requests', type=int, default=24)
    args = p.parse_args()
    if not 1 <= args.max_requests <= 40:
        p.error('request budget 1..40')
    import maintenance.fetch as fetch_module
    fetch_module.MAX_REQUESTS = args.max_requests
    docs, _ = catalog()
    by = {d.id: d for d in docs}
    old_cov = read('benchmarks/results/round11/coverage_final.json')
    fixed = {c['document_id'] for c in read('benchmarks/results/round6/resource_audit.json')['cases']
             if c['expected_resource_type'] == 'file_backed_document'}
    eligible_before = set(old_cov['eligible_ids'])
    prior = {int(r['document_id']): r for r in csv.DictReader((ROOT / 'benchmarks/results/round11/fingerprint_recovery_plan.csv').open(encoding='utf8'))}
    bundle = read_bundle()
    original = json.loads(json.dumps(bundle))
    existing = {(r['document_id'], r['canonical_file_sha256']) for r in bundle['records']}
    f = Fetcher(ROOT / 'benchmarks/cache', allow_network=args.allow_network, use_cache=True, timeout=8)
    observations = {}
    with sqlite3.connect((ROOT / 'data/catalog_seed.sqlite3').as_uri() + '?mode=ro', uri=True) as db:
        for did, metadata in db.execute('SELECT document_id,metadata_json FROM document_observations ORDER BY observed_at,id'):
            observations.setdefault(did, []).extend(r['url'] for r in json.loads(metadata).get('resources', [])
                                                    if isinstance(r, dict) and isinstance(r.get('url'), str))
    OUT.mkdir(parents=True, exist_ok=True)
    work = ROOT / 'benchmarks/work/round12-legacy'
    private = ROOT / 'tmp-build/round12-legacy-inspection'
    private.mkdir(parents=True, exist_ok=True)
    legacy_old = read('benchmarks/results/round10/legacy_resource_fingerprints.json')
    conversions = {r['original_sha256']: r for r in legacy_old['resources']}
    legacy_done, legacy, attempts, added, rows = {}, [], [], [], []
    for did in sorted(fixed - eligible_before, key=lambda i: (permanent(prior[i]), prior[i]['tier'], i)):
        d, old = by[did], prior[did]
        source = SOURCES[d.source_id]
        tier = 'D' if permanent(old) else 'C' if 'shared' in old['final_reason'] or 'cross_identity' in old['final_reason'] else old['tier']
        row = dict(zip(FIELDS, [did, source, old['final_reason'], tier,
                   'cached alternatives and bounded new official links; legacy preflight audit',
                   'R11 correlated resolver; bounded single-native archive', d.download_url or '', '', '', '',
                   False, False, False, '', old['final_reason']]))
        urls = list(dict.fromkeys(u for u in [d.download_url, *observations.get(did, [])[:64], d.detail_url] if u))
        visited = set()
        while urls and len(visited) < 24:
            url = urls.pop(0)
            try:
                url = validate_url(iri_to_uri(url), source)
                if url in visited:
                    continue
                visited.add(url)
                # Never retry a historical permanent block or legacy primary.
                if url not in f.cached and (permanent(old) or url in [d.download_url, d.detail_url]):
                    continue
                receipt = f.fetch(url, source)
                raw = f.read(receipt)
                mime = sniff(raw)
                event = dict(document_id=did, receipt=asdict(receipt), detected_mime=mime)
                attempts.append(event)
                if mime == 'text/html':
                    urls.extend(u for u in resolve_detail_links(raw, receipt.final_url, source, d) if u not in visited)
                    continue
                raw, outer_sha = unwrap_multipart(raw)
                mime = sniff(raw)
                archive_member = None
                if mime == 'application/zip':
                    try:
                        raw, archive_member = single_native_archive(raw)
                        outer_sha = receipt.sha256
                        mime = sniff(raw)
                    except (ValueError, zipfile.BadZipFile) as exc:
                        event['container_reason'] = str(exc)
                sha = hashlib.sha256(raw).hexdigest()
                row.update(resource_url=url, final_url=receipt.final_url, mime=mime, sha256=sha)
                if mime not in NATIVE:
                    suffix = unquote(urlsplit(url).path).lower()
                    ext = next((x for x in ['.rtf', '.doc', '.xls', '.xlsx', '.odt'] if suffix.endswith(x)), None)
                    previous = conversions.get(sha)
                    if ext and previous and previous.get('success') and url == iri_to_uri(d.download_url or ''):
                        if sha not in legacy_done:
                            try:
                                pdf, meta = convert_official(raw, ext, work)
                                import pymupdf
                                with pymupdf.open(stream=pdf, filetype='pdf') as document:
                                    texts = [page.get_text() for page in document]
                                    # Separate maintenance sketches, deliberately not v3 runtime records.
                                    fingerprints = [page_record(i + 1, text, '', (), ocr_status='unavailable_docx_renderer') for i, text in enumerate(texts)]
                                    for fingerprint in fingerprints:
                                        fingerprint['ocr_status'] = 'not_requested_maintenance_digital_only'
                                text = '\n'.join(texts)
                                (private / (sha + '.txt')).write_text(text[:2000], encoding='utf8')
                                legacy_done[sha] = dict(**meta, success=True, content_fingerprints=fingerprints,
                                                       opening_sha256=hashlib.sha256(text[:2000].encode()).hexdigest())
                                del pdf
                            except (ValueError, OSError, RuntimeError) as exc:
                                legacy_done[sha] = dict(success=False, original_sha256=sha, reason=str(exc))
                        legacy.append(dict(document_id=did, official_receipt=asdict(receipt), **legacy_done[sha],
                                           runtime_supported=False,
                                           eligibility='not_counted: original MIME unsupported; no official PDF/DOCX byte identity'))
                        row['final_reason'] = 'legacy_content_fingerprint_only_original_mime_unsupported'
                    else:
                        row['final_reason'] = 'legacy_prior_failure_or_unsupported_no_blind_retry'
                    continue
                if (did, sha) in existing:
                    continue
                text = extract_document(raw, 'official.pdf' if mime == 'application/pdf' else 'official.docx').text
                reason = safety_reason(text, d, docs, exact=True)
                title = normalize_text(d.titolo_ufficiale.split(' / ')[0])
                strong = not reason and (did in exact_code_candidates(text, [d]) or len(title) >= 20 and f' {title} ' in f' {normalize_text(text[:2000])} ')
                if not strong:
                    row['final_reason'] = reason or 'opening_identity_not_supported'
                    continue
                peers = sorted({r['document_id'] for r in bundle['records'] if r['canonical_file_sha256'] == sha and r['document_id'] != did})
                if peers:
                    row.update(shared_resource=True, ambiguity_group='RESOURCE-' + sha[:16],
                               final_reason='cross_identity_binding_not_added_without_complete_group_adjudication')
                    event['existing_identity_peers'] = peers
                    continue
                path = ROOT / 'benchmarks/cache' / (sha + '.body')
                if not path.exists():
                    path.write_bytes(raw)  # Official native member bytes; ignored cache only.
                rec = dict(document_id=did, source_id=d.source_id, catalog_binding_sha256=binding(d),
                           canonical_file_sha256=sha, mime_type=mime, url=url, final_url=receipt.final_url,
                           acquisition_date=receipt.acquired_at, size_bytes=len(raw))
                data = resource_pages(rec)
                rec.update(generated_at=data['generated_at'], status='active', shared_kind='unambiguous',
                           pages=data['pages'], aggregate=sketch({int(h, 16) for page in data['pages'] for k in ['digital', 'ocr'] for h in page[k]}, 192),
                           field_set=data['field_set'], ocr_metadata=dict(status='generated' if mime == 'application/pdf' else 'unavailable_docx_renderer',
                           container_sha256=outer_sha, archive_member=archive_member, scope='Original official native bytes, unchanged parameters and identity guards.'))
                bundle['records'].append(rec)
                existing.add((did, sha))
                added.append(dict(document_id=did, sha256=sha, receipt=asdict(receipt), container_sha256=outer_sha, archive_member=archive_member))
                row.update(success=True, fingerprint_built=True, final_reason='new_official_native_fingerprint')
                break
            except (ValueError, OSError, RuntimeError) as exc:
                attempts.append(dict(document_id=did, url=url, error=str(exc), status=getattr(exc, 'status', None)))
        rows.append(row)
        if len(rows) % 20 == 0:
            print('R12 residual', len(rows), 'native additions', len(added), 'legacy conversions', len(legacy_done), flush=True)
    assert bundle['records'][:len(original['records'])] == original['records']
    if added:
        atomic(bundle)
    with (OUT / 'fingerprint_recovery.csv').open('w', encoding='utf8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    atomic_json(OUT / 'recovery_attempts.json', dict(attempts=attempts, network_requests=f.requests, budget=args.max_requests,
                allow_network=args.allow_network, native_additions=added, prior_records_preserved=len(original['records']),
                original_bundle_sha256=hashlib.sha256((json.dumps(original, ensure_ascii=False, indent=2) + '\n').encode()).hexdigest(),
                final_bundle_sha256=hashlib.sha256(PATH.read_bytes()).hexdigest(), derived_legacy_bindings=legacy,
                temporary_converted_outputs_deleted=not work.exists() or not list(work.iterdir()),
                scope='No blocked URL retries, engine changes or derived-byte promotion into the native official fingerprint contract.'))
    print('R12 recovery complete', len(rows), 'added', len(added), 'requests', f.requests, flush=True)


if __name__ == '__main__':
    main()
