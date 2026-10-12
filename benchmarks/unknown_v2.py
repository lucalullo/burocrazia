"""Strict benchmark-only unknown v2 contract; no runtime import."""
import re
from datetime import datetime
from maintenance.policy import validate_url
from maintenance.iri import iri_to_uri

def validate(value):
 if value.get('schema_version')!=2 or value.get('manifest_id')!='official-unknown-v2':raise ValueError('Invalid unknown v2')
 ids=set();hashes=set();groups={}
 for c in value['cases']:
  for key in ['case_id','source','entity','title','official_url','acquisition_date','SHA256','mime','classification_reason','reference_truth_status','expected_result','receipt','audit_evidence','split']:
   if key not in c:raise ValueError('Incomplete unknown v2')
  if c['case_id'] in ids or c['SHA256'] in hashes:raise ValueError('Duplicate unknown v2')
  ids.add(c['case_id']);hashes.add(c['SHA256'])
  if not re.fullmatch('[a-f0-9]{64}',c['SHA256']):raise ValueError('Invalid SHA')
  if c['reference_truth_status']!='confirmed_unknown' or c['expected_result']!='NO_MATCH':raise ValueError('Unconfirmed unknown v2')
  if c['split'] not in ['unknown_dev','unknown_eval']:raise ValueError('Invalid split')
  if c.get('historically_seen') and c['split']!='unknown_dev':raise ValueError('Historical input cannot become independent evaluation')
  group=c.get('resource_group')
  if group:
   if group in groups and groups[group]!=c['split']:raise ValueError('Resource group split overlap')
   groups[group]=c['split']
  url=validate_url(c['official_url'],c['source']);r=c['receipt']
  if validate_url(iri_to_uri(r['requested_url']),c['source'])!=url:raise ValueError('Receipt URL mismatch')
  validate_url(r['final_url'],c['source'])
  for u in r['redirects']:validate_url(u,c['source'])
  if r['sha256']!=c['SHA256'] or r['status']!=200 or r['acquired_at']!=c['acquisition_date']:raise ValueError('Receipt mismatch')
  if datetime.fromisoformat(c['acquisition_date']).tzinfo is None:raise ValueError('Missing timezone')
  if c['mime'] not in ['application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document'] or not c['audit_evidence'] or not c['classification_reason']:raise ValueError('Missing official evidence')
 return value
