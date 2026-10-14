"""Opt-in official unknown4 discovery; no recognition and no catalog writes."""
import argparse,re
from collections import Counter,deque
from dataclasses import asdict
from urllib.parse import urlsplit,unquote
from scripts.round21_common import *
from maintenance.fetch import Fetcher
from maintenance.build_fingerprints import receipts
from maintenance.round17_unknown_acquire import ENTITIES,SEEDS,source
from maintenance.round11_unknown_acquire import links_with_context
from maintenance.resolve_resources import sniff
from maintenance.policy import validate_url,canonical_url

def exclusions():
    registry=read('benchmarks/reference/benchmark_contamination_registry_v6.json');seen=set(registry['observed_resource_sha256']);urls=set()
    for c in registry['unknown_resources']:
        if c.get('release_v1') or c.get('unknown_development') or c.get('prediction_observed'):
            seen.add(c['sha256']);urls.update(canonical_url(u) for u in [c.get('official_url'),c.get('url'),c.get('receipt',{}).get('final_url')] if u)
    for r in read('data/document_recognition_fingerprints_v3.json')['records']:
        seen.add(r['canonical_file_sha256']);urls.update(canonical_url(u) for u in [r['url'],r['final_url']])
    # Catalog resources that failed fingerprint qualification are still known
    # identities. Their absence from the active index cannot make them unknown.
    for p in ROOT.glob('benchmarks/manifests/official_fingerprint_cache_v*.json'):
        for r in read(p).get('files',[]):
            if r.get('sha256'):seen.add(r['sha256'])
            urls.update(canonical_url(u) for u in [r.get('url'),r.get('final_url')] if u)
    for p in [ROOT/'benchmarks/work/round20/development-inputs.json']:
        seen.update(c['sha256'] for c in read(p)['rows'] if c.get('sha256'))
    for p in OUT.glob('development_observations_*.json'):seen.update(c['input_sha256'] for c in read(p)['cases'] if c.get('input_sha256'))
    return seen,urls

def main():
    p=argparse.ArgumentParser();p.add_argument('--allow-network',action='store_true');p.add_argument('--max-requests',type=int,default=0);a=p.parse_args()
    assert 0<=a.max_requests<=400
    preserved();assert read(OUT/'calibration_v7.json')['passed'] and read(OUT/'v6_preflight.json')['passed']
    assert not (OUT/'freeze_manifest.json').exists() and not (ROOT/'benchmarks/manifests/official_unknown_release_v4.json').exists()
    import maintenance.fetch as fm
    fm.MAX_REQUESTS=a.max_requests
    f=Fetcher(ROOT/'benchmarks/cache',allow_network=a.allow_network,use_cache=True,timeout=8);receipts(f);excluded,oldurls=exclusions()
    previous=OUT/'unknown_v4_candidates.json';prior=read(previous) if previous.exists() else {};candidates={c['sha256']:c for c in prior.get('candidates',[])};attempts=prior.get('attempts',[]);blocked=set(prior.get('blocked_hosts',[]));seen={c['url'] for c in attempts};contexts={};queues={k:deque() for k in ENTITIES}
    for n in [9,10,11,14,16,17]:
        name='unknown_v3_candidates' if n in [16,17] else 'unknown_v2_candidates' if n==14 else 'unknown_candidates';old=read(f'benchmarks/results/round{n}/{name}.json');blocked.update(old.get('blocked_hosts',[]))
    def candidate(r,key,origin):
        if r.sha256 in excluded or canonical_url(r.requested_url) in oldurls or canonical_url(r.final_url) in oldurls:return
        mime=sniff(f.read(r))
        if mime not in ['application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document']:return
        candidates.setdefault(r.sha256,dict(id='U21C-'+r.sha256[:16],source_key=key,entity=ENTITIES[key],url=r.requested_url,sha256=r.sha256,format='pdf' if mime=='application/pdf' else 'docx',title=unquote(urlsplit(r.requested_url).path.rsplit('/',1)[-1]),receipt=asdict(r),origin=origin))
    def parse(r,key,depth):
        for row in links_with_context(f.read(r),r.final_url,key):
            contexts[row['url']]=dict(listing_url=r.requested_url,listing_sha256=r.sha256,attachment_label=row['label'],context_heading=row['context_heading'])
            if row['is_file']:queues[key].append((row['url'],depth+1))
            elif depth<2 and len(queues[key])<120:queues[key].append((row['url'],depth+1))
    for url,r in list(f.cached.items()):
        key=source(url)
        if not key:continue
        try:
            if 'html' in r.content_type:parse(r,key,0)
            else:candidate(r,key,'cached_official_never_predicted')
        except (ValueError,OSError):continue
    from maintenance.round10_unknown_acquire import SEEDS as earlier
    from maintenance.round11_unknown_acquire import SEEDS as later
    for key,urls in SEEDS.items():queues[key].extend((u,0) for u in urls)
    for key,(_,urls) in earlier.items():queues[key].extend((u,0) for u in urls)
    for key,urls in later.items():queues[key].extend((u,0) for u in urls)
    def export():
        for c in candidates.values():
            if c['url'] in contexts:c['source_evidence']=contexts[c['url']]
        save('unknown_v4_candidates',dict(schema_version=1,phase='pre_freeze_metadata_only',candidates=sorted(candidates.values(),key=lambda c:c['sha256']),attempts=attempts,blocked_hosts=sorted(blocked),source_counts=dict(Counter(c['source_key'] for c in candidates.values())),network_requests_this_invocation=f.requests,allow_network=a.allow_network,recognition_calls=0,excluded_sha256_count=len(excluded),created_at=now(),policy='Official institutional allowlist, robots, bounded sequential requests. No403/429 bypass/retry. Fresh relative to known canonical resources and all prior prediction/development resources; no catalog changes.'))
    export();print('R21 fresh cached candidates',len(candidates),dict(Counter(c['source_key'] for c in candidates.values())),flush=True)
    pages=Counter()
    while a.allow_network and f.requests<a.max_requests and any(queues.values()):
        progress=False;counts=Counter(c['source_key'] for c in candidates.values())
        for key in sorted(queues,key=lambda k:counts[k]):
            if counts[key]>=100:continue
            while queues[key] and (queues[key][0][0] in seen or canonical_url(queues[key][0][0]) in oldurls):queues[key].popleft()
            if not queues[key]:continue
            url,depth=queues[key].popleft();seen.add(url);progress=True
            try:
                if urlsplit(url).netloc in blocked and url not in f.cached:raise ValueError('prior403_429_host_block_preserved')
                r=f.fetch(url,key);mime=sniff(f.read(r))
                if mime in ['application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document']:candidate(r,key,'round21_official_acquisition');result='attachment_or_excluded'
                elif mime=='text/html' and depth<=2 and pages[key]<25:pages[key]+=1;parse(r,key,depth);result='official_listing'
                else:result='unsupported_or_bounded_depth'
                attempts.append(dict(url=url,source=key,result=result,receipt=asdict(r)))
            except (ValueError,OSError) as exc:
                status=getattr(exc,'status',None)
                if status in [403,429]:blocked.add(urlsplit(url).netloc)
                attempts.append(dict(url=url,source=key,result=str(exc),http_status=status))
            export();print('R21 discovery',key,'candidates',len(candidates),'sources',len({c['source_key'] for c in candidates.values()}),'requests',f.requests,flush=True)
            if f.requests>=a.max_requests:break
        if not progress:break
    export()
if __name__=='__main__':main()
