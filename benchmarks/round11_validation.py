"""R11 historical/canonical/performance reruns without changing semantics."""
import argparse,json,subprocess,sys
from benchmarks import round8_common as common,round8_validation as previous
from benchmarks.transactional_writer import atomic_json
OUT='benchmarks/results/round11/'

def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['historical','canonical','verify','performance','performance-worker','unknown-dev']);a=p.parse_args()
 common.OUT=OUT;common.SEED=2026101311;previous.OUT=OUT
 def write(path,value):return atomic_json(common.ROOT/path,value)
 common.write=write;previous.write=write
 if a.mode=='verify':
  from scripts import round9_verify
  round9_verify.atomic_json=lambda path,value:atomic_json(common.ROOT/OUT/path.name,value);round9_verify.main()
 elif a.mode.startswith('performance'):
  from benchmarks import round9_performance as perf
  if a.mode=='performance-worker':perf.worker();return
  raw=subprocess.check_output([sys.executable,'-m','benchmarks.round11_validation','performance-worker'],cwd=common.ROOT,text=True);lines=[l for l in raw.splitlines() if l.startswith('{')];assert len(lines)==1
  r=json.loads(lines[0]);r['scope']+=' R11 unchanged recognition protocol, no optimization; dataset additions separately hashed.';write(OUT+'performance.json',r);print('R11 performance',r['latency_ms'],flush=True)
 elif a.mode=='unknown-dev':
  from benchmarks.unknown_release import validate
  from benchmarks.round10_unknown import worker
  from benchmarks.transactional_writer import CaseJournal
  import hashlib
  manifest=validate(common.read('benchmarks/manifests/official_unknown_master_v1.json'));cases=[dict(c,split='unknown_dev') for c in manifest['cases'] if c['split']=='unknown_dev'];ident=common.identity();binding={k:v for k,v in ident.items() if k not in ['commit','executed_at']};binding['manifest_sha256']=hashlib.sha256((common.ROOT/'benchmarks/manifests/official_unknown_master_v1.json').read_bytes()).hexdigest()
  journal=CaseJournal(common.ROOT/'benchmarks/work/round11'/('unknown-dev-'+binding['code_sha256'][:12]+'-'+binding['manifest_sha256'][:12]+'.sqlite'),identity=binding,expected_ids=[c['case_id'] for c in cases]);pending=set(journal.pending())
  for c in cases:
   if c['case_id'] in pending:journal.append(worker(c))
  rows=journal.rows();target=common.ROOT/OUT/'unknown_development_observations.json';journal.export(target,complete=True)
  write(OUT+'unknown_development.json',dict(identity=ident,cases=rows,expected_count=len(cases),actual_count=len(rows),unique_case_ids=len({r['id'] for r in rows}),false_accepts=sum(r['observed']['match_type']!='NO_MATCH' for r in rows),extraction_failed=sum(r['extraction_failed'] for r in rows),observations_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),release_recognition_calls=0,scope='Only master-minus-release development resources; no R11 release predictions or tuning. Prior exposure of release cases remains explicitly reported.'))
  print('R11 unknown dev',len(rows),flush=True)
 else:getattr(previous,a.mode)()

if __name__=='__main__':main()
