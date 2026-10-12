"""R10 reruns of unchanged contracts; historical artifacts stay immutable."""
import argparse,json,subprocess,sys
from benchmarks import round8_common as common,round8_validation as previous
from benchmarks.transactional_writer import atomic_json
OUT='benchmarks/results/round10/'

def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['historical','canonical','family','verify','performance','performance-worker']);a=p.parse_args()
 common.OUT=OUT;common.SEED=2026101210;previous.OUT=OUT
 def write(path,value):return atomic_json(common.ROOT/path,value)
 common.write=write;previous.write=write
 if a.mode=='verify':
  from scripts import round9_verify
  def redirected(path,value):return atomic_json(common.ROOT/OUT/path.name,value)
  round9_verify.atomic_json=redirected;round9_verify.main()
 elif a.mode.startswith('performance'):
  from benchmarks import round9_performance as perf
  if a.mode=='performance-worker':perf.worker();return
  raw=subprocess.check_output([sys.executable,'-m','benchmarks.round10_validation','performance-worker'],cwd=common.ROOT,text=True)
  lines=[l for l in raw.splitlines() if l.startswith('{')];assert len(lines)==1
  result=json.loads(lines[0]);result['scope']+=' Unchanged R9 measurement protocol rerun for R10; no scoring/threshold/engine optimization.'
  write(OUT+'performance.json',result);write(OUT+'performance_profile.json',dict(identity=result['identity'],components=result['components'],cprofile=result['cprofile'],scope=result['scope']))
  print(json.dumps(result['latency_ms']),flush=True)
 else:getattr(previous,a.mode)()

if __name__=='__main__':main()
