"""Bind benchmark infrastructure independently of the unchanged R18 engine."""
from scripts.round19_common import *

def verify_benchmark_seal():
    sealed();s=read(OUT/'benchmark_seal.json')
    from benchmarks.evaluate import code_hash
    assert s['semantic_freeze_commit']==FREEZE and s['full_code_sha256']==code_hash()
    for p,h in s['files_sha256'].items():assert sha(p)==h,p
    for p,h in s['inputs_sha256'].items():assert sha(p)==h,p
    return s

def main():
    sealed();assert read(OUT/'evaluation_v5_generation_preflight.json')['passed']
    assert not (OUT/'benchmark_seal.json').exists() and not (OUT/'evaluation_v5_started.json').exists()
    s=benchmark_inventory()
    s.update(semantic_freeze_commit=FREEZE,recognition_semantic_sha256=sealed()['recognition_semantic_sha256'],scope='Benchmark-only inventory; not a new engine freeze. R18 freeze/evidence remain immutable.',
             inputs_sha256={p:sha(p) for p in [REGISTRY,'benchmarks/reference/v5_source_counting_policy_v1.json',*[str((OUT/(n+'.json')).relative_to(ROOT).as_posix()) for n in ['evaluation_v5_plan','evaluation_v5_prepared','evaluation_v5_leakage','evaluation_v5_representation_audit','evaluation_v5_generation_preflight']]]},created_at=now())
    save('benchmark_seal',s);verify_benchmark_seal();print('R19 benchmark inventory sealed; engine freeze reused',FREEZE,flush=True)

if __name__=='__main__':main()
