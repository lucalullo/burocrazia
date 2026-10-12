"""Local catalog/bootstrap/lock/CLI evidence on a separate temporary database."""
import hashlib,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from benchmarks.round8_common import read,write,OUT,checked
from benchmarks.evaluate import verify_locks
from scripts.verify_catalog import verify
from src.bootstrap import prepare_database

def main():
    frozen=checked();verify_locks()
    for path,digest in read(OUT+'baseline/metrics.json')['prior_raw_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest,path
    target=ROOT/'tmp-build/round8-bootstrap.sqlite3'
    if target.exists():target.unlink()
    prepare_database(target);bootstrap=verify(target);assert bootstrap['integrity']=='ok' and not bootstrap['foreign_key_violations']
    subprocess.run([sys.executable,'-m','compileall','-q','src','maintenance','benchmarks','scripts','app.py','run.py'],check=True,cwd=ROOT)
    commands=[['-m','maintenance.build_fingerprints','--validate-only'],['-m','maintenance.build_fingerprints_v2','--validate-only'],['-m','maintenance.build_fingerprints_v3','--validate-only'],['scripts/benchmark.py','--output',OUT+'development_cli.json'],['scripts/benchmark.py','--corpus','tests/fixtures/benchmark_v2.json','--output',OUT+'development_compat_cli.json']];rows=[]
    for command in commands:
        r=subprocess.run([sys.executable,*command],cwd=ROOT,capture_output=True,text=True);rows.append(dict(command='python '+' '.join(command),exit_code=r.returncode,stderr=r.stderr[-500:]))
    seed=verify(ROOT/'data/catalog_seed.sqlite3');assert seed['sha256']=='790b690123c82e1cb7bdfa67a10216284022987d50b0abbcc4a1a245785e3e99';checked()
    from src.fingerprint_v3 import read_bundle,public_index
    ix=public_index();resources=[]
    for r in read_bundle()['records']:
        sha=r['canonical_file_sha256'];raw=(ROOT/'benchmarks/cache'/(sha+'.body')).read_bytes();assert hashlib.sha256(raw).hexdigest()==sha
        resources.append(dict(document_id=r['document_id'],sha256=sha,status=r['status'],exact_resource_found=r['document_id'] in ix.sha.get(sha,set())))
    write(OUT+'canonical_resource_lookup.json',dict(cases=resources,bindings=len(resources),unique_resources=len({r['sha256'] for r in resources}),matched_bindings=sum(r['exact_resource_found'] for r in resources),scope='Exact bytes lookup only. A shared resource lookup does not identify a document. Canonical identity precision/recall is measured independently on unambiguous active resources.'))
    write(OUT+'ci_local.json',dict(catalog=seed,bootstrap='passed on separate temporary database',compileall='passed',historical_raw_unchanged=True,commands=rows,freeze=frozen,external_ci='pending_external_gate',platform_scope='Local Windows Python3.12 only; configured Ubuntu/macOS/Windows matrix not executed remotely; normal CI has no official cache requirement.'))
    print('Local catalog/bootstrap/locks/CLI checks saved',flush=True)
if __name__=='__main__':main()
