"""Resume-safe filled regeneration and metadata-only V6 preflight. No predictions."""
import argparse,os,tempfile
from collections import Counter
from scripts.round22_common import *
from benchmarks.transactional_writer import CaseJournal
from benchmarks.round19_representations import seed_for,reopened
from benchmarks.round19_plan import prior_representations,representation_key
from benchmarks.round22_fill import generate

def atomic_pdf(path,raw):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if any(p.is_symlink() or p.is_junction() for p in [path,*path.parents]):raise ValueError('Linked filled destination')
    if path.exists():
        if path.read_bytes()!=raw:raise ValueError('Existing completed output differs; refuse overwrite')
        return
    fd,name=tempfile.mkstemp(prefix=path.name+'.',suffix='.partial',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as out:out.write(raw);out.flush();os.fsync(out.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)
    assert path.read_bytes()==raw

def generate_one(item,raw=None,folder=None):
    row=dict(id=item['case']['id'],case_id=item['case']['id'],document_id=item['case']['expected']['document_id'],seed=item['seed'],variant=item['variant'],canonical_sha256=item['canonical_sha'],generated=False,valid_generated=False,error=None)
    try:
        if raw is None:raw=(ROOT/'benchmarks/cache'/(item['canonical_sha']+'.body')).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==item['canonical_sha']
        value,audit=generate(raw,item['variant'],item['seed'],read(POLICY))
        path=(folder or WORK/'filled-v2')/(item['case']['id']+'.pdf');atomic_pdf(path,value)
        assert path.stat().st_size>0 and sha(path)==audit['sha256']
        row.update(generated=True,valid_generated=True,audit=audit,mode=audit['mode'],fallback_from_acroform=audit['fallback_from_acroform'],generated_sha256=audit['sha256'],sha256=audit['sha256'],path=path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path),filename=path.name,case=item['case'],filled=True,scan_like=False,unknown=False,written_and_readback_verified=True)
    except Exception as exc:row.update(error=type(exc).__name__+': '+str(exc),exception_type=type(exc).__name__,failure_stage='generation_or_validation_or_atomic_write')
    return row

def inputs():
    from src.fingerprint_v3 import read_bundle
    from benchmarks import round8_common as common
    common.SEED=SEED;records=read_bundle()['records'];plan=read('benchmarks/results/round21/evaluation_v6_plan.json');by={c['document_id']:c for c in plan['selected']};items=[]
    for did in plan['filled_identities']:
        c=by[did];r=next(r for r in records if r['document_id']==did and r['canonical_file_sha256']==c['canonical_sha'])
        for i in range(plan['filled_variants_per_identity']):
            name='filled_'+str(i);seed=seed_for(SEED,did,name);variant=21000+seed%1_000_000;cc=common.case(r,name,dict(variant=variant));cc['id']=f'R21V6-{did}-{name}';cc['provenance']['representation_seed']=seed
            items.append(dict(case=cc,canonical_sha=c['canonical_sha'],seed=seed,variant=variant))
    assert len(items)==100 and len({c['case']['id'] for c in items})==100
    return items

def regenerate():
    f=boundary();assert not (OUT/'evaluation_v6_started.json').exists() and not (OUT/'filled_generation_v2.json').exists()
    assert sha(POLICY)==read(OUT/'filled_policy_frozen.json')['policy_sha256']
    items=inputs();m=dict(items=items,plan_sha256=sha('benchmarks/results/round21/evaluation_v6_plan.json'),policy_sha256=sha(POLICY))
    if (OUT/'filled_generation_inputs.json').exists():assert read(OUT/'filled_generation_inputs.json')==m
    else:save('filled_generation_inputs',m)
    key=dict(generator_sha256=sha('benchmarks/round22_fill.py'),runner_sha256=sha(__file__),policy_sha256=sha(POLICY),inputs_sha256=sha(OUT/'filled_generation_inputs.json'),recognition_semantic_sha256=f['recognition_semantic_hash'])
    journal=CaseJournal(WORK/'filled-generation-v2.sqlite',identity=key,expected_ids=[c['case']['id'] for c in items]);pending=set(journal.pending());done=len(items)-len(pending)
    checkpoint('Round22 coherent100-case filled generation v2 active','Policy v2 fixed before aggregation;same20IDs/5variants/caseIDs/seeds;all previous outputs preserved.', 'Resume generation journal pending IDs only with identical generator/policy/input hashes; never resample failed cases.',[dict(command='python -m benchmarks.round22_prepare generate',log='reports/round22-filled-generation.log',state='running; transactional generation receipts')])
    for item in items:
        if item['case']['id'] not in pending:continue
        row=generate_one(item);journal.append(row);done+=1
        if done%5==0:print('R22 filled generation persisted',done,'/100',flush=True)
    rows=journal.rows();journal.export(OUT/'filled_generation_v2_observations.json',complete=True)
    valid=[c for c in rows if c['valid_generated']];passed=len(valid)>=50 and len(valid)/100>=.9
    result=dict(identity=key,created_at=now(),generation_attempted=100,generation_valid=len(valid),generation_success_rate=len(valid)/100,preferred_pass=len(valid)>=95,passed=passed,recognition_calls=0,observations_sha256=sha(OUT/'filled_generation_v2_observations.json'),cases=rows,failures=[c for c in rows if not c['valid_generated']],mode_counts=dict(Counter(c['mode'] for c in valid)),fallback_count=sum(c['fallback_from_acroform'] for c in valid),policy_sha256=sha(POLICY))
    save('filled_generation_v2',result);boundary();print('R22 filled result',len(valid),'/100 PASS',passed,'modes',result['mode_counts'],flush=True)

def manifest():
    f=boundary();g=read(OUT/'filled_generation_v2.json');assert not (OUT/'v6_representation_manifest.json').exists()
    old=read('benchmarks/results/round21/evaluation_v6_prepared.json');nonfilled=[c for c in old['representations'] if not c['filled']];filled=[{k:c[k] for k in ['case','path','filename','sha256','filled','scan_like','unknown']} for c in g['cases'] if c['valid_generated']]
    rows=nonfilled+filled;plan=read('benchmarks/results/round21/evaluation_v6_plan.json');selected={c['document_id'] for c in plan['selected']};reserved={c['document_id'] for c in read(RESERVED)['cases'] if c['reserved_for_v6'] and not c['prior_tuning_seen']};registry=read(REGISTRY)
    assert len(nonfilled)==497 and len({c['case']['id'] for c in rows})==len(rows)
    validation=[]
    from src.fingerprint_v3 import read_bundle
    canonical={r['canonical_file_sha256'] for r in read_bundle()['records']}
    prior_keys,seen=prior_representations();seen|=canonical|set(registry['observed_resource_sha256'])
    # Generation alone is not recognition exposure. Reused Round21 outputs are
    # explicitly unpredicted; every actual historical observation remains banned.
    for path in [*ROOT.glob('benchmarks/results/round19/*observations*.json'),*ROOT.glob('benchmarks/results/round20/development_observations_*.json'),*ROOT.glob('benchmarks/results/round21/*observations*.json')]:
        for c in read(path).get('cases',[]):
            h=c.get('input_sha256')
            if h:seen.add(h)
    oldsha={c['sha256'] for c in old['representations']};oldby={c['case']['id']:c for c in nonfilled};inputby={c['case']['id']:c for c in inputs()};bad=[]
    for c in rows:
        path=ROOT/c['path'];assert path.is_file() and sha(path)==c['sha256'];reopened(path.read_bytes(),path.suffix)
        did=c['case']['expected']['document_id'];assert did in selected
        if c['filled']:assert c['case']==inputby[c['case']['id']]['case']
        else:assert c==oldby[c['case']['id']]
        p=c['case']['provenance'];name=c['case']['representation'];equivalent=representation_key(did,name,p['transform']) in prior_keys
        prior_seen=c['sha256'] in seen
        if prior_seen or equivalent:bad.append(c['case']['id'])
        validation.append(dict(case_id=c['case']['id'],document_id=did,SHA256=c['sha256'],file_exists=True,reopened=True,expected_identity_verified=True,transform_metadata_verified=True,validation_status='valid',filled=c['filled'],prior_prediction_SHA_seen=prior_seen,prior_equivalent=equivalent,previously_generated_unpredicted=c['sha256'] in oldsha,carried_round21_nonfilled=not c['filled']))
    duplicate_ids=len(rows)-len({c['case']['id'] for c in rows});duplicates={h:n for h,n in Counter(c['sha256'] for c in rows).items() if n>1};knownsha={c['sha256'] for c in rows};unknownsha={c['SHA256'] for c in read(UNKNOWN)['cases']}
    leak=dict(identity_tuning_overlap=sorted(selected&set(registry['round21']['development_identity_ids'])),unreserved_overlap=sorted(selected-reserved),V5_overlap=sorted(selected&set(registry['round20']['V5_identity_ids'])),prior_observed_representation_overlap=bad,unknown_overlap=sorted(knownsha&unknownsha),duplicate_case_ids=duplicate_ids,duplicate_SHA=duplicates,truth_ambiguity=[],seed_reuse_in_predictions=False,reserved_unpredicted_seed_preserved=True,scope='Same Round21 reserved seeds/representations have never been predicted;497 carried nonfilled hashes and any identical regenerated fill hash are explicitly unobserved. All actual historic prediction SHA,canonical hashes,tuning identities and equivalent historical representations remain excluded.')
    leak['prohibited_leakage']=sum(len(leak[n]) for n in ['identity_tuning_overlap','unreserved_overlap','V5_overlap','prior_observed_representation_overlap','unknown_overlap','duplicate_SHA','truth_ambiguity'])+duplicate_ids
    leak['passed']=leak['prohibited_leakage']==0;save('evaluation_v6_leakage',leak)
    m=dict(created_at=now(),recognition_calls=0,representations=rows,validation=validation,expected_count=len(rows),unique_case_ids=len(rows),generation_sha256=sha(OUT/'filled_generation_v2.json'),original_identity_plan_sha256=sha('benchmarks/results/round21/evaluation_v6_plan.json'),filled_policy_sha256=sha(POLICY),carried_nonfilled=497,filled_valid=len(filled),scan_count=sum(c['scan_like'] for c in rows))
    save('v6_representation_manifest',m)
    unknown=read('benchmarks/results/round21/unknown_release_v4.json')
    pre=dict(identities=len(selected),sources=len(plan['source_counts']),source_concentration=plan['source_concentration'],known_representations=len(rows),scan_like=sum(c['scan_like'] for c in rows),valid_filled=len(filled),generation_success_rate=g['generation_success_rate'],unknown_v4_available=unknown['n'],leakage_prohibited=leak['prohibited_leakage'],recognition_engine_unchanged=True,unknown_v4_engine_compatible=unknown['identity']['runtime_sha256']==f['recognition_semantic_hash'],recognition_calls=0,manifest_sha256=sha(OUT/'v6_representation_manifest.json'))
    pre['passed']=len(selected)>=30 and len(plan['source_counts'])>=6 and len(rows)>=400 and pre['scan_like']>=200 and len(filled)>=50 and unknown['n']>=30 and leak['passed'] and g['passed'] and pre['unknown_v4_engine_compatible'];save('evaluation_v6_preflight',pre)
    before=read(OUT/'recognition_freeze_check.json')['recognition_files_sha256'];after=recognition_files();assert before==after
    save('generator_change_scope',dict(recognition_semantics_changed=False,recognition_files_before=before,recognition_files_after=after,allowed_scope=['benchmark generation','validation','runner/checkpoint','new infrastructural tests/docs','release reporting/packaging'],new_generator_sha256=sha('benchmarks/round22_fill.py'),old_generator_v1_unchanged=True,original_selected_identities_and_seeds_unchanged=True,unknown_v4_replayed=False,checked_at=now()))
    boundary();checkpoint('Round22 generation and V6 preflight complete','Filled'+str(len(filled))+'/100,known'+str(len(rows))+'/420scans,leakage'+str(leak['prohibited_leakage'])+';same engine/unknown/identity plan.', 'If preflight PASS freeze all evaluation artifacts,then V6 once. On failure no predictions;finish NOT READY.')
    print('R22 V6 preflight',pre,'leakage',leak['prohibited_leakage'],flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['generate','manifest']);a=p.parse_args();{'generate':regenerate,'manifest':manifest}[a.mode]()
