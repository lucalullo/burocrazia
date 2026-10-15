"""Single selected development policy replay; no v5 evaluation selection/tuning."""
import hashlib,json,time
from concurrent.futures import ProcessPoolExecutor,as_completed
from collections import Counter
from benchmarks import round8_calibrate as previous
from benchmarks.round8_common import ROOT,catalog,read,identity,case,raw_record,case_result
from benchmarks.round6_recognition import transform_pdf
from benchmarks.evaluate import summary
from benchmarks.transactional_writer import CaseJournal,atomic_json,encoded
from src.fingerprint_decision_v5 import profile,revision
from src.fingerprint_v3 import read_bundle
from src.fingerprint_pages import prepare,RequestPages
from src.extract import extract_document
from src.models import CatalogRecognitionResult
from src.recognize import recognize_catalog
from scripts.benchmark import evaluate_case
OUT=ROOT/'benchmarks/results/round9'

def tasks():
    jobs=[j for j in previous.tasks() if 'unknown' not in j]
    records={r['document_id']:r for r in read_bundle()['records'] if r['status']=='active'}
    old_ids={r['id'] for r in read('benchmarks/results/round8/robustness_v4.json')['cases']}
    for item in read('benchmarks/results/round8/evaluation_prepared.json')['representations']:
        cc=item['case']
        if cc['id'] in old_ids:jobs.append(dict(id='DEV8-'+cc['id'],record=records[cc['expected']['document_id']],name=cc['representation'],params=cc['provenance']['transform'],path=item['path'],filename=item['path'].rsplit('/',1)[-1],historical_sha256=item['sha256']))
    for c in read('benchmarks/manifests/official_unknown_v1.json')['cases']:
        if c['split']=='development':jobs.append(dict(id='UNKNOWN-DEV-'+c['case_id'],unknown=c,name='confirmed_unknown_development',params={}))
    for j in jobs:
        if 'record' in j:j['record']={k:j['record'][k] for k in ['document_id','source_id','canonical_file_sha256','mime_type','url']}
    # H000..H029 occur in both immutable negative corpora; namespace by the
    # deterministic corpus occurrence rather than silently dropping duplicates.
    seen=Counter()
    for j in jobs:
        old=j['id'];seen[old]+=1
        if 'text_case' in j:j['id']=old+'-corpus'+str(seen[old])
    return jobs

def worker(job):
    docs,families=catalog();error=None;sha=None
    if 'text_case' in job:
        cc=dict(job['text_case'],label_status='historical_only');text=cc['text'];request=RequestPages((text,))
    else:
        if 'unknown' in job:
            u=job['unknown'];sha=u['sha256'];raw=(ROOT/'benchmarks/cache'/(sha+'.body')).read_bytes();filename='unknown.'+u['format']
            cc=dict(id=job['id'],group=sha,category='unknown_official',expected=dict(match_type='NO_MATCH'),label_status='confirmed')
        else:
            r=job['record'];cc=case(r,job['name'],job['params']);filename='input'+('.pdf' if r['mime_type']=='application/pdf' else '.docx')
            if job.get('path'):raw=(ROOT/job['path']).read_bytes();filename=job.get('filename',filename)
            elif job['name']=='digital_exact':raw=raw_record(r)
            else:raw,ext=transform_pdf(raw_record(r),job['params']);filename='input'+ext
            sha=hashlib.sha256(raw).hexdigest()
            if job.get('historical_sha256'):assert sha==job['historical_sha256'],'Development input changed'
        assert hashlib.sha256(raw).hexdigest()==sha
        try:ex=extract_document(raw,filename);text=ex.text;request=prepare(raw,filename,ex)
        except (ValueError,OSError,RuntimeError) as exc:error=type(exc).__name__+': '+str(exc);text='';request=RequestPages(('',))
    cc['id']=job['id'];diag={'expected_id':cc['expected'].get('document_id')};start=time.perf_counter()
    result=CatalogRecognitionResult('NO_MATCH',0,0,reason='Extraction failed') if error else recognize_catalog(text,docs,families,file_sha256=sha,page_context=request,fingerprint_diagnostics=diag)
    row=evaluate_case(cc,result,(time.perf_counter()-start)*1000);row.update(label_status=cc['label_status'],representation=job['name'],input_sha256=sha,extraction_error=error,extraction_failed=bool(error),signals=list(result.document_signals),decision_diagnostics={k:v for k,v in diag.items() if k not in ['candidate_ids','candidates']},top_candidates=diag.get('candidates',[])[:3])
    return row

def main():
    jobs=tasks();ident=identity();ident['profile_sha256']=revision()
    ident={k:v for k,v in ident.items() if k!='executed_at'}
    ident['jobs_sha256']=hashlib.sha256(encoded(jobs)).hexdigest()
    # Commit time is provenance only; resume binds byte identities, not HEAD.
    binding={k:v for k,v in ident.items() if k!='commit'}
    journal=CaseJournal(ROOT/('benchmarks/work/round9/calibration-'+binding['runtime_sha256'][:12]+'.sqlite'),identity=binding,expected_ids=[j['id'] for j in jobs]);pending=set(journal.pending())
    with ProcessPoolExecutor(max_workers=3) as pool:
        futures=[pool.submit(worker,j) for j in jobs if j['id'] in pending]
        for f in as_completed(futures):
            journal.append(f.result())
            if len(journal.rows())%25==0:print('Round9 development',len(journal.rows()),'/',len(jobs),flush=True)
    journal.export(OUT/'calibration_observations_v5.json',complete=True);rows=journal.rows();known=[r for r in rows if r['expected']['match_type']=='DOCUMENT_MATCH'];negative=[r for r in rows if r['expected']['match_type']=='NO_MATCH']
    atomic_json(OUT/'calibration_v5.json',dict(identity=ident,status='development_replay_complete',identity_ids=sorted(set(previous.calibration_ids())|{j['record']['document_id'] for j in jobs if 'record' in j}),parameters=profile(),channel_weights=dict(content=.5,chars=.35,anchors=.15),top_k=25,tiers=['A_exact_sha','B_digital_char_identity','B_ocr_char_layout','C_unique_fields_compatible_identity','D_refuse'],safety_constraints=['explicit entity/version conflicts veto','missing decimal revision cannot be inferred from catalog uniqueness','shared SHA not unique identity','operational binding required','metadata content contradiction veto'],metrics=summary(rows),known_metrics=summary(known),negative_metrics=summary(negative),false_accepts=sum(r['observed']['match_type']!='NO_MATCH' for r in negative),wrong_known=sum(r['observed']['match_type']=='DOCUMENT_MATCH' and not r['document_correct'] for r in known),representation_types=dict(Counter(r['representation'] for r in rows)),profile_sha256=revision(),source='R6/R7 scans, R8 valid development fills, saved R8 partial representations now development, historical hard negatives, confirmed unknown development subset.',tuning='No threshold search or v5 evaluation access. R8 numerical thresholds retained; general revision veto repaired. Development outcomes cannot certify independent robustness.'))
    print('Calibration complete',len(rows),'exact',sum(r['document_correct'] for r in known),'/',len(known),flush=True)
if __name__=='__main__':main()
