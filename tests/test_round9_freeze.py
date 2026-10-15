import pytest
from benchmarks.round9_freeze import prerequisites,require_freeze

def test_unfrozen_engine_cannot_start_v5_selection():
    with pytest.raises(ValueError,match='not frozen'):require_freeze()

def test_failed_prerequisites_are_not_relaxed_for_close_misses():
    v=prerequisites(coverage=dict(residual_audited=217,file_backed=1158,fingerprinted=941,coverage_file_backed=941/1158,coverage_all=941/1212),performance=dict(latency_ms=dict(p50=51,p95=250.01)),unknown=dict(cases=list(range(99)),sources={str(i):1 for i in range(8)},source_concentration=.25),canonical=dict(counts=dict(exact=1,wrong=0,extraction_failed=0),cases=[1]),calibration=dict(status='development_replay_complete',false_accepts=0,wrong_known=0))
    assert v['canonical_safety'] and v['coverage_recovery_finished']
    assert not v['coverage_file_backed'] and not v['unknown_truth_adequate'] and not v['performance_development']
