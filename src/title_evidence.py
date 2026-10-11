"""Conservative metadata-only title windows; no uploaded text is cached."""
from __future__ import annotations
from collections import Counter
from functools import lru_cache
import re
import unicodedata

STOP=frozenset('a al alla alle allo ai agli da dal dalla dalle dallo dei degli del della delle di e ed il la le lo i gli l un una per nel nella nelle con sul sulla si pdf docx modulo modello domanda richiesta istanza autorizzazione allegato art articolo legge decreto numero n ai sensi'.split())

def tokens(text):
    raw=re.findall(r'[a-z0-9]+',unicodedata.normalize('NFKD',text.casefold()).encode('ascii','ignore').decode())
    return tuple(t[:6] if len(t)>6 and t.isalpha() else t for t in raw if len(t)>2 and t not in STOP)

@lru_cache(maxsize=16)
def title_index(documents):
    titles={d.id:frozenset(tokens(d.titolo_ufficiale)) for d in documents if d.id is not None and d.stato_verifica not in {'demo','rifiutato'}}
    counts=Counter(t for v in titles.values() for t in v)
    weights={t:1/(1+count)**.5 for t,count in counts.items()}
    return titles,weights

def title_windows(text,documents,entities,*,reference=False):
    titles,weights=(title_index.__wrapped__ if reference else title_index)(tuple(documents));opening=tokens(text[:2000]);available=set(opening);candidates={}
    for d in documents:
        needed=titles.get(d.id,frozenset())
        # A unique code or two generic words cannot become a title identity.
        if len(needed)<4 or not entities or d.ente not in entities:continue
        found=needed & available
        total=sum(weights[t] for t in needed)
        coverage=sum(weights[t] for t in found)/total if total else 0
        if coverage<.94 or len(found)<3:continue
        positions=[i for i,t in enumerate(opening) if t in found]
        if not positions:continue
        # Require the supported title tokens in a bounded section, rather than
        # collecting unrelated references throughout a long document.
        if not any(len(set(opening[i:i+45]) & found)==len(found) for i in positions):continue
        candidates[d.id]=round(coverage,6)
    # A base title cannot silently select one of its unobserved subtypes.
    for d in documents:
        if d.id not in candidates:continue
        needed=titles[d.id]
        if any(other.ente==d.ente and needed < titles.get(other.id,frozenset()) and len(titles[other.id]-needed)<=3
               for other in documents):
            del candidates[d.id]
    return candidates


def compact_code(value):
    raw=unicodedata.normalize('NFKD',value.casefold()).encode('ascii','ignore').decode()
    parts=re.findall(r'[a-z]+|[0-9]+',raw)
    return ''.join(('.' if i and p.isdigit() and parts[i-1].isdigit() else '')+p for i,p in enumerate(parts))

@lru_cache(maxsize=16)
def code_index(documents):
    result={}
    for d in documents:
        if d.stato_verifica in {'demo','rifiutato'} or not d.codice:continue
        code=compact_code(d.codice)
        if len(code)>=3 and any(c.isalpha() for c in code) and any(c.isdigit() for c in code):result.setdefault(code,[]).append(d.id)
    return {k:tuple(v) for k,v in result.items()}

def exact_code_candidates(text,documents,*,reference=False):
    index=(code_index.__wrapped__ if reference else code_index)(tuple(documents));found=set()
    for line in text[:2000].splitlines():
        # Whole code spans, never joined across lines or truncated numeric suffixes.
        for m in re.finditer(r'(?<!\w)[A-Za-z]{1,8}[ ._-]*\d+(?:[ ./_-]+\d+)*(?![\w.])',line):
            if re.search(r'\b(?:protocollo|prot|fattura|importo|pagina|articolo)(?:\s+(?:n|numero))?\s*$',line[max(0,m.start()-60):m.start()],re.I):continue
            key=compact_code(m.group())
            if key in index:found.update(index[key])
    return frozenset(found)
