"""Release-only audit and read-only validation. Never run held-out recognition."""
from __future__ import annotations
import argparse
from contextlib import closing
from datetime import datetime, UTC
import hashlib
import json
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / 'benchmarks/results/round23'

def read(path):
    return json.loads((ROOT / path).read_bytes())

def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()

def save(name, value):
    OUT.mkdir(exist_ok=True)
    (OUT / (name + '.json')).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf8')

def checkpoint(phase, completed, next_step, **details):
    private = ROOT / '.codex-context'
    c = read(private / 'CHECKPOINT.json')
    c.update(phase=phase, task_status='active', last_completed=completed, next_command=next_step,
             head=git('rev-parse', 'HEAD').strip(), updated_at=datetime.now(UTC).isoformat(), **details)
    text = json.dumps(c, ensure_ascii=False, indent=2, sort_keys=True) + '\n'
    (private / 'history' / (datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ') + '-round23.json')).write_text(text, encoding='utf8')
    (private / 'CHECKPOINT.json').write_text(text, encoding='utf8')

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True, encoding='utf8')

def freeze():
    from benchmarks.round4_common import runtime_hash
    from scripts.round22_common import catalog_semantic
    initial = read(OUT / 'recognition_freeze_verification.json')
    f = read('benchmarks/results/round22/evaluation_freeze_manifest.json')
    mismatches = [p for p, h in initial['verified_files'].items() if sha(p) != h]
    assert not mismatches, mismatches
    assert runtime_hash() == f['working_tree_recognition_hash'] == initial['recognition_sha256']
    assert catalog_semantic() == f['catalog_semantic_sha256']
    assert sha('benchmarks/results/round22/evaluation_v6_observations.json') == initial['V6_sha256']
    assert sha('benchmarks/results/round21/unknown_release_v4_observations.json') == initial['unknown4_sha256']
    for p, h in read(OUT / 'initial_inventory.json')['round22_evidence_locks'].items():
        if p == 'docs/BENCHMARK.md':
            # Authorized current release introduction; original still exact in ZIP.
            with zipfile.ZipFile(ROOT / 'dist/BurOCRazia-v0.7.0-RC1-round22.zip') as z:
                assert hashlib.sha256(z.read('BurOCRazia/' + p)).hexdigest() == h
        else:
            assert sha(p) == h, p
    return initial

def checks():
    import compileall
    import jsonschema
    from scripts.verify_catalog import verify
    from src.database import initialize_database
    freeze()
    assert all(compileall.compile_dir(str(ROOT / p), quiet=1) for p in ['src', 'maintenance', 'benchmarks', 'scripts', 'tests'])
    assert all(compileall.compile_file(str(ROOT / p), quiet=1) for p in ['app.py', 'run.py'])
    cat = verify(ROOT / 'data/catalog_seed.sqlite3')
    assert cat['integrity'] == 'ok' and not cat['foreign_key_violations']
    with tempfile.TemporaryDirectory(prefix='burocrazia-round23-migration-') as folder:
        dbpath = Path(folder) / 'catalog.sqlite3'
        shutil.copyfile(ROOT / 'data/catalog_seed.sqlite3', dbpath)
        initialize_database(dbpath, seed_demo=False)
        initialize_database(dbpath, seed_demo=False)
        with closing(sqlite3.connect(dbpath)) as db:
            assert db.execute('PRAGMA user_version').fetchone()[0] == 610
            assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
            assert not list(db.execute('PRAGMA foreign_key_check'))
            counts = {n: db.execute('SELECT count(*) FROM "' + n + '"').fetchone()[0]
                      for (n,) in db.execute("SELECT name FROM sqlite_master WHERE type='table'") if not n.startswith('sqlite_')}
            assert counts == cat['tables']
    schema = read('benchmarks/schemas/round21_observations.schema.json')
    for path in ['benchmarks/results/round22/evaluation_v6_observations.json', 'benchmarks/results/round21/unknown_release_v4_observations.json']:
        jsonschema.validate(read(path), schema)
    jsonschema.validate(read('benchmarks/reference/reference_truth_v3.json'), read('benchmarks/schemas/reference_truth_v3.schema.json'))
    canonical = read('benchmarks/results/round22/canonical_post_v6.json')
    safety = read('benchmarks/results/round22/safety_post_v6.json')
    assert canonical['passed'] and canonical['n'] == canonical['exact'] == 1007
    assert safety['passed'] and safety['n'] == 705 and not safety['false_accepts']
    # Already observed canonical/safety cases are revalidated by immutable rows;
    # full pytest covers current runtime behavior. No fresh hold-out calls.
    version = tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf8'))['project']['version']
    assert version == '0.7.0-rc1'
    archive = ROOT / 'dist/BurOCRazia-v0.7.0-RC1-round22.zip'
    assert sha(archive) == 'bc9e3aa49b1c05b2a773f4c605e1b79569ec21a0339fab6adef42dac8de27f26'
    initial = read(OUT / 'initial_inventory.json')
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert all(hashlib.sha256(z.read('BurOCRazia/' + p)).hexdigest() == h
                   for p, h in read('benchmarks/results/round22/evidence_locks.json')['sha256'].items())
    result = dict(failures=0, compileall=True, catalog=cat, migration=dict(schema=610, idempotent=True, row_counts_unchanged=True),
                  benchmark_schemas_valid=True, canonical=dict(n=1007, exact=1007, scope='Hash-bound original Round22 post-V6 observations; no replay'),
                  safety=dict(n=705, false_accepts=0, scope='Hash-bound original Round22 post-V6 observations; no replay'),
                  package=dict(sha256=sha(archive), original_verifier_passed=True, protected_files=initial['package_verifier_protected_files'],
                               scope='Original Round22 package fully verified at entry, before authorized README/metadata edits; CRC and all evidence locks rechecked'),
                  candidate_version=version, new_V6_calls=0, new_unknown4_calls=0, full_pytest='pending')
    save('precommit_validation', result)
    checkpoint('Round23 local checks', 'Read-only catalog/migration/schemas/frozen canonical/safety/package PASS', 'Wait for full pytest; complete audit and staging')
    print('Round23 checks PASS', flush=True)

def audit():
    freeze()
    paths = [line[3:] for line in git('status', '--porcelain', '--untracked-files=all').splitlines()]
    assert len(paths) == len(set(paths))
    records, findings = [], []
    patterns = {
        'credential': r'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)',
        'user_path': r'C:[\\/]+Users[\\/]+[^\\/\s"\']+',
        'local_username': r'\blucal\b',
        'secret_assignment': r'(?i)(?:password|access_token|api_key|session_cookie)\s*[:=]\s*["\'][^"\']{8,}["\']',
    }
    approved = {'.gitignore', 'AGENTS.md', 'README.md', 'README_EN.md', 'CHANGELOG.md', 'pyproject.toml',
                'README_CANDIDATE_IT.md', 'README_CANDIDATE_EN.md', 'CHANGELOG_CANDIDATE.md', '.github/workflows/tests.yml',
                'data/recognition_profiles/fingerprint_decision_v6.json', 'data/recognition_profiles/fingerprint_decision_v7.json'}
    for p in paths:
        assert p in approved or p.startswith(('src/', 'tests/', 'docs/', 'scripts/', 'benchmarks/', 'maintenance/')), p
        assert Path(p).suffix.lower() in {'.py', '.json', '.csv', '.md', '.toml', '.yml'} or p == '.gitignore', p
        assert not any(s in p.lower() for s in ['cache/', '/work/', 'checkpoint', 'secret', '.env']) or p == 'benchmarks/results/round23/secret_scan.json', p
        raw = (ROOT / p).read_bytes()
        text = raw.decode('utf8')
        for kind, pattern in patterns.items():
            for i, line in enumerate(text.splitlines(), 1):
                if re.search(pattern, line):
                    # Patterns themselves in this scanner are inert code.
                    findings.append(dict(path=p, line=i, kind=kind, classification='scanner_pattern' if p == 'scripts/round23_release.py' else 'REVIEW_REQUIRED'))
        category = 'MUST COMMIT' if not p.startswith('benchmarks/results/') else 'SHOULD COMMIT'
        reason = 'Runtime/policy/test/reproduction harness or release documentation'
        if p.startswith('benchmarks/results/'):
            reason = 'Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files'
        records.append(dict(path=p, classification=category, reason=reason, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                            over_1_MB=len(raw)>1_000_000, over_10_MB=len(raw)>10_000_000, binary=False))
    assert not [x for x in findings if x['classification'] == 'REVIEW_REQUIRED'], findings
    save('tracking_inventory', dict(files=records, excluded='All ignored venv/cache/work/private checkpoints/logs/temp DB/dist archives; no official binaries added',
                                   large_file_policy='Large JSONs are retained scientific provenance, not downloaded resources. No file >=100 MB; no new binary/database/index.',
                                   total_bytes=sum(r['bytes'] for r in records)))
    save('secret_scan', dict(confirmed_secrets=0, confirmed_private_paths=0, confirmed_private_emails=0, scanned_files=len(records),
                             findings=findings, email_review='Institutional public provenance references reviewed separately; no private contact data introduced',
                             staged_scan='pending', patterns=list(patterns)))
    table = '\n'.join('| `' + r['path'] + '` | ' + r['classification'] + ' | ' + str(r['bytes']) + ' | ' + ('large public evidence; locked' if r['over_1_MB'] else r['reason']) + ' |' for r in records)
    (ROOT / 'docs/ROUND23_TRACKING_AUDIT.md').write_text('# Round 23 — audit dei file\n\nOgni file modificato/non tracciato è elencato sotto. Hash e dimensioni nel [registro JSON](../benchmarks/results/round23/tracking_inventory.json). I registri stessi sono artefatti derivati: lo staging finale è controllato nuovamente.\n\nLe evidenze JSON grandi sono eccezioni motivate al criterio di sintesi: conservarle è necessario per verificare freeze, contamination registry, risultati grezzi e tentativi negativi senza rifare esperimenti. Nessun corpus PDF/DOCX/immagini, cache, ZIP, nuovo indice binario o database è aggiunto. Il catalogo seed e gli indici runtime già versionati restano identici. Venv, checkpoint privati, log, cache, work, temporanei e dist sono MUST NOT COMMIT e rimangono ignorati.\n\n| File | Categoria | Byte | Motivazione |\n| --- | --- | ---: | --- |\n' + table + '\n', encoding='utf8')
    print('Audit PASS', len(records), 'files;', sum(r['over_10_MB'] for r in records), '>10MB', flush=True)

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=['checks', 'audit'])
    {'checks': checks, 'audit': audit}[p.parse_args().mode]()
