"""Catalog, immutable historical bytes, source safety and local workflow checks."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from benchmarks.round3_audit import read,catalog
from benchmarks.evaluate import verify_locks
from benchmarks.round8_common import case_result
from benchmarks.transactional_writer import atomic_json
from benchmarks.truth_v2 import validate_registry,validate_unknown
from scripts.verify_catalog import verify

def main():
    verify_locks();validate_registry(read('benchmarks/reference/reference_truth_v2.json'));validate_unknown(read('benchmarks/manifests/official_unknown_v1.json'))
    seed=verify(ROOT/'data/catalog_seed.sqlite3');assert seed['sha256']=='790b690123c82e1cb7bdfa67a10216284022987d50b0abbcc4a1a245785e3e99'
    historical={}
    paths=subprocess.check_output(['git','ls-tree','-r','--name-only','fa2a307','benchmarks/results/round8','benchmarks/results/round7','benchmarks/results/round6'],cwd=ROOT,text=True).splitlines()
    for path in paths:
        raw=(ROOT/path).read_bytes();old=subprocess.check_output(['git','show','fa2a307:'+path],cwd=ROOT)
        assert raw==old or raw.replace(b'\r\n',b'\n')==old,path
        historical[path]=hashlib.sha256(raw).hexdigest()
    baseline=read('benchmarks/results/round8/baseline/metrics.json')
    for path,sha in baseline['prior_raw_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==sha,path
    five=[];docs,families=catalog()
    for c in read('benchmarks/manifests/official_holdout_v1.json')['cases']:
        if c['id'] not in {'OH1-033','OH1-047','OH1-055','OH1-063','OH1-098'}:continue
        cc=dict(id=c['id'],group=c['sha256'],category='historical_safety',expected=dict(match_type=c['expected_match_type'],document_id=c.get('document_id')),label_status='historical_only',representation='official_original')
        raw=(ROOT/'benchmarks/cache'/(c['sha256']+'.body')).read_bytes();row=case_result(cc,raw,'input.'+c['format'],docs,families)
        row['safe']=row['observed']['match_type']=='NO_MATCH' or row['observed']['match_type']=='DOCUMENT_MATCH' and row['observed']['document_id']==c.get('document_id')
        five.append(row)
    assert len(five)==5 and all(r['safe'] for r in five)
    workflow=(ROOT/'.github/workflows/tests.yml').read_text(encoding='utf8');assert 'pytest' in workflow and 'verify_catalog' in workflow and 'macos' in workflow and 'windows' in workflow and 'ubuntu' in workflow and '--allow-network' not in workflow
    import yaml
    assert yaml.safe_load(workflow).get('jobs')
    atomic_json(ROOT/'benchmarks/results/round9/verification.json',dict(catalog=seed,historical_raw_sha256=historical,prior_workspace_raw_hashes_verified=len(baseline['prior_raw_sha256']),historical_byte_scope='Original tracked Git bytes or preexisting CRLF/LF serialization difference; all110 R6/R7 physical hashes also strict. No old raw rewritten.',historical_five=five,historical_five_passed=True,workflow_local='syntax and declared offline matrix/commands validated; full local test/catalog/benchmark executions separate',github_ci='external_pending',push=False,tag=False,release=False))
    print('Verified catalog/history/workflow; critical five',len(five))
if __name__=='__main__':main()
