"""Conservative split checks; catalog metadata is allowed, official files are not shared."""
from __future__ import annotations
from collections import defaultdict
import hashlib
import json
import re
from urllib.parse import urlsplit, urlunsplit, unquote, quote, parse_qsl, urlencode
from maintenance.iri import iri_to_uri
from src.recognize import normalize_text
from src.title_evidence import tokens,compact_code


def identity_key(item):
    return (item.get('entity') or item.get('ente') or '',item.get('document_id'))

def template_key(item):
    title=normalize_text(item.get('title') or item.get('titolo_ufficiale') or '')
    title=re.sub(r'\b(?:19|20)\d{2}\b','',title)
    if 'tribunale' in (item.get('entity') or '').casefold():
        title=re.sub(r'^(?:tutela minori|tutela|minori|curatela|amministratore di sostegno)\s*','',title)
    return tuple(sorted(set(tokens(title))))

def canonical_url(value):
    if not value:return None
    p=urlsplit(iri_to_uri(value))
    path=quote(unquote(p.path),safe="/:@!$&'()*+,;=-._~")
    query=urlencode(sorted(parse_qsl(p.query,keep_blank_values=True)))
    return urlunsplit((p.scheme,p.netloc,path,query,''))

def collision(a,b):
    if a.get('sha256') and a['sha256']==b.get('sha256'):return 'same_file_hash'
    if a.get('url') and b.get('url') and canonical_url(a['url'])==canonical_url(b['url']):return 'same_resource_url'
    if a.get('document_id') is not None and identity_key(a)==identity_key(b):return 'same_document_identity'
    if a.get('entity')!=b.get('entity'):return None
    ac,bc=compact_code(a.get('code') or ''),compact_code(b.get('code') or '')
    if ac and ac==bc:return 'same_code_or_version_group'
    at,bt=set(template_key(a)),set(template_key(b))
    if at and bt and (at==bt or (min(len(at),len(bt))>=3 and len(at&bt)/len(at|bt)>=.8)):return 'equivalent_title_or_template'
    return None

def check(development,holdout):
    overlaps=[];suspicious=[]
    for h in holdout:
        for d in development:
            why=collision(h,d)
            if why:overlaps.append(dict(holdout=h['id'],development=d['id'],reason=why))
            elif template_key(h) and template_key(h)==template_key(d):suspicious.append(dict(holdout=h['id'],development=d['id'],reason='cross_issuer_title_collision'))
    hashes=[c['sha256'] for c in holdout if c.get('sha256')]
    duplicate_hashes=len(hashes)-len(set(hashes))
    return dict(schema_version=1,passed=not overlaps and not duplicate_hashes,development_n=len(development),holdout_n=len(holdout),overlaps=overlaps,duplicate_holdout_hashes=duplicate_hashes,suspicious_title_collisions=suspicious,
                policy='Official development file hashes, URLs, document identities, code/version and territorial template groups are excluded. Catalog metadata and canonical synthetic tests are permitted because the task is recognition of catalogued identities, not discovery of unseen identities. Cross-issuer common titles are reported, never treated as issuer evidence. Near-equivalence is conservative metadata grouping, not a proof of content independence.')
