"""Generation proof first; development recognition is a later, separate step."""
import csv,hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from benchmarks.round3_audit import read,write
from benchmarks.round6_recognition import raw_record
from benchmarks.round8_fill import generate

def main():
    ids=read('benchmarks/results/round7/robustness_v3_evaluation_plan.json')['filled_identities']
    records=read('data/document_recognition_fingerprints_v2.json')['records'];work=ROOT/'benchmarks/work/round8-development-filled';work.mkdir(parents=True,exist_ok=True);rows=[]
    for did in ids:
        r=next(r for r in records if r['document_id']==did and r['status']=='active');raw=raw_record(r)
        for v in range(5):
            cid=f'R8DEV-{did}-filled-{v}';row=dict(case_id=cid,document_id=did,resource_type='pdf',acroform_static='',generation_method='',generated=False,reopened=False,fields_verified=0,error='',recognition_result='not_run_generation_first',canonical_sha256=r['canonical_file_sha256'])
            try:
                data,audit=generate(raw,'form.pdf',v);row.update({k:audit[k] for k in ['acroform_static','generation_method','reopened','fields_verified']},generated=True,sha256=hashlib.sha256(data).hexdigest(),synthetic_verified=audit['synthetic_verified'])
                if audit.get('acroform_fallback_reason'):row['fallback_reason']=audit['acroform_fallback_reason']
                (work/(cid+'.pdf')).write_bytes(data)
            except (ValueError,RuntimeError,OSError) as exc:row['error']=type(exc).__name__+': '+str(exc)
            rows.append(row)
    keys=['case_id','document_id','resource_type','acroform_static','generation_method','generated','reopened','fields_verified','error','recognition_result']
    with (ROOT/'benchmarks/results/round8/filled_generation_development.csv').open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=keys,extrasaction='ignore',lineterminator='\n');w.writeheader();w.writerows(rows)
    write('benchmarks/results/round8/filled_generation_development.json',dict(attempted=len(rows),generated=sum(r['generated'] for r in rows),reopened=sum(r['reopened'] for r in rows),verified=sum(bool(r['fields_verified']) for r in rows),cases=rows,scope='Old Round7 identities, development only. Generation and reopen/content validation before any recognition. Synthetic values only; PDFs ignored.'))
    print('Development generation',sum(r['generated'] for r in rows),'/',len(rows),flush=True)
    for r in rows:
        if r['error']:print(r['case_id'],r['error'])

if __name__=='__main__':main()
