"""Local CI evidence using a separate bootstrap database, never personal data."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from benchmarks.round3_audit import read,write
from benchmarks.round7_recognition import checked
from benchmarks.evaluate import verify_locks
from src.bootstrap import prepare_database
from scripts.verify_catalog import verify

def main():
    frozen=checked();verify_locks()
    for path,item in read('benchmarks/results/round7/baseline/audit.json')['raw'].items():
        p=ROOT/path
        assert hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256'],path
    for path,digest in read('benchmarks/manifests/development_compat_locks_v2.json')['sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest
    target=ROOT/'tmp-build/round7-bootstrap.sqlite3'
    if target.exists():target.unlink()
    prepare_database(target);bootstrap=verify(target)
    assert bootstrap['integrity']=='ok' and not bootstrap['foreign_key_violations']
    subprocess.run([sys.executable,'-m','compileall','-q','src','maintenance','benchmarks','scripts','app.py','run.py'],cwd=ROOT,check=True)
    commands=[['-m','maintenance.build_fingerprints','--validate-only'],['-m','maintenance.build_fingerprints_v2','--validate-only'],['scripts/benchmark.py','--output','benchmarks/results/round7/development_cli.json'],['scripts/benchmark.py','--corpus','tests/fixtures/benchmark_v2.json','--output','benchmarks/results/round7/development_compat_v2.json']]
    rows=[]
    for command in commands:
        result=subprocess.run([sys.executable,*command],cwd=ROOT,capture_output=True,text=True)
        rows.append(dict(command='python '+' '.join(command),exit_code=result.returncode))
        assert result.returncode==(1 if 'tests/fixtures/benchmark_v2.json' in command else 0),rows[-1]
    seed=verify(ROOT/'data/catalog_seed.sqlite3');assert seed['sha256']=='790b690123c82e1cb7bdfa67a10216284022987d50b0abbcc4a1a245785e3e99'
    checked();write('benchmarks/results/round7/ci_local.json',dict(catalog=seed,bootstrap='passed on separate temporary database',compileall='passed',frozen_corpora_and_round6_raw_unchanged=True,commands=rows,freeze=frozen,external_ci='pending_external_gate',platform_scope='Local Windows Python3.12 only; configured Linux/macOS/Windows matrix not executed remotely.'))
    print('Local bootstrap/catalog/locks/CLI evidence saved; compatibility fixture conflict retained')

if __name__=='__main__':main()
