"""Versioned, bounded public signatures. Upload features are request-local."""
from __future__ import annotations
from array import array
from collections import Counter,defaultdict
from functools import lru_cache
import hashlib,json,math,re,unicodedata
from pathlib import Path
from src.document_fingerprints import streams,binding

VERSION='fingerprint-v2'
PATH=Path(__file__).resolve().parents[1]/'data/document_recognition_fingerprints_v2.json'
CALIBRATION=PATH.parent/'recognition_profiles/fingerprint_v2.json'
PARAMETERS=dict(normalization='nfkc-casefold-v2',hash_algorithm='sha256-domain-64-v2',
    token_shingle=3,char_ngrams=[4,5,6],sketch_size=192,char_size=256,anchor_size=64,
    max_chars=16000,identity_chars=2000,ocr_pages=1,ocr_dpi=144,
    weighted_formula='log((N+1)/(df+1))+1',visual='rotation-invariant-dhash-16x16-v2')
DEFAULT_THRESHOLDS=dict(text=.78,chars=.72,anchors=.60,visual=.88,margin=.055,min_overlap=20)

def h(value,domain):
    return int.from_bytes(hashlib.sha256((VERSION+'\0'+domain+'\0'+value).encode()).digest()[:8],'big')

def features(text):
    text=text[:PARAMETERS['max_chars']]
    tokens,_=streams(text)
    trigrams=frozenset(h(' '.join(tokens[i:i+3]),'token') for i in range(max(0,len(tokens)-2)))
    head_tokens,_=streams(text[:2000])
    header=frozenset(h(' '.join(head_tokens[i:i+3]),'token') for i in range(max(0,len(head_tokens)-2)))
    compact=re.sub(r'[^\w]','',unicodedata.normalize('NFKC',text[:8000]).casefold())
    chars=frozenset(h(compact[i:i+n],'char'+str(n)) for n in (4,5,6) for i in range(max(0,len(compact)-n+1)))
    anchors=set()
    for line in text[:2000].splitlines():
        words,_=streams(line)
        if 3<=len(words)<=18:
            anchors.update(h(' '.join(words[i:i+3]),'anchor') for i in range(len(words)-2))
    return dict(tokens=trigrams,header=header,chars=chars,anchors=frozenset(anchors),
        structure=(min(len(tokens),10000),min(len(text.splitlines()),1000),min(text.count('_'),1000)))

def sketch(values,n):return [format(v,'016x') for v in sorted(values)[:n]]

def make_record(document,raw,text,*,ocr_text='',visual=(),receipt,mime,page_count,
                generated_at,ocr_metadata=None,status='active',container_sha256=None):
    d=features(text);o=features(ocr_text)
    return dict(document_id=document.id,source_id=document.source_id,
        catalog_binding_sha256=binding(document),canonical_file_sha256=hashlib.sha256(raw).hexdigest(),
        mime_type=mime,page_count=page_count,url=receipt['requested_url'],final_url=receipt['final_url'],
        acquisition_date=receipt['acquired_at'],generated_at=generated_at,size_bytes=len(raw),
        status=status,container_sha256=container_sha256,ocr_metadata=ocr_metadata or {},
        digital=sketch(d['tokens'],192),ocr=sketch(o['tokens'],192),
        chars=sketch(d['chars']|o['chars'],256),header=sketch(d['header'],128),
        ocr_header=sketch(o['header'],128),anchors=sketch(d['anchors']|o['anchors'],64),
        visual=list(visual),structure=list(d['structure']))

def validate(bundle):
    if not isinstance(bundle,dict) or set(bundle)!={'schema_version','fingerprint_version','parameters','records'}:
        raise ValueError('Schema fingerprint v2 non valido.')
    if type(bundle['schema_version']) is not int or bundle['schema_version']!=2 or bundle['fingerprint_version']!=VERSION or bundle['parameters']!=PARAMETERS:
        raise ValueError('Versione fingerprint v2 non valida.')
    if not isinstance(bundle['records'],list) or len(bundle['records'])>4000:raise ValueError('Troppi fingerprint v2.')
    required={'document_id','source_id','catalog_binding_sha256','canonical_file_sha256','mime_type','page_count',
        'url','final_url','acquisition_date','generated_at','size_bytes','status','container_sha256','ocr_metadata',
        'digital','ocr','chars','header','ocr_header','anchors','visual','structure'}
    seen=set()
    from datetime import datetime
    from urllib.parse import urlsplit
    for r in bundle['records']:
        if not isinstance(r,dict) or set(r)!=required:raise ValueError('Campi fingerprint v2 non validi.')
        for key in ['document_id','source_id','size_bytes']:
            if type(r[key]) is not int or r[key]<=0:raise ValueError('Identificativo/dimensione non valido.')
        for key in ['catalog_binding_sha256','canonical_file_sha256']:
            if not isinstance(r[key],str) or not re.fullmatch('[a-f0-9]{64}',r[key]):raise ValueError('SHA non valido.')
        key=(r['document_id'],r['canonical_file_sha256'])
        if key in seen:raise ValueError('Risorsa duplicata.')
        seen.add(key)
        if r['status'] not in ['active','stale','quarantined']:raise ValueError('Stato tecnico non valido.')
        if r['container_sha256'] is not None and not re.fullmatch('[a-f0-9]{64}',r['container_sha256']):raise ValueError('SHA contenitore non valido.')
        if r['mime_type'] not in ['application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document']:raise ValueError('MIME non valido.')
        if r['page_count'] is not None and (type(r['page_count']) is not int or not 1<=r['page_count']<=100):raise ValueError('Pagine non valide.')
        for k in ['url','final_url']:
            p=urlsplit(r[k])
            if p.scheme!='https' or not p.hostname or p.username or p.password or len(r[k])>4096:raise ValueError('URL non valida.')
        for k in ['acquisition_date','generated_at']:
            if datetime.fromisoformat(r[k]).tzinfo is None:raise ValueError('Data senza fuso.')
        for k,cap in [('digital',192),('ocr',192),('chars',256),('header',128),('ocr_header',128),('anchors',64)]:
            v=r[k]
            if not isinstance(v,list) or len(v)>cap or v!=sorted(set(v)) or any(not isinstance(x,str) or not re.fullmatch('[a-f0-9]{16}',x) for x in v):raise ValueError('Sketch non valido.')
        if not isinstance(r['visual'],list) or len(r['visual']) not in [0,4] or any(not isinstance(x,str) or not re.fullmatch('[a-f0-9]{64}',x) for x in r['visual']):raise ValueError('Visual non valido.')
        if not isinstance(r['structure'],list) or len(r['structure'])!=3 or any(type(x) is not int or not 0<=x<=10000 for x in r['structure']):raise ValueError('Struttura non valida.')
        if not isinstance(r['ocr_metadata'],dict) or len(json.dumps(r['ocr_metadata']))>2000 or set(r['ocr_metadata'])-{'status','engine','language','dpi','pages','error_type','traineddata_sha256'}:raise ValueError('OCR metadata non validi.')
    return bundle

def read_bundle(path=PATH):
    path=Path(path)
    if not path.exists():return dict(schema_version=2,fingerprint_version=VERSION,parameters=PARAMETERS,records=[])
    if path.stat().st_size>64*1024*1024 or any(p.is_symlink() or p.is_junction() for p in [path,*path.parents]):raise ValueError('Bundle non sicuro.')
    return validate(json.loads(path.read_bytes()))

def overlap(stored,query):return sum(x in query for x in stored)/len(stored) if stored else 0.0

def visual_similarity(a,b):
    if not a or not b:return 0.0
    return max(1-(int(x,16)^int(y,16)).bit_count()/256 for x in a for y in b)

def fused(row,t):
    # A visual hash is never sufficient; token/character evidence and independent
    # stable labels or layout must corroborate it. IDF reduces shared templates.
    strong=row['text']>=t['text'] and row['chars']>=t['chars'] and (row['anchors']>=t['anchors'] or row['visual']>=t['visual'])
    moderate=row['text']>=.52 and row['chars']>=.58 and row['visual']>=max(.94,t['visual']) and row['anchors']>=.40
    return row['overlap']>=t['min_overlap'] and (strong or moderate)

class FingerprintIndex:
    def __init__(self,bundle):
        validate(bundle);self.records=[];self.sha=defaultdict(set);post=defaultdict(list)
        for original in bundle['records']:
            if original['status']!='active':continue
            r=dict(original)
            for k in ['digital','ocr','chars','header','ocr_header','anchors']:r[k]=array('Q',(int(x,16) for x in r[k]))
            i=len(self.records);self.records.append(r);self.sha[r['canonical_file_sha256']].add(r['document_id'])
            for value in set(r['digital'])|set(r['ocr'])|set(r['header'])|set(r['ocr_header']):post[value].append(i)
        self.postings={h:array('H',ids) for h,ids in post.items()};N=len(self.records)
        self.weights={h:math.log((N+1)/(len(ids)+1))+1 for h,ids in self.postings.items()}
        # Public catalog-only denominators; never cache query features.
        self.denominators=[tuple(sum(self.weights.get(h,1) for h in r[k]) for k in ('digital','ocr','header','ocr_header')) for r in self.records]
    def candidates(self,query,visual=(),reference=False):
        if reference:return range(len(self.records))
        votes=Counter(i for h in query['tokens'] for i in self.postings.get(h,()))
        found={i for i,n in votes.items() if n>=3}
        if visual:
            found.update(i for i,r in enumerate(self.records) if visual_similarity(visual,r['visual'])>=.85)
        return found
    def similarities(self,query,visual=(),reference=False):
        rows=[]
        for i in self.candidates(query,visual,reference):
            r=self.records[i];best=0.;inter=0
            channels={}
            for j,k in enumerate(['digital','ocr','header','ocr_header']):
                values=r[k];den=self.denominators[i][j]
                matched=[h for h in values if h in query['tokens']]
                score=sum(self.weights.get(h,1) for h in matched)/den if den else 0
                channels[k]=score
                best=max(best,score);inter=max(inter,len(matched))
            chars=overlap(r['chars'],query['chars']);anchors=overlap(r['anchors'],query['anchors']);vs=visual_similarity(visual,r['visual'])
            row=dict(document_id=r['document_id'],resource_index=i,text=best,chars=chars,anchors=anchors,visual=vs,overlap=inter,
                structure=1-abs(r['structure'][1]-query['structure'][1])/max(r['structure'][1],query['structure'][1],1),
                score=.5*best+.25*chars+.15*anchors+.1*vs)
            row.update(channels);rows.append(row)
        # Multiple resources compete as one identity, never against themselves.
        by={}
        for row in rows:
            if row['document_id'] not in by or row['score']>by[row['document_id']]['score']:by[row['document_id']]=row
        return sorted(by.values(),key=lambda r:(-r['score'],r['document_id']))

@lru_cache(maxsize=1)
def public_index():return FingerprintIndex(read_bundle())

@lru_cache(maxsize=1)
def revision():return hashlib.sha256(PATH.read_bytes()).hexdigest() if PATH.exists() else 'absent'

@lru_cache(maxsize=1)
def thresholds():
    if not CALIBRATION.exists():return dict(DEFAULT_THRESHOLDS)
    if CALIBRATION.is_symlink() or CALIBRATION.stat().st_size>64000:raise ValueError('Calibrazione non sicura.')
    r=json.loads(CALIBRATION.read_bytes());t=r['thresholds']
    if set(t)!=set(DEFAULT_THRESHOLDS) or any(type(x) not in [int,float] or not math.isfinite(x) or x<0 for x in t.values()):raise ValueError('Soglie non valide.')
    return t
