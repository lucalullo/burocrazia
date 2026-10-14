"""Recover an interrupted preparation without changing sealed transformations.

The frozen loop did not catch lxml's C14NError. This operator adapter only
translates that exception into a recorded generation failure and reuses existing
bytes. It never changes XML, generators, seeds, selection or recognition.
"""
from io import BytesIO
from pathlib import Path
from lxml import etree
from scripts.round21_common import *
from benchmarks import round21_release as frozen

def main():
    f=frozen.sealed();assert not (OUT/'evaluation_v6_prepared.json').exists()
    assert not (OUT/'evaluation_v6_started.json').exists()
    plan=read(OUT/'evaluation_v6_plan.json');folder=WORK/'evaluation-v6'
    before={p.name:sha(p) for p in folder.iterdir() if p.is_file()}
    old_log=sha('reports/round21-v6-prepare.log')
    assert 'lxml.etree.C14NError: C14N failed' in (ROOT/'reports/round21-v6-prepare.log').read_text(encoding='utf8')
    records=frozen.read_bundle()['records'];lookup={};scans={};fills={};ordered=[]
    for c in plan['selected']:
        did=c['document_id'];r=next(r for r in records if r['document_id']==did and r['canonical_file_sha256']==c['canonical_sha']);ext='.pdf' if r['mime_type']=='application/pdf' else '.docx'
        for norm,name in [(False,'digital_canonical_derivative'),(True,'digital_normalized')]:
            cc=f'R21V6-{did}-{name}';lookup[(r['canonical_file_sha256'],ext,norm)]=cc;ordered.append(cc)
        if ext=='.pdf':
            for tr in plan['transform_policy']:
                cc=f"R21V6-{did}-{tr['name']}";scans[frozen.seed_for(frozen.V6_SEED,did,tr['name'])]=cc;ordered.append(cc)
        if did in plan['filled_identities']:
            for i in range(5):
                name='filled_'+str(i);cc=f'R21V6-{did}-{name}';variant=21000+frozen.seed_for(frozen.V6_SEED,did,name)%1_000_000;fills[(r['canonical_file_sha256'],variant)]=cc;ordered.append(cc)
    cached={p.stem:p for p in folder.iterdir() if p.is_file()}
    # The first absent case is precisely the interrupted normalized DOCX. Do not
    # retry it, repair the XML or substitute an alternative transformation.
    failed=next(cc for (h,ext,n),cc in lookup.items() if ext=='.docx' and n and cc not in cached and cc.replace('digital_normalized','digital_canonical_derivative') in cached)
    assert failed.endswith('digital_normalized') and any(cc==failed and ext=='.docx' for (h,ext,n),cc in lookup.items())
    audit=dict(created_at=now(),freeze_sha256=sha(OUT/'freeze_manifest.json'),plan_sha256=sha(OUT/'evaluation_v6_plan.json'),operator_adapter_sha256=sha(__file__),initial_log_sha256=old_log,preexisting_outputs=before,failed_case=failed,reused=[],new_generator_calls=[],generation_errors=[],recognition_calls=0,policy='Only reuse byte-identical existing outputs and translate lxml exceptions to failed generation. No repair/resampling/new variants, selection or engine change. Cached fill checks report a conservative actual synthetic-marker lower bound; original frozen generation verified fields before writing these files.')
    def persist():save('evaluation_v6_generation_recovery',audit)
    persist()
    def cached_bytes(cc):
        p=cached.get(cc)
        if not p:return None
        assert sha(p)==before[p.name];value=p.read_bytes();frozen.reopened(value,p.suffix);audit['reused'].append(cc);persist();return value,p.suffix
    derivative,scan,generate=frozen.derivative,frozen.scan,frozen.generate
    def wrapped_derivative(raw,ext,normalized=False):
        cc=lookup[(hashlib.sha256(raw).hexdigest(),ext,normalized)]
        value=cached_bytes(cc)
        if value:return value
        if cc==failed:
            audit['generation_errors'].append(dict(case_id=cc,error='C14NError: C14N failed',basis='Original interrupted log; no retry'));persist();raise ValueError('Original C14NError: C14N failed; generation failed, no XML repair or retry')
        audit['new_generator_calls'].append(cc);persist()
        try:return derivative(raw,ext,normalized)
        except etree.LxmlError as e:
            audit['generation_errors'].append(dict(case_id=cc,error=type(e).__name__+': '+str(e)));persist();raise ValueError(type(e).__name__+': '+str(e)) from e
    def wrapped_scan(raw,params,seed):
        cc=scans[seed];value=cached_bytes(cc)
        if value:return value
        audit['new_generator_calls'].append(cc);persist();return scan(raw,params,seed)
    def wrapped_generate(raw,filename,variant):
        cc=fills[(hashlib.sha256(raw).hexdigest(),variant)];value=cached_bytes(cc)
        if value:
            import pymupdf
            data,ext=value
            with pymupdf.open(stream=data,filetype='pdf') as pdf:
                text=' '.join(p.get_text() for p in pdf).upper();widgets=[str(w.field_value or '').upper() for p in pdf for w in (p.widgets() or ())]
            markers=['FITTIZ','ZZZZZZ','2030','0000000000','EXAMPLE.INVALID']
            count=sum(any(m in v for m in markers) for v in widgets)
            if not count:count=int(any(m in text for m in markers))
            assert count>0,'Cached fill must retain observable synthetic markers'
            return data,dict(reopened=True,synthetic_verified=True,fields_verified=count,generation_method='cached_original_verified_fill_with_reopened_marker_lower_bound')
        audit['new_generator_calls'].append(cc);persist();return generate(raw,filename,variant)
    original_write=Path.write_bytes
    def preserve_write(path,data):
        if path.parent==folder and path.exists():
            assert path.read_bytes()==data and sha(path)==before[path.name];return len(data)
        return original_write(path,data)
    frozen.derivative=wrapped_derivative;frozen.scan=wrapped_scan;frozen.generate=wrapped_generate;Path.write_bytes=preserve_write
    checkpoint('Round21 generation technical recovery; sealed semantics unchanged','133 outputs preserved; unhandled normalized DOCX C14N error before any V6 predictions. Existing outputs will be reused, failed variant recorded; no new XML workaround.', 'Run same sealed generation plan to completion via operator exception/cache adapter; inspect all generation/leakage gates before V6.')
    try:frozen.prepare_v6()
    finally:Path.write_bytes=original_write
    for name,h in before.items():assert sha(folder/name)==h
    frozen.sealed();audit.update(completed_at=now(),preexisting_outputs_unchanged=True,prepared_sha256=sha(OUT/'evaluation_v6_prepared.json'),recognition_calls=0);persist()

if __name__=='__main__':main()
