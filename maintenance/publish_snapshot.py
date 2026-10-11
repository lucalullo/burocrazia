"""Publish an audited candidate seed; operational databases are never opened."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3

from maintenance.build_catalog import verify_continuity
from maintenance.policy import validate_url
from src.local_resources import RESOURCE_ROOT_KEY

ROOT=Path(__file__).resolve().parents[1]


def publish(staging,apply=False):
    audit=json.loads((staging/'audit.json').read_text(encoding='utf-8'))
    if not audit['baseline_rows_unchanged'] or not audit['idempotent']:raise ValueError('Audit incompleto')
    baseline=json.loads((ROOT/'data/baseline_v061_rows.json').read_text(encoding='utf-8'))
    observations=json.loads((staging/'resource_observations.json').read_text(encoding='utf-8'))
    with closing(sqlite3.connect(staging/'candidate.sqlite3')) as db:
        db.row_factory=sqlite3.Row
        verify_continuity(db,baseline)
        for r in observations:
            for name in ['fonte_url','detail_url','download_url']:
                if r['observation'].get(name):validate_url(r['observation'][name],r['source_key'])
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert not db.execute('PRAGMA foreign_key_check').fetchall()
        assert not db.execute("SELECT 1 FROM documents d LEFT JOIN document_provenance p ON p.document_id=d.id WHERE d.stato_verifica<>'demo' AND p.id IS NULL").fetchone()
        counts={t:db.execute(f'SELECT count(*) FROM {t}').fetchone()[0] for t in baseline['tables']}
        real=db.execute("SELECT count(*) FROM documents WHERE stato_verifica<>'demo'").fetchone()[0]
    if not apply:return counts
    seed=ROOT/'data/catalog_seed.sqlite3'
    temporary=staging/'public.sqlite3'
    with closing(sqlite3.connect(staging/'candidate.sqlite3')) as source, closing(sqlite3.connect(temporary)) as target:
        source.backup(target)
        # Installation-specific path is not part of the public catalog.
        if target.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='catalog_metadata'").fetchone():
            target.execute('DELETE FROM catalog_metadata WHERE key=?',(RESOURCE_ROOT_KEY,));target.commit()
        target.execute('VACUUM')
        target.row_factory=sqlite3.Row;verify_continuity(target,baseline)
    shutil.copy2(temporary,seed)
    manifest=dict(catalog_version='2026.10.11-candidate',source='Acquisizione tecnica da fonti ufficiali; confronto per riga con v0.6.1; nessuna nuova revisione umana',
        sha256=hashlib.sha256(seed.read_bytes()).hexdigest(),tables=counts,real_documents=real,demo_documents=10,local_official_resources=0,
        baseline_sha256=baseline['seed_sha256'],acquisition_package_sha256=audit['package_sha256'])
    (ROOT/'data/catalog_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    destination=ROOT/'maintenance/releases/2026-10-11';destination.mkdir(parents=True,exist_ok=True)
    for name in ['records.json','manifest.json','audit.json','resource_observations.json']:shutil.copy2(staging/name,destination/name)
    return counts


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('staging',type=Path);p.add_argument('--apply',action='store_true');a=p.parse_args()
    print(json.dumps(publish(a.staging,a.apply)))
