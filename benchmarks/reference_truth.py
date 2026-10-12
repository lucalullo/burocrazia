"""Versioned reference labels, independent from the recognizer's observations."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/'benchmarks/reference/reference_truth_v1.json'
STATUSES={'historical_expected_preserved','official_truth_confirmed','historical_fixture_error','ambiguous','obsolete_source'}
LABELS={'confirmed','historical_only','ambiguous','excluded_from_release_gate'}

def load(path=PATH):
    path=Path(path)
    if path.is_symlink() or path.stat().st_size>512000:raise ValueError('Unsafe truth registry')
    r=json.loads(path.read_bytes())
    if r.get('schema_version')!=1 or r.get('unclassified_contradictions')!=0:raise ValueError('Unclassified truth contradictions')
    for c in r['cases']:
        if c['status'] not in STATUSES or c['label_status'] not in LABELS:raise ValueError('Invalid truth status')
        if c['label_status']=='confirmed' and (c['status']!='official_truth_confirmed' or not c['reconciled_expected'] or not any(e.get('sha256') for e in c['official_evidence'])):raise ValueError('Unsupported official truth')
    for name,digest in r['corpus_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise ValueError('Historical corpus changed')
    return r

def confirmed(path=PATH):return [c for c in load(path)['cases'] if c['status']=='official_truth_confirmed' and c['label_status']=='confirmed']
