"""Reaggregate frozen Round 5 evidence; never overwrite historical artifacts."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from benchmarks.evaluate import summary,verify_locks
from scripts.verify_catalog import verify
from src.document_fingerprints import read_bundle

def main():
    import sqlite3
    verify_locks()
    out=ROOT/'benchmarks/results/round6/baseline';out.mkdir(parents=True,exist_ok=True)
    audit=dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        catalog=verify(ROOT/'data/catalog_seed.sqlite3'),fingerprint_version=read_bundle()['fingerprint_version'],
        fingerprints=len(read_bundle()['records']),raw={})
    with sqlite3.connect('file:data/catalog_seed.sqlite3?mode=ro',uri=True) as db:
        audit['sqlite_schema']=db.execute('pragma user_version').fetchone()[0]
    for name in ['canonical','robustness','filled_forms','unknown_official','family_identity_holdout']:
        path=ROOT/'benchmarks/results/round5'/(name+'.json');r=json.loads(path.read_bytes());s=summary(r['cases'])
        assert s['metrics']==r['summary']['metrics'],name
        audit['raw'][name]=dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),counts=r['counts'],metrics=s['metrics'])
    for name in ['performance','memory','tests','fingerprint_coverage','historical_five','ocr_legacy_gate','ocr_synthetic_v2']:
        path=ROOT/'benchmarks/results/round5'/(name+'.json')
        audit['raw'][name]=dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),report=json.loads(path.read_bytes()))
    log=ROOT/'reports/round6-baseline-tests.log';text=log.read_text(encoding='utf8',errors='replace')
    m=re.search(r'(\d+) passed, (\d+) skipped in ([\d.]+)s',text)
    if not m:raise ValueError('Baseline test non terminata con successo.')
    audit['baseline_tests']=dict(passed=int(m[1]),failed=0,skipped=int(m[2]),seconds=float(m[3]),log_sha256=hashlib.sha256(log.read_bytes()).hexdigest())
    (out/'audit.json').write_bytes((json.dumps(audit,ensure_ascii=False,indent=2)+'\n').encode())
    rows=[]
    for n,r in audit['raw'].items():
        if 'counts' in r:
            c=r['counts'];rows.append(f"| {n} | {c['exact']} | {c['family']} | {c['reject']} | {c['wrong']} |")
    report=f"""# Round 6 — baseline audit

Ingresso verificato prima delle modifiche al runtime: `{audit['commit']}`, branch
`{subprocess.check_output(['git','branch','--show-current'],text=True).strip()}`.
Working tree iniziale pulito. Software 0.6.1, target 0.7.0, SQLite {audit['sqlite_schema']},
firma {audit['fingerprint_version']}. Catalogo: 1.216 reali, 1.212 operativi, quattro rifiutati.
SHA seed `{audit['catalog']['sha256']}`; integrity/FK e lock storici verificati.

369/1.212 firme (30,4455%). Tutte le metriche per caso sono ricalcolate dai raw Round 5
con confronto esatto con le metriche pubblicate. Hash, numeratori e denominatori sono in
`benchmarks/results/round6/baseline/audit.json`. Nessun raw storico modificato.

| Prova | Exact | Family | NO | Wrong |
|---|---:|---:|---:|---:|
{chr(10).join(rows)}

Canonical: 362/369, precision 100%, recall 98,103%. Robustness: 48/196, recall 24,49%.
Filled: 10/14. Unknown: 137/137 rifiutati. Famiglia: un caso, nessuna famiglia valutabile.
I sette canonical NO sono 89, 107, 112, 254, 440, 942, 1079.

Performance storica verificata dai raw: p50 91,2146 ms, p95 128,1624 ms;
indice 28.676.242 byte, bundle 12.188.225 byte. OCR storico 7/7 e sintetico v2 14/14.
Test Round 5: 615 passed, 3 skip Windows; baseline fresca Round 6:
{audit['baseline_tests']['passed']} passed, {audit['baseline_tests']['skipped']} skipped,
zero fallimenti, {audit['baseline_tests']['seconds']} s. Lo SHA del log è nel raw audit.

Candidata iniziale NOT READY. CI esterna non eseguita. Le misure sopra sono storiche
o baseline locale e non costituiscono risultati del nuovo motore.
"""
    (ROOT/'docs/ROUND6_BASELINE_AUDIT.md').write_bytes(report.encode())
    print('Round 6 baseline verified:',audit['baseline_tests'])

if __name__=='__main__':main()
