"""Freeze and release-infrastructure negative contracts."""
import pytest
from scripts.round17_common import invariant, ROOT

def test_round17_preserves_entire_round16_engine_dataset_and_truth():
    invariant()

def test_unknown_v3_cannot_start_with_another_freeze(monkeypatch):
    import benchmarks.round17_unknown as u
    monkeypatch.setattr(u,'sealed',lambda:dict(freeze_git_commit='correct-freeze'))
    with pytest.raises(AssertionError):
        u.validate_release(dict(manifest_id='official-unknown-release-v3',freeze_commit='other-freeze'))

def test_evaluation_cannot_start_before_unknown_pass(monkeypatch):
    import benchmarks.round17_evaluation as e
    monkeypatch.setattr(e,'sealed',lambda:{})
    monkeypatch.setattr(e,'read',lambda p:dict(passed=False))
    with pytest.raises(AssertionError,match='Unknown gate'): e.plan()

def test_inadequate_pool_never_becomes_a_release_subset(monkeypatch):
    import benchmarks.round17_unknown as u
    from benchmarks.unknown_release import balance
    monkeypatch.setattr(u,'sealed',lambda:dict(freeze_git_commit='fixed'))
    monkeypatch.setattr(u,'read',lambda p:dict(confirmed_cases=[]))
    monkeypatch.setattr(u,'sha',lambda p:'fixed-hash')
    captured=[]
    monkeypatch.setattr(u,'save',lambda n,v:captured.append(v))
    monkeypatch.setattr(u,'atomic_json',lambda *a:pytest.fail('Must not publish an inadequate manifest'))
    u.selection()
    assert captured[-1]['passed'] is False and captured[-1]['recognition_calls']==0
