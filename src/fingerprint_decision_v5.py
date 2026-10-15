"""Version 5: metadata uniqueness cannot establish a missing decimal revision.

Strong page fingerprints retain the calibrated two-channel/identity/margin rules.
The metadata fallback requires observed revision evidence in recognize.py.
All entity, explicit version, stale binding and shared resource vetoes remain.
"""
import hashlib,json,math
from functools import lru_cache
from pathlib import Path
from src.fingerprint_decision_v4 import DEFAULT,SETTINGS,match as fuse
VERSION='fingerprint-decision-v5'
PATH=Path(__file__).resolve().parents[1]/'data/recognition_profiles/fingerprint_decision_v5.json'

@lru_cache(maxsize=1)
def profile():
    if PATH.is_symlink() or PATH.stat().st_size>64000:raise ValueError('Profilo v5 non sicuro.')
    p=json.loads(PATH.read_bytes());t=p['thresholds'];s=p['settings']
    if p['rules_version']!=VERSION or set(t)!=set(DEFAULT) or any(type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=100 for v in t.values()):raise ValueError('Profilo v5 non valido.')
    if set(s)!=set(SETTINGS) or s['char_ngram'] not in ['3','4','5'] or s['aggregation'] not in ['max','top2'] or type(s['containment']) is not bool or not 1<=t['top_k']<=50:raise ValueError('Impostazioni v5 non valide.')
    return p

def revision():return hashlib.sha256(PATH.read_bytes()).hexdigest()

def match(text,documents,**kwargs):
    return fuse(text,documents,decision_profile=profile(),policy_version=VERSION,**kwargs)
