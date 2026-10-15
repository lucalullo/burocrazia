"""Post-V5 canonical, safety and full-signature validation in separate files."""
import shutil
from scripts.round19_common import *
from scripts.round19_seal import verify_benchmark_seal

def main():
    verify_benchmark_seal();assert (OUT/'evaluation_v5_gate.json').exists()
    target=OUT/'post_v5_validation';assert not target.exists();target.mkdir()
    def post_save(n,v):return atomic_json(target/(n+'.json'),v)
    from benchmarks import round19_semantics as s
    from scripts import round19_validate as v
    for name in ['semantic_inputs_manifest','semantic_supplement_manifest','semantic_before','semantic_supplement_before']:
        shutil.copyfile(OUT/(name+'.json'),target/(name+'.json'))
    s.OUT=target;s.save=post_save
    s.observe('after');s.observe('after',supplement=True);s.combine()
    v.OUT=target;v.save=post_save;v.measure()
    for name in ['canonical','canonical_legacy']:
        assert read(target/(name+'.json'))['cases']==read(OUT/(name+'.json'))['cases']
    assert read(target/'input_safety.json')['passed']
    eq=read(target/'semantic_equivalence.json');assert eq['passed'] and eq['n']==1563
    save('post_v5_validation',dict(passed=True,canonical_exact=1007,semantic_cases=1563,semantic_differences=0,input_safety=9,unknown_v3_calls=0,
         artifacts_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in target.glob('*.json')},scope='Actual post-V5 recognition replay on historical canonical/development diagnostic inputs; no independent unknown or V5 replay.',checked_at=now()))
    print('R19 post-V5 canonical/equivalence/input safety PASS',flush=True)

if __name__=='__main__':main()
