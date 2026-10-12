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


def headline_sections(summary):
    """Stable release-evidence precedence; development never fills a holdout gap."""
    values=dict(summary)
    if values.get('benchmark_model')=='known-family-unknown-v2':
        keys=['fingerprint_coverage','known_robustness','unknown_official']
        if values.get('family_identity_holdout',{}).get('families_evaluable',0)>=5:keys.append('family_identity_holdout')
        keys+=['scan_ocr','performance']
        return tuple((k,values.get(k,{'status':'not_run'})) for k in keys)
    if values.get('benchmark_model')=='known-family-unknown-v1':
        return tuple((key,values.get(key,{'status':'not_run'})) for key in
            ('known_canonical','known_robustness','filled_forms','family_identity_holdout',
             'unknown_official','hard_negatives','real_ocr','performance'))
    holdout=values.get('independent_holdout',{})
    if holdout and holdout.get('corpus_id') != 'official_holdout_v2':
        values['independent_holdout']={'status':'not_run','reason':'Round 4 richiede official_holdout_v2; v1 è storico.'}
    return tuple((key,values.get(key,{'status':'not_run'})) for key in
                 ('independent_holdout','hard_negatives','real_ocr','performance'))
