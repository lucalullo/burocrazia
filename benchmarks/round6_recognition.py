"""Offline release evidence, calibration/evaluation identities frozen separately."""
from __future__ import annotations
import argparse,hashlib,json,time,os
from concurrent.futures import ProcessPoolExecutor,as_completed
from collections import defaultdict
from dataclasses import asdict
from datetime import UTC,datetime
from pathlib import Path
from io import BytesIO
from benchmarks.round3_audit import ROOT,catalog,read,write
from benchmarks.evaluate import summary,code_hash
from benchmarks.round5_recognition import (known_case,raw_record,transform_pdf as historical_transform_pdf,filled_pdf,
    family_label,cached_texts,split_identities)
from scripts.benchmark import evaluate_case
from src.fingerprint_v2 import read_bundle,features,public_index,DEFAULT_THRESHOLDS,fused,thresholds,revision
from src.fingerprint_visual import visual_for_bytes
from src.fingerprint_match_v2 import safety_reason
from src.extract import extract_document,ExtractionError
from src.recognize import recognize_catalog,recognize_document_family
from src.models import CatalogRecognitionResult

OUT='benchmarks/results/round6/'
SEED=20261012
TRANSFORMS=[('digital_exact',{}),('raster_200',dict(dpi=200)),('raster_150',dict(dpi=150)),
 ('jpeg_90',dict(dpi=150,quality=90)),('jpeg_75',dict(dpi=150,quality=75)),('jpeg_60',dict(dpi=150,quality=60)),
 ('grayscale',dict(dpi=150,gray=True)),('contrast_minus20',dict(dpi=150,contrast=.8)),
 ('blur_mild',dict(dpi=150,blur=.65)),('crop_2pct',dict(dpi=150,crop=.02)),
 ('crop_5pct',dict(dpi=150,crop=.05)),('resize_075',dict(dpi=150,resize=.75)),
 ('first_page_only',dict(first_page_only=True)),('rotation_90',dict(dpi=150,angle=90)),
 ('rotation_180',dict(dpi=150,angle=180)),('rotation_270',dict(dpi=150,angle=270))]

def transform_pdf(raw,params):
    if params.get('first_page_only'):
        import fitz
        with fitz.open(stream=raw,filetype='pdf') as source,fitz.open() as out:
            out.insert_pdf(source,from_page=0,to_page=0)
            return out.tobytes(no_new_id=True),'.pdf'
    return historical_transform_pdf(raw,params)

def identity():
    from benchmarks.round4_common import runtime_hash
    return dict(code_sha256=code_hash(),runtime_sha256=runtime_hash(),fingerprint_sha256=revision(),seed=SEED,executed_at=datetime.now(UTC).isoformat())

def active_records():return [r for r in read_bundle()['records'] if r['status']=='active']

def plan():
    path=ROOT/OUT/'robustness_v2_plan.json'
    if path.exists():return read(OUT+'robustness_v2_plan.json')
    by=defaultdict(list)
    for r in active_records():
        if r['mime_type']=='application/pdf':by[r['source_id']].append(r)
    key=lambda r:hashlib.sha256((str(SEED)+':'+str(r['document_id'])).encode()).hexdigest()
    selected=[];seen=set()
    for sid in sorted(by):
        for r in sorted(by[sid],key=key):
            if r['document_id'] not in seen:selected.append(r);seen.add(r['document_id'])
            if sum(x['source_id']==sid for x in selected)>=2:break
    for r in sorted(active_records(),key=key):
        if len(selected)>=20:break
        if r['mime_type']=='application/pdf' and r['document_id'] not in seen:selected.append(r);seen.add(r['document_id'])
    selected=sorted(selected,key=key);cal=selected[:8];evaluation=selected[8:]
    result=dict(seed=SEED,selection='Two PDF identities/source where available, then SHA(seed:id) up to 20. Fixed algorithm, no result-based selection.',
        calibration_identities=[r['document_id'] for r in cal],evaluation_identities=[r['document_id'] for r in evaluation],
        resources={str(r['document_id']):r['canonical_file_sha256'] for r in selected},transforms=TRANSFORMS,
        frozen_at=datetime.now(UTC).isoformat(),independent_identity_generalization=False,
        limits='Known identity representation evaluation; canonical fingerprints contain evaluation identities. First-page scan transforms, not all pages. No parameter fitting on evaluation identities.')
    write(OUT+'robustness_v2_plan.json',result);return result

def checked_calibration():
    r=read(OUT+'fingerprint_calibration.json')
    raw=(ROOT/'data/recognition_profiles/fingerprint_v2.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=r['profile_sha256']:raise ValueError('Calibration changed after freeze')
    if set(r['calibration_identities'])&set(r['evaluation_identities']):raise ValueError('Identity leakage')
    if r['fingerprint_sha256']!=revision():raise ValueError('Fingerprint bundle changed after calibration freeze')
    from benchmarks.round4_common import runtime_hash
    if r.get('runtime_sha256') and r['runtime_sha256']!=runtime_hash():raise ValueError('Runtime changed after calibration freeze')
    return r

def case_result(case,raw,filename,docs,families,*,diagnostics=False):
    start=time.perf_counter();ex=None;error=None;ranks=[];scores=[];visual_ms=0
    try:
        ex=extract_document(raw,filename);extraction_ms=(time.perf_counter()-start)*1000
        visual_start=time.perf_counter();visual=visual_for_bytes(raw,filename);visual_ms=(time.perf_counter()-visual_start)*1000;begin=time.perf_counter()
        result=recognize_catalog(ex.text,docs,families,file_sha256=hashlib.sha256(raw).hexdigest(),visual_fingerprint=visual)
        matching_ms=(time.perf_counter()-begin)*1000
        if diagnostics:
            scores=public_index().similarities(features(ex.text),visual)
            ranks=[r['document_id'] for r in scores]
    except (ValueError,OSError,ExtractionError,RuntimeError) as exc:
        error=type(exc).__name__+': '+str(exc);extraction_ms=(time.perf_counter()-start)*1000;matching_ms=0
        result=CatalogRecognitionResult('NO_MATCH',0,0,reason='Extraction failed')
    row=evaluate_case(case,result,matching_ms)
    expected=case['expected'].get('document_id')
    rank=ranks.index(expected)+1 if expected in ranks else None
    row.update(provenance=case['provenance'],representation=case['representation'],input_sha256=hashlib.sha256(raw).hexdigest(),
        extraction_failed=error is not None,extraction_error=error,extraction_ms=extraction_ms,used_ocr=bool(ex and ex.used_ocr),
        extraction_method=ex.method if ex else None,signals=list(result.document_signals),candidate_rank=rank,
        visual_ms=visual_ms,end_to_end_ms=extraction_ms+visual_ms+matching_ms,
        candidate_recall_at_k={str(k):rank is not None and rank<=k for k in [1,5,10,25]},
        retrieval_scores=scores[:25] if diagnostics else [])
    return row

def save(name,rows,**extra):
    r=dict(schema_version=2,identity=identity(),summary=summary(rows),cases=rows,**extra)
    r['counts']=dict(exact=sum(x['document_correct'] for x in rows),family=sum(x['family_correct'] for x in rows),
        reject=sum(x['observed']['match_type']=='NO_MATCH' for x in rows),
        wrong=sum(x['observed']['match_type']!='NO_MATCH' and not (x['document_correct'] or x['family_correct']) for x in rows),
        extraction_failed=sum(x.get('extraction_failed',False) for x in rows))
    r['candidate_recall_at_k']={str(k):dict(numerator=sum(x.get('candidate_recall_at_k',{}).get(str(k),False) for x in rows),denominator=len(rows)) for k in [1,5,10,25]}
    write(OUT+name+'.json',r);return r

def canonical():
    docs,families=catalog();rows=[];records=active_records();formats=defaultdict(set)
    for r in records:formats[r['document_id']].add(r['mime_type'])
    for i,r in enumerate(records):
        ext='.pdf' if r['mime_type']=='application/pdf' else '.docx'
        row=case_result(known_case(r,'canonical_v2_'+r['canonical_file_sha256'][:12]),raw_record(r),'canonical'+ext,docs,families)
        row['canonical_mime_type']=r['mime_type'];rows.append(row)
        if i%50==0:print('Canonical v2',i+1,flush=True)
    save('canonical_v2',rows,scope='Active canonical resources, exact original bytes; shared/stale/quarantined resources excluded and counted separately in coverage.')
    selected={did for did,types in formats.items() if len(types)>1}
    save('cross_format_same_identity',[r for r in rows if r['expected']['document_id'] in selected],identities=sorted(selected),
        limits='Actual PDF/DOCX alternative resources of the same catalog identity, exact SHA recognition. Not a test of scanned DOCX rendering or cross-format text generalization.')

def identity_representations(did):
    p=plan();r=next(r for r in active_records() if r['document_id']==did and p['resources'].get(str(did))==r['canonical_file_sha256'])
    docs,families=catalog();rows=[];raw=raw_record(r)
    work=ROOT/'benchmarks/work/round6-representations';work.mkdir(parents=True,exist_ok=True)
    for name,params in TRANSFORMS:
        variant,ext=(raw,'.pdf') if name=='digital_exact' else transform_pdf(raw,params)
        (work/(str(did)+'-'+name+ext)).write_bytes(variant)
        rows.append(case_result(known_case(r,name,params),variant,'variant'+ext,docs,families,diagnostics=True))
    return rows

def representations(which):
    p=plan();ids=p[which+'_identities'];rows=[]
    # Disjoint identities, fixed order, <=3 local workers. No network, text cache
    # or parameter fitting in workers. Tesseract gets one OpenMP thread/worker.
    os.environ.setdefault('OMP_THREAD_LIMIT','1')
    checkpoint=ROOT/OUT/(which+'_checkpoint.json')
    prior=read(OUT+which+'_checkpoint.json')['cases'] if checkpoint.exists() else []
    completed={did for did in ids if sum(r['expected'].get('document_id')==did for r in prior)==len(TRANSFORMS)}
    rows=[r for r in prior if r['expected'].get('document_id') in completed]
    pending=[did for did in ids if did not in completed]
    with ProcessPoolExecutor(max_workers=3) as pool:
        futures={pool.submit(identity_representations,did):did for did in pending}
        for future in as_completed(futures):
            did=futures[future];rows.extend(future.result())
            write(OUT+which+'_checkpoint.json',dict(cases=rows));print(which,did,'cases',len(rows),flush=True)
    order={did:i for i,did in enumerate(ids)};trans={name:i for i,(name,_) in enumerate(TRANSFORMS)}
    rows.sort(key=lambda r:(order[r['expected']['document_id']],trans[r['representation']]))
    return rows

def calibrate():
    if (ROOT/OUT/'fingerprint_calibration.json').exists():raise ValueError('Calibration already frozen; create a new version instead of retuning')
    p=plan();rows=representations('calibration');save('calibration_observations',rows)
    docs,_=catalog();by={d.id:d for d in docs};options=[]
    for text in [.75,.82,.90,.95]:
        for chars in [.05,.1,.15,.2,.25,.3,.4,.5,.55,.65,.72,.78,.90]:
            for margin in [.005,.01,.02,.04,.055,.08]:
                t=dict(DEFAULT_THRESHOLDS,text=text,chars=chars,margin=margin);correct=wrong=0
                for row in rows:
                    scores=row['retrieval_scores'];eligible=[s for s in scores if fused(s,t)]
                    if not eligible:continue
                    b=eligible[0];runner=max((s['score'] for s in scores if s['document_id']!=b['document_id']),default=0)
                    if b['score']-runner<t['margin']:continue
                    if b['document_id']==row['expected']['document_id']:correct+=1
                    else:wrong+=1
                options.append(dict(thresholds=t,correct=correct,wrong=wrong))
    safe=[o for o in options if o['wrong']==0]
    chosen=max(safe,key=lambda o:(o['correct'],o['thresholds']['text'],o['thresholds']['chars'],o['thresholds']['margin'])) if safe else dict(thresholds=DEFAULT_THRESHOLDS,correct=0,wrong=0)
    profile=dict(schema_version=2,thresholds=chosen['thresholds'],weights=dict(text=.5,chars=.25,anchors=.15,visual=.1),
        objective='Maximize correct calibration retrieval/fusion under zero wrong calibration accepts; safety vetoes remain mandatory.',
        constraints=['no evaluation rows read','zero wrong calibration accepts','at least two corroborating channels','margin'],
        calibration_identities=p['calibration_identities'],evaluation_identities=p['evaluation_identities'],
        parameters=read_bundle()['parameters'],frozen_at=datetime.now(UTC).isoformat())
    path=ROOT/'data/recognition_profiles/fingerprint_v2.json';path.write_bytes((json.dumps(profile,ensure_ascii=False,indent=2)+'\n').encode())
    from benchmarks.round4_common import runtime_hash
    write(OUT+'fingerprint_calibration.json',dict(**profile,profile_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),fingerprint_sha256=revision(),runtime_sha256=runtime_hash(),
        grid=options,chosen=chosen,selection_limits='Grid objective uses retrieval scores before safety veto. Calibration recognizer results also reported; safety may reduce recall. No evaluation tuning.'))
    thresholds.cache_clear();print('Calibration frozen',chosen,flush=True)

def evaluate():
    cal=checked_calibration();rows=representations('evaluation')
    by={n:summary([r for r in rows if r['representation']==n]) for n,_ in TRANSFORMS}
    save('robustness_v2',rows,plan=plan(),calibration_profile_sha256=cal['profile_sha256'],by_transformation=by,
        robustness_v1_historical='benchmarks/results/round5/robustness.json')
    scans=[r for r in rows if r['representation'] not in ['digital_exact','first_page_only']]
    save('scan_ocr_v2',scans,ocr_extraction_success=sum(r['used_ocr'] and not r['extraction_failed'] for r in scans),
        limits='Generated scans of official known PDFs, not real handwritten/mobile acquisition. First page only; failures included.')

def filled():
    checked_calibration();docs,families=catalog();p=plan();by={r['document_id']:r for r in active_records() if p['resources'].get(str(r['document_id']))==r['canonical_file_sha256']};rows=[]
    from pypdf import PdfReader,PdfWriter
    work=ROOT/'benchmarks/work/round6-filled';work.mkdir(parents=True,exist_ok=True)
    for did in plan()['evaluation_identities']:
        r=by[did];raw=raw_record(r)
        for variant in range(10):
            case=known_case(r,'filled_'+str(variant));start=time.perf_counter()
            try:
                result,n=fill_acroform(raw,variant)
                # Static forms get varying realistic synthetic content at fixed
                # field-like positions. Explicitly weaker than actual widgets.
                import fitz
                if not n:
                    with fitz.open(stream=raw,filetype='pdf') as pdf:
                        page=pdf[0]
                        values=[f'Persona Fittizia {variant}',f'CF SINTETICO NON VALIDO {variant}',f'Via di Esempio {17+variant}',
                            f'{variant+1:02}/02/2030',f'EUR {1234+variant},50 [X]',f'Annotazione sintetica {variant}']
                        for i,v in enumerate(values):page.insert_text((55,130+i*45),v,fontsize=8)
                        result=pdf.tobytes(no_new_id=True)
                path=work/(str(did)+'-'+str(variant)+'.pdf');path.write_bytes(result)
                row=case_result(case,result,path.name,docs,families,diagnostics=True)
                row.update(acroform_fields_filled=n,fill_method='canonical_acroform_verified' if n else 'synthetic_static_overlay',
                    distinct_acroform_values=True)
            except (ValueError,OSError,RuntimeError) as exc:
                row=evaluate_case(case,CatalogRecognitionResult('NO_MATCH',0,0),0)
                row.update(provenance=case['provenance'],representation=case['representation'],generation_error=str(exc),
                    extraction_failed=False,used_ocr=False,acroform_fields_filled=0)
            rows.append(row)
        print('Filled',did,len(rows),flush=True)
    save('filled_forms_v2',rows,interactive_cases=sum(r['acroform_fields_filled']>0 for r in rows),
        limits='10 variants/identity with varying synthetic values. Cases share templates and are dependent. Static overlays are weaker than interactive fields; no handwriting. Generation failures counted NO.')

def fill_acroform(raw,variant):
    """Require the canonical field tree and rendered widget values to agree."""
    from pypdf import PdfReader,PdfWriter
    import fitz
    reader=PdfReader(BytesIO(raw));tree=reader.get_fields() or {};values={}
    with fitz.open(stream=raw,filetype='pdf') as pdf:
        for page in pdf:
            for w in page.widgets() or ():
                if w.field_name not in tree:raise ValueError('Ambiguous/orphaned field, no automatic repair')
                if w.field_type==fitz.PDF_WIDGET_TYPE_TEXT:
                    label=w.field_name.casefold()
                    if any(k in label for k in ['data','date']):v=f'{variant+1:02}/02/2030'
                    elif any(k in label for k in ['fiscal','cf','codice']):v=f'CF-NON-VALIDO-{variant}'
                    elif any(k in label for k in ['import','euro','somma']):v=f'{1234+variant},50'
                    elif any(k in label for k in ['indirizz','via','residen']):v=f'Via Fittizia {17+variant}'
                    else:v=f'Esempio {variant}'
                    values[w.field_name]=v[:w.text_maxlen] if w.text_maxlen>0 else v
                elif w.field_type==fitz.PDF_WIDGET_TYPE_CHECKBOX:values[w.field_name]=w.on_state() if variant%2==0 else '/Off'
    if not values:return raw,0
    writer=PdfWriter();writer.clone_document_from_reader(reader);writer.update_page_form_field_values(None,values,auto_regenerate=False)
    out=BytesIO();writer.write(out);result=out.getvalue();actual=PdfReader(BytesIO(result)).get_fields() or {}
    for key,value in values.items():
        if key not in actual or str(actual[key].get('/V'))!=str(value):raise ValueError('Canonical /V mismatch')
    with fitz.open(stream=result,filetype='pdf') as check:
        for page in check:
            for w in page.widgets() or ():
                if w.field_name in values and str(w.field_value)!=str(values[w.field_name]).lstrip('/'):
                    raise ValueError('Widget /V mismatch')
    for page in PdfReader(BytesIO(result)).pages:
        for ref in page.get('/Annots',[]):
            obj=ref.get_object()
            if obj.get('/Subtype')=='/Widget' and not obj.get('/AP',{}).get('/N'):raise ValueError('Missing widget appearance')
    return result,len(values)

def unknown():
    docs,families=catalog();rows=[];seen=set();historical=[]
    for name in ['official_documents_v2','official_holdout_v1','official_holdout_v2']:
        manifest,values=cached_texts(name)
        for c in manifest['cases']:
            if c['id'] in {'OH1-033','OH1-047','OH1-055','OH1-063','OH1-098'}:
                result=recognize_catalog(values[c['id']].get('text',''),docs,families,file_sha256=c['sha256'])
                historical.append(dict(id=c['id'],expected=c['document_id'],observed=result.document.id if result.document else None,
                    safe=result.match_type=='NO_MATCH' or bool(result.document and result.document.id==c['document_id'])))
            if c.get('expected_match_type')!='NO_MATCH' or c['sha256'] in seen:continue
            seen.add(c['sha256']);raw=(ROOT/'benchmarks/cache'/(c['sha256']+'.body')).read_bytes()
            case=dict(id=c['id'],group=c['sha256'],category='unknown_official',expected=dict(match_type='NO_MATCH'),representation='official_original',
                provenance=dict(url=c['url'],canonical_sha256=c['sha256'],source=c['source_key']))
            rows.append(case_result(case,raw,c['id']+'.'+c['format'],docs,families))
    save('unknown_official',rows,additional_unseen=0,limits='All 137 historical distinct official negatives retained. Additional cache resources lack independently adjudicated unknown labels; none relabelled from titles automatically.')
    write(OUT+'historical_five.json',dict(cases=historical,passed=all(x['safe'] for x in historical)))

def main():
    p=argparse.ArgumentParser();p.add_argument('kind',choices=['plan','canonical','calibrate','evaluate','filled','unknown']);a=p.parse_args()
    {'plan':plan,'canonical':canonical,'calibrate':calibrate,'evaluate':evaluate,'filled':filled,'unknown':unknown}[a.kind]()

if __name__=='__main__':main()
