"""Lock R10 evidence and preserve original historical blobs, without a freeze."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from benchmarks.transactional_writer import atomic_json
BASELINE='8c13da270fe2c4db212ca3611fb5ce0ddef7b0d8'

def main():
 gates=json.loads((ROOT/'docs/release_gates.json').read_bytes())
 assert gates['round']==10 and gates['tests']['status']=='passed' and gates['freeze'] is None and gates['status']=='NOT READY'
 out=ROOT/'benchmarks/results/round10'
 paths=[p for p in out.iterdir() if p.suffix in {'.json','.csv','.md'} and p.name!='evidence_locks.json']
 paths.extend(ROOT/p for p in ['benchmarks/manifests/official_unknown_v2.json','benchmarks/reference/reference_truth_v2_round10_addendum.json','docs/ROUND10_BASELINE_AUDIT.md','docs/ROUND10_REPORT.md','docs/BENCHMARK.md','docs/FINGERPRINT_COVERAGE_AUDIT.md','docs/REFERENCE_TRUTH_V2.md','docs/release_gates.json','benchmarks/latest_summary.json'])
 hashes={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}
 old_paths=subprocess.check_output(['git','ls-tree','-r','--name-only',BASELINE,'benchmarks/results/round6','benchmarks/results/round7','benchmarks/results/round8','benchmarks/results/round9'],cwd=ROOT,text=True).splitlines()
 old_paths.extend(['benchmarks/manifests/official_unknown_v1.json','benchmarks/reference/reference_truth_v2.json','data/document_recognition_fingerprints_v3.json','data/recognition_profiles/fingerprint_decision_v5.json'])
 historical={}
 for path in old_paths:
  original=subprocess.check_output(['git','show',BASELINE+':'+path],cwd=ROOT);current=(ROOT/path).read_bytes()
  assert current==original or current.replace(b'\r\n',b'\n')==original,path
  historical[path]=hashlib.sha256(original).hexdigest()
 for path,sha in json.loads((ROOT/'benchmarks/results/round8/baseline/metrics.json').read_bytes())['prior_raw_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==sha,path
 atomic_json(out/'evidence_locks.json',dict(schema_version=1,status='NOT READY',baseline_commit=BASELINE,sha256=hashes,historical_original_git_sha256=historical,scope='R10 evidence byte locks, not an engine freeze. Historical original Git hashes separate from preexisting workspace CRLF; all physical R6/R7 hashes additionally verified.'))
 print('Locked R10',len(hashes),'historical',len(historical))

if __name__=='__main__':main()
