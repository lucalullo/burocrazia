"""Offline fixtures exercise the maintenance boundary, without contacting a PA."""
from dataclasses import asdict
import hashlib
import io
import json
from pathlib import Path
import sqlite3
from urllib.error import HTTPError, URLError

import pytest

from maintenance.fetch import Fetcher, AcquisitionError, Fetched
from maintenance.policy import validate_url
from maintenance.parsers import parse, merge_observations
from maintenance.acquire import collect, main
from maintenance.build_catalog import verify_continuity, same_identity
from benchmarks.evaluate import verify_locks, metrics, bootstrap

ROOT=Path(__file__).resolve().parents[1]
URL='https://www.ispettorato.gov.it/servizio/test/'
SOURCE=dict(key='inl',ente='Ispettorato Nazionale del Lavoro',urls=[URL],forms_collection=True)
RECEIPT=dict(final_url=URL,acquired_at='2026-10-11T10:00:00+00:00',sha256='a'*64)


@pytest.mark.parametrize('url',['http://www.inps.it/x','https://inps.it.evil.example/x','https://user@inps.it/x','https://127.0.0.1/x','https://inps.it:8443/x','https://evil.example/x','https://inps.it/a b'])
def test_hostile_primary_source(url):
    with pytest.raises(ValueError): validate_url(url,'inps')


def test_ipa_domain_is_exact_boundary():
    assert validate_url('https://servizi.comune.example/a','ipa_territorial',ipa_site='http://www.comune.example')
    with pytest.raises(ValueError):validate_url('https://comune.example.evil.test/a','ipa_territorial',ipa_site='https://comune.example')


class Response(io.BytesIO):
    def __init__(self,url,body=b'User-agent: *\nAllow: /',status=200):
        super().__init__(body); self.url=url;self.status=status;self.headers={'Content-Type':'text/html'}


class Opener:
    def __init__(self,operation):self.calls=[];self.operation=operation
    def open(self,request,timeout):
        self.calls.append(request.full_url)
        if request.full_url.endswith('/robots.txt'):return Response(request.full_url)
        return self.operation(request.full_url)


def test_default_does_not_fetch(tmp_path):
    op=Opener(lambda u:Response(u))
    with pytest.raises(AcquisitionError):Fetcher(tmp_path,opener=op).fetch(URL,'inl')
    assert op.calls==[]
    assert main(['--source','inl'])==0


@pytest.mark.parametrize('status',[403,429])
def test_block_is_not_retried(tmp_path,status):
    def fail(u):raise HTTPError(u,status,'blocked',{},None)
    op=Opener(fail);f=Fetcher(tmp_path,allow_network=True,opener=op,sleeper=lambda _:None)
    with pytest.raises(AcquisitionError) as e:f.fetch(URL,'inl')
    assert e.value.status==status
    with pytest.raises(AcquisitionError):f.fetch(URL,'inl')
    assert len(op.calls)==2


def test_timeout_has_one_retry(tmp_path):
    def fail(u):raise URLError('timed out')
    op=Opener(fail)
    with pytest.raises(AcquisitionError) as e:Fetcher(tmp_path,allow_network=True,opener=op,sleeper=lambda _:None).fetch(URL,'inl')
    assert e.value.attempts==2 and len(op.calls)==3


def test_redirect_is_validated_before_request(tmp_path):
    def redirect(u):raise HTTPError(u,302,'redirect',{'Location':'https://evil.test/x'},None)
    op=Opener(redirect)
    with pytest.raises(ValueError):Fetcher(tmp_path,allow_network=True,opener=op,sleeper=lambda _:None).fetch(URL,'inl')
    assert not any('evil.test' in u for u in op.calls)


def test_final_response_url_is_validated(tmp_path):
    with pytest.raises(ValueError):Fetcher(tmp_path,allow_network=True,opener=Opener(lambda _:Response('https://evil.test/a')),sleeper=lambda _:None).fetch(URL,'inl')


def test_cache_hash_and_path(tmp_path):
    f=Fetcher(tmp_path,allow_network=True,opener=Opener(lambda u:Response(u,b'<main>ok</main>')),sleeper=lambda _:None)
    receipt=f.fetch(URL,'inl');assert f.read(receipt)==b'<main>ok</main>'
    (tmp_path/(receipt.sha256+'.body')).write_bytes(b'corrupted')
    with pytest.raises(AcquisitionError):f.read(receipt)
    with pytest.raises(AcquisitionError):f.read(Fetched(**dict(asdict(receipt),sha256='../outside')))


def test_format_and_language_are_resources():
    raw=b'''<main><a href="/x.pdf">INL-31-Modulo-richiesta-intervento PDF, 1 MB</a>
    <a href="/y.docx">INL 31 Modulo richiesta intervento</a>
    <a href="/en.pdf">INL-31-Modulo-richiesta-intervento-inglese</a>
    <a href="https://evil.test/x.pdf">INL 40 Modulo</a>
    <a href="/manual.pdf">Manuale INL 31</a></main>'''
    items,excluded=parse(raw,SOURCE,RECEIPT);merged,n=merge_observations(items)
    assert len(merged)==1 and n==2 and len(merged[0]['resources'])==3
    assert merged[0]['resources'][-1]['language']=='inglese'
    assert len(excluded)==2


def test_law_year_is_not_version():
    items,_=parse(b'<main><a href="/x.pdf">INL 40 Dichiarazione art. 2 legge 2024</a></main>',SOURCE,RECEIPT)
    assert items[0]['versione'] is None
    a=dict(items[0],versione='2024');b=dict(items[0],versione='2025')
    assert len(merge_observations([a,b])[0])==2


def test_inps_changed_structure_fails():
    with pytest.raises(ValueError):parse(b'{"results":[]}',dict(SOURCE,key='inps'),dict(RECEIPT,final_url='https://www.inps.it/list.json'))


def test_all_baseline_rows_preserved():
    baseline=json.loads((ROOT/'data/baseline_v061_rows.json').read_text(encoding='utf-8'))
    with sqlite3.connect((ROOT/'data/catalog_seed.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row;verify_continuity(db,baseline)


def test_corpora_are_frozen():verify_locks()


def test_undefined_precision_is_not_100_percent():
    assert metrics([])['document_precision']['value'] is None
    assert bootstrap([])['intervals'] is None


def test_missing_version_does_not_create_another_copy():
    d=dict(ente='INPS',titolo_ufficiale='Domanda di test',codice='SR1',versione='1.2',download_url='https://www.inps.it/a.pdf')
    assert same_identity(d,dict(d,versione=None))
    assert not same_identity(d,dict(d,versione='1.3'))


@pytest.mark.parametrize('identifier',[369,372,376,377])
def test_law_year_does_not_override_revision(identifier):
    from src.database import list_documents
    from src.recognize import recognize_document
    with sqlite3.connect((ROOT/'data/catalog_seed.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row;docs=list_documents(db)
    doc=next(d for d in docs if d.id==identifier)
    result=recognize_document('\n'.join([doc.ente,doc.codice,doc.titolo_ufficiale,'Versione '+doc.versione]),docs)
    assert result.recognized and result.document.id==identifier


def test_challenge_is_not_an_empty_collection():
    with pytest.raises(ValueError,match='blocco/challenge'):
        parse(b'<html><title>Gcore</title></html>',SOURCE,RECEIPT)


class InpsPages:
    def __init__(self,pages):self.pages=pages;self.calls=[];self.bodies={}
    def fetch(self,url,key):
        self.calls.append(url);body=json.dumps(self.pages[len(self.calls)-1]).encode();digest=hashlib.sha256(body).hexdigest();self.bodies[digest]=body
        return Fetched(url,url,RECEIPT['acquired_at'],digest,'application/json',len(body),200,(),1)
    def read(self,receipt):return self.bodies[receipt.sha256]


def test_inps_pagination_runs_until_declared_total():
    pages=[dict(totResult=2,items=[dict(title='SR1',description='Domanda Alfa')]),dict(totResult=2,items=[dict(title='SR2',description='Domanda Beta')])]
    f=InpsPages(pages);r=collect(dict(SOURCE,key='inps',ente='INPS',urls=['https://www.inps.it/it/it/moduli.html']),f)
    assert r['coverage_status']=='complete_for_declared_collection' and r['importable']==2 and len(f.calls)==2


@pytest.mark.parametrize('second',[dict(totResult=2,items=[]),dict(totResult=3,items=[]),dict(totResult=2,items=[dict(title='SR1',description='Domanda Alfa')])])
def test_inps_pagination_inconsistency_is_not_complete(second):
    first=dict(totResult=2,items=[dict(title='SR1',description='Domanda Alfa')])
    r=collect(dict(SOURCE,key='inps',ente='INPS',urls=['https://www.inps.it/it/it/moduli.html']),InpsPages([first,second]))
    assert r['errors'] and r['coverage_status']!='complete_for_declared_collection'


def test_static_summary_limits_and_inert_labels(tmp_path):
    from src.benchmark_display import load_summary, metric_label
    path=tmp_path/'summary.json'
    value=dict(schema_version=1,evaluations=[dict(name='![remote](https://evil.test/a.png)',summary={})])
    path.write_text(json.dumps(value),encoding='utf-8');assert load_summary(path)==value
    assert metric_label(dict(numerator=0,denominator=0)).startswith('Non definito')
    path.write_text('x'*512001)
    with pytest.raises(ValueError):load_summary(path)


def test_entity_lexicon_deduplication_preserves_evidence():
    from src.recognize import _detect_entities, normalize_text
    names=['INPS','INAIL','Agenzia delle Entrate','Agenzia delle Entrate-Riscossione']
    for text in names+['INPS e INAIL','Istituto Nazionale della Previdenza Sociale']:
        assert _detect_entities(normalize_text(text),names)==_detect_entities(normalize_text(text),names*500)


def test_privacy_footer_does_not_identify_another_issuer():
    from src.database import list_documents
    from src.families import list_document_families
    from src.recognize import recognize_catalog
    with sqlite3.connect((ROOT/'data/catalog_seed.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row;docs=list_documents(db);families=list_document_families(db)
    text='SEGNALAZIONE CERTIFICATA DI INIZIO ATTIVITA PER AGENZIE DI VIAGGIO\n'+'Dati della attivita e allegati. '*120
    text+='\nInformativa privacy. Garante per la protezione dei dati personali. RESPONSABILE DELLA PROTEZIONE DEI DATI'
    result=recognize_catalog(text,docs,families)
    assert result.match_type=='NO_MATCH'


def test_catalog_cache_preserves_reference_results(monkeypatch):
    from src import recognize
    from src.database import list_documents
    from src.families import list_document_families
    with sqlite3.connect((ROOT/'data/catalog_seed.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row;docs=list_documents(db);families=list_document_families(db)
    cases=[]
    for name in ['development_regression','release_locked_v1','hard_negatives_v1']:
        cases+=json.loads((ROOT/f'benchmarks/corpora/{name}.json').read_text(encoding='utf-8'))['cases']
    expected=[recognize.recognize_catalog(c['text'],docs,families) for c in cases]
    prepared_directly={d:recognize._catalog_features.__wrapped__(d) for d in docs}
    monkeypatch.setattr(recognize,'_catalog_features',prepared_directly.__getitem__)
    assert expected==[recognize.recognize_catalog(c['text'],docs,families) for c in cases]
