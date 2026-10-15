"""Paired latency and isolated-process current RSS, with explicit memory scopes."""
from __future__ import annotations
import argparse
import ctypes
from dataclasses import fields,is_dataclass
import json
from pathlib import Path
import platform
import sqlite3
import subprocess
import sys
import time
import tracemalloc
import types
from benchmarks.evaluate import quantile,code_hash
from src.database import list_documents
from src.families import list_document_families
from src import recognize as candidate
from src.title_evidence import title_index,code_index
from src.technical_anchors import load_features

ROOT=Path(__file__).resolve().parents[1]

def load_engine(name):
    if name=='candidate':return candidate
    ref='f9e1fa06821907da53f75417555bd3cbdd50c7d0'
    source=subprocess.check_output(['git','show',ref+':src/recognize.py'],cwd=ROOT)
    module=types.ModuleType('performance_'+name);sys.modules[module.__name__]=module
    exec(compile(source,name+'/src/recognize.py','exec'),module.__dict__)
    return module

def data(name):
    path=ROOT/'data/catalog_seed.sqlite3'
    with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row;return list_documents(db),list_document_families(db)

def rss():
    if sys.platform=='win32':
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)]+[(k,ctypes.c_size_t) for k in ['PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage']]
        result=Counters();result.cb=ctypes.sizeof(result)
        process=ctypes.windll.kernel32.GetCurrentProcess;process.restype=wintypes.HANDLE
        measure=ctypes.windll.psapi.GetProcessMemoryInfo
        measure.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD];measure.restype=wintypes.BOOL
        if not measure(process(),ctypes.byref(result),result.cb):raise OSError('RSS not available')
        return result.WorkingSetSize
    if sys.platform.startswith('linux'):
        import os
        return int(Path('/proc/self/statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE')
    import os
    return int(subprocess.check_output(['ps','-o','rss=','-p',str(os.getpid())]))*1024

def deep_size(value,seen=None):
    seen=set() if seen is None else seen
    if id(value) in seen:return 0
    seen.add(id(value));total=sys.getsizeof(value)
    if isinstance(value,dict):return total+sum(deep_size(k,seen)+deep_size(v,seen) for k,v in value.items())
    if isinstance(value,(tuple,list,set,frozenset)):return total+sum(deep_size(v,seen) for v in value)
    if is_dataclass(value):return total+sum(deep_size(getattr(value,f.name),seen) for f in fields(value))
    return total

def guard(report):
    return all(report['ratios_to_baseline'][k]<=1.5 for k in ['p50','p95']) and report['memory']['candidate']['rss_growth_after_warm_bytes']<=16*1024*1024

def memory_worker(name,cases):
    engine=load_engine(name);docs,fams=data(name);start=rss()
    for c in cases:engine.recognize_catalog(c['text'],docs,fams)
    samples=[rss()]
    for _ in range(8):
        for c in cases:engine.recognize_catalog(c['text'],docs,fams)
        samples.append(rss())
    tracemalloc.start();engine.recognize_catalog(cases[0]['text'],docs,fams);_,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    index_bytes=deep_size((__import__('src.document_fingerprints',fromlist=['public_index']).public_index().__dict__,title_index(tuple(docs)),code_index(tuple(docs)),load_features(),candidate._unversioned_annual_peers(tuple(docs)),candidate._catalog_domains(tuple(docs)),candidate.safety_profiles())) if name=='candidate' else 0
    return dict(rss_before_warm_bytes=start,rss_after_warm_bytes=samples[0],rss_samples_bytes=samples,rss_growth_after_warm_bytes=max(samples)-samples[0],warm_python_peak_bytes=peak,catalog_objects_bytes=deep_size((docs,fams)),technical_index_bytes=index_bytes,index_scope='Fingerprint records/postings, title/code indexes, sparse features and safety profiles; recursive Python object size, excluding other legacy caches')

def main():
    p=argparse.ArgumentParser();p.add_argument('--memory-worker',choices=['baseline','candidate']);a=p.parse_args()
    cases=json.loads((ROOT/'benchmarks/corpora/development_regression.json').read_text(encoding='utf-8'))['cases']
    if a.memory_worker:print(json.dumps(memory_worker(a.memory_worker,cases)));return
    load_started=time.perf_counter(); loaded=data('candidate'); catalog_load_ms=(time.perf_counter()-load_started)*1000
    candidate._catalog_features.cache_clear(); title_index.cache_clear(); code_index.cache_clear()
    build_started=time.perf_counter()
    for document in loaded[0]:candidate._catalog_features(document)
    title_index(tuple(loaded[0])); code_index(tuple(loaded[0])); candidate._unversioned_annual_peers(tuple(loaded[0])); candidate._catalog_domains(tuple(loaded[0])); load_features()
    from src.document_fingerprints import public_index,PATH
    public_index()
    index_build_ms=(time.perf_counter()-build_started)*1000
    runners={n:(load_engine(n),data(n)) for n in ['baseline','candidate']};times={n:[] for n in runners}
    for engine,args in runners.values():
        for c in cases:engine.recognize_catalog(c['text'],*args)
    for iteration in range(6):
        for i,c in enumerate(cases):
            order=['baseline','candidate'] if (i+iteration)%2 else ['candidate','baseline']
            for name in order:
                engine,args=runners[name];start=time.perf_counter();engine.recognize_catalog(c['text'],*args);times[name].append((time.perf_counter()-start)*1000)
    measures={name:dict(n=len(v),p50=quantile(v,.5),p95=quantile(v,.95)) for name,v in times.items()}
    memory={}
    for name in runners:
        raw=subprocess.check_output([sys.executable,'-m','benchmarks.round5_performance','--memory-worker',name],cwd=ROOT,text=True)
        memory[name]=json.loads(raw)
    from benchmarks.round4_common import runtime_hash
    report=dict(schema_version=1,baseline_ref='f9e1fa06821907da53f75417555bd3cbdd50c7d0',code_sha256=code_hash(),runtime_sha256=runtime_hash(),python=platform.python_version(),platform=platform.platform(),warmup=35,iterations=6,order='Interleaved Round4 and candidate, reverse every case/iteration',latency_ms=measures,ratios_to_baseline={k:measures['candidate'][k]/measures['baseline'][k] for k in ['p50','p95']},ratios_to_round4={k:measures['candidate'][k]/measures['baseline'][k] for k in ['p50','p95']},memory=memory,catalog_load_ms=catalog_load_ms,index_build_ms=index_build_ms,
        memory_ratios={k:memory['candidate'][k]/memory['baseline'][k] if memory['baseline'][k] else None for k in ['rss_after_warm_bytes','catalog_objects_bytes','warm_python_peak_bytes']},memory_scope='Current working set/RSS in separate fresh processes. Eight repeated warm passes; 16 MiB growth ceiling is a stability guard, not a general RAM certification.')
    report['guard_passed']=guard(report)
    fp_bytes=deep_size(public_index().__dict__);count=len(public_index().records)
    report['fingerprints']=dict(disk_bytes=PATH.stat().st_size,index_bytes=fp_bytes,
        records=count,average_disk_bytes_per_document=PATH.stat().st_size/count if count else None,
        average_index_bytes_per_document=fp_bytes/count if count else None,
        projected_index_bytes_for_1200=fp_bytes*1200/count if count else None,
        memory_scope='Recursive Python size of canonical signature records and tuple posting lists; process RSS reported separately.')
    path=ROOT/'benchmarks/results/round5/performance.json';path.write_bytes((json.dumps(report,indent=2)+'\n').encode())
    (ROOT/'benchmarks/results/round5/memory.json').write_text(json.dumps(dict(code_sha256=code_hash(),runtime_sha256=runtime_hash(),measurements=memory,scope=report['memory_scope']),indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:report[k] for k in ['latency_ms','ratios_to_baseline','ratios_to_round4','memory_ratios','guard_passed']},indent=2))

if __name__=='__main__':main()
