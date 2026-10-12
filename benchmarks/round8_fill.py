"""Verified synthetic form perturbations, separate from recognition outcomes."""
from io import BytesIO
import random,re

def pdf_state(value):
    from urllib.parse import unquote_to_bytes
    value=str(value or 'Off').lstrip('/')
    raw=unquote_to_bytes(re.sub(r'#([0-9a-fA-F]{2})',r'%\1',value))
    try:return raw.decode('utf8')
    except UnicodeDecodeError:return raw.decode('latin1')

def synthetic(label,variant,maxlen=0):
    label=label.casefold()
    if re.search(r'fiscal|codice.?fisc|\bcf\b',label):value='ZZZZZZ00A00Z000X'
    elif re.search(r'\b(?:data|date)\b|(?:nato|deceduto).{0,12}\bil\b|gg/mm/aaaa',label):value=f'{variant%27+1:02}/02/2030'
    elif re.search(r'\b(?:importo|euro|somma|totale)\b',label):value=f'{100+variant},50'
    elif re.search(r'telefon|cellular|recapito',label):value='0000000000'
    elif re.search(r'mail|\bpec\b',label):value=f'fittizio{variant}@example.invalid'
    elif re.search(r'\b(?:indirizzo|via|domicilio)\b',label):value=f'Via Fittizia {variant+1}'
    elif re.search(r'\b(?:cap)\b',label):value='00000'
    else:value=f'FITTIZIO {variant}'
    if 0<maxlen<4:return 'Z'*maxlen
    return value[:maxlen] if maxlen else value

def fill_acroform(raw,variant):
    import fitz
    from pypdf import PdfReader,PdfWriter
    from pypdf.generic import NameObject
    original=PdfReader(BytesIO(raw));tree=original.get_fields() or {}
    if not tree:raise ValueError('No canonical AcroForm fields')
    values={};expected={}
    with fitz.open(stream=raw,filetype='pdf') as pdf:
        for page in pdf:
            widgets=list(page.widgets() or ());words=page.get_text('words');dates={}
            textwidgets=[w for w in widgets if w.field_type==fitz.PDF_WIDGET_TYPE_TEXT]
            for first in textwidgets:
                row=sorted([w for w in textwidgets if abs(w.rect.y0-first.rect.y0)<3],key=lambda w:w.rect.x0)
                for i in range(len(row)-2):
                    triple=row[i:i+3]
                    if not (all(w.rect.width<=36 for w in triple[:2]) and triple[2].rect.width<=75 and triple[2].rect.width>=triple[0].rect.width and all(0<=triple[j+1].rect.x0-triple[j].rect.x1<=15 for j in [0,1])):continue
                    left=' '.join(word[4] for word in words if word[2]<=triple[0].rect.x0+2 and word[0]>=triple[0].rect.x0-220 and abs((word[1]+word[3])/2-(first.rect.y0+first.rect.y1)/2)<7)
                    if re.search(r'data|date|presentata|decorrenza|\bdal\b|\bal\b|sottoscrizione',left,re.I):
                        for w,value in zip(triple,[f'{variant%27+1:02}','02','2030']):dates[w.field_name]=value
            for w in widgets:
                if not w.field_name or w.field_name not in tree:raise ValueError('Orphan/ambiguous field; static method required')
                if w.field_flags&1:continue
                if w.field_type==fitz.PDF_WIDGET_TYPE_TEXT:
                    # Only a narrow immediate label window: no date inherited
                    # from an earlier line into a name/address field.
                    candidates=[word for word in words if word[2]<=w.rect.x0+2 and word[0]>=w.rect.x0-130 and abs((word[1]+word[3])/2-(w.rect.y0+w.rect.y1)/2)<6]
                    nearby=' '.join(word[4] for word in sorted(candidates,key=lambda a:a[0])[-3:])
                    meaningful=r'fiscal|\bcf\b|\bnome\b|cognome|denominazione|ragione.sociale|data|date|nato|deceduto|indirizzo|via\b|domicilio|telefon|cellular|mail|\bpec\b|importo|euro|\bcap\b|motivo|descrizione|note|testo.libero'
                    label=nearby if re.search(meaningful,nearby,re.I) else w.field_name
                    if w.field_name in dates:value=dates[w.field_name]
                    elif not re.search(meaningful,label,re.I):continue
                    else:value=synthetic(label,variant,w.text_maxlen)
                    # Short text fits small boxes; dates use only digit segments
                    # when the actual field has an explicit short max length.
                    fit=max(1,int(w.rect.width/3.5))
                    if len(value)>fit and w.field_name not in dates:
                        # Skip rather than truncate a CF, email or full date.
                        if re.search(r'fiscal|\bcf\b|data|date|mail|pec',label,re.I):continue
                        value=value[:fit]
                    values[w.field_name]=value;expected[w.field_name]=value
                elif w.field_type==fitz.PDF_WIDGET_TYPE_CHECKBOX:
                    states=tree[w.field_name].get('/_States_',[])
                    on=[str(v).lstrip('/') for v in states if str(v) not in ['Off','/Off']]
                    if on:
                        value=('/'+on[0].lstrip('/')) if variant%2 else '/Off'
                        values[w.field_name]=NameObject(value);expected[w.field_name]=value
    if not values:raise ValueError('No editable supported fields')
    if not any(not isinstance(value,NameObject) and bool(value) for value in values.values()):
        raise ValueError('No synthetic text value in editable fields; static perturbation required')
    writer=PdfWriter();writer.clone_document_from_reader(original)
    # Each field uses its original font resource. Font size zero asks pypdf for
    # automatic bounded fitting; original layout and field labels are retained.
    for page in writer.pages:
        for ref in page.get('/Annots',[]):
            obj=ref.get_object();parent=obj.get('/Parent');parent=parent.get_object() if parent else obj
            name=str(obj.get('/T') or parent.get('/T'))
            da=obj.get('/DA') or parent.get('/DA')
            if name in values and (obj.get('/FT') or parent.get('/FT'))=='/Tx' and da:
                obj[NameObject('/DA')]=__import__('pypdf.generic',fromlist=['TextStringObject']).TextStringObject(re.sub(r'[\d.]+\s+Tf','0 Tf',str(da)))
    writer.update_page_form_field_values(None,values,auto_regenerate=False)
    out=BytesIO();writer.write(out);result=out.getvalue();check=PdfReader(BytesIO(result));actual=check.get_fields() or {}
    for name,value in expected.items():
        if name not in actual or str(actual[name].get('/V'))!=str(value):raise ValueError('Canonical field persistence failed')
    checked=0
    with fitz.open(stream=result,filetype='pdf') as pdf:
        for page in pdf:
            for w in page.widgets() or ():
                if w.field_name not in expected:continue
                target=pdf_state(expected[w.field_name]);observed=pdf_state(w.field_value)
                if target!=observed:raise ValueError('Widget persistence failed')
                checked+=1
    for page in check.pages:
        for ref in page.get('/Annots',[]):
            obj=ref.get_object();parent=obj.get('/Parent')
            parent=parent.get_object() if parent else {}
            name=obj.get('/T') or parent.get('/T')
            if str(name) in expected and not obj.get('/AP',{}).get('/N'):raise ValueError('Missing updated appearance')
    if checked<len(expected):raise ValueError('Updated fields missing widgets')
    return result,dict(acroform_static='acroform',generation_method='real_fields_pypdf_persisted',fields_verified=len(expected),reopened=True,synthetic_verified=True)

def fill_static(raw,variant):
    import fitz
    rng=random.Random(2026101208+variant);values=[f'NOME: PERSONA FITTIZIA {variant}', 'CF: ZZZZZZ00A00Z000X',f'INDIRIZZO: VIA FITTIZIA {variant+1}', 'DATA: 01/02/2030',f'IMPORTO: {100+variant},50', '[X] ESEMPIO SINTETICO', 'TESTO: SOLO DATI FITTIZI']
    with fitz.open(stream=raw,filetype='pdf') as pdf:
        if pdf.needs_pass or not 1<=len(pdf)<=100:raise ValueError('PDF limits')
        if any(list(p.widgets() or ()) for p in pdf):pdf.bake(annots=False,widgets=True)
        page=pdf[0];occupied=[fitz.Rect(w[:4])+(-2,-2,2,2) for w in page.get_text('words')];written=[]
        # Avoid table rules and other visible artwork as well as printed words.
        for drawing in page.get_drawings():
            for item in drawing['items']:
                if item[0]=='l':occupied.append(fitz.Rect(item[1],item[2]).normalize()+(-1,-1,1,1))
                elif item[0]=='re':
                    r=item[1]
                    occupied.extend([fitz.Rect(r.x0-1,r.y0-1,r.x1+1,r.y0+1),fitz.Rect(r.x0-1,r.y1-1,r.x1+1,r.y1+1),fitz.Rect(r.x0-1,r.y0-1,r.x0+1,r.y1+1),fitz.Rect(r.x1-1,r.y0-1,r.x1+1,r.y1+1)])
        xs=[page.rect.width*.08,page.rect.width*.52];ys=list(range(int(page.rect.height*.34),int(page.rect.height*.93),17));rng.shuffle(ys)
        for value in values:
            candidates=[fitz.Rect(x,y,x+min(245,page.rect.width*.39),y+12) for y in ys for x in xs]
            rect=next((r for r in candidates if page.rect.contains(r) and not any(r.intersects(b) for b in occupied)),None)
            if rect is None:raise ValueError('No safe blank overlay rectangle')
            if page.insert_textbox(rect,value,fontsize=6.5,fontname='helv',color=(0,0,.45))<0:raise ValueError('Overlay text does not fit')
            occupied.append(rect);written.append(value)
        result=pdf.tobytes(garbage=3,deflate=True)
    with fitz.open(stream=result,filetype='pdf') as check:
        text=check[0].get_text()
        if not all(value in text for value in written):raise ValueError('Synthetic overlay persistence failed')
        if any(list(p.widgets() or ()) for p in check):raise ValueError('Static output retained interactive widgets')
    return result,dict(acroform_static='static',generation_method='seeded_blank_rectangles_overlay',fields_verified=len(written),reopened=True,synthetic_verified=True)

def generate(raw,filename,variant):
    if filename.endswith('.docx'):
        from docx import Document
        d=Document(BytesIO(raw));count=0;expected=[]
        paras=list(d.paragraphs)+[p for table in d.tables for row in table.rows for cell in row.cells for p in cell.paragraphs]
        for pi,p in enumerate(paras):
            for ri,run in enumerate(p.runs):
                changed,n=re.subn(r'_{4,}|\.{6,}',lambda m:synthetic('testo',variant,min(len(m[0]),16)),run.text)
                if n:run.text=changed;count+=n;expected.append((pi,ri,changed))
        if not count:raise ValueError('No editable DOCX placeholders')
        out=BytesIO();d.save(out);result=out.getvalue();check=Document(BytesIO(result))
        reopened=list(check.paragraphs)+[p for table in check.tables for row in table.rows for cell in row.cells for p in cell.paragraphs]
        if any(pi>=len(reopened) or ri>=len(reopened[pi].runs) or reopened[pi].runs[ri].text!=value for pi,ri,value in expected):raise ValueError('DOCX synthetic placeholder persistence failed')
        return result,dict(acroform_static='static',generation_method='docx_placeholders_only',fields_verified=count,reopened=True,synthetic_verified=True)
    try:return fill_acroform(raw,variant)
    except (ValueError,RuntimeError,KeyError,TypeError,AttributeError) as exc:
        result,audit=fill_static(raw,variant);audit['acroform_fallback_reason']=type(exc).__name__+': '+str(exc);return result,audit
