"""fingerprint-v1: bounded, offline, hash-only canonical content signatures.

Only the public bundle/index is cached. Upload tokens/hashes are request-local.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
import unicodedata

VERSION = 'fingerprint-v1'
PARAMETERS = dict(normalization='nfkc-casefold-page-boundaries-v1', shingle_size=4,
                  hash_algorithm='sha256-truncated-128-domain-v1', sketch_size=512,
                  header_chars=2000, header_size=256, anchor_derivation='line-4grams-v1')
PATH = Path(__file__).resolve().parents[1]/'data/document_recognition_fingerprints.json'
MAX_BUNDLE_BYTES = 64 * 1024 * 1024
MAX_TOKENS = 50_000
HEX128 = re.compile(r'[a-f0-9]{32}')
HEX256 = re.compile(r'[a-f0-9]{64}')


def digest(value: str, domain='shingle') -> str:
    return hashlib.sha256((VERSION+'\0'+domain+'\0'+value).encode()).hexdigest()[:32]


def streams(text: str):
    """Remove repeated short lines, join line-wrap hyphens, retain years/codes.

    Lexical stream masks long numeric values (filled amounts/identifiers), while
    aware stream preserves all numbers. Neither stream is persisted as text.
    """
    text=unicodedata.normalize('NFKC',text).casefold().replace('\u00ad','')
    text=re.sub(r'(?<=\w)-\s*\n\s*(?=\w)','',text)
    pages=[[re.sub(r'\s+',' ',line).strip() for line in page.splitlines() if line.strip()] for page in text.split('\f')]
    lines=[line for page in pages for line in page]
    # Repetition inside a single page can be a legitimate repeated field label.
    # Deduplicate only repeated lines at explicit page boundaries.
    counts=Counter(line for page in pages for line in set(page[:2]+page[-2:]) if 0<len(line)<160) if len(pages)>1 else Counter()
    seen=set(); kept=[]
    for line in lines:
        if counts[line]>1:
            if line in seen:continue
            seen.add(line)
        kept.append(line)
    # Isolated single OCR letters are joined only in runs of >=3 letters.
    normalized='\n'.join(kept)
    normalized=re.sub(r'\b(?:[a-zà-ÿ] ){2,}[a-zà-ÿ]\b',lambda m:m[0].replace(' ',''),normalized)
    aware=re.findall(r'[^\W_]+',normalized,flags=re.UNICODE)[:MAX_TOKENS]
    lexical=['number' if t.isdigit() and len(t)>=3 and not re.fullmatch(r'(?:19|20)\d{2}|730',t) else t for t in aware]
    return lexical,aware


def shingles(tokens, domain='shingle'):
    n=PARAMETERS['shingle_size']
    return frozenset(digest(' '.join(tokens[i:i+n]),domain) for i in range(max(0,len(tokens)-n+1)))


def features(text: str, field_names=()):
    lexical,aware=streams(text)
    header,_=streams(text[:PARAMETERS['header_chars']])
    anchors=set()
    for line in text[:8000].splitlines():
        words,_=streams(line)
        if 4<=len(words)<=16:anchors.update(shingles(words,'anchor'))
    return dict(lexical=shingles(lexical), aware=shingles(aware,'aware'),
                header=shingles(header), anchors=frozenset(anchors),
                fields=frozenset(digest(' '.join(streams(n)[1]),'field') for n in field_names if n),
                token_count=len(lexical))


def binding(document):
    value=[document.id,document.source_id,document.ente,document.codice,
           document.titolo_ufficiale,document.versione,document.stato_verifica]
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


def make_record(document, raw, text, *, receipt, mime, page_count, method, generated_at, field_names=()):
    f=features(text,field_names)
    bounded=lambda key,size:sorted(f[key])[:size]
    return dict(document_id=document.id,source_id=document.source_id,
        fingerprint_version=VERSION,catalog_binding_sha256=binding(document),
        canonical_file_sha256=hashlib.sha256(raw).hexdigest(),mime_type=mime,
        page_count=page_count,extraction_method=method,generated_at=generated_at,
        acquisition_date=receipt['acquired_at'],url=receipt['requested_url'],
        final_url=receipt['final_url'],size_bytes=len(raw),status='active',
        lexical=bounded('lexical',512),aware=bounded('aware',128),
        header=bounded('header',256),anchors=bounded('anchors',64),fields=bounded('fields',128),
        feature_counts={k:len(f[k]) for k in ('lexical','aware','header','anchors','fields')},
        token_count=f['token_count'],version_signature_hash=digest(document.versione or '','version'),
        entity_signature_hash=digest(document.ente,'entity'))


def validate(bundle):
    if not isinstance(bundle,dict) or set(bundle)!={'schema_version','fingerprint_version','parameters','records'}:
        raise ValueError('Schema fingerprint non valido.')
    if bundle['schema_version']!=1 or bundle['fingerprint_version']!=VERSION or bundle['parameters']!=PARAMETERS:
        raise ValueError('Versione fingerprint non supportata.')
    records=bundle['records']
    if not isinstance(records,list) or len(records)>2000:raise ValueError('Limite fingerprint superato.')
    ids=set()
    fields={'document_id','source_id','fingerprint_version','catalog_binding_sha256',
        'canonical_file_sha256','mime_type','page_count','extraction_method','generated_at',
        'acquisition_date','url','final_url','size_bytes','status','lexical','aware','header',
        'anchors','fields','feature_counts','token_count','version_signature_hash','entity_signature_hash'}
    for r in records:
        if not isinstance(r,dict) or set(r)!=fields:raise ValueError('Record fingerprint non valido.')
        if type(r['document_id']) is not int or r['document_id']<=0 or r['document_id'] in ids:raise ValueError('Identità fingerprint duplicata.')
        ids.add(r['document_id'])
        if type(r['source_id']) is not int or r['source_id']<=0:raise ValueError('Fonte fingerprint non valida.')
        if r['fingerprint_version']!=VERSION or r['status']!='active':raise ValueError('Stato fingerprint non valido.')
        for k in ['catalog_binding_sha256','canonical_file_sha256']:
            if not isinstance(r[k],str) or not HEX256.fullmatch(r[k]):raise ValueError('Hash fingerprint non valido.')
        for k in ['version_signature_hash','entity_signature_hash']:
            if not isinstance(r[k],str) or not HEX128.fullmatch(r[k]):raise ValueError('Firma fingerprint non valida.')
        for key,limit in [('lexical',512),('aware',128),('header',256),('anchors',64),('fields',128)]:
            a=r[key]
            if not isinstance(a,list) or len(a)>limit or any(not isinstance(h,str) or not HEX128.fullmatch(h) for h in a) or a!=sorted(set(a)):
                raise ValueError('Sketch fingerprint non valido.')
        for k in ['token_count','size_bytes']:
            if type(r[k]) is not int or not 0<=r[k]<=20*1024*1024:raise ValueError('Conteggio fingerprint non valido.')
        if r['page_count'] is not None and (type(r['page_count']) is not int or not 1<=r['page_count']<=100):raise ValueError('Pagine fingerprint non valide.')
        if r['mime_type']=='application/pdf' and r['page_count'] is None:raise ValueError('Pagine PDF mancanti.')
        if not isinstance(r['feature_counts'],dict) or set(r['feature_counts'])!={'lexical','aware','header','anchors','fields'} or any(type(n) is not int or not 0<=n<=MAX_TOKENS for n in r['feature_counts'].values()):raise ValueError('Conteggi feature non validi.')
        for k in ['mime_type','extraction_method','generated_at','acquisition_date','url','final_url']:
            if not isinstance(r[k],str) or not 1<=len(r[k])<=2048:raise ValueError('Metadato fingerprint non valido.')
        if r['mime_type'] not in {'application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document'}:raise ValueError('MIME fingerprint non valido.')
        from datetime import datetime
        for k in ['generated_at','acquisition_date']:
            if datetime.fromisoformat(r[k]).tzinfo is None:raise ValueError('Data fingerprint senza fuso.')
        from urllib.parse import urlsplit
        for k in ['url','final_url']:
            p=urlsplit(r[k])
            if p.scheme!='https' or not p.hostname or p.username or p.password:raise ValueError('URL fingerprint non valido.')
    return bundle


def read_bundle(path=PATH):
    path=Path(path)
    if not path.exists():return dict(schema_version=1,fingerprint_version=VERSION,parameters=PARAMETERS,records=[])
    if any(p.is_symlink() or p.is_junction() for p in [path,*path.parents]) or path.stat().st_size>MAX_BUNDLE_BYTES:
        raise ValueError('Bundle fingerprint oltre i limiti o collegato.')
    return validate(json.loads(path.read_text(encoding='utf-8')))


class FingerprintIndex:
    def __init__(self,bundle):
        validate(bundle)
        self.records={r['document_id']:r for r in bundle['records']}
        self.inverted=defaultdict(list);self.sha=defaultdict(set)
        for r in self.records.values():
            self.sha[r['canonical_file_sha256']].add(r['document_id'])
            for h in set(r['lexical'])|set(r['header']):self.inverted[h].append(r['document_id'])
        self.inverted={h:tuple(ids) for h,ids in self.inverted.items()}

    def candidates(self,query,*,reference=False):
        if reference:return set(self.records)
        votes=Counter()
        for h in query['lexical']:
            for docid in self.inverted.get(h,()):votes[docid]+=1
        # No top-N truncation: all candidates with minimum evidence survive.
        return {docid for docid,n in votes.items() if n>=16}

    def similarities(self,query,*,reference=False):
        rows=[]
        query_bottom=set(sorted(query['lexical'])[:512])
        for docid in self.candidates(query,reference=reference):
            r=self.records[docid];inter=len(set(r['lexical'])&query['lexical'])
            containment=inter/len(r['lexical']) if r['lexical'] else 0
            header=len(set(r['header'])&query['header'])/len(r['header']) if r['header'] else 0
            anchors=len(set(r['anchors'])&query['anchors'])/len(r['anchors']) if r['anchors'] else 0
            # inverse-document-frequency weights reduce shared template evidence.
            weights=[1/len(self.inverted[h]) for h in r['lexical']]
            weighted=sum(w for h,w in zip(r['lexical'],weights) if h in query['lexical'])/sum(weights) if weights else 0
            union=r['feature_counts']['lexical']+len(query['lexical'])-containment*r['feature_counts']['lexical']
            jaccard=containment*r['feature_counts']['lexical']/union if union>0 else 0
            fields=len(set(r['fields'])&query['fields'])/len(r['fields']) if r['fields'] else 0
            union_bottom=set(sorted(set(r['lexical'])|query_bottom)[:512])
            bottom_k=len(union_bottom&set(r['lexical'])&query_bottom)/len(union_bottom) if union_bottom else 0
            eligible=inter>=24 and ((containment>=.80 and weighted>=.80 and (header>=.65 or anchors>=.80)) or (header>=.90 and inter>=32 and query['token_count']>=80))
            rows.append(dict(document_id=docid,overlap=inter,containment=containment,header=header,
                anchors=anchors,weighted_overlap=weighted,jaccard_estimate=jaccard,bottom_k_similarity=bottom_k,fields=fields,
                eligible=eligible,score=max(containment,header)*weighted))
        return sorted(rows,key=lambda r:(-r['score'],r['document_id']))


@lru_cache(maxsize=1)
def public_index():return FingerprintIndex(read_bundle())


@lru_cache(maxsize=1)
def revision():return hashlib.sha256(PATH.read_bytes()).hexdigest() if PATH.exists() else 'absent'
