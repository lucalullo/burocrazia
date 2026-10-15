"""Page-aware public signatures. Only canonical statistics enter the index cache."""
from __future__ import annotations
from array import array
from bisect import bisect_left
from collections import Counter,defaultdict
from functools import lru_cache
import hashlib,json,math,re,unicodedata
from pathlib import Path
from src.document_fingerprints import streams
from src.fingerprint_v2 import h as token_hash

VERSION='fingerprint-v3'
PATH=Path(__file__).resolve().parents[1]/'data/document_recognition_fingerprints_v3.json'
PARAMETERS=dict(token_hash='sha256-domain-64-v2-compatible',char_hash='blake2b-domain-64-v3',
    char_ngrams=[3,4,5],token_size=64,char_size=64,anchor_size=32,max_page_chars=8000,
    max_pages=100,ocr_dpi=144,identity_chars=2000,visual='rotation-dhash64-center-tiles2x2-v3',
    idf='token exact page DF; char deterministic 32768-bucket page DF; log((pages+1)/(df+1))+1',containment='sampled canonical overlap scaled by canonical/query cardinality; capped at 1')

def char_hash(value,n):return int.from_bytes(hashlib.blake2b(('char'+str(n)+'\0'+value).encode(),digest_size=8,person=b'BurOCRazia-v3').digest(),'big')

def features(text):
    text=unicodedata.normalize('NFKC',text[:PARAMETERS['max_page_chars']]).casefold()
    words,_=streams(text)
    # Deduplicate within this request before hashing. Hash-set semantics are
    # identical, including collisions; no uploaded text enters a shared cache.
    tokens=frozenset(token_hash(value,'token') for value in {' '.join(words[i:i+3]) for i in range(max(0,len(words)-2))})
    compact=re.sub(r'[^\w]','',text)
    chars={str(n):frozenset(char_hash(value,n) for value in {compact[i:i+n] for i in range(max(0,len(compact)-n+1))}) for n in (3,4,5)}
    anchors=set()
    for line in text[:2000].splitlines():
        w,_=streams(line)
        if 3<=len(w)<=18:anchors.update(token_hash(' '.join(w[i:i+3]),'anchor') for i in range(len(w)-2))
    return dict(tokens=tokens,chars=chars,anchors=frozenset(anchors))

def sketch(values,n):return [format(h,'016x') for h in sorted(values)[:n]]

def page_record(number,digital,ocr,visual,*,reused_ocr=None,ocr_status='generated'):
    d=features(digital);o=features(ocr)
    stored_ocr=sketch(o['tokens'],64) if reused_ocr is None else sorted(set(reused_ocr))[:64]
    return dict(number=number,digital=sketch(d['tokens'],64),ocr=stored_ocr,
        digital_count=len(d['tokens']),ocr_count=len(o['tokens']) if reused_ocr is None else max(len(d['tokens']),len(stored_ocr)),
        chars={str(n):sketch(d['chars'][str(n)]|o['chars'][str(n)],64) for n in (3,4,5)},
        char_counts={str(n):len(d['chars'][str(n)]|o['chars'][str(n)]) for n in (3,4,5)},
        anchors=sketch(d['anchors']|o['anchors'],32),visual=list(visual),ocr_status=ocr_status)

def validate_legacy_source(record):
    """Validate source provenance only; upload formats and scoring are unchanged."""
    formats={'.doc':'application/msword','.rtf':'application/rtf','.xls':'application/vnd.ms-excel',
             '.xlsx':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
             '.odt':'application/vnd.oasis.opendocument.text'}
    meta=record['ocr_metadata']
    if not isinstance(meta,dict) or meta.get('source_kind')!='maintenance_derived_legacy':raise ValueError('Provenienza legacy v3 assente.')
    if not isinstance(meta.get('original_format'),str) or formats.get(meta['original_format'])!=record['mime_type']:raise ValueError('Formato originale legacy incoerente.')
    if meta.get('original_sha256')!=record['canonical_file_sha256']:raise ValueError('SHA originale legacy incoerente.')
    for key in ['derived_sha256','converter_sha256','profile_sha256','provenance_manifest_sha256']:
        if not isinstance(meta.get(key),str) or not re.fullmatch('[a-f0-9]{64}',meta[key]):raise ValueError('Prova legacy v3 incompleta.')
    if meta['derived_sha256']==record['canonical_file_sha256'] or meta.get('derived_mime_type')!='application/pdf' or meta.get('deterministic_conversion') is not True:raise ValueError('Derivazione legacy non verificata.')
    if meta.get('conversion_method')!='libreoffice-pdf-normalized-v1' or meta.get('representation_byte_identity')!='derived_not_official':raise ValueError('Identità dei byte derivati non valida.')

def validate(bundle):
    if not isinstance(bundle,dict) or set(bundle)!={'schema_version','fingerprint_version','parameters','records'}:raise ValueError('Schema fingerprint v3 non valido.')
    if bundle['schema_version']!=3 or bundle['fingerprint_version']!=VERSION or bundle['parameters']!=PARAMETERS:raise ValueError('Versione fingerprint v3 non valida.')
    records=bundle['records']
    if not isinstance(records,list) or len(records)>4000:raise ValueError('Numero risorse v3 non valido.')
    seen=set();total_pages=0
    for r in records:
        required={'document_id','source_id','catalog_binding_sha256','canonical_file_sha256','mime_type','url','final_url','acquisition_date','generated_at','size_bytes','status','shared_kind','pages','aggregate','field_set','ocr_metadata'}
        if not isinstance(r,dict) or set(r)!=required:raise ValueError('Risorsa v3 non valida.')
        if type(r['document_id']) is not int or r['document_id']<=0 or type(r['source_id']) is not int or r['source_id']<=0:raise ValueError('Identità v3 non valida.')
        for k in ['catalog_binding_sha256','canonical_file_sha256']:
            if not isinstance(r[k],str) or not re.fullmatch('[a-f0-9]{64}',r[k]):raise ValueError('SHA v3 non valido.')
        key=(r['document_id'],r['canonical_file_sha256'])
        if key in seen:raise ValueError('Risorsa v3 duplicata.')
        seen.add(key)
        if r['status'] not in ['active','shared','stale','quarantined'] or r['shared_kind'] not in ['same_identity_duplicate','shared_attachment','common_form','ambiguous','unambiguous']:raise ValueError('Stato v3 non valido.')
        from datetime import datetime
        from urllib.parse import urlsplit
        for k in ['acquisition_date','generated_at']:
            if datetime.fromisoformat(r[k]).tzinfo is None:raise ValueError('Data v3 senza fuso.')
        for k in ['url','final_url']:
            u=urlsplit(r[k])
            if u.scheme!='https' or not u.hostname or u.username or u.password or len(r[k])>4096:raise ValueError('URL v3 non valida.')
        if type(r['size_bytes']) is not int or not 0<r['size_bytes']<=20*1024*1024:raise ValueError('Dimensione v3 non valida.')
        legacy=r['mime_type'] not in ['application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document']
        if legacy:validate_legacy_source(r)
        elif isinstance(r['ocr_metadata'],dict) and r['ocr_metadata'].get('source_kind')=='maintenance_derived_legacy':raise ValueError('MIME originale legacy mascherato da PDF/DOCX.')
        if not isinstance(r['ocr_metadata'],dict) or len(json.dumps(r['ocr_metadata']))>3000:raise ValueError('Metadata OCR v3 non validi.')
        def hashes(v,cap):
            if not isinstance(v,list) or len(v)>cap or v!=sorted(set(v)) or any(not isinstance(x,str) or not re.fullmatch('[a-f0-9]{16}',x) for x in v):raise ValueError('Sketch v3 non valido.')
        hashes(r['field_set'],512);hashes(r['aggregate'],192)
        if not isinstance(r['pages'],list) or not 1<=len(r['pages'])<=100:raise ValueError('Pagine v3 non valide.')
        nums=set()
        for p in r['pages']:
            if set(p)!={'number','digital','ocr','digital_count','ocr_count','chars','char_counts','anchors','visual','ocr_status'}:raise ValueError('Campi pagina v3 non validi.')
            if type(p['number']) is not int or not 1<=p['number']<=100 or p['number'] in nums:raise ValueError('Indice pagina v3 non valido.')
            nums.add(p['number'])
            for k in ['digital','ocr']:hashes(p[k],64)
            hashes(p['anchors'],32)
            if set(p['chars'])!={'3','4','5'} or set(p['char_counts'])!={'3','4','5'}:raise ValueError('Ngram v3 non validi.')
            for n in ['3','4','5']:hashes(p['chars'][n],64)
            counts=[p['digital_count'],p['ocr_count'],*p['char_counts'].values()]
            if any(type(n) is not int or not 0<=n<=100000 for n in counts):raise ValueError('Cardinalità v3 non valida.')
            if not isinstance(p['visual'],list) or len(p['visual']) not in [0,24] or any(not isinstance(x,str) or not re.fullmatch('[a-f0-9]{16}',x) for x in p['visual']):raise ValueError('Visual v3 non valido.')
            if p['ocr_status'] not in ['generated','reused_v2_first_page','unavailable_docx_renderer','failed','bounded_timeout'] and not (legacy and p['ocr_status']=='not_requested_maintenance_digital_only'):raise ValueError('Stato OCR pagina non valido.')
        total_pages+=len(r['pages'])
    if total_pages>20000:raise ValueError('Troppe pagine v3.')
    return bundle

def read_bundle(path=PATH):
    path=Path(path)
    if not path.exists():return dict(schema_version=3,fingerprint_version=VERSION,parameters=PARAMETERS,records=[])
    if path.stat().st_size>128*1024*1024 or any(p.is_symlink() or p.is_junction() for p in [path,*path.parents]):raise ValueError('Bundle v3 non sicuro.')
    return validate(json.loads(path.read_bytes()))

def visual_similarity(a,b):
    if not a or not b:return 0.
    def sim(x,y):return 1-(int(x,16)^int(y,16)).bit_count()/64
    return max(.65*max(sim(x,y) for x in a[i:i+2] for y in b[j:j+2])+.35*sum(sim(a[i+k],b[j+k]) for k in range(2,6))/4 for i in range(0,24,6) for j in range(0,24,6))

class FingerprintIndex:
    def __init__(self,bundle):
        validate(bundle);self.records=[];self.pages=[];self.sha=defaultdict(set);self.field_map=defaultdict(set)
        post=defaultdict(list);cp=defaultdict(list)
        for r in bundle['records']:
            if r['status'] not in ['active','shared']:continue
            rid=len(self.records);record={k:v for k,v in r.items() if k not in ['pages','aggregate','field_set']};record['page_indexes']=[]
            self.records.append(record);self.sha[r['canonical_file_sha256']].add(r['document_id'])
            if r['field_set']:self.field_map[tuple(r['field_set'])].add(r['document_id'])
            for p in r['pages']:
                q=dict(p,resource_index=rid,document_id=r['document_id']);i=len(self.pages)
                # Immutable public integer tuples avoid repeated uint64 boxing
                # in per-request C intersections/bisections. Weights/postings
                # remain compact arrays. Measured complete index stays <100MB.
                for k in ['digital','ocr','anchors']:q[k]=tuple(int(h,16) for h in p[k])
                q['chars']={n:tuple(int(h,16) for h in v) for n,v in p['chars'].items()}
                self.pages.append(q);record['page_indexes'].append(i)
                for h in set(q['digital'])|set(q['ocr']):post[h].append(i)
                for h in q['chars']['4'][:16]:cp[h].append(i)
        self.postings={h:array('H',ids) for h,ids in post.items()};self.char_postings={h:array('H',ids) for h,ids in cp.items()}
        N=len(self.pages)
        buckets=array('I',[0])*32768
        bucket=lambda n,h:(h^(int(n)*2654435761))&32767
        for p in self.pages:
            for b in {bucket(n,h) for n in ['3','4','5'] for h in p['chars'][n]}:buckets[b]+=1
        self.page_weights=[tuple(array('f',(math.log((N+1)/(len(self.postings[h])+1))+1 for h in p[k])) for k in ['digital','ocr']) for p in self.pages]
        self.char_weights=[{n:array('f',(math.log((N+1)/(buckets[bucket(n,h)]+1))+1 for h in p['chars'][n])) for n in ['3','4','5']} for p in self.pages]
        self.den=[tuple(sum(w) for w in weights) for weights in self.page_weights]
        self.char_den=[{n:sum(weights[n]) for n in ['3','4','5']} for weights in self.char_weights]

    def candidates(self,q,n='4',reference=False):
        if reference:return list(range(len(self.pages)))
        votes=Counter(i for h in q['tokens'] for i in self.postings.get(h,()))
        cv=Counter(i for h in q['chars']['4'] for i in self.char_postings.get(h,()))
        return sorted({i for i,v in votes.items() if v>=3}|{i for i,v in cv.items() if v>=4})

    def page_scores_reference(self,q,ids,n='4',containment=True):
        rows=[]
        for i in ids:
            p=self.pages[i];channels=[];over=0
            for j,k in enumerate(['digital','ocr']):
                hits=[h for h in p[k] if h in q['tokens']];over=max(over,len(hits));den=self.den[i][j]
                score=sum(w for h,w in zip(p[k],self.page_weights[i][j]) if h in q['tokens'])/den if den else 0
                if containment and q['tokens']:score=min(1,score*max(1,p[k+'_count']/len(q['tokens'])))
                channels.append(score)
            hits=[h for h in p['chars'][n] if h in q['chars'][n]];den=self.char_den[i][n]
            char=sum(w for h,w in zip(p['chars'][n],self.char_weights[i][n]) if h in q['chars'][n])/den if den else 0
            if containment and q['chars'][n]:char=min(1,char*max(1,p['char_counts'][n]/len(q['chars'][n])))
            anchor=sum(h in q['anchors'] for h in p['anchors'])/len(p['anchors']) if p['anchors'] else 0
            score=.5*max(channels)+.35*char+.15*anchor
            rows.append(dict(document_id=p['document_id'],resource_index=p['resource_index'],page_index=i,canonical_page=p['number'],digital=channels[0],ocr=channels[1],chars=char,anchors=anchor,visual=0.,overlap=over,score=score))
        return rows

    def page_scores(self,q,ids,n='4',containment=True):
        # C-level intersection skips Python membership loops and duplicate
        # channel traversals. Sorted hits preserve the reference's summation
        # order exactly, including float32 public IDF weights. No top-K pruning.
        rows=[];tokens=q['tokens'];chars=q['chars'][n];anchors=q['anchors']
        nt=len(tokens);nc=len(chars)
        for i in ids:
            p=self.pages[i];channels=[];over=0
            for j,k in enumerate(('digital','ocr')):
                hashes=p[k];hits=sorted(tokens.intersection(hashes));over=max(over,len(hits));den=self.den[i][j]
                weights=self.page_weights[i][j]
                score=sum(weights[bisect_left(hashes,h)] for h in hits)/den if den else 0
                if containment and nt:score=min(1,score*max(1,p[k+'_count']/nt))
                channels.append(score)
            hashes=p['chars'][n];weights=self.char_weights[i][n];den=self.char_den[i][n]
            hits=sorted(chars.intersection(hashes));char=sum(weights[bisect_left(hashes,h)] for h in hits)/den if den else 0
            if containment and nc:char=min(1,char*max(1,p['char_counts'][n]/nc))
            anchor=len(anchors.intersection(p['anchors']))/len(p['anchors']) if p['anchors'] else 0
            score=.5*max(channels)+.35*char+.15*anchor
            rows.append(dict(document_id=p['document_id'],resource_index=p['resource_index'],page_index=i,canonical_page=p['number'],digital=channels[0],ocr=channels[1],chars=char,anchors=anchor,visual=0.,overlap=over,score=score))
        return rows

    def similarities(self,queries,*,n='4',aggregation='max',containment=True,reference=False,counters=None):
        aligned=defaultdict(list);initial=set();textcount=0
        for qi,q in enumerate(queries):
            ids=self.candidates(q,n,reference);initial.update(ids);textcount+=len(ids)
            scorer=self.page_scores_reference if reference else self.page_scores
            for row in scorer(q,ids,n,containment):row['input_page']=qi;aligned[row['document_id']].append(row)
        result=[]
        for did,rows in aligned.items():
            rows.sort(key=lambda r:(-r['score'],r['input_page'],r['canonical_page'],r['resource_index']))
            chosen=[];usedin=set();usedout=set()
            for r in rows:
                if r['input_page'] in usedin or r['page_index'] in usedout:continue
                chosen.append(r);usedin.add(r['input_page']);usedout.add(r['page_index'])
                if len(chosen)>=min(len(queries),2):break
            best=dict(chosen[0]);best['alignment']=[(r['input_page'],r['canonical_page']) for r in chosen]
            best['max_similarity']=best['score'];best['top2_average']=sum(r['score'] for r in chosen)/len(chosen)
            best['score']=best['top2_average'] if aggregation=='top2' else best['max_similarity']
            result.append(best)
        if counters is not None:counters.update(candidates_initial=len(initial),candidates_text=textcount,candidates_visual=0)
        return sorted(result,key=lambda r:(-r['score'],r['document_id']))

@lru_cache(maxsize=1)
def public_index():return FingerprintIndex(read_bundle())

@lru_cache(maxsize=1)
def revision():return hashlib.sha256(PATH.read_bytes()).hexdigest() if PATH.exists() else 'absent'
