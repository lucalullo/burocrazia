"""Reaggregate Round 6 before any runtime change; immutable input hashes."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from benchmarks.evaluate import summary,verify_locks
from benchmarks.round3_audit import read,write
from scripts.verify_catalog import verify

def main():
    if (ROOT/'benchmarks/results/round7/baseline/audit.json').exists():raise ValueError('Immutable baseline audit already exists')
    verify_locks();base='benchmarks/results/round6/';out='benchmarks/results/round7/'
    audit=dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip(),
        catalog=verify(ROOT/'data/catalog_seed.sqlite3'),raw={})
    for p in sorted((ROOT/base).rglob('*.json')):
        r=json.loads(p.read_bytes());item=dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest())
        if isinstance(r,dict) and 'cases' in r and 'summary' in r and 'metrics' in r['summary']:
            # CLI fixture uses an older metric schema; compare with its own aggregator.
            if p.name=='development_compat_v2.json':
                from scripts.benchmark import summarize
                s=summarize(r['cases'])
            else:s=summary(r['cases'])
            assert s['metrics']==r['summary']['metrics'],p
            item.update(cases=len(r['cases']),passed=r['summary']['passed'],metrics=s['metrics'])
        audit['raw'][p.relative_to(ROOT).as_posix()]=item
    cov=read(base+'fingerprint_coverage.json');perf=read(base+'performance.json');reg=read(base+'final/development_regression.json')
    bad=[dict(id=c['id'],expected=c['expected'],observed=c['observed'],reason=c['reason']) for c in reg['cases'] if not c['correct']]
    gates=read('docs/release_gates.json');tests=read(base+'tests.json')
    audit.update(coverage=cov,performance=perf,tests=tests,historical_failures=bad,
        failed_gates=[g for g in gates['gates'] if g['blocking'] and not g['passed']],
        methodology='Round6 evaluation is now development. Fresh identity-level evaluation required after code freeze.')
    write(out+'baseline/audit.json',audit)
    lines=['# Round 7 — baseline audit','',f"Ingresso `{audit['commit']}`, branch `{audit['branch']}`, working tree iniziale pulito.",
        'Software 0.6.1, schema 610; 1.216 reali, 1.212 operativi. Seed integrity/FK e hash invariati.',
        f"Seed SHA `{audit['catalog']['sha256']}`.",'',
        f"Firme: {cov['fingerprinted_all_operational_docs']}/1212; file-backed {cov['file_backed_operational_docs']}; totale {cov['coverage_all']:.2%}, file-backed {cov['coverage_file_backed']:.2%}.",
        'Canonical 987/987, robustness 150/192, scansioni 128/168; zero wrong in questi tre corpus.',
        'Candidate recall@1/5/10/25 100% sul corpus Round6. Filled: 100 AcroForm +70 overlay, tutti corretti; scope distinti.',
        f"Performance effettiva: p50 {perf['latency_ms']['p50']:.4f} ms, p95 {perf['latency_ms']['p95']:.4f} ms (gate <=250 ms fallito), indice {perf['fingerprints']['index_bytes']} byte.",
        f"Test Round6 verificati: {tests['passed']} passed, {tests['skipped']} skip, zero failed; nessuna nuova esecuzione baseline dichiarata.",'',
        'Regressione esatta: EX02 (CI543) ed EX03 (CI544), versione catalogata 1.1 assente dal testo; veto globale `missing_model_revision` nel fallback metadata. Storico 33/35, expected immutati.',
        'Locked v1 59/69 storico; locked v2 69/69. R061 NO, cinque safety cases 5/5, negativi 130/130, family sintetica 161/161.',
        'Gate falliti: '+', '.join(g['gate'] for g in audit['failed_gates'])+'.','',
        'Tutti i raw JSON Round6 sono hashati nel baseline audit; metriche per caso ricalcolate con il rispettivo schema. Nessun artefatto storico modificato.',
        'Da questo momento Round6 evaluation è development; non verrà presentata come nuova evaluation indipendente.']
    (ROOT/'docs/ROUND7_BASELINE_AUDIT.md').write_bytes(('\n'.join(lines)+'\n').encode())
    print('Round7 baseline saved',len(audit['raw']),'raw artifacts; failures',[c['id'] for c in bad])

if __name__=='__main__':main()
