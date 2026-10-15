"""Conditional decision tiers over unchanged fingerprint-v2 retrieval."""
import hashlib,json,re
from functools import lru_cache
from pathlib import Path

VERSION='fingerprint-decision-v3'
PATH=Path(__file__).resolve().parents[1]/'data/recognition_profiles/fingerprint_decision_v3.json'
DEFAULT=dict(text_visual=.55,ocr_visual=.80,visual=.94,char_floor=.10,anchors=.12,overlap=24,margin=.04,
    text_char=.85,char_strong=.30,anchor_strong=.45,exceptional=.97)

@lru_cache(maxsize=1)
def profile():
    if not PATH.exists():return dict(DEFAULT)
    if PATH.is_symlink() or PATH.stat().st_size>64000:raise ValueError('Decision profile unsafe')
    p=json.loads(PATH.read_bytes());t=p['thresholds']
    if p['rules_version']!=VERSION or set(t)!=set(DEFAULT) or any(type(v) not in (int,float) or not 0<=v<=100 for v in t.values()):raise ValueError('Decision profile invalid')
    return t

def revision():return hashlib.sha256(PATH.read_bytes()).hexdigest() if PATH.exists() else 'development-default-v3'

def entity_evidence(text,names):
    from src.recognize import _issuer_entities,normalize_text
    opening=text[:2000]
    # A ministry remains the issuer when an OCR spelling omits the article;
    # subordinate department lines must not replace its explicit parent.
    opening=re.sub(r'ministero\s+delle\s+imprese\s+e\s+(?:del\s+)?made\s+in\s+italy',
        'Ministero delle Imprese e del Made in Italy',opening,flags=re.I)
    lines=opening.splitlines();filtered=[];recipient=False
    for line in lines:
        n=normalize_text(line)
        if re.match(r'^(?:al|ai|alla)\s+suap\b',n) or n.startswith('compilato a cura del suap'):
            recipient=True;filtered.append('Destinatario SUAP');continue
        if recipient and re.match(r'^comune\s+di\b',n):
            filtered.append('Campo ente destinatario');continue
        filtered.append(line)
        if n.startswith(('segnalazione certificata','dichiarazione','richiesta','oggetto')):recipient=False
    names=tuple(dict.fromkeys(names));entities=_issuer_entities('\n'.join(filtered),names)
    known={normalize_text(n) for n in names}
    if entities and all(e.startswith('dipartimento ') and e not in known for e in entities):
        head=normalize_text(opening[:500])
        parents={normalize_text(n) for n in names if n.casefold().startswith('ministero ') and normalize_text(n) in head}
        if len(parents)==1:entities=frozenset(parents)
    return entities-{'comune','comuni','regione','regioni','enti locali'}

def tier(row,t=None,*,code_anchor=False):
    t=profile() if t is None else t
    if row['overlap']<t['overlap']:return None
    text=row['text'];ocr=max(row.get('ocr',0),row.get('ocr_header',0));char=row['chars'];visual=row['visual'];anchors=row['anchors']
    if visual>=t['visual'] and char>=t['char_floor'] and anchors>=t['anchors'] and (ocr>=t['ocr_visual'] or text>=t['text_visual']):return 'B_text_visual'
    if text>=t['text_char'] and char>=t['char_strong'] and anchors>=t['anchor_strong']:return 'B_text_char_anchors'
    if text>=t['exceptional'] and char>=t['char_strong'] and (code_anchor or anchors>=.80):return 'C_exceptional_identity_anchor'
    return None

def metadata_revision_supported(text,document,documents):
    """Unique code + full title + explicit issuer can identify a sole revision.

    A conflicting stated revision is still rejected by the existing scorer.
    A template-only refusal cannot jump to a different revision through fuzzy metadata.
    """
    from src.recognize import normalize_text,_catalog_features
    f=_catalog_features(document);opening=normalize_text(text[:2000])
    # Bilingual catalogue titles contain complete language headings separated
    # by spaced slashes. A complete first heading is explicit title evidence.
    heading=lambda d:normalize_text(re.split(r'\s+/\s+',d.titolo_ufficiale)[0])
    title=heading(document)
    peers=[d for d in documents if d.stato_verifica not in ('demo','rifiutato') and normalize_text(d.codice or '')==f.code and heading(d)==title and d.ente==document.ente]
    return bool(f.code and len(peers)==1 and f' {title} ' in f' {opening} ' and
        any(f.code_pattern.search(normalize_text(line)) for line in text[:2000].splitlines()) and
        f.entity in entity_evidence(text,[d.ente for d in documents]))
