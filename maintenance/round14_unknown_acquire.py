"""Post-freeze, benchmark-only discovery. No recognition calls or catalog writes."""
import argparse,re
from collections import Counter,deque
from dataclasses import asdict
from urllib.parse import urlsplit,unquote
from urllib.parse import urljoin
from lxml import html
from scripts.round14_common import *
from maintenance.fetch import Fetcher
from maintenance.build_fingerprints import receipts
from maintenance.policy import DOMAINS,validate_url
from maintenance.round11_unknown_acquire import links_with_context
from maintenance.resolve_resources import sniff

ENTITIES={'agid':'Agenzia per l’Italia Digitale','anac':'Autorità Nazionale Anticorruzione','interno':'Ministero dell’Interno',
          'mit':'Ministero delle Infrastrutture e dei Trasporti','mef':'Ministero dell’Economia e delle Finanze',
          'salute':'Ministero della Salute','mimit':'Ministero delle Imprese e del Made in Italy','adm':'Agenzia delle Dogane e dei Monopoli',
          'regione_piemonte':'Regione Piemonte','giustizia':'Ministero della Giustizia / uffici giudiziari','polizia':'Polizia di Stato',
          'aci':'Automobile Club d’Italia','inail':'INAIL','inps':'INPS','lavoro':'Ministero del Lavoro','inl':'Ispettorato Nazionale del Lavoro',
          'funzione_pubblica':'Dipartimento della Funzione Pubblica','garante_privacy':'Garante per la protezione dei dati personali','unioncamere':'Unioncamere','ader':'Agenzia delle Entrate-Riscossione'}
SEEDS={
 'mimit':['https://www.mimit.gov.it/it/normativa/circolari-note-direttive-e-atti-di-indirizzo','https://www.mimit.gov.it/it/normativa/decreti-ministeriali'],
 'salute':['https://www.pnes.salute.gov.it/it/tema/programma-nazionale-equita-nella-salute/documenti-e-linee-guida/'],
 'adm':['https://www.adm.gov.it/portale/dogane/operatore/modulistica'],
 'polizia':['https://www.poliziadistato.it/articolo/1087-Passaporto/'],
 'aci':['https://www.aci.it/i-servizi/servizi-online.html'],
 'inail':['https://www.inail.it/portale/it/atti-e-documenti/note-e-circolari.html'],
 'garante_privacy':['https://www.garanteprivacy.it/home/modulistica-e-servizi-online'],
}

def source(url):
    host=(urlsplit(url).hostname or '').lower()
    return next((k for k in ENTITIES if any(host==d or host.endswith('.'+d) for d in DOMAINS.get(k,()))),None)

def main():
    p=argparse.ArgumentParser();p.add_argument('--allow-network',action='store_true');p.add_argument('--max-requests',type=int,default=0);a=p.parse_args()
    if not 0<=a.max_requests<=400:p.error('request budget 0..400')
    freeze=sealed();assert not (ROOT/'benchmarks/manifests/official_unknown_release_v2.json').exists(),'Selection already locked'
    import maintenance.fetch as fm
    fm.MAX_REQUESTS=a.max_requests
    f=Fetcher(ROOT/'benchmarks/cache',allow_network=a.allow_network,use_cache=True,timeout=8);receipts(f)
    registry=read(REGISTRY);excluded=set(registry['observed_resource_sha256'])
    excluded|={r['sha256'] for r in registry['unknown_resources'] if r['release_v1'] or r['unknown_development'] or r['prediction_observed']}
    excluded|={r['canonical_file_sha256'] for r in read('data/document_recognition_fingerprints_v3.json')['records']}
    candidates={};contexts={};attempts=[];blocked=set();queues={k:deque() for k in ENTITIES};seen=set();pages=Counter()
    for n in [9,10,11]:
        old=read(f'benchmarks/results/round{n}/unknown_candidates.json');blocked.update(old.get('blocked_hosts',[]))
        for c in old.get('candidates',[]):
            key=c.get('source_key',source(c.get('url','')))
            if key in ENTITIES and c.get('sha256') not in excluded:candidates[c['sha256']]=dict(c,source_key=key,entity=ENTITIES[key])
    previous=OUT/'unknown_v2_candidates.json'
    if previous.exists():
        prior=read(previous);assert prior['freeze_commit']==freeze['freeze_git_commit']
        for c in prior['candidates']:
            if c['sha256'] not in excluded:candidates[c['sha256']]=c
        attempts.extend(prior['attempts']);blocked.update(prior['blocked_hosts'])
    def parse(r,key):
        for row in links_with_context(f.read(r),r.final_url,key):
            evidence=dict(listing_url=r.requested_url,listing_sha256=r.sha256,listing_receipt=asdict(r),attachment_label=row['label'],context_heading=row['context_heading'])
            old=contexts.get(row['url'])
            if old is None or len(evidence['context_heading'])>len(old['context_heading']):contexts[row['url']]=evidence
            yield row
        # Follow bounded archive/pagination links as discovery, including
        # numeric years that contain no document-type word in their label.
        tree=html.fromstring(f.read(r),parser=html.HTMLParser(no_network=True))
        for link in tree.xpath('//a[@href]')[:4000]:
            label=' '.join(link.text_content().split());href=link.get('href','')
            if not (re.fullmatch(r'20(?:1[5-9]|2[0-6])',label) or re.search(r'(?:[?&]page=|[?&]_cur=|/page/)',href) or label.lower() in ['successivo','successiva','next','pagina successiva']):continue
            try:url=validate_url(urljoin(r.final_url,href),key)
            except ValueError:continue
            yield dict(url=url,label=label,context_heading='',is_file=False)
    # Cached listings are official evidence. Unobserved cached attachments may
    # be fresh predictions even when their acquisition date predates freeze.
    for url,r in list(f.cached.items()):
        key=source(url)
        if not key:continue
        try:
            if 'html' in r.content_type:
                for row in parse(r,key):
                    if row['is_file'] or len(queues[key])<80:queues[key].append((row['url'],0 if row['is_file'] else 1))
            elif r.sha256 not in excluded and ('pdf' in r.content_type or re.search(r'\.(pdf|docx)(?:[?#]|$)',url,re.I)):
                raw=f.read(r);mime=sniff(raw)
                if mime in ['application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
                    candidates.setdefault(r.sha256,dict(id='U14C-'+r.sha256[:16],source_key=key,entity=ENTITIES[key],url=r.requested_url,title=unquote(urlsplit(url).path.rsplit('/',1)[-1]),sha256=r.sha256,format='pdf' if mime=='application/pdf' else 'docx',receipt=asdict(r),origin='cached_official_unobserved'))
        except (ValueError,OSError):continue
    for key,urls in SEEDS.items():queues[key].extend((u,0) for u in urls)
    # Existing official source roots from previous bounded discovery are
    # reused as listings only; previous prediction resources remain excluded.
    from maintenance.round10_unknown_acquire import SEEDS as old_seeds
    from maintenance.round11_unknown_acquire import SEEDS as later_seeds
    for key,(_,urls) in old_seeds.items():queues[key].extend((u,0) for u in urls)
    for key,urls in later_seeds.items():queues[key].extend((u,0) for u in urls)
    counts=Counter(c['source_key'] for c in candidates.values())
    def export():
        for c in candidates.values():
            if c['url'] in contexts:c['source_evidence']=contexts[c['url']]
        atomic_json(previous,dict(schema_version=1,freeze_commit=freeze['freeze_git_commit'],created_at=now(),candidates=sorted(candidates.values(),key=lambda c:c['sha256']),attempts=attempts,
                    source_counts=dict(counts),network_requests_this_invocation=f.requests,allow_network=a.allow_network,blocked_hosts=sorted(blocked),
                    policy='Post-freeze discovery, not release selection. Cached unobserved resources allowed; known canonical, observed SHA, release v1 and development unknown excluded. Bounded sequential requests, robots and institutional allowlist. No recognition or catalog changes.'))
    export();print('R14 cached candidate counts',dict(counts),flush=True)
    while a.allow_network and any(queues.values()) and f.requests<a.max_requests:
        progressed=False
        for key in queues:
            if not queues[key] or counts[key]>=40:continue
            url,depth=queues[key].popleft()
            if url in seen:continue
            seen.add(url);progressed=True
            try:
                if urlsplit(url).netloc in blocked and url not in f.cached:raise ValueError('prior_403_429_no_retry')
                r=f.fetch(url,key);raw=f.read(r);mime=sniff(raw)
                if mime in ['application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
                    if r.sha256 not in excluded and r.sha256 not in candidates:
                        meta=contexts.get(url,{})
                        candidates[r.sha256]=dict(id='U14C-'+r.sha256[:16],source_key=key,entity=ENTITIES[key],url=r.requested_url,title=meta.get('attachment_label') or unquote(urlsplit(url).path.rsplit('/',1)[-1]),sha256=r.sha256,format='pdf' if mime=='application/pdf' else 'docx',receipt=asdict(r),origin='round14_official_discovery',source_evidence=meta)
                        counts[key]+=1
                    result='official_candidate_or_excluded_prior_resource'
                elif mime=='text/html' and depth<=2 and pages[key]<15:
                    pages[key]+=1;result='official_listing'
                    for row in parse(r,key):
                        if row['url'] not in seen:
                            if row['is_file']:queues[key].appendleft((row['url'],depth+1))
                            elif depth<2:queues[key].append((row['url'],depth+1))
                else:result='unsupported_or_depth_limit:'+mime
                attempts.append(dict(url=url,source=key,result=result,receipt=asdict(r)))
            except (ValueError,OSError) as exc:
                status=getattr(exc,'status',None)
                if status in [403,429]:blocked.add(urlsplit(url).netloc)
                attempts.append(dict(url=url,source=key,result=str(exc),http_status=status))
            export();print('R14 discovery',key,'sources',len(counts),'counts',dict(counts),'requests',f.requests,flush=True)
            if f.requests>=a.max_requests:break
        if not progressed:break
    export();sealed()

if __name__=='__main__':main()
