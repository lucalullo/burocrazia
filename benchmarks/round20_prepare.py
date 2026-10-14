"""Ignored public/synthetic preparation only; never call recognition."""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor,as_completed
from scripts.round20_common import *
from src.extract import extract_document
from src.fingerprint_pages import prepare
from src.text_quality import text_quality

def worker(item):
    raw=(ROOT/item['raw_file']).read_bytes();assert hashlib.sha256(raw).hexdigest()==item['sha256']
    revision=sha('src/extract.py')+sha('src/ocr.py')
    cache=WORK/'extracted'/(item['sha256']+'-'+Path(item['filename']).suffix.lstrip('.')+'.json');cache.parent.mkdir(exist_ok=True)
    if cache.exists():
        cached=read(cache);assert cached['extraction_revision']==revision
        return dict(item,**cached['prepared'])
    try:
        ex=extract_document(raw,item['filename']);ctx=prepare(raw,item['filename'],ex)
        value=dict(text=ex.text,texts=list(ctx.texts),representation=ctx.representation,numbers=list(ctx.numbers),field_set=list(ctx.field_set),quality=text_quality(ex.text),extraction_failed=False)
    except (ValueError,RuntimeError,OSError) as ex:
        value=dict(text='',texts=[''],representation='unknown',numbers=[],field_set=[],quality=text_quality(''),extraction_failed=True,extraction_error=type(ex).__name__+': '+str(ex))
    atomic_json(cache,dict(extraction_revision=revision,prepared=value,scope='Ignored public benchmark input only; no recognition result or personal upload.'))
    return dict(item,**value)

def main():
    preserved();assert not (WORK/'development-inputs.json').exists();WORK.mkdir(parents=True,exist_ok=True)
    # All canonical and already extracted historic diagnostic inputs remain
    # separate from threshold-fitting identities; no future V6 identities probed.
    historical=read('benchmarks/work/round16/semantic-inputs.json')['rows']+read('benchmarks/work/round16/semantic-supplement.json')['rows']
    prepared=[];tasks=[];seen=set()
    for c in historical:
        prepared.append(dict(c,id='HIST:'+c['id'],group='canonical' if c['category'] in ['canonical','canonical_legacy'] else 'historical',filename=c['filename'],quality=text_quality(c['text'])))
        if c['sha256']:seen.add(c['sha256'])
    # First prepare all original V5 known inputs and the full observed v3 as
    # development. Any new extraction is cached only under ignored benchmark work.
    for item in read('benchmarks/results/round19/evaluation_v5_prepared.json')['representations']:
        if item['unknown']:continue
        cc=item['case'];tasks.append(dict(id='DEV5:'+cc['id'],group='v5',category='development_regression_v5_after_fix',expected=cc['expected'],raw_file=item['path'],filename=Path(item['path']).name,sha256=item['sha256'],filled=item['filled'],scan_like=item['scan_like'],transform=cc['representation'],provenance=cc['provenance']))
    manifests=[('unknown_v1','benchmarks/manifests/official_unknown_release_v1.json'),('unknown_v2','benchmarks/manifests/official_unknown_release_v2.json'),('unknown_v3','benchmarks/manifests/official_unknown_release_v3.json')]
    for name,path in manifests:
        if not (ROOT/path).exists():continue
        for c in read(path)['cases']:
            h=c.get('SHA256',c.get('sha256'));mime=c.get('mime',c.get('mime_type','application/pdf'))
            ident=c.get('case_id',c.get('id'))
            # R14 two INAIL resources are adjudicated ambiguous, no forced
            # negative labels; original observations remain in historical audit.
            if name=='unknown_v2' and ident in ['U14-5f0c017c3d56e6c5','U14-c1fc4765c01dcd62']:continue
            if h in seen:continue
            seen.add(h);filename='development'+('.docx' if 'wordprocessingml' in mime else '.pdf')
            tasks.append(dict(id='DEVNEG:'+name+':'+ident,group='confirmed_unknown',category=name,expected=dict(match_type='NO_MATCH'),raw_file='benchmarks/cache/'+h+'.body',filename=filename,sha256=h,source=c.get('source'),unknown=True))
    # Reuse the complete Round9 historical development design, without invoking
    # its recognizer or rewriting any previous output. Reuse exact stored bytes
    # where available; assert every historical SHA after local preparation.
    from benchmarks.round9_calibrate import tasks as old_tasks
    from benchmarks.round6_recognition import transform_pdf
    from benchmarks.round8_common import raw_record
    old={c['id']:c for c in read('benchmarks/results/round9/calibration_observations_v5.json')['cases']}
    for j in old_tasks():
        prior=old[j['id']]
        if j.get('text_case'):
            text=j['text_case']['text'];prepared.append(dict(id='OLDDEV:'+j['id'],group='historical_development',category='hard_negative',expected=prior['expected'],text=text,texts=[text],representation='unknown',numbers=[],field_set=[],raw_file=None,filename='',sha256=None,quality=text_quality(text)))
            continue
        h=prior['input_sha256']
        if h in seen:continue
        seen.add(h)
        if 'unknown' in j:
            raw_file='benchmarks/cache/'+h+'.body';filename='development.'+j['unknown']['format']
        else:
            r=j['record'];filename=j.get('filename','development'+('.pdf' if r['mime_type']=='application/pdf' else '.docx'))
            if j.get('path'):raw_file=j['path']
            elif j['name']=='digital_exact':raw_file='benchmarks/cache/'+h+'.body'
            else:
                existing=next((p for p in WORK.glob(h+'.*') if p.suffix in ['.pdf','.jpg','.png'] and hashlib.sha256(p.read_bytes()).hexdigest()==h),None)
                if existing:p=existing
                else:
                    raw,suffix=transform_pdf(raw_record(r),j['params']);assert hashlib.sha256(raw).hexdigest()==h,'Historical development transform differs; no regenerated relabel'
                    p=WORK/(h+suffix);p.write_bytes(raw)
                raw_file=p.relative_to(ROOT).as_posix();filename=p.name
        tasks.append(dict(id='OLDDEV:'+j['id'],group='historical_development',category='old_development',expected=prior['expected'],raw_file=raw_file,filename=filename,sha256=h,filled=j['name'].startswith('filled') or j['name']=='valid_filled',scan_like=j['name']!='digital_exact' and 'record' in j,transform=j['name']))
    # Deduplicate extraction by bytes+format but preserve all expectation rows.
    aliases={};jobs={}
    for c in tasks:
        key=(c['sha256'],Path(c['filename']).suffix);aliases.setdefault(key,[]).append(c);jobs.setdefault(key,c)
    with ProcessPoolExecutor(max_workers=3) as pool:
        futures={pool.submit(worker,c):key for key,c in jobs.items()}
        for f in as_completed(futures):
            result=f.result();key=futures[f]
            for c in aliases[key]:prepared.append(dict(result,**c))
            if len(prepared)%50==0:print('R20 extracted development',len(prepared),flush=True)
    prepared.sort(key=lambda c:c['id']);assert len(prepared)==len({c['id'] for c in prepared})
    atomic_json(WORK/'development-inputs.json',dict(rows=prepared,recognition_calls=0,extraction_sha256=sha('src/extract.py'),ocr_sha256=sha('src/ocr.py'),scope='Ignored public/synthetic benchmark preparation only. No application upload text/cache. No fresh future release input.'))
    save('development_inputs_manifest',dict(cases=[dict(case_id=c['id'],group=c['group'],expected=c['expected'],sha256=c['sha256'],text_sha256=hashlib.sha256(c['text'].encode()).hexdigest(),quality=c['quality']) for c in prepared],counts=dict(Counter(c['group'] for c in prepared)),prepared_sha256=sha(WORK/'development-inputs.json'),recognition_calls=0))
    print('R20 prepared',len(prepared),Counter(c['group'] for c in prepared),flush=True)

if __name__=='__main__':main()
