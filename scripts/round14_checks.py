"""Final offline checks after the failed release; never replay unknown v2."""
import compileall,shutil,sqlite3,subprocess,tempfile
from contextlib import closing
from scripts.round14_common import *
from scripts.verify_catalog import verify
from src.database import initialize_database
from benchmarks.round14_unknown import validate_release,validate_observations
from src.fingerprint_v3 import read_bundle
from src.document_fingerprints import binding
from benchmarks.round3_audit import catalog

def main():
    freeze=sealed();assert read('benchmarks/results/round14/unknown_release_v2.json')['passed'] is False
    compilation=all(compileall.compile_dir(str(ROOT/p),quiet=1) for p in ['src','maintenance','benchmarks','scripts'])
    compilation &= all(compileall.compile_file(str(ROOT/p),quiet=1) for p in ['app.py','run.py'])
    assert compilation
    cat=verify(ROOT/'data/catalog_seed.sqlite3');assert cat['integrity']=='ok' and not cat['foreign_key_violations']
    with tempfile.TemporaryDirectory(prefix='round14-migration-',dir=ROOT/'tmp-build') as folder:
        path=Path(folder)/'seed-copy.sqlite3';shutil.copyfile(ROOT/'data/catalog_seed.sqlite3',path);initialize_database(path,seed_demo=False)
        with closing(sqlite3.connect(path)) as db:
            schema=db.execute('PRAGMA user_version').fetchone()[0]
            names=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'") if not r[0].startswith('sqlite_')]
            migrated=dict(integrity=db.execute('PRAGMA integrity_check').fetchone()[0],foreign_key_violations=list(db.execute('PRAGMA foreign_key_check')),
                          tables={name:db.execute('SELECT count(*) FROM "'+name.replace('"','""')+'"').fetchone()[0] for name in names})
        assert schema==610 and migrated['integrity']=='ok' and not migrated['foreign_key_violations'] and migrated['tables']==cat['tables']
    m=validate_release(read('benchmarks/manifests/official_unknown_release_v2.json'));obs=validate_observations(read('benchmarks/results/round14/unknown_release_v2_observations.json'))
    expected={c['case_id']:c['SHA256'] for c in m['cases']};assert {r['id']:r['input_sha256'] for r in obs['cases']}==expected
    assert sha('benchmarks/results/round14/unknown_release_v2_observations.json')==read('benchmarks/results/round14/unknown_release_v2.json')['observations_sha256']
    docs,_=catalog();by={d.id:d for d in docs};records=read_bundle()['records']
    for r in records:
        if r['status']=='active':assert r['catalog_binding_sha256']==binding(by[r['document_id']])
    cli=[]
    jobs=[('fingerprint_v1_validate',['-m','maintenance.build_fingerprints','--validate-only'],0),
          ('fingerprint_v2_validate',['-m','maintenance.build_fingerprints_v2','--validate-only'],0),
          ('fingerprint_v3_validate',['-m','maintenance.build_fingerprints_v3','--validate-only'],0),
          ('compat_v2',['scripts/benchmark.py','--corpus','tests/fixtures/benchmark_v2.json','--output','reports/round14-cli-compat-v2.json'],0),
          ('release_fast',['-m','benchmarks.evaluate','--fast','--output-dir','reports/round14-fast'],1)]
    for name,args,expected_exit in jobs:
        result=subprocess.run([sys.executable,*args],cwd=ROOT,capture_output=True)
        cli.append(dict(name=name,args=args,exit_code=result.returncode,expected_exit=expected_exit,expected_status=result.returncode==expected_exit,
                        stdout_sha256=hashlib.sha256(result.stdout).hexdigest(),stderr_sha256=hashlib.sha256(result.stderr).hexdigest()))
        print('R14 final check',name,'exit',result.returncode,flush=True)
    fast={p.stem:json.loads(p.read_bytes()) for p in (ROOT/'reports/round14-fast').glob('*.json')}
    assert {r['id'] for r in fast['development_regression']['cases'] if not r['correct']}=={'EX02','EX03'}
    save('final_checks',dict(status='verified_with_historical_nonzero_cli',freeze_commit=freeze['freeze_git_commit'],compile_pass=compilation,catalog=cat,
        migration=dict(schema=schema,integrity=migrated['integrity'],foreign_key_violations=migrated['foreign_key_violations'],row_counts_unchanged=migrated['tables']==cat['tables']),
        canonical_hash_binding_integrity=True,canonical_scope='Integrity of executed pre-freeze native/legacy results and byte-identical frozen engine; no post-STOP recognition rerun.',
        benchmark_schema_validation=True,unknown_expected_actual_unique=len(expected),unknown_replays=0,cli=cli,
        release_fast_exit=next(c['exit_code'] for c in cli if c['name']=='release_fast'),
        release_fast_historical_failed_ids=['EX02','EX03'],release_fast_scope='Existing v1 contradictions retained; actual CLI exit1, not a green CLI or CI claim.',
        release_fast_summaries={k:v.get('summary') for k,v in fast.items()},checked_at=now()))
    assert all(c['expected_status'] for c in cli)
    sealed()

if __name__=='__main__':main()
