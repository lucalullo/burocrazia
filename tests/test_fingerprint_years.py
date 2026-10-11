"""Annual lookalikes must not inherit an illegible or contradictory year."""
from dataclasses import replace
import pytest
from tests.test_document_fingerprints import document,record,bundle,TEXT
from src.document_fingerprints import FingerprintIndex
from src.fingerprint_match import match

@pytest.mark.parametrize('model,title',[('730','Modello 730'),('CU','Certificazione Unica')])
@pytest.mark.parametrize('observed_year',['2026',''])
def test_annual_fingerprint_requires_matching_readable_year(model,title,observed_year):
    d=replace(document(versione='2025'),ente='Agenzia delle Entrate',codice=model,
              titolo_ufficiale=title+' 2025')
    canonical='Agenzia delle Entrate\n'+title+' 2025\n'+TEXT.replace('INPS','')
    i=FingerprintIndex(bundle([record(d,canonical,raw=(model+'-2025').encode())]))
    upload=canonical.replace(title+' 2025',title+' '+observed_year)
    assert match(upload,[d],index=i) is None
    if observed_year:
        assert match(upload,[d],index=i,file_sha256=i.records[d.id]['canonical_file_sha256']) is None

def test_actual_pdf_fields_can_be_filled_without_changing_identity():
    import fitz
    from src.extract import extract_document
    from maintenance.build_fingerprints import fields
    d=document()
    with fitz.open() as pdf:
        page=pdf.new_page();page.insert_text((35,45),TEXT,fontsize=7)
        for j,name in enumerate(['nome','data','indirizzo','importo']):
            w=fitz.Widget();w.field_name=name;w.field_type=fitz.PDF_WIDGET_TYPE_TEXT
            w.rect=fitz.Rect(35,550+35*j,300,575+35*j);page.add_widget(w)
        original=pdf.tobytes()
    names=fields(original,'application/pdf');assert len(names)==4
    ex=extract_document(original,'canonical.pdf')
    r=record(d,ex.text,raw=original);r['fields']=sorted(__import__('src.document_fingerprints',fromlist=['digest']).digest(name,'field') for name in names)
    with fitz.open(stream=original,filetype='pdf') as filled:
        values=['Mario Esempio','01/02/2030','Via Fittizia 17','1234,50']
        for j,w in enumerate(filled[0].widgets()):w.field_value=values[j];w.update()
        variant=filled.tobytes()
    with fitz.open(stream=variant,filetype='pdf') as check:
        assert [w.field_value for w in check[0].widgets()]==values
    uploaded=extract_document(variant,'filled.pdf')
    result=match(uploaded.text,[d],index=FingerprintIndex(bundle([r])),field_names=fields(variant,'application/pdf'))
    assert result and result.document.id==d.id and 'content_fingerprint_match' in result.matched_signals

@pytest.mark.parametrize('wanted,heading',[('acquisto','vendita'),('vendita','acquisto')])
def test_heading_transaction_overrides_body_cross_reference(wanted,heading):
    from src.recognize import _qualifier_conflict
    assert _qualifier_conflict({wanted,'immobili'},{wanted,heading,'immobili'},{heading,'immobili'})
    assert not _qualifier_conflict({wanted,'immobili'},{wanted,heading,'immobili'},{wanted,'immobili'})
