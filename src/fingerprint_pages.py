"""Bounded request-local page evidence, lazy rendering, no persistent upload cache."""
from dataclasses import dataclass,field
from contextlib import closing
from pathlib import Path
from PIL import Image,ImageOps
import hashlib
from src.fingerprint_v3 import features

def image_signature(image):
    out=[]
    for angle in (0,90,180,270):
        with image.rotate(angle,expand=True) as rotated,ImageOps.grayscale(rotated) as gray:
            w,h=gray.size
            boxes=[(0,0,w,h),(w*.06,h*.06,w*.94,h*.94),*( (x*w/2,y*h/2,(x+1)*w/2,(y+1)*h/2) for y in (0,1) for x in (0,1))]
            for box in boxes:
                with gray.crop(box) as crop,crop.resize((9,8),Image.Resampling.LANCZOS) as small:
                    pixels=list(small.getdata());bits=0
                    for y in range(8):
                        for x in range(8):bits=(bits<<1)|int(pixels[y*9+x]>pixels[y*9+x+1])
                    out.append(format(bits,'016x'))
    return tuple(out)

def field_signature(names):return tuple(sorted({hashlib.blake2b(str(n).encode(),digest_size=8,person=b'BurOCRazia-field').hexdigest() for n in names}))

def classify(filename,extraction,*,has_fields=False,filled=False):
    suffix=Path(filename).suffix.lower()
    if suffix=='.docx':return 'docx'
    if suffix in ['.png','.jpg','.jpeg']:return 'image'
    if suffix=='.pdf':
        if has_fields and filled:return 'filled_acroform'
        return 'scanned_pdf' if extraction.used_ocr else 'digital_pdf'
    return 'unknown'

@dataclass
class RequestPages:
    texts:tuple[str,...]
    representation:str='unknown'
    field_set:tuple[str,...]=()
    numbers:tuple[int,...]=()
    raw:bytes=field(default=b'',repr=False)
    filename:str=''
    _queries:tuple=field(default=(),repr=False)
    _visuals:dict=field(default_factory=dict,repr=False)
    counters:dict=field(default_factory=dict)
    _memo:dict=field(default_factory=dict,repr=False)

    def memo(self,key,factory):
        if key not in self._memo:self._memo[key]=factory()
        return self._memo[key]

    def queries(self):
        if not self._queries:self._queries=tuple(features(t) for t in self.texts[:5])
        return self._queries

    def visual(self,page=0):
        if page in self._visuals:return self._visuals[page]
        if not self.raw:return ()
        import time
        start=time.perf_counter()
        from src.extract import _read_bytes,_pdf_page_image,MAX_PDF_PAGES,ExtractionError
        raw=_read_bytes(self.raw);suffix=Path(self.filename).suffix.lower()
        if suffix=='.pdf':
            import fitz
            with fitz.open(stream=raw,filetype='pdf') as pdf:
                if pdf.needs_pass or not 1<=len(pdf)<=MAX_PDF_PAGES:raise ExtractionError('PDF oltre i limiti.')
                number=self.numbers[page]-1 if self.numbers else page
                if not 0<=number<len(pdf):return ()
                with closing(_pdf_page_image(pdf[number])) as im:value=image_signature(im)
        elif suffix in ['.png','.jpg','.jpeg']:
            from src.ocr import load_image
            with closing(load_image(raw)) as im:value=image_signature(im)
        else:value=()
        self._visuals[page]=value;self.counters['page_renders']=self.counters.get('page_renders',0)+1
        self.counters['visual_ms']=self.counters.get('visual_ms',0)+(time.perf_counter()-start)*1000
        return value

def _prepare(raw,filename,extraction):
    from src.extract import _read_bytes,MAX_PDF_PAGES,ExtractionError
    raw=_read_bytes(raw);names=[];filled=False
    if Path(filename).suffix.lower()=='.pdf':
        import fitz
        with fitz.open(stream=raw,filetype='pdf') as pdf:
            if pdf.needs_pass or not 1<=len(pdf)<=MAX_PDF_PAGES:raise ExtractionError('PDF oltre i limiti.')
            for page in pdf:
                for w in page.widgets() or ():
                    if len(names)>=512:break
                    if w.field_name:names.append(w.field_name)
                    filled=filled or (w.field_type==fitz.PDF_WIDGET_TYPE_TEXT and bool(w.field_value))
    texts=getattr(extraction,'page_texts',()) or (extraction.text,)
    numbers=getattr(extraction,'page_numbers',()) or tuple(range(1,len(texts)+1))
    return RequestPages(tuple(texts[:5]),classify(filename,extraction,has_fields=bool(names),filled=filled),field_signature(names),tuple(numbers[:5]),raw,filename)

def prepare(raw,filename,extraction):
    from src.extract import ExtractionError
    try:return _prepare(raw,filename,extraction)
    except (ValueError,RuntimeError,OSError) as exc:
        raise ExtractionError('Impossibile leggere la struttura del documento.') from exc
