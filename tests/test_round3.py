from __future__ import annotations
import json
from pathlib import Path
import pytest
from maintenance.iri import iri_to_uri
from benchmarks.holdout_leakage import check,collision
from benchmarks.round3_audit import catalog,CAUSES
from src.recognize import recognize_catalog
from src.title_evidence import exact_code_candidates
from src.text_quality import text_quality

@pytest.mark.parametrize('iri,uri',[
 ('https://www.inps.it/città/attività.pdf','https://www.inps.it/citt%C3%A0/attivit%C3%A0.pdf'),
 ("https://www.inps.it/l'attività (1).pdf?q=città Roma#sezione à","https://www.inps.it/l'attivit%C3%A0%20(1).pdf?q=citt%C3%A0%20Roma#sezione%20%C3%A0"),
 ('https://münchen.example/a%20b/%E0?x=%25','https://xn--mnchen-3ya.example/a%20b/%E0?x=%25'),
 ('https://www.inps.it/100%/x','https://www.inps.it/100%25/x'),
])
def test_iri_conversion(iri,uri):
    assert iri_to_uri(iri)==uri
    assert iri_to_uri(uri)==uri

@pytest.mark.parametrize('value',['http://www.inps.it/a','https://user:pw@www.inps.it/a','https://www.inps.it/a\nHost:x','https://www.inps.it\\evil/x','https://inps.it:bad/a'])
def test_iri_rejects_invalid_authority_or_controls(value):
    with pytest.raises(ValueError):iri_to_uri(value)

def test_all_eight_round2_ascii_failures_convert_without_special_cases():
    attempts=json.loads(Path('benchmarks/results/round2/official_acquisition.json').read_text(encoding='utf-8'))['attempts']
    failed=[a for a in attempts if 'ascii' in a.get('reason','')]
    assert len(failed)==8
    for a in failed:assert iri_to_uri(a['url']).isascii()

def test_leakage_detects_file_identity_version_template_and_reports_collisions():
    dev=[dict(id='D',document_id=1,entity='Tribunale di Venezia',title='Tutela Minori Autorizzazione acquisto immobili 2026',sha256='a'*64,url='https://example.test/a')]
    for hold in [dict(id='H',sha256='a'*64),dict(id='H',entity='Tribunale di Venezia',document_id=1),dict(id='H',entity='Tribunale di Venezia',title='Minori Autorizzazione acquisto immobili 2025')]:
        assert not check(dev,[hold])['passed']
    assert check(dev,[dict(id='H',entity='INAIL',title='Denuncia malattia professionale',sha256='b'*64)])['passed']

def test_code_index_preserves_numeric_subcodes_and_line_boundaries():
    docs,_=catalog()
    assert 1225 in exact_code_candidates('Modulo INL 1.4',docs)
    assert 153 not in exact_code_candidates('Modulo INL 1.4',docs)
    assert not exact_code_candidates('Modulo INL\n31',docs)
    assert not exact_code_candidates('Protocollo INL 31',docs)

@pytest.mark.parametrize('text',[
 'Ispettorato Nazionale del Lavoro\nGuida\nRichiesta di intervento ispettivo',
 'Tribunale di Milano\nTutela minori\nRinuncia incarico tutore',
 'Ministero delle Imprese e del Made in Italy\nRichiesta di rinnovo certificato radio operatore GMDSS\nGOC ROC\nGente di Mare',
 'Direzione Generale per le politiche previdenziali e assicurative\nDivisione VI\nCOMUNICATO 2022\nMinistero del Lavoro\nDichiarazione sostitutiva di certificazione',
])
def test_near_negative_new_title_rules_refuse(text):
    assert recognize_catalog(text,*catalog()).match_type=='NO_MATCH'

def test_family_heading_with_explicit_issuer_and_unknown_model_version():
    docs,families=catalog()
    text='Ispettorato Nazionale del Lavoro\nRichiesta di intervento ispettivo'
    # Force the family path without altering production thresholds or metadata.
    result=recognize_catalog(text,[],families)
    assert result.match_type=='FAMILY_MATCH' and result.family.id==10
    wrong=recognize_catalog('Tribunale di Milano\nRichiesta di intervento ispettivo',[],families)
    assert wrong.match_type=='NO_MATCH'

def test_text_quality_does_not_confuse_normal_forms_with_corruption():
    assert text_quality('Documento amministrativo. Codice fiscale _____________')['usable']
    assert not text_quality('\ufffd'*100)['usable']
    assert not text_quality('a b c d e '*40)['usable']

def test_official_audit_covers_all_positives_and_stable_causes():
    import csv
    rows=list(csv.DictReader(Path('benchmarks/results/round3/official_positive_audit.csv').open(encoding='utf-8')))
    assert len(rows)==150 and len({r['case_id'] for r in rows})==150
    assert {r['root_cause'] for r in rows}<=set(CAUSES)
    assert sum(r['current_result']=='NO_MATCH' for r in rows)==123

def test_rejected_identities_are_retained_with_provenance_but_never_operational():
    import sqlite3
    docs,families=catalog();rejected={429,1077,1081,1091}
    assert {d.id for d in docs if d.stato_verifica=='rifiutato'}==rejected
    for d in docs:
        if d.id in rejected:
            result=recognize_catalog(d.ente+'\n'+d.titolo_ufficiale,docs,families)
            assert not result.document or result.document.id not in rejected
    with sqlite3.connect('file:data/catalog_seed.sqlite3?mode=ro',uri=True) as db:
        assert db.execute('SELECT count(*) FROM document_provenance WHERE document_id IN (429,1077,1081,1091)').fetchone()[0]==4

def test_benchmark_precedence_never_promotes_locked_v2_to_independent():
    from src.benchmark_display import headline_sections
    sections=headline_sections({'evaluations':[{'name':'locked_v2','summary':{'cases':69}}]})
    assert [key for key,_ in sections]==['independent_holdout','hard_negatives','real_ocr','performance']
    assert sections[0][1]['status']=='not_run'

def test_technical_features_require_issuer_catalog_identity_and_unique_anchor_set():
    from src.technical_anchors import load_features,match_anchors
    docs,_=catalog();feature=load_features()[0];d=next(d for d in docs if d.id==feature['document_id'])
    text=' '.join(feature['anchor_tokens'])
    assert not match_anchors(text,docs,[])
    assert not match_anchors(text,docs,['Wrong issuer'])
    from dataclasses import replace
    changed=[replace(x,titolo_ufficiale='Changed identity') if x.id==d.id else x for x in docs]
    assert d.id not in match_anchors(text,changed,[d.ente])

def test_numeric_code_alias_does_not_merge_versions():
    from src.title_evidence import compact_code
    assert compact_code('INL 1.4')!=compact_code('INL 14')
    assert compact_code('INL 29-2')==compact_code('INL 29.2')

def test_duplicate_audit_is_read_only_and_reconciles_all_groups():
    from scripts.round3_quality_report import audit
    value=audit()
    assert len(value['groups'])==11 and value['automatic_merges']==0
    assert value['rejected_provenance_count']==4

def test_ui_benchmark_headline_and_rejected_history(tmp_path,monkeypatch):
    import shutil
    import app
    from streamlit.testing.v1 import AppTest
    db=tmp_path/'catalog.sqlite3';shutil.copy2('data/catalog_seed.sqlite3',db)
    monkeypatch.setattr(app,'DEFAULT_DB_PATH',db)
    at=AppTest.from_string('import app\napp.main()',default_timeout=20).run()
    at.radio(key='main_navigation').set_value('Benchmark').run()
    assert not at.exception
    values=[e.value for e in at.text]
    assert values.index('Holdout ufficiale indipendente')<values.index('Hard negatives')<values.index('OCR reale')<values.index('Performance')
    at.radio(key='main_navigation').set_value('Catalogo').run()
    at.selectbox(key='catalog_status').set_value('rifiutato').run()
    assert not at.exception and len(at.dataframe[0].value)==4

def test_performance_guard_rejects_latency_or_unbounded_warm_growth():
    from benchmarks.round3_performance import guard
    report={'ratios_to_baseline':{'p50':1.0,'p95':1.49},'memory':{'candidate':{'rss_growth_after_warm_bytes':1024}}}
    assert guard(report)
    report['ratios_to_baseline']['p95']=1.51
    assert not guard(report)
    report['ratios_to_baseline']['p95']=1.0;report['memory']['candidate']['rss_growth_after_warm_bytes']=17*1024*1024
    assert not guard(report)

def test_unusable_digital_layer_uses_bounded_ocr_fallback(monkeypatch):
    import fitz
    from src.extract import extract_document
    from src.ocr import OCRResult
    pdf=fitz.open();pdf.new_page();raw=pdf.tobytes();pdf.close()
    monkeypatch.setattr(fitz.Page,'get_text',lambda *args,**kwargs:'\ufffd'*200)
    calls=[]
    def local(*args,**kwargs):
        calls.append(kwargs);return OCRResult('Testo amministrativo leggibile dopo OCR locale.','ita')
    monkeypatch.setattr('src.extract.local_ocr.ocr_image',local)
    result=extract_document(raw,'fixture.pdf')
    assert result.used_ocr and result.ocr_pages==1 and len(calls)==1
    assert 'non utilizzabile' in result.warning

@pytest.mark.parametrize('entity,title',[
 ('Tribunale di Venezia','Tutela dei minori Rinuncia incarico tutore'),
 ('Tribunale di Venezia','Minori autorizzazione ad accettare risarcimento danni'),
 ('Tribunale di Venezia','Minori autorizzazione acquisto immobili'),
 ('Ispettorato Nazionale del Lavoro','Richiesta tentativo di conciliazione congiunta'),
])
def test_development_heading_alone_cannot_infer_catalog_year(entity,title):
    result=recognize_catalog(entity+'\n'+title,*catalog())
    assert not result.document or not result.document.versione

def test_issuer_mentions_without_resolved_heading_cannot_promote_generic_declaration():
    text='Dichiarazione sostitutiva\nINAIL\nMinistero del Lavoro\nINPS\nAutocertificazione per riduzione contributiva settore edile'
    assert recognize_catalog(text,*catalog()).match_type=='NO_MATCH'

