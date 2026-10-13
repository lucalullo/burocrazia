"""Ordered R13 checkpoints, single-shot unknown and unchanged benchmark runners."""
import argparse
from collections import Counter
import csv
import hashlib
import math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from benchmarks.round3_audit import read,catalog
from benchmarks.transactional_writer import atomic_json,CaseJournal
from benchmarks import round8_common as common
from benchmarks.unknown_release import validate,select,balance
from src.fingerprint_v3 import read_bundle,PATH
from src.document_fingerprints import binding

OUT=ROOT/'benchmarks/results/round13'


def sha(path):return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()


def coverage():
    definition=sha('benchmarks/reference/fingerprint_support_definition_v1.json')
    assert read('benchmarks/results/round13/support_definition_lock.json')['sha256']==definition
    rows=list(csv.DictReader((OUT/'legacy_fingerprint_audit.csv').open(encoding='utf8')))
    assert len(rows)==40
    docs,_=catalog();by={d.id:d for d in docs};bundle=read_bundle()
    native=set(read('benchmarks/results/round12/coverage_final.json')['eligible_ids'])
    eligible={int(r['document_id']) for r in rows if r['eligible_for_fingerprint_coverage']=='True'}
    final=read('benchmarks/results/round13/legacy_supported_observations.json')['final_cases']
    for did in eligible:
        r=next(r for r in bundle['records'] if r['document_id']==did and r['ocr_metadata'].get('source_kind')=='maintenance_derived_legacy')
        assert r['status']=='active' and r['catalog_binding_sha256']==binding(by[did])
        c=next(c for c in final if c['provenance']['document_id']==did)
        assert c['document_correct'] and 'fingerprint_v3' in c['signals'] and 'content_fingerprint_match' in c['signals']
        assert c['input_sha256']==r['ocr_metadata']['derived_sha256']!=r['canonical_file_sha256']
    supported=native|eligible;needed=math.ceil(.85*1158)
    result=dict(file_backed_total=1158,operational_total=1212,native_fingerprint_supported=len(native),
                runtime_usable_fingerprint_supported=len(supported),native_percent=100*len(native)/1158,
                runtime_usable_percent=100*len(supported)/1158,all_operational_percent=100*len(supported)/1212,
                legacy_eligible_count=len(eligible),legacy_ineligible_count=40-len(eligible),shared_supported_count=33,
                exact_shortfall_to_85=max(0,needed-len(supported)),minimum_required=needed,
                native_eligible_ids=sorted(native),legacy_eligible_ids=sorted(eligible),eligible_ids=sorted(supported),
                coverage_definition='runtime_usable_fingerprint_supported',definition_sha256=definition,
                legacy_exclusion_reasons=dict(Counter(r['exclusion_reason'] for r in rows if r['eligible_for_fingerprint_coverage']!='True')))
    result['pass']=result['runtime_usable_percent']>=85 and result['all_operational_percent']>=70
    atomic_json(OUT/'coverage_final.json',result)
    with (OUT/'final_recovery.csv').open('w',encoding='utf8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=['document_id','source','action','success','reason'],lineterminator='\n');writer.writeheader()
        if not result['pass']:
            # Only already-known best alternatives; no repeated blocked crawl.
            prior=list(csv.DictReader((ROOT/'benchmarks/results/round12/fingerprint_recovery.csv').open(encoding='utf8')))
            for r in prior:
                if int(r['document_id']) in [174,177,179,951,954,1216]:
                    writer.writerow(dict(document_id=r['document_id'],source=r['source'],action='review known cached alternative and immutable prior attempt',success=False,
                                         reason=r['final_reason']+'; no new safe evidence, no repeated permanent/policy request'))
    print('R13 coverage',result,flush=True)


def wilson(k,n):
    if not n:return None
    z=1.959963984540054;p=k/n;den=1+z*z/n;center=(p+z*z/(2*n))/den
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return dict(lower=max(0,center-half),upper=min(1,center+half),method='Wilson score two-sided95%',n=n)


def unknown():
    cov=read('benchmarks/results/round13/coverage_final.json')
    release=validate(read('benchmarks/manifests/official_unknown_release_v1.json'));master=validate(read('benchmarks/manifests/official_unknown_master_v1.json'))
    assert [c['case_id'] for c in select(master['cases'])]==[c['case_id'] for c in release['cases']]
    manifest_sha=sha('benchmarks/manifests/official_unknown_release_v1.json')
    assert manifest_sha==read('benchmarks/results/round13/baseline_audit.json')['unknown_manifest_sha256']
    target=OUT/'unknown_release_v1.json';stats=balance(release['cases'])
    if not cov['pass']:
        atomic_json(target,dict(status='not_run',reason='Coverage below historical support gate',selected_count=105,recognition_calls=0,cases=[],rejection_rate=None,confidence_interval_95=None,manifest_sha256=manifest_sha))
        return
    if target.exists():raise ValueError('Unknown release already exported; preserve single-shot results')
    common.SEED=2026101313;ident=common.identity()
    key={k:v for k,v in ident.items() if k not in ['commit','executed_at']}
    key.update(manifest_sha256=manifest_sha,definition_sha256=cov['definition_sha256'])
    journal=CaseJournal(ROOT/'benchmarks/work/round13/unknown-release.sqlite',identity=key,expected_ids=[c['case_id'] for c in release['cases']])
    marker=OUT/'unknown_release_started.json'
    if marker.exists():assert read('benchmarks/results/round13/unknown_release_started.json')['identity']==key
    else:atomic_json(marker,dict(identity=key,selection_seed=release['selection_seed'],expected_count=105,scope='Predictions start only after coverage pass; no tuning or reselection. Resume only same identity/set.'))
    pending=set(journal.pending());docs,families=catalog()
    for i,c in enumerate(release['cases'],1):
        if c['case_id'] not in pending:continue
        raw=(ROOT/'benchmarks/cache'/(c['SHA256']+'.body')).read_bytes();assert hashlib.sha256(raw).hexdigest()==c['SHA256']
        cc=dict(id=c['case_id'],group=c['resource_group'],category=c['document_type'],expected=dict(match_type='NO_MATCH'),
                label_status='confirmed_unknown',representation='official_original',provenance=dict(source=c['source'],entity=c['entity'],sha256=c['SHA256'],historically_seen=c['historically_seen']))
        row=common.case_result(cc,raw,'unknown.pdf' if c['mime']=='application/pdf' else 'unknown.docx',docs,families)
        journal.append(row)
        if i%10==0:print('R13 unknown release persisted',i,'/105',flush=True)
    rows=journal.rows();export=OUT/'unknown_release_observations.json';journal.export(export,complete=True)
    def metrics(values):
        n=len(values);no=sum(r['observed']['match_type']=='NO_MATCH' and not r['extraction_failed'] for r in values)
        wrong_doc=sum(r['observed']['match_type']=='DOCUMENT_MATCH' for r in values);wrong_family=sum(r['observed']['match_type']=='FAMILY_MATCH' for r in values)
        return dict(n=n,correct_no_match=no,wrong_document_match=wrong_doc,wrong_family_match=wrong_family,
                    extraction_failed=sum(r['extraction_failed'] for r in values),false_acceptance_rate=(wrong_doc+wrong_family)/n if n else None,
                    rejection_rate=no/n if n else None,confidence_interval_95=wilson(no,n),entity_errors=wrong_doc)
    m=metrics(rows)
    atomic_json(target,dict(schema_version=1,status='complete',identity=ident,manifest_sha256=manifest_sha,
                expected_count=105,actual_count=len(rows),unique_case_ids=len({r['id'] for r in rows}),recognition_calls=len(rows),
                **m,selection=stats,per_source={s:metrics([r for r in rows if r['provenance']['source']==s]) for s in stats['counts_per_source']},
                per_category={s:metrics([r for r in rows if r['category']==s]) for s in stats['document_types']},
                wrong_accepts=[dict(id=r['id'],observed=r['observed'],signals=r['signals']) for r in rows if r['observed']['match_type']!='NO_MATCH'],
                observations_sha256=hashlib.sha256(export.read_bytes()).hexdigest(),passed=m['rejection_rate']>=.99 and m['entity_errors']==0,
                entity_error_basis='Conservative unsupported document/entity assertions on NO_MATCH; no inference from hosting authority alone.',
                scope='First R13 release single-shot, same frozen R11 manifest. Historical55 exposure retained; Wilson interval describes this finite set, not a claim of independent population performance. No tuning or labels changed.'))
    print('R13 unknown release',m,flush=True)


def configure():
    from benchmarks import round8_validation as previous
    common.OUT='benchmarks/results/round13/';common.SEED=2026101313;previous.OUT=common.OUT
    write=lambda path,value:atomic_json(ROOT/path,value)
    common.write=write;previous.write=write
    return previous


def canonical():
    previous=configure()
    previous.active_records=lambda:[r for r in read_bundle()['records'] if r['status']=='active' and r['mime_type'] in ['application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document']]
    previous.canonical()
    from maintenance.legacy_convert import convert_official
    from maintenance.round13_legacy import normalize_pdf
    docs,families=catalog();cases=[]
    for r in read_bundle()['records']:
        if r['status']!='active' or r['ocr_metadata'].get('source_kind')!='maintenance_derived_legacy':continue
        raw=(ROOT/'benchmarks/cache'/(r['canonical_file_sha256']+'.body')).read_bytes()
        pdf=normalize_pdf(convert_official(raw,r['ocr_metadata']['original_format'],ROOT/'benchmarks/work/round13-canonical')[0])
        assert hashlib.sha256(pdf).hexdigest()==r['ocr_metadata']['derived_sha256'],'Legacy derivation changed'
        cc=dict(id='CAN13-LEGACY-'+str(r['document_id']),group='document:'+str(r['document_id']),category='legacy_canonical_representation',
                expected=dict(match_type='DOCUMENT_MATCH',document_id=r['document_id']),representation='deterministic_derived_pdf',label_status='source_association_audited')
        cases.append(common.case_result(cc,pdf,'legacy-derived.pdf',docs,families))
    common.save('canonical_legacy',cases,scope='Supported derived representations, not official PDF byte identities; native canonical reported separately.')


def performance():
    from benchmarks import round12_performance as perf
    perf.OUT=OUT/'performance_confirmation.json';perf.SEED=2026101313
    perf.main()
    r=read('benchmarks/results/round13/performance_confirmation.json')
    r.update(p50_runs=[c['latency_ms']['p50'] for c in r['runs']],p95_runs=[c['latency_ms']['p95'] for c in r['runs']],
             max_p95=max(c['latency_ms']['p95'] for c in r['runs']),historical_gate='Median<=250ms mandatory; 4/5 preferred, not blocker.')
    atomic_json(perf.OUT,r)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['coverage','unknown','historical','canonical','verify','performance']);a=p.parse_args()
    if a.mode=='historical':configure().historical()
    elif a.mode=='verify':
        from scripts import round9_verify
        round9_verify.atomic_json=lambda path,value:atomic_json(OUT/path.name,value);round9_verify.main()
    else:globals()[a.mode]()
