"""Bounded source resolvers for existing catalog identities only."""
from email import policy
from email.parser import BytesParser
import hashlib,re
from urllib.parse import urljoin,urlsplit,unquote
from lxml import html
from maintenance.iri import iri_to_uri
from maintenance.policy import validate_url

SOURCES={2:'inps',3:'inail',4:'ade',5:'lavoro',10:'mimit',12:'funzione_pubblica',
    14:'garante_privacy',15:'inl',16:'giustizia',17:'mef',18:'anac',19:'unioncamere'}

def sniff(raw):
    if not raw:return 'empty_file'
    if raw.startswith(b'%PDF-'):return 'application/pdf'
    if raw.startswith(b'PK'):return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    if raw.startswith(b'\xd0\xcf\x11\xe0'):return 'application/msword'
    if b'<html' in raw[:4000].lower() or b'<!doctype html' in raw[:4000].lower():return 'text/html'
    return 'unsupported_mime'

def unwrap_multipart(raw):
    """INPS serves a single MIME attachment despite application/pdf headers.

    Never scrape a PDF-looking substring out of HTML. Require a complete MIME
    envelope, one attachment, supported magic and a closing boundary.
    """
    if not raw.startswith(b'--'):return raw,None
    line=raw.splitlines()[0]
    if len(line)>150 or not re.fullmatch(rb'--[A-Za-z0-9_-]{8,140}',line) or line+b'--' not in raw[-200:]:
        raise ValueError('Invalid MIME multipart envelope')
    msg=BytesParser(policy=policy.default).parsebytes(b'Content-Type: multipart/mixed; boundary="'+line[2:]+b'"\r\nMIME-Version: 1.0\r\n\r\n'+raw)
    parts=list(msg.iter_parts())
    if msg.defects or len(parts)!=1:raise ValueError('Ambiguous MIME multipart resource')
    body=parts[0].get_payload(decode=True)
    if not body or len(body)>8*1024*1024 or sniff(body) not in ['application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
        raise ValueError('Unsupported MIME multipart attachment')
    return body,hashlib.sha256(raw).hexdigest()

def words(s):return set(re.findall(r'[a-z0-9]{3,}',unquote(s).casefold()))-{'pdf','doc','docx','https','www','modulo','modello','download','scarica','documenti'}

def resolve_links(raw,base_url,source_key,document):
    """One official detail page, <=6 identity-correlated attachments; no crawling."""
    if source_key not in SOURCES.values():raise ValueError('Unknown source resolver')
    validate_url(base_url,source_key)
    if len(raw)>8*1024*1024:raise ValueError('Detail page too large')
    root=html.fromstring(raw,parser=html.HTMLParser(no_network=True,recover=True))
    wanted=words(' '.join([document.titolo_ufficiale,document.codice or '',urlsplit(document.download_url or '').path.rsplit('/',1)[-1]]))
    rows={}
    for a in root.xpath('//a[@href]')[:2000]:
        href=a.get('href','')
        if not re.search(r'\.(?:pdf|docx?)(?:[/?#]|$)',href,re.I):continue
        try:url=validate_url(iri_to_uri(urljoin(base_url,href)),source_key)
        except ValueError:continue
        label=a.text_content()[:1000]+' '+urlsplit(url).path.rsplit('/',1)[-1]
        target=words(label);score=len(wanted&target)/max(1,len(wanted))
        if document.codice and document.codice.casefold() in label.casefold():score=max(score,.9)
        rows[url]=max(score,rows.get(url,0))
    # A unique generic attachment is safe only on the identity's own detail
    # page; a shared listing page cannot grant a new association.
    selected=[u for u,s in sorted(rows.items(),key=lambda x:(-x[1],x[0])) if s>=.55]
    if not selected and len(rows)==1 and base_url==document.detail_url:selected=list(rows)
    return selected[:6]

def classify_error(reason,status=None):
    s=reason.lower()
    if status in [403,404,429]:return 'http_'+str(status)
    if 'robots' in s or 'policy' in s or 'dominio' in s or 'bloccata' in s:return 'robots_or_policy_block'
    if 'timeout' in s or 'timed out' in s:return 'timeout'
    if any(x in s for x in ['ssl','tls','network','urlopen','connessione','resolve']):return 'tls_or_network_error'
    if 'empty' in s:return 'empty_file'
    return 'other'

def resource_kind(document):
    # A declared official file remains in the denominator even when blocked,
    # missing, legacy .doc or unextractable. No exclusion by acquisition success.
    if document.download_url:return 'file_backed_document'
    title=document.titolo_ufficiale.casefold()
    if any(s in title for s in ['servizio online','servizi online','procedura telematica','comunicazioni online']):return 'dynamic_service'
    if any(s in title for s in ['famiglia di','raccolta di modelli']):return 'document_family_reference'
    if document.detail_url:return 'metadata_only_document'
    return 'unclear'
