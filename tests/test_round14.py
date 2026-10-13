import pytest
from benchmarks.round14_unknown import metrics,validate_observations,validate_release
from benchmarks.unknown_release import select

def test_unknown_family_acceptance_and_extraction_error_are_not_correct_rejections():
    def row(kind,error=False,version=None):
        return dict(observed=dict(match_type=kind,version=version,entity='Other' if kind=='DOCUMENT_MATCH' else 'Issuer'),extraction_failed=error,provenance=dict(truth_version='2025',entity='Issuer'))
    result=metrics([row('NO_MATCH'),row('NO_MATCH',True),row('FAMILY_MATCH'),row('DOCUMENT_MATCH',version='2026')])
    assert result['correct_no_match']==1 and result['rejection_rate']==.25
    assert result['false_acceptance_rate']==.5 and result['wrong_family_match']==1
    assert result['entity_errors']==1 and result['version_errors']==1

def test_exposure_cannot_be_removed_by_renaming_a_case(monkeypatch):
    import benchmarks.round14_unknown as u
    monkeypatch.setattr(u,'sealed',lambda:dict(freeze_git_commit='freeze'))
    monkeypatch.setattr(u,'validate_old_contract',lambda m:m)
    monkeypatch.setattr(u,'excluded',lambda:{'a'*64})
    monkeypatch.setattr(u,'read',lambda p:dict(cases=[]))
    manifest=dict(manifest_id='official-unknown-release-v2',freeze_commit='freeze',cases=[dict(case_id='NEW-ID',SHA256='a'*64)])
    with pytest.raises(AssertionError):validate_release(manifest)

def test_selection_does_not_split_near_resource_groups_or_depend_on_input_order():
    cases=[dict(case_id=str(i),resource_group='g'+str(i//2),source='s'+str(i//4)) for i in range(12)]
    a=select(cases,seed=2026101314,source_cap=3);b=select(list(reversed(cases)),seed=2026101314,source_cap=3)
    assert a==b
    for group in {c['resource_group'] for c in cases}:
        assert len([c for c in a if c['resource_group']==group]) in [0,2]

def test_frozen_engine_bytes_cannot_change_during_benchmark(monkeypatch):
    import scripts.round14_common as c
    monkeypatch.setattr(c,'read',lambda p:dict(engine_files_sha256={'src/example.py':'before'},contamination_registry_sha256='registry'))
    monkeypatch.setattr(c,'engine_files',lambda:{'src/example.py':'after'})
    with pytest.raises(AssertionError,match='Frozen engine'):c.sealed()

def test_observation_schema_rejects_partial_final_export():
    import jsonschema
    identity={k:'a'*64 for k in ['freeze_commit','manifest_sha256','runtime_sha256','fingerprint_sha256','runner_code_sha256','registry_sha256']}
    row=dict(id='U14-'+'a'*16,expected=dict(match_type='NO_MATCH'),observed=dict(match_type='NO_MATCH',document_id=None,family_id=None,entity=None,version=None),
             input_sha256='a'*64,extraction_failed=False,signals=[],representation='official_original',
             provenance=dict(source='fixture',entity='Fixture',document_type='manuale',sha256='a'*64,previously_seen=False,official_url='https://example.invalid/fixture.pdf'))
    value=dict(schema_version=1,identity=identity,expected_count=1,completed=1,complete=True,cases=[row]);validate_observations(value)
    with pytest.raises(AssertionError):validate_observations(dict(value,expected_count=100))
    with pytest.raises(jsonschema.ValidationError):validate_observations(dict(value,complete=False))
