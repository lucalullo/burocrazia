"""Official benchmark-only discovery with attachment-local title provenance."""
import argparse,re
from collections import Counter,deque
from dataclasses import asdict
from urllib.parse import urljoin,urlsplit,unquote
from lxml import html
from benchmarks.round3_audit import ROOT,read
from benchmarks.transactional_writer import atomic_json
from maintenance.fetch import Fetcher
from maintenance.build_fingerprints import receipts
from maintenance.policy import validate_url
from maintenance.iri import iri_to_uri
from maintenance.resolve_resources import sniff
OUT=ROOT/'benchmarks/results/round11'
ENTITIES={'interno':'Ministero dell’Interno','giustizia':'Ministero della Giustizia','regione_piemonte':'Regione Piemonte','mit':'Ministero delle Infrastrutture e dei Trasporti','agid':'Agenzia per l’Italia Digitale','anac':'Autorità Nazionale Anticorruzione','mef':'Ministero dell’Economia e delle Finanze'}
SEEDS={
 'interno':['https://www.interno.gov.it/it/circolari','https://prefettura.interno.gov.it/it/prefetture/bari/circolari-0'],
 'giustizia':['https://www.giustizia.it/giustizia/it/mg_1_8.page'],
 'regione_piemonte':['https://bandi.regione.piemonte.it/contributi-finanziamenti/progetti-i-giovani-ambito-sportivo','https://servizi.regione.piemonte.it/catalogo/presentazione-domanda-flaidom','https://www.regione.piemonte.it/web/sites/default/files/media/documenti/2020-05/note_operative_per_la_compilazione_della_domanda.pdf','https://trasparenza.regione.piemonte.it/media/27859/download']}
WORDS=re.compile(r'\b(?:circolare|decreto|guida|manuale|istruzioni|domanda|modulo|allegato|modulistica|documentazione)\b',re.I)

def links_with_context(raw,base,key):
 if len(raw)>8*1024*1024:raise ValueError('listing_byte_limit')
 tree=html.fromstring(raw,parser=html.HTMLParser(no_network=True))
 headings=[' '.join(n.text_content().split())[:700] for n in tree.xpath('//h1|//h2|//h3|//title')]
 useful=[t for t in headings if len(t.split())>=8 and WORDS.search(t)]
 page_title=useful[0] if useful else ''
 rows=[]
 for a in tree.xpath('//a[@href]')[:4000]:
  label=' '.join(a.text_content().split())[:600]
  try:url=validate_url(iri_to_uri(urljoin(base,a.get('href',''))),key)
  except ValueError:continue
  file=bool(re.search(r'\.(?:pdf|docx)(?:[?#/]|$)',unquote(url),re.I) or re.search(r'/media/\d+/download',url) or a.get('download') is not None)
  if not file and not WORDS.search(label):continue
  local='';parent=a
  for _ in range(5):
   parent=parent.getparent()
   if parent is None:break
   hs=[' '.join(n.text_content().split())[:700] for n in parent.xpath('.//h2|.//h3')]
   hs=[t for t in hs if len(t.split())>=8 and WORDS.search(t)]
   if len(hs)==1:local=hs[0];break
  rows.append(dict(url=url,label=label,context_heading=local or page_title,is_file=file))
 return rows

def main():
 p=argparse.ArgumentParser();p.add_argument('--allow-network',action='store_true');p.add_argument('--max-requests',type=int,default=140);a=p.parse_args()
 if not 1<=a.max_requests<=200:p.error('request budget1..200')
 import maintenance.fetch as fetch_module
 fetch_module.MAX_REQUESTS=a.max_requests
 f=Fetcher(ROOT/'benchmarks/cache',allow_network=a.allow_network,use_cache=True,timeout=8);receipts(f)
 blocked=set(read('benchmarks/results/round10/unknown_candidates.json')['blocked_hosts'])
 old=read('benchmarks/results/round10/unknown_candidates.json')['candidates'];candidates={c['sha256']:dict(c) for c in old};contexts={};attempts=[]
 def parse(r,key):
  for row in links_with_context(f.read(r),r.final_url,key):
   evidence=dict(listing_url=r.requested_url,listing_sha256=r.sha256,listing_receipt=asdict(r),attachment_label=row['label'],context_heading=row['context_heading'])
   previous=contexts.get(row['url'])
   if previous is None or len(evidence['context_heading'])>len(previous['context_heading']):contexts[row['url']]=evidence
   yield row
 # Recover actual detail-heading evidence for the previously generic labels.
 for url,r in list(f.cached.items()):
  if 'html' not in r.content_type:continue
  key=next((k for k in ENTITIES if any(urlsplit(url).hostname==d or urlsplit(url).hostname.endswith('.'+d) for d in __import__('maintenance.policy',fromlist=['DOMAINS']).DOMAINS[k])),None)
  if key:
   try:list(parse(r,key))
   except (ValueError,OSError):pass
 queues={k:deque((u,0) for u in urls) for k,urls in SEEDS.items()};seen=set();pages=Counter();count=Counter()
 while any(queues.values()) and f.requests<a.max_requests:
  for key in queues:
   if not queues[key] or count[key]>=24:continue
   url,depth=queues[key].popleft()
   if url in seen:continue
   seen.add(url)
   try:
    if urlsplit(url).netloc in blocked and url not in f.cached:raise ValueError('prior_403_429_no_retry')
    if url in SEEDS[key] and a.allow_network:f.cached.pop(url,None)
    r=f.fetch(url,key);raw=f.read(r);mime=sniff(raw)
    if mime in ['application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
     meta=contexts.get(url,{})
     candidates.setdefault(r.sha256,dict(id='U11C-'+r.sha256[:16],source_key=key,entity=ENTITIES[key],url=r.requested_url,title=meta.get('attachment_label') or unquote(urlsplit(url).path.rsplit('/',1)[-1]),sha256=r.sha256,format='pdf' if mime=='application/pdf' else 'docx',receipt=asdict(r),origin='round11_official_discovery'))
     count[key]+=1;result='official_candidate'
    elif mime=='text/html' and depth<=2 and pages[key]<12:
     pages[key]+=1;result='official_listing'
     for item in parse(r,key):
      if item['url'] in seen:continue
      if item['is_file']:queues[key].appendleft((item['url'],depth+1))
      elif depth<2:queues[key].append((item['url'],depth+1))
    else:result='unsupported_or_depth_limit:'+mime
    attempts.append(dict(url=url,source=key,result=result,sha256=r.sha256,receipt=asdict(r)))
   except (ValueError,OSError) as exc:
    status=getattr(exc,'status',None)
    if status in [403,429]:blocked.add(urlsplit(url).netloc)
    attempts.append(dict(url=url,source=key,result=str(exc),http_status=status))
   for k in queues:
    if count[k]>=24:queues[k].clear()
   print('R11 unknown discovery',key,'new',dict(count),'requests',f.requests,flush=True)
 for c in candidates.values():
  if c['url'] in contexts:c['source_evidence']=contexts[c['url']]
 atomic_json(OUT/'unknown_candidates.json',dict(candidates=list(candidates.values()),attempts=attempts,network_requests=f.requests,allow_network=a.allow_network,blocked_hosts=sorted(blocked),scope='Benchmark-only; catalog unchanged. Cached attachment/detail context and bounded live official sources; robots/allowlist, no bypass. Discovery is not truth.'))
 print('R11 candidate total',len(candidates),flush=True)

if __name__=='__main__':main()
