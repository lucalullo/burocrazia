"""Content-addressed artifact freeze and sole fresh V6 recognition run."""
import argparse,math
from collections import Counter
from concurrent.futures import ProcessPoolExecutor,as_completed
from functools import lru_cache
from scripts.round22_common import *
from benchmarks.evaluate import code_hash,summary
from benchmarks.round4_common import runtime_hash
from benchmarks.transactional_writer import CaseJournal
from benchmarks.round8_common import case_result

def seal():
    boundary();assert read(OUT/'evaluation_v6_preflight.json')['passed'];assert not (OUT/'evaluation_freeze_manifest.json').exists()
    paths=[*ROOT.glob('src/**/*.py'),*ROOT.glob('benchmarks/*.py'),*ROOT.glob('maintenance/*.py'),*ROOT.glob('data/recognition_profiles/*.json'),*ROOT.glob('data/document_recognition_fingerprints*.json'),ROOT/'app.py',ROOT/'run.py',ROOT/'data/recognition_features.json',ROOT/'scripts/benchmark.py',ROOT/'scripts/round22_common.py',ROOT/'tests/test_round22_generator.py',ROOT/POLICY,ROOT/REGISTRY,ROOT/RESERVED,ROOT/UNKNOWN,ROOT/'benchmarks/results/round21/evaluation_v6_plan.json',ROOT/'benchmarks/results/round21/unknown_release_v4_observations.json',ROOT/'benchmarks/results/round21/unknown_release_v4.json',ROOT/'benchmarks/schemas/round21_observations.schema.json']
    paths.extend(OUT/n for n in ['recognition_freeze_check.json','filled_policy_frozen.json','filled_generation_inputs.json','filled_generation_v2.json','filled_generation_v2_observations.json','generator_change_scope.json','evaluation_v6_preflight.json','evaluation_v6_leakage.json','v6_representation_manifest.json','visual_review_inputs.json','visual_review_result.json'])
    f=dict(schema_version=1,created_at=now(),HEAD_commit=head(),new_commit_created=False,recognition_source_tree=read('benchmarks/results/round21/freeze_manifest.json')['semantic_source_tree'],working_tree_recognition_hash=runtime_hash(),recognition_files_sha256=recognition_files(),full_code_sha256=code_hash(),fingerprint_dataset_sha256=sha('data/document_recognition_fingerprints_v3.json'),decision_v7_sha256=sha('data/recognition_profiles/fingerprint_decision_v7.json'),catalog_semantic_sha256=catalog_semantic(),contamination_registry_sha256=sha(REGISTRY),V6_identity_manifest_sha256=sha(RESERVED),selected_identity_plan_sha256=sha('benchmarks/results/round21/evaluation_v6_plan.json'),transformation_policy_sha256=sha('benchmarks/results/round21/evaluation_v6_plan.json'),filled_policy_sha256=sha(POLICY),unknown_v4_manifest_sha256=sha(UNKNOWN),unknown_v4_raw_result_sha256=sha('benchmarks/results/round21/unknown_release_v4_observations.json'),leakage_sha256=sha(OUT/'evaluation_v6_leakage.json'),generator_result_sha256=sha(OUT/'filled_generation_v2.json'),representations_sha256=sha(OUT/'v6_representation_manifest.json'),frozen_files_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(set(paths))},policy='Content-addressed freeze of existing recognition plus final representation/policy/validation/runner artifacts. No commit. No semantic/generator/representation/label/selection/seed changes after first result. Unknown4 is reused from its sole original observations,never replayed.')
    save('evaluation_freeze_manifest',f);checkpoint('Round22 evaluation artifacts frozen; V6 next','Generator/preflight/leakage and unchanged-engine/unknown compatibility PASS. All selected IDs,case IDs,seeds,bytes,policies bound by SHA.', 'Run benchmarks.round22_release evaluate once;resume journal pending IDs only on identical freeze. No post-result tuning.')
    print('R22 evaluation freeze',sha(OUT/'evaluation_freeze_manifest.json'),runtime_hash(),flush=True)

def sealed():
    boundary();f=read(OUT/'evaluation_freeze_manifest.json');assert f['working_tree_recognition_hash']==runtime_hash() and f['full_code_sha256']==code_hash()
    assert f['recognition_files_sha256']==recognition_files()
    for p,h in f['frozen_files_sha256'].items():assert sha(p)==h,p
    return f

@lru_cache(maxsize=1)
def worker_catalog():
    from benchmarks.round3_audit import catalog
    return catalog()  # Metadata only; request text/features remain local.
def init(expected):assert runtime_hash()==expected;worker_catalog()
def worker(c):
    raw=(ROOT/c['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==c['sha256'];docs,families=worker_catalog();r=case_result(c['case'],raw,c['filename'],docs,families)
    r.update(filled=c['filled'],scan_like=c['scan_like'],unknown=False);return r

def wilson(x,n):
    if not n:return dict(lower=None,upper=None)
    z=1.959963984540054;p=x/n;d=1+z*z/n;mid=(p+z*z/(2*n))/d;half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return dict(lower=max(0,mid-half),upper=min(1,mid+half),method='Nominal Wilson95%; representation rows are correlated by40 selected identities,not a population guarantee.')
def rates(rows):
    n=len(rows);tp=sum(r['document_correct'] for r in rows);accepted=sum(r['observed']['match_type']=='DOCUMENT_MATCH' for r in rows);fp=accepted-tp
    return dict(n=n,TP=tp,FP=fp,FN=n-tp,exact=tp,wrong=fp,family=sum(r['observed']['match_type']=='FAMILY_MATCH' for r in rows),reject=sum(r['observed']['match_type']=='NO_MATCH' for r in rows),precision=tp/accepted if accepted else 0,recall=tp/n if n else 0,f1=2*tp/(n+accepted) if n+accepted else 0,precision_ci95=wilson(tp,accepted),recall_ci95=wilson(tp,n),extraction_failed=sum(r['extraction_failed'] for r in rows),entity_errors=sum(r['entity_error'] for r in rows),version_errors=sum(r['version_error'] for r in rows))

def evaluate():
    f=sealed();assert not (OUT/'evaluation_v6_gate.json').exists(),'Completed V6 single-shot; no replay'
    m=read(OUT/'v6_representation_manifest.json');items=m['representations'];key=dict(freeze_manifest_sha256=sha(OUT/'evaluation_freeze_manifest.json'),semantic_source_tree=f['recognition_source_tree'],input_manifest_sha256=sha(OUT/'v6_representation_manifest.json'),runtime_sha256=runtime_hash(),fingerprint_sha256=f['fingerprint_dataset_sha256'],runner_code_sha256=code_hash(),registry_sha256=sha(REGISTRY))
    journal=CaseJournal(WORK/'evaluation-v6.sqlite',identity=key,expected_ids=[c['case']['id'] for c in items]);pending=set(journal.pending());done=len(items)-len(pending)
    if (OUT/'evaluation_v6_started.json').exists():assert read(OUT/'evaluation_v6_started.json')['identity']==key
    else:save('evaluation_v6_started',dict(identity=key,expected_count=len(items),started_at=now(),single_shot=True,unknown_recognition_calls_allowed=0))
    checkpoint('Round22 V6 single-shot active','Every representation/hash/identity and immutable freeze verified. No unknown4 replay. No tuning or generator changes permitted.', 'Follow reports/round22-v6.log;resume pending IDs only with same freeze/manifest/code. Never replay completed result.',[dict(command='python -m benchmarks.round22_release evaluate',log='reports/round22-v6.log',state='running; transactional journal')])
    with ProcessPoolExecutor(max_workers=3,initializer=init,initargs=(runtime_hash(),)) as pool:
        jobs={pool.submit(worker,c):c['case']['id'] for c in items if c['case']['id'] in pending}
        for future in as_completed(jobs):
            row=future.result();assert row['id']==jobs[future];journal.append(row);done+=1
            if done%10==0:print('R22 V6 persisted',done,'/',len(items),flush=True)
    target=OUT/'evaluation_v6_observations.json';journal.export(target,complete=True);raw=read(target);rows=raw['cases']
    import jsonschema
    jsonschema.validate(raw,read('benchmarks/schemas/round21_observations.schema.json'))
    assert raw['expected_count']==len(rows)==len(items)==len({r['id'] for r in rows})
    assert {r['id']:r['input_sha256'] for r in rows}=={c['case']['id']:c['sha256'] for c in items}
    scan=[r for r in rows if r['scan_like']];filled=[r for r in rows if r['filled']];unknown=read('benchmarks/results/round21/unknown_release_v4_observations.json')['cases'];u=read('benchmarks/results/round21/unknown_release_v4.json')
    from benchmarks.round17_unknown import metrics as unknown_metrics
    assert all(u[k]==v for k,v in unknown_metrics(unknown).items())
    for n,cs in [('robustness_v6',rows),('scan_v6',scan),('filled_v6',filled),('end_to_end_v6',rows+unknown)]:save(n,dict(status='complete',summary=summary(cs),cases=cs,identity=key,observations_sha256=sha(target),scope='Fresh V6 known single-shot; unknown mix reuses all120 original compatible unknown4 rows with0 new calls.'))
    retrieval={str(k):sum(r['candidate_recall_at_k'][str(k)] for r in rows)/len(rows) for k in [1,5,10,25]};save('retrieval_v6',dict(status='complete',n=len(rows),recall_at_k=retrieval,observations_sha256=sha(target)))
    overall,s,fill=map(rates,[rows,scan,filled]);gen=read(OUT/'filled_generation_v2.json');gates={}
    for name,a,p,b in [('v6_precision',overall['precision'],overall['precision']>=.995,True),('v6_exact_recall',overall['recall'],overall['recall']>=.9,True),('v6_entity_version',dict(entity=overall['entity_errors'],version=overall['version_errors']),overall['entity_errors']==overall['version_errors']==0,True),('v6_scan_precision',s['precision'],s['precision']>=.995,True),('v6_scan_recall',s['recall'],s['recall']>=.85,True),('v6_filled_generation',gen['generation_success_rate'],gen['passed'],True),('v6_filled_precision',fill['precision'],fill['precision']>=.995,True),('v6_filled_recall',fill['recall'],fill['recall']>=.9,True),('v6_retrieval_at25',retrieval['25'],retrieval['25']==1,True),('v6_retrieval_at1_target',retrieval['1'],retrieval['1']>=.99,False),('unknown_end_to_end',u['rejection_rate'],u['rejection_rate']>=.99 and u['wrong_family_match']==u['wrong_document_match']==0,True)]:gates[name]=dict(actual=a,passed=bool(p),blocking=b)
    result=dict(passed=all(g['passed'] for g in gates.values() if g['blocking']),gates=gates,metrics=overall,scan=s,filled=fill,filled_generation=dict(attempted=100,valid=gen['generation_valid'],rate=gen['generation_success_rate'],valid_and_correct=fill['exact'],end_to_end_rate=fill['exact']/100),retrieval=retrieval,unknown_mix=dict(n=len(unknown),correct_rejects=u['correct_no_match'],false_accepts=u['wrong_document_match']+u['wrong_family_match'],new_recognition_calls=0,original_observations_sha256=u['observations_sha256']),identity=key,expected_count=len(rows),actual_count=len(rows),unique_case_ids=len(rows),observations_sha256=sha(target),single_shot=True,known_recognition_calls=len(rows),unknown_recognition_calls=0,freeze_manifest_sha256=sha(OUT/'evaluation_freeze_manifest.json'))
    save('evaluation_v6_gate',result);sealed();checkpoint('Round22 V6 single-shot complete; semantic work closed','V6 result persisted and raw SHA verified. Overall'+str(overall)+'; no post-result changes authorized.', 'Run prescribed post-V6 canonical/safety/full tests,then7 isolated warm timing runs. Report actual gates without tuning.')
    print('R22 V6 complete',result,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['freeze','evaluate']);a=p.parse_args();{'freeze':seal,'evaluate':evaluate}[a.mode]()
