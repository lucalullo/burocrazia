"""Bounded official benchmark discovery, separate from catalog and runtime.

Discovery is not truth. An offline auditor must adjudicate every attachment.
"""
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

OUT=ROOT/'benchmarks/results/round10'
SEEDS={
 'agid':('Agenzia per l’Italia Digitale',[
  'https://www.agid.gov.it/it/linee-guida',
  'https://www.agid.gov.it/it/agenzia/atti-documenti',
  'https://trasparenza.agid.gov.it/page/30/modulistica.html']),
 'interno':('Ministero dell’Interno',[
  'https://www.interno.gov.it/it/circolari',
  'https://libertaciviliimmigrazione.dlci.interno.gov.it/documentazione/circolari',
  'https://dait.interno.gov.it/ricerca?f%5B0%5D=content_type%3Acircolare&page=0']),
 'mit':('Ministero delle Infrastrutture e dei Trasporti',[
  'https://www.mit.gov.it/normativa',
  'https://lavoromarittimo.mit.gov.it/circolari/',
  'https://trasparenza.mit.gov.it/archivio19_regolamenti_0_6463.html']),
 'salute':('Ministero della Salute',[
  'https://www.salute.gov.it/portale/documentazione/p6_2_0.jsp?id=773',
  'https://www.salute.gov.it/new/it/pubblicazione/sistema-cup-linee-guida-nazionali/',
  'https://www.pnes.salute.gov.it/it/tema/programma-nazionale-equita-nella-salute/documenti-e-linee-guida/',
  'https://www.pnrr.salute.gov.it/it/news-e-media/notizie/pnrr-gazzetta-ufficiale-le-linee-guida-modello-digitale-lattuazione/']),
 'mef':('Ministero dell’Economia e delle Finanze',[
  'https://revisionelegale.rgs.mef.gov.it/area-pubblica/normativa/Circolari/']),
 'anac':('Autorità Nazionale Anticorruzione',[
  'https://www.anticorruzione.it/consulta-i-documenti',
  'https://www.anticorruzione.it/-/accesso-civico-e-accesso-civico-generalizzato']),
 'polizia':('Polizia di Stato',[
  'https://www.poliziadistato.it/articolo/1087-Passaporto/']),
 'giustizia':('Ministero della Giustizia / uffici giudiziari',[
  'https://www.giustizia.it/giustizia/it/mg_1_8.page'])}
WORDS=re.compile(r'\b(?:guid[ae]|manual[ei]|istruzion\w*|circolar[ei]|provvediment\w*|decret\w*|regolament\w*|direttiv\w*|modul\w*|domanda|richiesta|delibera|allegato)\b',re.I)
DIRECT=[
 ('salute','https://www.salute.gov.it/new/sites/default/files/imported/C_17_opuscoliPoster_421_2_alleg.pdf','Guida per l’assistenza a casa per il cittadino che è curato a casa e per la sua famiglia'),
 ('salute','https://www.salute.gov.it/imgs/C_17_pubblicazioni_1255_allegato.pdf','Guida in breve Dati di registrazione e gestione del fascicolo')]

def attachment_links(raw,base,key):
 """Inert bounded HTML parsing; final fetch rechecks policy and redirects."""
 root=html.fromstring(raw,parser=html.HTMLParser(no_network=True))
 result=[]
 for a in root.xpath('//a[@href]')[:4000]:
  title=' '.join(a.text_content().split())[:600]
  try:url=validate_url(iri_to_uri(urljoin(base,a.get('href',''))),key)
  except ValueError:continue
  file=bool(re.search(r'\.(?:pdf|docx)(?:[?#/]|$)',unquote(url),re.I))
  if file or WORDS.search(title):result.append((url,title,file))
 return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--allow-network',action='store_true');p.add_argument('--max-requests',type=int,default=300);a=p.parse_args()
 if not 1<=a.max_requests<=350:p.error('max requests must be 1..350')
 import maintenance.fetch as fetch_module
 fetch_module.MAX_REQUESTS=a.max_requests
 f=Fetcher(ROOT/'benchmarks/cache',allow_network=a.allow_network,use_cache=True,timeout=8);receipts(f)
 blocked=set(read('benchmarks/results/round9/recovery_attempts.json')['blocked_hosts'])
 checkpoint=OUT/'unknown_candidates.json'
 prior=read('benchmarks/results/round10/unknown_candidates.json') if checkpoint.exists() else dict(candidates=[],attempts=[])
 candidates={c['sha256']:c for c in prior['candidates']};attempts=list(prior['attempts'])
 seen={r['url'] for r in attempts};count=Counter(c['source_key'] for c in candidates.values())
 queues={k:deque((u,'Official discovery page',0,False) for u in urls) for k,(_,urls) in SEEDS.items()};page_count=Counter()
 for key,url,title in DIRECT:queues[key].appendleft((url,title,0,True))
 while any(queues.values()) and f.requests<a.max_requests:
  for key in sorted(queues,key=lambda k:(count[k],k)):
   if not queues[key] or count[key]>=32:continue
   url,title,depth,isfile=queues[key].popleft()
   if url in seen:continue
   seen.add(url)
   if not isfile and page_count[key]>=15:continue
   try:
    if url not in f.cached and urlsplit(url).netloc in blocked:raise ValueError('prior_403_429_no_retry')
    if f.requests>=a.max_requests:raise ValueError('round10_request_budget')
    r=f.fetch(url,key);raw=f.read(r);mime=sniff(raw)
    if mime in ['application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
     c=dict(id='U10C-'+r.sha256[:16],source_key=key,entity=SEEDS[key][0],url=r.requested_url,title=title,sha256=r.sha256,format='pdf' if mime=='application/pdf' else 'docx',receipt=asdict(r),origin='round10_official_discovery')
     if r.sha256 not in candidates:candidates[r.sha256]=c;count[key]+=1
     result='official_candidate'
    elif mime=='text/html' and depth<=2:
     result='official_listing';page_count[key]+=1
     for target,label,file in attachment_links(raw,r.final_url,key):
      if target in seen:continue
      if file:queues[key].appendleft((target,label or title,depth+1,True))
      elif depth<2 and page_count[key]<15:queues[key].append((target,label,depth+1,False))
    else:result='unsupported_or_depth_limit:'+mime
    attempts.append(dict(url=url,source=key,result=result,sha256=r.sha256))
   except (ValueError,OSError) as exc:
    status=getattr(exc,'status',None)
    if status in [403,429]:blocked.add(urlsplit(url).netloc)
    attempts.append(dict(url=url,source=key,result=str(exc),http_status=status))
   atomic_json(checkpoint,dict(candidates=list(candidates.values()),attempts=attempts,network_requests=prior.get('network_requests',0)+f.requests,session_network_requests=f.requests,allow_network=a.allow_network,blocked_hosts=sorted(blocked),counts=dict(count),scope='Official benchmark discovery only; max32 candidates/source, bounded depth2/pages15/source, robots/allowlist/no bypass; not truth and no catalog mutation.'))
   print('Unknown discovery',key,dict(count),'requests',f.requests,flush=True)
  # Sources at their cap need no more requests.
  for key in queues:
   if count[key]>=32:queues[key].clear()
 print('Candidates',len(candidates),dict(count),flush=True)

if __name__=='__main__':main()
