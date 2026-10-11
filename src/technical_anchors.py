"""Bounded public metadata cache; never retain uploaded text."""
from __future__ import annotations
from dataclasses import asdict
from functools import lru_cache
import hashlib
import json
from pathlib import Path
from src.title_evidence import tokens

PATH=Path(__file__).resolve().parents[1]/'data/recognition_features.json'

@lru_cache(maxsize=1)
def load_features():
    if not PATH.is_file():return ()
    if PATH.is_symlink() or PATH.stat().st_size>512_000:raise ValueError('Feature tecniche oltre i limiti.')
    data=json.loads(PATH.read_text(encoding='utf-8'))
    if data.get('schema_version')!=1 or not isinstance(data.get('features'),list) or len(data['features'])>2000:raise ValueError('Schema feature tecniche non supportato.')
    for f in data['features']:
        if type(f.get('document_id')) is not int or len(f.get('anchor_tokens',[]))!=8 or not all(isinstance(t,str) and t.isascii() and t.isalnum() and 2<len(t)<=40 for t in f['anchor_tokens']):raise ValueError('Anchor tecnico non valido.')
    return tuple(data['features'])

@lru_cache(maxsize=4096)
def fingerprint(document):
    return hashlib.sha256(json.dumps(asdict(document),ensure_ascii=False,sort_keys=True).encode()).hexdigest()

def match_anchors(text,documents,entities):
    available=set(tokens(text[:800]));by_id={d.id:d for d in documents};found=[]
    for f in load_features():
        d=by_id.get(f['document_id'])
        if d is None or d.stato_verifica in {'rifiutato','demo'} or d.ente not in entities:continue
        if set(f['anchor_tokens'])<=available and fingerprint(d)==f['catalog_fingerprint']:found.append(d.id)
    return frozenset(found) if len(found)==1 else frozenset()

@lru_cache(maxsize=1)
def feature_revision():
    load_features()
    return hashlib.sha256(PATH.read_bytes()).hexdigest() if PATH.is_file() else 'none'
