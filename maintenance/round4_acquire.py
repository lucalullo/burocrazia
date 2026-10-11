"""Opt-in, bounded official acquisition for frozen v2; never imported by runtime."""
import argparse
from collections import Counter
from dataclasses import asdict
from datetime import UTC,datetime
import hashlib
from benchmarks.round4_holdout import ROOT,OUT,MANIFEST,previous,require_freeze,leakage_report
from benchmarks.round4_common import read,write
from benchmarks.holdout_leakage import collision
from maintenance.fetch import Fetcher

def acquire(allow_network=False):
    event=require_freeze()
    if (ROOT/MANIFEST).exists():raise ValueError('Manifest v2 already exists; no overwrite.')
    plan=read(OUT+'holdout_v2_plan.json');prior=previous();hashes={c.get('sha256') for c in prior};cases=[];attempts=[];counts=Counter();used_ids=set();non_documents=Counter();closed=set();positive=negative=0
    fetcher=Fetcher(ROOT/'benchmarks/cache',allow_network=allow_network,use_cache=False)
    # Negative budget reserved before positive acquisition. Selection never
    # depends on extraction or recognition; malformed responses are reported.
    for c in plan['negative_options']+plan['positive_options']:
        neg=c['expected_match_type']=='NO_MATCH';key=c['source_key']
        if key in closed:continue
        if neg and negative>=75:continue
        if not neg and (positive>=200 or counts[key]>=40 or c['document_id'] in used_ids):continue
        if fetcher.requests>=395:break
        try:
            receipt=fetcher.fetch(c['url'],key);raw=fetcher.read(receipt)
            fmt='pdf' if raw.startswith(b'%PDF-') else 'docx' if raw.startswith(b'PK') else None
            if not fmt:
                non_documents[key]+=1
                if non_documents[key]>=3:closed.add(key)
                raise ValueError('Non-document response; close source after three, no challenge bypass.')
            if receipt.sha256 in hashes:
                attempts.append(dict(url=c['url'],source_key=key,status='duplicate_or_prior_hash',sha256=receipt.sha256));continue
            item=dict(c,id=f'OH2-{len(cases)+1:03}',format=fmt,sha256=receipt.sha256,acquired_at=receipt.acquired_at,cache_key=receipt.sha256+'.body',receipt=asdict(receipt),label_basis='Official listing identity; informational exclusions labelled before recognition. No result-based relabelling.',reuse_conditions='Ignored local cache only; no redistribution rights assumed.')
            overlap=next((collision(item,p) for p in prior+cases if collision(item,p)),None)
            if overlap:
                attempts.append(dict(url=c['url'],source_key=key,status='leakage_excluded',reason=overlap));continue
            cases.append(item);hashes.add(receipt.sha256)
            if neg:negative+=1
            else:positive+=1;counts[key]+=1;used_ids.add(c['document_id'])
            attempts.append(dict(url=c['url'],source_key=key,status='downloaded',sha256=receipt.sha256,acquired_at=receipt.acquired_at))
        except (ValueError,OSError) as exc:
            reason=str(exc)
            if '403' in reason or '429' in reason or 'robots:' in reason:closed.add(key)
            attempts.append(dict(url=c['url'],source_key=key,status='failed',reason=reason))
        if len(attempts)%10==0:print('v2 acquired',positive,'positive',negative,'negative;',len(attempts),'attempts;',fetcher.requests,'network requests',flush=True)
    manifest=dict(schema_version=1,corpus_id='official_holdout_v2',independent=True,freeze=event,created_at=datetime.now(UTC).isoformat(),selection=plan['selection'],cases=cases)
    write(MANIFEST,manifest);leakage=leakage_report(cases);write(OUT+'holdout_v2_leakage.json',leakage);assert leakage['passed']
    write(OUT+'holdout_v2_acquisition.json',dict(positives=positive,negatives=negative,source_counts=dict(counts),network_requests=fetcher.requests,closed_sources=sorted(closed),attempts=attempts,complete_target=positive>=200 and negative>=75,manifest_sha256=hashlib.sha256((ROOT/MANIFEST).read_bytes()).hexdigest()))
    print('Acquisition ended:',positive,negative,dict(counts),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--allow-network',action='store_true');a=p.parse_args();acquire(a.allow_network)
