"""Final current-engine validation; old benchmark results are never rewritten."""
import compileall,shutil,sqlite3,tempfile,jsonschema
from contextlib import closing
from scripts.round19_common import *
from scripts.round14_baseline import tests
from scripts.verify_catalog import verify
from src.database import initialize_database
from benchmarks.release_truth import load_release

def main():
    sealed()
    assert all(compileall.compile_dir(str(ROOT/p),quiet=1) for p in ['src','benchmarks','maintenance','scripts','tests'])
    assert all(compileall.compile_file(str(ROOT/p),quiet=1) for p in ['app.py','run.py'])
    cat=verify(ROOT/'data/catalog_seed.sqlite3');assert cat['integrity']=='ok' and not cat['foreign_key_violations']
    with tempfile.TemporaryDirectory(prefix='round19-migration-',dir=ROOT/'tmp-build') as folder:
        path=Path(folder)/'seed-copy.sqlite3';shutil.copyfile(ROOT/'data/catalog_seed.sqlite3',path)
        initialize_database(path,seed_demo=False);initialize_database(path,seed_demo=False)
        with closing(sqlite3.connect(path)) as db:
            schema=db.execute('PRAGMA user_version').fetchone()[0]
            names=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'") if not r[0].startswith('sqlite_')]
            counts={n:db.execute('SELECT count(*) FROM "'+n.replace('"','""')+'"').fetchone()[0] for n in names}
            integrity=db.execute('PRAGMA integrity_check').fetchone()[0];fk=list(db.execute('PRAGMA foreign_key_check'))
        assert schema==610 and integrity=='ok' and not fk and counts==cat['tables']
    load_release();jsonschema.validate(read(TRUTH),read('benchmarks/schemas/reference_truth_v3.schema.json'))
    if (OUT/'evaluation_v5_observations.json').exists():jsonschema.validate(read(OUT/'evaluation_v5_observations.json'),read('benchmarks/schemas/round19_evaluation_observations.schema.json'))
    jobs=[('fingerprint_v1_validate',['-m','maintenance.build_fingerprints','--validate-only'],0),('fingerprint_v2_validate',['-m','maintenance.build_fingerprints_v2','--validate-only'],0),('fingerprint_v3_validate',['-m','maintenance.build_fingerprints_v3','--validate-only'],0),('compat_v2',['scripts/benchmark.py','--corpus','tests/fixtures/benchmark_v2.json','--output','reports/round19-cli-compat-v2.json'],0),('historical_legacy_fast',['-m','benchmarks.evaluate','--fast','--output-dir','reports/round19-legacy-fast'],1),('release-gate-fast',['-m','benchmarks.round19_gates','release-gate-fast'],0),('historical-regression-fast',['-m','benchmarks.round19_gates','historical-regression-fast'],1)]
    cli=[]
    for name,args,expected in jobs:
        r=subprocess.run([sys.executable,*args],cwd=ROOT,capture_output=True)
        (ROOT/'reports'/('round19-'+name+'.log')).write_bytes(r.stdout+b'\n'+r.stderr)
        cli.append(dict(name=name,args=args,exit_code=r.returncode,expected_exit=expected,stdout_sha256=hashlib.sha256(r.stdout).hexdigest(),stderr_sha256=hashlib.sha256(r.stderr).hexdigest()))
        assert r.returncode==expected,(name,r.stderr.decode(errors='replace'))
        print('R19 final CLI',name,'exit',r.returncode,flush=True)
    failed=[c['id'] for c in read('reports/round19-legacy-fast/development_regression.json')['cases'] if not c['correct']]
    assert set(failed)=={'EX02','EX03'}
    assert len(read(OUT/'historical_regression_fast.json')['mismatches'])==15
    save('final_checks',dict(passed=True,compile_pass=True,catalog=cat,migration=dict(schema=schema,integrity=integrity,foreign_key_violations=fk,row_counts_unchanged=True,idempotent=True),cli=cli,legacy_fast_failed_ids=failed,benchmark_schema_valid=True,engine_invariant=True,unknown_v3_replayed=False,checked_at=now(),ci='external_pending'))

if __name__=='__main__':main()
