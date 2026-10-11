"""Small synthetic signatures; CI needs neither official cache nor network."""
from dataclasses import replace
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3
import pytest
from src.models import AdministrativeDocument
from src.document_fingerprints import (PARAMETERS,VERSION,FingerprintIndex,make_record,
    streams,features,validate,read_bundle,public_index,binding)
from src.fingerprint_match import match
from maintenance.build_fingerprints import atomic_bundle

TEXT='INPS\nModulo TEST Richiesta prestazione sociale\n'+ '\n'.join(
    'Sezione '+str(i)+' generalita richiedente dichiarazione beneficiario indirizzo residenza campo '+str(i)
    for i in range(40))

def document(docid=1,**kw):
    return AdministrativeDocument(id=docid,source_id=2,ente='INPS',codice='TEST',
        titolo_ufficiale='Richiesta prestazione sociale',categoria='modulo',
        descrizione_ufficiale=None,significato_semplice=None,versione=kw.get('versione'),
        data_rilevazione='2026-10-11',stato_verifica=kw.get('stato_verifica','da_verificare'))

def record(d=None,text=TEXT,raw=b'synthetic-official-fixture'):
    return make_record(d or document(),raw,text,
        receipt=dict(acquired_at='2026-10-11T19:00:00+00:00',requested_url='https://www.inps.it/fixture.pdf',final_url='https://www.inps.it/fixture.pdf'),
        mime='application/pdf',page_count=2,method='pdf_text',generated_at='2026-10-11T19:01:00+00:00',field_names=['nome','data'])

def bundle(records=None):return dict(schema_version=1,fingerprint_version=VERSION,parameters=PARAMETERS,records=records if records is not None else [record()])

def test_build_deterministic():
    assert record()==record()
    assert record()['lexical']==sorted(record()['lexical'])
    assert all(len(h)==32 for h in record()['lexical'])
    assert 'richiedente' not in json.dumps(record())

def test_normalization_keeps_years_and_codes():
    a,b=streams('INPS\nAnno 2026 TEST-31\n123456789\fINPS\nAltra pagina\n')
    assert '2026' in a and '31' in b and a.count('inps')==1
    assert '123456789' in b and '123456789' not in a
    assert streams('r i c h i e s t a')[0]==['richiesta']

def test_exact_sha_and_rejected_block():
    d=document();i=FingerprintIndex(bundle());sha=record()['canonical_file_sha256']
    assert match(TEXT,[d],index=i,file_sha256=sha).document==d
    assert match(TEXT,[replace(d,stato_verifica='rifiutato')],index=i,file_sha256=sha) is None

def test_sha_collision_or_shared_attachment_is_ambiguous():
    a=record();b=record(document(2));i=FingerprintIndex(bundle([a,b]))
    assert match(TEXT,[document(),document(2)],index=i,file_sha256=a['canonical_file_sha256']) is None

def test_artificial_shingle_collision_cannot_accept_from_one_hash():
    a=record();h=a['lexical'][0]
    a.update(lexical=[h],header=[h],anchors=[],aware=[])
    i=FingerprintIndex(bundle([a]));q=features('alien unknown fields')
    q['lexical']=frozenset({h});q['header']=frozenset({h})
    assert not any(r['eligible'] for r in i.similarities(q,reference=True))

@pytest.mark.parametrize('version,text',[('2025','INPS\nAnno 2026\n'+TEXT),('1.2','INPS\nVersione 1.3\n'+TEXT)],ids=['annual','revision'])
def test_version_conflict(version,text):
    d=document(versione=version);i=FingerprintIndex(bundle([record(d)]))
    assert match(text,[d],index=i) is None
    assert match(text,[d],index=i,file_sha256=record(d)['canonical_file_sha256']) is None

def test_entity_conflict_cannot_be_overridden():
    i=FingerprintIndex(bundle())
    assert match(TEXT.replace('INPS','INAIL'),[document()],index=i) is None

def test_filled_form_tolerance():
    filled=TEXT.replace('generalita richiedente','generalita richiedente Mario Esempio')+'\nVia Fittizia 17 01/02/2030 importo 1234,50 [X]'
    r=match(filled,[document()],index=FingerprintIndex(bundle()))
    assert r and r.document.id==1

def test_page_subset_containment():
    r=match(TEXT[:2000],[document()],index=FingerprintIndex(bundle()))
    assert r and r.document.id==1

def test_reference_and_candidate_recall():
    i=FingerprintIndex(bundle());q=features(TEXT)
    assert 1 in i.candidates(q)
    a=[r for r in i.similarities(q) if r['eligible']]
    b=[r for r in i.similarities(q,reference=True) if r['eligible']]
    assert a==b

def test_bounded_index_has_no_upload_cache():
    i=FingerprintIndex(bundle());before=deepcopy(i.__dict__)
    for n in range(100):match(TEXT+'\nUtente Fittizio '+str(n),[document()],index=i)
    assert before==i.__dict__

@pytest.mark.parametrize('change',[lambda b:b.update(fingerprint_version='unknown'),lambda b:b['records'][0].update(text='private'),lambda b:b['records'].append(b['records'][0]),lambda b:b['records'][0].update(lexical=['not-a-hash'])])
def test_schema_rejects_invalid(change):
    b=bundle();change(b)
    with pytest.raises(ValueError):validate(b)

def test_atomic_idempotent_and_failed_validation(tmp_path):
    p=tmp_path/'bundle.json';assert atomic_bundle(bundle(),p)
    raw=p.read_bytes();assert not atomic_bundle(bundle(),p)
    with pytest.raises(ValueError):atomic_bundle(dict(records=[]),p)
    assert p.read_bytes()==raw

def test_old_snapshot_compatibility_no_database_migration(tmp_path):
    # A separate versioned data bundle adds no SQL tables or schema mutation.
    source=Path(__file__).parents[1]/'data/catalog_seed.sqlite3'
    before=hashlib.sha256(source.read_bytes()).hexdigest()
    db=tmp_path/'round4.sqlite3';db.write_bytes(source.read_bytes())
    from src.database import list_documents
    with sqlite3.connect(db) as c:
        c.row_factory=sqlite3.Row;docs=list_documents(c)
        tables=c.execute("select name from sqlite_master where type='table'").fetchall()
        for _ in range(2):
            validate(read_bundle());public_index();assert len(list_documents(c))==len(docs)
        assert c.execute("pragma integrity_check").fetchone()[0]=='ok'
        assert not c.execute('pragma foreign_key_check').fetchall()
        assert c.execute("select name from sqlite_master where type='table'").fetchall()==tables
    assert hashlib.sha256(source.read_bytes()).hexdigest()==before

def test_family_identity_split_never_splits_shared_bytes():
    from benchmarks.round5_recognition import split_identities
    cases=[dict(document_id=i,sha256=str(i//2)) for i in range(8)]
    a,b=split_identities(cases)
    assert a and b
    assert not {x['sha256'] for x in a}&{x['sha256'] for x in b}
    assert not {x['document_id'] for x in a}&{x['document_id'] for x in b}
    assert split_identities(cases)==(a,b)

def test_family_macro_and_negatives_are_distinct():
    from benchmarks.evaluate import summary
    from scripts.benchmark import evaluate_case
    from src.models import CatalogRecognitionResult
    c=dict(id='negative',group='outside',category='family_negative',expected=dict(match_type='NO_MATCH'))
    r=evaluate_case(c,CatalogRecognitionResult('NO_MATCH',0,0))
    assert summary([r])['metrics']['unknown_correct_rejection_rate']['value']==1
    assert summary([r])['metrics']['family_precision']['value'] is None

def test_published_schema_and_bundle():
    jsonschema=pytest.importorskip('jsonschema')
    root=Path(__file__).parents[1]
    jsonschema.validate(read_bundle(),json.loads((root/'data/document_recognition_fingerprints.schema.json').read_text()))

@pytest.mark.parametrize('angle',[90,180,270])
def test_real_ocr_rotation_when_tesseract_available(angle):
    import os,shutil
    command=os.environ.get('BUROCRAZIA_TESSERACT_CMD','tesseract')
    if not shutil.which(command) and not Path(command).is_file():pytest.skip('Optional local Tesseract absent')
    from benchmarks.files import generate_synthetic
    from src.extract import extract_document
    text='INPS\nModulo TEST Richiesta prestazione sociale\n'+ '\n'.join(
        'Sezione '+str(i)+' generalita richiedente dichiarazione beneficiario indirizzo residenza' for i in range(6))
    raw=generate_synthetic(dict(text=text,format='PNG',transform=dict(angle=angle)))
    ex=extract_document(raw,'rotation.png');d=document()
    result=match(ex.text,[d],index=FingerprintIndex(bundle([record(d,text=text)])))
    assert ex.used_ocr and result and result.document.id==1
