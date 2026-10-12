"""Offline canonical OCR builder. Public bundle contains hashes, never text."""
from __future__ import annotations
import argparse,hashlib,json,os,subprocess
from collections import Counter,defaultdict
from datetime import UTC,datetime
from pathlib import Path
from benchmarks.round3_audit import ROOT,catalog,read,write
from src.fingerprint_v2 import PATH,PARAMETERS,VERSION,make_record,validate,read_bundle
from src.fingerprint_visual import first_page_image,image_signature
from src.fingerprint_match_v2 import safety_reason
from src.document_fingerprints import binding
from src.extract import extract_document
from src.ocr import ocr_image,TESSERACT_COMMAND_ENV,OCRError

def atomic_bundle(bundle,path=PATH):
    validate(bundle);path=Path(path)
    if any(p.is_symlink() or p.is_junction() for p in [path,*path.parents]):raise ValueError('Destinazione collegata.')
    raw=(json.dumps(bundle,ensure_ascii=False,indent=2)+'\n').encode()
    if path.exists() and path.read_bytes()==raw:return False
    tmp=path.with_suffix('.json.tmp')
    if tmp.exists():raise ValueError('Transazione già presente.')
    try:
        with tmp.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
        validate(json.loads(tmp.read_bytes()));os.replace(tmp,path)
    finally:
        if tmp.exists():tmp.unlink()
    return True

def build(*,worker=False,shard=0,shards=1):
    docs,_=catalog();by={d.id:d for d in docs}
    resources=read('benchmarks/manifests/official_fingerprint_cache_v2.json')['files']
    if worker:resources=[r for i,r in enumerate(resources) if i%shards==shard]
    work=ROOT/'benchmarks/work/fingerprint-v2';work.mkdir(parents=True,exist_ok=True)
    negative=set()
    for name in ['official_documents_v1','official_documents_v2','official_holdout_v1','official_holdout_v2']:
        negative.update(c['sha256'] for c in read('benchmarks/manifests/'+name+'.json')['cases'] if c.get('expected_match_type')=='NO_MATCH')
    command=os.environ.get(TESSERACT_COMMAND_ENV,'tesseract')
    engine=subprocess.check_output([command,'--version'],text=True).splitlines()[0]
    traineddata={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(command).parent.glob('tessdata/*.traineddata')}
    records=[];failures=[]
    for i,r in enumerate(resources):
        d=by[r['document_id']];key=str(d.id)+'-'+r['sha256'];checkpoint=work/(key+'.json')
        try:
            if d.stato_verifica in ['demo','rifiutato']:raise ValueError('non_operational')
            if r['sha256'] in negative or r.get('container_sha256') in negative:raise ValueError('frozen_unknown_label_conflict')
            if checkpoint.exists():
                record=json.loads(checkpoint.read_bytes())
                if record['catalog_binding_sha256']==binding(d):records.append(record);continue
            raw=(ROOT/'benchmarks/cache'/(r['sha256']+'.body')).read_bytes()
            if len(raw)!=r['size'] or hashlib.sha256(raw).hexdigest()!=r['sha256']:raise ValueError('cache_hash_mismatch')
            ext='.pdf' if r['mime']=='application/pdf' else '.docx'
            ex=extract_document(raw,'canonical'+ext)
            reason=safety_reason(ex.text,d,docs,exact=True)
            if reason:raise ValueError('canonical_'+reason)
            ocr_text='';visual=();meta=dict(status='unavailable_docx_renderer',engine=engine,pages=0)
            if ext=='.pdf':
                with first_page_image(raw,'canonical.pdf') as im:
                    visual=image_signature(im)
                    try:
                        ocr=ocr_image(im,auto_orient=False);ocr_text=ocr.text
                        meta=dict(status='generated',engine=engine,language=ocr.language,dpi=144,pages=1,traineddata_sha256=traineddata)
                    except OCRError as exc:meta=dict(status='failed',engine=engine,pages=1,error_type=type(exc).__name__)
            receipt=dict(requested_url=r['url'],final_url=r['final_url'],acquired_at=r['acquisition_date'])
            record=make_record(d,raw,ex.text,ocr_text=ocr_text,visual=visual,receipt=receipt,mime=r['mime'],
                page_count=ex.total_pages if ext=='.pdf' else None,generated_at=datetime.now(UTC).isoformat(),
                ocr_metadata=meta,container_sha256=r.get('container_sha256'))
            if len(record['digital'])<20 and len(record['ocr'])<20:raise ValueError('insufficient_canonical_content')
            checkpoint.write_bytes((json.dumps(record,ensure_ascii=False)+'\n').encode());records.append(record)
        except (ValueError,OSError,RuntimeError) as exc:failures.append(dict(document_id=d.id,sha256=r['sha256'],reason=str(exc)))
        if i%20==0:print('OCR canonical',i+1,'/',len(resources),'built',len(records),'failures',len(failures),flush=True)
    if worker:
        print('Worker',shard,'complete; hash-only records',len(records),'failures',len(failures),flush=True)
        return
    shared=defaultdict(set)
    for r in records:shared[r['canonical_file_sha256']].add(r['document_id'])
    for r in records:
        if len(shared[r['canonical_file_sha256']])>1:r['status']='quarantined'
    # Older bytes at the same URL are stale only with an actual newer receipt.
    latest={}
    for r in records:
        key=(r['document_id'],r['url']);latest[key]=max(latest.get(key,''),r['acquisition_date'])
    for r in records:
        if r['acquisition_date']<latest[(r['document_id'],r['url'])]:r['status']='stale'
    bundle=dict(schema_version=2,fingerprint_version=VERSION,parameters=PARAMETERS,
        records=sorted(records,key=lambda r:(r['document_id'],r['canonical_file_sha256'])))
    atomic_bundle(bundle)
    write('benchmarks/results/round6/fingerprint_build.json',dict(resources=len(resources),records=len(records),
        identities=len({r['document_id'] for r in records if r['status']=='active'}),
        status_counts=dict(Counter(r['status'] for r in records)),ocr_counts=dict(Counter(r['ocr_metadata']['status'] for r in records)),
        failures=failures,bundle_sha256=hashlib.sha256(PATH.read_bytes()).hexdigest(),
        notes='Prime pagine PDF a 144 dpi, stesso OCR locale del runtime. Nessun testo/immagine OCR persistito. DOCX senza renderer: solo canale digitale, esplicitamente non OCR.'))
    print('V2 built',len(records),'resources',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--worker',action='store_true');parser.add_argument('--shard',type=int,default=0);parser.add_argument('--shards',type=int,default=1);parser.add_argument('--validate-only',action='store_true');a=parser.parse_args()
    if not 1<=a.shards<=4 or not 0<=a.shard<a.shards:parser.error('Invalid bounded worker shard')
    if a.validate_only:validate(read_bundle());print('Fingerprint v2 schema valid.')
    else:build(worker=a.worker,shard=a.shard,shards=a.shards)
