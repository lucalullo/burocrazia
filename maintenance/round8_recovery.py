"""Bounded residual recovery for existing IDs; no retry of blocked 403/429 hosts."""
import argparse,csv,hashlib,json,sqlite3
from dataclasses import asdict
from urllib.parse import urlsplit,unquote
from collections import Counter,defaultdict
from benchmarks.round3_audit import ROOT,catalog,read,write
from maintenance.fetch import Fetcher
from maintenance.build_fingerprints import receipts
from maintenance.resolve_resources import SOURCES,sniff,unwrap_multipart,resolve_links,classify_error

def main():
    p=argparse.ArgumentParser();p.add_argument('--allow-network',action='store_true');a=p.parse_args()
    docs,_=catalog();by={d.id:d for d in docs};bundle=read('data/document_recognition_fingerprints_v2.json')['records']
    active={r['document_id'] for r in bundle if r['status']=='active'}
    blocked=set(read('benchmarks/results/round7/recovery_attempts.json')['blocked_hosts'])
    f=Fetcher(ROOT/'benchmarks/cache',allow_network=a.allow_network,use_cache=True);receipts(f)
    files=list(read('benchmarks/manifests/official_fingerprint_cache_v3.json')['files']);seen={(r['document_id'],r['sha256']) for r in files}
    alternatives=defaultdict(list)
    with sqlite3.connect((ROOT/'data/catalog_seed.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
        for did,metadata in db.execute('SELECT document_id,metadata_json FROM document_observations ORDER BY observed_at,id'):
            alternatives[did].extend(r['url'] for r in json.loads(metadata).get('resources',[]) if isinstance(r,dict) and isinstance(r.get('url'),str))
    rows=[];attempts=[]
    for d in docs:
        if d.stato_verifica in ['demo','rifiutato'] or d.id in active:continue
        row=dict(document_id=d.id,source_id=d.source_id,recovered=False,additional_resources=0,final_reason='no_supported_alternate')
        urls=list(dict.fromkeys(u for u in [d.download_url,*alternatives[d.id][:16],d.detail_url] if u));visited=set()
        while urls and len(visited)<12:
            url=urls.pop(0)
            if url in visited:continue
            visited.add(url);before=f.requests
            try:
                if url not in f.cached and urlsplit(url).netloc in blocked:raise ValueError('prior_403_429_no_retry')
                if url not in f.cached and f.requests>=60:raise ValueError('bounded_round8_network_budget')
                receipt=f.fetch(url,SOURCES[d.source_id]);raw,container=unwrap_multipart(f.read(receipt));mime=sniff(raw)
                if mime=='text/html':
                    urls.extend(u for u in resolve_links(raw,receipt.final_url,SOURCES[d.source_id],d) if u not in visited);reason='official_html_wrapper'
                elif mime in {'application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document'}:
                    sha=hashlib.sha256(raw).hexdigest();reason='supported_official_bytes'
                    if (d.id,sha) not in seen:
                        (ROOT/'benchmarks/cache'/(sha+'.body')).write_bytes(raw);seen.add((d.id,sha));row.update(recovered=True,additional_resources=row['additional_resources']+1)
                        files.append(dict(document_id=d.id,source_id=d.source_id,url=receipt.requested_url,final_url=receipt.final_url,sha256=sha,mime=mime,size=len(raw),acquisition_date=receipt.acquired_at,container_sha256=container,receipt=asdict(receipt),derivation='single_mime_attachment' if container else 'identity'))
                else:reason='unsupported_actual_format:'+mime
                row['final_reason']=reason
                attempt=dict(document_id=d.id,url=url,sha256=receipt.sha256,mime=mime,reason=reason,network_requests=f.requests-before)
            except (ValueError,OSError) as exc:
                status=getattr(exc,'status',None)
                if status in [403,429]:blocked.add(urlsplit(url).netloc)
                reason=classify_error(str(exc),status);row['final_reason']=str(exc)
                attempt=dict(document_id=d.id,url=url,http_status=status,reason=str(exc),classification=reason,network_requests=f.requests-before)
                # Decode only a single URL-encoded path, preserving origin and
                # policy checks. Never bypass a prior 403/429 host restriction.
                if '%25' in url and urlsplit(url).netloc not in blocked:
                    decoded=unquote(url)
                    if urlsplit(decoded).netloc==urlsplit(url).netloc:urls.append(decoded)
            attempts.append(attempt)
        rows.append(row)
        if len(rows)%30==0:print('Residual recovery',len(rows),'network',f.requests,'new IDs with bytes',sum(r['recovered'] for r in rows),flush=True)
    write('benchmarks/manifests/official_fingerprint_cache_v4.json',dict(schema_version=4,files=files))
    write('benchmarks/results/round8/recovery_attempts.json',dict(cases=rows,attempts=attempts,network_requests=f.requests,allow_network=a.allow_network,blocked_hosts=sorted(blocked),recovered_ids=[r['document_id'] for r in rows if r['recovered']],limits='Existing IDs/sources only, max60 network requests, max12 URLs/ID, robots/allowlist, no 403/429 bypass; unsupported DOC/XLSX/PPTX/ZIP stays unsupported.'))
    with (ROOT/'benchmarks/results/round8/fingerprint_recovery.csv').open('w',encoding='utf8',newline='') as out:
        w=csv.DictWriter(out,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    print('Recovery complete',f.requests,'network requests',sum(r['recovered'] for r in rows),'IDs with additional bytes',flush=True)

if __name__=='__main__':main()
