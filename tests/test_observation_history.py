from dataclasses import replace
import sqlite3
import pytest
from src.database import connect_database, initialize_database, SCHEMA_VERSION
from src.observation_history import append_observation, observation_times

def test_migration_preserves_rows_and_is_idempotent(tmp_path):
    path=tmp_path/'catalog.sqlite3';initialize_database(path,seed_demo=False)
    with connect_database(path) as db:
        before=list(db.execute('SELECT * FROM documents'))
        db.execute('DROP TABLE document_observations')
        db.execute('DROP TABLE document_replacements')
        db.execute('DELETE FROM schema_migrations WHERE version=?',(SCHEMA_VERSION,))
        db.execute('PRAGMA user_version=600')
    initialize_database(path,seed_demo=False)
    with connect_database(path) as db:
        assert list(db.execute('SELECT * FROM documents'))==before
        assert db.execute('PRAGMA user_version').fetchone()[0]==SCHEMA_VERSION
        assert db.execute('SELECT count(*) FROM document_observations').fetchone()[0]==0
        assert db.execute('PRAGMA foreign_key_check').fetchall()==[]

def test_observations_are_append_only_and_retry_is_idempotent(tmp_path):
    path=tmp_path/'catalog.sqlite3';initialize_database(path,seed_demo=True)
    with connect_database(path) as db:
        # Demo source/document are a synthetic fixture; not historical official evidence.
        row=db.execute('SELECT id,source_id FROM documents LIMIT 1').fetchone()
        if row['source_id'] is None:
            sid=db.execute('SELECT id FROM sources LIMIT 1').fetchone()[0]
            db.execute('UPDATE documents SET source_id=? WHERE id=?',(sid,row['id']))
        else:sid=row['source_id']
        kw=dict(document_id=row['id'],source_id=sid,observed_at='2026-10-11T12:00:00+00:00',listing_sha256='a'*64,metadata={'versione':'fixture-1'},observer='synthetic test')
        assert append_observation(db,**kw)
        assert not append_observation(db,**kw)
        assert append_observation(db,**dict(kw,metadata={'versione':'fixture-2'}))
        assert observation_times(db,row['id'])['last_seen']==kw['observed_at']
        with pytest.raises(sqlite3.IntegrityError,match='append-only'):db.execute('UPDATE document_observations SET observer=?',('changed',))
        with pytest.raises(sqlite3.IntegrityError,match='append-only'):db.execute('DELETE FROM document_observations')
        with pytest.raises(ValueError):append_observation(db,**dict(kw,source_id=9999))
        with pytest.raises(ValueError):append_observation(db,**dict(kw,observer=''))
        with pytest.raises(ValueError):append_observation(db,**dict(kw,listing_sha256='invalid'))

@pytest.mark.parametrize('identifier',[429,1077,1081,1091])
def test_confirmed_informational_record_is_retained_with_technical_rejection(identifier):
    from pathlib import Path
    from src.recognize import recognize_catalog
    from src.database import list_documents
    from src.families import list_document_families
    root=Path(__file__).resolve().parents[1]
    with connect_database(root/'data/catalog_seed.sqlite3') as db:
        doc=db.execute('SELECT * FROM documents WHERE id=?',(identifier,)).fetchone()
        assert doc['stato_verifica']=='rifiutato'
        event=db.execute("SELECT * FROM review_events WHERE entity_type='document' AND entity_id=?",(identifier,)).fetchone()
        assert event['reviewer']=='Codex - audit tecnico automatico Round 2' and event['decision']=='rifiutato'
        assert 'SHA-256' in event['notes'] and 'non revisione umana' in event['notes']
        result=recognize_catalog(doc['ente']+'\n'+doc['titolo_ufficiale'],list_documents(db),list_document_families(db))
        assert not result.document or result.document.id!=identifier

def test_faq_is_never_imported_as_a_form():
    from maintenance.parsers import classify
    assert classify('Faq interventi del modello OT23 /2027',collection_is_forms=True)=='other'
