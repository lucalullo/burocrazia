"""Prospective benchmark guards, independent of recognition outcomes."""
from io import BytesIO
import pytest
from benchmarks.round19_representations import derivative,scan,seed_for
from benchmarks.round19_plan import representation_key
from scripts.round19_common import sealed

def pdf_fixture():
    import pymupdf
    with pymupdf.open() as pdf:
        page=pdf.new_page();page.insert_text((40,80),'Synthetic administrative identity - test only')
        return pdf.tobytes(no_new_id=True)

def test_existing_semantic_freeze_is_reused():
    from benchmarks.historical_seals import verify_engine_at
    from scripts.round19_common import read
    f=read('benchmarks/results/round18/freeze_manifest.json')
    assert f['freeze_git_commit'].startswith('aa81678')
    verify_engine_at(f['freeze_git_commit'],f['engine_files_sha256'])

def test_scan_seed_changes_actual_pixels_and_is_repeatable():
    from PIL import Image,ImageChops
    raw=pdf_fixture();params=dict(dpi=150,noise_fraction=.0005,noise_amplitude=2)
    a,_=scan(raw,params,191);b,_=scan(raw,params,192);again,_=scan(raw,params,191)
    assert a==again and a!=b
    with Image.open(BytesIO(a)) as ia,Image.open(BytesIO(b)) as ib:assert ImageChops.difference(ia,ib).getbbox()

def test_derivative_preserves_text_without_exact_sha_shortcut():
    import pymupdf
    raw=pdf_fixture();derived,_=derivative(raw,'.pdf')
    assert raw!=derived
    with pymupdf.open(stream=raw,filetype='pdf') as a,pymupdf.open(stream=derived,filetype='pdf') as b:assert a[0].get_text()==b[0].get_text()

def test_case_equivalence_ignores_parameter_order_and_preserves_seed():
    assert representation_key(1,'raster',{'dpi':150,'noise_seed':19})==representation_key(1,'raster',{'noise_seed':19,'dpi':150})
    assert representation_key(1,'raster',{'dpi':150,'noise_seed':19})!=representation_key(1,'raster',{'dpi':150,'noise_seed':20})

def test_case_seed_deterministic_and_identity_specific():
    assert seed_for(2026101419,616,'digital')==seed_for(2026101419,616,'digital')
    assert seed_for(2026101419,616,'digital')!=seed_for(2026101419,615,'digital')
