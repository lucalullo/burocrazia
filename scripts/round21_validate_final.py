"""Final read-only/catalog-copy checks on the sealed runtime; append-only outputs."""
import compileall,shutil,sqlite3,tempfile,jsonschema
from contextlib import closing
from scripts.round21_common import *
from benchmarks.round21_release import sealed
from scripts.round14_baseline import tests as parse_tests
from scripts.verify_catalog import verify
from src.database import initialize_database

def main():
    f=sealed();assert not (OUT/'final_validation_on_freeze.json').exists()
    t=parse_tests('reports/round21-tests-on-freeze.log');assert t['failed']==0
    t.update(status='passed',runtime_sha256=f['recognition_semantic_hash'],freeze_manifest_sha256=sha(OUT/'freeze_manifest.json'),scope='Full suite on frozen runtime/runner/dataset; Windows platform skips only.')
    if (OUT/'final_tests_on_freeze.json').exists():assert read(OUT/'final_tests_on_freeze.json')==t
    else:save('final_tests_on_freeze',t)
    assert all(compileall.compile_dir(str(ROOT/p),quiet=1) for p in ['src','maintenance','benchmarks','scripts','tests'])
    assert all(compileall.compile_file(str(ROOT/p),quiet=1) for p in ['app.py','run.py'])
    cat=verify(ROOT/'data/catalog_seed.sqlite3');assert cat['integrity']=='ok' and not cat['foreign_key_violations']
    with tempfile.TemporaryDirectory(prefix='round21-frozen-migration-',dir=ROOT/'tmp-build') as folder:
        path=Path(folder)/'copy.sqlite3';shutil.copyfile(ROOT/'data/catalog_seed.sqlite3',path)
        initialize_database(path,seed_demo=False);initialize_database(path,seed_demo=False)
        with closing(sqlite3.connect(path)) as db:
            assert db.execute('PRAGMA user_version').fetchone()[0]==610
            assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and not list(db.execute('PRAGMA foreign_key_check'))
            counts={n:db.execute('SELECT count(*) FROM "'+n.replace('"','""')+'"').fetchone()[0] for (n,) in db.execute("SELECT name FROM sqlite_master WHERE type='table'") if not n.startswith('sqlite_')}
        assert counts==cat['tables']
    obs=read(OUT/'unknown_release_v4_observations.json');jsonschema.validate(obs,read('benchmarks/schemas/round21_observations.schema.json'))
    if (OUT/'evaluation_v6_observations.json').exists():jsonschema.validate(read(OUT/'evaluation_v6_observations.json'),read('benchmarks/schemas/round21_observations.schema.json'))
    checks=read(OUT/'final_checks.json');assert checks['passed'] and checks['runtime_sha256']==f['recognition_semantic_hash']
    sealed()
    save('final_validation_on_freeze',dict(passed=True,compile_pass=True,catalog=cat,migration=dict(schema=610,idempotent=True,integrity='ok',foreign_key_violations=[],row_counts_unchanged=True),final_tests_sha256=sha(OUT/'final_tests_on_freeze.json'),runtime_sha256=f['recognition_semantic_hash'],freeze_manifest_sha256=sha(OUT/'freeze_manifest.json'),retained_measured_gates_sha256={n:sha(OUT/(n+'.json')) for n in ['canonical','development_safety','hard_negatives_development','coverage','input_safety','performance_stability','release_gate_fast','historical_regression_fast','final_checks']},schemas_valid=True,scope='Current compile/catalog/migration and full pytest on freeze. Existing canonical/safety/input/performance/diagnostic evidence is bound to identical frozen runtime/data; no redundant recognition replay or repeated timing. Historical regression exit1 remains intentional evidence, not a falsely declared success.',github_ci='external_pending',checked_at=now()))
    print('R21 final validation',t,flush=True)

if __name__=='__main__':main()
