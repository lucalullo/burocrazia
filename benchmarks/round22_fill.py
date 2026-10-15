"""Versioned benchmark-only PDF filling and template validation, no recognition."""
from io import BytesIO
import hashlib,random,re
import numpy as np
import pymupdf as fitz
from pypdf import PdfReader
from benchmarks.round8_fill import fill_acroform

def active_references(raw):
    from pypdf.generic import IndirectObject
    values=set();seen=set();count=0
    def walk(node):
        nonlocal count
        if isinstance(node,IndirectObject):
            key=('indirect',node.idnum,node.generation)
            if key in seen:return
            seen.add(key);node=node.get_object()
        key=('object',id(node))
        if key in seen:return
        seen.add(key);count+=1
        if count>100000:raise ValueError('Active-reference inspection object limit')
        if isinstance(node,dict):
            for name in ['/URI','/JS','/F']:
                value=node.get(name)
                if isinstance(value,IndirectObject):value=value.get_object()
                if isinstance(value,str):values.add((name,value))
            if str(node.get('/S')) in ['/JavaScript','/Launch','/GoToR','/SubmitForm','/ImportData']:values.add(('action',str(node['/S'])))
            for value in node.values():walk(value)
        elif isinstance(node,(list,tuple)):
            for value in node:walk(value)
    reader=PdfReader(BytesIO(raw));walk(reader.trailer['/Root'])
    return values

def form_info(raw):
    reader=PdfReader(BytesIO(raw));tree=reader.get_fields() or {};has_root=bool(reader.trailer['/Root'].get('/AcroForm'))
    with fitz.open(stream=raw,filetype='pdf') as pdf:
        widgets=[dict(page=i,name=w.field_name,value=str(w.field_value or ''),rect=list(w.rect),type=w.field_type) for i,p in enumerate(pdf) for w in (p.widgets() or ())]
    return tree,widgets,has_root or bool(widgets)

def values(variant):
    return [f'NOME: PERSONA FITTIZIA {variant}','CF: ZZZZZZ00A00Z000X',f'INDIRIZZO: VIA FITTIZIA {variant+1}','DATA: 01/02/2030',f'IMPORTO: {100+variant},50','[X] ESEMPIO SINTETICO','TESTO: SOLO DATI FITTIZI']

def blank_index(page,p):
    pix=page.get_pixmap(matrix=fitz.Matrix(1,1),colorspace=fitz.csGRAY,alpha=False)
    mask=(np.frombuffer(pix.samples,dtype=np.uint8).reshape(pix.height,pix.width)<p['blank_min_gray']).astype(np.uint8)
    # Protect even pale/dotted printed glyphs, independently of raster threshold.
    for w in page.get_text('words'):
        x0=max(0,int(w[0]-2-page.rect.x0));y0=max(0,int(w[1]-2-page.rect.y0));x1=min(pix.width,int(w[2]+3-page.rect.x0));y1=min(pix.height,int(w[3]+3-page.rect.y0));mask[y0:y1,x0:x1]=1
    integral=np.pad(mask.astype(np.int64).cumsum(0).cumsum(1),((1,0),(1,0)))
    return integral,pix.width,pix.height

def dark_count(rect,integral,w,h,origin):
    x0=max(0,int(rect.x0-origin.x0));y0=max(0,int(rect.y0-origin.y0));x1=min(w,int(rect.x1-origin.x0)+1);y1=min(h,int(rect.y1-origin.y0)+1)
    return int(integral[y1,x1]-integral[y0,x1]-integral[y1,x0]+integral[y0,x0])

def static_overlay(raw,variant,seed,policy,*,flatten_widgets=False):
    p=policy['static_parameters'];rng=random.Random(seed);placements=[];written=[];indices={};occupied={}
    with fitz.open(stream=raw,filetype='pdf') as pdf:
        if pdf.needs_pass or not 1<=len(pdf)<=100:raise ValueError('PDF encrypted or page limit')
        if flatten_widgets:pdf.bake(annots=False,widgets=True)
        for value in values(variant):
            found=None
            width=fitz.get_text_length(value,fontname=p['font'],fontsize=p['font_size'])+2*p['padding']
            for i,page in enumerate(pdf):
                if i not in indices:indices[i]=blank_index(page,p);occupied[i]=[]
                r=page.rect;start=p['first_page_start_fraction'] if i==0 else p['later_page_start_fraction']
                ys=list(range(int(r.y0+r.height*start),int(r.y0+r.height*p['end_fraction']-p['line_height']),p['y_grid_points']));xs=list(range(int(r.x0+r.width*p['side_margin_fraction']),int(r.x1-r.width*p['side_margin_fraction']-width),p['x_grid_points']));rng.shuffle(ys);rng.shuffle(xs)
                tries=0
                for y in ys:
                    for x in xs:
                        tries+=1
                        if tries>p['max_candidates_per_page_per_value']:break
                        rect=fitz.Rect(x,y,x+width,y+p['line_height']);safe=rect+(-p['padding'],-p['padding'],p['padding'],p['padding'])
                        if not r.contains(safe) or any(safe.intersects(b) for b in occupied[i]):continue
                        if dark_count(safe,*indices[i],r)>p['max_dark_pixels']:continue
                        if page.insert_textbox(rect,value,fontname=p['font'],fontsize=p['font_size'],color=(0,0,.45))<0:raise ValueError('Measured overlay did not fit')
                        occupied[i].append(safe);placements.append(dict(page=i,rect=list(rect),value=value));written.append(value);found=True;break
                    if found or tries>p['max_candidates_per_page_per_value']:break
                if found:break
        if len(written)<p['minimum_verified_values']:raise ValueError('No raster-verified safe overlay value')
        result=pdf.tobytes(garbage=3,deflate=True,no_new_id=True)
    return result,dict(mode='static_overlay',fields_verified=len(written),written_values=written,placements=placements,partial_overlay=len(written)<p['values_target'],flattened_original_widgets=flatten_widgets)

def validate(original,result,audit,*,parser=True):
    if not 0<len(result)<=20*1024*1024:raise ValueError('Generated PDF byte limit')
    if not active_references(result)<=active_references(original):raise ValueError('New external/active reference introduced')
    changed=[];synthetic=False
    if audit['mode']=='acroform_native':
        old,_,_=form_info(original);new,widgets,_=form_info(result)
        for name,field in new.items():
            value=str(field.get('/V',''));prior=str(old.get(name,{}).get('/V',''))
            if value!=prior:
                changed.append(name)
                if re.search(r'FITTIZ|ZZZZZZ|2030|EXAMPLE.INVALID',value,re.I):synthetic=True
                relevant=[w for w in widgets if w['name']==name]
                if not relevant:raise ValueError('Changed field lacks page widget')
                if any(str(w['value']).lstrip('/')!=value.lstrip('/') for w in relevant):raise ValueError('Reopened widget/canonical field mismatch')
        if not changed or not synthetic:raise ValueError('No verified changed synthetic native field')
        audit['changed_field_names']=changed
        with fitz.open(stream=result,filetype='pdf') as pdf:
            for page in pdf:
                for w in page.widgets() or ():
                    if w.field_name in changed:
                        t,v=pdf.xref_get_key(w.xref,'AP/N')
                        if t=='null':raise ValueError('Updated native widget has no appearance')
    render_checks=[]
    with fitz.open(stream=original,filetype='pdf') as before,fitz.open(stream=result,filetype='pdf') as after:
        if after.needs_pass or len(before)!=len(after):raise ValueError('Page count/encryption changed')
        all_text='\n'.join(p.get_text() for p in after)
        if audit['mode']=='static_overlay':
            if not audit['written_values'] or not all(v in all_text for v in audit['written_values']):raise ValueError('Synthetic overlay persistence failed')
            synthetic=True
        for i,(a,b) in enumerate(zip(before,after)):
            if a.rect!=b.rect:raise ValueError('Page geometry changed')
            source_text=a.get_text().strip()
            if source_text and source_text not in b.get_text():raise ValueError('Original template text changed')
            old=a.get_pixmap(matrix=fitz.Matrix(2,2),colorspace=fitz.csGRAY,alpha=False);new=b.get_pixmap(matrix=fitz.Matrix(2,2),colorspace=fitz.csGRAY,alpha=False)
            x=np.frombuffer(old.samples,dtype=np.uint8).reshape(old.height,old.width).astype(np.int16);y=np.frombuffer(new.samples,dtype=np.uint8).reshape(new.height,new.width).astype(np.int16);diff=np.abs(x-y)>8;mask=np.zeros(diff.shape,dtype=bool)
            rects=[fitz.Rect(q['rect']) for q in audit.get('placements',[]) if q['page']==i]
            if audit['mode']=='acroform_native':rects.extend(w.rect for w in b.widgets() or () if w.field_name in changed)
            for r in rects:
                r=r+(-2,-2,2,2);x0=max(0,int((r.x0-a.rect.x0)*2));x1=min(old.width,int((r.x1-a.rect.x0)*2)+1);y0=max(0,int((r.y0-a.rect.y0)*2));y1=min(old.height,int((r.y1-a.rect.y0)*2)+1);mask[y0:y1,x0:x1]=True
            fraction=float(np.count_nonzero(diff&~mask))/max(1,np.count_nonzero(~mask))
            if fraction>.0001:raise ValueError(f'Template pixels changed outside fill rectangles:{fraction}')
            if audit['mode']=='static_overlay':
                for q in audit['placements']:
                    if q['page']==i:
                        r=fitz.Rect(q['rect']);region=diff[max(0,int(r.y0*2)):int(r.y1*2)+1,max(0,int(r.x0*2)):int(r.x1*2)+1]
                        if not np.any(region):raise ValueError('Synthetic overlay text not rendered')
            render_checks.append(dict(page=i+1,outside_changed_pixel_fraction=fraction))
    if parser:
        from src.extract import extract_document
        extract_document(result,'synthetic-filled.pdf')  # parser only; never recognition
    audit.update(reopened=True,synthetic_values_verified=synthetic,template_integrity_ok=True,render_checks=render_checks,external_references_introduced=False,safety_parser_pass=parser,byte_count=len(result),sha256=hashlib.sha256(result).hexdigest())
    return audit

def generate(raw,variant,seed,policy):
    try:tree,widgets,has_acro=form_info(raw)
    except Exception as exc:tree={};widgets=[];has_acro=True;form_error=type(exc).__name__+': '+str(exc)
    else:form_error=None
    errors=[]
    if has_acro:
        try:
            if not tree or not widgets:raise ValueError('Malformed/unsupported AcroForm field tree')
            result,old=fill_acroform(raw,variant);audit=dict(old,mode='acroform_native',fallback_from_acroform=False,seed=seed,variant=variant)
            return result,validate(raw,result,audit)
        except Exception as exc:errors.append(type(exc).__name__+': '+str(exc))
    result,audit=static_overlay(raw,variant,seed,policy,flatten_widgets=has_acro)
    audit.update(seed=seed,variant=variant,fallback_from_acroform=has_acro,native_failure=errors or ([form_error] if form_error else []))
    return result,validate(raw,result,audit)
