import copy,json
from pathlib import Path
import pytest
from benchmarks.truth_v2 import validate_registry,validate_unknown,classify_unknown
from maintenance.legacy_resolver import inspect_legacy

def test_truth_v2_preserves_historical_and_excludes_ambiguities():
    r=validate_registry(json.loads(Path('benchmarks/reference/reference_truth_v2.json').read_bytes()))
    assert r['unclassified_contradictions']==0
    cases=[c for c in r['cases'] if c['case_id'] in ['EX02MISSINGREV','EX03MISSINGREV']]
    assert cases and all(c['confidence_status']=='ambiguous' for c in cases)
    unsupported=copy.deepcopy(r);c=next(c for c in unsupported['cases'] if c['confidence_status']=='historical_only');c['confidence_status']='confirmed'
    with pytest.raises(ValueError,match='Unsupported confirmation'):validate_registry(unsupported)

def test_unknown_manifest_validates_receipts_and_excludes_duplicates():
    r=validate_unknown(json.loads(Path('benchmarks/manifests/official_unknown_v1.json').read_bytes()))
    assert r['cases']
    for mutation in ['ambiguous','duplicate','receipt','source']:
        v=copy.deepcopy(r)
        if mutation=='ambiguous':v['cases'][0]['classification']='ambiguous'
        elif mutation=='duplicate':v['cases'].append(v['cases'][0])
        elif mutation=='receipt':v['cases'][0]['receipt']['sha256']='a'*64
        else:v['cases'][0]['url']='https://example.net/untrusted.pdf'
        with pytest.raises(ValueError):validate_unknown(v)

def test_unknown_classifier_requires_positive_official_heading_not_just_low_similarity():
    flags=dict(duplicate=False,near_catalog=False,possible_family=False,heading_supported=True,informational_type=True)
    assert classify_unknown(**flags)=='confirmed_unknown'
    for key,result in [('duplicate','duplicate_of_catalog'),('near_catalog','possible_catalog_match'),('possible_family','possible_family_match')]:
        assert classify_unknown(**dict(flags,**{key:True}))==result
    assert classify_unknown(**dict(flags,heading_supported=False))=='ambiguous'
    assert classify_unknown(**dict(flags,informational_type=False))=='ambiguous'

def test_legacy_resolver_fails_closed_without_converter(monkeypatch):
    monkeypatch.setattr('maintenance.legacy_resolver.shutil.which',lambda _:None)
    r=inspect_legacy(b'{\\rtf1 official sample}')
    assert r['format']=='rtf' and r['reason']=='unsupported_no_local_converter' and not r['conversion_performed']
    assert inspect_legacy(b'\xd0\xcf\x11\xe0'+b'\0'*20)['format']=='ole_compound_doc_or_xls'
    assert inspect_legacy(b'%PDF-1.7')['format']=='not_legacy'
    with pytest.raises(ValueError):inspect_legacy(b'x'*(20*1024*1024+1))
