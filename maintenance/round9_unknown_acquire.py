"""Acquire bounded informational candidates from existing official sources.

Discovery is not truth. This only records receipts; the separate offline audit
must exclude catalog identities, families and uncertain candidates before use.
"""
import argparse,json,hashlib,re
from collections import Counter,defaultdict
from dataclasses import asdict
from urllib.parse import urlsplit,urljoin,unquote
from lxml import html
from maintenance.fetch import Fetcher
from maintenance.build_fingerprints import receipts,SOURCES
from maintenance.policy import validate_url
from maintenance.iri import iri_to_uri
from maintenance.resolve_resources import sniff
from benchmarks.round3_audit import ROOT,read
from benchmarks.transactional_writer import atomic_json

OUT=ROOT/'benchmarks/results/round9'
WORDS=re.compile(r'\b(?:guid[ae]|manual[ei]|istruzion\w*|circolar[ei]|provvediment\w*|decret\w*|regolament\w*|direttiv\w*)\b',re.I)

def main():
    p=argparse.ArgumentParser();p.add_argument('--allow-network',action='store_true');a=p.parse_args()
    f=Fetcher(ROOT/'benchmarks/cache',allow_network=a.allow_network,use_cache=True,timeout=8);receipts(f)
    sources=read('maintenance/sources.json');entities={s['key']:s['ente'] for s in sources};candidates={};links=defaultdict(dict);pages=defaultdict(dict);attempts=[]
    def source(url):
        for key in SOURCES.values():
            try:validate_url(url,key);return key
            except ValueError:pass
    for name in ['official_documents_v2','official_holdout_v1','official_holdout_v2']:
        for c in read('benchmarks/manifests/'+name+'.json')['cases']:
            if c.get('expected_match_type')=='NO_MATCH':candidates.setdefault(c['sha256'],dict(c,origin='historical_unknown_candidate'))
    # Parse only locally cached listing pages; never execute page scripts.
    for url,r in list(f.cached.items()):
        if 'html' not in r.content_type:continue
        key=source(url)
        if not key:continue
        try:
            root=html.fromstring(f.read(r),parser=html.HTMLParser(no_network=True))
            for node in root.xpath('//a[@href]')[:4000]:
                label=' '.join(node.text_content().split())[:600];target=iri_to_uri(urljoin(r.final_url,node.get('href','')))
                try:target=validate_url(target,key)
                except ValueError:continue
                if WORDS.search(label):
                    if re.search(r'\.(?:pdf|docx)(?:[?#/]|$)',unquote(target),re.I):links[key].setdefault(target,dict(title=label,listing_url=url,listing_sha256=r.sha256))
                    elif target not in f.cached:pages[key].setdefault(target,label)
        except (ValueError,OSError):continue
    # Prefer absent/underrepresented sources, cap each source and total requests.
    blocked=set(read('benchmarks/results/round8/recovery_attempts.json')['blocked_hosts']);closed=set();count=Counter(c['source_key'] for c in candidates.values())
    # One additional level, at most six official informational landing pages
    # per existing source. No generic crawler and no retry of blocked hosts.
    for key in sorted(pages,key=lambda k:(count[k],k)):
        if count[key]>=40:continue
        for url,label in sorted(pages[key].items())[:6]:
            try:
                if urlsplit(url).netloc in blocked:raise ValueError('prior_403_429_no_retry')
                if f.requests>=120:raise ValueError('bounded_round9_network_budget')
                r=f.fetch(url,key);raw=f.read(r)
                if 'html' not in r.content_type:raise ValueError('not_html_listing')
                root=html.fromstring(raw,parser=html.HTMLParser(no_network=True))
                for node in root.xpath('//a[@href]')[:4000]:
                    title=' '.join(node.text_content().split())[:600];target=iri_to_uri(urljoin(r.final_url,node.get('href','')))
                    try:target=validate_url(target,key)
                    except ValueError:continue
                    if WORDS.search(title) and re.search(r'\.(?:pdf|docx)(?:[?#/]|$)',unquote(target),re.I):links[key].setdefault(target,dict(title=title,listing_url=url,listing_sha256=r.sha256))
                attempts.append(dict(url=url,source=key,result='discovery_page',sha256=r.sha256))
            except (ValueError,OSError) as exc:
                status=getattr(exc,'status',None)
                if status in [403,429]:blocked.add(urlsplit(url).netloc);closed.add(key)
                attempts.append(dict(url=url,source=key,result=str(exc),http_status=status))
    order=sorted(links,key=lambda k:(count[k],k));positions=Counter()
    for _ in range(30):
        for key in order:
            if key in closed or count[key]>=40:continue
            items=sorted(links[key].items())
            if positions[key]>=len(items):continue
            url,meta=items[positions[key]];positions[key]+=1
            try:
                if url not in f.cached and urlsplit(url).netloc in blocked:raise ValueError('prior_403_429_no_retry')
                if url not in f.cached and f.requests>=120:raise ValueError('bounded_round9_network_budget')
                receipt=f.fetch(url,key);raw=f.read(receipt);mime=sniff(raw)
                if mime not in ['application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document']:raise ValueError('not_supported_document:'+mime)
                c=dict(id='U9C-'+receipt.sha256[:16],source_key=key,entity=entities[key],url=url,title=meta['title'],sha256=receipt.sha256,format='pdf' if mime=='application/pdf' else 'docx',acquired_at=receipt.acquired_at,receipt=asdict(receipt),origin='round9_official_listing',source_evidence=meta)
                if receipt.sha256 not in candidates:candidates[receipt.sha256]=c;count[key]+=1
                attempts.append(dict(url=url,source=key,result='official_candidate',sha256=receipt.sha256))
            except (ValueError,OSError) as exc:
                status=getattr(exc,'status',None)
                if status in [403,429]:blocked.add(urlsplit(url).netloc);closed.add(key)
                attempts.append(dict(url=url,source=key,result=str(exc),http_status=status))
        atomic_json(OUT/'unknown_acquisition_checkpoint.json',dict(candidates=list(candidates.values()),attempts=attempts,network_requests=f.requests))
    atomic_json(OUT/'unknown_candidates.json',dict(candidates=list(candidates.values()),attempts=attempts,network_requests=f.requests,allow_network=a.allow_network,listing_candidates_by_source={k:len(v) for k,v in links.items()},blocked_hosts=sorted(blocked),scope='Discovery only. Historical NO labels are not automatically confirmed. No catalog additions. Maximum120 requests,30 candidates/source,robots/allowlist,blocked hosts not retried.'))
    print('Unknown candidates',len(candidates),dict(count),'network',f.requests,flush=True)
if __name__=='__main__':main()
