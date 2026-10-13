"""Final prepackage audit and byte locks; this does not freeze the engine."""
import hashlib,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from benchmarks.round3_audit import read
from benchmarks.transactional_writer import atomic_json
from benchmarks.unknown_release import validate,select
from src.benchmark_display import load_summary
from src.fingerprint_v3 import read_bundle
from scripts.verify_catalog import verify
BASELINE='d19547f458e46d38c11a84ffd9e2f735510ac5bc'
OUT=ROOT/'benchmarks/results/round11'

def main():
 master=validate(read('benchmarks/manifests/official_unknown_master_v1.json'));release=validate(read('benchmarks/manifests/official_unknown_release_v1.json'))
 assert {c['case_id'] for c in select(master['cases'])}=={c['case_id'] for c in release['cases']}
 assert {c['case_id'] for c in read('benchmarks/manifests/official_unknown_v2.json')['cases']}<={c['case_id'] for c in master['cases']}
 for c in master['cases']:assert hashlib.sha256((ROOT/'benchmarks/cache'/(c['SHA256']+'.body')).read_bytes()).hexdigest()==c['SHA256']
 dev=read('benchmarks/results/round11/unknown_development_observations.json');assert dev['identity']['manifest_sha256']==hashlib.sha256((ROOT/'benchmarks/manifests/official_unknown_master_v1.json').read_bytes()).hexdigest()
 seed=verify(ROOT/'data/catalog_seed.sqlite3');assert seed['sha256']=='790b690123c82e1cb7bdfa67a10216284022987d50b0abbcc4a1a245785e3e99' and seed['integrity']=='ok'
 original_raw=subprocess.check_output(['git','show',BASELINE+':data/document_recognition_fingerprints_v3.json'],cwd=ROOT);original=json.loads(original_raw);bundle=read_bundle();assert bundle['records'][:len(original['records'])]==original['records']
 restored=(json.dumps(dict(bundle,records=bundle['records'][:len(original['records'])]),ensure_ascii=False,indent=2)+'\n').encode();assert restored==original_raw
 archives={}
 for n in [8,9,10]:
  manifest=read(f'dist/package-verification-round{n}.json');path=ROOT/'dist'/manifest['archive'];sha=hashlib.sha256(path.read_bytes()).hexdigest();assert sha==manifest['sha256'];archives[path.name]=sha
 summary=load_summary(ROOT/'benchmarks/latest_summary.json');assert summary['round']==11 and summary['status']=='NOT READY'
 gates=read('docs/release_gates.json');assert gates['round']==11 and gates['tests']['status']=='passed' and gates['freeze'] is None
 for p in OUT.iterdir():
  if p.suffix in {'.json','.csv','.md'}:assert not re.search(rb'C:\\+(?:Users|users)\\',p.read_bytes()),p.name
 atomic_json(OUT/'prepackage_audit.json',dict(catalog=seed,official_unknown_hashes_verified=len(master['cases']),prior_archives_sha256=archives,prior_fingerprint_records_preserved=len(original['records']),prior_fingerprint_sha256=hashlib.sha256(restored).hexdigest(),prior_fingerprint_restore='Select first1027 records from current bundle; serialize UTF8 ensure_ascii=False indent=2 with trailing LF. Exact original Git bytes verified; no duplicate50MB required.',summary_contract='valid',release_selection_reproducible=True,release_recognition_calls=0))
 paths=[p for p in OUT.iterdir() if p.suffix in {'.json','.csv','.md'} and p.name!='evidence_locks.json']
 paths.extend(ROOT/p for p in ['benchmarks/manifests/official_fingerprint_cache_v6.json','benchmarks/manifests/official_unknown_master_v1.json','benchmarks/manifests/official_unknown_release_v1.json','benchmarks/reference/reference_truth_v2_round11_addendum.json','docs/ROUND11_BASELINE_AUDIT.md','docs/ROUND11_REPORT.md','docs/BENCHMARK.md','docs/FINGERPRINT_COVERAGE_AUDIT.md','docs/SOURCES.md','docs/release_gates.json','benchmarks/latest_summary.json'])
 hashes={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}
 historical={}
 old_paths=subprocess.check_output(['git','ls-tree','-r','--name-only',BASELINE,*[f'benchmarks/results/round{n}' for n in [6,7,8,9,10]]],cwd=ROOT,text=True).splitlines()
 old_paths+=['benchmarks/manifests/official_unknown_v1.json','benchmarks/manifests/official_unknown_v2.json','benchmarks/reference/reference_truth_v2.json','benchmarks/reference/reference_truth_v2_round10_addendum.json','data/recognition_profiles/fingerprint_decision_v5.json']
 for path in old_paths:
  raw=subprocess.check_output(['git','show',BASELINE+':'+path],cwd=ROOT);current=(ROOT/path).read_bytes();assert current==raw or current.replace(b'\r\n',b'\n')==raw,path;historical[path]=hashlib.sha256(raw).hexdigest()
 for p,sha in read('benchmarks/results/round8/baseline/metrics.json')['prior_raw_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==sha
 atomic_json(OUT/'evidence_locks.json',dict(schema_version=1,status='NOT READY',baseline_commit=BASELINE,sha256=hashes,historical_original_git_sha256=historical,scope='R11 evidence locks, not a freeze. Original v3 data is exactly reconstructible and prior archive retained; old raw/corpus/physical hashes unchanged.'))
 print('R11 verified/locked',len(hashes),'historical',len(historical),flush=True)

if __name__=='__main__':main()
