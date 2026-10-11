"""Capture pre-fix scores from actual historical files; never rewrite old results."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from benchmarks.round4_common import OUT,catalog,read,write,texts
from benchmarks.evaluate import metrics,verify_locks
from src import recognize as engine
from scripts.verify_catalog import verify

def main():
    if (ROOT/OUT/'false_acceptance_before.json').exists():
        raise ValueError('Pre-fix audit already captured; do not overwrite it with the changed engine.')
    verify_locks();baseline={}
    for name,path in [('development','benchmarks/results/round3/official_development_v2.json'),('holdout_v1_historical','benchmarks/results/round3/official_holdout_v1.json')]:
        r=read(path);assert metrics(r['cases'])==r['summary']['metrics'];baseline[name]=r['summary']
    locks=read('benchmarks/manifests/official_holdout_locks_v1.json')['sha256']
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==s for p,s in locks.items())
    baseline.update(catalog=verify(ROOT/'data/catalog_seed.sqlite3'),locked_v1_final=read('benchmarks/results/round3/final/release_locked_v1.json')['summary'],prompt_discrepancy='Round 3 final locked v1 is 60/69; 59/69 belongs to Round 2. Both historical raw results preserved.')
    write(OUT+'baseline_verified.json',baseline)
    findings=read('benchmarks/results/round3/holdout_failures.json')['wrong_accepted'];ids={f['case_id'] for f in findings}
    manifest,values=texts('official_holdout_v1',ids);docs,fams=catalog();trace=[];original=engine._score_candidate;rows=[]
    def capture(*args,**kwargs):
        v=original(*args,**kwargs);trace.append(v);return v
    engine._score_candidate=capture
    try:
        for f in findings:
            trace.clear();result=engine.recognize_catalog(values[f['case_id']]['text'],docs,fams)
            predicted=f['observed']['document_id'];top=next(t for t in trace if t.document.id==predicted)
            eligible=sorted([t for t in trace if t.strong_evidence and not t.entity_conflict],key=lambda t:(t.evidence_rank,t.score),reverse=True)
            runner=next((t for t in eligible if t.document.id!=predicted),None)
            row=dict(f,score=top.score,runner_up=dict(document_id=runner.document.id,score=runner.score) if runner else None,margin=result.document_score_margin,strong_signals=[s for s in top.signals if s in {'codice esatto','titolo','ente'}],weak_signals=[s for s in top.signals if s not in {'codice esatto','titolo','ente'}],contradictions_ignored=list(top.conflicts),root_cause='pending_content_analysis',general_rule_violated='pending',minimal_safe_fix='pending',regression_test='pending')
            rows.append(row);print(f['case_id'],repr(values[f['case_id']]['text'][:750]),'SCORE',top.score,'SIGNALS',top.signals,flush=True)
    finally:engine._score_candidate=original
    r061=next(c for c in read('benchmarks/corpora/release_locked_v2.json')['cases'] if c['id']=='R061')
    result=engine.recognize_catalog(r061['text'],docs,fams);write(OUT+'r061_before.json',dict(case=r061,result=asdict(result)))
    write(OUT+'false_acceptance_before.json',rows)
    print('Baseline and six blockers captured',flush=True)

if __name__=='__main__':main()
