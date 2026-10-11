"""Recompute Round 4 evidence without overwriting historical artifacts."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from benchmarks.round3_audit import read, write, load_texts
from benchmarks.round4_common import texts
from benchmarks.round4_evidence import evaluate
from benchmarks.evaluate import summary, run, verify_locks
from scripts.verify_catalog import verify
import hashlib
import subprocess

def main():
    verify_locks()
    paths = ['development_after', 'historical_holdout_diagnostic', 'official_holdout_v2']
    audit = dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
                 catalog=verify(ROOT/'data/catalog_seed.sqlite3'), raw={})
    for name in paths:
        path='benchmarks/results/round4/'+name+'.json'
        report=read(path)
        recalculated=summary(report['cases'])
        assert recalculated['metrics']==report['summary']['metrics'], name
        audit['raw'][name]=dict(sha256=hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),summary=recalculated)
    m=read('benchmarks/manifests/official_documents_v2.json')
    r=evaluate(m,load_texts())
    frozen={row['id']:row['expected'] for row in read('benchmarks/results/round4/development_after.json')['cases']}
    for row in r['cases']:
        if frozen[row['id']].get('family_id') is not None:
            row['expected']['family_id']=frozen[row['id']]['family_id']
    r['summary']=summary(r['cases'])
    write('benchmarks/results/round5/baseline/development.json',r)
    assert r['summary']['metrics']==audit['raw']['development_after']['summary']['metrics']
    for version in [1,2]:
        m,v=texts('official_holdout_v'+str(version));r=evaluate(m,v)
        write('benchmarks/results/round5/baseline/holdout_v'+str(version)+'.json',r)
        original=audit['raw']['historical_holdout_diagnostic' if version==1 else 'official_holdout_v2']['summary']['metrics']
        assert r['summary']['metrics']==original
    for name in ['development_regression','release_locked_v1','release_locked_v2','hard_negatives_v1','hard_negatives_v2']:
        corpus={'development_regression':'development_regression.json'}.get(name,name+'.json')
        r=run(ROOT/'data/catalog_seed.sqlite3',ROOT/'benchmarks/corpora'/corpus,intervals=False)
        write('benchmarks/results/round5/baseline/'+name+'.json',r)
    write('benchmarks/results/round5/baseline/audit.json',audit)
    print('Baseline raw and recognition recomputed; historical artifacts unchanged.',flush=True)

if __name__=='__main__':main()
