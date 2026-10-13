import copy
from io import BytesIO
from pathlib import Path

import pytest
from src.fingerprint_v3 import read_bundle, validate


def legacy_fixture():
    bundle=read_bundle()
    record=copy.deepcopy(bundle['records'][0])
    record['mime_type']='application/rtf'
    record['ocr_metadata']=dict(source_kind='maintenance_derived_legacy',original_format='.rtf',
        original_sha256=record['canonical_file_sha256'],derived_sha256='a'*64,derived_mime_type='application/pdf',
        deterministic_conversion=True,conversion_method='libreoffice-pdf-normalized-v1',
        converter_sha256='b'*64,profile_sha256='c'*64,provenance_manifest_sha256='d'*64,
        representation_byte_identity='derived_not_official')
    return dict(bundle,records=[record])


def test_legacy_source_requires_complete_truthful_derivation_provenance():
    bundle=legacy_fixture();validate(bundle)
    for mutation in ['missing_manifest','same_bytes','fake_native_mime','not_deterministic','invalid_format_type']:
        bad=copy.deepcopy(bundle);r=bad['records'][0];m=r['ocr_metadata']
        if mutation=='missing_manifest':m.pop('provenance_manifest_sha256')
        elif mutation=='same_bytes':m['derived_sha256']=r['canonical_file_sha256']
        elif mutation=='fake_native_mime':r['mime_type']='application/pdf'
        elif mutation=='not_deterministic':m['deterministic_conversion']=False
        else:m['original_format']={}
        with pytest.raises(ValueError):validate(bad)


def test_legacy_upload_format_is_still_rejected():
    from src.extract import extract_document,ExtractionError
    with pytest.raises(ExtractionError):extract_document(b'{\\rtf1 fixture}','official.rtf')
    with pytest.raises(ExtractionError):extract_document(b'legacy fixture','official.xls')


def test_pdf_normalization_removes_variable_metadata_without_changing_text():
    import pymupdf
    from maintenance.round13_legacy import normalize_pdf
    values=[]
    for date in ['D:20200101000000','D:20261013000000']:
        with pymupdf.open() as pdf:
            pdf.new_page().insert_text((40,40),'Public deterministic fixture')
            pdf.set_metadata(dict(creationDate=date,modDate=date))
            values.append(normalize_pdf(pdf.tobytes()))
    assert values[0]==values[1]
    with pymupdf.open(stream=values[0],filetype='pdf') as pdf:assert 'Public deterministic fixture' in pdf[0].get_text()


def test_fingerprint_scoring_and_decision_semantics_are_unchanged():
    from scripts.round13_semantics import ROOT,check
    if not (ROOT/'.git').exists():pytest.skip('Historical Git checkout required; package includes the semantic audit')
    # Preserve the Round13 guarantee against its final committed artifact.
    # Round15 explicitly authorizes an adjudicated metadata-heading fix; its
    # current-engine invariant is tested separately in test_round15.py.
    assert check(target_commit='19883ba6a1e0e7360716aa0d9bba5ecb52a569eb')['features_index_scoring_ast_unchanged']


def test_common_legacy_page_cannot_establish_exact_identity_without_disambiguation(monkeypatch):
    from benchmarks.round3_audit import catalog
    from src.fingerprint_v3 import FingerprintIndex,page_record
    from src.fingerprint_pages import RequestPages
    from src.fingerprint_decision_v5 import match
    import src.fingerprint_decision_v4 as decision
    bundle=read_bundle()
    source=next((r for r in bundle['records'] if r['document_id']==618 and r['ocr_metadata'].get('source_kind')=='maintenance_derived_legacy'),None)
    if source is None:pytest.skip('Legacy source dataset required')
    target=next(d for d in catalog()[0] if d.id==618)
    text='UNIONCAMERE\nPagina comune sintetica per verifica del rifiuto prudente\nInformativa sul trattamento dei dati raccolti con le richieste\nDiritti accesso rettifica conservazione sicurezza limitazione trattamento personale\n'
    record=copy.deepcopy(source);record['pages']=[page_record(1,text,'',(),ocr_status='not_requested_maintenance_digital_only')]
    record['aggregate']=record['pages'][0]['digital'];record['field_set']=[];record['status']='shared'
    index=FingerprintIndex(dict(bundle,records=[record]));monkeypatch.setattr(decision,'public_index',lambda:index)
    assert match(text,[target],pages=RequestPages((text,),'digital_pdf')) is None
    # Control: identical technical channels would otherwise accept this page.
    record['status']='active';index=FingerprintIndex(dict(bundle,records=[record]))
    result=match(text,[target],pages=RequestPages((text,),'digital_pdf'))
    assert result and result.recognized and result.document.id==618
