"""Prospective fixed stratified selection, generation and leakage barrier."""
import csv
from collections import Counter,defaultdict
from scripts.round19_common import *
from benchmarks.round3_audit import catalog
from benchmarks.round8_common import raw_record,case
from benchmarks import round8_common as common
from benchmarks.round6_recognition import TRANSFORMS
from benchmarks.round8_fill import generate
from benchmarks.round19_representations import derivative,scan,reopened,seed_for
from src.fingerprint_v3 import read_bundle

WORK=ROOT/'benchmarks/work/round19/evaluation-v5'

def representation_key(did,name,params):
    return json.dumps([did,name,params],sort_keys=True,separators=(',',':'))

def prior_representations():
    paths=['benchmarks/results/round5/robustness.json','benchmarks/results/round6/robustness_v2.json',
           'benchmarks/results/round7/robustness_v3.json','benchmarks/results/round8/evaluation_prepared.json',
           'benchmarks/results/round8/calibration_observations_v4.json','benchmarks/results/round9/calibration_observations_v5.json']
    keys=set();hashes=set()
    def walk(node):
        if isinstance(node,list):
            for child in node:walk(child)
        elif isinstance(node,dict):
            provenance=node.get('provenance',{});e=node.get('expected',{});did=provenance.get('document_id',e.get('document_id'))
            if did is not None and node.get('representation'):
                keys.add(representation_key(did,node['representation'],provenance.get('transform',provenance.get('transform_params',{}))))
            h=node.get('input_sha256',node.get('sha256'))
            if isinstance(h,str) and len(h)==64:hashes.add(h)
            for child in node.values():walk(child)
    for p in paths:
        if (ROOT/p).exists():walk(read(p))
    return keys,hashes

def plan():
    sealed();assert read(OUT/'evaluation_v5_preflight.json')['passed']
    assert not (OUT/'evaluation_v5_plan.json').exists()
    docs,_=catalog();by={d.id:d for d in docs}
    pool=read(OUT/'round18_pool_diagnostics.json')['pool'];sources=defaultdict(list)
    for r in pool:sources[r['source_id']].append(r)
    key=lambda r:hashlib.sha256(f"{SEED}:{r['document_id']}:{r['sha256']}".encode()).hexdigest()
    selected=[];ids=set();counts=Counter();strata=Counter();docx=0
    def metadata(r):
        d=by[r['document_id']];pages=r['pages']
        return (d.ente,r['mime_type'],bool(d.codice),bool(d.versione),'1' if pages==1 else '2-5' if pages<=5 else '6+')
    while len(selected)<50:
        progress=False
        for sid in sorted(sources):
            reserved=sum(not counts[s] and s!=sid and all(r['mime_type']!='application/pdf' for r in rs) for s,rs in sources.items())
            r=min((r for r in sources[sid] if r['document_id'] not in ids and counts[sid]<10 and (r['mime_type']=='application/pdf' or docx<2-reserved)),key=lambda r:(sum(strata[(i,v)] for i,v in enumerate(metadata(r))),key(r)),default=None)
            if r:
                selected.append(r);ids.add(r['document_id']);counts[sid]+=1;docx+=r['mime_type']!='application/pdf';progress=True
                strata.update((i,v) for i,v in enumerate(metadata(r)))
        if not progress:break
    assert len(selected)>=30 and len(counts)>=6 and max(counts.values())/len(selected)<=.35
    fillers=[];fc=Counter()
    for r in sorted((r for r in selected if r['mime_type']=='application/pdf'),key=lambda r:(not r['field_count'],key(r))):
        if fc[r['source_id']]>=3:continue
        fillers.append(r['document_id']);fc[r['source_id']]+=1
        if len(fillers)==12:break
    transforms=[dict(name=n,params=dict(p,noise_fraction=.0005,noise_amplitude=2)) for n,p in TRANSFORMS if n not in ['digital_exact','resize_075']]
    save('evaluation_v5_plan',dict(freeze_commit=FREEZE,selection_seed=SEED,selected=sorted(selected,key=key),filled_identities=fillers,source_counts=dict(counts),source_concentration=max(counts.values())/len(selected),sampling_max=.35,preferred_max=.30,
         strata_counts={name:dict(Counter(str(metadata(r)[i]) for r in selected)) for i,name in enumerate(['entity','format','coded','versioned','page_count_bucket'])},transform_policy=transforms,
         registry_sha256=sha(REGISTRY),preflight_sha256=sha(OUT/'evaluation_v5_preflight.json'),source_policy_sha256=sha('benchmarks/reference/v5_source_counting_policy_v1.json'),
         method='Metadata/hash-only round robin,target50,max10/source,max2DOCX;12 PDF fillers prefer fields,max3/source. No predictions. Distinct per-case seed adds0.05% scan pixels with +/-2 intensity; no metadata-only freshness for scans. Digital derivatives rebuild PDF objects/XML; normalization flattens widgets/canonicalizes XML. Filled variants1419..1423 are new synthetic values.',created_at=now()))
    print('R19 V5 plan',len(selected),dict(counts),flush=True)

def prepare_inputs():
    sealed();common.SEED=SEED
    assert not (OUT/'evaluation_v5_prepared.json').exists()
    p=read(OUT/'evaluation_v5_plan.json');records=read_bundle()['records'];WORK.mkdir(parents=True,exist_ok=True)
    prior_keys,prior_hashes=prior_representations()
    seen=set(read(REGISTRY)['observed_resource_sha256'])|{r['canonical_file_sha256'] for r in records}|prior_hashes
    items=[];generation=[];audit=[]
    for chosen in p['selected']:
        did=chosen['document_id'];r=next(r for r in records if r['document_id']==did and r['canonical_file_sha256']==chosen['sha256']);raw=raw_record(r);ext='.pdf' if r['mime_type']=='application/pdf' else '.docx'
        variants=[('digital_canonical_derivative',dict(method='rebuild_objects_xml_v1')),('digital_normalized',dict(method='flatten_clean_xml_c14n_v1'))]
        if ext=='.pdf':variants.extend((t['name'],t['params']) for t in p['transform_policy'])
        if did in p['filled_identities']:variants.extend(('filled_'+str(j),dict(variant=1419+j)) for j in range(5))
        for name,params in variants:
            seed=seed_for(SEED,did,name);params=dict(params,noise_seed=seed) if 'noise_fraction' in params else dict(params)
            cc=case(r,name,params);cc['id']=f'R19V5-{did}-{name}';cc['provenance']['representation_seed']=seed
            filled=name.startswith('filled_');g=dict(case_id=cc['id'],document_id=did,filled=filled,generated=False,reopened=False,fields_verified=0,method='',error='')
            try:
                if filled:
                    value,details=generate(raw,'canonical'+ext,params['variant']);suffix=ext
                    assert details['reopened'] and details['synthetic_verified'] and details['fields_verified']>0
                    g.update(reopened=True,fields_verified=details['fields_verified'],method=details['generation_method'],acroform_static=details['acroform_static'])
                elif name.startswith('digital_'):value,suffix=derivative(raw,ext,name=='digital_normalized')
                else:value,suffix=scan(raw,params,seed)
                reopened(value,suffix);h=hashlib.sha256(value).hexdigest();path=WORK/(cc['id']+suffix);path.write_bytes(value)
                g.update(generated=True,reopened=True)
                items.append(dict(case=cc,path=path.relative_to(ROOT).as_posix(),sha256=h,filled=filled,scan_like=not name.startswith('digital_') and not filled,unknown=False))
                # New algorithm/params/seed differ from all previous standard
                # transforms; prior bytes are still checked independently.
                equivalent=representation_key(did,name,params) in prior_keys
                audit.append(dict(case_id=cc['id'],document_id=did,transformation=name,params=params,seed=seed,SHA=h,prior_SHA_seen=h in seen,prior_case_equivalent=equivalent,fresh_representation=h not in seen and not equivalent,equivalence_basis='Compared to actual historical transform/parameter keys and SHA union. New structural derivative method, raster noise realization, or actual synthetic field values; not a renamed case/metadata perturbation.'))
            except (ValueError,OSError,RuntimeError,AssertionError) as ex:g['error']=type(ex).__name__+': '+str(ex)
            generation.append(g)
        print('R19 prepared',did,len(items),flush=True)
    # Exactly30 deterministically selected existing unknowns, same semantic F.
    mix=[];uc=Counter()
    for c in sorted(read('benchmarks/manifests/official_unknown_release_v3.json')['cases'],key=lambda c:hashlib.sha256(f"{SEED}:mix:{c['SHA256']}".encode()).hexdigest()):
        if uc[c['source']]>=6:continue
        mix.append(c);uc[c['source']]+=1
        if len(mix)==30:break
    for c in mix:
        cc=dict(id='R19V5U-'+c['case_id'],group=c['resource_group'],category=c['document_type'],expected=dict(match_type='NO_MATCH'),label_status='confirmed_unknown_v3_mix',representation='official_original',provenance=dict(source=c['source'],entity=c['entity'],sha256=c['SHA256'],official_url=c['official_url'],truth_version=c['version'],same_freeze_unknown_v3_mix=True))
        ext='.pdf' if c['mime']=='application/pdf' else '.docx';path=WORK/(cc['id']+ext);value=(ROOT/'benchmarks/cache'/(c['SHA256']+'.body')).read_bytes();assert hashlib.sha256(value).hexdigest()==c['SHA256'];path.write_bytes(value)
        items.append(dict(case=cc,path=path.relative_to(ROOT).as_posix(),sha256=c['SHA256'],filled=False,scan_like=False,unknown=True))
    known=[c for c in items if not c['unknown']];attempted=sum(g['filled'] for g in generation);filled=sum(c['filled'] for c in known)
    ids={c['document_id'] for c in p['selected']};registry={k['document_id']:k for k in read(REGISTRY)['known_identities']}
    overlap=[i for i in ids if not registry[i]['eligible_v5']];duplicates={h:n for h,n in Counter(c['sha256'] for c in items).items() if n>1}
    bad=[a['case_id'] for a in audit if not a['fresh_representation']];dupids=len(items)-len({c['case']['id'] for c in items})
    leakage=dict(identity_tuning_overlap=overlap,representation_overlap=bad,SHA_overlap=bad,duplicate_representation_sha=duplicates,duplicate_case_ids=dupids,truth_ambiguity=[],unknown_mix_exception='30 previously observed v3 resources on the identical semantic freeze; not fresh known representations and not independent unknown evidence.',prohibited_leakage=len(overlap)+len(bad)+sum(n-1 for n in duplicates.values())+dupids)
    leakage['passed']=leakage['prohibited_leakage']==0
    save('evaluation_v5_representation_audit',dict(cases=audit,all_fresh=not bad,case_equivalence_policy='Identity + actual transformation algorithm/parameters/seed; seed affects actual pixels/fields. Digital structural derivatives differ from previous digital_exact. Canonical original SHA excluded.',recognition_calls=0))
    save('evaluation_v5_leakage',leakage)
    save('evaluation_v5_prepared',dict(plan_sha256=sha(OUT/'evaluation_v5_plan.json'),representations=items,generation_audit=generation,recognition_calls=0,created_at=now()))
    stats=dict(identities=len(ids),sources=len(p['source_counts']),known=len(known),scans=sum(c['scan_like'] for c in known),valid_filled=filled,attempted_filled=attempted,filled_generation_rate=filled/attempted if attempted else 0,unknown_mix=len(mix))
    passed=stats['identities']>=30 and stats['sources']>=6 and stats['known']>=400 and stats['scans']>=200 and filled>=50 and len(mix)>=30 and stats['filled_generation_rate']>=.9 and leakage['passed']
    save('evaluation_v5_generation_preflight',dict(**stats,passed=passed,prepared_sha256=sha(OUT/'evaluation_v5_prepared.json'),recognition_calls=0))
    with (OUT/'evaluation_v5_filled_generation_audit.csv').open('w',encoding='utf8',newline='') as stream:
        fields=['case_id','document_id','filled','generated','reopened','fields_verified','method','error','acroform_static'];w=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(g for g in generation if g['filled'])
    print('R19 generated adequacy',stats,'passed',passed,flush=True)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['plan','prepare']);a=p.parse_args();dict(plan=plan,prepare=prepare_inputs)[a.mode]()
