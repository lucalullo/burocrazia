"""Release regression truth selection, separate from immutable old expectations."""
from scripts.round16_common import ROOT,read,sha,POLICY,TRUTH,ADDENDUM

def select_release(cases):
    selected=[];seen=set()
    for c in cases:
        key=c['case_id']
        if key in seen:raise ValueError('Duplicate release truth key')
        seen.add(key);state=c['confidence']
        if state=='confirmed':
            if c.get('release_gate_eligible') is not True:raise ValueError('Confirmed contract cannot be silently excluded')
            if not c.get('evidence'):raise ValueError('Confirmed contract lacks evidence')
            selected.append(c)
        elif state in ['ambiguous','insufficient','historical_only','obsolete']:
            if c.get('release_gate_eligible'):raise ValueError('Uncertain/obsolete truth cannot enter release gate')
        else:raise ValueError('Unknown truth confidence')
    return selected

def load_release():
    p=read(POLICY);v=read(ADDENDUM)
    assert p['base_reference_truth_v3_sha256']==sha(TRUTH)==v['base_reference_truth_v3_sha256']
    assert p['registry_sha256']==sha(ADDENDUM)
    for path,h in v['source_sha256'].items():assert sha(path)==h,path
    cases=select_release(v['cases'])
    catalog_sha=sha('data/catalog_seed.sqlite3')
    fingerprint_sha=sha('data/document_recognition_fingerprints_v3.json')
    for c in cases:
        if c['truth_domain']=='technical_canonical_binding':
            assert c['evidence']['catalog_sha256']==catalog_sha
            assert c['evidence']['fingerprint_sha256']==fingerprint_sha
    return p,v,cases
