"""Separate known-representation, family-identity and unknown benchmarks.

All official bytes/derived images stay ignored. No acquisition in this runner.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
from dataclasses import asdict
from datetime import UTC,datetime
import hashlib
from io import BytesIO
import json
from pathlib import Path
import random
import time
from functools import lru_cache
import fitz
from PIL import Image,ImageFilter,ImageEnhance
from benchmarks.round3_audit import ROOT,read,write,catalog
from benchmarks.round4_common import texts
from benchmarks.round3_audit import load_texts
from benchmarks.evaluate import summary,code_hash
from scripts.benchmark import evaluate_case
from src.document_fingerprints import read_bundle,FingerprintIndex,features
from src.extract import extract_document,ExtractionError
from src.recognize import recognize_catalog,recognize_document_family,normalize_text
from src.models import CatalogRecognitionResult

OUT='benchmarks/results/round5/'
SEED=20261011
TRANSFORMS=[('raster_150',dict(dpi=150)),('raster_200',dict(dpi=200)),
 ('grayscale',dict(dpi=150,gray=True)),('jpeg_60',dict(dpi=150,quality=60)),
 ('jpeg_75',dict(dpi=150,quality=75)),('jpeg_90',dict(dpi=150,quality=90)),
 ('blur',dict(dpi=150,blur=.65)),('low_contrast',dict(dpi=150,contrast=.65)),
 ('crop_margins',dict(dpi=150,crop=.01)),('rotate_90',dict(dpi=150,angle=90)),
 ('rotate_180',dict(dpi=150,angle=180)),('rotate_270',dict(dpi=150,angle=270)),
 ('resize_down_up',dict(dpi=150,resize=.7)),('first_page_only',dict(first_page_only=True))]

def cached_texts(name):
    return (read('benchmarks/manifests/official_documents_v2.json'),load_texts()) if name=='official_documents_v2' else texts(name)


def identity():
    from src.document_fingerprints import revision
    return dict(code_sha256=code_hash(),fingerprint_sha256=revision(),seed=SEED,executed_at=datetime.now(UTC).isoformat())


def raw_record(r):
    raw=(ROOT/'benchmarks/cache'/(r['canonical_file_sha256']+'.body')).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=r['canonical_file_sha256']:raise ValueError('Canonical hash mismatch')
    return raw


def case_result(case,raw,filename,docs,families):
    start=time.perf_counter();error=None;ex=None;result=None
    try:
        ex=extract_document(raw,filename)
        extraction_ms=(time.perf_counter()-start)*1000;begin=time.perf_counter()
        result=recognize_catalog(ex.text,docs,families,file_sha256=hashlib.sha256(raw).hexdigest())
        ms=(time.perf_counter()-begin)*1000
    except (ValueError,OSError,ExtractionError) as exc:
        error=str(exc);ms=0;extraction_ms=(time.perf_counter()-start)*1000
        result=CatalogRecognitionResult('NO_MATCH',0,0,reason='Extraction failed')
    row=evaluate_case(case,result,ms)
    row.update(provenance=case['provenance'],representation=case['representation'],
        input_sha256=hashlib.sha256(raw).hexdigest(),extraction_failed=bool(error),
        extraction_error=error,extraction_ms=extraction_ms,used_ocr=bool(ex and ex.used_ocr),
        extraction_method=ex.method if ex else None,signals=list(result.document_signals))
    return row


def known_case(r,name,params=None):
    family_id=r.get('expected_family')
    d=catalog_by_id()[r['document_id']]
    return dict(id=f"FP-{r['document_id']}-{name}",group='document:'+str(r['document_id']),category='known_identity',
        expected=dict(match_type='DOCUMENT_MATCH',document_id=r['document_id'],family_id=family_id,entity=d.ente,version=d.versione),representation=name,
        provenance=dict(canonical_sha256=r['canonical_file_sha256'],canonical_url=r['url'],
            source_id=r['source_id'],document_id=r['document_id'],expected_family=family_id,
            transform_params=params or {},seed=SEED))

@lru_cache(maxsize=1)
def catalog_by_id():return {d.id:d for d in catalog()[0]}


def save(name,rows,**extra):
    report=dict(schema_version=1,identity=identity(),independent_identity_generalization=False,
        summary=summary(rows),cases=rows,**extra)
    report['counts']=dict(exact=sum(r['document_correct'] for r in rows),family=sum(r['family_correct'] for r in rows),
        reject=sum(r['observed']['match_type']=='NO_MATCH' for r in rows),
        wrong=sum(not (r['document_correct'] or r['family_correct']) and r['observed']['match_type']!='NO_MATCH' for r in rows),
        extraction_failed=sum(r.get('extraction_failed',False) for r in rows))
    write(OUT+name+'.json',report);return report


def canonical():
    docs,families=catalog();rows=[];by={d.id:d for d in docs}
    for i,r in enumerate(read_bundle()['records']):
        r=dict(r,expected_family=family_label(by[r['document_id']]))
        ext='.pdf' if r['mime_type']=='application/pdf' else '.docx'
        rows.append(case_result(known_case(r,'canonical'),raw_record(r),'canonical'+ext,docs,families))
        if i%25==0:print('Canonical benchmark',i+1,flush=True)
    save('canonical',rows,scope='Known identity, exact original bytes; not identity generalization.',
        sha_recognized=sum('official_file_sha256_exact' in r['signals'] for r in rows))


def transform_pdf(raw,params):
    with fitz.open(stream=raw,filetype='pdf') as source:
        if params.get('first_page_only'):
            with fitz.open() as out:
                out.insert_pdf(source,from_page=0,to_page=0);return out.tobytes(),'.pdf'
        page=source[0];pix=page.get_pixmap(dpi=params['dpi'],alpha=False)
        im=Image.frombytes('RGB',[pix.width,pix.height],pix.samples)
    if params.get('gray'):im=im.convert('L')
    if params.get('blur'):im=im.filter(ImageFilter.GaussianBlur(params['blur']))
    if params.get('contrast'):im=ImageEnhance.Contrast(im).enhance(params['contrast'])
    if params.get('crop'):
        x=int(im.width*params['crop']);y=int(im.height*params['crop']);im=im.crop((x,y,im.width-x,im.height-y))
    if params.get('angle'):im=im.rotate(params['angle'],expand=True)
    if params.get('resize'):
        size=im.size;im=im.resize((int(size[0]*params['resize']),int(size[1]*params['resize']))).resize(size)
    buf=BytesIO();ext='.jpg' if params.get('quality') else '.png'
    im.save(buf,format='JPEG' if ext=='.jpg' else 'PNG',**({'quality':params['quality']} if ext=='.jpg' else {}));im.close()
    return buf.getvalue(),ext


def filled_pdf(raw):
    from pypdf import PdfReader,PdfWriter
    reader=PdfReader(BytesIO(raw));writer=PdfWriter();writer.clone_document_from_reader(reader)
    field_tree=reader.get_fields() or {};values={};n=0
    with fitz.open(stream=raw,filetype='pdf') as pdf:
        for page in pdf:
            for widget in page.widgets() or ():
                if widget.field_name not in field_tree:
                    raise ValueError('Orphaned/ambiguous widget: no automatic field-tree repair.')
                if widget.field_type==fitz.PDF_WIDGET_TYPE_TEXT:
                    values[widget.field_name]=['Mario Esempio','01/02/2030','Via Fittizia 17','1234,50'][n%4];n+=1
                elif widget.field_type==fitz.PDF_WIDGET_TYPE_CHECKBOX:
                    values[widget.field_name]=widget.on_state();n+=1
        if n==0:
            page=pdf[0];page.insert_text((35,page.rect.height-25),'Mario Esempio - Via Fittizia 17 - 01/02/2030 - EUR 1234,50 [X]',fontsize=8)
            return pdf.tobytes(),n
    writer.update_page_form_field_values(None,values,auto_regenerate=False)
    output=BytesIO();writer.write(output);result=output.getvalue()
    actual=PdfReader(BytesIO(result)).get_fields() or {}
    for key,value in values.items():
        if str(actual[key].get('/V'))!=str(value):raise ValueError('Filled AcroForm canonical value mismatch.')
    with fitz.open(stream=result,filetype='pdf') as check:
        for page in check:
            for widget in page.widgets() or ():
                if widget.field_name in values and str(widget.field_value)!=str(values[widget.field_name]):raise ValueError('Filled widget appearance/value mismatch.')
    return result,n


def robustness(per_source=2):
    docs,families=catalog();groups=defaultdict(list);by={d.id:d for d in docs}
    for r in read_bundle()['records']:
        if r['mime_type']=='application/pdf':groups[r['source_id']].append(dict(r,expected_family=family_label(by[r['document_id']])))
    selected=[]
    for key in sorted(groups):selected+=sorted(groups[key],key=lambda r:hashlib.sha256(str(r['document_id']).encode()).hexdigest())[:per_source]
    plan=dict(seed=SEED,selection='SHA(document_id) order within source; fixed before representations are evaluated.',
        canonical_document_ids=[r['document_id'] for r in selected],transforms=TRANSFORMS,
        scope='First canonical page transformed; representation holdout only. No official file/image is redistributed.')
    write(OUT+'robustness_plan.json',plan)
    rows=[];filled=[];work=ROOT/'benchmarks/work/round5-representations';work.mkdir(parents=True,exist_ok=True)
    for r in selected:
        raw=raw_record(r)
        for name,params in TRANSFORMS:
            variant,ext=transform_pdf(raw,params)
            path=work/(str(r['document_id'])+'-'+name+ext);path.write_bytes(variant)
            rows.append(case_result(known_case(r,name,params),variant,path.name,docs,families))
            print('Robustness',r['document_id'],name,rows[-1]['observed'],flush=True)
            write(OUT+'robustness_checkpoint.json',dict(cases=rows))
        case=known_case(r,'filled',dict(fictitious_only=True))
        try:
            variant,widgets=filled_pdf(raw);path=work/(str(r['document_id'])+'-filled.pdf');path.write_bytes(variant)
            case['provenance']['transform_params'].update(acroform_fields_filled=widgets,noninteractive_overlay=widgets==0)
            row=case_result(case,variant,path.name,docs,families);row['acroform_fields_filled']=widgets
        except (ValueError,KeyError) as exc:
            row=evaluate_case(case,CatalogRecognitionResult('NO_MATCH',0,0))
            row.update(provenance=case['provenance'],representation='filled',generation_failed=True,
                generation_error=str(exc),extraction_failed=False,used_ocr=False,acroform_fields_filled=0)
        filled.append(row)
    by={name:summary([r for r in rows if r['representation']==name]) for name,_ in TRANSFORMS}
    ocr=[r for r in rows if r['used_ocr']]
    save('robustness',rows,plan=plan,by_transformation=by,ocr_conditioned=summary(ocr),
        selection_limits='Two available PDF identities per source; no DOCX scan transformations; conditional OCR excludes failures only in its own additional table.')
    save('filled_forms',filled,interactive_forms=sum(r['acroform_fields_filled']>0 for r in filled),
        limits='Actual widgets filled when present; otherwise footer overlay is a weaker filled-content perturbation and is explicitly labelled.')


def unknown_and_historical():
    docs,families=catalog();rows=[];seen=set();blockers=[]
    for name in ['official_documents_v2','official_holdout_v1','official_holdout_v2']:
        manifest,values=cached_texts(name)
        for c in manifest['cases']:
            if c['id'] in {'OH1-033','OH1-047','OH1-055','OH1-063','OH1-098'}:
                ex=values[c['id']];result=recognize_catalog(ex.get('text',''),docs,families,file_sha256=c['sha256'])
                blockers.append(dict(id=c['id'],expected_document=c['document_id'],observed_document=result.document.id if result.document else None,match_type=result.match_type,safe=result.match_type=='NO_MATCH' or bool(result.document and result.document.id==c['document_id'])))
            if c.get('expected_match_type')!='NO_MATCH' or c['sha256'] in seen:continue
            seen.add(c['sha256']);raw=(ROOT/'benchmarks/cache'/(c['sha256']+'.body')).read_bytes()
            case=dict(id=c['id'],group=c['sha256'],category='unknown_official',expected=dict(match_type='NO_MATCH'),representation='official_original',
                provenance=dict(url=c['url'],canonical_sha256=c['sha256'],source=c['source_key'],expected_document=None,expected_family=None,transform_params={},seed=SEED))
            rows.append(case_result(case,raw,c['id']+'.'+c['format'],docs,families))
    save('unknown_official',rows,scope='Frozen official informational resources; out of supported catalog/families. Historical known negatives, not a fresh unseen sample.')
    write(OUT+'historical_five.json',dict(cases=blockers,passed=all(r['safe'] for r in blockers)))


def family_label(d):
    title=normalize_text(d.titolo_ufficiale)
    if d.source_id==15 and 'richiesta di intervento ispettivo' in title:return 10
    if d.source_id==14 and 'reclamo' in title and not any(x in title for x in ['fac simile','trasferimento']):return 11
    if d.source_id==14 and ('esercizio' in title and 'diritti' in title):return 12
    if d.source_id==4 and re_full_model(title,'730'):return 13
    if d.source_id==4 and ('certificazione unica' in title) and not any(x in title for x in ['istruzioni','specifiche','allegato']):return 14
    return None


def re_full_model(title,model):
    import re
    return bool(re.fullmatch(r'(?:modello )?'+model+r'(?: (?:19|20)\d{2})?',title))


def split_identities(items):
    # Shared attachment bytes are indivisible; split cannot leak them.
    groups=defaultdict(list)
    for item in items:groups[item['sha256']].append(item)
    ordered=sorted(groups,key=lambda h:hashlib.sha256((str(SEED)+h).encode()).hexdigest())
    if len(ordered)<2:return [],[i for h in ordered for i in groups[h]]
    held=set(ordered[1::2]);return [i for h in ordered if h not in held for i in groups[h]],[i for h in ordered if h in held for i in groups[h]]


def family_holdout():
    docs,families=catalog();by={d.id:d for d in docs};items={}
    for r in read_bundle()['records']:
        label=family_label(by[r['document_id']])
        if label:
            ex=json.loads((ROOT/'benchmarks/work/fingerprint-text'/(r['canonical_file_sha256']+'.json')).read_text(encoding='utf-8'))
            items[r['document_id']]=dict(document_id=r['document_id'],sha256=r['canonical_file_sha256'],family_id=label,text=ex['text'],url=r['url'],source_id=r['source_id'])
    for name in ['official_documents_v2','official_holdout_v1','official_holdout_v2']:
        manifest,values=cached_texts(name)
        for c in manifest['cases']:
            if c.get('expected_match_type')=='NO_MATCH':continue
            d=by[c['document_id']];label=family_label(d)
            if label:items[d.id]=dict(document_id=d.id,sha256=c['sha256'],family_id=label,text=values[c['id']].get('text',''),url=c['url'],source_id=d.source_id)
    train=[];held=[];rows=[];splits={}
    for f in families:
        a,b=split_identities([i for i in items.values() if i['family_id']==f.id]);train+=a;held+=b
        splits[str(f.id)]=dict(development_identities=[i['document_id'] for i in a],held_out_identities=[i['document_id'] for i in b],evaluable=bool(a) and len(b)>=3)
    for c in held:
        r=recognize_document_family(c['text'],families,known_entities=[d.ente for d in docs])
        result=CatalogRecognitionResult('FAMILY_MATCH' if r.recognized else 'NO_MATCH',0,r.confidence,family=r.family)
        row=evaluate_case(dict(id='FH-'+str(c['document_id']),group='document:'+str(c['document_id']),category='family_identity_holdout',expected=dict(match_type='FAMILY_MATCH',family_id=c['family_id'])),result)
        row.update(source_id=c['source_id'],provenance={k:v for k,v in c.items() if k!='text'},representation='official_original');rows.append(row)
    per={str(f.id):summary([r for r in rows if r['expected']['family_id']==f.id]) for f in families if any(r['expected']['family_id']==f.id for r in rows)}
    metrics=[r['metrics'] for r in per.values()]
    macro={key:sum(m[key]['value'] for m in metrics if m[key]['value'] is not None)/sum(m[key]['value'] is not None for m in metrics) if any(m[key]['value'] is not None for m in metrics) else None for key in ['family_precision','family_recall','family_f1']}
    save('family_identity_holdout',rows,splits=splits,per_family=per,macro=macro,
        families_evaluable=sum(s['evaluable'] for s in splits.values()),families_tested=len(per),
        train_identities=len(train),held_out_identities=len(held),
        pattern_build='Pre-existing verified family phrases unchanged from Round 4; held-out IDs never used to build new family patterns or scored via exact fingerprints.',
        limitations='Retrospective split of previously inspected official identities; insufficient prospective independent family evidence. Families without catalog/file evidence remain unevaluated.')


def main():
    p=argparse.ArgumentParser();p.add_argument('kind',choices=['canonical','robustness','unknown','family']);p.add_argument('--per-source',type=int,default=2);a=p.parse_args()
    {'canonical':canonical,'robustness':lambda:robustness(a.per_source),'unknown':unknown_and_historical,'family':family_holdout}[a.kind]()

if __name__=='__main__':main()
