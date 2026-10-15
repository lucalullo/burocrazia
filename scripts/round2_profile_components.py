"""Supplement the paired latency report with separately instrumented stages."""
import cProfile
from contextlib import closing
import json
from pathlib import Path
import pstats
import sqlite3
import sys
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src import recognize as engine
from src.database import list_documents
from src.families import list_document_families

def main():
    with closing(sqlite3.connect((ROOT/'data/catalog_seed.sqlite3').as_uri()+'?mode=ro',uri=True)) as db:
        db.row_factory=sqlite3.Row;docs=list_documents(db);families=list_document_families(db)
    cases=json.loads((ROOT/'benchmarks/corpora/development_regression.json').read_text(encoding='utf-8'))['cases']
    for c in cases:engine.recognize_catalog(c['text'],docs,families)
    totals={'title_similarity':0.,'generic_similarity':0.};calls={k:0 for k in totals}
    original_title=engine.fuzz.partial_ratio;original_generic=engine.fuzz.token_set_ratio
    def timed(key,original,*args,**kwargs):
        start=time.perf_counter()
        try:return original(*args,**kwargs)
        finally:totals[key]+=time.perf_counter()-start;calls[key]+=1
    engine.fuzz.partial_ratio=lambda *args,**kw:timed('title_similarity',original_title,*args,**kw)
    engine.fuzz.token_set_ratio=lambda *args,**kw:timed('generic_similarity',original_generic,*args,**kw)
    profile=cProfile.Profile();profile.enable()
    try:
        for c in cases:engine.recognize_catalog(c['text'],docs,families)
    finally:
        profile.disable();engine.fuzz.partial_ratio=original_title;engine.fuzz.token_set_ratio=original_generic
    stats=pstats.Stats(profile)
    def ms(name):return 1000*sum(v[3] for (_,_,f),v in stats.stats.items() if f==name)
    stages=dict(normalization_ms=ms('normalize_text'),entity_detection_ms=ms('_detect_entities'),candidate_scoring_inclusive_ms=ms('_score_candidate'),candidate_generation='full enumeration, no shortlist',family_matching_ms=ms('recognize_document_family'),title_similarity_ms=1000*totals['title_similarity'],generic_similarity_ms=1000*totals['generic_similarity'],similarity_calls=calls,
        note='Inclusive stage times overlap and must not be summed. Instrumentation adds overhead; release latency uses the separate uninstrumented paired run.',cases=len(cases))
    path=ROOT/'benchmarks/results/performance_profile_round2.json';report=json.loads(path.read_text(encoding='utf-8'));report['stage_timings']=stages;path.write_bytes((json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode('utf-8'));print(json.dumps(stages))

if __name__=='__main__':main()
