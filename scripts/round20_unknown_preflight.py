"""Fresh v4 metadata feasibility only; never predict or select a release set."""
from collections import Counter
from scripts.round20_common import *

def main():
    preserved();v=read('benchmarks/reference/benchmark_contamination_registry_v6.json');seen=set(v['observed_resource_sha256'])
    master=read('benchmarks/results/round18/unknown_master_pool.json')['eligible_cases'];candidates=[c for c in master if c['SHA256'] not in seen]
    for c in candidates:assert sha('benchmarks/cache/'+c['SHA256']+'.body')==c['SHA256']
    counts=Counter(c['source'] for c in candidates);concentration=max(counts.values())/len(candidates) if candidates else None
    requirements=dict(count=len(candidates)>=100,sources=len(counts)>=8,concentration=concentration is not None and concentration<=.25,no_contamination=not {c['SHA256'] for c in candidates}&seen)
    pool=read(OUT/'v6_preflight.json')
    save('unknown_v4_preflight',dict(passed=all(requirements.values()),N=len(candidates),sources=len(counts),counts_per_source=dict(counts),max_concentration=concentration,requirements=requirements,
         confirmed_existing_fresh_cases=candidates,recognition_calls=0,acquisition_performed=False,
         reason='V6 source adequacy fails before freeze. No fresh release acquisition/selection/prediction is justified for an unreachable joint gate; existing unused confirmed official resources are inventoried honestly.',
         V6_sources=pool['sources'],minimum_sources_v6=6,minimum_N=100,minimum_sources=8,maximum_source_concentration=.25,
         scope='Preflight only; no official_unknown_release_v4 manifest published. Unknown v1-v3 and all development resources excluded; no historical116/116 transferred to new engine.'))
    print('R20 fresh unknown v4 available',len(candidates),dict(counts),'passed',all(requirements.values()),flush=True)

if __name__=='__main__':main()
