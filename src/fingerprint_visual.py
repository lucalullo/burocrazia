"""Bounded local visual signatures; never retain upload pixels or hashes."""
from contextlib import closing
from io import BytesIO
from pathlib import Path
from PIL import Image,ImageOps

def image_signature(image):
    result=[]
    for angle in (0,90,180,270):
        with image.rotate(angle,expand=True) as rotated:
            with ImageOps.grayscale(rotated) as gray:
                with gray.resize((17,16),Image.Resampling.LANCZOS) as small:
                    p=list(small.getdata());bits=0
                    for y in range(16):
                        for x in range(16):bits=(bits<<1)|int(p[y*17+x]>p[y*17+x+1])
                    result.append(format(bits,'064x'))
    return tuple(result)

def first_page_image(raw,filename):
    from src.extract import _read_bytes,_pdf_page_image,MAX_PDF_PAGES,ExtractionError
    raw=_read_bytes(raw);suffix=Path(filename).suffix.lower()
    if suffix=='.pdf':
        import fitz
        with fitz.open(stream=raw,filetype='pdf') as pdf:
            if pdf.needs_pass or not 1<=len(pdf)<=MAX_PDF_PAGES:raise ExtractionError('PDF oltre i limiti.')
            return _pdf_page_image(pdf[0])
    if suffix in ['.jpg','.jpeg','.png']:
        from src.ocr import load_image
        return load_image(raw)
    return None

def visual_for_bytes(raw,filename):
    from src.extract import ExtractionError
    try:
        im=first_page_image(raw,filename)
        if im is None:return ()
        with closing(im):return image_signature(im)
    except (ValueError,RuntimeError,OSError,ExtractionError):return ()
