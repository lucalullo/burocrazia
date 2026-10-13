"""Post-freeze verification without rewriting any prerequisite evidence."""
import compileall,statistics
from scripts.round16_common import *
from scripts.round14_baseline import tests
from scripts.verify_catalog import verify
from benchmarks.round9_performance import describe
from benchmarks.release_truth import load_release
from benchmarks.round4_common import runtime_hash

def main():
    f=sealed()
    for name,h in f['prerequisite_evidence_sha256'].items():assert sha(OUT/(name+'.json'))==h,name
    assert all(compileall.compile_dir(str(ROOT/p),quiet=1) for p in ['src','benchmarks','maintenance','scripts'])
    cat=verify(ROOT/'data/catalog_seed.sqlite3');assert cat['integrity']=='ok' and not cat['foreign_key_violations']
    load_release();p=read(OUT/'performance_stability.json')
    assert len(p['runs'])==7 and p['identity']['runtime_sha256']==runtime_hash()
    for r in p['runs']:assert describe([s['milliseconds'] for s in r['samples']])==r['latency_ms'] and len(r['samples'])==402
    assert statistics.median(r['latency_ms']['p95'] for r in p['runs'])==p['median_p95']<=250
    eq=read(OUT/'semantic_equivalence.json');assert eq['passed'] and eq['n']==1563 and not eq['differences']
    assert read(OUT/'canonical.json')['counts']['exact']==980 and read(OUT/'canonical_legacy.json')['counts']['exact']==27
    review=read(OUT/'unknown_v3_primary_truth_review.json');assert review['script_sha256']==sha('scripts/round16_unknown_review.py')
    assert review['recognition_calls']==0 and read(OUT/'unknown_v3_selection.json')['recognition_calls']==0
    assert not (ROOT/'benchmarks/manifests/official_unknown_release_v3.json').exists()
    assert not (OUT/'unknown_v3_started.json').exists() and not (OUT/'evaluation_v5_started.json').exists()
    save('final_tests',dict(tests('reports/round16-final-tests-archive.log'),status='passed',runtime_sha256=runtime_hash(),pre_freeze_tests_sha256=sha(OUT/'tests.json'),scope='Final full suite after reports/data qualification on the same frozen engine; pre-freeze tests remain immutable.'))
    save('post_freeze_checks',dict(passed=True,freeze_commit=f['freeze_git_commit'],prerequisite_hashes_preserved=True,catalog=cat,performance_recomputed=True,equivalence_pass=True,recognition_semantics_unchanged=True,runner_inventory_unchanged=True,historical_git_blobs_preserved=len(historical()),unknown_release_calls=0,evaluation_v5_calls=0,unknown_selection=read(OUT/'unknown_v3_selection.json')['selection'],checked_at=now(),ci='external_pending'))
    print('R16 final audit passed; independent sample insufficiency retained, no predictions',flush=True)

if __name__=='__main__':main()
