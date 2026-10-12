"""Calibration uses only already seen identities/negatives; never evaluation v4."""
import argparse,hashlib,json,time
from concurrent.futures import ProcessPoolExecutor,as_completed
from collections import Counter
from pathlib import Path
from benchmarks.round8_common import ROOT,OUT,catalog,read,write,identity,case,raw_record
from benchmarks.round6_recognition import TRANSFORMS,transform_pdf
from benchmarks.evaluate import summary
from scripts.benchmark import evaluate_case
from src.extract import extract_document
from src.fingerprint_pages import prepare,RequestPages
from src.fingerprint_v3 import read_bundle
from src.models import CatalogRecognitionResult
from src.recognize import recognize_catalog,recognize_document_family
from src.fingerprint_decision_v4 import DEFAULT,VERSION,PATH

def grid():
    return [dict(rules_version=VERSION,thresholds=dict(DEFAULT,ocr=ocr),settings=dict(char_ngram=n,aggregation=agg,containment=containment)) for n in ['3','4','5'] for agg,containment in [('max',False),('max',True),('top2',True)] for ocr in [.80,.85]]

def calibration_ids():
    p=read('benchmarks/results/round6/robustness_v2_plan.json');ids=set(p['calibration_identities']+p['evaluation_identities'])
    ids.update(read('benchmarks/results/round7/robustness_v3_evaluation_plan.json')['evaluation_identities'])
    for n in ['development_regression','release_locked_v1','release_locked_v2']:
        ids.update(c['expected']['document_id'] for c in read('benchmarks/corpora/'+n+'.json')['cases'] if c['expected'].get('document_id'))
    return sorted(ids)

def tasks():
    jobs=[];r6=read('benchmarks/results/round6/robustness_v2_plan.json');r7=read('benchmarks/results/round7/robustness_v3.json');records=read_bundle()['records']
    keep={'digital_exact','raster_150','jpeg_60','contrast_minus20','crop_5pct','first_page_only','rotation_90','rotation_270'}
    for did,sha in r6['resources'].items():
        r=next(r for r in records if r['document_id']==int(did) and r['canonical_file_sha256']==sha)
        for name,params in TRANSFORMS:
            if name in keep:jobs.append(dict(id=f'DEV6-{did}-{name}',record=r,name=name,params=params))
    for old in r7['cases']:
        if old.get('generation_failed') or old['representation'].startswith('filled_'):continue
        p=old['provenance'];r=next(r for r in records if r['document_id']==p['document_id'] and r['canonical_file_sha256']==p['canonical_sha256'])
        jobs.append(dict(id='DEV7-'+old['id'],record=r,name=old['representation'],params=p['transform'],historical_sha256=old['input_sha256']))
    for f in read(OUT+'filled_generation_development.json')['cases']:
        if f['generated']:
            r=next(r for r in records if r['document_id']==f['document_id'] and r['canonical_file_sha256']==f['canonical_sha256'])
            jobs.append(dict(id=f['case_id'],record=r,name='valid_filled',path='benchmarks/work/round8-development-filled/'+f['case_id']+'.pdf',params={},historical_sha256=f['sha256']))
    for n in ['hard_negatives_v1','hard_negatives_v2']:
        jobs.extend(dict(id='NEG-'+c['id'],text_case=c,name='hard_negative',params={}) for c in read('benchmarks/corpora/'+n+'.json')['cases'])
    seen=set()
    for n in ['official_documents_v2','official_holdout_v1','official_holdout_v2']:
        for c in read('benchmarks/manifests/'+n+'.json')['cases']:
            if c.get('expected_match_type')!='NO_MATCH' or c['sha256'] in seen:continue
            seen.add(c['sha256']);jobs.append(dict(id='UNKNOWN-'+c['id'],unknown=c,name='unknown_historical',params={}))
    return jobs

def worker(job):
    import src.fingerprint_decision_v4 as decision
    docs,families=catalog();error=None;started=time.perf_counter()
    if 'text_case' in job:
        cc=dict(job['text_case'],label_status='historical_only');text=cc['text'];request=RequestPages((text,));sha=None
    else:
        if 'unknown' in job:
            u=job['unknown'];raw=(ROOT/'benchmarks/cache'/(u['sha256']+'.body')).read_bytes();assert hashlib.sha256(raw).hexdigest()==u['sha256'];filename='unknown.'+u['format']
            cc=dict(id=job['id'],group=u['sha256'],category='unknown_official',expected=dict(match_type='NO_MATCH'),label_status='historical_only')
        else:
            r=job['record'];cc=case(r,job['name'],job['params']);cc['id']=job['id'];filename='input'+('.pdf' if r['mime_type']=='application/pdf' else '.docx')
            if job.get('path'):raw=(ROOT/job['path']).read_bytes()
            elif job['name']=='digital_exact':raw=raw_record(r)
            else:raw,ext=transform_pdf(raw_record(r),job['params']);filename='input'+ext
        sha=hashlib.sha256(raw).hexdigest()
        try:ex=extract_document(raw,filename);text=ex.text;request=prepare(raw,filename,ex)
        except (ValueError,OSError,RuntimeError) as exc:text='';request=RequestPages(('',));error=type(exc).__name__+': '+str(exc)
    options=[];original=decision.profile
    try:
        for configuration in grid():
            decision.profile=lambda:configuration;diagnostics={'expected_id':cc['expected'].get('document_id')}
            result=CatalogRecognitionResult('NO_MATCH',0,0,reason='Extraction failed') if error else recognize_catalog(text,docs,families,file_sha256=sha,page_context=request,fingerprint_diagnostics=diagnostics)
            diagnostics.pop('candidate_ids',None)
            if diagnostics.get('candidates'):diagnostics['candidates']=diagnostics['candidates'][:3]
            row=evaluate_case(cc,result);row.update(label_status=cc['label_status'],representation=job['name'],input_sha256=sha,extraction_failed=error is not None,extraction_error=error,decision_diagnostics=diagnostics,signals=list(result.document_signals))
            options.append(row)
    finally:decision.profile=original
    return dict(id=job['id'],known='record' in job,grid_results=options,seconds=time.perf_counter()-started,historical_sha_match=None if not job.get('historical_sha256') else sha==job['historical_sha256'])

def main():
    if (ROOT/OUT/'freeze.json').exists():raise ValueError('Calibration cannot change after freeze')
    jobs=tasks();rows=[]
    with ProcessPoolExecutor(max_workers=3) as pool:
        fs={pool.submit(worker,j):j['id'] for j in jobs}
        for f in as_completed(fs):
            rows.append(f.result())
            if len(rows)%25==0:print('Development calibration',len(rows),'/',len(jobs),flush=True);write(OUT+'calibration_checkpoint.json',dict(completed=len(rows),planned=len(jobs)))
    rows.sort(key=lambda r:r['id']);options=[]
    for i,cfg in enumerate(grid()):
        actual=[r['grid_results'][i] for r in rows];negative=[r['grid_results'][i] for r in rows if not r['known']]
        fp=sum(r['observed']['match_type']!='NO_MATCH' for r in negative);wrong=sum(r['observed']['match_type']=='DOCUMENT_MATCH' and not r['document_correct'] for r in actual if r['expected']['match_type']=='DOCUMENT_MATCH')
        options.append(dict(index=i,configuration=cfg,false_accepts=fp,wrong_known=wrong,exact=sum(r['document_correct'] for r in actual),known=sum(r['known'] for r in rows)))
    safe=[o for o in options if o['false_accepts']==0 and o['wrong_known']==0]
    compact_keys=['id','group','category','expected','observed','correct','document_correct','family_correct','entity_error','version_error','entity_labelled','version_labelled','matching_ms','label_status','input_sha256','extraction_failed']
    raw_rows=[dict(id=r['id'],known=r['known'],grid_results=[{k:v for k,v in row.items() if k in compact_keys} for row in r['grid_results']]) for r in rows]
    evidence=[dict(id=r['id'],configuration=i,case=row) for r in rows for i,row in enumerate(r['grid_results']) if (not r['known'] and row['observed']['match_type']!='NO_MATCH') or (r['known'] and row['observed']['match_type']=='DOCUMENT_MATCH' and not row['document_correct'])]
    write(OUT+'calibration_grid_observations.json',dict(cases=raw_rows,wrong_or_false_accept_evidence=evidence,grid=options,scope='All 18 development configuration outcomes, numeric/labels only; no extracted text.'))
    if not safe:
        write(OUT+'calibration_failed_attempt.json',dict(grid=options));raise ValueError('No safe calibration configuration; fix development implementation before any freeze')
    chosen=max(safe,key=lambda o:(o['exact'],-o['index']));cfg=chosen['configuration']
    write('data/recognition_profiles/fingerprint_decision_v4.json',dict(**cfg,scope='Only contaminated Round6/7 known representations, repaired historical fills, and historical development negatives.'))
    import src.fingerprint_decision_v4 as decision
    decision.profile.cache_clear()
    selected=[r['grid_results'][chosen['index']] for r in rows]
    write(OUT+'calibration_observations_v4.json',dict(cases=selected,summary=summary(selected),historical_sha_mismatches=[r['id'] for r in rows if r['historical_sha_match'] is False],scope='Development only; old invalid filled samples excluded, all old identities still excluded from evaluation.'))
    fneg=[c for c in read('benchmarks/corpora/family_release_v3.json')['cases'] if c['expected']['match_type']=='NO_MATCH']
    docs,families=catalog();fail=[]
    for c in fneg:
        result=recognize_document_family(c['text'],families,known_entities=[d.ente for d in docs])
        if result.recognized:fail.append(c['id'])
    assert not fail,'Historical isolated family safety failed'
    ident=identity();write(OUT+'calibration_v4.json',dict(**ident,profile_sha256=hashlib.sha256(PATH.read_bytes()).hexdigest(),identity_ids=calibration_ids(),representation_types=dict(Counter(r['grid_results'][0]['representation'] for r in rows)),thresholds=cfg['thresholds'],channel_weights=dict(content=.5,chars=.35,anchors=.15,visual='independent conditional veto/support'),page_aggregation=cfg['settings']['aggregation'],containment=cfg['settings']['containment'],char_ngram=cfg['settings']['char_ngram'],char_idf='32768 deterministic buckets, public canonical pages only',visual_settings='4 rotations x (whole,6% center crop,2x2 tiles), 64-bit dHash; lazy top25',decision_tiers=['A_exact_sha','B_digital_char_identity','B_ocr_char_layout','C_unique_fields_compatible_identity','D_safe_fallback_or_NO'],grid=options,selected=chosen,metrics=summary(selected),negative_controls=len(rows)-chosen['known'],isolated_family_negative_controls=len(fneg),scope='Pre-freeze development calibration, zero false accepts and zero wrong known identity first. Evaluation v4 not selected or opened.'))
    print('Calibration selected',chosen,flush=True)

if __name__=='__main__':main()
