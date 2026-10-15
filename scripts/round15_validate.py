"""Round15 prerequisite measurements, using the existing benchmark contracts."""
import argparse,os,tempfile,zipfile
from io import BytesIO
from collections import Counter
from scripts.round15_common import *
from benchmarks.round3_audit import catalog
from benchmarks import round8_common as common
from src.fingerprint_v3 import read_bundle
from src.document_fingerprints import binding

def configure():
    from scripts import round13_validation as v
    from benchmarks import round8_validation as previous
    common.OUT='benchmarks/results/round15/';common.SEED=SEED;previous.OUT=common.OUT
    common.write=lambda path,value:atomic_json(ROOT/path,value);previous.write=common.write
    v.OUT=OUT;v.configure=lambda:previous
    return v,previous

def coverage():
    docs,_=catalog();by={d.id:d for d in docs};bundle=read_bundle()
    fixed={c['document_id'] for c in read('benchmarks/results/round6/resource_audit.json')['cases'] if c['expected_resource_type']=='file_backed_document'}
    native={r['document_id'] for r in bundle['records'] if r['status']=='active' and r['mime_type'] in ['application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document']}
    shared={c['document_id'] for c in read('benchmarks/results/round12/shared_eligibility_audit.json')['cases'] if c['eligible']}
    legacy={r['document_id'] for r in bundle['records'] if r['status']=='active' and r['ocr_metadata'].get('source_kind')=='maintenance_derived_legacy'}
    for r in bundle['records']:
        if r['status']=='active':assert r['catalog_binding_sha256']==binding(by[r['document_id']])
    ids=(native|shared|legacy)&fixed
    save('coverage',dict(file_backed_total=len(fixed),operational_total=1212,runtime_usable_supported=len(ids),native_supported=len((native|shared)&fixed),legacy_qualified=len(legacy),shared_resource_only=33,
        eligible_ids=sorted(ids),file_backed_percent=100*len(ids)/len(fixed),all_operational_percent=100*len(ids)/1212,
        definition_sha256=sha('benchmarks/reference/fingerprint_support_definition_v1.json'),dataset_sha256=sha('data/document_recognition_fingerprints_v3.json'),passed=len(ids)/len(fixed)>=.85 and len(ids)/1212>=.70,measured_at=now()))
    print('Coverage',len(ids),len(fixed),flush=True)

def historical_run():
    configure()[1].historical()
    from scripts import round9_verify
    round9_verify.atomic_json=lambda path,value:atomic_json(OUT/path.name,value);round9_verify.main()
    hist={p.stem:read(p) for p in OUT.glob('historical_*.json') if isinstance(read(p).get('cases'),list)}
    no=[c for v in hist.values() for c in v['cases'] if c['expected']['match_type']=='NO_MATCH']
    wrong=[c['id'] for c in no if c['observed']['match_type']!='NO_MATCH']
    r061=next(c for c in hist['historical_release_locked_v2']['cases'] if c['id']=='R061')
    two=[c for c in hist['historical_development_compat_v2']['cases'] if c['id'] in ['EX02MISSINGREV','EX03MISSINGREV']]
    five=read(OUT/'verification.json')['historical_five_passed']
    save('historical_safety',dict(n=len(no),false_accepts=wrong,r061=r061['observed'],round8_two=[c['observed'] for c in two],historical_five_passed=five,
        passed=len(no)==241 and not wrong and five and r061['observed']['match_type']=='NO_MATCH' and len(two)==2 and all(c['observed']['match_type']=='NO_MATCH' for c in two),measured_at=now()))

def canonical():configure()[0].canonical()

def performance():
    from benchmarks import round12_performance as p
    p.OUT=OUT/'performance_pre_freeze.json';p.SEED=SEED;p.main()

def development():
    from benchmarks.transactional_writer import CaseJournal
    from benchmarks.round14_unknown import metrics
    configure();m=read('benchmarks/manifests/official_unknown_release_v2.json');docs,families=catalog()
    ident=common.identity();key=dict(runtime=ident['runtime_sha256'],dataset=ident['fingerprint_sha256'],manifest=sha('benchmarks/manifests/official_unknown_release_v2.json'),purpose='development_regression_after_round15_fix')
    target=OUT/'development_regression_after_round15_fix.json';assert not target.exists(),'Development replay already recorded'
    journal=CaseJournal(ROOT/'benchmarks/work/round15/development.sqlite',identity=key,expected_ids=[c['case_id'] for c in m['cases']]);pending=set(journal.pending())
    for c in m['cases']:
        if c['case_id'] not in pending:continue
        raw=(ROOT/'benchmarks/cache'/(c['SHA256']+'.body')).read_bytes();assert __import__('hashlib').sha256(raw).hexdigest()==c['SHA256']
        cc=dict(id=c['case_id'],group=c['resource_group'],category=c['document_type'],expected=dict(match_type='NO_MATCH'),label_status='historical_frozen_expected',representation='official_original',provenance=dict(source=c['source'],entity=c['entity'],sha256=c['SHA256'],truth_version=c['version'],previously_seen=True))
        journal.append(common.case_result(cc,raw,'development.pdf' if c['mime']=='application/pdf' else 'development.docx',docs,families))
    rows=journal.rows();journal.export(OUT/'development_regression_observations.json',complete=True)
    save('development_regression_after_round15_fix',dict(status='development_regression_after_round15_fix',identity=ident,**metrics(rows),observations_sha256=sha(OUT/'development_regression_observations.json'),release_gate_eligible=False,
        interpretation='Original114 labels retained for diagnostic comparison only. The two INAIL acceptances remain unresolved truth, not confirmed false accepts. The four extraction errors remain errors, not correct NO.',
        confirmed_anac_after=next(r['observed'] for r in rows if r['id']=='U14-d6e51fa8e7f88431')))
    print('Development regression',metrics(rows),flush=True)

def input_safety():
    from src.extract import extract_document,ExtractionError
    from src.recognize import recognize_catalog
    from src.extract import MAX_UPLOAD_BYTES
    docs,families=catalog();cases=[]
    for c in read(OUT/'page_limit_audit.json')['round14_oversized_cases']:
        raw=(ROOT/'benchmarks/cache'/(next(ca['SHA256'] for ca in read('benchmarks/manifests/official_unknown_release_v2.json')['cases'] if ca['case_id']==c['case_id'])+'.body')).read_bytes()
        cases.append((dict(case_id='IS15-'+c['case_id'],kind='official_pdf_over100pages',filename='official.pdf',pages=c['pages'],official_url=c['official_url'],expected_error='100 pagine'),raw))
    cases.append((dict(case_id='IS15-oversized',kind='synthetic_upload_over20MiB',filename='limit.txt',generator=dict(repeat_byte=65,count=MAX_UPLOAD_BYTES+1),expected_error='20 MiB'),b'A'*(MAX_UPLOAD_BYTES+1)))
    cases.append((dict(case_id='IS15-unsupported',kind='unsupported_format',filename='input.exe',generator=dict(hex='4d5a'),expected_error='Formato non supportato'),b'MZ'))
    cases.append((dict(case_id='IS15-text-limit',kind='synthetic_text_over1Mcharacters',filename='limit.txt',generator=dict(repeat_byte=65,count=1000001),expected_error='1.000.000'),b'A'*1000001))
    cases.append((dict(case_id='IS15-mime',kind='mime_mismatch',filename='input.txt',mime='application/pdf',generator=dict(hex='74657874'),expected_error='MIME'),b'text'))
    buffer=BytesIO()
    with zipfile.ZipFile(buffer,'w',compression=zipfile.ZIP_STORED) as z:z.writestr('../outside.xml','<r/>')
    cases.append((dict(case_id='IS15-zip-traversal',kind='docx_unsafe_path',filename='input.docx',generator=dict(zip_path='../outside.xml',payload='<r/>',compression='stored'),expected_error='percorsi non validi'),buffer.getvalue()))
    # ZIP timestamp fixed for reproducible generated bytes.
    buffer=BytesIO()
    with zipfile.ZipFile(buffer,'w') as z:
        info=zipfile.ZipInfo('../outside.xml',date_time=(2026,1,1,0,0,0));z.writestr(info,'<r/>')
    cases[-1]=(cases[-1][0],buffer.getvalue())
    manifest=dict(schema_version=1,manifest_id='input-safety-v1',page_limit_contract_sha256=sha(OUT/'page_limit_audit.json'),cases=[dict(c,SHA256=__import__('hashlib').sha256(raw).hexdigest(),size_bytes=len(raw),expected='safe_extraction_rejection') for c,raw in cases],scope='Unsupported-limit safety, never unknown recognition accuracy.')
    path=ROOT/'benchmarks/manifests/input_safety_v1.json'
    if path.exists():assert read(path)==manifest
    else:atomic_json(path,manifest)
    rows=[]
    with tempfile.TemporaryDirectory(prefix='round15-input-safety-',dir=ROOT/'tmp-build') as folder:
        before={p.relative_to(folder).as_posix() for p in Path(folder).rglob('*')};old_temp,old_tmp=os.environ.get('TEMP'),os.environ.get('TMP');os.environ['TEMP']=os.environ['TMP']=folder
        try:
            for c,raw in cases:
                outcome=None;error=None;crash=False;calls=0
                try:
                    extracted=extract_document(raw,c['filename'],c.get('mime'));calls+=1
                    outcome=recognize_catalog(extracted.text,docs,families).match_type
                except ExtractionError as ex:error=str(ex)
                except Exception as ex:crash=True;error=type(ex).__name__+': '+str(ex)
                residue=sorted({p.relative_to(folder).as_posix() for p in Path(folder).rglob('*')}-before)
                rows.append(dict(case_id=c['case_id'],input_sha256=__import__('hashlib').sha256(raw).hexdigest(),rejected_safely=bool(error and c['expected_error'] in error and not crash),error=error,crash=crash,temp_residue=residue,recognition_calls=calls,result=outcome,no_false_document_result=outcome!='DOCUMENT_MATCH'))
        finally:
            for key,val in [('TEMP',old_temp),('TMP',old_tmp)]:
                if val is None:os.environ.pop(key,None)
                else:os.environ[key]=val
    save('input_safety',dict(schema_version=1,n=len(rows),safe_rejects=sum(r['rejected_safely'] for r in rows),cases=rows,manifest_sha256=sha(path),passed=all(r['rejected_safely'] and not r['temp_residue'] and r['no_false_document_result'] for r in rows),measured_at=now()))
    print('Input safety',len(rows),all(r['rejected_safely'] for r in rows),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['coverage','historical_run','canonical','performance','development','input_safety']);a=p.parse_args();globals()[a.mode]()
