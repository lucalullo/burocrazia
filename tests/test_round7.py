"""Decision v3 safety and exact optimization equivalence on synthetic data."""
from dataclasses import replace
from io import BytesIO
import json,zipfile
import pytest
from tests.test_fingerprint_v2 import bundle,record,document,TEXT
from src.fingerprint_v2 import FingerprintIndex,features,overlap,visual_similarity
from src.fingerprint_decision_v3 import tier,DEFAULT,entity_evidence,metadata_revision_supported
from src.fingerprint_match_v2 import safety_reason,match
from maintenance.resolve_resources import resolve_links,sniff,SOURCES

def test_conditional_tiers_never_accept_visual_alone():
    r=dict(text=0,ocr=0,ocr_header=0,chars=0,visual=1,anchors=1,overlap=100)
    assert tier(r,DEFAULT) is None
    r.update(text=.60,chars=.14,anchors=.18)
    assert tier(r,DEFAULT)=='B_text_visual'
    r['visual']=.7;assert tier(r,DEFAULT) is None
    r.update(text=.98,chars=.35,anchors=.3,visual=0)
    assert tier(r,DEFAULT,code_anchor=True)=='C_exceptional_identity_anchor'

def test_recipient_roles_do_not_override_explicit_issuer_conflicts():
    names=['INPS','INAIL','Dipartimento della Funzione Pubblica','Ministero delle Imprese e del Made in Italy']
    assert not entity_evidence('Compilato a cura del SUAP:\nAl SUAP del\nComune di Esempio\nProtocollo\nSCIA',names)
    assert entity_evidence('INAIL\nAl SUAP del\nComune di Esempio\nSCIA',names)=={'inail'}
    e=entity_evidence('Richiesta duplicato\nAI MINISTERO DELLE IMPRESE E MADE IN ITALY\nDipartimento per i servizi interni',names)
    assert e=={'ministero delle imprese e del made in italy'}
    assert entity_evidence('Ministero Sconosciuto\nINPS',names)=={'ministero sconosciuto'}

def test_unique_metadata_code_exception_preserves_revision_ambiguity():
    d=document(versione='1.2')
    assert metadata_revision_supported(TEXT,d,[d])
    assert not metadata_revision_supported(TEXT,d,[d,replace(d,id=2,versione='1.3')])
    assert not metadata_revision_supported(TEXT.replace('INPS','INAIL'),d,[d])
    assert safety_reason('INPS\nVersione 1.3\n'+TEXT,d,[d],exact=True)=='explicit_revision_conflict'

@pytest.mark.parametrize('i',range(8))
def test_precomputed_denominators_identical_to_original_scoring(i):
    records=[record(document(j+1),raw=str(j).encode(),text=TEXT+f'\nSpecifico {j}') for j in range(8)]
    index=FingerprintIndex(bundle(records));q=features(TEXT[:400+200*i]);visual=()
    actual=index.similarities(q,visual)
    expected=[]
    for n in index.candidates(q,visual):
        r=index.records[n];best=0;count=0
        for k in ['digital','ocr','header','ocr_header']:
            values=r[k];den=sum(index.weights.get(h,1) for h in values)
            score=sum(index.weights.get(h,1) for h in values if h in q['tokens'])/den if den else 0
            best=max(best,score);count=max(count,sum(h in q['tokens'] for h in values))
        expected.append((r['document_id'],best,count,.5*best+.25*overlap(r['chars'],q['chars'])+.15*overlap(r['anchors'],q['anchors'])))
    expected.sort(key=lambda r:(-r[3],r[0]))
    assert [(r['document_id'],r['text'],r['overlap'],r['score']) for r in actual]==expected

@pytest.mark.parametrize('source',SOURCES.values())
def test_official_meta_refresh_and_extensionless_fixture(source):
    from maintenance.policy import DOMAINS
    base='https://www.'+DOMAINS[source][0]+'/detail'
    d=replace(document(),detail_url=base)
    raw=b'<meta http-equiv="refresh" content="0;url=/documents/Modulo%20TEST.pdf"><a download="Modulo TEST" href="/documents/attachment">Richiesta prestazione sociale</a>'
    links=resolve_links(raw,base,source,d)
    assert base.rsplit('/',1)[0]+'/documents/Modulo%20TEST.pdf' in links
    assert not resolve_links(b'<meta http-equiv="refresh" content="0;url=https://evil.example/a.pdf">',base,source,d)

def test_zip_magic_does_not_mislabel_spreadsheets_as_word():
    b=BytesIO()
    with zipfile.ZipFile(b,'w') as z:z.writestr('xl/workbook.xml','<workbook/>')
    assert sniff(b.getvalue())=='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

def test_filled_values_cover_dates_amounts_and_fictitious_personal_fields():
    from benchmarks.round7_fill import field_value
    assert field_value('Data nascita',2)=='03/02/2030'
    assert field_value('Importo euro',2)=='1236,50'
    assert field_value('Codice fiscale',2)=='ZZZZZZ00A00Z000X'
    assert field_value('Indirizzo',2)=='Via Fittizia 19'

@pytest.mark.parametrize('text',[TEXT,'INAIL\n'+TEXT,TEXT[:35],'Comune di Esempio\nIstruzioni generiche','INPS\nVersione 9.9\n'+TEXT])
def test_title_coverage_shortcut_preserves_complete_reference_result(text):
    from src.recognize import recognize_document
    docs=[document(i+1,titolo_ufficiale=TEXT+f' testo titolo aggiuntivo {i}') for i in range(6)]+[document(9)]
    assert recognize_document(text,docs)==recognize_document(text,docs,reference_full_scan=True)

def test_optimized_metadata_matches_reference_on_frozen_development_and_negatives():
    from pathlib import Path
    from benchmarks.round3_audit import catalog
    from src.recognize import recognize_document
    docs,_=catalog()
    cases=json.loads(Path('benchmarks/corpora/development_regression.json').read_bytes())['cases']
    cases+=json.loads(Path('benchmarks/corpora/hard_negatives_v2.json').read_bytes())['cases'][:5]
    for c in cases:
        assert recognize_document(c['text'],docs)==recognize_document(c['text'],docs,reference_full_scan=True),c['id']

def test_frozen_fixture_expectations_are_contradictory_and_unchanged():
    from pathlib import Path
    old=json.loads(Path('tests/fixtures/benchmark.json').read_bytes())
    new=json.loads(Path('tests/fixtures/benchmark_v2.json').read_bytes())
    for case_id in ['EX02','EX03']:
        a=next(c for c in old['cases'] if c['id']==case_id)
        b=next(c for c in new['cases'] if c['id']==case_id+'MISSINGREV')
        assert a['text']==b['text'] and a['expected']['match_type']=='DOCUMENT_MATCH' and b['expected']['match_type']=='NO_MATCH'
