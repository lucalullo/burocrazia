"""Final read-only R10 audit; no evaluation or catalog mutation."""
import hashlib,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from benchmarks.round3_audit import read
from benchmarks.transactional_writer import atomic_json
from benchmarks.unknown_v2 import validate
from src.benchmark_display import load_summary
from src.fingerprint_v3 import read_bundle

def main():
 baseline='8c13da270fe2c4db212ca3611fb5ce0ddef7b0d8'
 changes=subprocess.check_output(['git','diff','--name-only',baseline,'--','src','app.py','run.py','data'],cwd=ROOT,text=True).splitlines()
 assert not changes,changes
 manifest=validate(read('benchmarks/manifests/official_unknown_v2.json'))
 for c in manifest['cases']:assert hashlib.sha256((ROOT/'benchmarks/cache'/(c['SHA256']+'.body')).read_bytes()).hexdigest()==c['SHA256']
 active={r['document_id'] for r in read_bundle()['records'] if r['status']=='active'}
 fixed={c['document_id'] for c in read('benchmarks/results/round6/resource_audit.json')['cases'] if c['expected_resource_type']=='file_backed_document'}
 assert len(active)==941 and len(fixed)==1158 and len(active&fixed)==941
 latest=load_summary(ROOT/'benchmarks/latest_summary.json');assert latest['round']==10
 assert latest['fingerprint_coverage']['operational_docs_total']==1212
 assert latest['fingerprint_coverage']['fingerprinted_all_operational_docs']==941
 assert not read('benchmarks/results/round10/prerequisite_gate.json')['ready_to_freeze']
 dev=read('benchmarks/results/round10/unknown_development.json');assert dev['expected_count']==dev['actual_count']==dev['unique_case_ids']==75 and dev['evaluation_recognition_calls']==0
 archives={}
 for name,sha in [('BurOCRazia-v0.7.0-candidate-NOT-READY-round8.zip','d1b8cf63e9f4b857bccb61942e0b52e2a36badeae7213be41aca33478909752a'),('BurOCRazia-v0.7.0-candidate-NOT-READY-round9.zip','4eb297530a7ab2854e1d10004fcaec6d73ddb5771810e13d9210540a865e4517')]:
  actual=hashlib.sha256((ROOT/'dist'/name).read_bytes()).hexdigest();assert actual==sha;archives[name]=actual
 for p in (ROOT/'benchmarks/results/round10').iterdir():
  if p.suffix in {'.json','.csv','.md'}:
   raw=p.read_bytes();assert not re.search(rb'C:\\+(?:Users|users)\\',raw),p.name
   if p.suffix=='.json':json.loads(raw)
 atomic_json(ROOT/'benchmarks/results/round10/prepackage_audit.json',dict(runtime_and_catalog_unchanged=True,official_unknown_byte_hashes_verified=len(manifest['cases']),fixed_denominator=1158,active_unique_ids=941,prior_archives_sha256=archives,evaluation_recognition_calls=0,public_artifact_user_paths=0,summary_contract='valid',scope='Read-only local audit; no freeze or evaluation, no source or seed mutation.'))
 print('R10 prepackage audit passed; official unknown bytes',len(manifest['cases']))

if __name__=='__main__':main()
