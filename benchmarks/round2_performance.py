"""Alternate unchanged 0.6.1 baseline and candidate on the same machine."""
from __future__ import annotations
import cProfile
import hashlib
import json
from pathlib import Path
import platform
import pstats
import sqlite3
import subprocess
import sys
import time
import tracemalloc
import types

from benchmarks.evaluate import quantile, code_hash
from src.database import list_documents
from src.families import list_document_families
from src import recognize as candidate

ROOT=Path(__file__).resolve().parents[1]

def read_catalog(path):
    start=time.perf_counter()
    with sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row
        result=list_documents(db),list_document_families(db)
    return result,(time.perf_counter()-start)*1000

def main():
    ref='d747d0ff663bbf5ac89f5ba1de71d2cdce22018c'
    source=subprocess.check_output(['git','show',ref+':src/recognize.py'],cwd=ROOT)
    module=types.ModuleType('baseline_round2');sys.modules[module.__name__]=module
    exec(compile(source,'baseline/src/recognize.py','exec'),module.__dict__)
    old,oldload=read_catalog(ROOT/'reports/baseline/catalog_seed.sqlite3')
    new,newload=read_catalog(ROOT/'data/catalog_seed.sqlite3')
    cases=json.loads((ROOT/'benchmarks/corpora/development_regression.json').read_text(encoding='utf-8'))['cases']
    runners={'baseline':(module,old),'candidate':(candidate,new)}
    for engine,(docs,fams) in runners.values():
        for case in cases:engine.recognize_catalog(case['text'],docs,fams)
    times={k:[] for k in runners};rounds=[]
    for iteration in range(6):
        for index,case in enumerate(cases):
            order=['baseline','candidate'] if (iteration+index)%2==0 else ['candidate','baseline']
            for name in order:
                engine,(docs,fams)=runners[name];start=time.perf_counter();engine.recognize_catalog(case['text'],docs,fams)
                times[name].append((time.perf_counter()-start)*1000)
        rounds.append({name:{'p50':quantile(v[-len(cases):],.5),'p95':quantile(v[-len(cases):],.95)} for name,v in times.items()})
    memory={}
    for name,(engine,(docs,fams)) in runners.items():
        tracemalloc.start();engine.recognize_catalog(cases[0]['text'],docs,fams);_,peak=tracemalloc.get_traced_memory();tracemalloc.stop();memory[name]=peak
    profiler=cProfile.Profile();profiler.enable()
    for case in cases:candidate.recognize_catalog(case['text'],*new)
    profiler.disable();stats=pstats.Stats(profiler)
    functions=[dict(function=name,calls=v[1],self_seconds=v[2],cumulative_seconds=v[3]) for (file,line,name),v in stats.stats.items() if 'recognize.py' in file]
    summary={k:{'n':len(v),'p50':quantile(v,.5),'p95':quantile(v,.95)} for k,v in times.items()}
    report=dict(schema_version=1,baseline_commit=ref,baseline_code_sha256=hashlib.sha256(source).hexdigest(),candidate_code_sha256=code_hash(),python=platform.python_version(),platform=platform.platform(),warmup_cases=35,iterations=6,order='alternate per case and iteration',summary=summary,rounds=rounds,
        ratios={k:summary['candidate'][k]/summary['baseline'][k] for k in ['p50','p95']},catalog_load_ms=dict(baseline=oldload,candidate=newload),warm_python_peak_bytes=memory,memory_scope='one warm recognition; Python allocations only; catalog metadata caches already prepared',functions=sorted(functions,key=lambda f:f['cumulative_seconds'],reverse=True),
        decision='Retained full scan: repeated metadata/year analysis, not fuzzy candidate enumeration, dominated the initial profile. Both latency ratios must pass before expansion; no shortlist or index equivalence claim.')
    path=ROOT/'benchmarks/results/performance_profile_round2.json';path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ['summary','ratios','warm_python_peak_bytes']},indent=2))

if __name__=='__main__':main()
