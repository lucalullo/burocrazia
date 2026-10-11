"""Replay real listing observations into an additive staging snapshot, offline."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
from src.database import initialize_database
from src.observation_history import append_observation
from maintenance.build_catalog import verify_continuity

ROOT=Path(__file__).resolve().parents[1]
FIELDS=('titolo_ufficiale','codice','versione','data_pubblicazione','download_url','detail_url','fonte_url')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Use a new staging snapshot')
    a.output.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/'data/catalog_seed.sqlite3',a.output)
    initialize_database(a.output,seed_demo=False)
    observations=json.loads((ROOT/'maintenance/releases/2026-10-11/resource_observations.json').read_text(encoding='utf-8'))
    differences=[];added=0
    with sqlite3.connect(a.output) as db:
        db.row_factory=sqlite3.Row
        for item in observations:
            if not item.get('document_id'):continue
            d=db.execute('SELECT * FROM documents WHERE id=?',(item['document_id'],)).fetchone();o=item['observation']
            metadata={k:o.get(k) for k in FIELDS};metadata.update(resources=o['resources'],publication_status='observed_in_listing',file_sha256=None)
            added+=append_observation(db,document_id=d['id'],source_id=d['source_id'],observed_at=o['acquired_at'],listing_sha256=o['response_sha256'],metadata=metadata,observer='maintenance_https_listing; technical acquisition, not editorial review')
            if item['disposition']=='existing_no_change':
                changes={k:dict(snapshot=d[k],observed=o.get(k)) for k in FIELDS if d[k]!=o.get(k)}
                if changes:differences.append(dict(document_id=d['id'],source_key=item['source_key'],observed_at=o['acquired_at'],changes=changes,action='append observation only; no overwrite, withdrawal or replacement inferred'))
        db.commit()
        verify_continuity(db,json.loads((ROOT/'data/baseline_v061_rows.json').read_text(encoding='utf-8')))
        count=db.execute('SELECT count(*) FROM document_observations').fetchone()[0]
        for item in observations:
            if item.get('document_id'):
                d=db.execute('SELECT * FROM documents WHERE id=?',(item['document_id'],)).fetchone();o=item['observation']
                metadata={k:o.get(k) for k in FIELDS};metadata.update(resources=o['resources'],publication_status='observed_in_listing',file_sha256=None)
                assert not append_observation(db,document_id=d['id'],source_id=d['source_id'],observed_at=o['acquired_at'],listing_sha256=o['response_sha256'],metadata=metadata,observer='maintenance_https_listing; technical acquisition, not editorial review')
        assert db.execute('SELECT count(*) FROM document_observations').fetchone()[0]==count
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and not db.execute('PRAGMA foreign_key_check').fetchall()
    report=dict(schema_version=1,observations_added=added,existing_observation_differences=len(differences),by_field=dict(Counter(k for r in differences for k in r['changes'])),differences=differences,baseline_rows_unchanged=True,idempotent=True,
        limits='Different resource variants/formatting/missing fields are observations, not necessarily replacements or updates. File hashes were not acquired in this historical census. No invented withdrawal/review events.')
    (ROOT/'docs/observation_history_round2.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='differences'},ensure_ascii=False))

if __name__=='__main__':main()
