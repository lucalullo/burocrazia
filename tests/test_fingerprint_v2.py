"""Synthetic v2 tests: no official bytes, network or personal fixtures."""
from dataclasses import replace
from copy import deepcopy
from io import BytesIO
import hashlib,json,sqlite3
import pytest
from PIL import Image,ImageDraw,ImageFilter,ImageOps
from tests.test_document_fingerprints import document,TEXT
from src.fingerprint_v2 import (PARAMETERS,VERSION,DEFAULT_THRESHOLDS,features,make_record,
    validate,FingerprintIndex,visual_similarity,fused)
from src.fingerprint_visual import image_signature,visual_for_bytes
from src.fingerprint_match_v2 import match,safety_reason
from maintenance.resolve_resources import (SOURCES,unwrap_multipart,resolve_links,resource_kind,classify_error)
from maintenance.build_fingerprints_v2 import atomic_bundle

def record(d=None,raw=b'canonical',text=TEXT,**kw):
    return make_record(d or document(),raw,text,ocr_text=kw.pop('ocr_text',text),
        receipt=dict(requested_url='https://www.inps.it/a.pdf',final_url='https://www.inps.it/a.pdf',acquired_at='2026-10-12T06:00:00+00:00'),
        mime='application/pdf',page_count=1,generated_at='2026-10-12T06:01:00+00:00',**kw)

def bundle(records=None):return dict(schema_version=2,fingerprint_version=VERSION,parameters=PARAMETERS,records=records if records is not None else [record()])

def test_deterministic_hash_only_digital_and_ocr():
    assert record()==record()
    assert record()['digital']==record()['ocr']
    assert 'richiedente' not in json.dumps(record()).casefold()
    assert features('NOME  Mario\nEsempio')==features('NOME  Mario\nEsempio')

def test_char_grams_tolerate_spacing():
    a=features('INPS Modulo richiesta prestazione sociale')['chars']
    b=features('I N P S Modulo ri chiesta prestazione sociale')['chars']
    assert len(a&b)/len(a)>.9

def test_token_containment_and_ocr_channel():
    r=record(ocr_text=TEXT.replace('richiedente','richiedente rumore'))
    i=FingerprintIndex(bundle([r]));q=features(TEXT[:1800])
    rows=i.similarities(q)
    assert rows[0]['document_id']==1 and rows[0]['text']>.8
    assert i.similarities(q,reference=True)==rows

def test_multiple_resources_one_identity_no_self_ambiguity():
    a=record();b=record(raw=b'other-format');i=FingerprintIndex(bundle([a,b]))
    assert len(i.records)==2
    for raw in [b'canonical',b'other-format']:
        assert match(TEXT,[document()],index=i,file_sha256=hashlib.sha256(raw).hexdigest()).document.id==1
    assert len(i.similarities(features(TEXT)))==1

@pytest.mark.parametrize('status',['stale','quarantined'])
def test_stale_and_quarantine_excluded(status):
    i=FingerprintIndex(bundle([record(status=status)]))
    assert not i.records and match(TEXT,[document()],index=i,file_sha256=hashlib.sha256(b'canonical').hexdigest()) is None

def test_shared_bytes_refuse_exact():
    i=FingerprintIndex(bundle([record(),record(document(2))]))
    # Both content candidates remain ambiguous, too.
    assert match(TEXT,[document(),document(2)],index=i,file_sha256=hashlib.sha256(b'canonical').hexdigest()) is None

def test_safety_veto_entity_year_revision_rejected():
    i=FingerprintIndex(bundle())
    assert match(TEXT.replace('INPS','INAIL'),[document()],index=i,file_sha256=hashlib.sha256(b'canonical').hexdigest()) is None
    for version,heading in [('2025','Anno 2026'),('1.2','Versione 1.3')]:
        d=document(versione=version);idx=FingerprintIndex(bundle([record(d)]))
        assert match('INPS\n'+heading+'\n'+TEXT,[d],index=idx,file_sha256=hashlib.sha256(b'canonical').hexdigest()) is None
    assert match(TEXT,[replace(document(),stato_verifica='rifiutato')],index=i,file_sha256=hashlib.sha256(b'canonical').hexdigest()) is None

def test_competence_year_and_date_not_model_revision():
    d=document(versione='2026')
    assert safety_reason('INPS\nCOMUNICATO 2026\nAnno di competenza 2025\nversione 4.2.2026',[d][0],[d],exact=True) is None
    assert safety_reason('COMUNE\nCampo residenza\n'+TEXT,d,[d],exact=True) is None

def test_fusion_single_signal_cannot_accept():
    row=dict(text=0.,chars=0.,anchors=0.,visual=1.,overlap=200)
    assert not fused(row,DEFAULT_THRESHOLDS)
    row.update(text=1.,chars=1.)
    assert fused(row,DEFAULT_THRESHOLDS)
    row.update(visual=0.,anchors=0.)
    assert not fused(row,DEFAULT_THRESHOLDS)

def test_candidate_recall_at_k_and_no_upload_cache():
    i=FingerprintIndex(bundle());before=deepcopy(i.__dict__)
    for n in range(20):
        ranked=i.similarities(features(TEXT+'\nPersona Fittizia '+str(n)))
        assert ranked[0]['document_id']==1
    assert before==i.__dict__

def test_visual_rotation_resize_jpeg_gray_blur():
    with Image.new('RGB',(500,700),'white') as im:
        d=ImageDraw.Draw(im)
        for n in range(20):d.rectangle((25,30+n*28,150+n%5*50,45+n*28),outline='black')
        original=image_signature(im)
        with im.rotate(90,expand=True) as changed:assert visual_similarity(original,image_signature(changed))==1
        with im.resize((250,350)) as small:assert visual_similarity(original,image_signature(small))>.9
        with ImageOps.grayscale(im) as gray:assert visual_similarity(original,image_signature(gray))==1
        with im.filter(ImageFilter.GaussianBlur(.6)) as blur:assert visual_similarity(original,image_signature(blur))>.9
        b=BytesIO();im.save(b,format='JPEG',quality=60)
        assert visual_similarity(original,visual_for_bytes(b.getvalue(),'scan.jpg'))>.9

@pytest.mark.parametrize('mutate',[lambda b:b.update(schema_version=True),lambda b:b['records'][0].update(text='private'),
    lambda b:b['records'][0].update(ocr_metadata={'text':'private'}),lambda b:b['records'][0].update(digital=['bad']),
    lambda b:b['records'].append(b['records'][0])])
def test_schema_strict(mutate):
    b=bundle();mutate(b)
    with pytest.raises(ValueError):validate(b)

def test_atomic_idempotence_and_validation(tmp_path):
    p=tmp_path/'v2.json';assert atomic_bundle(bundle(),p);raw=p.read_bytes()
    assert not atomic_bundle(bundle(),p)
    with pytest.raises(ValueError):atomic_bundle(dict(records=[]),p)
    assert p.read_bytes()==raw

def test_missing_fingerprint_classifications():
    d=document();assert resource_kind(d)=='unclear'
    assert resource_kind(replace(d,download_url='https://www.inps.it/a.doc'))=='file_backed_document'
    assert resource_kind(replace(d,detail_url='https://www.inps.it/a'))=='metadata_only_document'
    assert classify_error('robots: no')=='robots_or_policy_block'
    assert classify_error('HTTP 403',403)=='http_403'
    assert classify_error('timed out')=='timeout'

def test_inps_multipart_offline_fixture():
    raw=b'--fixture-boundary\r\nContent-Type: application/pdf\r\n\r\n%PDF-1.7\nfixture\r\n--fixture-boundary--\r\n'
    body,container=unwrap_multipart(raw)
    assert body.startswith(b'%PDF-') and container==hashlib.sha256(raw).hexdigest()
    assert unwrap_multipart(b'<html>%PDF-</html>')==(b'<html>%PDF-</html>',None)
    with pytest.raises(ValueError):unwrap_multipart(raw.replace(b'--fixture-boundary--',b'truncated'))

@pytest.mark.parametrize('source',SOURCES.values())
def test_source_resolver_offline_fixture_and_allowlist(source):
    from maintenance.policy import DOMAINS
    base='https://www.'+DOMAINS[source][0]+'/detail'
    d=replace(document(),titolo_ufficiale='Richiesta prestazione sociale',detail_url=base)
    raw=b'<a href="/Richiesta_prestazione_sociale.pdf">Modulo</a><a href="https://evil.example/richiesta_prestazione_sociale.pdf">Modulo</a>'
    assert resolve_links(raw,base,source,d)==[base.rsplit('/',1)[0]+'/Richiesta_prestazione_sociale.pdf']

def test_no_sql_migration_old_snapshots(tmp_path):
    from pathlib import Path
    import subprocess
    seed=Path('data/catalog_seed.sqlite3');before=hashlib.sha256(seed.read_bytes()).hexdigest()
    for ref in ['v0.6.1','f9e1fa0','498c198']:
        if subprocess.run(['git','cat-file','-e',ref+':data/catalog_seed.sqlite3'],capture_output=True).returncode:
            pytest.skip('Historical Git snapshot unavailable; release workflow uses full history')
        target=tmp_path/(ref+'.sqlite3');target.write_bytes(subprocess.check_output(['git','show',ref+':data/catalog_seed.sqlite3']))
        from src.database import initialize_database
        for _ in range(2):
            initialize_database(target)
            with sqlite3.connect(target) as c:
                assert c.execute('pragma user_version').fetchone()[0]==610
                assert c.execute('pragma integrity_check').fetchone()[0]=='ok'
                assert not c.execute('pragma foreign_key_check').fetchall()
    assert hashlib.sha256(seed.read_bytes()).hexdigest()==before

def test_ui_summary_v2_separates_unvalidated_family():
    from src.benchmark_display import headline_sections
    s=dict(benchmark_model='known-family-unknown-v2',family_identity_holdout=dict(families_evaluable=2))
    assert [k for k,_ in headline_sections(s)]==['fingerprint_coverage','known_robustness','unknown_official','scan_ocr','performance']
    s['family_identity_holdout']['families_evaluable']=5
    assert 'family_identity_holdout' in [k for k,_ in headline_sections(s)]

def test_calibration_identity_separation_and_freeze(tmp_path,monkeypatch):
    import benchmarks.round6_recognition as bench
    base=tmp_path/'benchmarks/results/round6';base.mkdir(parents=True)
    profile=tmp_path/'data/recognition_profiles/fingerprint_v2.json';profile.parent.mkdir(parents=True);profile.write_bytes(b'{}')
    artifact=dict(calibration_identities=[1,2],evaluation_identities=[3,4],profile_sha256=hashlib.sha256(b'{}').hexdigest(),fingerprint_sha256=bench.revision())
    (base/'fingerprint_calibration.json').write_text(json.dumps(artifact))
    monkeypatch.setattr(bench,'ROOT',tmp_path)
    monkeypatch.setattr(bench,'read',lambda name:json.loads((tmp_path/name).read_bytes()))
    assert bench.checked_calibration()['evaluation_identities']==[3,4]
    profile.write_bytes(b'{"changed":true}')
    with pytest.raises(ValueError,match='changed after freeze'):bench.checked_calibration()

def test_json_schema_v2(tmp_path):
    import jsonschema
    from pathlib import Path
    jsonschema.validate(bundle(),json.loads(Path('data/document_recognition_fingerprints_v2.schema.json').read_bytes()))

def test_real_ocr_canonical_sketch_deterministic():
    import os
    if not os.environ.get('BUROCRAZIA_TESSERACT_CMD'):pytest.skip('Optional real local OCR')
    from src.ocr import ocr_image
    with Image.new('RGB',(700,220),'white') as im:
        draw=ImageDraw.Draw(im)
        from PIL import ImageFont
        font=ImageFont.load_default(size=24)
        draw.text((30,40),'INPS Modulo sintetico richiesta prestazione',font=font,fill='black')
        draw.text((30,90),'Sezione dati anagrafici del richiedente',font=font,fill='black')
        a=ocr_image(im,auto_orient=False);b=ocr_image(im,auto_orient=False)
        assert features(a.text)==features(b.text)

def test_actual_filled_fields_and_scan_transforms():
    pytest.importorskip('pypdf')
    import fitz
    from benchmarks.round6_recognition import fill_acroform,TRANSFORMS
    from benchmarks.round5_recognition import transform_pdf
    from src.extract import extract_document
    with fitz.open() as pdf:
        page=pdf.new_page();page.insert_text((40,40),'INPS Modulo sintetico richiesta prestazione sociale')
        for i,name in enumerate(['nome','data','codice_fiscale','importo','indirizzo']):
            w=fitz.Widget();w.field_name=name;w.field_type=fitz.PDF_WIDGET_TYPE_TEXT;w.rect=fitz.Rect(40,100+i*40,350,125+i*40);page.add_widget(w)
        raw=pdf.tobytes()
    first,n=fill_acroform(raw,0);second,_=fill_acroform(raw,1)
    assert n==5 and first!=second
    from pypdf import PdfReader
    values=PdfReader(BytesIO(first)).get_fields()
    assert values['nome']['/V']=='Esempio 0' and values['data']['/V']=='01/02/2030'
    assert values['codice_fiscale']['/V']=='CF-NON-VALIDO-0'
    for name,params in TRANSFORMS:
        if name=='digital_exact':continue
        transformed,ext=transform_pdf(raw,params)
        assert transformed and ext in ['.pdf','.jpg','.png']
        if ext=='.pdf':assert extract_document(transformed,'one.pdf').total_pages==1

def test_metadata_fallback_requires_readable_semantic_revision():
    from src.recognize import recognize_catalog
    d=document(versione='1.2')
    result=recognize_catalog(TEXT,[d],[])
    assert result.match_type=='NO_MATCH'
    result=recognize_catalog('INPS\nVersione 1.2\n'+TEXT,[d],[])
    assert result.match_type=='DOCUMENT_MATCH'
