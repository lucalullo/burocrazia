"""Expand actual AcroForm cases by field availability, never by recognition result."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from datetime import UTC,datetime
from benchmarks.round3_audit import read,write,catalog
from benchmarks.round6_recognition import (OUT,active_records,plan,raw_record,known_case,
    case_result,fill_acroform,save,checked_calibration)
from benchmarks.evaluate import summary

def main():
    checked_calibration();initial_path=ROOT/OUT/'filled_forms_initial_matrix.json'
    initial=read(OUT+'filled_forms_v2.json')
    if initial.get('supplement_cases'):
        print('Filled supplement already measured; preserved without rewriting.')
        return
    if not initial_path.exists():write(OUT+'filled_forms_initial_matrix.json',initial)
    ids=sorted({r['expected']['document_id'] for r in initial['cases'] if r.get('acroform_fields_filled',0)>0})
    fixed=plan();by={r['document_id']:r for r in active_records() if fixed['resources'].get(str(r['document_id']))==r['canonical_file_sha256']}
    if not (ROOT/OUT/'filled_supplement_plan.json').exists():write(OUT+'filled_supplement_plan.json',dict(frozen_at=datetime.now(UTC).isoformat(),document_ids=ids,
        variants=list(range(10,20)),selection='All evaluation identities with actual canonical AcroForm fields successfully filled; no selection by recognition result.',
        reason='Reach 100 actual interactive field-fill cases; keep the initial 120-case matrix and static overlays separately visible.',threshold_changes=False))
    docs,families=catalog();rows=list(initial['cases']);new=[]
    work=ROOT/'benchmarks/work/round6-filled'
    for did in ids:
        r=by[did]
        for variant in range(10,20):
            raw,n=fill_acroform(raw_record(r),variant);path=work/(str(did)+'-'+str(variant)+'.pdf');path.write_bytes(raw)
            row=case_result(known_case(r,'filled_'+str(variant)),raw,path.name,docs,families,diagnostics=True)
            row.update(acroform_fields_filled=n,fill_method='canonical_acroform_verified',distinct_acroform_values=True,supplement=True)
            rows.append(row);new.append(row)
        print('Additional actual field fills',did,len(new),flush=True)
    interactive=[r for r in rows if r.get('acroform_fields_filled',0)>0]
    overlays=[r for r in rows if not r.get('acroform_fields_filled',0)]
    save('filled_forms_v2',rows,interactive_cases=len(interactive),interactive_summary=summary(interactive),
        static_overlay_summary=summary(overlays),initial_matrix_cases=len(initial['cases']),supplement_cases=len(new),
        limits='Five actual interactive templates, 20 variants each; 70 additional static content overlays include non-form official documents and are weaker evidence. Correlated cases, no handwriting. Initial matrix and supplement plan retained. No parameter changes.')
    save('filled_acroform_v2',interactive,limits='100 actual programmatic field-fill variants across five fixed evaluation identities; canonical /V, widget value and appearance verified. Not 100 independent templates.')
    save('filled_static_overlays_v2',overlays,limits='Static content overlays on known official PDFs, including non-form documents. Not equivalent to actual field filling.')

if __name__=='__main__':main()
