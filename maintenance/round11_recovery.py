"""Deduplicated final source pass for fixed-denominator existing identities."""
import argparse,csv,hashlib,json,sqlite3
from collections import defaultdict,Counter
from dataclasses import asdict
from urllib.parse import urlsplit
from benchmarks.round3_audit import ROOT,catalog,read
from benchmarks.transactional_writer import atomic_json
from maintenance.fetch import Fetcher
from maintenance.build_fingerprints import receipts
from maintenance.resolve_resources import SOURCES,sniff,unwrap_multipart
from maintenance.round11_resolver import resolve_detail_links
from src.fingerprint_v3 import read_bundle
OUT=ROOT/'benchmarks/results/round11'

def main():
 p=argparse.ArgumentParser();p.add_argument('--allow-network',action='store_true');p.add_argument('--max-requests',type=int,default=80);a=p.parse_args()
 if not 1<=a.max_requests<=120:p.error('request budget1..120')
 import maintenance.fetch as fetch_module
 fetch_module.MAX_REQUESTS=a.max_requests
 docs,_=catalog();active={r['document_id'] for r in read_bundle()['records'] if r['status']=='active'}
 prior=list(csv.DictReader((ROOT/'benchmarks/results/round10/fingerprint_recovery_plan.csv').open(encoding='utf8')));by={d.id:d for d in docs};old_attempts=[]
 for round in [8,9]:old_attempts.extend(read(f'benchmarks/results/round{round}/recovery_attempts.json')['attempts'])
 denied={x['url'] for x in old_attempts if x.get('http_status') in [403,404,410,429]}
 blocked=set(read('benchmarks/results/round9/recovery_attempts.json')['blocked_hosts'])
 f=Fetcher(ROOT/'benchmarks/cache',allow_network=a.allow_network,use_cache=True,timeout=8);receipts(f)
 alternatives=defaultdict(list)
 with sqlite3.connect((ROOT/'data/catalog_seed.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
  for did,metadata in db.execute('SELECT document_id,metadata_json FROM document_observations ORDER BY observed_at,id'):
   alternatives[did].extend(r['url'] for r in json.loads(metadata).get('resources',[]) if isinstance(r,dict) and isinstance(r.get('url'),str))
 rows=[];attempts=[];files=[];seen=set()
 for old in sorted(prior,key=lambda r:(r['tier'],int(r['document_id']))):
  did=int(old['document_id']);d=by[did];key=SOURCES[d.source_id];tier={'1':'A','2':'B','3':'C','4':'D'}[old['tier']]
  urls=list(dict.fromkeys(u for u in [d.download_url,*alternatives[did][:16],d.detail_url] if u));visited=set();new=0
  row=dict(document_id=did,source=key,entity=d.ente,tier=tier,primary_url=d.download_url or '',alternate_url='',previous_reason=old['final_reason'],action='deduplicated cached/official detail pass; no blocked/permanent retries',attempted=True,success=False,fingerprint_built=False,final_reason=old['final_reason'])
  while urls and len(visited)<14:
   url=urls.pop(0)
   if url in visited:continue
   visited.add(url)
   try:
    if url not in f.cached and (tier=='D' or url in denied or urlsplit(url).netloc in blocked):raise ValueError('prior_permanent_or_policy_block_no_retry')
    r=f.fetch(url,key);raw,container=unwrap_multipart(f.read(r));mime=sniff(raw)
    if mime=='text/html':
     for target in resolve_detail_links(raw,r.final_url,key,d):
      if target not in visited:urls.append(target)
     result='official_detail_inspected'
    elif mime in ['application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
     sha=hashlib.sha256(raw).hexdigest();result='official_supported_bytes'
     if (did,sha) not in seen:
      seen.add((did,sha));(ROOT/'benchmarks/cache'/(sha+'.body')).write_bytes(raw)
      files.append(dict(document_id=did,source_id=d.source_id,url=r.requested_url,final_url=r.final_url,sha256=sha,mime=mime,size=len(raw),acquisition_date=r.acquired_at,receipt=asdict(r),container_sha256=container,derivation='single_mime_attachment' if container else 'official_bytes'))
      new+=1
    else:result='legacy_or_unsupported:'+mime
    attempts.append(dict(document_id=did,url=url,result=result,sha256=r.sha256,mime=mime));row['final_reason']=result
   except (ValueError,OSError) as exc:
    status=getattr(exc,'status',None)
    if status in [403,429]:blocked.add(urlsplit(url).netloc)
    attempts.append(dict(document_id=did,url=url,result=str(exc),http_status=status));row['final_reason']=str(exc)
  row['success']=bool(new);row['alternate_url']=';'.join(sorted(visited-{d.download_url,d.detail_url}));rows.append(row)
  if len(rows)%25==0:print('R11 source pass',len(rows),'requests',f.requests,'bindings with bytes',len(files),flush=True)
 with (OUT/'fingerprint_recovery_plan.csv').open('w',encoding='utf8',newline='') as out:
  w=csv.DictWriter(out,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
 atomic_json(OUT/'recovery_attempts.json',dict(cases=rows,attempts=attempts,network_requests=f.requests,allow_network=a.allow_network,per_source=dict(Counter(r['source'] for r in rows)),blocked_hosts=sorted(blocked),scope='All217 R10 unambiguous residuals, existing catalog IDs/sources only; max14 URLs/ID, global explicit network budget, no permanent/robots bypass. Acquisition success is not a fingerprint/identity success.'))
 atomic_json(ROOT/'benchmarks/manifests/official_fingerprint_cache_v6.json',dict(schema_version=6,files=files,scope='Round11 final pass receipts; source associations require offline truth/fingerprint validation.'))
 print('R11 final source pass',len(rows),'requests',f.requests,flush=True)

if __name__=='__main__':main()
