"""Isolated warm decision timing, page/input work and OCR e2e kept separate."""
import argparse,cProfile,json,platform,pstats,subprocess,sys,time
from collections import defaultdict
from pathlib import Path
from benchmarks.round8_common import ROOT,OUT,catalog,read,write,identity,raw_record
from benchmarks.round5_performance import rss,deep_size
from benchmarks.evaluate import quantile
from src.fingerprint_v3 import public_index,read_bundle,PATH,visual_similarity
from src.fingerprint_pages import RequestPages,prepare
from src.fingerprint_decision_v5 import profile,match
from src.fingerprint_match_v2 import safety_reason
from src.fingerprint_pages import classify
from src.extract import extract_document
from src.recognize import recognize_catalog,normalize_text,recognize_document_family
OUT='benchmarks/results/round9/'

def describe(values):return dict(n=len(values),p50=quantile(values,.5),p95=quantile(values,.95),p99=quantile(values,.99))

def worker():
    start=time.perf_counter();docs,families=catalog();load=(time.perf_counter()-start)*1000
    start=time.perf_counter();ix=public_index();build=(time.perf_counter()-start)*1000;cases=[]
    for c in read('benchmarks/corpora/development_regression.json')['cases']:cases.append(dict(text=c['text'],context=RequestPages((c['text'],)),group='historical_fixed51'))
    for item in read('benchmarks/results/round7/baseline/performance_sample.json')['resources']:
        r=next(r for r in read_bundle()['records'] if r['document_id']==item['document_id'] and r['canonical_file_sha256']==item['sha256'])
        raw=raw_record(r);name='canonical'+('.pdf' if r['mime_type']=='application/pdf' else '.docx');ex=extract_document(raw,name)
        cases.append(dict(text=ex.text,context=prepare(raw,name,ex),group='historical_fixed51',extraction=ex))
    # Fixed sorted historical development scans, independent of fresh v4 results.
    scans=sorted((ROOT/'benchmarks/work/round6-representations').glob('*'))
    chosen=[];names=set()
    for p in scans:
        if p.suffix not in ['.pdf','.jpg','.png']:continue
        tag=p.stem.split('-',1)[-1]
        if tag in ['digital_exact','first_page_only'] or tag in names:continue
        names.add(tag);chosen.append(p)
        if len(chosen)>=14:break
    e2e=[]
    for p in chosen:
        raw=p.read_bytes();t=time.perf_counter();ex=extract_document(raw,p.name);e2e.append((time.perf_counter()-t)*1000)
        cases.append(dict(text=ex.text,context=prepare(raw,p.name,ex),group='historical_scans',extraction=ex))
    import fitz
    for c in cases[-14:-12]:
        p=c['context']
        if p.representation!='image':continue
        with fitz.open() as pdf:
            page=pdf.new_page();page.insert_image(page.rect,stream=p.raw);raw=pdf.tobytes()
        cases.append(dict(text=c['text'],context=RequestPages(p.texts,'scanned_pdf',numbers=(1,),raw=raw,filename='wrapped.pdf'),group='historical_scans_wrapped_pdf',extraction=c['extraction']))
    def request(c):
        p=c['context'];return RequestPages(p.texts,p.representation,p.field_set,p.numbers,p.raw,p.filename)
    before=rss()
    for c in cases:recognize_catalog(c['text'],docs,families,page_context=request(c))
    after=rss();times=defaultdict(list);counters=[];samples=[after]
    for _ in range(6):
        for c in cases:
            p=request(c);t=time.perf_counter();recognize_catalog(c['text'],docs,families,page_context=p);elapsed=(time.perf_counter()-t)*1000
            times[c['group']].append(elapsed);times['combined'].append(elapsed);counters.append(dict(p.counters))
            times['representation:'+p.representation].append(elapsed)
        samples.append(rss())
    components=defaultdict(list)
    def measure(k,fn):
        t=time.perf_counter();out=fn();components[k].append((time.perf_counter()-t)*1000);return out
    for c in cases:
        p=request(c);measure('normalization',lambda:normalize_text(c['text'][:2000]));queries=measure('input_fingerprint_generation',p.queries)
        if c.get('extraction'):measure('representation_classification',lambda:classify(p.filename,c['extraction'],has_fields=bool(p.field_set),filled=p.representation=='filled_acroform'))
        ids=measure('candidate_retrieval',lambda:ix.candidates(queries[0]));q=queries[0];n=profile()['settings']['char_ngram']
        def ocr_compare():return [sum(w for h,w in zip(ix.pages[i]['ocr'],ix.page_weights[i][1]) if h in q['tokens'])/ix.den[i][1] if ix.den[i][1] else 0 for i in ids]
        measure('ocr_sketch_compare',ocr_compare)
        measure('char_overlap',lambda:[sum(w for h,w in zip(ix.pages[i]['chars'][n],ix.char_weights[i][n]) if h in q['chars'][n]) for i in ids])
        measure('anchors',lambda:[len(q['anchors'].intersection(ix.pages[i]['anchors'])) for i in ids])
        measure('entity_version_checks',lambda:[safety_reason(c['text'],d,docs,exact=True) for d in docs[:5]])
        v=p.visual(0) if p.raw and ids else ()
        measure('visual_compare',lambda:[visual_similarity(v,ix.pages[i]['visual']) for i in ids[:25]])
        measure('decision_fusion_inclusive',lambda:match(c['text'],docs,pages=request(c)))
        measure('family_fallback',lambda:recognize_document_family(c['text'],families,known_entities=[d.ente for d in docs]))
    prof=cProfile.Profile();prof.enable()
    for c in cases:recognize_catalog(c['text'],docs,families,page_context=request(c))
    prof.disable();stats=pstats.Stats(prof)
    top=[dict(file=Path(f).name,line=l,function=n,calls=v[1],own_seconds=v[2],cumulative_seconds=v[3]) for (f,l,n),v in sorted(stats.stats.items(),key=lambda kv:-kv[1][3])[:40]]
    size=deep_size(ix.__dict__)
    result=dict(identity=identity(),python=platform.python_version(),platform=platform.platform(),catalog_load_ms=load,index_build_ms=build,startup_ms=load+build,latency_ms=describe(times['combined']),by_input_group={k:describe(v) for k,v in times.items() if k!='combined'},index=dict(bytes=size,pages=len(ix.pages),resources=len(ix.records),identities=len({r['document_id'] for r in ix.records}),disk_bytes=PATH.stat().st_size),rss=dict(before_warm_bytes=before,after_warm_bytes=after,samples=samples,growth_after_warm_bytes=max(samples)-after),components={k:describe(v) for k,v in components.items()},cprofile=top,counters=dict(candidates_initial=describe([c.get('candidates_initial',0) for c in counters]),candidates_text=describe([c.get('candidates_text',0) for c in counters]),candidates_visual=describe([c.get('candidates_visual',0) for c in counters]),page_renders=sum(c.get('page_renders',0) for c in counters)),scope='Fresh isolated process. Warm recognition excludes extraction/OCR and pre-extraction field enumeration; includes per-request text fingerprints and lazy visual rendering. No input features retained across timed requests. Fixed51 uses the same 35 synthetic+16 official inputs as R7; scan group uses fixed sorted historical scans. Component probes are non-additive, outside the latency measure; OCR e2e is reported from evaluation raw, separately.')
    result['ocr_end_to_end_extraction_ms']=describe(e2e)
    result['decision_version']='fingerprint-decision-v5'
    result['scope']+=' Round9 additionally measures two historical images wrapped in PDFs using their already available OCR text; OCR extraction timing is separate, before warm timing. No v5 evaluation identities selected.'
    print(json.dumps(result))

def main():
    p=argparse.ArgumentParser();p.add_argument('--worker',action='store_true');p.add_argument('--final',action='store_true');a=p.parse_args()
    if a.worker:worker();return
    raw=subprocess.check_output([sys.executable,'-m','benchmarks.round9_performance','--worker'],cwd=ROOT,text=True)
    lines=[l for l in raw.splitlines() if l.startswith('{')];assert len(lines)==1
    r=json.loads(lines[0]);name='performance' if a.final else 'development_performance'
    write(OUT+name+'.json',r)
    write(OUT+'performance_profile_v2.json',dict(identity=r['identity'],components=r['components'],cprofile=r['cprofile'],scope=r['scope']))
    print(json.dumps({k:r[k] for k in ['latency_ms','by_input_group','index','counters']},indent=2))

if __name__=='__main__':main()
