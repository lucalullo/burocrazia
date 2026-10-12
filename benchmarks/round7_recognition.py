"""Offline development calibration and one-shot fresh identity evaluation."""
from __future__ import annotations
import argparse,hashlib,json,os,subprocess,time
from collections import Counter,defaultdict
from concurrent.futures import ProcessPoolExecutor,as_completed
from dataclasses import replace
from datetime import UTC,datetime
from pathlib import Path
from benchmarks.round3_audit import ROOT,catalog,read,write
from benchmarks.round4_common import runtime_hash
from benchmarks.evaluate import code_hash,summary
from benchmarks.round6_recognition import (active_records,raw_record,case_result,TRANSFORMS,transform_pdf,cached_texts)
from benchmarks.round7_fill import fill_acroform
from src.fingerprint_v2 import public_index,features,revision,read_bundle
from src.fingerprint_decision_v3 import profile,tier,DEFAULT,PATH,VERSION,entity_evidence
from src.fingerprint_match_v2 import safety_reason
from src.title_evidence import exact_code_candidates
from src.extract import extract_document
from src.fingerprint_visual import visual_for_bytes
from src.models import CatalogRecognitionResult
from src.recognize import recognize_catalog,normalize_text,DISTINCT_ENTITY_NAMES
from scripts.benchmark import evaluate_case

OUT='benchmarks/results/round7/';SEED=2026101207

def identity():return dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),runtime_sha256=runtime_hash(),code_sha256=code_hash(),fingerprint_sha256=revision(),seed=SEED,executed_at=datetime.now(UTC).isoformat())

def case(r,name,params=None):
    docs,_=catalog();d=next(d for d in docs if d.id==r['document_id'])
    from benchmarks.round5_recognition import family_label
    return dict(id=f'R7-{d.id}-{name}',group=f'document:{d.id}',category='known_official',
        expected=dict(match_type='DOCUMENT_MATCH',document_id=d.id,family_id=family_label(d),entity=d.ente,version=d.versione),representation=name,
        provenance=dict(document_id=d.id,canonical_sha256=r['canonical_file_sha256'],canonical_url=r['url'],canonical_mime_type=r['mime_type'],source_id=r['source_id'],seed=SEED,transform=params or {}))

def save(name,rows,**extra):
    value=dict(schema_version=3,identity=identity(),summary=summary(rows),cases=rows,**extra)
    value['counts']=dict(exact=sum(r['document_correct'] for r in rows),family=sum(r['family_correct'] for r in rows),reject=sum(r['observed']['match_type']=='NO_MATCH' for r in rows),wrong=sum(r['observed']['match_type']!='NO_MATCH' and not (r['document_correct'] or r['family_correct']) for r in rows),extraction_failed=sum(r.get('extraction_failed',False) for r in rows))
    value['candidate_recall_at_k']={str(k):dict(numerator=sum(r.get('candidate_recall_at_k',{}).get(str(k),False) for r in rows),denominator=len(rows)) for k in [1,5,10,25]}
    value['by_transformation']={name:summary([r for r in rows if r.get('representation')==name]) for name in sorted({r.get('representation','') for r in rows})}
    value['by_source']={name:summary([r for r in rows if str(r.get('provenance',{}).get('source_id','unlabelled'))==name]) for name in sorted({str(r.get('provenance',{}).get('source_id','unlabelled')) for r in rows})}
    value['by_format']={name:summary([r for r in rows if r.get('provenance',{}).get('canonical_mime_type','unlabelled')==name]) for name in sorted({r.get('provenance',{}).get('canonical_mime_type','unlabelled') for r in rows})}
    write(OUT+name+'.json',value);return value

def calibration_ids():
    p=read('benchmarks/results/round6/robustness_v2_plan.json');ids=set(p['calibration_identities']+p['evaluation_identities'])
    for n in ['development_regression','release_locked_v1','release_locked_v2']:
        ids.update(c['expected']['document_id'] for c in read('benchmarks/corpora/'+n+'.json')['cases'] if c['expected'].get('document_id'))
    return sorted(ids)

def grid():
    return [dict(DEFAULT,text_visual=text,visual=vis,char_floor=char) for text in [.55,.65] for vis in [.94,.97] for char in [.10,.15]]

def simulate(text,visual,sha,expected):
    """Same tiers, safety, margin and actual metadata fallback as the runtime."""
    docs,families=catalog();index=public_index();by={d.id:d for d in docs};q=features(text);rows=index.similarities(q,visual)
    entities=entity_evidence(text,[d.ente for d in docs]+list(DISTINCT_ENTITY_NAMES));codes=set(exact_code_candidates(text,docs))
    safety={}
    def safe(r):
        did=r['document_id']
        if did not in safety:safety[did]=safety_reason(text,by[did],docs,entities=entities)
        return safety[did] is None
    selected=[]
    for t in grid():
        eligible=[r for r in rows if tier(r,t,code_anchor=r['document_id'] in codes) and safe(r)]
        if eligible:
            best=eligible[0];runner=max((r['score'] for r in rows if r['document_id']!=best['document_id'] and r['score']>=best['score']-t['margin'] and safe(r)),default=0)
            selected.append(best['document_id'] if best['score']-runner>=t['margin'] else None)
        else:selected.append(None)
    actual=recognize_catalog(text,docs,families,file_sha256=sha,visual_fingerprint=visual)
    # Exact canonical bytes are independent of fusion thresholds.
    if 'official_file_sha256_exact' in actual.document_signals:selected=[actual.document.id]*len(selected)
    fallback=None
    if any(did is None for did in selected):
        import src.fingerprint_match_v2 as matcher
        original=matcher.match
        try:
            matcher.match=lambda *args,**kwargs:None
            fallback=recognize_catalog(text,docs,families)
        finally:matcher.match=original
    outcomes=[]
    import src.fingerprint_decision_v3 as decision
    original_profile=decision.profile
    expected_case=dict(id='grid',group='development',category='known_official' if expected is not None else 'negative',expected=dict(match_type='DOCUMENT_MATCH',document_id=expected,entity=by[expected].ente,version=by[expected].versione) if expected is not None else dict(match_type='NO_MATCH'))
    for i,did in enumerate(selected):
        kind='DOCUMENT_MATCH' if did is not None else fallback.match_type
        observed=did if did is not None else fallback.document.id if fallback.document else None
        correct=(kind=='NO_MATCH') if expected is None else kind=='DOCUMENT_MATCH' and observed==expected
        try:
            decision.profile=lambda:grid()[i]
            actual_grid=recognize_catalog(text,docs,families,file_sha256=sha,visual_fingerprint=visual)
        finally:decision.profile=original_profile
        assert (kind,observed)==(actual_grid.match_type,actual_grid.document.id if actual_grid.document else None),'Grid/runtime mismatch'
        outcomes.append(dict(correct=correct,false_accept=expected is None and kind!='NO_MATCH',wrong=expected is not None and kind=='DOCUMENT_MATCH' and observed!=expected,observed=observed,match_type=kind,observed_case=evaluate_case(expected_case,actual_grid)))
    return outcomes,rows[:25],actual

def calibration_worker(did,verify=False):
    p=read('benchmarks/results/round6/robustness_v2_plan.json');r=next(r for r in read_bundle()['records'] if r['document_id']==did and r['canonical_file_sha256']==p['resources'][str(did)])
    docs,families=catalog();rows=[]
    historical={r['input_sha256'] for name in ['calibration_observations','robustness_v2'] for r in read('benchmarks/results/round6/'+name+'.json')['cases'] if r['provenance']['document_id']==did}
    for name,params in TRANSFORMS:
        paths=list((ROOT/'benchmarks/work/round6-representations').glob(f'{did}-{name}.*'))
        if paths:path=paths[0];raw=path.read_bytes();filename=path.name
        else:
            raw,ext=(raw_record(r),'.pdf') if name=='digital_exact' else transform_pdf(raw_record(r),params);filename='variant'+ext
        ex=extract_document(raw,filename);visual=visual_for_bytes(raw,filename);sha=hashlib.sha256(raw).hexdigest()
        assert sha in historical,'Round6 development representation bytes changed'
        if verify:
            actual=recognize_catalog(ex.text,docs,families,file_sha256=sha,visual_fingerprint=visual);options=[];scores=[]
        else:options,scores,actual=simulate(ex.text,visual,sha,did)
        row=evaluate_case(case(r,name,params),actual);row.update(grid_results=options,retrieval_scores=scores,input_sha256=sha,representation=name,used_ocr=ex.used_ocr,scope='Round6 now development')
        rows.append(row)
    return rows

def calibration_negatives(verify=False):
    rows=[];docs,families=catalog()
    for name in ['hard_negatives_v1','hard_negatives_v2','family_release_v3']:
        for c in read('benchmarks/corpora/'+name+'.json')['cases']:
            if c['expected']['match_type']!='NO_MATCH':continue
            if name=='family_release_v3':
                from src.recognize import recognize_document_family
                result=recognize_document_family(c['text'],families,known_entities=[d.ente for d in docs])
                actual=CatalogRecognitionResult('FAMILY_MATCH' if result.recognized else 'NO_MATCH',0,result.confidence,family=result.family)
                observation=evaluate_case(c,actual)
                options=[dict(correct=observation['correct'],false_accept=not observation['correct'],wrong=False,observed=None,match_type=actual.match_type,observed_case=observation) for _ in grid()];scores=[]
            elif verify:actual=recognize_catalog(c['text'],docs,families);options=[];scores=[]
            else:options,scores,actual=simulate(c['text'],(),None,None)
            row=evaluate_case(c,actual);row.update(grid_results=options,retrieval_scores=scores,scope='isolated family fallback, unchanged corpus contract' if name=='family_release_v3' else 'full pipeline hard negative');rows.append(row)
    seen=set()
    for name in ['official_documents_v2','official_holdout_v1','official_holdout_v2']:
        manifest,values=cached_texts(name)
        for c in manifest['cases']:
            if c.get('expected_match_type')!='NO_MATCH' or c['sha256'] in seen:continue
            seen.add(c['sha256']);raw=(ROOT/'benchmarks/cache'/(c['sha256']+'.body')).read_bytes();ext=c['format']
            try:text=values[c['id']].get('text','');visual=visual_for_bytes(raw,'negative.'+ext)
            except (ValueError,OSError,RuntimeError):text='';visual=()
            if verify:actual=recognize_catalog(text,docs,families,file_sha256=c['sha256'],visual_fingerprint=visual);options=[];scores=[]
            else:options,scores,actual=simulate(text,visual,c['sha256'],None)
            cc=dict(id=c['id'],group=c['sha256'],category='unknown_official',expected=dict(match_type='NO_MATCH'))
            row=evaluate_case(cc,actual);row.update(grid_results=options,retrieval_scores=scores,scope='Historical official extraction from ignored development cache; canonical bytes SHA checked; final unknown run re-extracts.');rows.append(row)
    return rows

def calibrate():
    if (ROOT/OUT/'decision_calibration.json').exists():raise ValueError('Calibration already frozen; use a new round')
    p=read('benchmarks/results/round6/robustness_v2_plan.json');ids=p['calibration_identities']+p['evaluation_identities'];rows=[]
    with ProcessPoolExecutor(max_workers=3) as pool:
        futures={pool.submit(calibration_worker,did):did for did in ids}
        for f in as_completed(futures):
            rows.extend(f.result());write(OUT+'calibration_checkpoint.json',dict(cases=rows));print('Calibration development',futures[f],len(rows),flush=True)
    rows.sort(key=lambda r:r['id']);negatives=calibration_negatives();options=[]
    for i,t in enumerate(grid()):
        options.append(dict(thresholds=t,exact=sum(r['grid_results'][i]['correct'] for r in rows),total=len(rows),wrong=sum(r['grid_results'][i]['wrong'] for r in rows),false_accepts=sum(r['grid_results'][i]['false_accept'] for r in negatives),negative_cases=len(negatives)))
    write(OUT+'calibration_development_observations.json',dict(cases=rows,negative_cases=negatives,grid=options))
    safe=[o for o in options if o['wrong']==0 and o['false_accepts']==0]
    if not safe:raise ValueError('No policy satisfies zero calibration false accepts; audit before freezing')
    chosen=max(safe,key=lambda o:(o['exact'],o['thresholds']['text_visual'],o['thresholds']['visual'],o['thresholds']['char_floor']))
    p=dict(schema_version=3,rules_version=VERSION,thresholds=chosen['thresholds'],weights=dict(text=.5,chars=.25,anchors=.15,visual=.1),objective='Zero development hard-negative false accepts, then maximum exact recall; full safety and metadata fallback included.',calibration_identities=calibration_ids(),frozen_at=datetime.now(UTC).isoformat())
    PATH.write_bytes((json.dumps(p,indent=2)+'\n').encode());profile.cache_clear()
    selected_index=options.index(chosen)
    def observed(r):
        value={k:v for k,v in r.items() if k not in ('grid_results','retrieval_scores')}
        value.update(r['grid_results'][selected_index]['observed_case']);value['id']=r['id'];return value
    verified=[observed(r) for r in rows];verified_neg=[observed(r) for r in negatives]
    assert sum(r['correct'] for r in verified)==chosen['exact'],'Grid/runtime recall mismatch'
    assert all(r['correct'] for r in verified_neg),'Grid/runtime negative mismatch'
    save('calibration_runtime_verified',verified,negative_cases=verified_neg,scope='All grid outcomes checked against actual runtime during each development request; selected outcome retained without repeating OCR. Family negatives retain isolated-family corpus contract. Official negatives use historical extraction; final unknown run re-extracts.')
    write(OUT+'calibration_development_observations.json',dict(cases=rows,negative_cases=negatives,grid=options))
    write(OUT+'decision_calibration.json',dict(**p,commit=identity()['commit'],runtime_sha256=runtime_hash(),fingerprint_sha256=revision(),profile_sha256=hashlib.sha256(PATH.read_bytes()).hexdigest(),results=chosen,grid=options,scope='Round6 representations and historical development negatives; never fresh evaluation identities or new evaluation unknowns. Simulation uses runtime tier/safety/margin and actual metadata fallback.'))
    print('Decision calibration frozen',chosen,flush=True)

def freeze():
    cal=read(OUT+'decision_calibration.json');equivalence=None
    if cal['runtime_sha256']!=runtime_hash():
        proof=read(OUT+'decision_calibration_reference_fix.json')
        assert proof['runtime_sha256']==runtime_hash() and proof['original_runtime_sha256']==cal['runtime_sha256']
        assert proof['profile_sha256']==hashlib.sha256(PATH.read_bytes()).hexdigest()==cal['profile_sha256']
        assert proof['fingerprint_sha256']==revision()==cal['fingerprint_sha256']
        assert proof['original_calibration_sha256']==hashlib.sha256((ROOT/OUT/'decision_calibration.json').read_bytes()).hexdigest()
        assert proof['production_branch_changed'] is False and proof['full_tests']['failed']==0
        equivalence=hashlib.sha256((ROOT/OUT/'decision_calibration_reference_fix.json').read_bytes()).hexdigest()
    write(OUT+'freeze.json',dict(**identity(),profile_sha256=hashlib.sha256(PATH.read_bytes()).hexdigest(),calibration_sha256=hashlib.sha256((ROOT/OUT/'decision_calibration.json').read_bytes()).hexdigest(),calibration_reference_fix_sha256=equivalence))
    print('Evaluation code freeze recorded')

def checked():
    f=read(OUT+'freeze.json')
    assert f['runtime_sha256']==runtime_hash() and f['code_sha256']==code_hash() and f['fingerprint_sha256']==revision(),'Frozen bytes changed'
    assert f['calibration_sha256']==hashlib.sha256((ROOT/OUT/'decision_calibration.json').read_bytes()).hexdigest()
    if f.get('calibration_reference_fix_sha256'):assert f['calibration_reference_fix_sha256']==hashlib.sha256((ROOT/OUT/'decision_calibration_reference_fix.json').read_bytes()).hexdigest()
    return f

def new_plan():
    f=checked();docs,_=catalog();by={d.id:d for d in docs};excluded=set(calibration_ids());all_records=active_records()
    cal_records=[r for r in read_bundle()['records'] if r['document_id'] in excluded]
    shas={r['canonical_file_sha256'] for r in cal_records};urls={r['url'] for r in cal_records}|{r['final_url'] for r in cal_records}
    # Historical official unknowns also participated in development safety
    # calibration. Their bytes/URLs cannot reappear in the fresh known set.
    for name in ['official_documents_v2','official_holdout_v1','official_holdout_v2']:
        for c in read('benchmarks/manifests/'+name+'.json')['cases']:
            if c.get('expected_match_type')=='NO_MATCH':
                shas.add(c['sha256']);urls.add(c['url'])
                if c.get('receipt',{}).get('final_url'):urls.add(c['receipt']['final_url'])
    key=lambda d:(normalize_text(d.titolo_ufficiale),normalize_text(d.codice or ''),d.versione)
    signatures={key(by[i]) for i in excluded if i in by};cal_docs=[by[i] for i in excluded if i in by];candidates={}
    from rapidfuzz.fuzz import ratio
    def near_calibration(d):
        title,code,version=key(d)
        return any((code and code==key(c)[1] and d.ente==c.ente) or
            (version==c.versione and (code==key(c)[1] or not code or not key(c)[1]) and ratio(title,key(c)[0])>=92)
            for c in cal_docs)
    for r in all_records:
        did=r['document_id']
        if did in excluded or r['canonical_file_sha256'] in shas or r['url'] in urls or r['final_url'] in urls or key(by[did]) in signatures or near_calibration(by[did]):continue
        if did not in candidates:candidates[did]=r
    order=lambda r:hashlib.sha256(f'{SEED}:{r["document_id"]}'.encode()).hexdigest()
    pdfs=sorted([r for r in candidates.values() if r['mime_type']=='application/pdf'],key=order);selected=[];widgets=[]
    import fitz
    from pypdf import PdfReader
    from io import BytesIO
    for r in pdfs:
        raw=raw_record(r);fields=PdfReader(BytesIO(raw)).get_fields() or {}
        with fitz.open(stream=raw,filetype='pdf') as doc:
            all_widgets=[w for page in doc for w in page.widgets() or ()]
            if all_widgets and all(w.field_name in fields for w in all_widgets) and any(w.field_type in (fitz.PDF_WIDGET_TYPE_TEXT,fitz.PDF_WIDGET_TYPE_CHECKBOX) and not w.field_flags&1 for w in all_widgets):widgets.append(r)
        if len(widgets)>=10:break
    selected.extend(widgets)
    for source in sorted({r['source_id'] for r in pdfs}):
        for r in pdfs:
            if r['source_id']==source and r not in selected:selected.append(r);break
    for r in pdfs:
        if r not in selected:selected.append(r)
        if len(selected)>=40:break
    other=sorted([r for r in candidates.values() if r['mime_type']!='application/pdf'],key=order)[:2]
    selected=selected[:40]+other
    plan=dict(seed=SEED,freeze_commit=f['commit'],selection='After code freeze: first ten deterministic AcroForm templates with canonical field tree, no orphan widgets and editable text/checkbox, one PDF/source then hashed order to 40 PDFs, plus two DOCX where available. No recognition-result-based selection.',calibration_identities=sorted(excluded),evaluation_identities=[r['document_id'] for r in selected],filled_identities=[r['document_id'] for r in widgets],resources={str(r['document_id']):r['canonical_file_sha256'] for r in selected},source_counts=dict(Counter(str(r['source_id']) for r in selected)))
    leakage=dict(identity_overlap=sorted(excluded&set(plan['evaluation_identities'])),resource_sha_overlap=sorted(shas&{r['canonical_file_sha256'] for r in selected}),canonical_url_overlap=sorted(urls&{u for r in selected for u in [r['url'],r['final_url']]}),title_code_version_overlap=[r['document_id'] for r in selected if key(by[r['document_id']]) in signatures or near_calibration(by[r['document_id']])],near_duplicate_rule='Exclude same nonempty code+issuer at any version, or title ratio >=92 with compatible code and equal version; normalized exact triple also excluded.',transformation_provenance='Every case records original resource SHA, identity, fixed seed and transform parameters; runtime hashes checked before and after.',prohibited_leakage=0)
    assert not any(leakage[k] for k in ['identity_overlap','resource_sha_overlap','canonical_url_overlap','title_code_version_overlap'])
    write(OUT+'robustness_v3_evaluation_plan.json',plan);write(OUT+'evaluation_v3_leakage.json',leakage);return plan

def evaluation_worker(did,index):
    p=read(OUT+'robustness_v3_evaluation_plan.json');r=next(r for r in active_records() if r['document_id']==did and r['canonical_file_sha256']==p['resources'][str(did)]);raw=raw_record(r);docs,families=catalog();rows=[]
    ext='.pdf' if r['mime_type']=='application/pdf' else '.docx'
    variants=[('digital_exact',{})]
    if ext=='.pdf':
        scans=[x for x in TRANSFORMS if x[0] not in ['digital_exact','first_page_only']]
        variants += [scans[(7*index+j)%len(scans)] for j in range(7)]
    for name,params in variants:
        cc=case(r,name,params)
        try:
            value,suffix=(raw,ext) if name=='digital_exact' else transform_pdf(raw,params)
            row=case_result(cc,value,'variant'+suffix,docs,families,diagnostics=True)
        except (ValueError,OSError,RuntimeError) as exc:
            row=evaluate_case(cc,CatalogRecognitionResult('NO_MATCH',0,0));row.update(generation_failed=True,generation_error=type(exc).__name__,representation=name,provenance=cc['provenance'])
        row['scan_like']=name!='digital_exact';rows.append(row)
    if did in p['filled_identities']:
        for n in range(5):
            cc=case(r,'filled_'+str(n),dict(variant=n));count=0
            try:
                value,count=fill_acroform(raw,n)
                if not count:raise ValueError('No fields filled')
                row=case_result(cc,value,'filled.pdf',docs,families,diagnostics=True)
            except (ValueError,OSError,RuntimeError) as exc:
                row=evaluate_case(cc,CatalogRecognitionResult('NO_MATCH',0,0));row.update(generation_failed=True,generation_error=type(exc).__name__,representation=cc['representation'],provenance=cc['provenance'])
            row.update(acroform_fields_filled=count,scan_like=False,fill_method='canonical_acroform_verified');rows.append(row)
    return rows

def evaluate():
    checked()
    if (ROOT/OUT/'evaluation_started.json').exists():raise ValueError('Single-shot evaluation already started; do not rerun or retune')
    p=new_plan();assert len(p['evaluation_identities'])>=25
    write(OUT+'evaluation_started.json',dict(started_at=datetime.now(UTC).isoformat(),freeze=checked(),plan_sha256=hashlib.sha256((ROOT/OUT/'robustness_v3_evaluation_plan.json').read_bytes()).hexdigest()))
    rows=[]
    with ProcessPoolExecutor(max_workers=3) as pool:
        futures={pool.submit(evaluation_worker,did,i):did for i,did in enumerate(p['evaluation_identities'])}
        for f in as_completed(futures):rows.extend(f.result());write(OUT+'evaluation_checkpoint.json',dict(cases=rows));print('Single-shot evaluation',futures[f],len(rows),flush=True)
    rows.sort(key=lambda r:r['id']);checked()
    save('robustness_v3',rows,plan=p,scope='Fresh identity-level representation evaluation. Canonical fingerprints exist for known identities; no identity used in calibration.')
    save('scan_v3',[r for r in rows if r.get('scan_like')],scope='Generated scan-like first-page images, OCR failures remain in denominator; not real user scans.')
    save('filled_v3',[r for r in rows if r.get('fill_method')],scope='Actual AcroForm fields, five correlated synthetic variants/template; no semantic/legal validity claim.')
    save('retrieval_v3',rows,scope='Same one-shot rows. Expected ranking diagnostic computed before safety/fusion; no second evaluation.')

def canonical():
    docs,families=catalog();rows=[]
    for i,r in enumerate(active_records()):
        ext='.pdf' if r['mime_type']=='application/pdf' else '.docx';rows.append(case_result(case(r,'canonical_'+r['canonical_file_sha256'][:12]),raw_record(r),'canonical'+ext,docs,families))
        if i%100==0:print('Canonical',i+1,flush=True)
    save('canonical',rows)

def unknown():
    docs,families=catalog();rows=[];seen=set();five=[]
    for name in ['official_documents_v2','official_holdout_v1','official_holdout_v2']:
        manifest,values=cached_texts(name)
        for c in manifest['cases']:
            if c['id'] in {'OH1-033','OH1-047','OH1-055','OH1-063','OH1-098'}:
                result=recognize_catalog(values[c['id']].get('text',''),docs,families,file_sha256=c['sha256']);five.append(dict(id=c['id'],safe=result.match_type=='NO_MATCH' or bool(result.document and result.document.id==c['document_id'])))
            if c.get('expected_match_type')!='NO_MATCH' or c['sha256'] in seen:continue
            seen.add(c['sha256']);raw=(ROOT/'benchmarks/cache'/(c['sha256']+'.body')).read_bytes()
            cc=dict(id=c['id'],group=c['sha256'],category='unknown_official',expected=dict(match_type='NO_MATCH'),representation='official_original',provenance=dict(canonical_sha256=c['sha256'],url=c['url']))
            rows.append(case_result(cc,raw,c['id']+'.'+c['format'],docs,families))
    save('unknown_v3',rows,additional_fresh_unknown=0,scope='Historical official unknowns also used as development safety calibration; not fresh independent unknown evaluation.')
    write(OUT+'historical_five.json',dict(cases=five,passed=all(c['safe'] for c in five)))

def main():
    p=argparse.ArgumentParser();p.add_argument('kind',choices=['calibrate','freeze','evaluate','canonical','unknown']);a=p.parse_args();os.environ.setdefault('OMP_THREAD_LIMIT','1')
    globals()[a.kind]()

if __name__=='__main__':main()
