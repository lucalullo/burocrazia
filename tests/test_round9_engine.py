import json,random
from dataclasses import replace
from pathlib import Path
import pytest
from src.fingerprint_v3 import public_index,features
from src.fingerprint_pages import RequestPages
from src.recognize import recognize_catalog
from benchmarks.round3_audit import catalog,read

@pytest.mark.parametrize('n',['3','4','5'])
@pytest.mark.parametrize('containment',[False,True])
def test_optimized_page_comparison_exactly_equivalent(n,containment):
    ix=public_index();rng=random.Random(909);ids=rng.sample(range(len(ix.pages)),100)
    q=features('INPS Richiesta di pensione e dichiarazione dati personali. '+('Richiesta informazioni amministrative anno 2024. '*30))
    assert ix.page_scores(q,ids,n,containment)==ix.page_scores_reference(q,ids,n,containment)
    # Dense adversarial queries include every stored hash; ordering and floats
    # must remain identical even when containment saturates.
    q=dict(tokens=frozenset(h for i in ids for k in ['digital','ocr'] for h in ix.pages[i][k]),chars={n:frozenset(h for i in ids for h in ix.pages[i]['chars'][n])},anchors=frozenset(h for i in ids for h in ix.pages[i]['anchors']))
    assert ix.page_scores(q,ids,n,containment)==ix.page_scores_reference(q,ids,n,containment)

def test_candidate_index_does_not_depend_on_scoring_ngram():
    ix=public_index();q=features('Modulo INPS dichiarazione amministrativa '*20)
    assert ix.candidates(q,'3')==ix.candidates(q,'4')==ix.candidates(q,'5')
    assert set(ix.candidates(q))<=set(ix.candidates(q,reference=True))

@pytest.mark.parametrize('case_id',['EX02MISSINGREV','EX03MISSINGREV'])
def test_historical_missing_revision_is_conservative_for_any_id(case_id):
    docs,families=catalog();cc=next(c for c in read('tests/fixtures/benchmark_v2.json')['cases'] if c['id']==case_id)
    assert recognize_catalog(cc['text'],docs,families).match_type=='NO_MATCH'
    did=13 if case_id=='EX02MISSINGREV' else 12;d=next(d for d in docs if d.id==did)
    assert recognize_catalog(cc['text'],[replace(d,id=99001)],[]).match_type=='NO_MATCH'
    r=recognize_catalog(cc['text']+'\nVersione '+d.versione,[replace(d,id=99001)],[])
    assert r.match_type=='DOCUMENT_MATCH' and r.document.id==99001

def test_v5_conflicting_revision_and_entity_never_exact(monkeypatch):
    import src.fingerprint_decision_v5 as policy
    from tests.test_round8 import document,record,index,TEXT
    d=document();r=record(d);ix=index([r])
    monkeypatch.setattr('src.fingerprint_decision_v4.public_index',lambda:ix)
    assert policy.match(TEXT,[d],file_sha256=r['canonical_file_sha256']).document.id==d.id
    assert policy.match(TEXT.replace('Versione 1.0','Versione 2.0'),[d],file_sha256=r['canonical_file_sha256']) is None
    assert policy.match(TEXT.replace('INPS','INAIL'),[d],file_sha256=r['canonical_file_sha256']) is None
    assert policy.match(TEXT.split('Versione')[0],[d]) is None
    assert policy.match(TEXT,[d]).document.id==d.id

def test_v5_shared_bytes_cannot_choose_identity(monkeypatch):
    import src.fingerprint_decision_v5 as policy
    from tests.test_round8 import document,record,index,TEXT
    d=document();e=replace(d,id=9002,codice=None);sha='a'*64
    monkeypatch.setattr('src.fingerprint_decision_v4.public_index',lambda:index([record(d,sha=sha,status='shared'),record(e,sha=sha,status='shared')]))
    assert policy.match(TEXT.replace('TEST-81',''),[d,e],file_sha256=sha) is None
