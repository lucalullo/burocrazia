"""Strict versioned truth and unknown-manifest validation, no recognition calls."""
import hashlib,json,re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1]
STATES={'confirmed','historical_only','ambiguous','obsolete','excluded'}
UNKNOWN_STATES={'confirmed_unknown','possible_catalog_match','possible_family_match','ambiguous','duplicate_of_catalog'}

def validate_registry(value):
    if value.get('schema_version')!=2:raise ValueError('Invalid truth version')
    seen=set()
    for c in value['cases']:
        key=(c.get('corpus'),c['case_id'])
        if key in seen:raise ValueError('Duplicate truth case')
        seen.add(key)
        if c['confidence_status'] not in STATES or c['expected_status'] not in ['DOCUMENT_MATCH','FAMILY_MATCH','NO_MATCH']:raise ValueError('Invalid truth state')
        for k in ['expected_document_id','expected_family_id','source_evidence','source_url','evidence_date','notes']:
            if k not in c:raise ValueError('Incomplete truth case')
        if c['expected_status']=='DOCUMENT_MATCH' and (type(c['expected_document_id']) is not int or c['expected_document_id']<=0):raise ValueError('Invalid document truth identity')
        if c['expected_status']=='FAMILY_MATCH' and (type(c['expected_family_id']) is not int or c['expected_family_id']<=0):raise ValueError('Invalid family truth identity')
        if c['expected_status']=='NO_MATCH' and (c['expected_document_id'] is not None or c['expected_family_id'] is not None):raise ValueError('NO truth with identity')
        if c['confidence_status']=='confirmed':
            if not c['source_evidence'] or not c['source_url'] or not c['evidence_date']:raise ValueError('Unsupported confirmation')
            if urlsplit(c['source_url']).scheme!='https' or datetime.fromisoformat(c['evidence_date']).tzinfo is None:raise ValueError('Invalid official evidence')
            if not any(re.fullmatch('[a-f0-9]{64}',e.get('sha256','')) for e in c['source_evidence']):raise ValueError('Missing official byte evidence')
    for path,sha in value['historical_locks'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=sha:raise ValueError('Historical bytes changed')
    return value

def validate_unknown(value):
    if value.get('schema_version')!=1 or value.get('manifest_id')!='official-unknown-v1':raise ValueError('Invalid unknown manifest')
    ids=set();shas=set()
    from maintenance.policy import validate_url # evaluation tooling only; never runtime
    from maintenance.iri import iri_to_uri
    for c in value['cases']:
        if c['case_id'] in ids or c['sha256'] in shas:raise ValueError('Duplicate unknown')
        ids.add(c['case_id']);shas.add(c['sha256'])
        if c['classification']!='confirmed_unknown' or c['expected_status']!='NO_MATCH':raise ValueError('Unconfirmed unknown included')
        if c['split'] not in ['development','evaluation']:raise ValueError('Invalid unknown split')
        validate_url(c['url'],c['source_key'])
        if validate_url(iri_to_uri(c['receipt']['requested_url']),c['source_key'])!=c['url']:raise ValueError('Source receipt URL mismatch')
        if c['receipt']['sha256']!=c['sha256'] or c['receipt']['status']!=200 or c['receipt']['acquired_at']!=c['evidence_date']:raise ValueError('Receipt mismatch')
        if datetime.fromisoformat(c['evidence_date']).tzinfo is None:raise ValueError('Missing receipt timezone')
        if not c['audit_evidence'] or c['format'] not in ['pdf','docx']:raise ValueError('Unsupported unknown evidence')
    return value

def classify_unknown(*,duplicate,near_catalog,possible_family,heading_supported,informational_type):
    if duplicate:return 'duplicate_of_catalog'
    if near_catalog:return 'possible_catalog_match'
    if possible_family:return 'possible_family_match'
    if heading_supported and informational_type:return 'confirmed_unknown'
    return 'ambiguous'
