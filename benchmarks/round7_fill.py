"""Synthetic AcroForm perturbations with logical and widget verification."""
from io import BytesIO
import re


def field_value(label,variant):
    label=label.casefold()
    if re.search(r'\b(data|date|nato|nascita)\b',label):return f'{variant+1:02}/02/2030'
    if re.search(r'fiscal|\bcf\b',label):return 'ZZZZZZ00A00Z000X'
    if re.search(r'import|euro|somma|totale',label):return f'{1234+variant},50'
    if re.search(r'indirizz|via|residen|domicil',label):return f'Via Fittizia {17+variant}'
    if re.search(r'cognome|denominazione',label):return f'Esempio {variant}'
    if re.search(r'\bnome\b',label):return f'Persona {variant}'
    if re.search(r'\bcap\b',label):return '00100'
    if re.search(r'telefon|cellular',label):return '0000000000'
    if re.search(r'email|e-mail',label):return f'esempio{variant}@example.invalid'
    return f'Esempio {variant}'


def fill_acroform(raw,variant):
    from pypdf import PdfReader,PdfWriter
    import fitz
    reader=PdfReader(BytesIO(raw));tree=reader.get_fields() or {};values={}
    with fitz.open(stream=raw,filetype='pdf') as pdf:
        for page in pdf:
            for w in page.widgets() or ():
                if w.field_name not in tree:raise ValueError('Ambiguous/orphan field')
                if w.field_flags & 1:continue
                if w.field_type==fitz.PDF_WIDGET_TYPE_TEXT:
                    # Generic field names also get their immediate printed label.
                    rect=w.rect
                    nearby=' '.join(word[4] for word in page.get_text('words') if word[0]>=rect.x0-160 and word[2]<=rect.x0+3 and word[1]<rect.y1 and word[3]>rect.y0-5)
                    label=w.field_name+' '+nearby
                    value=field_value(label,variant)
                    values[w.field_name]=value[:w.text_maxlen] if w.text_maxlen>0 else value
                elif w.field_type==fitz.PDF_WIDGET_TYPE_CHECKBOX:
                    values[w.field_name]=w.on_state() if variant%2==0 else '/Off'
    if not values:return raw,0
    writer=PdfWriter();writer.clone_document_from_reader(reader)
    writer.update_page_form_field_values(None,values,auto_regenerate=False)
    output=BytesIO();writer.write(output);result=output.getvalue();check=PdfReader(BytesIO(result));actual=check.get_fields() or {}
    for name,value in values.items():
        if name not in actual or str(actual[name].get('/V'))!=str(value):raise ValueError('Canonical /V mismatch')
    with fitz.open(stream=result,filetype='pdf') as pdf:
        for page in pdf:
            for w in page.widgets() or ():
                if w.field_name in values and str(w.field_value)!=str(values[w.field_name]).lstrip('/'):
                    raise ValueError('Widget /V mismatch')
    for page in check.pages:
        for ref in page.get('/Annots',[]):
            obj=ref.get_object()
            if obj.get('/Subtype')=='/Widget' and not obj.get('/AP',{}).get('/N'):raise ValueError('Missing appearance')
    return result,len(values)
