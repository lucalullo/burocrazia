"""Seven historical OCR gates with a real Tesseract executable, no mocks."""
from __future__ import annotations
from dataclasses import asdict
import argparse
from datetime import UTC, datetime
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import fitz
from PIL import Image
from rapidfuzz.fuzz import ratio
from benchmarks.files import generate_synthetic
from src.extract import extract_document, ExtractionError
from src import ocr
from src.recognize import normalize_text

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'benchmarks/results/round3/ocr_legacy_gate.json')
    args=parser.parse_args()
    command=os.environ.get(ocr.TESSERACT_COMMAND_ENV,'tesseract')
    version=subprocess.check_output([command,'--version'],text=True).splitlines()[0]
    languages=subprocess.check_output([command,'--list-langs'],text=True).splitlines()[1:]
    work=ROOT/'benchmarks/work/ocr-temp';work.mkdir(parents=True,exist_ok=True)
    previous=tempfile.tempdir;tempfile.tempdir=str(work)
    before=set(work.iterdir());rows=[]
    fixture=json.loads((ROOT/'benchmarks/corpora/ocr_synthetic_v1.json').read_text(encoding='utf-8'))['cases'][0]
    try:
        for angle in [0,90,180,270]:
            start=time.perf_counter();raw=generate_synthetic(dict(fixture,transform={'angle':angle}))
            try:
                result=ocr.ocr_image_bytes(raw)
                similarity=ratio(normalize_text(fixture['text']),normalize_text(result.text))/100
                passed='inps demo 01' in normalize_text(result.text) and similarity>=.9
                rows.append(dict(id=f'orientation_{angle}',passed=passed,similarity=similarity,rotation=result.rotation,seconds=time.perf_counter()-start))
            except ocr.OCRError as exc:rows.append(dict(id=f'orientation_{angle}',passed=False,error=str(exc)))
        doc=fitz.open();doc.new_page();raw=doc.tobytes();doc.close()
        try:extract_document(raw,'blank.pdf');rows.append(dict(id='blank_pdf',passed=False))
        except ExtractionError as exc:rows.append(dict(id='blank_pdf',passed=True,error=str(exc)))
        raw=generate_synthetic(fixture)
        with Image.open(io.BytesIO(raw)) as image:
            try:ocr._LocalTesseractBackend(command)._read_image(image,lang='ita',timeout=.2);rows.append(dict(id='native_timeout',passed=False))
            except ocr.OCRTimeoutError:rows.append(dict(id='native_timeout',passed=True,timeout_seconds=.2))
        doc=fitz.open();page=doc.new_page();page.insert_text((50,100),fixture['text'],fontsize=14);raw=doc.tobytes();doc.close()
        result=extract_document(raw,'digital.pdf')
        rows.append(dict(id='digital_pdf_bypass',passed=not result.used_ocr and 'INPS' in result.text,used_ocr=result.used_ocr))
    finally:tempfile.tempdir=previous
    residue=[p.name for p in set(work.iterdir())-before]
    report=dict(schema_version=1,executed_at=datetime.now(UTC).isoformat(),real_tesseract=True,mocked=False,version=version,languages=languages,cases=rows,passed=sum(r['passed'] for r in rows),total=7,temporary_residue=residue,
        full_gate_passed=len(rows)==7 and all(r['passed'] for r in rows) and not residue and {'ita','eng','osd'}.issubset(languages),
        traineddata_sha256={lang:hashlib.sha256(p.read_bytes()).hexdigest() for lang in ['ita','eng','osd'] for p in [Path(command).parent/'tessdata'/(lang+'.traineddata')] if p.is_file()})
    path=args.output;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return int(not report['full_gate_passed'])

if __name__=='__main__':raise SystemExit(main())
