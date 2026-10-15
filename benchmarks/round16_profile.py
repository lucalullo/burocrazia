import sys,cProfile,pstats,time,ast,statistics,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from benchmarks.transactional_writer import atomic_json
from benchmarks.round12_performance import suite,fresh_request
from benchmarks.round3_audit import catalog
from benchmarks.round9_performance import describe
from benchmarks.round8_common import identity
from src.recognize import recognize_catalog
from src.fingerprint_pages import classify
from types import SimpleNamespace
out=ROOT/'benchmarks/results/round16';out.mkdir(exist_ok=True)
assert not (out/'performance_profile.json').exists(),'Baseline profile already recorded; preserve it'
prep=cProfile.Profile();prep.enable();cases,e2e=suite();prep.disable()
docs,families=catalog()
for c in cases:recognize_catalog(c['text'],docs,families,page_context=fresh_request(c['context']))
raw=[]
for c in cases:
    t=time.perf_counter();recognize_catalog(c['text'],docs,families,page_context=fresh_request(c['context']));raw.append(dict(case_id=c['id'],milliseconds=(time.perf_counter()-t)*1000))
p=cProfile.Profile();p.enable()
for c in cases:recognize_catalog(c['text'],docs,families,page_context=fresh_request(c['context']))
p.disable();stats=pstats.Stats(p);ps=pstats.Stats(prep)
def total(names):return 1000*sum(v[3] for (f,l,n),v in stats.stats.items() if (Path(f).name,n) in names)
groups={
'normalization':{('recognize.py','normalize_text'),('document_fingerprints.py','streams')},
'candidate_generation':{('recognize.py','_score_candidate')},
'page_candidate_lookup':{('fingerprint_v3.py','candidates')},
'ocr_char_overlap':{('fingerprint_v3.py','page_scores'),('fingerprint_v3.py','features')},
'visual_layout_compare':{('fingerprint_pages.py','image_signature'),('fingerprint_v3.py','visual_similarity')},
'entity_version_checks':{('fingerprint_match_v2.py','safety_reason'),('fingerprint_decision_v3.py','entity_evidence'),('recognize.py','_annual_version_evidence')},
'decision_fusion':{('fingerprint_decision_v4.py','match')},
'family_fallback':{('recognize.py','recognize_document_family')}}
components={k:dict(inclusive_ms=total(v),method='cProfile inclusive function attribution; overlapping stages are not additive') for k,v in groups.items()}
components['representation_classification']=dict(inclusive_ms=1000*sum(v[3] for (f,l,n),v in ps.stats.items() if Path(f).name=='fingerprint_pages.py' and n=='classify'),scope='Actual preparation, outside warm recognition')
# Attribute the actual diagnostics blocks with line tracing on a fixed subset.
source=ROOT/'src/fingerprint_decision_v4.py';tree=ast.parse(source.read_bytes());lines=set()
for node in ast.walk(tree):
    if isinstance(node,ast.If) and ast.unparse(node.test)=='diagnostics is not None':lines.update(range(node.lineno,node.end_lineno+1))
acc=[0.,0];state={}
def trace(frame,event,arg):
    if frame.f_code.co_filename!=str(source) or frame.f_code.co_name!='match':return None
    key=id(frame);now=time.perf_counter()
    if key in state:
        line,t=state[key]
        if line in lines:acc[0]+=now-t;acc[1]+=1
    if event=='return':state.pop(key,None)
    else:state[key]=(frame.f_lineno,now)
    return trace
sys.settrace(trace)
try:
    for c in [*cases[:3],*cases[-4:]]:recognize_catalog(c['text'],docs,families,page_context=fresh_request(c['context']))
finally:sys.settrace(None)
components['debug_explanation_construction']=dict(inclusive_ms=1000*acc[0],line_events=acc[1],cases=7,method='Actual diagnostics blocks, line-attributed instrumented subset; includes tracing overhead, not release latency.')
top=[dict(file=Path(f).name,line=l,function=n,calls=v[1],own_seconds=v[2],cumulative_seconds=v[3]) for (f,l,n),v in sorted(stats.stats.items(),key=lambda kv:-kv[1][3])[:55]]
atomic_json(out/'performance_profile.json',dict(status='baseline_profile',identity=identity(),components=components,cprofile=top,uninstrumented_one_pass=describe([r['milliseconds'] for r in raw]),samples=raw,ocr_end_to_end_samples=e2e,scope='67 historical inputs, before engine changes. One-pass timing is diagnostic, not the mandatory seven-run gate. cProfile and traced categories overlap and cannot be summed. EX02/EX03 are included only as historical workload; no truth/threshold tuning.'))
print('PROFILE',json.dumps(top[:15]),flush=True)
