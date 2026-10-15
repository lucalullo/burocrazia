"""Fresh identity audit, deterministic representations, one transactional v5 run."""
import argparse,csv,re
from collections import Counter,defaultdict
from concurrent.futures import ProcessPoolExecutor,as_completed
from rapidfuzz.fuzz import ratio
from scripts.round18_common import *
from benchmarks.round3_audit import catalog
from benchmarks.round8_common import case,case_result,raw_record,identity
from benchmarks import round8_common as common
from benchmarks.round8_evaluation import transformed
from benchmarks.round8_fill import generate
from benchmarks.round6_recognition import TRANSFORMS
from benchmarks.transactional_writer import CaseJournal
from benchmarks.evaluate import summary,code_hash
from src.recognize import normalize_text
from src.fingerprint_v3 import read_bundle
from src.document_fingerprints import binding

WORK=ROOT/'benchmarks/work/round18/evaluation-v5'

def plan():
    common.SEED=SEED
    f=sealed();assert read(OUT/'unknown_release_v3.json')['passed'],'Unknown gate must pass first'
    assert not (OUT/'evaluation_v5_plan.json').exists(),'Prospective plan already fixed'
    docs,_=catalog();by={d.id:d for d in docs};registry=read(REGISTRY);known={c['document_id']:c for c in registry['known_identities']};records=read_bundle()['records']
    contaminated={i for i,c in known.items() if not c['eligible_v5']};old=[r for r in records if r['document_id'] in contaminated]
    old_shas={r['canonical_file_sha256'] for r in old};old_urls={u for r in old for u in [r['url'],r['final_url']]};old_docs=[by[i] for i in contaminated if i in by]
    fields=[set(r['field_set']) for r in old if len(r['field_set'])>=8];aggregates=[set(r['aggregate']) for r in old if len(r['aggregate'])>=24]
    verified={r['expected']['document_id'] for n in ['canonical','canonical_legacy'] for r in read(OUT/(n+'.json'))['cases'] if r['correct']}
    key=lambda r:hashlib.sha256((str(SEED)+':'+str(r['document_id'])+':'+r['canonical_file_sha256']).encode()).hexdigest()
    def relation(r):
        d=by[r['document_id']]
        if d.id in contaminated:return 'contaminated_identity'
        if d.stato_verifica in ['demo','rifiutato'] or d.id not in verified:return 'not_operational_or_not_current_canonical_verified'
        if r['status']!='active' or r['catalog_binding_sha256']!=binding(d):return 'unsupported_binding'
        if r['mime_type'] not in ['application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document']:return 'legacy_not_native_upload'
        if r['canonical_file_sha256'] in old_shas:return 'resource_sha_overlap'
        if r['url'] in old_urls or r['final_url'] in old_urls:return 'url_overlap'
        title=normalize_text(d.titolo_ufficiale);code=normalize_text(d.codice or '')
        if any((code and code==normalize_text(c.codice or '') and d.ente==c.ente) or (d.versione==c.versione and (not code or not c.codice or code==normalize_text(c.codice)) and ratio(title,normalize_text(c.titolo_ufficiale))>=92) for c in old_docs):return 'near_title_code_version'
        fs=set(r['field_set']);ag=set(r['aggregate'])
        if len(fs)>=8 and any(len(fs&s)/max(1,len(fs|s))>=.90 for s in fields):return 'near_field_template'
        if len(ag)>=24 and any(len(ag&s)/max(1,len(ag|s))>=.85 for s in aggregates):return 'near_aggregate_template'
        return None
    pool={};audit=[]
    for r in sorted(records,key=key):
        reason=relation(r);audit.append(dict(document_id=r['document_id'],source=r['source_id'],canonical_sha256=r['canonical_file_sha256'],binding_current=r['catalog_binding_sha256']==binding(by[r['document_id']]),canonical_verified=r['document_id'] in verified,eligible=not reason,exclusion=reason or '',previously_influential=r['document_id'] in contaminated))
        if not reason:pool.setdefault(r['document_id'],r)
    with (OUT/'evaluation_v5_pool_audit.csv').open('w',encoding='utf8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(audit[0]),lineterminator='\n');writer.writeheader();writer.writerows(audit)
    sources=defaultdict(list)
    for r in pool.values():sources[r['source_id']].append(r)
    selected=[];ids=set();counts=Counter();docx=0;strata=Counter()
    def metadata(r):
        d=by[r['document_id']]
        pages=len(r['pages'])
        return (d.ente,r['mime_type'],bool(d.codice),bool(d.versione),'1' if pages==1 else '2-5' if pages<=5 else '6+')
    def stratified(r):
        return (sum(strata[(i,v)] for i,v in enumerate(metadata(r))),key(r))
    while len(selected)<50:
        progress=False
        for sid in sorted(sources):
            r=min((r for r in sources[sid] if r['document_id'] not in ids and counts[sid]<10 and (r['mime_type']=='application/pdf' or docx<2)),key=stratified,default=None)
            if r:
                selected.append(r);ids.add(r['document_id']);counts[sid]+=1;docx+=r['mime_type']!='application/pdf';progress=True
                strata.update((i,v) for i,v in enumerate(metadata(r)))
                if len(selected)==50:break
        if not progress:break
    fillers=[];fc=Counter()
    for r in sorted([r for r in selected if r['mime_type']=='application/pdf'],key=lambda r:(not bool(r['field_set']),key(r))):
        if fc[r['source_id']]>=3:continue
        fillers.append(r['document_id']);fc[r['source_id']]+=1
        if len(fillers)==12:break
    selected.sort(key=key)
    value=dict(freeze_commit=f['freeze_git_commit'],registry_sha256=sha(REGISTRY),pool_audit_sha256=sha(OUT/'evaluation_v5_pool_audit.csv'),selection_seed=SEED,selected=[dict(document_id=r['document_id'],sha256=r['canonical_file_sha256'],source_id=r['source_id']) for r in selected],filled_identities=fillers,source_counts=dict(counts),created_at=now(),method='Metadata/hash-only source round-robin,50 identities target,max10/source,max2DOCX;12 PDF fillers preferring fields,max3/source. No scores or recognition probes. Fourteen fixed scans per PDF plus canonical/normalized digital,5 filled variants/filler.')
    value['strata_counts']={name:dict(Counter(str(metadata(r)[i]) for r in selected)) for i,name in enumerate(['entity','format','coded','versioned','page_count_bucket'])}
    value['transform_policy']=[dict(name=n,params=p) for n,p in TRANSFORMS if n not in ['digital_exact','resize_075']]
    save('evaluation_v5_plan',value)
    save('evaluation_v5_leakage',dict(prohibited_leakage=0,selected_identity_overlap=sorted(ids&contaminated),near_template_overlap=[r['document_id'] for r in selected if relation(r)],pool_audit_sha256=value['pool_audit_sha256'],passed=not(ids&contaminated) and not any(relation(r) for r in selected),basis='Canonical-only technical verification explicitly allowed; all prior influential tuning/development/evaluation identities and their resource/template near variants excluded.'))
    print('R18 v5 plan',len(selected),'identities',len(counts),'sources',flush=True)

def prepare_inputs():
    common.SEED=SEED
    sealed();assert not (OUT/'evaluation_v5_prepared.json').exists()
    p=read(OUT/'evaluation_v5_plan.json');records=read_bundle()['records'];WORK.mkdir(parents=True,exist_ok=True);items=[];generation=[]
    scans=[t for t in TRANSFORMS if t[0] not in ['digital_exact','resize_075']]
    for i,chosen in enumerate(p['selected']):
        r=next(r for r in records if r['document_id']==chosen['document_id'] and r['canonical_file_sha256']==chosen['sha256']);raw=raw_record(r);ext='.pdf' if r['mime_type']=='application/pdf' else '.docx'
        variants=[('digital_exact',{}),('digital_normalized',{})]
        if ext=='.pdf':variants.extend(scans)
        if r['document_id'] in p['filled_identities']:variants.extend(('filled_'+str(j),dict(variant=j)) for j in range(5))
        for name,params in variants:
            cc=case(r,name,params);cc['id']='V5-'+str(r['document_id'])+'-'+name
            filled=name.startswith('filled_');audit=dict(case_id=cc['id'],document_id=r['document_id'],filled=filled,generated=False,reopened=False,fields_verified=0,method='',error='')
            try:
                if filled:
                    value,details=generate(raw,'canonical'+ext,params['variant']);suffix=ext
                    assert details['reopened'] and details['synthetic_verified'] and details['fields_verified']>0
                    audit.update(reopened=True,fields_verified=details['fields_verified'],method=details['generation_method'],acroform_static=details['acroform_static'])
                elif name=='digital_exact':value,suffix=raw,ext
                elif name=='digital_normalized':
                    if ext=='.pdf':
                        import pymupdf
                        with pymupdf.open(stream=raw,filetype='pdf') as pdf:
                            pdf.set_metadata(dict(pdf.metadata,producer='BurOCRazia synthetic normalized benchmark'))
                            value=pdf.tobytes(garbage=4,deflate=True,no_new_id=True)
                    else:
                        from docx import Document
                        from io import BytesIO
                        document=Document(BytesIO(raw));document.core_properties.comments='BurOCRazia synthetic normalized benchmark';buffer=BytesIO();document.save(buffer);value=buffer.getvalue()
                    suffix=ext
                else:value,suffix=transformed(raw,params)
                if suffix=='.pdf':
                    import pymupdf
                    with pymupdf.open(stream=value,filetype='pdf') as pdf:assert not pdf.needs_pass and 1<=len(pdf)<=100
                elif suffix in ['.png','.jpg']:
                    from PIL import Image
                    from io import BytesIO
                    with Image.open(BytesIO(value)) as image:assert image.width*image.height<=40_000_000;image.verify()
                else:
                    from docx import Document
                    from io import BytesIO
                    Document(BytesIO(value))
                assert len(value)<=20*1024*1024
                h=hashlib.sha256(value).hexdigest();path=WORK/(cc['id']+suffix);path.write_bytes(value)
                audit.update(generated=True,reopened=True)
                items.append(dict(case=cc,path=path.relative_to(ROOT).as_posix(),sha256=h,filled=filled,scan_like=name not in ['digital_exact','digital_normalized'] and not filled,unknown=False))
            except (ValueError,OSError,RuntimeError,AssertionError) as ex:audit['error']=type(ex).__name__+': '+str(ex)
            generation.append(audit)
        print('R18 v5 prepared',r['document_id'],len(items),flush=True)
    # Explicit same-freeze v3 end-to-end mix: deterministic selection before
    # v5 predictions. This is a named mix, never a new independent unknown set.
    unknowns=read('benchmarks/manifests/official_unknown_release_v3.json')['cases'];uc=Counter();mix=[]
    for c in sorted(unknowns,key=lambda c:hashlib.sha256((str(SEED)+':mix:'+c['SHA256']).encode()).hexdigest()):
        if uc[c['source']]>=6:continue
        mix.append(c);uc[c['source']]+=1
        if len(mix)==30:break
    for c in mix:
        cc=dict(id='V5U-'+c['case_id'],group=c['resource_group'],category=c['document_type'],expected=dict(match_type='NO_MATCH'),label_status='confirmed_unknown_v3_mix',representation='official_original',provenance=dict(source=c['source'],entity=c['entity'],sha256=c['SHA256'],official_url=c['official_url'],truth_version=c['version'],same_freeze_unknown_v3_mix=True))
        ext='.pdf' if c['mime']=='application/pdf' else '.docx';path=WORK/(cc['id']+ext);path.write_bytes((ROOT/'benchmarks/cache'/(c['SHA256']+'.body')).read_bytes())
        items.append(dict(case=cc,path=path.relative_to(ROOT).as_posix(),sha256=c['SHA256'],filled=False,scan_like=False,unknown=True))
    known=[c for c in items if not c['unknown']];attempted=sum(c['filled'] for c in generation);valid=sum(c['filled'] for c in known)
    stats=dict(identities=len(p['selected']),sources=len(p['source_counts']),known=len(known),scans=sum(c['scan_like'] for c in known),valid_filled=valid,attempted_filled=attempted,filled_generation_rate=valid/attempted if attempted else 0,unknown_mix=len(mix))
    passed=stats['identities']>=30 and stats['sources']>=6 and stats['known']>=400 and stats['scans']>=200 and valid>=50 and len(mix)>=30 and stats['filled_generation_rate']>=.9 and read(OUT/'evaluation_v5_leakage.json')['passed']
    assert len({c['case']['id'] for c in items})==len(items)
    duplicate_sha={h:[c['case']['id'] for c in items if c['sha256']==h] for h,n in Counter(c['sha256'] for c in items).items() if n>1}
    leakage=read(OUT/'evaluation_v5_leakage.json')
    leakage.update(duplicate_representation=duplicate_sha,case_id_duplication=0,calibration_overlap=leakage['selected_identity_overlap'],
                   improper_sha_overlap=[],near_duplicate_contamination=leakage['near_template_overlap'])
    leakage['prohibited_leakage']+=sum(len(v)-1 for v in duplicate_sha.values())
    leakage['passed'] &= not duplicate_sha
    save('evaluation_v5_leakage',leakage)
    passed &= leakage['passed']
    save('evaluation_v5_prepared',dict(plan_sha256=sha(OUT/'evaluation_v5_plan.json'),representations=items,generation_audit=generation,recognition_calls=0,created_at=now()))
    save('evaluation_v5_preflight',dict(**stats,passed=passed,prepared_sha256=sha(OUT/'evaluation_v5_prepared.json'),recognition_calls=0))
    with (OUT/'evaluation_v5_filled_generation_audit.csv').open('w',encoding='utf8',newline='') as stream:
        fields=['case_id','document_id','filled','generated','reopened','fields_verified','method','error','acroform_static'];writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n');writer.writeheader();writer.writerows(c for c in generation if c['filled'])
    print('R18 v5 preflight',stats,passed,flush=True)

def worker(item):
    raw=(ROOT/item['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==item['sha256']
    r=case_result(item['case'],raw,Path(item['path']).name);r.update(filled=item['filled'],scan_like=item['scan_like'],unknown=item['unknown']);return r

def run():
    common.SEED=SEED
    f=sealed();assert read(OUT/'evaluation_v5_preflight.json')['passed'];assert not (OUT/'evaluation_v5_gate.json').exists(),'No completed evaluation replay'
    prepared=read(OUT/'evaluation_v5_prepared.json');items=prepared['representations'];ident=identity();key=dict(freeze_commit=f['freeze_git_commit'],prepared_sha256=sha(OUT/'evaluation_v5_prepared.json'),runtime_sha256=ident['runtime_sha256'],fingerprint_sha256=ident['fingerprint_sha256'],runner_code_sha256=code_hash(),registry_sha256=sha(REGISTRY),infrastructure_sha256=infrastructure_sha256())
    journal=CaseJournal(WORK/'evaluation.sqlite',identity=key,expected_ids=[c['case']['id'] for c in items]);pending=set(journal.pending())
    if not (OUT/'evaluation_v5_started.json').exists():save('evaluation_v5_started',dict(identity=key,expected_count=len(items),single_shot=True,created_at=now()))
    else:assert read(OUT/'evaluation_v5_started.json')['identity']==key
    with ProcessPoolExecutor(max_workers=3) as pool:
        jobs={pool.submit(worker,c):c['case']['id'] for c in items if c['case']['id'] in pending}
        for future in as_completed(jobs):
            r=future.result();assert r['id']==jobs[future];journal.append(r)
            if len(journal.rows())%25==0:print('R18 v5 persisted',len(journal.rows()),'/',len(items),flush=True)
    rows=journal.rows();journal.export(OUT/'evaluation_v5_observations.json',complete=True);assert len(rows)==len(items)==len({r['id'] for r in rows})
    import jsonschema
    jsonschema.validate(read(OUT/'evaluation_v5_observations.json'),read('benchmarks/schemas/round18_evaluation_observations.schema.json'))
    assert {r['id']:r['input_sha256'] for r in rows}=={c['case']['id']:c['sha256'] for c in items}
    known=[r for r in rows if not r['unknown']];scans=[r for r in known if r['scan_like']];filled=[r for r in known if r['filled']];unknown=[r for r in rows if r['unknown']]
    for name,group in [('robustness_v5',known),('scan_v5',scans),('filled_v5',filled),('end_to_end_v5',rows)]:save(name,dict(summary=summary(group),cases=group,identity=ident,observations_sha256=sha(OUT/'evaluation_v5_observations.json')))
    retrieval={str(k):sum(r['candidate_recall_at_k'][str(k)] for r in known)/len(known) for k in [1,5,10,25]};save('retrieval_v5',dict(n=len(known),recall_at_k=retrieval,observations_sha256=sha(OUT/'evaluation_v5_observations.json')))
    gates={}
    def g(n,a,passed):gates[n]=dict(actual=a,passed=bool(passed))
    def rate(group):
        tp=sum(r['document_correct'] for r in group);accepted=sum(r['observed']['match_type']=='DOCUMENT_MATCH' for r in group)
        return tp/accepted if accepted else 0,tp/len(group) if group else 0
    precision,recall=rate(known);sp,sr=rate(scans);fp,fr=rate(filled);generation=read(OUT/'evaluation_v5_preflight.json')['filled_generation_rate'];errors=dict(entity=sum(r['entity_error'] for r in known),version=sum(r['version_error'] for r in known));reject=sum(r['observed']['match_type']=='NO_MATCH' and not r['extraction_failed'] for r in unknown)/len(unknown)
    g('v5_preflight',read(OUT/'evaluation_v5_preflight.json'),True);g('v5_leakage',0,read(OUT/'evaluation_v5_leakage.json')['passed']);g('v5_precision',precision,precision>=.995);g('v5_exact_recall',recall,recall>=.90);g('v5_scan_precision',sp,sp>=.995);g('v5_scan_recall',sr,sr>=.85);g('v5_filled_generation',generation,generation>=.90);g('v5_filled_precision',fp,fp>=.995);g('v5_filled_recall',fr,fr>=.90);g('v5_retrieval_at25',retrieval['25'],retrieval['25']==1);g('v5_retrieval_at1',retrieval['1'],retrieval['1']>=.99);g('v5_entity_version',errors,not any(errors.values()));g('v5_unknown_mix',reject,reject>=.99)
    save('evaluation_v5_gate',dict(passed=all(v['passed'] for v in gates.values()),gates=gates,expected_count=len(items),actual_count=len(rows),unique_case_ids=len(rows),final_observations_sha256=sha(OUT/'evaluation_v5_observations.json'),freeze_commit=f['freeze_git_commit'],identity=ident,single_shot=True))
    sealed();print('R18 v5 final gates',gates,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['plan','prepare','run']);a=p.parse_args();dict(plan=plan,prepare=prepare_inputs,run=run)[a.mode]()
