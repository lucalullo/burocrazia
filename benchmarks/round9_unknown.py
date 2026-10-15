"""Confirmed unknown observations, retrospective evidence separate from adequacy."""
import hashlib,math
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor,as_completed
from benchmarks.round8_common import ROOT,read,case_result,identity
from benchmarks.evaluate import summary
from benchmarks.truth_v2 import validate_unknown
from benchmarks.transactional_writer import CaseJournal,atomic_json
OUT=ROOT/'benchmarks/results/round9'

def interval(k,n):
    if not n:return None
    z=1.959963984540054;p=k/n;d=1+z*z/n;m=(p+z*z/(2*n))/d;half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return [max(0,m-half),min(1,m+half)]

def worker(c):
    raw=(ROOT/'benchmarks/cache'/(c['sha256']+'.body')).read_bytes();assert hashlib.sha256(raw).hexdigest()==c['sha256']
    cc=dict(id=c['case_id'],group=c['sha256'],category='confirmed_unknown_official',expected=dict(match_type='NO_MATCH'),label_status='confirmed',representation='official_original',provenance=dict(url=c['url'],source_key=c['source_key'],entity=c['entity'],document_type=c['document_type'],sha256=c['sha256'],split=c['split']))
    return case_result(cc,raw,'unknown.'+c['format'])

def main():
    manifest=validate_unknown(read('benchmarks/manifests/official_unknown_v1.json'));ident=identity();binding={k:v for k,v in ident.items() if k not in ['commit','executed_at']};binding['manifest_sha256']=hashlib.sha256((ROOT/'benchmarks/manifests/official_unknown_v1.json').read_bytes()).hexdigest()
    journal=CaseJournal(ROOT/('benchmarks/work/round9/unknown-'+binding['runtime_sha256'][:12]+'.sqlite'),identity=binding,expected_ids=[c['case_id'] for c in manifest['cases']]);pending=set(journal.pending())
    with ProcessPoolExecutor(max_workers=3) as pool:
        for f in as_completed([pool.submit(worker,c) for c in manifest['cases'] if c['case_id'] in pending]):journal.append(f.result())
    rows=journal.rows();journal.export(OUT/'unknown_observations.json',complete=True);false=sum(r['observed']['match_type']!='NO_MATCH' for r in rows);errors=sum(r['extraction_failed'] for r in rows)
    groups={}
    for name in ['source_key','entity','document_type']:
        by=defaultdict(list)
        for r in rows:by[r['provenance'][name]].append(r)
        groups['by_'+name]={k:dict(n=len(v),false_accepts=sum(r['observed']['match_type']!='NO_MATCH' for r in v),extraction_failed=sum(r['extraction_failed'] for r in v),summary=summary(v)) for k,v in by.items()}
    atomic_json(OUT/'unknown_v1.json',dict(identity=ident,status='measured_retrospective',cases=rows,summary=summary(rows),false_accepts=false,wrong_document=sum(r['observed']['match_type']=='DOCUMENT_MATCH' for r in rows),wrong_family=sum(r['observed']['match_type']=='FAMILY_MATCH' for r in rows),extraction_failed=errors,correct_rejection_count=sum(r['observed']['match_type']=='NO_MATCH' and not r['extraction_failed'] for r in rows),false_acceptance_rate=false/len(rows) if rows else None,false_acceptance_ci95=interval(false,len(rows)),adequacy_passed=len(rows)>=100 and len(manifest['sources'])>=8 and manifest['source_concentration']<=.25,independent=False,scope='Only confirmed truth included, but retrospective contaminated corpus; source/size adequacy separate. Extraction failures excluded from correct-recognition rejection count.',**groups))
    print('Confirmed unknown',len(rows),'false accept',false,'extraction failure',errors,flush=True)
if __name__=='__main__':main()
