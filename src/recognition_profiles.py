"""Bounded declarative safety metadata. Request text is never cached."""
from functools import lru_cache
import hashlib
import json
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / 'data/recognition_profiles/safety_v1.json'

def validate(data):
    keys = {'schema_version', 'version', 'purpose', 'exclusive_qualifiers', 'family_context', 'weak_entity_prefixes', 'boilerplate'}
    if not isinstance(data, dict) or set(data) != keys or type(data['schema_version']) is not int or data['schema_version'] != 1 or not isinstance(data['version'], str) or not 0 < len(data['version']) <= 80 or not isinstance(data['purpose'], str) or len(data['purpose']) > 1000:
        raise ValueError('Schema profili di riconoscimento non valido.')
    groups = data['exclusive_qualifiers']
    context = data['family_context']
    if not isinstance(groups, list) or len(groups) > 50 or not isinstance(context, dict) or len(context) > 100:
        raise ValueError('Profili oltre i limiti.')
    lists = [*groups, *context.values(), data['weak_entity_prefixes'], data['boilerplate']]
    if not all(isinstance(v, list) and 0 < len(v) <= 50 and all(isinstance(s, str) and 0 < len(s) <= 120 for s in v) for v in lists):
        raise ValueError('Segnali del profilo non validi.')
    if not all(isinstance(k, str) and 0 < len(k) <= 120 for k in context):
        raise ValueError('Contesto famiglia non valido.')
    return data

@lru_cache(maxsize=1)
def load():
    if PATH.is_symlink() or PATH.stat().st_size > 64_000:
        raise ValueError('File profili non valido.')
    return validate(json.loads(PATH.read_text(encoding='utf-8')))

@lru_cache(maxsize=1)
def revision():
    load()
    return hashlib.sha256(PATH.read_bytes()).hexdigest()
