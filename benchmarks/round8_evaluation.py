"""Prospective identity selection, generation audit, then one recognition run."""
import argparse,csv,hashlib,json
from collections import Counter,defaultdict
from concurrent.futures import ProcessPoolExecutor,as_completed
from datetime import UTC,datetime
from pathlib import Path
from rapidfuzz.fuzz import ratio
from benchmarks.round8_common import *
from benchmarks.round8_calibrate import calibration_ids
from benchmarks.round6_recognition import TRANSFORMS,transform_pdf
from benchmarks.round8_fill import generate
from src.recognize import normalize_text

WORK=ROOT/'benchmarks/work/round8-evaluation'

def new_plan():
    freeze=checked()
    if (ROOT/OUT/'robustness_v4_evaluation_plan.json').exists():raise ValueError('Evaluation plan immutable; already selected')
    docs,_=catalog();by={d.id:d for d in docs};excluded=set(calibration_ids());records=read_bundle()['records'];calrecords=[r for r in records if r['document_id'] in excluded]
    shas={r['canonical_file_sha256'] for r in calrecords};urls={u for r in calrecords for u in [r['url'],r['final_url']]}
    for name in ['official_documents_v2','official_holdout_v1','official_holdout_v2']:
        for c in read('benchmarks/manifests/'+name+'.json')['cases']:
            if c.get('expected_match_type')=='NO_MATCH':
                shas.add(c['sha256']);urls.add(c['url'])
                if c.get('receipt',{}).get('final_url'):urls.add(c['receipt']['final_url'])
    caldocs=[by[i] for i in excluded if i in by];fields=[set(r['field_set']) for r in calrecords if len(r['field_set'])>=8];aggregates=[set(r['aggregate']) for r in calrecords if len(r['aggregate'])>=24]
    def key(d):return (normalize_text(d.titolo_ufficiale),normalize_text(d.codice or ''),d.versione or '')
    signatures={key(d) for d in caldocs}
    def relation(r):
        d=by[r['document_id']];title,code,version=key(d)
        if r['document_id'] in excluded:return 'identity_overlap'
        if r['canonical_file_sha256'] in shas:return 'resource_sha_overlap'
        if r['url'] in urls or r['final_url'] in urls:return 'url_overlap'
        if key(d) in signatures:return 'title_code_version_overlap'
        if any((code and code==key(c)[1] and d.ente==c.ente) or (version==key(c)[2] and (not code or not key(c)[1] or code==key(c)[1]) and ratio(title,key(c)[0])>=92) for c in caldocs):return 'near_title_code_template'
        fs=set(r['field_set'])
        if len(fs)>=8 and any(len(fs&other)/len(fs|other)>=.90 for other in fields):return 'near_acroform_field_template'
        ag=set(r['aggregate'])
        if len(ag)>=24 and any(len(ag&other)/len(ag|other)>=.85 for other in aggregates):return 'near_aggregate_template'
        return None
    eligible={};exclusions=[]
    order=lambda r:hashlib.sha256((str(SEED)+':'+str(r['document_id'])+':'+r['canonical_file_sha256']).encode()).hexdigest()
    for r in sorted(active_records(),key=order):
        reason=relation(r)
        if reason:exclusions.append(dict(document_id=r['document_id'],sha256=r['canonical_file_sha256'],reason=reason))
        elif r['document_id'] not in eligible:eligible[r['document_id']]=r
    sources=defaultdict(list)
    for r in eligible.values():sources[r['source_id']].append(r)
    selected=[];seen=set();counts=Counter();docx=0
    # At most two DOCX: enough to represent DOCX-only issuers while retaining
    # >=350 planned representations with 38 PDFs x seven scans +50 fills.
    while len(selected)<40:
        progress=False
        for sid in sorted(sources):
            r=next((r for r in sources[sid] if r['document_id'] not in seen and counts[sid]<10 and (r['mime_type']=='application/pdf' or docx<2)),None)
            if r:
                selected.append(r);seen.add(r['document_id']);counts[sid]+=1;docx+=r['mime_type']!='application/pdf';progress=True
                if len(selected)==40:break
        if not progress:break
    fillers=[];fc=Counter()
    pdfs=[r for r in selected if r['mime_type']=='application/pdf']
    for r in sorted(pdfs,key=lambda r:(not bool(r['field_set']),order(r))):
        if fc[r['source_id']]>=3:continue
        fillers.append(r);fc[r['source_id']]+=1
        if len(fillers)>=10:break
    selected.sort(key=order)
    plan=dict(seed=SEED,freeze_commit=freeze['commit'],created_at=datetime.now(UTC).isoformat(),selection='Metadata/hash-only source round-robin, max10 IDs/source, max2 DOCX, first10 PDF fillers preferring actual field sets with max3/source. No recognition outcomes used.',calibration_identities=sorted(excluded),evaluation_identities=[r['document_id'] for r in selected],filled_identities=[r['document_id'] for r in fillers],resources={str(r['document_id']):r['canonical_file_sha256'] for r in selected},source_counts=dict(counts),source_concentration=max(counts.values())/len(selected) if selected else None,planned_representations=len(selected)+len(pdfs)*7+len(fillers)*5,planned_scan_like=len(pdfs)*7)
    leakage=dict(identity_overlap=sorted(excluded&seen),resource_sha_overlap=sorted(shas&{r['canonical_file_sha256'] for r in selected}),url_overlap=sorted(urls&{u for r in selected for u in [r['url'],r['final_url']]}),title_code_version_or_near_template_overlap=[r['document_id'] for r in selected if relation(r)],prohibited_leakage=0,excluded_resources=exclusions,rule='Same code+issuer any version; normalized title/code/version; title ratio>=92 with compatible code/version; field-set Jaccard>=.90 (>=8 fields); aggregate Jaccard>=.85 (>=24 hashes).')
    assert not any(leakage[k] for k in ['identity_overlap','resource_sha_overlap','url_overlap','title_code_version_or_near_template_overlap'])
    write(OUT+'robustness_v4_evaluation_plan.json',plan);write(OUT+'evaluation_v4_leakage.json',leakage)
    print('Prospective evaluation plan',len(selected),'IDs',len(counts),'sources',plan['planned_representations'],'representations',flush=True)

def transformed(raw,params):
    if params.get('page'):
        import fitz
        with fitz.open(stream=raw,filetype='pdf') as pdf,fitz.open() as out:
            n=min(int(params['page'])-1,len(pdf)-1);out.insert_pdf(pdf,from_page=n,to_page=n);raw=out.tobytes(no_new_id=True)
        params={k:v for k,v in params.items() if k!='page'}
    return transform_pdf(raw,params)

def prepare_evaluation():
    checked()
    if (ROOT/OUT/'evaluation_started.json').exists() or (ROOT/OUT/'evaluation_prepared.json').exists():raise ValueError('Evaluation representations immutable after preparation/start')
    p=read(OUT+'robustness_v4_evaluation_plan.json');WORK.mkdir(parents=True,exist_ok=True);records=active_records();manifest=[];generation=[]
    scans=[x for x in TRANSFORMS if x[0] not in ['digital_exact','first_page_only']]
    for i,did in enumerate(p['evaluation_identities']):
        r=next(r for r in records if r['document_id']==did and r['canonical_file_sha256']==p['resources'][str(did)]);raw=raw_record(r);ext='.pdf' if r['mime_type']=='application/pdf' else '.docx'
        variants=[('digital_exact',{})]
        if ext=='.pdf':
            variants += [scans[(7*i+j)%len(scans)] for j in range(7)]
            if len(r['pages'])>1:
                name,params=variants[-1];variants[-1]=(name+'_page2',dict(params,page=2))
        if did in p['filled_identities']:variants += [('filled_'+str(v),dict(variant=v)) for v in range(5)]
        for name,params in variants:
            cc=case(r,name,params);audit=dict(case_id=cc['id'],document_id=did,resource_type='pdf' if ext=='.pdf' else 'docx',acroform_static='',generation_method='',generated=False,reopened=False,fields_verified=0,error='',recognition_result='not_run_generation_first')
            try:
                if name.startswith('filled_'):
                    value,details=generate(raw,'canonical'+ext,params['variant']);suffix=ext;audit.update({k:details[k] for k in ['acroform_static','generation_method','reopened','fields_verified']})
                    audit['synthetic_verified']=details['synthetic_verified']
                    if details.get('acroform_fallback_reason'):audit['fallback_reason']=details['acroform_fallback_reason']
                elif name=='digital_exact':value=raw;suffix=ext
                else:value,suffix=transformed(raw,params)
                sha=hashlib.sha256(value).hexdigest();path=WORK/(cc['id']+suffix);path.write_bytes(value);audit['generated']=True
                manifest.append(dict(case=cc,path=path.relative_to(ROOT).as_posix(),sha256=sha,filled=name.startswith('filled_'),scan_like=name!='digital_exact' and not name.startswith('filled_')))
            except (ValueError,OSError,RuntimeError) as exc:audit['error']=type(exc).__name__+': '+str(exc)
            generation.append(audit)
        print('Prepared identity',did,'valid inputs',len(manifest),flush=True)
    write(OUT+'evaluation_prepared.json',dict(plan_sha256=hashlib.sha256((ROOT/OUT/'robustness_v4_evaluation_plan.json').read_bytes()).hexdigest(),prepared_at=datetime.now(UTC).isoformat(),representations=manifest,generation_audit=generation,scope='No recognizer called. Failed generation is separate from recognition denominator under Round8 instructions. Adequacy uses actual generated inputs.'))
    generation_csv(generation)
    print('Prepared',len(manifest),'inputs; valid fills',sum(r['filled'] for r in manifest),flush=True)

def generation_csv(rows):
    fields=['case_id','document_id','resource_type','acroform/static','generation_method','generated','reopened','fields_verified','error','recognition_result']
    with (ROOT/OUT/'filled_generation_audit.csv').open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore',lineterminator='\n');w.writeheader()
        for r in rows:
            if '-filled_' in r['case_id']:w.writerow(dict(r,**{'acroform/static':r['acroform_static']}))

def evaluate_worker(item):
    raw=(ROOT/item['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==item['sha256']
    row=case_result(item['case'],raw,Path(item['path']).name);row.update(filled=item['filled'],scan_like=item['scan_like']);return row

def evaluate():
    checked()
    if (ROOT/OUT/'evaluation_started.json').exists():raise ValueError('Single-shot Round8 evaluation already started; never rerun or retune')
    p=read(OUT+'robustness_v4_evaluation_plan.json');prepared=read(OUT+'evaluation_prepared.json')
    assert hashlib.sha256((ROOT/OUT/'robustness_v4_evaluation_plan.json').read_bytes()).hexdigest()==prepared['plan_sha256']
    write(OUT+'evaluation_started.json',dict(started_at=datetime.now(UTC).isoformat(),freeze=checked(),prepared_sha256=hashlib.sha256((ROOT/OUT/'evaluation_prepared.json').read_bytes()).hexdigest()))
    rows=[]
    with ProcessPoolExecutor(max_workers=3) as pool:
        futures={pool.submit(evaluate_worker,item):item['case']['id'] for item in prepared['representations']}
        for f in as_completed(futures):
            rows.append(f.result());write(OUT+'evaluation_checkpoint.json',dict(completed=len(rows),cases=rows))
            if len(rows)%25==0:print('Single-shot v4',len(rows),'/',len(futures),flush=True)
    rows.sort(key=lambda r:r['id']);checked()
    save('robustness_v4',rows,plan=p,scope='Single-shot fresh representation evaluation after freeze; generated valid inputs only, generation failures reported separately. Canonical fingerprints contain known identities; no generalization claim to unknown identities.')
    save('scan_v4',[r for r in rows if r['scan_like']]);save('filled_v4',[r for r in rows if r['filled']]);save('retrieval_v4',rows,scope='Same one-shot rows, no second evaluation.')
    lookup={r['id']:r for r in rows}
    for a in prepared['generation_audit']:
        if a['case_id'] in lookup:a['recognition_result']=lookup[a['case_id']]['observed']['match_type']
        else:a['recognition_result']='not_run_generation_failed'
    generation_csv(prepared['generation_audit'])
    print('Single-shot v4 complete',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['plan','prepare','evaluate','freeze']);a=p.parse_args();dict(plan=new_plan,prepare=prepare_evaluation,evaluate=evaluate,freeze=freeze)[a.mode]()
