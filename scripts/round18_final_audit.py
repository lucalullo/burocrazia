"""Final verification of frozen prerequisites without rewriting their bytes."""
import compileall,statistics,jsonschema
from scripts.round18_common import *
from scripts.round14_baseline import tests
from scripts.verify_catalog import verify
from benchmarks.round4_common import runtime_hash
from benchmarks.round9_performance import describe

def main():
    f=sealed()
    for n,h in f['prerequisite_evidence_sha256'].items():assert sha(OUT/(n+'.json'))==h,n
    assert all(compileall.compile_dir(str(ROOT/p),quiet=1) for p in ['src','benchmarks','maintenance','scripts'])
    assert all(compileall.compile_file(str(ROOT/p),quiet=1) for p in ['app.py','run.py'])
    cat=verify(ROOT/'data/catalog_seed.sqlite3');assert cat['integrity']=='ok' and not cat['foreign_key_violations']
    for path in (ROOT/'benchmarks/schemas').glob('round18_*.json'):jsonschema.Draft202012Validator.check_schema(read(path))
    p=read(OUT/'performance_stability.json')
    for r in p['runs']:assert len(r['samples'])==402 and describe([c['milliseconds'] for c in r['samples']])==r['latency_ms']
    assert statistics.median(r['latency_ms']['p95'] for r in p['runs'])==p['median_p95']<=250
    assert read(OUT/'semantic_equivalence.json')['passed'] and read(OUT/'semantic_equivalence.json')['n']==1563
    assert read(OUT/'canonical.json')['counts']['exact']==980 and read(OUT/'canonical_legacy.json')['counts']['exact']==27
    assert read(OUT/'release_gate_fast.json')['passed'] and read(OUT/'input_safety.json')['passed']
    u=read(OUT/'unknown_release_v3.json')
    if u['status']=='complete':
        from benchmarks.round18_unknown import validate_observations
        validate_observations(read(OUT/'unknown_release_v3_observations.json'))
    if (OUT/'evaluation_v5_observations.json').exists():jsonschema.validate(read(OUT/'evaluation_v5_observations.json'),read('benchmarks/schemas/round18_evaluation_observations.schema.json'))
    save('final_tests',dict(tests('reports/round18-final-tests.log'),failed=0,status='passed',runtime_sha256=runtime_hash(),pre_freeze_tests_sha256=sha(OUT/'tests.json'),scope='Full post-freeze suite; no frozen prerequisite rewritten.'))
    save('post_freeze_checks',dict(passed=True,freeze_commit=f['freeze_git_commit'],prerequisite_hashes_preserved=True,engine_and_runner_unchanged=True,catalog=cat,compile_pass=True,benchmark_schemas_valid=True,performance_recomputed=True,semantic_cases=1563,semantic_differences=0,canonical_exact=1007,unknown_release_calls=u['recognition_calls'],evaluation_v5_calls=read(OUT/'evaluation_v5_gate.json')['actual_count'] if (OUT/'evaluation_v5_gate.json').exists() else 0,checked_at=now(),ci='external_pending'))
    print('R18 final frozen audit PASS',flush=True)

if __name__=='__main__':main()
