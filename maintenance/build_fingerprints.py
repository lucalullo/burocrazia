"""Build minimized canonical signatures from verified cache; opt-in acquisition.

Run as python -m maintenance.build_fingerprints [--allow-network].
No catalog/editorial row is modified. The runtime never imports this module.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
from dataclasses import asdict
from datetime import UTC,datetime
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

from benchmarks.round3_audit import catalog,read,write,ROOT
from maintenance.fetch import Fetcher,Fetched,AcquisitionError
from maintenance.iri import iri_to_uri
from maintenance.policy import validate_url
from src.document_fingerprints import (PATH,PARAMETERS,VERSION,make_record,validate,read_bundle,binding)
from src.extract import extract_document,ExtractionError

SOURCES={2:'inps',3:'inail',4:'ade',5:'lavoro',10:'mimit',12:'funzione_pubblica',
         14:'garante_privacy',15:'inl',16:'giustizia',17:'mef',18:'anac',19:'unioncamere'}
ORDER=[2,3,4,5,16,15,10,14,17,12,18,19]
OUT='benchmarks/results/round5/'


def atomic_bundle(bundle,path=PATH):
    validate(bundle)
    raw=(json.dumps(bundle,ensure_ascii=False,indent=2)+'\n').encode()
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and path.read_bytes()==raw:return False
    if any(p.is_symlink() or p.is_junction() for p in [path,*path.parents]):raise ValueError('Destinazione collegata rifiutata.')
    if path.exists():
        previous=path.read_bytes();backup=ROOT/'benchmarks/work'/('fingerprints-backup-'+hashlib.sha256(previous).hexdigest()+'.json')
        backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(previous)
    temporary=path.with_suffix('.json.tmp')
    if temporary.exists():raise ValueError('Transazione fingerprint già presente.')
    try:
        with temporary.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
        validate(json.loads(temporary.read_text(encoding='utf-8')))
        os.replace(temporary,path)
    finally:
        if temporary.exists():temporary.unlink()
    return True


def fields(raw,mime):
    names=[]
    if mime=='application/pdf':
        import fitz
        with fitz.open(stream=raw,filetype='pdf') as pdf:
            for page in pdf:
                for widget in page.widgets() or ():names.append(widget.field_name or '')
    else:
        from zipfile import ZipFile
        from lxml import etree
        # Called only after bounded DOCX extraction has validated the archive.
        with ZipFile(BytesIO(raw)) as z:
            root=etree.fromstring(z.read('word/document.xml'),etree.XMLParser(resolve_entities=False,no_network=True))
            ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            names=root.xpath('//w:sdtPr/w:alias/@w:val | //w:sdtPr/w:tag/@w:val | //w:ffData/w:name/@w:val',namespaces=ns)
    return sorted(set(names))[:128]


def receipts(fetcher):
    # Frozen receipts preserve URL aliases when identical bytes had overwritten
    # the cache's single SHA receipt. Every body is still independently verified.
    for name in ['official_documents_v1','official_documents_v2','official_holdout_v1','official_holdout_v2']:
        path=ROOT/'benchmarks/manifests'/ (name+'.json')
        if not path.exists():continue
        for c in read(path)['cases']:
            if 'receipt' in c:
                r=Fetched(**c['receipt']);fetcher.cached[r.requested_url]=r


def build(allow_network=False, network_sources=None, rebuild=False):
    docs,_=catalog();docs=[d for d in docs if d.stato_verifica not in {'demo','rifiutato'}]
    docs.sort(key=lambda d:(ORDER.index(d.source_id),d.id))
    old={} if rebuild else {r['document_id']:r for r in read_bundle()['records']}
    fetcher=Fetcher(ROOT/'benchmarks/cache',allow_network=allow_network,use_cache=True)
    receipts(fetcher)
    rows=[];records=[];manifest=[];closed=set();non_documents=Counter()
    prior_path=ROOT/OUT/'fingerprint_coverage.json'
    prior={r['document_id']:r for r in read(prior_path)['cases']} if prior_path.exists() else {}
    denied_sources={r['source_id'] for r in prior.values() if 'HTTP 403' in r.get('reason','') or 'HTTP 429' in r.get('reason','')}
    for r in prior.values():
        if r.get('reason')=='blocked_host_session' and r['source_id'] not in denied_sources:
            r.update(status='acquisition_failed',reason='Prior session stopped after three non-document responses; this uncached path was not requested.')
    now=datetime.now(UTC).isoformat()
    negative_hashes=set()
    for name in ['official_documents_v1','official_documents_v2','official_holdout_v1','official_holdout_v2']:
        path=ROOT/'benchmarks/manifests'/(name+'.json')
        if path.exists():negative_hashes.update(c['sha256'] for c in read(path)['cases'] if c.get('expected_match_type')=='NO_MATCH')
    from src.recognize import _issuer_entities,normalize_text,_qualifier_conflict,_catalog_features
    for i,d in enumerate(docs):
        key=SOURCES[d.source_id];url=d.download_url;row=dict(document_id=d.id,source_id=d.source_id,source_key=key)
        if not url:row.update(status='dynamic_service_only',reason='No canonical download URL in catalog.')
        else:
            try:
                canonical=validate_url(iri_to_uri(url),key);host=urlsplit(canonical).hostname
                cached=canonical in fetcher.cached or url in fetcher.cached
                if not cached and network_sources is not None and key not in network_sources:
                    rows.append(prior.get(d.id,dict(row,status='acquisition_failed',reason='Source not selected for network acquisition.')));continue
                if not cached and host in closed:raise ValueError('non_document_host_session; stopped after three non-document responses')
                if not cached and host in fetcher.blocked:raise ValueError('blocked_host_session')
                if not cached and fetcher.requests>=390:raise ValueError('network_budget_exhausted')
                r=fetcher.fetch(url,key);raw=fetcher.read(r)
                if raw.startswith(b'%PDF-'):mime='application/pdf';ext='.pdf'
                elif raw.startswith(b'PK'):mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document';ext='.docx'
                else:
                    non_documents[host]+=1
                    if non_documents[host]>=3:closed.add(host)
                    raise ValueError('non_document_response; no challenge bypass')
                row['canonical_file_sha256']=r.sha256
                manifest.append(dict(document_id=d.id,source_id=d.source_id,url=url,final_url=r.final_url,
                    sha256=r.sha256,mime=mime,size=r.size,acquisition_date=r.acquired_at,
                    reuse_note='Verified ignored local cache; no document redistribution rights assumed.'))
                if r.sha256 in negative_hashes:raise ValueError('canonical_conflicts_with_frozen_unknown_label; requires adjudication')
                cache=ROOT/'benchmarks/work/fingerprint-text'/(r.sha256+'.json');cache.parent.mkdir(parents=True,exist_ok=True)
                if cache.exists():ex=json.loads(cache.read_text(encoding='utf-8'))
                else:
                    ex=asdict(extract_document(raw,'canonical'+ext))
                    cache.write_bytes(json.dumps(ex,ensure_ascii=False).encode())
                entities=_issuer_entities(ex['text'],[x.ente for x in docs])
                if entities and normalize_text(d.ente) not in entities:raise ValueError('canonical_issuer_conflict; requires editorial adjudication')
                if _qualifier_conflict(_catalog_features(d).title_tokens,set(normalize_text(ex['text'][:800]).split())):raise ValueError('canonical_subtype_conflict; requires editorial adjudication')
                if d.id in old and old[d.id]['canonical_file_sha256']==r.sha256 and old[d.id]['catalog_binding_sha256']==binding(d) and (ext=='.pdf' or old[d.id]['page_count'] is None):record=old[d.id]
                else:record=make_record(d,raw,ex['text'],receipt=asdict(r),mime=mime,
                    page_count=(ex.get('total_pages') or ex.get('pages_processed')) if ext=='.pdf' else None,
                    method=ex['method'],generated_at=now,field_names=fields(raw,mime))
                if len(record['lexical'])<24:raise ValueError('insufficient_canonical_content')
                records.append(record);row.update(status='built',cached=cached)
            except (ValueError,OSError,ExtractionError) as exc:
                reason=str(exc)
                # robots denial is PER PATH. Only actual HTTP 403/429 block a host.
                status='blocked' if ('403' in reason or '429' in reason or 'robots:' in reason or 'blocked_host' in reason) else 'acquisition_failed'
                row.update(status=status,reason=reason)
        rows.append(row)
        if i%25==0:
            write(OUT+'fingerprint_acquisition_checkpoint.json',dict(cases=rows,network_requests=fetcher.requests))
            print('Canonical',i+1,'/',len(docs),'built',len(records),'network',fetcher.requests,flush=True)
    hashes=defaultdict(list)
    for r in records:hashes[r['canonical_file_sha256']].append(r['document_id'])
    ambiguous={i for ids in hashes.values() if len(ids)>1 for i in ids}
    for row in rows:
        if row['document_id'] in ambiguous:row.update(status='ambiguous_shared_file',reason='Same canonical bytes assigned to distinct catalog identities; no auto-merge.')
    records=[r for r in records if r['document_id'] not in ambiguous]
    bundle=dict(schema_version=1,fingerprint_version=VERSION,parameters=PARAMETERS,records=sorted(records,key=lambda r:r['document_id']))
    changed=atomic_bundle(bundle)
    by_source={}
    for source_id in ORDER:
        group=[r for r in rows if r['source_id']==source_id]
        counts=Counter(r['status'] for r in group)
        by_source[SOURCES[source_id]]=dict(operational_docs=len(group),canonical_files_available=sum('canonical_file_sha256' in r for r in group),fingerprints_built=counts['built'],blocked=counts['blocked'],dynamic_service_only=counts['dynamic_service_only'],acquisition_failed=counts['acquisition_failed'],ambiguous=counts['ambiguous_shared_file'])
    write('benchmarks/manifests/official_fingerprint_cache_v1.json',dict(schema_version=1,files=manifest))
    report=dict(operational_docs=len(docs),canonical_files_available=len(manifest),fingerprints_built=len(records),coverage=len(records)/len(docs),network_requests=fetcher.requests,allow_network=allow_network,bundle_changed=changed,bundle_sha256=hashlib.sha256(PATH.read_bytes()).hexdigest(),by_source=by_source,cases=rows,shared_files=[dict(sha256=h,document_ids=ids) for h,ids in hashes.items() if len(ids)>1])
    write(OUT+'fingerprint_coverage.json',report)
    print('Fingerprint coverage:',len(records),'/',len(docs),flush=True)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--allow-network',action='store_true');p.add_argument('--source',action='append',choices=list(SOURCES.values()));p.add_argument('--rebuild',action='store_true');p.add_argument('--validate-only',action='store_true');a=p.parse_args()
    if a.validate_only:validate(read_bundle());print('Fingerprint schema valid.')
    else:build(a.allow_network,set(a.source) if a.source else None,a.rebuild)
