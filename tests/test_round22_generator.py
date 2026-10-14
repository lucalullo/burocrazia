"""Synthetic generation contracts only; old recognition tests remain immutable."""
import hashlib
from io import BytesIO
import pytest
import pymupdf as fitz
from pypdf import PdfReader
from benchmarks.round22_fill import generate,validate,active_references
from benchmarks.round22_prepare import generate_one,atomic_pdf
from scripts.round22_common import read,POLICY

def static(pages=1,dense=False):
    with fitz.open() as pdf:
        for i in range(pages):
            page=pdf.new_page();page.insert_text((35,45),f'INPS MODULO FITTIZIO TEST22 ANNO2030 PAGINA{i+1}')
            if dense and i==0:
                for y in range(65,815,9):page.insert_text((20,y),'TESTO ORIGINALE PROTETTO '*12,fontsize=6)
            else:page.insert_textbox((35,70,560,170),'Contenuto originale del template di esempio,senza persone reali. '*15,fontsize=8)
        return pdf.tobytes(no_new_id=True)

def native(malformed=False):
    with fitz.open(stream=static(),filetype='pdf') as pdf:
        p=pdf[0]
        for n,t,r in [('nome',fitz.PDF_WIDGET_TYPE_TEXT,(50,190,350,214)),('data',fitz.PDF_WIDGET_TYPE_TEXT,(50,230,220,254)),('importo',fitz.PDF_WIDGET_TYPE_TEXT,(50,270,220,294)),('scelta',fitz.PDF_WIDGET_TYPE_CHECKBOX,(50,310,66,326))]:
            w=fitz.Widget();w.field_name=n;w.field_type=t;w.rect=fitz.Rect(r);p.add_widget(w)
        if malformed:pdf.xref_set_key(pdf.pdf_catalog(),'AcroForm','<< /Fields [] >>')
        return pdf.tobytes(no_new_id=True)

@pytest.mark.parametrize('variant',[0,1])
def test_valid_native_widget_value_checkbox_numeric_date_persistence(variant):
    raw=native();out,a=generate(raw,variant,77,read(POLICY));fields=PdfReader(BytesIO(out)).get_fields()
    assert a['mode']=='acroform_native' and not a['fallback_from_acroform']
    assert 'FITTIZIO' in str(fields['nome']['/V']) and '2030' in str(fields['data']['/V']) and ',50' in str(fields['importo']['/V'])
    assert str(fields['scelta']['/V']) in ['/Off','/Yes'] and a['template_integrity_ok'] and a['reopened']

def test_malformed_acroform_static_fallback_retains_template():
    raw=native(malformed=True);out,a=generate(raw,1,78,read(POLICY))
    assert a['mode']=='static_overlay' and a['fallback_from_acroform'] and a['native_failure']
    assert a['template_integrity_ok'] and a['synthetic_values_verified']

@pytest.mark.parametrize('pages,dense',[(1,False),(2,True)])
def test_static_overlay_multiple_pages_safe_rectangles_and_reopen(pages,dense):
    raw=static(pages,dense);out,a=generate(raw,2,79,read(POLICY));assert a['mode']=='static_overlay' and a['fields_verified']>=1
    with fitz.open(stream=out,filetype='pdf') as pdf:assert len(pdf)==pages and 'TEST22' in pdf[0].get_text()
    if dense:assert any(q['page']==1 for q in a['placements'])
    assert all(c['outside_changed_pixel_fraction']<=.0001 for c in a['render_checks'])

def test_static_seed_is_byte_deterministic_and_records_values():
    raw=static();a,x=generate(raw,3,80,read(POLICY));b,y=generate(raw,3,80,read(POLICY))
    assert a==b and x==y and any('ZZZZZZ' in v for v in x['written_values'])

def test_validation_rejects_new_external_reference():
    raw=static();out,a=generate(raw,4,81,read(POLICY))
    with fitz.open(stream=out,filetype='pdf') as pdf:
        pdf[0].insert_link({'kind':fitz.LINK_URI,'from':fitz.Rect(20,20,35,35),'uri':'https://example.invalid/new'})
        changed=pdf.tobytes(no_new_id=True)
    with pytest.raises(ValueError,match='external/active'):validate(raw,changed,a)

def test_validation_rejects_template_damage_outside_fill_rectangles():
    raw=static();out,a=generate(raw,5,82,read(POLICY))
    with fitz.open(stream=out,filetype='pdf') as pdf:pdf[0].draw_rect((10,10,90,25),fill=(0,0,0));changed=pdf.tobytes(no_new_id=True)
    with pytest.raises(ValueError,match='Template pixels'):validate(raw,changed,a)

def test_atomic_write_and_failure_receipt_cleanup(tmp_path):
    path=tmp_path/'a.pdf';atomic_pdf(path,b'example');atomic_pdf(path,b'example')
    with pytest.raises(ValueError,match='differs'):atomic_pdf(path,b'other')
    assert not list(tmp_path.glob('*.partial')) and path.read_bytes()==b'example'
    raw=b'invalid';item=dict(case=dict(id='R21V6-999-filled_0',expected=dict(document_id=999)),canonical_sha=hashlib.sha256(raw).hexdigest(),seed=1,variant=1)
    row=generate_one(item,raw=raw,folder=tmp_path)
    assert not row['valid_generated'] and row['exception_type'] and row['error'] and not list(tmp_path.glob('R21V6*.pdf'))

def test_generation_valid_only_after_file_written_and_verified(tmp_path):
    raw=static();item=dict(case=dict(id='R21V6-999-filled_0',expected=dict(document_id=999)),canonical_sha=hashlib.sha256(raw).hexdigest(),seed=83,variant=6)
    row=generate_one(item,raw=raw,folder=tmp_path)
    assert row['valid_generated'] and row['written_and_readback_verified'] and (tmp_path/row['filename']).is_file()
    assert row['audit']['safety_parser_pass'] and not row['audit']['external_references_introduced']

def test_existing_official_reference_is_preserved_without_new_target():
    with fitz.open(stream=static(),filetype='pdf') as pdf:
        pdf[0].insert_link({'kind':fitz.LINK_URI,'from':fitz.Rect(20,20,35,35),'uri':'https://example.invalid/original'})
        raw=pdf.tobytes(no_new_id=True)
    out,a=generate(raw,7,84,read(POLICY));assert active_references(out)==active_references(raw) and not a['external_references_introduced']
