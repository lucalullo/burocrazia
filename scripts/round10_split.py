"""Keep exact and near resource groups on one side of unknown dev/eval."""
import hashlib,json,sys
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from benchmarks.round3_audit import read
from benchmarks.transactional_writer import atomic_json
from benchmarks.unknown_v2 import validate
from src.fingerprint_v3 import features

def main():
 manifest=validate(read('benchmarks/manifests/official_unknown_v2.json'));cases=manifest['cases'];parent=list(range(len(cases)));queries=[];edges=[]
 def find(i):
  while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
  return i
 for c in cases:
  sha=c['SHA256'];paths=[ROOT/'tmp-build'/f'round{r}-truth-text'/(sha+'.json') for r in [9,10]]
  p=next(p for p in paths if p.exists());text=json.loads(p.read_bytes())['opening']
  assert hashlib.sha256(text.encode()).hexdigest()==c['audit_evidence']['opening_sha256']
  queries.append(features(text))
 for i,a in enumerate(queries):
  for j in range(i):
   b=queries[j]
   token=len(a['tokens']&b['tokens'])/max(1,len(a['tokens']|b['tokens']))
   chars=len(a['chars']['4']&b['chars']['4'])/max(1,len(a['chars']['4']|b['chars']['4']))
   if token>=.8 and chars>=.8:
    parent[find(i)]=find(j);edges.append(dict(a=cases[i]['case_id'],b=cases[j]['case_id'],token_jaccard=token,char4_jaccard=chars))
 groups=defaultdict(list)
 for i,c in enumerate(cases):groups[find(i)].append(c)
 for group in groups.values():
  representative=min(c['SHA256'] for c in group);old=any(c['historically_seen'] for c in group)
  split='unknown_dev' if old or int(representative[:8],16)%5==0 else 'unknown_eval'
  for c in group:c.update(split=split,resource_group='UG10-'+representative[:16])
 validate(manifest);atomic_json(ROOT/'benchmarks/manifests/official_unknown_v2.json',manifest)
 audit=dict(schema_version=1,near_edges=edges,groups=[dict(resource_group=g[0]['resource_group'],case_ids=[c['case_id'] for c in g],split=g[0]['split'],historically_seen=any(c['historically_seen'] for c in g)) for g in groups.values()],exact_sha_disjoint=True,near_resource_groups_disjoint=True,method='Connected components of public first2000 content sketches: token and char4 Jaccard both>=.8. Every historical group forced to development; remaining groups deterministic80/20 by minimum SHA. No recognition calls or v5 identity selection.',scope='Resource split audit only, not a frozen evaluation leakage certificate. Semantic duplicates beyond these sketches remain a limitation.')
 atomic_json(ROOT/'benchmarks/results/round10/unknown_resource_split_audit.json',audit)
 balance=read('benchmarks/results/round10/unknown_balance.json');balance['split']=dict(Counter(c['split'] for c in cases));balance['near_resource_groups']=len(groups);atomic_json(ROOT/'benchmarks/results/round10/unknown_balance.json',balance)
 print('Unknown resource split',balance['split'],'near pairs',len(edges))

if __name__=='__main__':main()
