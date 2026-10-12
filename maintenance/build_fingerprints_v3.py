"""Offline page-level canonical signatures; no official text/pixels persisted."""
from __future__ import annotations
import argparse,hashlib,json,os,subprocess,time
from concurrent.futures import ProcessPoolExecutor,as_completed
from collections import Counter,defaultdict
from datetime import UTC,datetime
from pathlib import Path
from contextlib import closing
from benchmarks.round3_audit import ROOT,catalog,read,write
from src.fingerprint_v3 import PATH,VERSION,PARAMETERS,page_record,sketch,validate
from src.fingerprint_pages import image_signature,field_signature

WORK=ROOT/'benchmarks/work/fingerprint-v3'

def resource_pages(r):
    import fitz
    from src.extract import _read_bytes,_pdf_page_image,extract_document,MAX_PDF_PAGES
    from src.ocr import ocr_image,OCRError
    key=r['canonical_file_sha256']+'-'+hashlib.sha256(json.dumps(PARAMETERS,sort_keys=True).encode()).hexdigest()[:12]
    checkpoint=WORK/(key+'.json')
    if checkpoint.exists():return json.loads(checkpoint.read_bytes())
    raw=(ROOT/'benchmarks/cache'/(r['canonical_file_sha256']+'.body')).read_bytes();_read_bytes(raw)
    assert hashlib.sha256(raw).hexdigest()==r['canonical_file_sha256']
    started=time.monotonic();pages=[];fields=[]
    if r['mime_type']=='application/pdf':
        with fitz.open(stream=raw,filetype='pdf') as pdf:
            if pdf.needs_pass or not 1<=len(pdf)<=MAX_PDF_PAGES:raise ValueError('canonical_pdf_limits')
            for number,page in enumerate(pdf,1):
                for w in page.widgets() or ():
                    if w.field_name and len(fields)<512:fields.append(w.field_name)
                digital=page.get_text('text');ocr='';status='generated'
                with closing(_pdf_page_image(page)) as im:
                    visual=image_signature(im)
                    if time.monotonic()-started>120:status='bounded_timeout'
                    else:
                        try:ocr=ocr_image(im,min_text_length=0,auto_orient=False,deadline=started+120).text
                        except OCRError:status='failed'
                pages.append(page_record(number,digital,ocr,visual,ocr_status=status))
    else:
        ex=extract_document(raw,'canonical.docx');pages=[page_record(1,ex.text,'',(),ocr_status='unavailable_docx_renderer')]
    result=dict(pages=pages,field_set=list(field_signature(fields)),generated_at=datetime.now(UTC).isoformat(),seconds=time.monotonic()-started)
    checkpoint.write_bytes((json.dumps(result,ensure_ascii=False)+'\n').encode());return result

def atomic(bundle):
    validate(bundle);raw=(json.dumps(bundle,ensure_ascii=False,indent=2)+'\n').encode()
    temp=PATH.with_suffix('.json.tmp')
    if temp.exists():raise ValueError('Transazione v3 già presente.')
    try:
        with temp.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
        validate(json.loads(temp.read_bytes()));os.replace(temp,PATH)
    finally:
        if temp.exists():temp.unlink()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--validate-only',action='store_true');args=parser.parse_args()
    if args.validate_only:
        from src.fingerprint_v3 import read_bundle
        b=read_bundle();print('V3 valid',len(b['records']));return
    old=list(read('data/document_recognition_fingerprints_v2.json')['records']);WORK.mkdir(parents=True,exist_ok=True)
    extra=ROOT/'benchmarks/manifests/official_fingerprint_cache_v4.json';rejected=[]
    if extra.exists():
        from src.document_fingerprints import binding
        from src.extract import extract_document
        from src.fingerprint_match_v2 import safety_reason
        from src.recognize import normalize_text
        from src.title_evidence import exact_code_candidates
        docs,_=catalog();by={d.id:d for d in docs};seen={(r['document_id'],r['canonical_file_sha256']) for r in old}
        for r in read('benchmarks/manifests/official_fingerprint_cache_v4.json')['files']:
            key=(r['document_id'],r['sha256'])
            if key in seen or r['mime'] not in ['application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document']:continue
            try:
                d=by[r['document_id']];raw=(ROOT/'benchmarks/cache'/(r['sha256']+'.body')).read_bytes()
                assert hashlib.sha256(raw).hexdigest()==r['sha256']
                ex=extract_document(raw,'canonical'+('.pdf' if r['mime']=='application/pdf' else '.docx'))
                reason=safety_reason(ex.text,d,docs,exact=True)
                title=normalize_text(d.titolo_ufficiale.split(' / ')[0]);opening=normalize_text(ex.text[:2000])
                if reason or not (d.id in exact_code_candidates(ex.text,[d]) or len(title)>=20 and f' {title} ' in f' {opening} '):raise ValueError(reason or 'additional_resource_identity_not_supported')
                old.append(dict(document_id=d.id,source_id=d.source_id,canonical_file_sha256=r['sha256'],catalog_binding_sha256=binding(d),mime_type=r['mime'],url=r['url'],final_url=r['final_url'],acquisition_date=r['acquisition_date'],size_bytes=len(raw),status='active',ocr_metadata={}))
                seen.add(key)
            except (ValueError,OSError,RuntimeError) as exc:rejected.append(dict(document_id=r['document_id'],sha256=r['sha256'],reason=str(exc)))
    unique={r['canonical_file_sha256']:r for r in old};built={};failures=[]
    with ProcessPoolExecutor(max_workers=3) as pool:
        fs={pool.submit(resource_pages,r):sha for sha,r in unique.items()}
        for f in as_completed(fs):
            sha=fs[f]
            try:built[sha]=f.result()
            except (ValueError,OSError,RuntimeError) as exc:failures.append(dict(sha256=sha,error_type=type(exc).__name__,reason=str(exc)))
            if (len(built)+len(failures))%25==0:print('V3 canonical resources',len(built),'/',len(unique),'failures',len(failures),flush=True)
    shared=defaultdict(set)
    for r in old:shared[r['canonical_file_sha256']].add(r['document_id'])
    records=[]
    for r in old:
        data=built.get(r['canonical_file_sha256'])
        if not data:continue
        common=len(shared[r['canonical_file_sha256']])>1
        rec={k:r[k] for k in ['document_id','source_id','catalog_binding_sha256','canonical_file_sha256','mime_type','url','final_url','acquisition_date','size_bytes']}
        states=Counter(p['ocr_status'] for p in data['pages'])
        meta=dict(r['ocr_metadata'],pages=states['generated'],status='unavailable_docx_renderer' if r['mime_type']!='application/pdf' else 'generated' if states['generated']==len(data['pages']) else 'partial',total_pages=len(data['pages']),page_status_counts=dict(states))
        rec.update(generated_at=data['generated_at'],status='shared' if common and r['status'] in ['active','quarantined'] else r['status'],shared_kind='shared_attachment' if common else 'unambiguous',pages=data['pages'],aggregate=sketch({int(h,16) for p in data['pages'] for k in ['digital','ocr'] for h in p[k]},192),field_set=data['field_set'],ocr_metadata=meta)
        records.append(rec)
    b=dict(schema_version=3,fingerprint_version=VERSION,parameters=PARAMETERS,records=records);atomic(b)
    counts=Counter(p['ocr_status'] for d in records for p in d['pages'])
    write('benchmarks/results/round8/fingerprint_build.json',dict(resources=len(records),unique_resources=len(built),pages=sum(len(r['pages']) for r in records),identities=len({r['document_id'] for r in records if r['status']=='active'}),status_counts=dict(Counter(r['status'] for r in records)),page_ocr_counts=dict(counts),failures=failures,additional_resources_rejected=rejected,bundle_sha256=hashlib.sha256(PATH.read_bytes()).hexdigest(),limits='100 canonical pages/resource, 120 seconds OCR/resource, 20 MiB; real local Tesseract at 144 dpi. Runtime OCR remains capped at five pages. DOCX has one logical text page, no invented layout/OCR. No official text or image persisted.'))
    print('V3 canonical build complete',dict(counts),flush=True)

if __name__=='__main__':main()
