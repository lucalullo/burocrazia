"""Offline, append-only package construction from hash-checked observations.

Never writes the public seed: the maintainer publishes the verified candidate.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, fields
from datetime import UTC, date, datetime
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import zipfile

from maintenance.fetch import Fetcher, Fetched
from maintenance.parsers import parse, merge_observations
from maintenance.policy import validate_url
from src.database import initialize_database, connect_database
from src.local_packages import COLLECTIONS, import_local_package
from src.recognize import normalize_text

ROOT = Path(__file__).resolve().parents[1]


def same_identity(document, item):
    if document['ente'] != item['ente']:
        return False
    same = (normalize_text(document['titolo_ufficiale']) == normalize_text(item['titolo_ufficiale']) or
            bool(item.get('codice') and normalize_text(document.get('codice') or '') == normalize_text(item['codice'])) or
            bool(item.get('download_url') and document.get('download_url') == item['download_url']))
    return same and (item.get('versione') is None or document['versione'] == item['versione'])


def verify_continuity(db, baseline):
    for table, rows in baseline['tables'].items():
        for identifier, digest in rows.items():
            row = db.execute(f'SELECT * FROM {table} WHERE id=?', (identifier,)).fetchone()
            if row is None or hashlib.sha256(json.dumps(dict(row), sort_keys=True, ensure_ascii=False).encode()).hexdigest() != digest:
                raise ValueError(f'Riga storica alterata: {table}/{identifier}')


def replay(report, source, cache):
    items, excluded = [], []
    for receipt in report['pages']:
        fetched = Fetched(**{f.name: receipt[f.name] for f in fields(Fetched)})
        raw = cache.read(fetched)
        try:
            current, skipped = parse(raw, source, receipt)
        except ValueError as exc:
            report=dict(report,coverage_status='blocked',errors=report['errors']+[dict(url=receipt['final_url'],error=str(exc),status=receipt['status'],attempts=receipt['attempts'])])
            continue
        items.extend(current); excluded.extend(skipped)
    merged, duplicates = merge_observations(items)
    return dict(report, observations=merged, excluded=excluded, discovered=len(items)+len(excluded),
                importable=len(merged), duplicates=duplicates, new=0, updated=0, existing=0, deferred=[])


def build(baseline_path, report_paths, output):
    output.mkdir(parents=True, exist_ok=True)
    if (output/'candidate.sqlite3').exists():
        raise ValueError('Usare una cartella staging nuova; il candidato esiste già.')
    sources = {s['key']: s for s in json.loads((ROOT/'maintenance/sources.json').read_text(encoding='utf-8'))}
    cache = Fetcher(ROOT/'maintenance/cache', use_cache=True)
    selected = {}
    for path in report_paths:
        for r in json.loads(path.read_text(encoding='utf-8')):
            selected[r['source_key']] = replay(r, sources[r['source_key']], cache)
    records = {key: [] for key in COLLECTIONS}
    c = sqlite3.connect(baseline_path); c.row_factory = sqlite3.Row
    existing = [dict(row) for row in c.execute('SELECT * FROM documents')]
    source_rows = {row['ente']: dict(row) for row in c.execute('SELECT * FROM sources')}
    c.close()
    resources = []
    for key, report in selected.items():
        source = sources[key]; issuer = source['ente']
        if not report['observations']:
            continue
        if issuer in source_rows:
            records['sources'].append(dict(key=key, existing_id=source_rows[issuer]['id']))
        else:
            records['sources'].append(dict(key=key, ente=issuer, nome_fonte='Raccolta ufficiale '+issuer,
                tipo_ente='ufficio_giudiziario' if key=='giustizia' else 'ente_nazionale', livello='territoriale' if key=='giustizia' else 'nazionale',
                ambito='modulistica', metodo_acquisizione='maintenance_https_package', stato_verifica='da_verificare',
                url_principale=source['urls'][0], url_modulistica=source['urls'][0], attiva=True,
                coverage_status='parziale', note='Acquisizione tecnica; nessuna revisione editoriale umana attribuita.'))
        for item in report['observations']:
            valid_resources=[]
            for resource in item['resources']:
                try: valid_resources.append(dict(resource,url=validate_url(resource['url'],key)))
                except ValueError: report['deferred'].append(dict(title=item['titolo_ufficiale'],reason='invalid_resource_url',url=resource['url']))
            item['resources']=valid_resources
            for field in ['fonte_url','detail_url','download_url']:
                if item.get(field):
                    try: item[field] = validate_url(item[field], key)
                    except ValueError:
                        report['deferred'].append(dict(title=item['titolo_ufficiale'], reason='invalid_'+field, url=item[field]))
                        item[field] = None
            if not item['fonte_url']:
                continue
            # Legacy fields, explanations and review history are never overwritten.
            candidates = [d for d in existing if same_identity(d,item)]
            if candidates:
                if candidates[0]['id'] is None:
                    report['duplicates'] += 1
                    report['importable'] -= 1
                else:
                    report['existing'] += 1
                ref = dict(document_id=candidates[0]['id']) if candidates[0]['id'] is not None else dict(document_key=candidates[0]['key'])
                resources.append(dict(ref, source_key=key, observation=item, disposition='existing_no_change'))
                continue
            # The package importer uses code OR title for identity. Guard both.
            record_key = key+'-'+hashlib.sha256(json.dumps([issuer,item['titolo_ufficiale'],item.get('codice'),item.get('versione')],ensure_ascii=False).encode()).hexdigest()[:20]
            publication = item.get('data_pubblicazione')
            if publication:
                try: date.fromisoformat(publication)
                except ValueError: publication = None
            doc = dict(key=record_key,source_key=key,ente=issuer,titolo_ufficiale=item['titolo_ufficiale'],codice=item.get('codice'),
                categoria=item.get('categoria'),descrizione_ufficiale=item.get('descrizione_ufficiale'),versione=item.get('versione'),
                data_pubblicazione=publication,data_rilevazione=item['acquired_at'][:10],stato_verifica='da_verificare',
                fonte_url=item['fonte_url'],detail_url=item.get('detail_url'),download_url=item.get('download_url'),parole_chiave=[])
            records['documents'].append(doc)
            records['provenance'].append(dict(key=record_key,document_key=record_key,source_key=key,listing_url=item['fonte_url'],
                detail_url=item.get('detail_url'),download_url=item.get('download_url'),acquired_at=item['acquired_at'],last_seen_at=item['acquired_at'],
                content_hash=None,acquisition_method='maintenance_https_listing_sha256_receipt',source_status='rilevato'))
            # Response hash is explicitly distinct from the unavailable file hash.
            resources.append(dict(document_key=record_key,source_key=key,observation=item,disposition='new'))
            existing.append(dict(doc,id=None,versione=item.get('versione')))
            report['new'] += 1
    payload = (json.dumps(records,ensure_ascii=False,indent=2)+'\n').encode()
    manifest = dict(format_version=1,catalog_schema_version=1,package_id='official-census-20261011',package_version='1',
        catalog_version='2026.10.11-candidate',created_at=datetime.now(UTC).isoformat(),producer='BurOCRazia maintenance; technical acquisition only',demo=False,
        files=[dict(path='records.json',size_bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest())],resources=[])
    (output/'records.json').write_bytes(payload)
    (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    package = output/'catalog-update.zip'
    with zipfile.ZipFile(package,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for name in ['manifest.json','records.json']: z.write(output/name,name)
    candidate = output/'candidate.sqlite3'
    shutil.copy2(baseline_path,candidate)
    initialize_database(candidate,seed_demo=False)
    with connect_database(candidate) as db:
        preview = import_local_package(db,package,output/'resources')
        applied = import_local_package(db,package,output/'resources',dry_run=False,expected_sha256=preview.sha256)
        again = import_local_package(db,package,output/'resources',dry_run=False,expected_sha256=preview.sha256)
        assert again.already_imported
        continuity = json.loads((ROOT/'data/baseline_v061_rows.json').read_text(encoding='utf-8'))
        verify_continuity(db,continuity)
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert not db.execute('PRAGMA foreign_key_check').fetchall()
        ids={normalize_text(r['titolo_ufficiale'])+'|'+str(r['versione'])+'|'+r['ente']:r['id'] for r in db.execute('SELECT * FROM documents')}
        records_by_key={r['key']:r for r in records['documents']}
        for r in resources:
            if r.get('document_key'):
                o=records_by_key[r['document_key']]; r['document_id']=ids[normalize_text(o['titolo_ufficiale'])+'|'+str(o['versione'])+'|'+o['ente']]
    for r in selected.values(): r.pop('observations',None)
    audit = dict(package_sha256=preview.sha256,preview=asdict(preview),applied=asdict(applied),idempotent=True,baseline_rows_unchanged=True,sources=list(selected.values()))
    (output/'audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (output/'resource_observations.json').write_text(json.dumps(resources,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return audit


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline',type=Path,required=True);p.add_argument('--reports',type=Path,nargs='+',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();audit=build(a.baseline,a.reports,a.output)
    print(json.dumps(audit['applied']['new_records']))

if __name__=='__main__':main()
