"""Offline Round 4 evidence helpers; full extracted text stays ignored."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from benchmarks.round3_audit import ROOT,catalog,read,write
from maintenance.fetch import Fetcher,Fetched
from src.extract import extract_document,ExtractionError

OUT='benchmarks/results/round4/'

def texts(manifest_name,only=None):
    manifest=read('benchmarks/manifests/'+manifest_name+'.json')
    cache=ROOT/'benchmarks/work'/('round4-'+manifest_name+'-text.json')
    values=json.loads(cache.read_text(encoding='utf-8')) if cache.exists() else {}
    fetcher=Fetcher(ROOT/'benchmarks/cache',use_cache=True)
    for c in manifest['cases']:
        if c['id'] in values or (only and c['id'] not in only):continue
        try:
            receipt=Fetched(**c['receipt']) if 'receipt' in c else fetcher.fetch(c['url'],c['source_key'])
            raw=fetcher.read(receipt);assert hashlib.sha256(raw).hexdigest()==c['sha256']
            values[c['id']]=asdict(extract_document(raw,c['id']+'.'+c['format']))
        except (ValueError,OSError,ExtractionError) as exc:values[c['id']]=dict(text='',extraction_failed=True,error=str(exc))
        cache.parent.mkdir(parents=True,exist_ok=True)
        cache.write_text(json.dumps(values,ensure_ascii=False),encoding='utf-8')
    return manifest,values

def runtime_hash():
    files=sorted([*ROOT.glob('src/**/*.py'),*ROOT.glob('data/recognition_profiles/*.json'),ROOT/'app.py',ROOT/'run.py',ROOT/'data/recognition_features.json'])
    return hashlib.sha256(b''.join(p.relative_to(ROOT).as_posix().encode()+b'\0'+p.read_bytes()+b'\0' for p in files)).hexdigest()
