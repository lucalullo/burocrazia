"""Final offline checks on the stopped candidate; never launch a release gate."""
import compileall,shutil,sqlite3,subprocess,tempfile,jsonschema
from contextlib import closing
from scripts.round15_common import *
from scripts.round14_baseline import perf_check,tests
from scripts.verify_catalog import verify
from src.database import initialize_database
from benchmarks.round4_common import runtime_hash
from src.fingerprint_v3 import read_bundle
from src.document_fingerprints import binding
from benchmarks.round3_audit import catalog

def main():
    p=read(OUT/'performance_pre_freeze.json');perf=perf_check(p)
    assert p['identity']['runtime_sha256']==runtime_hash(),'Runtime differs from the measured performance engine'
    assert p['identity']['fingerprint_sha256']==sha('data/document_recognition_fingerprints_v3.json')
    for name in ['canonical','canonical_legacy','development_regression_after_round15_fix']:
        measured=read(OUT/(name+'.json'))['identity']
        assert measured['runtime_sha256']==runtime_hash(),name
        assert measured['fingerprint_sha256']==sha('data/document_recognition_fingerprints_v3.json'),name
    test=tests('reports/round15-final-tests.log');test.update(status='passed');save('tests',test)
    compile_pass=all(compileall.compile_dir(str(ROOT/p),quiet=1) for p in ['src','maintenance','benchmarks','scripts'])
    compile_pass &= all(compileall.compile_file(str(ROOT/p),quiet=1) for p in ['app.py','run.py']);assert compile_pass
    cat=verify(ROOT/'data/catalog_seed.sqlite3');assert cat['integrity']=='ok' and not cat['foreign_key_violations']
    with tempfile.TemporaryDirectory(prefix='round15-migration-',dir=ROOT/'tmp-build') as folder:
        path=Path(folder)/'seed-copy.sqlite3';shutil.copyfile(ROOT/'data/catalog_seed.sqlite3',path);initialize_database(path,seed_demo=False)
        with closing(sqlite3.connect(path)) as db:
            schema=db.execute('PRAGMA user_version').fetchone()[0]
            names=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'") if not r[0].startswith('sqlite_')]
            migrated=dict(integrity=db.execute('PRAGMA integrity_check').fetchone()[0],foreign_key_violations=list(db.execute('PRAGMA foreign_key_check')),tables={n:db.execute('SELECT count(*) FROM "'+n.replace('"','""')+'"').fetchone()[0] for n in names})
        assert schema==610 and migrated['integrity']=='ok' and not migrated['foreign_key_violations'] and migrated['tables']==cat['tables']
    truth=read('benchmarks/reference/reference_truth_v3.json');jsonschema.validate(truth,read('benchmarks/schemas/reference_truth_v3.schema.json'),format_checker=jsonschema.FormatChecker())
    assert len({c['case_id'] for c in truth['cases']})==7
    assert all(not c['release_gate_eligible'] for c in truth['cases'])
    evidence=read(OUT/'official_truth_evidence.json')
    for c in evidence['files']:
        h=c.get('canonical_sha256') or c['receipt']['sha256']
        assert sha('benchmarks/cache/'+h+'.body')==h
    anac=next(c for c in evidence['files'] if c.get('document_id')==615)
    record=next(r for r in read_bundle()['records'] if r['document_id']==615)
    assert anac['official_url']==record['url'] and anac['canonical_sha256']==record['canonical_file_sha256']
    safety=read(OUT/'input_safety.json');manifest=read('benchmarks/manifests/input_safety_v1.json')
    assert safety['passed'] and safety['safe_rejects']==safety['n']==len(manifest['cases'])==9
    assert {c['case_id']:c['SHA256'] for c in manifest['cases']}=={c['case_id']:c['input_sha256'] for c in safety['cases']}
    docs,_=catalog();by={d.id:d for d in docs}
    for r in read_bundle()['records']:
        if r['status']=='active':assert r['catalog_binding_sha256']==binding(by[r['document_id']])
    for path in ['data/catalog_seed.sqlite3','data/document_recognition_fingerprints_v3.json','data/recognition_profiles/fingerprint_decision_v5.json']:
        assert (ROOT/path).read_bytes()==subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT),path
    cli=[]
    jobs=[('fingerprint_v1_validate',['-m','maintenance.build_fingerprints','--validate-only']),('fingerprint_v2_validate',['-m','maintenance.build_fingerprints_v2','--validate-only']),('fingerprint_v3_validate',['-m','maintenance.build_fingerprints_v3','--validate-only']),
          ('compat_v2',['scripts/benchmark.py','--corpus','tests/fixtures/benchmark_v2.json','--output','reports/round15-cli-compat-v2.json']),('release_fast',['-m','benchmarks.evaluate','--fast','--output-dir','reports/round15-fast'])]
    for name,args in jobs:
        r=subprocess.run([sys.executable,*args],cwd=ROOT,capture_output=True)
        cli.append(dict(name=name,args=args,exit_code=r.returncode,passed=r.returncode==0,stdout_sha256=hashlib.sha256(r.stdout).hexdigest(),stderr_sha256=hashlib.sha256(r.stderr).hexdigest()))
        print('Round15 final check',name,'exit',r.returncode,flush=True)
    fast={p.stem:read(p) for p in (ROOT/'reports/round15-fast').glob('*.json')};fail=[c['id'] for c in fast['development_regression']['cases'] if not c['correct']]
    assert set(fail)=={'EX02','EX03'},'Unexpected historical release-fast regression'
    assert all(c['passed'] for c in cli if c['name']!='release_fast')
    h=historical();archives={}
    for n in range(8,15):
        report=read(f'dist/package-verification-round{n}.json');assert sha('dist/'+report['archive'])==report['sha256'];archives[report['archive']]=report['sha256']
    save('final_checks',dict(status='NOT READY',compile_pass=compile_pass,catalog=cat,migration=dict(schema=schema,integrity=migrated['integrity'],foreign_key_violations=migrated['foreign_key_violations'],row_counts_unchanged=True),
        benchmark_schema_validation=True,canonical_hash_binding_integrity=True,truth_v3_schema_valid=True,input_safety_count_hash_valid=True,performance=perf,performance_runtime_binding=True,cli=cli,
        release_fast_exit=next(c['exit_code'] for c in cli if c['name']=='release_fast'),release_fast_historical_failed_ids=fail,release_fast_scope='Actual nonzero exit retained, historical EX02/EX03 unchanged; not a green CLI claim.',
        prior_archives_sha256=archives,historical_git_blobs_verified=len(h),checked_at=now(),freeze_created=False,release_predictions=0))
    save('historical_locks',dict(baseline_commit=BASE,historical_original_git_sha256=h,prior_archives_sha256=archives))
    print('Round15 checks complete; actual performance and release-fast gates FAIL, no freeze/release bench',flush=True)

if __name__=='__main__':main()
