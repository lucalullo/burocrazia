import argparse,sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from benchmarks.round8_common import read,write,OUT

def one(job):
    import benchmarks.round8_calibrate as cal
    from src.fingerprint_decision_v4 import profile
    p=profile();cal.grid=lambda:[p]
    row=cal.worker(job)['grid_results'][0]
    return row

def main():
    import benchmarks.round8_calibrate as cal
    p=argparse.ArgumentParser();p.add_argument('subset',choices=['filled','r6','r7','other_known']);a=p.parse_args()
    jobs=[j for j in cal.tasks() if 'record' in j and (j['name']=='valid_filled' if a.subset=='filled' else j['name']!='valid_filled' if a.subset=='other_known' else j['id'].startswith('DEV6-' if a.subset=='r6' else 'DEV7-'))];rows=[]
    with ProcessPoolExecutor(max_workers=3) as pool:
        for f in as_completed([pool.submit(one,j) for j in jobs]):
            rows.append(f.result())
            if len(rows)%25==0:print('Development diagnostic',a.subset,len(rows),'/',len(jobs),flush=True)
    wrong=[r for r in rows if r['observed']['match_type']=='DOCUMENT_MATCH' and not r['document_correct']]
    write(OUT+'calibration_wrong_diagnostic_'+a.subset+'.json',dict(cases=rows,wrong=wrong));print('Wrong',[(r['id'],r['expected'],r['observed'],r['signals']) for r in wrong],flush=True)
if __name__=='__main__':main()
