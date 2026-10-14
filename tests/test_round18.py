"""Prospective subset selection and independent freeze barriers."""
import copy,random
import pytest
from scripts.round18_common import read,invariant
from benchmarks.round18_sampling import sample,feasible_size
from benchmarks.unknown_release import balance

def master():return read('benchmarks/results/round17/unknown_v3_truth_audit.json')['confirmed_cases']

def test_round18_entire_engine_and_catalog_remain_frozen():
    from benchmarks.historical_seals import verify_engine_at
    f=read('benchmarks/results/round18/freeze_manifest.json')
    verify_engine_at(f['freeze_git_commit'],f['engine_files_sha256'])

def test_imbalanced_master_has_a_maximal_balanced_release_subset():
    b=balance(master());assert b['max_concentration']>.25
    selected=sample(master(),20261014);s=balance(selected)
    assert len(selected)==116 and s['counts_per_source']['inl']==29 and s['sources']==13 and s['max_concentration']==.25
    counts=b['counts_per_source'];assert sum(min(v,117//4) for v in counts.values())<117

def test_sampling_is_invariant_to_file_order_and_ignores_forged_scores():
    cases=master();expected=[c['case_id'] for c in sample(cases,20261014)]
    varied=copy.deepcopy(cases);random.Random(23).shuffle(varied)
    for i,c in enumerate(varied):c.update(score=i,prediction='DOCUMENT_MATCH',candidate_rank=999-i,fingerprint_similarity=1)
    assert [c['case_id'] for c in sample(varied,20261014)]==expected

def test_too_few_sources_cannot_be_repaired_with_more_cases():
    assert feasible_size({'one':1000,'two':1000}) is None

def test_unknown_validation_requires_the_frozen_manifest(monkeypatch):
    import benchmarks.round18_unknown as u
    monkeypatch.setattr(u,'sealed',lambda:dict(unknown_manifest_sha256='frozen'))
    monkeypatch.setattr(u,'sha',lambda p:'changed')
    with pytest.raises(AssertionError):u.validate_release({})

def test_v5_is_blocked_by_failed_unknown(monkeypatch):
    import benchmarks.round18_evaluation as e
    monkeypatch.setattr(e,'sealed',lambda:{})
    monkeypatch.setattr(e,'read',lambda p:dict(passed=False))
    with pytest.raises(AssertionError,match='Unknown gate'):e.plan()
