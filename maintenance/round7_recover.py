"""Bounded recovery for already catalogued identities; opt-in network only."""
import argparse,csv,hashlib,json,sqlite3
from dataclasses import asdict
from urllib.parse import urlsplit
from benchmarks.round3_audit import ROOT,catalog,read,write
from maintenance.fetch import Fetcher
from maintenance.build_fingerprints import receipts
from maintenance.resolve_resources import SOURCES,sniff,unwrap_multipart,resolve_links,classify_error

SUPPORTED={'application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--allow-network',action='store_true');a=p.parse_args()
    docs,_=catalog();by={d.id:d for d in docs};f=Fetcher(ROOT/'benchmarks/cache',allow_network=a.allow_network,use_cache=True);receipts(f)
    previous=read('benchmarks/results/round6/resource_audit.json');missing=list(csv.DictReader((ROOT/'benchmarks/results/round6/missing_fingerprint_final.csv').open(encoding='utf8')))
    files=list(read('benchmarks/manifests/official_fingerprint_cache_v2.json')['files']);seen={(r['document_id'],r['sha256']) for r in files}
    blocked=set()
    first=read('benchmarks/results/round5/fingerprint_acquisition_first.json')['cases']
    for r in first:
        if any(s in r.get('reason','') for s in ['HTTP 403','HTTP 429']):blocked.add(urlsplit(by[r['document_id']].download_url or '').netloc)
    alternatives={}
    with sqlite3.connect((ROOT/'data/catalog_seed.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
        for did,metadata in db.execute('SELECT document_id,metadata_json FROM document_observations ORDER BY observed_at,id'):
            alternatives[did]=[r['url'] for r in json.loads(metadata).get('resources',[]) if isinstance(r,dict) and isinstance(r.get('url'),str)][:16]
    rows=[];attempts=[]
    for old in missing:
        did=int(old['document_id']);d=by[did];source=SOURCES[d.source_id]
        row=dict(document_id=did,source=source,previous_reason=old['classification'],action='existing_files_and_bounded_official_detail',recovered=False,fingerprinted=False,final_reason=old['reason'])
        urls=list(dict.fromkeys(u for u in [d.download_url,*alternatives.get(did,[]),d.detail_url] if u));visited=set()
        while urls and len(visited)<20:
            url=urls.pop(0)
            if url in visited:continue
            visited.add(url)
            before=f.requests
            try:
                if url not in f.cached and urlsplit(url).netloc in blocked:raise ValueError('prior_403_429_no_retry')
                if url not in f.cached and f.requests>=300:raise ValueError('bounded_session_budget')
                receipt=f.fetch(url,source);raw,container=unwrap_multipart(f.read(receipt));mime=sniff(raw)
                attempt=dict(document_id=did,url=url,final_url=receipt.final_url,http_status=receipt.status,content_type=receipt.content_type,mime=mime,bytes=len(raw),resolver_path='official_detail_attachment_or_meta_refresh',network_requests=f.requests-before)
                if mime=='text/html':
                    links=resolve_links(raw,receipt.final_url,source,d);urls.extend(u for u in links if u not in visited);attempt['reason']='HTML wrappers: '+str(len(links))+' official candidates'
                elif mime in SUPPORTED:
                    sha=hashlib.sha256(raw).hexdigest();row['final_reason']='supported_official_bytes_available'
                    if (did,sha) not in seen:
                        (ROOT/'benchmarks/cache'/(sha+'.body')).write_bytes(raw);seen.add((did,sha));row['recovered']=True
                        files.append(dict(document_id=did,source_id=d.source_id,url=receipt.requested_url,final_url=receipt.final_url,sha256=sha,mime=mime,size=len(raw),acquisition_date=receipt.acquired_at,container_sha256=container,receipt=asdict(receipt),derivation='single_mime_attachment' if container else 'identity',reuse_note='Official cache ignored and not redistributed.'))
                    attempt['reason']='supported_official_bytes_available'
                else:attempt['reason']='unsupported_actual_format:'+mime
            except (ValueError,OSError) as exc:
                status=getattr(exc,'status',None)
                if status in (403,429):blocked.add(urlsplit(url).netloc)
                attempt=dict(document_id=did,url=url,http_status=status,reason=str(exc),failure_type=classify_error(str(exc),status),network_requests=f.requests-before)
            attempts.append(attempt)
        rows.append(row)
        if len(rows)%20==0:print('Recovery',len(rows),'new resources',sum(r['recovered'] for r in rows),'network',f.requests,flush=True)
    write('benchmarks/manifests/official_fingerprint_cache_v3.json',dict(schema_version=3,files=files))
    write('benchmarks/results/round7/recovery_attempts.json',dict(cases=rows,attempts=attempts,network_requests=f.requests,blocked_hosts=sorted(blocked),allow_network=a.allow_network))
    with (ROOT/'benchmarks/results/round7/fingerprint_recovery.csv').open('w',encoding='utf8',newline='') as out:
        w=csv.DictWriter(out,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    print('Recovery complete',f.requests,'network requests',sum(r['recovered'] for r in rows),'identities with additional bytes',flush=True)

if __name__=='__main__':main()
