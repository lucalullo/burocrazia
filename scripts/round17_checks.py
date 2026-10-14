"""Final local tests, catalog/migration and real CLI exit evidence."""
import compileall,shutil,sqlite3,tempfile,jsonschema,re
from contextlib import closing
from scripts.round17_common import *
from scripts.round14_baseline import tests
from scripts.verify_catalog import verify
from src.database import initialize_database
from benchmarks.round4_common import runtime_hash
from benchmarks.release_truth import load_release

def main():
    raw=(ROOT/'reports/round17-prefreeze-tests.log').read_bytes()
    line=raw.splitlines()[-1].decode('utf8')
    def count(label):
        m=re.search(r'(\d+) '+label,line);return int(m[1]) if m else 0
    elapsed=re.search(r'in ([\d.]+)s',line);assert elapsed and count('passed')>0
    save('tests',dict(passed=count('passed'),failed=count('failed'),skipped=count('skipped'),seconds=float(elapsed[1]),log_sha256=hashlib.sha256(raw).hexdigest(),status='passed' if count('failed')==0 else 'failed'))
    assert all(compileall.compile_dir(str(ROOT/p),quiet=1) for p in ['src','benchmarks','maintenance','scripts'])
    assert all(compileall.compile_file(str(ROOT/p),quiet=1) for p in ['app.py','run.py'])
    cat=verify(ROOT/'data/catalog_seed.sqlite3');assert cat['integrity']=='ok' and not cat['foreign_key_violations']
    with tempfile.TemporaryDirectory(prefix='round17-migration-',dir=ROOT/'tmp-build') as folder:
        path=Path(folder)/'seed-copy.sqlite3';shutil.copyfile(ROOT/'data/catalog_seed.sqlite3',path);initialize_database(path,seed_demo=False)
        with closing(sqlite3.connect(path)) as db:
            schema=db.execute('PRAGMA user_version').fetchone()[0]
            names=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'") if not r[0].startswith('sqlite_')]
            migrated=dict(integrity=db.execute('PRAGMA integrity_check').fetchone()[0],foreign_key_violations=list(db.execute('PRAGMA foreign_key_check')),tables={n:db.execute('SELECT count(*) FROM "'+n.replace('"','""')+'"').fetchone()[0] for n in names})
        assert schema==610 and migrated['integrity']=='ok' and not migrated['foreign_key_violations'] and migrated['tables']==cat['tables']
    jsonschema.validate(read(TRUTH),read('benchmarks/schemas/reference_truth_v3.schema.json'),format_checker=jsonschema.FormatChecker());load_release()
    for path in ['data/catalog_seed.sqlite3','data/document_recognition_fingerprints_v3.json','data/recognition_profiles/fingerprint_decision_v5.json']:
        assert (ROOT/path).read_bytes()==subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT),path
    jobs=[('fingerprint_v1_validate',['-m','maintenance.build_fingerprints','--validate-only']),('fingerprint_v2_validate',['-m','maintenance.build_fingerprints_v2','--validate-only']),('fingerprint_v3_validate',['-m','maintenance.build_fingerprints_v3','--validate-only']),('compat_v2',['scripts/benchmark.py','--corpus','tests/fixtures/benchmark_v2.json','--output','reports/round17-cli-compat-v2.json']),('historical_legacy_fast',['-m','benchmarks.evaluate','--fast','--output-dir','reports/round17-legacy-fast']),('release-gate-fast',['-m','benchmarks.round17_gates','release-gate-fast']),('historical-regression-fast',['-m','benchmarks.round17_gates','historical-regression-fast'])]
    cli=[]
    for name,args in jobs:
        r=subprocess.run([sys.executable,*args],cwd=ROOT,capture_output=True)
        cli.append(dict(name=name,args=args,exit_code=r.returncode,stdout_sha256=hashlib.sha256(r.stdout).hexdigest(),stderr_sha256=hashlib.sha256(r.stderr).hexdigest()))
        (ROOT/'reports'/('round17-'+name+'.log')).write_bytes(r.stdout+b'\n'+r.stderr)
        assert r.returncode==(1 if name in ['historical_legacy_fast','historical-regression-fast'] else 0),(name,r.stderr.decode(errors='replace'))
        print('R17 CLI',name,'exit',r.returncode,flush=True)
    fast={p.stem:read(p) for p in (ROOT/'reports/round17-legacy-fast').glob('*.json')};failed=[c['id'] for c in fast['development_regression']['cases'] if not c['correct']];assert set(failed)=={'EX02','EX03'}
    # Include the original metadata-coverage diagnostic without promoting it
    # to official canonical accuracy or rewriting its43 historical refusals.
    if 'catalog_coverage' in fast:save('historical_catalog_coverage',fast['catalog_coverage'])
    h=historical();archives={}
    for n in range(8,17):
        r=read(f'dist/package-verification-round{n}.json');assert sha('dist/'+r['archive'])==r['sha256'];archives[r['archive']]=r['sha256']
    save('historical_locks',dict(baseline_commit=BASE,historical_original_git_sha256=h,prior_archives_sha256=archives))
    save('final_checks',dict(compile_pass=True,catalog=cat,migration=dict(schema=schema,integrity=migrated['integrity'],foreign_key_violations=migrated['foreign_key_violations'],row_counts_unchanged=True),truth_v3_schema_valid=True,truth_policy_hashes_valid=True,seed_dataset_policy_unchanged=True,cli=cli,legacy_fast_exit=1,legacy_fast_failed_ids=failed,release_gate_fast_exit=0,historical_regression_fast_exit=1,historical_git_blobs_verified=len(h),prior_archives_sha256=archives,runtime_sha256=runtime_hash(),checked_at=now(),github_ci='external_pending'))

if __name__=='__main__':main()
