"""Fresh deterministic synthetic inputs; no recognizer is imported here."""
from io import BytesIO
import hashlib,random,zipfile

def derivative(raw,ext,normalized=False):
    if ext=='.pdf':
        import pymupdf
        with pymupdf.open(stream=raw,filetype='pdf') as source:
            if normalized:
                # Flatten actual interactive appearances and rewrite streams.
                source.bake(annots=False,widgets=True)
                return source.tobytes(garbage=4,deflate=True,clean=True,no_new_id=True),ext
            with pymupdf.open() as target:
                target.insert_pdf(source,widgets=True)
                return target.tobytes(garbage=2,deflate=True,no_new_id=True),ext
    from lxml import etree
    with zipfile.ZipFile(BytesIO(raw)) as original:
        out=BytesIO()
        with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as target:
            for name in sorted(original.namelist()):
                data=original.read(name)
                if name.endswith('.xml'):
                    parser=etree.XMLParser(resolve_entities=False,no_network=True)
                    node=etree.fromstring(data,parser)
                    data=etree.tostring(node,method='c14n') if normalized else etree.tostring(node,xml_declaration=True,encoding='UTF-8',pretty_print=True)
                info=zipfile.ZipInfo(name,date_time=(2026,10,14,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
                target.writestr(info,data)
        return out.getvalue(),ext

def scan(raw,params,seed):
    from benchmarks.round8_evaluation import transformed
    from PIL import Image
    base={k:v for k,v in params.items() if k not in ['noise_fraction','noise_amplitude','noise_seed']}
    # first_page_only is an actual raster first-page sample in this round.
    if base.pop('first_page_only',False):base['dpi']=150
    value,ext=transformed(raw,base)
    with Image.open(BytesIO(value)) as original:
        im=original.convert('L' if params.get('gray') else 'RGB')
        rng=random.Random(seed);pix=im.load()
        for _ in range(max(1,int(im.width*im.height*params['noise_fraction']))):
            x,y=rng.randrange(im.width),rng.randrange(im.height);v=pix[x,y]
            delta=rng.choice([-params['noise_amplitude'],params['noise_amplitude']])
            pix[x,y]=max(0,min(255,v+delta)) if isinstance(v,int) else tuple(max(0,min(255,c+delta)) for c in v)
        result=BytesIO();im.save(result,format='JPEG' if ext=='.jpg' else 'PNG',**({'quality':params['quality']} if ext=='.jpg' else {}))
        im.close();return result.getvalue(),ext

def reopened(raw,ext):
    assert len(raw)<=20*1024*1024
    if ext=='.pdf':
        import pymupdf
        with pymupdf.open(stream=raw,filetype='pdf') as pdf:assert not pdf.needs_pass and 1<=len(pdf)<=100
    elif ext=='.docx':
        from docx import Document
        Document(BytesIO(raw))
    else:
        from PIL import Image
        with Image.open(BytesIO(raw)) as image:assert image.width*image.height<=40_000_000;image.verify()

def seed_for(seed,did,name):return int(hashlib.sha256(f'{seed}:{did}:{name}'.encode()).hexdigest()[:16],16)
