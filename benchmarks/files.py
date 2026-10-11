"""Real extraction/OCR runners. Official files remain in an ignored cache."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import UTC, datetime
import hashlib
import io
import json
from pathlib import Path
import platform
import shutil
import sqlite3
import subprocess
import time

import fitz
from PIL import Image, ImageEnhance, ImageFilter
from benchmarks.evaluate import summary, code_hash
from maintenance.fetch import Fetcher
from scripts.benchmark import evaluate_case
from src.database import list_documents
from src.families import list_document_families
from src.extract import extract_document, ExtractionError
from src.recognize import recognize_catalog, catalog_revision, RULES_VERSION
from src.ocr import TESSERACT_COMMAND_ENV
import os

ROOT=Path(__file__).resolve().parents[1]


def generate_synthetic(case):
    doc=fitz.open();page=doc.new_page(width=595,height=842)
    page.insert_textbox(fitz.Rect(50,70,545,750),case['text'],fontsize=18,fontname='helv')
    pix=page.get_pixmap(matrix=fitz.Matrix(2,2));im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples);doc.close()
    transform=case['transform']
    im=im.rotate(transform.get('angle',0),expand=True,fillcolor='white')
    if transform.get('contrast'): im=ImageEnhance.Contrast(im).enhance(transform['contrast'])
    if transform.get('blur'): im=im.filter(ImageFilter.GaussianBlur(transform['blur']))
    if transform.get('scale'): im=im.resize((int(im.width*transform['scale']),int(im.height*transform['scale'])))
    if transform.get('crop'): im=im.crop((20,20,im.width-20,im.height-20))
    fmt=case['format'];out=io.BytesIO()
    im.save(out,format=fmt,**({'quality':35} if fmt=='JPEG' else {}))
    im.close();return out.getvalue()


def run(kind,catalog,output,allow_network=False):
    manifest_path=ROOT/('benchmarks/corpora/ocr_synthetic_v1.json' if kind=='ocr' else 'benchmarks/manifests/official_documents_v1.json')
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    with sqlite3.connect(catalog.resolve().as_uri()+'?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row;documents=list_documents(db);families=list_document_families(db)
    fetcher=Fetcher(ROOT/'benchmarks/cache',allow_network=allow_network,use_cache=True)
    rows=[];attempts=[];work=ROOT/'benchmarks/work';work.mkdir(parents=True,exist_ok=True)
    command=os.environ.get(TESSERACT_COMMAND_ENV) or 'tesseract'
    available=shutil.which(command) or (str(Path(command)) if Path(command).is_file() else None)
    for item in manifest['cases']:
        start=time.perf_counter();receipt=None
        case=dict(id=item['id'],group='document:'+str(item['document_id']),category=kind,source=item['entity'],noise=item.get('noise','official_original'),
                  expected=dict(match_type='DOCUMENT_MATCH',document_id=item['document_id'],entity=item['entity'],version=item.get('version')))
        try:
            if kind=='ocr':
                raw=generate_synthetic(item);filename=item['id']+'.'+{'PDF':'pdf','PNG':'png','JPEG':'jpg'}[item['format']]
                (work/filename).write_bytes(raw)
                if not available:
                    attempts.append(dict(id=item['id'],status='not_run',reason='Tesseract locale non disponibile',input_sha256=hashlib.sha256(raw).hexdigest()));continue
            else:
                receipt=fetcher.fetch(item['url'],item['source_key']);raw=fetcher.read(receipt);filename=item['id']+'.pdf'
                if item.get('sha256') and hashlib.sha256(raw).hexdigest()!=item['sha256']:
                    raise ValueError('Hash ufficiale differente dal manifest congelato; nuova versione richiesta.')
            acquisition_ms=(time.perf_counter()-start)*1000
            begin_extraction=time.perf_counter()
            extracted=extract_document(raw,filename)
            extraction_ms=(time.perf_counter()-begin_extraction)*1000
            begin=time.perf_counter();result=recognize_catalog(extracted.text,documents,families)
            row=evaluate_case(case,result,(time.perf_counter()-begin)*1000)
            row.update(source=item['entity'],noise=case['noise'],extraction_ms=round(extraction_ms,3),used_ocr=extracted.used_ocr,
                       acquisition_or_generation_ms=round(acquisition_ms,3),
                       extracted_characters=len(extracted.text),input_sha256=hashlib.sha256(raw).hexdigest(),receipt=asdict(receipt) if receipt else None)
            rows.append(row);attempts.append(dict(id=item['id'],status='executed'))
        except (ValueError,OSError,ExtractionError) as exc:
            attempts.append(dict(id=item['id'],status='failed',reason=str(exc),receipt=asdict(receipt) if receipt else None))
    report=dict(schema_version=1,corpus_id=manifest['corpus_id'],synthetic=kind=='ocr',executed_at=datetime.now(UTC).isoformat(),
        status='executed' if len(rows)==len(manifest['cases']) else 'partial' if rows else 'not_run',attempts=attempts,cases=rows,summary=summary(rows),
        identity=dict(corpus_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),catalog_semantic_sha256=catalog_revision(documents,families),code_sha256=code_hash(),rules_version=RULES_VERSION,
                      git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),catalog_file_sha256=hashlib.sha256(catalog.read_bytes()).hexdigest()),
        environment=dict(python=platform.python_version(),system=platform.system(),tesseract_executable=available,pillow=Image.__version__,pymupdf=fitz.VersionBind),
        limits='Campione di convenienza; nessun testo estratto conservato. Errori di acquisizione/estrazione esclusi dalle metriche di matching e riportati negli attempts.')
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(kind,report['status'],len(rows),'/',len(manifest['cases']),flush=True)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('kind',choices=['ocr','official']);p.add_argument('--allow-network',action='store_true')
    p.add_argument('--catalog',type=Path,default=ROOT/'data/catalog_seed.sqlite3');p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=run(a.kind,a.catalog,a.output,a.allow_network)
    return int(r['status']!='executed' or r['summary']['failed']>0)

if __name__=='__main__':raise SystemExit(main())
