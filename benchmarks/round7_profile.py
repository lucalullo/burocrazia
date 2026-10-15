"""Offline phase and cProfile diagnostics of the real final configuration."""
import argparse,cProfile,io,pstats,time
from benchmarks.round3_audit import ROOT,catalog,read,write
from benchmarks.round6_recognition import active_records,raw_record
from src.extract import extract_document
from src.fingerprint_visual import visual_for_bytes
from src.fingerprint_v2 import public_index,read_bundle
from src.recognize import recognize_catalog

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='benchmarks/results/round7/development_profile.json');args=parser.parse_args()
    docs,families=catalog();start=time.perf_counter();index=public_index();load=(time.perf_counter()-start)*1000
    cases=[(c['text'],()) for c in read('benchmarks/corpora/development_regression.json')['cases']]
    for item in read('benchmarks/results/round7/baseline/performance_sample.json')['resources']:
        r=next(r for r in read_bundle()['records'] if r['document_id']==item['document_id'] and r['canonical_file_sha256']==item['sha256'])
        raw=raw_record(r);name='canonical'+('.pdf' if r['mime_type']=='application/pdf' else '.docx')
        cases.append((extract_document(raw,name).text,visual_for_bytes(raw,name)))
    for text,visual in cases:recognize_catalog(text,docs,families,visual_fingerprint=visual)
    profile=cProfile.Profile();profile.enable()
    for text,visual in cases:recognize_catalog(text,docs,families,visual_fingerprint=visual)
    profile.disable();stats=pstats.Stats(profile);top=[]
    for (file,line,name),(primitive,calls,own,cumulative,callers) in sorted(stats.stats.items(),key=lambda kv:-kv[1][3])[:35]:
        top.append(dict(file=file.replace('\\','/').rsplit('/',1)[-1],line=line,function=name,calls=calls,own_seconds=own,cumulative_seconds=cumulative))
    write(args.output,dict(index_load_ms=load,cases=len(cases),top=top,scope='Warm recognition only; extraction and visual prepared before profiling. cProfile overhead means these are diagnostic, not release latency.'))
    print(top[:12])

if __name__=='__main__':main()
