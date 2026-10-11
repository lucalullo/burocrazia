"""Bounded static benchmark data. No evaluation or network imports."""
import json
from pathlib import Path


def load_summary(path: Path) -> dict:
    if path.is_symlink() or path.stat().st_size > 512_000:
        raise ValueError('Artefatto benchmark oltre i limiti.')
    value=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value,dict) or value.get('schema_version')!=1 or not isinstance(value.get('evaluations'),list):
        raise ValueError('Formato benchmark non supportato.')
    if len(value['evaluations'])>12 or any(not isinstance(e,dict) or not isinstance(e.get('summary'),dict) for e in value['evaluations']):
        raise ValueError('Valutazioni non valide.')
    for evaluation in value['evaluations']:
        if any(not isinstance(evaluation['summary'].get(key,{}),dict) for key in ['metrics','latency_ms']):
            raise ValueError('Metriche non valide.')
    return value


def metric_label(value):
    if not isinstance(value,dict):return 'Non misurato'
    n,d=value.get('numerator'),value.get('denominator')
    if type(n) is not int or type(d) is not int or d<=0:return 'Non definito (denominatore zero)'
    return f'{100*n/d:.2f}% ({n}/{d})'
