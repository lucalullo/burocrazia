"""Publish an additive history snapshot only after comparing every old row."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
from contextlib import closing
from maintenance.build_catalog import verify_continuity
from scripts.verify_catalog import verify

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('candidate',type=Path);p.add_argument('--apply',action='store_true');p.add_argument('--reviewed-rejection',type=int,action='append',default=[]);a=p.parse_args()
    seed=ROOT/'data/catalog_seed.sqlite3';before=hashlib.sha256(seed.read_bytes()).hexdigest()
    with closing(sqlite3.connect(seed.resolve().as_uri()+'?mode=ro',uri=True)) as old,closing(sqlite3.connect(a.candidate.resolve().as_uri()+'?mode=ro',uri=True)) as new:
        old.row_factory=new.row_factory=sqlite3.Row
        tables=[r[0] for r in old.execute("SELECT name FROM sqlite_master WHERE type='table'") if not r[0].startswith('sqlite_')]
        checked={}
        for table in tables:
            rows=old.execute(f'SELECT * FROM "{table}"').fetchall();actual=[tuple(r) for r in new.execute(f'SELECT * FROM "{table}"')]
            for row in rows:
                if tuple(row) not in actual:
                    if table!='documents' or row['id'] not in a.reviewed_rejection:raise ValueError('Changed historical row in '+table)
                    changed=new.execute('SELECT * FROM documents WHERE id=?',(row['id'],)).fetchone()
                    if changed['stato_verifica']!='rifiutato' or any(row[k]!=changed[k] for k in row.keys() if k!='stato_verifica'):raise ValueError('Only documented status rejection is allowed')
                    events=new.execute("SELECT * FROM review_events WHERE entity_type='document' AND entity_id=? AND decision='rifiutato'",(row['id'],)).fetchall()
                    if not events or not all(e['reviewer'] and e['notes'] for e in events):raise ValueError('Missing rejection author/history')
            if table not in {'schema_migrations','review_events'} and len(rows)!=len(actual):raise ValueError('Unexpected changes in '+table)
            checked[table]=len(rows)
        verify_continuity(new,json.loads((ROOT/'data/baseline_v061_rows.json').read_text(encoding='utf-8')))
    validation=verify(a.candidate)
    if validation['integrity']!='ok' or validation['foreign_key_violations'] or validation['real_documents_without_provenance']:raise ValueError('Invalid candidate')
    report=dict(schema_version=1,before_sha256=before,after_sha256=validation['sha256'],old_tables_rows_compared=checked,documented_status_rejections=a.reviewed_rejection,validation=validation,applied=a.apply)
    if a.apply:
        backup=ROOT/'reports/round2-baseline/catalog_seed.sqlite3';backup.parent.mkdir(parents=True,exist_ok=True)
        if not backup.exists():backup.write_bytes(seed.read_bytes())
        temporary=seed.with_suffix('.sqlite3.tmp');temporary.write_bytes(a.candidate.read_bytes());temporary.replace(seed)
        manifest=json.loads((ROOT/'data/catalog_manifest.json').read_text(encoding='utf-8'))
        manifest.update(catalog_version='2026.10.11-round2-candidate',sha256=validation['sha256'])
        manifest['tables'].update(document_observations=validation['tables']['document_observations'],document_replacements=validation['tables']['document_replacements'])
        manifest['rejected_documents']=validation['rejected_real_documents']
        manifest['active_real_documents']=validation['active_real_documents']
        manifest['history_migration']=dict(schema=610,source_snapshot_sha256=before,kind='Additive actual receipt observations; explicit technical rejection with author/history, no verification or inferred replacement')
        (ROOT/'data/catalog_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'docs/snapshot_history_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':main()
