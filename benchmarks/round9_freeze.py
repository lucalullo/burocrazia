"""Fail-closed prerequisites for selecting any new independent v5 identity."""
from benchmarks.round3_audit import ROOT,read

def prerequisites(*,coverage,performance,unknown,canonical,calibration):
    return dict(
        coverage_recovery_finished=coverage['residual_audited']==coverage['file_backed']-coverage['fingerprinted'],
        coverage_file_backed=coverage['coverage_file_backed']>=.85,
        coverage_operational=coverage['coverage_all']>=.70,
        performance_development=performance['latency_ms']['p50']<=150 and performance['latency_ms']['p95']<=250,
        unknown_truth_adequate=len(unknown['cases'])>=100 and len(unknown['sources'])>=8 and unknown['source_concentration']<=.25,
        canonical_safety=canonical['counts']['exact']==len(canonical['cases']) and canonical['counts']['wrong']==0 and canonical['counts']['extraction_failed']==0,
        calibration_safety=calibration.get('status')=='development_replay_complete' and calibration['false_accepts']==0 and calibration['wrong_known']==0,
    )

def require_freeze():
    path=ROOT/'benchmarks/results/round9/freeze.json'
    if not path.exists():raise ValueError('Round9 engine not frozen: v5 selection/evaluation prohibited')
    freeze=read('benchmarks/results/round9/freeze.json')
    if not freeze.get('prerequisites') or not all(freeze['prerequisites'].values()):raise ValueError('Freeze prerequisites not met')
    from benchmarks.round8_common import identity
    current=identity()
    for key in ['runtime_sha256','code_sha256','fingerprint_sha256']:
        if freeze[key]!=current[key]:raise ValueError('Frozen engine or tooling changed: '+key)
    import hashlib
    for path,key in [('benchmarks/reference/reference_truth_v2.json','truth_sha256'),('benchmarks/manifests/official_unknown_v1.json','unknown_manifest_sha256'),('benchmarks/results/round9/calibration_v5.json','calibration_sha256')]:
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=freeze[key]:raise ValueError('Frozen evidence changed')
    return freeze
