"""Sealed metadata selection and transactional unknown4/V6 single-shot runs."""
import argparse,csv
from collections import Counter,defaultdict
from concurrent.futures import ProcessPoolExecutor,as_completed
from functools import lru_cache
from scripts.round21_common import *
from benchmarks.round4_common import runtime_hash
from benchmarks.evaluate import code_hash,summary
from benchmarks.transactional_writer import CaseJournal
from benchmarks.round3_audit import catalog
from benchmarks import round8_common as common
from benchmarks.round8_common import case_result,raw_record,case
from benchmarks.round17_unknown import metrics as unknown_metrics
from benchmarks.unknown_release import balance
from benchmarks.round19_representations import derivative,scan,reopened,seed_for
from benchmarks.round19_plan import prior_representations,representation_key
from benchmarks.round8_fill import generate
from benchmarks.round6_recognition import TRANSFORMS
from src.fingerprint_v3 import read_bundle

UNKNOWN='benchmarks/manifests/official_unknown_release_v4.json'
RESERVED='benchmarks/manifests/v6_reserved_identity_pool.json'
REGISTRY='benchmarks/reference/benchmark_contamination_registry_v7.json'
UNKNOWN_SEED=202610142104
V6_SEED=202610142106

def sealed():
    preserved();f=read(OUT/'freeze_manifest.json')
    assert f['recognition_semantic_hash']==runtime_hash()
    assert f['full_code_sha256']==code_hash()
    for p,h in f['frozen_files_sha256'].items():assert sha(p)==h,p
    return f

def fixed_selection(cases,*,seed,target,source_field,identity_field,cap,strata):
    groups=defaultdict(list)
    for c in cases:groups[c[source_field]].append(c)
    used=set();counts=Counter();frequencies=Counter();chosen=[]
    key=lambda c:hashlib.sha256(f"{seed}:{c[identity_field]}".encode()).hexdigest()
    while len(chosen)<target:
        progress=False
        for source_id in sorted(groups,key=str):
            eligible=[c for c in groups[source_id] if c[identity_field] not in used and counts[source_id]<cap]
            if not eligible:continue
            c=min(eligible,key=lambda c:(sum(frequencies[(i,v)] for i,v in enumerate(strata(c))),key(c)))
            chosen.append(c);used.add(c[identity_field]);counts[source_id]+=1;frequencies.update((i,v) for i,v in enumerate(strata(c)));progress=True
            if len(chosen)==target:break
        if not progress:break
    return sorted(chosen,key=key)

def select_unknown():
    sealed();assert not (ROOT/UNKNOWN).exists()
    truth=read(OUT/'unknown_v4_truth_audit.json');pool=truth['confirmed_cases']
    chosen=fixed_selection(pool,seed=UNKNOWN_SEED,target=120,source_field='source',identity_field='SHA256',cap=24,strata=lambda c:(c['entity'],c['document_type'],c['mime'],bool(c.get('code')),bool(c.get('version'))))
    stats=balance(chosen);assert stats['total']>=100 and stats['sources']>=8 and stats['max_concentration']<=.25
    assert len({c['SHA256'] for c in chosen})==len(chosen)
    from maintenance.round21_unknown_acquire import exclusions
    old,_=exclusions();assert not {c['SHA256'] for c in chosen}&old
    rows=[dict(c,resource_group='unknown_release_v4',truth_status='confirmed_unknown',contamination_status='fresh',previously_seen=False,historically_seen=False) for c in chosen]
    m=dict(schema_version=1,manifest_id='official-unknown-release-v4',freeze_manifest_sha256=sha(OUT/'freeze_manifest.json'),selection_seed=UNKNOWN_SEED,registry_sha256=sha(REGISTRY),truth_audit_sha256=sha(OUT/'unknown_v4_truth_audit.json'),cases=rows,selection=stats,recognition_calls=0,created_at=now(),selection_policy='After freeze; fixed source round-robin then underrepresented type/entity/format/code/version strata and seeded SHA. No prediction or recognition-score information.')
    atomic_json(ROOT/UNKNOWN,m);save('unknown_v4_selection',dict(manifest_sha256=sha(UNKNOWN),selection=stats,case_ids=[c['case_id'] for c in rows],recognition_calls=0))
    print('R21 unknown4 selected',stats,flush=True)

@lru_cache(maxsize=1)
def worker_catalog():return catalog()
def worker_init(expected_runtime):assert runtime_hash()==expected_runtime;worker_catalog()
def worker(item):
    raw=(ROOT/item['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==item['sha256']
    docs,families=worker_catalog();r=case_result(item['case'],raw,item['filename'],docs,families)
    r.update(filled=item.get('filled',False),scan_like=item.get('scan_like',False),unknown=item.get('unknown',False));return r

def journal_run(name,items):
    f=sealed();key=dict(freeze_manifest_sha256=sha(OUT/'freeze_manifest.json'),semantic_source_tree=f['semantic_source_tree'],runtime_sha256=runtime_hash(),fingerprint_sha256=sha('data/document_recognition_fingerprints_v3.json'),runner_code_sha256=code_hash(),registry_sha256=sha(REGISTRY),input_manifest_sha256=sha(UNKNOWN) if name=='unknown_release_v4' else sha(OUT/'evaluation_v6_prepared.json'))
    journal=CaseJournal(WORK/(name+'.sqlite'),identity=key,expected_ids=[c['case']['id'] for c in items]);pending=set(journal.pending())
    marker=OUT/(name+'_started.json')
    if marker.exists():assert read(marker)['identity']==key
    else:save(name+'_started',dict(identity=key,expected_count=len(items),single_shot=True,started_at=now()))
    checkpoint('Round21 '+name+' single-shot active','Frozen runtime/tree/registry and manifests verified. No post-freeze tuning allowed.',f'Follow{name} journal; resume pending IDs only with identical freeze/code/input identity. Never replay a completed result.',[dict(command='python -m benchmarks.round21_release '+('unknown' if name=='unknown_release_v4' else 'evaluate'),log='reports/round21-'+name+'.log',state='running; transactional journal')])
    done=len(items)-len(pending)
    with ProcessPoolExecutor(max_workers=3,initializer=worker_init,initargs=(f['recognition_semantic_hash'],)) as pool:
        futures={pool.submit(worker,c):c['case']['id'] for c in items if c['case']['id'] in pending}
        for future in as_completed(futures):
            r=future.result();assert r['id']==futures[future];journal.append(r);done+=1
            if done%10==0:print('R21',name,'persisted',done,'/',len(items),flush=True)
    rows=journal.rows();target=OUT/(name+'_observations.json');journal.export(target,complete=True)
    import jsonschema
    jsonschema.validate(read(target),read('benchmarks/schemas/round21_observations.schema.json'))
    assert len(rows)==len(items)==len({r['id'] for r in rows})
    assert {r['id']:r['input_sha256'] for r in rows}=={c['case']['id']:c['sha256'] for c in items}
    sealed();return rows,key,target

def run_unknown():
    sealed();assert not (OUT/'unknown_release_v4.json').exists(),'Completed single-shot; no replay'
    m=read(UNKNOWN);assert m['freeze_manifest_sha256']==sha(OUT/'freeze_manifest.json') and m['truth_audit_sha256']==sha(OUT/'unknown_v4_truth_audit.json')
    items=[]
    for c in m['cases']:
        cc=dict(id=c['case_id'],group=c['resource_group'],category=c['document_type'],expected=dict(match_type='NO_MATCH'),label_status='confirmed_unknown',representation='official_original',provenance=dict(source=c['source'],entity=c['entity'],sha256=c['SHA256'],official_url=c['official_url'],truth_version=c.get('version'),previously_seen=False))
        items.append(dict(case=cc,path='benchmarks/cache/'+c['SHA256']+'.body',filename='unknown.pdf' if c['mime']=='application/pdf' else 'unknown.docx',sha256=c['SHA256'],unknown=True))
    rows,key,target=journal_run('unknown_release_v4',items);metrics=unknown_metrics(rows)
    save('unknown_release_v4',dict(status='complete',identity=key,**metrics,expected_count=len(items),actual_count=len(rows),unique_case_ids=len(rows),recognition_calls=len(rows),manifest_sha256=sha(UNKNOWN),observations_sha256=sha(target),selection=m['selection'],passed=metrics['rejection_rate']>=.99 and metrics['false_acceptance_rate']<=.01 and metrics['entity_errors']==metrics['version_errors']==0,per_source={s:unknown_metrics([r for r in rows if r['provenance']['source']==s]) for s in sorted({r['provenance']['source'] for r in rows})},wrong_accepts=[dict(id=r['id'],observed=r['observed'],signals=r['signals']) for r in rows if r['observed']['match_type']!='NO_MATCH'],scope='First and only fresh unknown4 predictions on the sealed v7 runtime. Extraction failure is never credited as correct rejection. No tuning/relabel/replay.'))
    print('R21 unknown4 result',metrics,flush=True)

def plan_v6():
    sealed();assert read(OUT/'unknown_release_v4.json')['passed'];assert not (OUT/'evaluation_v6_plan.json').exists()
    pool=read(RESERVED)['cases'];docs,_=catalog();by={d.id:d for d in docs}
    selected=fixed_selection(pool,seed=V6_SEED,target=40,source_field='source_id',identity_field='document_id',cap=10,strata=lambda c:(by[c['document_id']].ente,c['mime_type'],bool(by[c['document_id']].codice),bool(by[c['document_id']].versione),'1' if c['pages']==1 else '2-5' if c['pages']<=5 else '6+'))
    counts=Counter(c['source_id'] for c in selected);assert len(selected)>=30 and len(counts)>=6 and max(counts.values())/len(selected)<=.35
    fills=[];fc=Counter()
    for c in sorted((c for c in selected if c['mime_type']=='application/pdf'),key=lambda c:(not c['field_count'],seed_for(V6_SEED,c['document_id'],'fill_selection'))):
        if fc[c['source_id']]>=4:continue
        fills.append(c['document_id']);fc[c['source_id']]+=1
        if len(fills)==20:break
    assert len(fills)>=10
    transforms=[dict(name=n,params=dict(p,noise_fraction=.0005,noise_amplitude=2)) for n,p in TRANSFORMS if n not in ['digital_exact','resize_075']]
    save('evaluation_v6_plan',dict(selection_seed=V6_SEED,selected=selected,source_counts=dict(counts),source_concentration=max(counts.values())/len(selected),filled_identities=fills,filled_variants_per_identity=5,transform_policy=transforms,freeze_manifest_sha256=sha(OUT/'freeze_manifest.json'),reservation_manifest_sha256=sha(RESERVED),registry_sha256=sha(REGISTRY),created_at=now(),recognition_calls=0,policy='Fixed metadata/hash-only target40,max10/source; no dependence on unknown predictions except mandatory global gate. Up to20 PDF filler IDs prefer fields,max4/source,5 predeclared fresh synthetic variants each. No resampling after failures.'))
    print('R21 V6 plan',len(selected),dict(counts),'fillIDs',len(fills),flush=True)

def prepare_v6():
    sealed();assert read(OUT/'unknown_release_v4.json')['passed'];assert not (OUT/'evaluation_v6_prepared.json').exists()
    p=read(OUT/'evaluation_v6_plan.json');common.SEED=V6_SEED;records=read_bundle()['records'];folder=WORK/'evaluation-v6';folder.mkdir(parents=True,exist_ok=True)
    prior_keys,seen=prior_representations();seen|=set(read(REGISTRY)['observed_resource_sha256']);seen|={r['canonical_file_sha256'] for r in records}
    for path in [ROOT/'benchmarks/results/round19/evaluation_v5_prepared.json']:
        seen.update(c['sha256'] for c in read(path)['representations'])
    for path in [*ROOT.glob('benchmarks/results/round20/development_observations_*.json'),*OUT.glob('development_observations_*.json')]:seen.update(c['input_sha256'] for c in read(path)['cases'] if c.get('input_sha256'))
    rows=[];generation=[];audit=[]
    for chosen in p['selected']:
        did=chosen['document_id'];r=next(r for r in records if r['document_id']==did and r['canonical_file_sha256']==chosen['canonical_sha']);raw=raw_record(r);ext='.pdf' if r['mime_type']=='application/pdf' else '.docx'
        variants=[('digital_canonical_derivative',dict(method='rebuild_objects_xml_v1')),('digital_normalized',dict(method='flatten_clean_xml_c14n_v1'))]
        if ext=='.pdf':variants.extend((c['name'],c['params']) for c in p['transform_policy'])
        if did in p['filled_identities']:variants.extend(('filled_'+str(i),dict(variant=21000+seed_for(V6_SEED,did,'filled_'+str(i))%1_000_000)) for i in range(5))
        for name,params0 in variants:
            seed=seed_for(V6_SEED,did,name);params=dict(params0,noise_seed=seed) if 'noise_fraction' in params0 else dict(params0);cc=case(r,name,params);cc['id']=f'R21V6-{did}-{name}';cc['provenance']['representation_seed']=seed
            filled=name.startswith('filled_');g=dict(case_id=cc['id'],document_id=did,filled=filled,generated=False,reopened=False,fields_verified=0,error='')
            try:
                if filled:
                    value,detail=generate(raw,'canonical'+ext,params['variant']);suffix=ext;assert detail['reopened'] and detail['synthetic_verified'] and detail['fields_verified']>0;g.update(fields_verified=detail['fields_verified'],method=detail['generation_method'])
                elif name.startswith('digital_'):value,suffix=derivative(raw,ext,name=='digital_normalized')
                else:value,suffix=scan(raw,params,seed)
                reopened(value,suffix);h=hashlib.sha256(value).hexdigest();path=folder/(cc['id']+suffix);path.write_bytes(value);g.update(generated=True,reopened=True)
                rows.append(dict(case=cc,path=path.relative_to(ROOT).as_posix(),filename=path.name,sha256=h,filled=filled,scan_like=not name.startswith('digital_') and not filled,unknown=False))
                equivalent=representation_key(did,name,params) in prior_keys
                audit.append(dict(case_id=cc['id'],document_id=did,seed=seed,params=params,SHA256=h,prior_SHA_seen=h in seen,prior_equivalent=equivalent,fresh=h not in seen and not equivalent))
            except (ValueError,OSError,RuntimeError,AssertionError) as ex:g['error']=type(ex).__name__+': '+str(ex)
            generation.append(g)
        print('R21 V6 prepared',did,len(rows),flush=True)
    reserved={c['document_id'] for c in read(RESERVED)['cases'] if c['reserved_for_v6'] and not c['prior_tuning_seen']};selected={c['document_id'] for c in p['selected']}
    overlap=sorted(selected-reserved);bad=[a['case_id'] for a in audit if not a['fresh']];duplicates={h:n for h,n in Counter(c['sha256'] for c in rows).items() if n>1};duplicate_ids=len(rows)-len({c['case']['id'] for c in rows})
    leakage=dict(identity_tuning_overlap=overlap,V5_overlap=sorted(selected&set(read(REGISTRY)['round20']['V5_identity_ids'])),representation_overlap=bad,seed_reuse=V6_SEED in [2026101208,2026101419,2026101420],duplicate_case_ids=duplicate_ids,duplicate_SHA=duplicates,truth_ambiguity=[],prohibited_leakage=len(overlap)+len(bad)+len(duplicates)+duplicate_ids)
    leakage['passed']=not leakage['prohibited_leakage'] and not leakage['V5_overlap'] and not leakage['seed_reuse'];save('evaluation_v6_leakage',leakage)
    save('evaluation_v6_representation_audit',dict(cases=audit,recognition_calls=0,all_fresh=not bad))
    save('evaluation_v6_prepared',dict(representations=rows,generation_audit=generation,plan_sha256=sha(OUT/'evaluation_v6_plan.json'),recognition_calls=0,created_at=now()))
    attempted=sum(g['filled'] for g in generation);valid=sum(c['filled'] for c in rows);scans=sum(c['scan_like'] for c in rows)
    stats=dict(identities=len(selected),sources=len(p['source_counts']),known=len(rows),scans=scans,valid_filled=valid,attempted_filled=attempted,filled_generation_rate=valid/attempted if attempted else 0)
    save('evaluation_v6_generation_preflight',dict(**stats,passed=len(selected)>=30 and len(p['source_counts'])>=6 and len(rows)>=400 and scans>=200 and valid>=50 and stats['filled_generation_rate']>=.9 and leakage['passed'],recognition_calls=0,prepared_sha256=sha(OUT/'evaluation_v6_prepared.json')))
    with (OUT/'evaluation_v6_filled_generation_audit.csv').open('w',encoding='utf8',newline='') as stream:
        filled_rows=[g for g in generation if g['filled']];fields=sorted(set().union(*(r.keys() for r in filled_rows)));w=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(filled_rows)
    print('R21 V6 generation',stats,flush=True)

def evaluate_v6():
    sealed();assert read(OUT/'unknown_release_v4.json')['passed'] and read(OUT/'evaluation_v6_generation_preflight.json')['passed'];assert not (OUT/'evaluation_v6_gate.json').exists(),'Completed V6; no replay'
    rows,key,target=journal_run('evaluation_v6',read(OUT/'evaluation_v6_prepared.json')['representations']);scan_rows=[r for r in rows if r['scan_like']];filled=[r for r in rows if r['filled']];unknown=read(OUT/'unknown_release_v4_observations.json')['cases']
    for name,cs in [('robustness_v6',rows),('scan_v6',scan_rows),('filled_v6',filled),('end_to_end_v6',rows+unknown)]:save(name,dict(status='complete',summary=summary(cs),cases=cs,identity=key,observations_sha256=sha(target),scope='Fresh known V6 single-shot. End-to-end includes the existing fresh unknown4 observations without any second recognition call.'))
    retrieval={str(k):sum(r['candidate_recall_at_k'][str(k)] for r in rows)/len(rows) for k in [1,5,10,25]};save('retrieval_v6',dict(status='complete',n=len(rows),recall_at_k=retrieval,observations_sha256=sha(target)))
    def rates(cs):
        tp=sum(r['document_correct'] for r in cs);ac=sum(r['observed']['match_type']=='DOCUMENT_MATCH' for r in cs);return dict(n=len(cs),exact=tp,wrong=ac-tp,accepted=ac,precision=tp/ac if ac else 0,recall=tp/len(cs) if cs else 0,f1=2*tp/(len(cs)+ac) if cs else 0)
    m,s,f=map(rates,[rows,scan_rows,filled]);errors=dict(entity=sum(r['entity_error'] for r in rows),version=sum(r['version_error'] for r in rows));generation=read(OUT/'evaluation_v6_generation_preflight.json')['filled_generation_rate'];u=read(OUT/'unknown_release_v4.json');gates={}
    for name,actual,passed in [('v6_precision',m['precision'],m['precision']>=.995),('v6_exact_recall',m['recall'],m['recall']>=.9),('v6_scan_precision',s['precision'],s['precision']>=.995),('v6_scan_recall',s['recall'],s['recall']>=.85),('v6_filled_generation',generation,generation>=.9),('v6_filled_precision',f['precision'],f['precision']>=.995),('v6_filled_recall',f['recall'],f['recall']>=.9),('v6_retrieval_at25',retrieval['25'],retrieval['25']==1),('v6_retrieval_at1',retrieval['1'],retrieval['1']>=.99),('v6_entity_version',errors,not any(errors.values())),('unknown_end_to_end',u['rejection_rate'],u['passed'])]:gates[name]=dict(actual=actual,passed=passed)
    save('evaluation_v6_gate',dict(passed=all(v['passed'] for v in gates.values()),gates=gates,metrics=m,scan=s,filled=f,errors=errors,retrieval=retrieval,identity=key,expected_count=len(rows),actual_count=len(rows),unique_case_ids=len(rows),observations_sha256=sha(target),single_shot=True,known_recognition_calls=len(rows),unknown_recognition_calls_repeated=0,freeze_manifest_sha256=sha(OUT/'freeze_manifest.json')))
    print('R21 V6 complete',m,s,f,'gates',gates,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['select-unknown','unknown','plan','prepare','evaluate']);a=p.parse_args();{'select-unknown':select_unknown,'unknown':run_unknown,'plan':plan_v6,'prepare':prepare_v6,'evaluate':evaluate_v6}[a.mode]()
