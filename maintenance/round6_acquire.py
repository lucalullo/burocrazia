"""Resolve only existing identities, sequential HTTPS and explicit opt-in."""
from __future__ import annotations
import argparse,csv,hashlib,json,sqlite3
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from urllib.parse import urlsplit
from benchmarks.round3_audit import ROOT,catalog,read,write
from maintenance.fetch import Fetcher,AcquisitionError
from maintenance.build_fingerprints import receipts
from maintenance.resolve_resources import SOURCES,sniff,unwrap_multipart,resolve_links,classify_error,resource_kind

OUT='benchmarks/results/round6/'
MANIFEST='benchmarks/manifests/official_fingerprint_cache_v2.json'

def acquire(allow_network=False):
    docs,_=catalog();docs=[d for d in docs if d.stato_verifica not in ['demo','rifiutato']]
    docs.sort(key=lambda d:([2,3,5,16,15,10,14,17,12,18,19,4].index(d.source_id),d.id))
    fetcher=Fetcher(ROOT/'benchmarks/cache',allow_network=allow_network,use_cache=True);receipts(fetcher)
    v1=read('data/document_recognition_fingerprints.json');old_ids={r['document_id'] for r in v1['records']}
    prior=read('benchmarks/results/round5/fingerprint_acquisition_first.json')['cases']
    blocked_hosts={urlsplit(next(d.download_url for d in docs if d.id==r['document_id'])).netloc for r in prior if 'HTTP 403' in r.get('reason','') or 'HTTP 429' in r.get('reason','')}
    previous_audit=read(OUT+'resource_audit.json') if (ROOT/OUT/'resource_audit.json').exists() else {}
    blocked_hosts.update(urlsplit(r['url']).netloc for r in previous_audit.get('attempts',[]) if r.get('network_requests') and r.get('http_status') in [403,429])
    previous=read(MANIFEST)['files'] if (ROOT/MANIFEST).exists() else []
    alternatives={}
    with sqlite3.connect((ROOT/'data/catalog_seed.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
        for did,metadata in db.execute('SELECT document_id, metadata_json FROM document_observations ORDER BY observed_at,id'):
            observation=json.loads(metadata)
            # The latest immutable listing is already associated with this
            # identity; alternative formats/languages are not new identities.
            alternatives[did]=[r['url'] for r in observation.get('resources',[]) if isinstance(r,dict) and isinstance(r.get('url'),str)][:16]
    files=[];audit=[];attempts=[]
    for pos,d in enumerate(docs):
        source=SOURCES[d.source_id]
        row=dict(document_id=d.id,source=source,source_id=d.source_id,entity=d.ente,title=d.titolo_ufficiale,
            code=d.codice,version=d.versione,detail_url=d.detail_url,download_url=d.download_url,
            operational_status=d.stato_verifica,expected_resource_type=resource_kind(d),fetch_attempted=False,
            final_url=None,http_status=None,content_type=None,bytes=None,classification='no_download_url',
            reason='Nessun URL file dichiarato; verificare la detail page ufficiale.',safe_next_action='resolve_official_detail_page',
            missing_v1=d.id not in old_ids,resources_available=0)
        candidates=list(dict.fromkeys([u for u in [d.download_url,*alternatives.get(d.id,[]),*[f['url'] for f in previous if f['document_id']==d.id]] if u]))
        visited=set();detail_tried=False;document_hashes=set()
        while candidates or not detail_tried:
            if candidates:url=candidates.pop(0)
            else:
                detail_tried=True
                if row['resources_available'] or not d.detail_url:break
                url=d.detail_url
            if url in visited:continue
            visited.add(url)
            if len(visited)>16:break
            before=fetcher.requests
            try:
                host=urlsplit(url).netloc
                if url not in fetcher.cached and host in blocked_hosts:
                    row.update(classification='robots_or_policy_block',reason='Host con HTTP 403/429 già documentato nel Round 5; nessuna nuova richiesta.',safe_next_action='wait_for_official_unblocked_access');continue
                if url not in fetcher.cached and fetcher.requests>=390:
                    row.update(classification='other',reason='Budget sequenziale della sessione esaurito; percorso non richiesto.',safe_next_action='new_bounded_maintenance_session');continue
                receipt=fetcher.fetch(url,source);envelope=fetcher.read(receipt)
                raw,container=unwrap_multipart(envelope);mime=sniff(raw)
                row.update(fetch_attempted=True,final_url=receipt.final_url,http_status=receipt.status,content_type=receipt.content_type,bytes=receipt.size)
                if mime=='text/html':
                    links=resolve_links(raw,receipt.final_url,source,d)
                    candidates.extend(u for u in links if u not in visited)
                    row.update(classification='download_url_html' if url==d.download_url else 'detail_page_only',
                        reason='Pagina HTML ufficiale; '+str(len(links))+' allegati coerenti trovati.',safe_next_action='follow_validated_attachment' if links else 'manual_official_resource_review')
                elif mime in ['application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
                    sha=hashlib.sha256(raw).hexdigest()
                    if sha not in document_hashes:
                        (ROOT/'benchmarks/cache'/(sha+'.body')).write_bytes(raw)
                        document_hashes.add(sha)
                        files.append(dict(document_id=d.id,source_id=d.source_id,url=receipt.requested_url,
                            final_url=receipt.final_url,sha256=sha,mime=mime,size=len(raw),acquisition_date=receipt.acquired_at,
                            container_sha256=container,receipt=asdict(receipt),derivation='single_mime_attachment' if container else 'identity',
                            reuse_note='Cache locale ignorata; nessun documento ufficiale redistribuito.'))
                        row['resources_available']+=1
                        row.update(classification='available',reason='File ufficiale e hash verificati.',safe_next_action='build_minimized_signature',expected_resource_type='file_backed_document')
                else:row.update(classification='empty_file' if mime=='empty_file' else 'unsupported_mime',reason='Formato '+mime+' non estraibile dal runtime corrente.',safe_next_action='resolve_official_supported_alternative')
            except (ValueError,OSError) as exc:
                row.update(classification=classify_error(str(exc),getattr(exc,'status',None)),reason=str(exc),
                    http_status=getattr(exc,'status',None),safe_next_action='review_actual_failure_without_bypass')
                if fetcher.requests>before:row['fetch_attempted']=True
            attempts.append(dict(document_id=d.id,url=url,network_requests=fetcher.requests-before,classification=row['classification'],http_status=row['http_status'],reason=row['reason']))
        if row['resources_available']:
            row.update(classification='available',reason='Risorse ufficiali e hash verificati.',safe_next_action='build_minimized_signature')
        elif d.download_url:
            actual=[a for a in attempts if a['document_id']==d.id]
            unsupported=next((a for a in actual if a['classification']=='unsupported_mime'),None)
            html_download=next((a for a in actual if a['url']==d.download_url and a['classification']=='download_url_html'),None)
            if unsupported:row.update(classification='unsupported_mime',reason=unsupported['reason'])
            elif html_download:row.update(classification='download_url_html',reason=html_download['reason'])
        audit.append(row)
        if pos%25==0:
            write(OUT+'acquisition_checkpoint.json',dict(cases=audit,files=files,network_requests=fetcher.requests));print('Resolved',pos+1,'files',len(files),'network',fetcher.requests,flush=True)
    write(MANIFEST,dict(schema_version=2,files=files))
    write(OUT+'resource_audit.json',dict(cases=audit,attempts=attempts,network_requests=fetcher.requests,network_requests_total=fetcher.requests+previous_audit.get('network_requests_total',previous_audit.get('network_requests',0)),allow_network=allow_network,
        classification_counts=dict(Counter(r['classification'] for r in audit))))
    print('Resolved resources:',len(files),'network:',fetcher.requests,flush=True)
    return audit

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--allow-network',action='store_true');a=p.parse_args();acquire(a.allow_network)
