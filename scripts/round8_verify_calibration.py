"""Verify selected calibration on final pre-freeze source; never evaluation v4."""
import hashlib,json,sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from benchmarks.round8_common import OUT,read,write,identity
from benchmarks.evaluate import summary

def one(job):
    import benchmarks.round8_calibrate as cal
    from src.fingerprint_decision_v4 import profile
    selected=profile();cal.grid=lambda:[selected]
    return cal.worker(job)['grid_results'][0]

def main():
    if (ROOT/OUT/'freeze.json').exists():raise ValueError('Calibration verification is pre-freeze only')
    import benchmarks.round8_calibrate as cal
    original=(ROOT/OUT/'calibration_v4.json').read_bytes();parent=hashlib.sha256(original).hexdigest();(ROOT/OUT/'calibration_grid_v4.json').write_bytes(original)
    before=identity();rows=[];jobs=cal.tasks()
    with ProcessPoolExecutor(max_workers=3) as pool:
        for f in as_completed([pool.submit(one,j) for j in jobs]):
            rows.append(f.result())
            if len(rows)%50==0:print('Final pre-freeze calibration verification',len(rows),'/',len(jobs),flush=True)
    rows.sort(key=lambda r:r['id']);old={r['id']:r for r in read(OUT+'calibration_observations_v4.json')['cases']};keys=['observed','correct','document_correct','family_correct','entity_error','version_error','input_sha256'];differences=[]
    for r in rows:
        for key in keys:
            if r[key]!=old[r['id']][key]:differences.append(dict(id=r['id'],field=key))
    after=identity();assert all(before[k]==after[k] for k in ['runtime_sha256','code_sha256','fingerprint_sha256'])
    proof=dict(identity=after,parent_grid_calibration_sha256=parent,cases=rows,summary=summary(rows),differences=differences,scope='Selected profile re-executed on all 799 development cases after final pre-freeze UI error handling and leakage URL guard completion. No threshold selection or fresh evaluation identities. Original grid and labels preserved. Normal recognizer source did not change during the grid; UI and prospective-plan guards do not participate in its decisions.')
    write(OUT+'calibration_runtime_verification.json',proof);assert not differences,'Selected calibration differs on final source; audit before freeze'
    value=json.loads(original);value.update(after,parent_grid_sha256=parent,runtime_verification_sha256=hashlib.sha256((ROOT/OUT/'calibration_runtime_verification.json').read_bytes()).hexdigest());write(OUT+'calibration_v4.json',value)
    print('Selected calibration equivalent on all',len(rows),'cases',flush=True)
if __name__=='__main__':main()
