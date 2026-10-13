"""R11 master/release contracts and prediction-independent quota selection."""
import hashlib,math,re
from collections import Counter,defaultdict
from datetime import datetime
from maintenance.policy import validate_url
from maintenance.iri import iri_to_uri
SEED=2026101311

def validate(value):
 if value.get('schema_version')!=1 or value.get('manifest_id') not in ['official-unknown-master-v1','official-unknown-release-v1']:raise ValueError('Invalid R11 manifest')
 ids=set();shas=set()
 for c in value['cases']:
  for k in ['case_id','source','entity','title','official_url','acquisition_date','SHA256','mime','reference_truth_status','expected_result','receipt','audit_evidence','resource_group']:
   if k not in c:raise ValueError('Incomplete R11 unknown')
  if c['case_id'] in ids or c['SHA256'] in shas:raise ValueError('Duplicate R11 unknown')
  ids.add(c['case_id']);shas.add(c['SHA256'])
  if not re.fullmatch('[a-f0-9]{64}',c['SHA256']) or c['reference_truth_status']!='confirmed_unknown' or c['expected_result']!='NO_MATCH':raise ValueError('Unconfirmed R11 truth')
  url=validate_url(c['official_url'],c['source']);r=c['receipt']
  if validate_url(iri_to_uri(r['requested_url']),c['source'])!=url or r['sha256']!=c['SHA256'] or r['status']!=200 or r['acquired_at']!=c['acquisition_date']:raise ValueError('R11 receipt mismatch')
  validate_url(r['final_url'],c['source'])
  for u in r['redirects']:validate_url(u,c['source'])
  if datetime.fromisoformat(c['acquisition_date']).tzinfo is None or not c['audit_evidence']:raise ValueError('Unsupported R11 official evidence')
  if c['mime'] not in ['application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document']:raise ValueError('R11 unsupported mime')
 return value

def select(cases,*,seed=SEED,source_cap=25):
 """All-or-none near-resource groups; source quotas and seeded SHA only."""
 groups=defaultdict(list)
 for c in cases:groups[c['resource_group']].append(c)
 key=lambda g:hashlib.sha256((str(seed)+':'+g).encode()).hexdigest()
 counts=Counter();selected=[]
 for name in sorted(groups,key=key):
  group=groups[name];delta=Counter(c['source'] for c in group)
  if any(counts[k]+n>source_cap for k,n in delta.items()):continue
  selected.extend(group);counts.update(delta)
 return sorted(selected,key=lambda c:c['case_id'])

def balance(cases):
 counts=Counter(c['source'] for c in cases)
 return dict(total=len(cases),sources=len(counts),entities=len({c['entity'] for c in cases}),counts_per_source=dict(counts),max_concentration=max(counts.values(),default=0)/len(cases) if cases else None,document_types=dict(Counter(c['document_type'] for c in cases)),type_groups=len({c['document_type'] for c in cases}),with_code=sum(bool(c.get('code')) for c in cases),without_code=sum(not c.get('code') for c in cases),versioned=sum(bool(c.get('version')) for c in cases),unversioned=sum(not c.get('version') for c in cases),previously_recognized=sum(c.get('historically_seen',False) for c in cases))
