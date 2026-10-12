"""Isolated local startup/index/RSS and warmed recognition, excluding OCR time."""
import argparse,json,platform,subprocess,sys,time
from benchmarks.round3_audit import ROOT,catalog,read,write
from benchmarks.round5_performance import rss,deep_size
from benchmarks.round6_recognition import identity,active_records,raw_record
from benchmarks.evaluate import quantile
from src.fingerprint_v2 import public_index,PATH
from src.recognize import recognize_catalog
from src.extract import extract_document
from src.fingerprint_visual import visual_for_bytes

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--worker',action='store_true');args=parser.parse_args()
    if not args.worker:
        started=time.perf_counter()
        raw=subprocess.check_output([sys.executable,'-m','benchmarks.round6_performance','--worker'],text=True,cwd=ROOT)
        # Native PDF imports may write a deprecation notice to stdout. The
        # worker emits exactly one JSON line; do not change the measured scope.
        records=[line for line in raw.splitlines() if line.startswith('{')]
        if len(records)!=1:raise ValueError('Missing or ambiguous performance worker JSON')
        result=json.loads(records[0])
        result['subprocess_wall_ms']=(time.perf_counter()-started)*1000
        write('benchmarks/results/round6/performance.json',result)
        write('benchmarks/results/round6/memory.json',dict(identity=result['identity'],fingerprints=result['fingerprints'],rss=result['rss'],scope=result['scope']))
        print(json.dumps({k:result[k] for k in ['latency_ms','catalog_load_ms','index_build_ms','fingerprints','gate_passed']},indent=2));return
    started=time.perf_counter();docs,families=catalog();catalog_ms=(time.perf_counter()-started)*1000
    begin=time.perf_counter();index=public_index();index_ms=(time.perf_counter()-begin)*1000
    synthetic=read('benchmarks/corpora/development_regression.json')['cases'];known=[]
    # Fixed resource order, no selection based on measured outcomes/latency.
    for r in active_records()[::max(1,len(active_records())//16)][:16]:
        raw=raw_record(r);ext='.pdf' if r['mime_type']=='application/pdf' else '.docx'
        try:
            ex=extract_document(raw,'canonical'+ext);known.append(dict(text=ex.text,visual=visual_for_bytes(raw,'canonical'+ext)))
        except (ValueError,OSError):continue
    cases=[dict(text=c['text'],visual=()) for c in synthetic]+known
    before=rss()
    for c in cases:recognize_catalog(c['text'],docs,families,visual_fingerprint=c['visual'])
    after=rss();times=[];samples=[after]
    for _ in range(6):
        for c in cases:
            t=time.perf_counter();recognize_catalog(c['text'],docs,families,visual_fingerprint=c['visual']);times.append((time.perf_counter()-t)*1000)
        samples.append(rss())
    size=deep_size(index.__dict__);latency=dict(n=len(times),p50=quantile(times,.5),p95=quantile(times,.95),p99=quantile(times,.99))
    report=dict(schema_version=2,identity=identity(),python=platform.python_version(),platform=platform.platform(),
        catalog_load_ms=catalog_ms,index_build_ms=index_ms,startup_ms=catalog_ms+index_ms,latency_ms=latency,
        warmup=len(cases),synthetic_cases=len(synthetic),official_known_cases=len(known),
        fingerprints=dict(disk_bytes=PATH.stat().st_size,index_bytes=size,resources=len(index.records),identities=len({r['document_id'] for r in index.records})),
        rss=dict(before_warm_bytes=before,after_warm_bytes=after,samples=samples,growth_after_warm_bytes=max(samples)-after),
        scope='Fresh process. Warm inference excludes extraction/OCR and visual generation (reported per case). Index is recursive Python records, arrays, postings, IDF weights; RSS is entire process, not additive. No upload-feature cache.',
        gate_passed=latency['p50']<=150 and latency['p95']<=250 and size<=100_000_000,
        target_passed=latency['p50']<=150 and size<=64_000_000)
    print(json.dumps(report))

if __name__=='__main__':main()
