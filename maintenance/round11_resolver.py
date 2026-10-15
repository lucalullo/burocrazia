"""Bounded official detail hops; source association is never identity truth."""
import re
from urllib.parse import urljoin,urlsplit,unquote
from lxml import html
from maintenance.policy import validate_url
from maintenance.iri import iri_to_uri
from maintenance.resolve_resources import words,resolve_links

def resolve_detail_links(raw,base,key,document):
 result=resolve_links(raw,base,key,document)
 tree=html.fromstring(raw,parser=html.HTMLParser(no_network=True))
 wanted=words(document.titolo_ufficiale+' '+(document.codice or ''))
 for a in tree.xpath('//a[@href]')[:2000]:
  h=a.get('href','');label=' '.join(a.text_content().split())[:1000]
  # Garante stores PDF attachments behind a document page; do not follow
  # general navigation or arbitrary same-origin links.
  if key!='garante_privacy' or not re.search(r'(?:/garante/(?:document|doc[.]jsp)[?]ID=\d+|/docweb/\d+)',h):continue
  evidence=words(label);support=len(wanted&evidence)/max(1,len(wanted))
  if not wanted or support<.60:continue
  try:url=validate_url(iri_to_uri(urljoin(base,h)),key)
  except ValueError:continue
  if url!=base and url not in result:result.append(url)
 return result[:6]
