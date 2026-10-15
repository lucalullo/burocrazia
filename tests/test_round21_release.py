"""Verify metadata-only selection and real synthetic worker/schema integration."""
import hashlib,jsonschema
from scripts.round21_common import ROOT,read
from benchmarks.round21_release import fixed_selection,worker

def test_selection_does_not_use_prediction_fields_or_input_order():
    rows=[dict(id=f'{source}-{i}',source=source,kind=str(i%3),recognition_score=i) for source in range(8) for i in range(12)]
    kwargs=dict(seed=211,target=40,source_field='source',identity_field='id',cap=10,strata=lambda c:(c['kind'],))
    first=fixed_selection(rows,**kwargs)
    altered=[dict(c,recognition_score=1000-c['recognition_score']) for c in reversed(rows)]
    second=fixed_selection(altered,**kwargs)
    assert [c['id'] for c in first]==[c['id'] for c in second]
    assert len(first)==40 and len({c['source'] for c in first})==8

def test_single_shot_worker_produces_schema_valid_synthetic_observation(tmp_path):
    raw='Testo sintetico privo di intestazioni documentali, codici e moduli ufficiali. Esempio per verificare soltanto estrazione e journal.'.encode()
    path=tmp_path/'synthetic.txt';path.write_bytes(raw);sha=hashlib.sha256(raw).hexdigest()
    case=dict(id='U21-SYNTHETIC-SMOKE',group='synthetic_development',category='hard_negative',expected=dict(match_type='NO_MATCH'),provenance=dict(sha256=sha),representation='synthetic_text')
    row=worker(dict(path=str(path),filename=path.name,sha256=sha,case=case,unknown=True))
    assert row['observed']['match_type']=='NO_MATCH' and row['correct'] and not row['extraction_failed']
    identity={k:'synthetic' for k in ['freeze_manifest_sha256','semantic_source_tree','input_manifest_sha256','runtime_sha256','fingerprint_sha256','runner_code_sha256','registry_sha256']}
    jsonschema.validate(dict(schema_version=1,identity=identity,expected_count=1,completed=1,complete=True,cases=[row]),read('benchmarks/schemas/round21_observations.schema.json'))
