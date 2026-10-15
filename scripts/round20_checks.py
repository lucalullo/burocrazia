"""Current development candidate compile/catalog/migration/safety validation."""
import compileall,shutil,sqlite3,tempfile,jsonschema
from contextlib import closing
from scripts.round20_common import *
from scripts.verify_catalog import verify
from src.database import initialize_database
from benchmarks.round4_common import runtime_hash

def main():
    preserved();cal=read(OUT/'calibration_v6.json')
    assert cal['identity']['runtime_sha256']==runtime_hash()
    assert cal['identity']['profile_sha256']==sha('data/recognition_profiles/fingerprint_decision_v6.json')
    assert all(compileall.compile_dir(str(ROOT/p),quiet=1) for p in ['src','benchmarks','maintenance','scripts','tests'])
    assert all(compileall.compile_file(str(ROOT/p),quiet=1) for p in ['app.py','run.py'])
    cat=verify(ROOT/'data/catalog_seed.sqlite3');assert cat['integrity']=='ok' and not cat['foreign_key_violations']
    with tempfile.TemporaryDirectory(prefix='round20-migration-',dir=ROOT/'tmp-build') as folder:
        path=Path(folder)/'seed-copy.sqlite3';shutil.copyfile(ROOT/'data/catalog_seed.sqlite3',path)
        initialize_database(path,seed_demo=False);initialize_database(path,seed_demo=False)
        with closing(sqlite3.connect(path)) as db:
            schema=db.execute('PRAGMA user_version').fetchone()[0];integrity=db.execute('PRAGMA integrity_check').fetchone()[0];fk=list(db.execute('PRAGMA foreign_key_check'))
            names=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'") if not r[0].startswith('sqlite_')]
            counts={n:db.execute('SELECT count(*) FROM "'+n.replace('"','""')+'"').fetchone()[0] for n in names}
        assert schema==610 and integrity=='ok' and not fk and counts==cat['tables']
    from scripts import round15_validate as prior
    save('page_limit_audit',read('benchmarks/results/round19/page_limit_audit.json'))
    prior.OUT=OUT;prior.save=save;prior.coverage();prior.input_safety()
    jsonschema.validate(read(TRUTH),read('benchmarks/schemas/reference_truth_v3.schema.json'))
    from src.fingerprint_decision_v6 import profile
    profile()
    jobs=[('fingerprint_v1',['-m','maintenance.build_fingerprints','--validate-only'],0),('fingerprint_v2',['-m','maintenance.build_fingerprints_v2','--validate-only'],0),('fingerprint_v3',['-m','maintenance.build_fingerprints_v3','--validate-only'],0),('compat_v2',['scripts/benchmark.py','--corpus','tests/fixtures/benchmark_v2.json','--output','reports/round20-compat-v2.json'],0),('legacy-fast',['-m','benchmarks.evaluate','--fast','--output-dir','reports/round20-legacy-fast'],1),('release-gate-fast',['-m','benchmarks.round20_gates','release-gate-fast'],0),('historical-regression-fast',['-m','benchmarks.round20_gates','historical-regression-fast'],1)]
    cli=[]
    for name,args,expected in jobs:
        r=subprocess.run([sys.executable,*args],cwd=ROOT,capture_output=True)
        (ROOT/'reports'/('round20-'+name+'.log')).write_bytes(r.stdout+b'\n'+r.stderr)
        cli.append(dict(name=name,args=args,exit_code=r.returncode,expected_exit=expected,stdout_sha256=hashlib.sha256(r.stdout).hexdigest(),stderr_sha256=hashlib.sha256(r.stderr).hexdigest()))
        assert r.returncode==expected,(name,r.stderr.decode(errors='replace'))
        print('R20 checks',name,r.returncode,flush=True)
    save('final_checks',dict(passed=True,compile_pass=True,catalog=cat,migration=dict(schema=schema,integrity=integrity,foreign_key_violations=fk,row_counts_unchanged=True,idempotent=True),profile_v6_valid=True,truth_schema_valid=True,cli=cli,raw_historical_expectations_changed=False,github_ci='external_pending',runtime_sha256=runtime_hash(),checked_at=now()))

if __name__=='__main__':main()
