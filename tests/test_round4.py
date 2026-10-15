"""General safety invariants from historical failures; no held-out v2 text."""
from dataclasses import replace
import json
from pathlib import Path
import pytest
from benchmarks.round4_common import catalog,read
from benchmarks.holdout_leakage import canonical_url,collision,check
from src.recognize import recognize_catalog,recognize_document_family,_issuer_entities,normalize_text

@pytest.fixture(scope='module')
def loaded():return catalog()

def test_segmented_code_over_generic_title(loaded):
    r=recognize_catalog('Ispettorato Nazionale del Lavoro\nPROPOSTA PER IL CONFERIMENTO ONORIFICENZA STELLA AL MERITO DEL LAVORO\nModulo INL 28.1',*loaded)
    assert r.document and r.document.id==1222

@pytest.mark.parametrize('title',['Contributo unificato','Quadro C'])
def test_generic_body_title_not_identity(loaded,title):
    text='Agenzia delle Entrate\nGENERALITA DEL RICHIEDENTE\n'+'Campo da compilare. '*25+'\nRiferimento '+title
    r=recognize_catalog(text,*loaded)
    assert r.match_type=='NO_MATCH'

def test_unversioned_annual_peer_refuses_table_years(loaded):
    r=recognize_catalog('INAIL\nRETRIBUZIONI MEDIE GIORNALIERE PER GRANDE GRUPPO DI LAVORAZIONE\n2022\n2023\n2024',*loaded)
    assert r.match_type=='NO_MATCH'

def test_exclusive_qualifiers_override_technical_anchors(loaded):
    from src.technical_anchors import load_features
    feature=next(f for f in load_features() if f['document_id']==441)
    text='Tribunale di Venezia\nDichiarazione di assenso alla nomina tutore\n'+' '.join(feature['anchor_tokens'])
    r=recognize_catalog(text,*loaded)
    assert not r.document or r.document.id!=441

@pytest.mark.parametrize('tail',[
 'Avviso di addebito INPS\navviso di addebito inps\navviso di addebito',
 'Avviso di addebito INPS\nINPS\nInformazioni generiche',
 'Avviso di addebito\nAvviso di addebito INPS\nAnno 2026',
 'Guida\nAvviso di addebito INPS\ncrediti previdenziali',
])
def test_r061_near_negatives_have_no_independent_debt_context(loaded,tail):
    assert recognize_catalog('Agenzia delle Entrate-Riscossione\n'+tail,*loaded).match_type=='NO_MATCH'

def test_r061_positive_and_wrong_issuer(loaded):
    docs,families=loaded;body='Avviso di addebito INPS\ncrediti previdenziali\nAnno 2025'
    r=recognize_document_family('Agenzia delle Entrate-Riscossione\n'+body,families)
    assert r.family and r.family.id==4
    assert not recognize_document_family('INAIL\n'+body,families).recognized

@pytest.mark.parametrize('issuer,mention',[
 ('Agenzia delle Entrate-Riscossione','Agenzia delle Entrate'),
 ('INAIL','INPS'),
 ('Ministero delle Imprese e del Made in Italy','Ministero del Lavoro'),
 ('Comune di Esempio Alfa','Regione Veneto'),
 ('Tribunale di Milano','Tribunale di Venezia'),
])
def test_issuer_outweighs_body_reference(issuer,mention,loaded):
    names=[d.ente for d in loaded[0]]+[f.ente for f in loaded[1]]
    found=_issuer_entities(issuer+'\nDestinatario '+mention+'\nRiferimento '+mention,names)
    assert normalize_text(mention) not in found
    assert len(found)==1

@pytest.mark.parametrize('prefix',['Al','Alla','Spettabile','Destinatario','Per conoscenza','Riferimento'])
def test_recipient_alone_is_weak(prefix):
    assert not _issuer_entities(prefix+' INPS',['INPS'])

@pytest.mark.parametrize('year,expected',[(2025,False),(2026,True),(2027,False)])
def test_generic_annual_year_gate(loaded,year,expected):
    d=replace(loaded[0][0],id=999999,ente='INAIL',codice='TEST-567',titolo_ufficiale='Prova annuale di retribuzione anno 2026',versione='2026',stato_verifica='da_verificare',parole_chiave=())
    r=recognize_catalog(f'INAIL\nTEST-567\nProva annuale di retribuzione\nAnno {year}',[d],[])
    assert bool(r.document)==expected

def test_annual_missing_and_ambiguous_years_refuse(loaded):
    d=replace(loaded[0][0],id=999999,ente='INAIL',codice='TEST-567',titolo_ufficiale='Prova annuale di retribuzione anno 2026',versione='2026',stato_verifica='da_verificare',parole_chiave=())
    for text in ['INAIL\nTEST-567\nProva annuale di retribuzione','INAIL\nTEST-567\nProva annuale di retribuzione anno 2026\nAnno 2025']:
        assert not recognize_catalog(text,[d],[]).document

def test_model_year_is_distinct_from_fiscal_year(loaded):
    r=recognize_catalog('Agenzia delle Entrate\nMODELLO 730/2026\nREDDITI 2025',*loaded)
    assert r.document and r.document.id==49

def test_shared_code_without_subtype_stays_ambiguous(loaded):
    assert recognize_catalog('Agenzia delle Entrate\nModello F24',*loaded).match_type=='NO_MATCH'
    r=recognize_catalog('INAIL\nINL 28.1',*loaded)
    assert r.match_type=='NO_MATCH'

def test_profiles_validate_and_are_bounded():
    from src.recognition_profiles import load,validate
    value=load();assert value['schema_version']==1
    for wrong in [dict(value,schema_version=99),dict(value,exclusive_qualifiers=[['x'*121]]),dict(value,family_context={'x':'wrong'}),dict(value,unexpected=True)]:
        with pytest.raises(ValueError):validate(wrong)

def test_rarity_index_never_retains_request_text(loaded):
    from src.title_evidence import title_index,title_windows
    docs,_=loaded;before=title_index.cache_info().currsize
    title_windows('TESTO PERSONALE UNICO 123456',docs,[])
    title_windows('ALTRO TESTO PERSONALE',docs,[])
    assert title_index.cache_info().currsize<=before+1

def test_canonical_url_leakage_catches_iri_query_order_fragment():
    a=dict(id='D',url='https://www.inps.it/città.pdf?b=2&a=1#sezione')
    b=dict(id='H',url='https://www.inps.it/citt%C3%A0.pdf?a=1&b=2')
    assert collision(a,b)=='same_resource_url'
    assert not check([a],[b])['passed']

def test_historical_holdout_never_headlines_round4():
    from src.benchmark_display import headline_sections
    assert headline_sections({'independent_holdout':{'corpus_id':'official_holdout_v1','status':'executed'}})[0][1]['status']=='not_run'
    assert headline_sections({'independent_holdout':{'corpus_id':'official_holdout_v2','status':'executed'}})[0][1]['status']=='executed'

def test_family_corpora_are_frozen_and_label_repair_explained():
    import hashlib
    for v in (1,2,3):
        locks=read(f'benchmarks/manifests/family_release_locks_v{v}.json')['sha256']
        for p,s in locks.items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==s
    assert 'FR01-N4' in read('benchmarks/corpora/family_release_v2.json')['supersedes']['reason']
    assert 'case-sensitive' in read('benchmarks/corpora/family_release_v3.json')['supersedes']['reason']

def test_profile_schema_matches_runtime_validator():
    import jsonschema
    from src.recognition_profiles import load
    jsonschema.validate(load(),read('data/recognition_profiles/schema.json'))

def test_title_windows_cannot_use_weak_entity_to_override_wrong_heading(loaded):
    docs,families=loaded
    title='Richiesta di rinnovo del certificato di radio operatore GMDSS'
    result=recognize_catalog('INAIL\n'+title+'\nMinistero delle Imprese e del Made in Italy\nGente di Mare',docs,families)
    assert result.match_type=='NO_MATCH'

@pytest.mark.parametrize('number',[4,6])
def test_annex_number_is_an_identity_constraint(loaded,number):
    d=next(d for d in loaded[0] if d.id==612)
    text=f'Autorità Nazionale Anticorruzione\nAllegato n. {number}\n'+d.titolo_ufficiale
    r=recognize_catalog(text,*loaded)
    if number==6:assert not r.document or r.document.id!=612
    else:assert r.document and r.document.id==612

def test_runtime_never_imports_round4_acquisition():
    import ast
    for path in Path('src').rglob('*.py'):
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
            if isinstance(node,ast.ImportFrom):assert not (node.module or '').startswith(('maintenance','benchmarks'))
