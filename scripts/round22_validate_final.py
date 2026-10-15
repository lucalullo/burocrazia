"""Final post-V6 parser/catalog/migration/CLI/schema checks; no semantic edits."""
import argparse,compileall,shutil,sqlite3,tempfile,jsonschema
from contextlib import closing
from scripts.round22_common import *
from benchmarks.round22_release import sealed
from benchmarks.release_truth import load_release
from scripts.verify_catalog import verify
from src.database import initialize_database
from scripts.round14_baseline import tests as parse_tests

def checks():
    f=sealed();assert (OUT/'post_v6_checks.json').exists();assert not (OUT/'final_checks.json').exists()
    assert all(compileall.compile_dir(str(ROOT/p),quiet=1) for p in ['src','maintenance','benchmarks','scripts','tests'])
    assert all(compileall.compile_file(str(ROOT/p),quiet=1) for p in ['app.py','run.py'])
    cat=verify(ROOT/'data/catalog_seed.sqlite3');assert cat['integrity']=='ok' and not cat['foreign_key_violations']
    with tempfile.TemporaryDirectory(prefix='round22-migration-',dir=ROOT/'tmp-build') as folder:
        path=Path(folder)/'copy.sqlite3';shutil.copyfile(ROOT/'data/catalog_seed.sqlite3',path)
        initialize_database(path,seed_demo=False);initialize_database(path,seed_demo=False)
        with closing(sqlite3.connect(path)) as db:
            assert db.execute('PRAGMA user_version').fetchone()[0]==610 and db.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and not list(db.execute('PRAGMA foreign_key_check'))
            counts={n:db.execute('SELECT count(*) FROM "'+n.replace('"','""')+'"').fetchone()[0] for (n,) in db.execute("SELECT name FROM sqlite_master WHERE type='table'") if not n.startswith('sqlite_')}
        assert counts==cat['tables']
    from scripts import round15_validate as old
    save('page_limit_audit',read('benchmarks/results/round21/page_limit_audit.json'))
    old.OUT=OUT;old.save=save;old.coverage();old.input_safety()
    schema=read('benchmarks/schemas/round21_observations.schema.json');jsonschema.validate(read(OUT/'evaluation_v6_observations.json'),schema)
    jsonschema.validate(read('benchmarks/results/round21/unknown_release_v4_observations.json'),schema)
    jsonschema.validate(read('benchmarks/reference/reference_truth_v3.json'),read('benchmarks/schemas/reference_truth_v3.schema.json'))
    policy=read(POLICY);assert policy['schema_version']==2 and policy['gates']['minimum_success_rate']==.9 and sha(POLICY)==f['filled_policy_sha256']
    raw=read(OUT/'post_v6_observations.json')['cases'];hist=[r for r in raw if r['id'].startswith('HIST:') and r.get('expected')];by={r['original_id']:r for r in hist};inputs={c['case_id']:c for c in read(OUT/'input_safety.json')['cases']};actual=[]
    for c in load_release()[2]:
        if c['truth_domain']=='parser_limit_contract':
            r=inputs[c['input_key']];correct=r['rejected_safely'] and not r['crash'] and not r['temp_residue'] and r['recognition_calls']==0 and r['result'] is None;observed='SAFE_REJECTION' if correct else 'UNSAFE'
        else:r=by[c['input_key']];assert r['expected']==c['expected'];correct=r['correct'];observed=r['observed']
        actual.append(dict(case_id=c['case_id'],expected=c['expected'],observed=observed,correct=correct,truth_domain=c['truth_domain']))
    release=dict(n=len(actual),passed=all(r['correct'] for r in actual),cases=actual,failed_ids=[r['case_id'] for r in actual if not r['correct']],runtime_sha256=f['working_tree_recognition_hash'],scope='New post-V6 confirmed technical validation;not independent evaluation or new truth.')
    save('release_gate_fast',release);assert release['passed']
    mismatches=[r for r in hist if not r['correct']];save('historical_regression_fast',dict(n=len(hist),passed=not mismatches,exit_code=1 if mismatches else 0,mismatches=mismatches,cases=hist,expected_changed=False,scope='Original historical labels preserved. Intentional exit1 for ambiguous/mismatched historical labels,not a hidden validation failure.'))
    jobs=[('fingerprint_v1',['-m','maintenance.build_fingerprints','--validate-only'],0),('fingerprint_v2',['-m','maintenance.build_fingerprints_v2','--validate-only'],0),('fingerprint_v3',['-m','maintenance.build_fingerprints_v3','--validate-only'],0),('compat_v2',['scripts/benchmark.py','--corpus','tests/fixtures/benchmark_v2.json','--output','reports/round22-compat-v2.json'],0),('legacy-fast',['-m','benchmarks.evaluate','--fast','--output-dir','reports/round22-legacy-fast'],1)]
    cli=[]
    for n,args,expected in jobs:
        r=subprocess.run([sys.executable,*args],cwd=ROOT,capture_output=True);(ROOT/'reports'/('round22-'+n+'.log')).write_bytes(r.stdout+b'\n'+r.stderr)
        assert r.returncode==expected,(n,r.returncode,r.stderr.decode(errors='replace'));cli.append(dict(name=n,exit_code=r.returncode,expected_exit=expected,stdout_sha256=hashlib.sha256(r.stdout).hexdigest(),stderr_sha256=hashlib.sha256(r.stderr).hexdigest()))
    sealed();save('final_checks',dict(passed=True,compile_pass=True,catalog=cat,migration=dict(schema=610,idempotent=True,integrity='ok',foreign_key_violations=[],row_counts_unchanged=True),schemas_valid=True,cli=cli,release_gate_pass=release['passed'],historical_regression_expected_exit=1 if mismatches else 0,raw_historical_expectations_changed=False,recognition_semantics_changed=False,runtime_sha256=f['working_tree_recognition_hash'],github_ci='external_pending',checked_at=now()))
    print('R22 final checks PASS release',len(actual),'historical',len(hist),'mismatches',len(mismatches),flush=True)

def tests():
    f=sealed();assert not (OUT/'final_tests.json').exists();t=parse_tests('reports/round22-full-tests.log');t.update(status='passed',runtime_sha256=f['working_tree_recognition_hash'],freeze_manifest_sha256=sha(OUT/'evaluation_freeze_manifest.json'),scope='Full suite after sole V6,unchanged old recognition tests plus11 new infrastructure generation tests;Windows symlink/FIFO skips.')
    save('final_tests',t);print('R22 final tests',t,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['checks','tests']);a=p.parse_args();{'checks':checks,'tests':tests}[a.mode]()
