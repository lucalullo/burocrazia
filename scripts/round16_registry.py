"""Add current diagnostic exposures, preserving the immutable R15 registry."""
import copy,re
from scripts.round16_common import *

def main():
    assert not (ROOT/REGISTRY).exists(),'Registry already sealed'
    old='benchmarks/reference/benchmark_contamination_registry_v2.json';v=copy.deepcopy(read(old));known={c['document_id']:c for c in v['known_identities']};seen=set(v['observed_resource_sha256'])
    for prepared,artifact in [('semantic-inputs.json','semantic_after.json'),('semantic-supplement.json','semantic_supplement_after.json')]:
        source='benchmarks/work/round16/'+prepared;rows=read(source)['rows'];actual=read(OUT/artifact)['cases']
        for c,r in zip(rows,actual):
            assert c['id']==r['case_id']
            if c['sha256']:seen.add(c['sha256'])
            if c['category'] in ['canonical','canonical_legacy']:continue
            ids={r['signature']['document_id'],(c.get('expected') or {}).get('document_id')}
            if c['raw_file'] and c['category'] in ['round6_scan_development','round6_filled_development','round8_filled_development','round7_development','round8_observed_development']:
                # Only generated development filenames encode document IDs;
                # hexadecimal cache filenames must never become identities.
                m=re.match(r'(?:R8DEV-|R8-)?(\d+)',Path(c['raw_file']).name)
                if m:ids.add(int(m[1]))
            for did in ids:
                if did not in known:continue
                k=known[did];k.update(tuning=True,prior_evaluation_seen=True,eligible_v5=False)
                k['contamination_reason']=sorted(set(k['contamination_reason']+['tuning','prior_evaluation_seen']))
                for flag in ['tuning','prior_evaluation_seen']:k['evidence'][flag]=sorted(set(k['evidence'].get(flag,[])+['benchmarks/results/round16/'+artifact]))
    paths=['semantic_inputs_manifest.json','semantic_supplement_manifest.json','semantic_before.json','semantic_after.json','semantic_supplement_before.json','semantic_supplement_after.json','performance_profile.json','performance_stability.json']
    for n in paths:v['input_sha256']['benchmarks/results/round16/'+n]=sha(OUT/n)
    v.update(schema_version=3,registry_id='benchmark-contamination-registry-v3-round16',baseline_commit=BASE,parent_registry_sha256=sha(old),created_at=now(),known_identities=[known[k] for k in sorted(known)],observed_resource_sha256=sorted(seen),policy=v['policy']+' Additive Round16 equivalence/performance exposures; canonical-only verification stays distinct from tuning. Fresh unknown must exclude this union plus technical/semantic near variants. No future predictions folded back into this pre-freeze seal.')
    v['counts'].update(known_contaminated=sum(bool(k['contamination_reason']) for k in known.values()),known_eligible=sum(k['eligible_v5'] for k in known.values()),all_previously_observed_resource_shas=len(seen))
    assert set(read(old)['observed_resource_sha256'])<=seen
    atomic_json(ROOT/REGISTRY,v);print('R16 registry',v['counts'],flush=True)

if __name__=='__main__':main()
