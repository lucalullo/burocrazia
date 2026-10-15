"""Materialize already measured gates, reserve identities, seal a Git tree."""
import argparse,copy,csv,os,sqlite3
from collections import Counter
from scripts.round21_common import *
from benchmarks.round4_common import runtime_hash
from benchmarks.evaluate import code_hash
from benchmarks.release_truth import load_release

REGISTRY='benchmarks/reference/benchmark_contamination_registry_v7.json'
RESERVED='benchmarks/manifests/v6_reserved_identity_pool.json'

def prerequisites():
    preserved();assert not (OUT/'freeze_manifest.json').exists()
    assert not (ROOT/REGISTRY).exists() and not (ROOT/RESERVED).exists()
    cal=read(OUT/'calibration_v7.json');rows=read(cal['observations_path'])['cases']
    assert cal['identity']['runtime_sha256']==runtime_hash()
    assert sha(cal['observations_path'])==cal['observations_sha256']
    canon=[r for r in rows if r['group']=='canonical']
    save('canonical',dict(n=len(canon),exact=sum(r['document_correct'] for r in canon),passed=len(canon)==1007 and all(r['document_correct'] for r in canon),cases=canon,runtime_sha256=runtime_hash(),observations_sha256=cal['observations_sha256'],scope='Product canonical verification completed before reservation. Reuses original measured rows; no new recognition calls.'))
    qualified={c['input_key'] for c in load_release()[2] if c['truth_domain']!='parser_limit_contract'}
    certain=[r for r in rows if r.get('expected') and (r['group']!='historical' or r['original_id'] in qualified)]
    neg=[r for r in certain if r['expected']['match_type']=='NO_MATCH' and not r['extraction_failed']]
    hard=[r for r in neg if 'hard_negative' in r['category'] or 'hard_negative' in r['id']]
    assert len(neg)==cal['confirmed_negative_count']==705 and len(hard)>0
    save('development_safety',dict(confirmed_negative_count=len(neg),false_accepts=cal['confirmed_false_accept_ids'],passed=not cal['confirmed_false_accept_ids'],cases=neg,unsupported_not_credited=sum(r['extraction_failed'] for r in rows),runtime_sha256=runtime_hash(),scope='Confirmed historical/synthetic/observed unknown development only. Ambiguous historical labels remain preserved separately; extraction refusal is not a correct unknown rejection.'))
    save('hard_negatives_development',dict(n=len(hard),correct_rejects=sum(r['observed']['match_type']=='NO_MATCH' for r in hard),false_accept_ids=[r['id'] for r in hard if r['observed']['match_type']!='NO_MATCH'],passed=all(r['observed']['match_type']=='NO_MATCH' for r in hard),cases=hard))
    tests=read(OUT/'final_tests.json');assert tests['failed']==0 and tests['runtime_sha256']==runtime_hash()
    assert '2 passed' in (ROOT/'reports/round21-release-targeted.log').read_text(encoding='utf8')
    save('pre_freeze_tests',dict(full_suite=tests,release_infrastructure=dict(passed=2,failed=0,log_sha256=sha('reports/round21-release-targeted.log')),passed=True,scope='876-test full runtime suite plus two new benchmark selection/worker/schema tests; final full suite repeated on the freeze.'))
    old='benchmarks/reference/benchmark_contamination_registry_v6.json';v=copy.deepcopy(read(old));prospects=read(OUT/'v6_pool_prospects.json')
    audit={int(r['document_id']):r for r in csv.DictReader((OUT/'v6_identity_eligibility.csv').open(encoding='utf8'))}
    pool=prospects['cases'];ids={c['document_id'] for c in pool};resolved=set(prospects['resolved_candidate_only_or_evaluation_ids'])
    used=set(v['round20']['calibration_identity_ids']);seen=set(v['observed_resource_sha256']);provenance=[]
    for p in sorted([*ROOT.glob('benchmarks/results/round20/development_observations_*.json'),*OUT.glob('development_observations_*.json')]):
        provenance.append(p.relative_to(ROOT).as_posix())
        for r in read(p)['cases']:
            if r.get('input_sha256'):seen.add(r['input_sha256'])
            if r['group']!='canonical' or not r['correct']:
                if (r.get('expected') or {}).get('document_id'):used.add(r['expected']['document_id'])
                if r['observed'].get('document_id'):used.add(r['observed']['document_id'])
    assert not ids&used
    for k in v['known_identities']:
        did=k['document_id'];k['prior_registry_v6_flags']={n:k.get(n) for n in ['identity_seen_in_tuning','tuning_history_unresolved','eligible_v6','v6_exclusion_reason']}
        if did in resolved:k.update(tuning_history_unresolved=False,round21_uncertainty_resolution='Candidate-only legacy diagnostic or historical qualification/evaluation exposure; no direct tuning evidence. See source audit/proof hashes.')
        if did in used:
            k.update(identity_seen_in_tuning=True,historical_result_used_for_tuning=True,round21_development_seen=True)
            k['tuning_provenance']=sorted(set(k['tuning_provenance']+provenance))
        else:k['round21_development_seen']=False
        k.update(tuning_seen=k['identity_seen_in_tuning'],reserved_for_v6=did in ids,eligible_v6=did in ids,canonical_qualification_guard=did in prospects['legacy_actual_inputs_excluded'])
        if did in audit:k['round21_exclusion_reason']=audit[did]['exclusion_reason']
        if did in ids:assert not k['tuning_seen'] and not k['tuning_history_unresolved'] and not k.get('V5_seen')
    unknown=read(OUT/'unknown_v4_truth_audit.json')['confirmed_cases'];unknownsha={c['SHA256'] for c in unknown};assert not unknownsha&seen
    v.update(schema_version=7,registry_id='benchmark-contamination-registry-v7-round21',created_at=now(),parent_registry_sha256=sha(old),observed_resource_sha256=sorted(seen),unknown_v4_reserved_resources=[dict(SHA256=c['SHA256'],case_id=c['case_id'],source=c['source'],tuning_seen=False,reserved=True) for c in unknown],round21=dict(development_identity_ids=sorted(used),development_provenance=provenance,reserved_identity_ids=sorted(ids),uncertainty_resolution_ids=sorted(resolved),source_audit_sha256=sha(OUT/'v6_identity_eligibility.csv'),unknown_truth_audit_sha256=sha(OUT/'unknown_v4_truth_audit.json'),scope='Canonical/product verification and candidate-only exposure alone are not tuning. Actual V5/development/tuning identities remain excluded. Original registries and flags retained.'))
    v['counts'].update(round21_tuning_identities=len(used),reserved_v6_identities=len(ids),reserved_unknown_v4_resources=len(unknownsha));atomic_json(ROOT/REGISTRY,v)
    final=[dict(c,reserved_for_v6=True,reservation_reason='Reserved after all development/canonical/safety/performance measurements. No identity tuning evidence; new representations required. No transformations/predictions until freeze.') for c in pool]
    atomic_json(ROOT/RESERVED,dict(schema_version=1,created_at=now(),registry_sha256=sha(REGISTRY),cases=final,counts_per_source=dict(Counter(c['source_id'] for c in final)),recognition_calls_after_reservation=0,transform_calls_before_freeze=0))
    p=read(OUT/'v6_preflight.json');p.update(reserved_manifest_created=True,reserved_manifest_sha256=sha(RESERVED));save('v6_preflight',p)
    perf=read(OUT/'performance_stability.json');assert perf['identity']['runtime_sha256']==runtime_hash()
    pre=dict(cal['gates'],hard_negatives_pass=read(OUT/'hard_negatives_development.json')['passed'],coverage_pass=read(OUT/'coverage.json')['file_backed_percent']>=85,input_safety_pass=read(OUT/'input_safety.json')['passed'],performance_pass=perf['required_pass'],tests_pass=True,V6_pool_pass=p['passed'],unknown_v4_preflight_pass=read(OUT/'unknown_v4_preflight.json')['passed'],final_checks_pass=read(OUT/'final_checks.json')['passed'])
    pre['ready_to_freeze']=all(pre.values());pre.update(created_at=now(),recognition_calls_on_reserved=0,runtime_sha256=runtime_hash(),full_code_sha256=code_hash())
    save('pre_freeze_gate',pre);assert pre['ready_to_freeze']
    checkpoint('Round21 all pre-freeze gates PASS; final reservation fixed','Development P100/R90.3937,scan88.2937,canonical1007/1007,705 confirmed negatives0FA,7-run p95176.6788ms; pool639/8; unknown213/15. No reserved recognition/transform calls.', 'Create separate temporary-index Git tree then run scripts.round21_prerequisites freeze TREE. Do not run development/canonical predictions between reservation and freeze.')
    print('R21 ready to freeze',len(final),'identities',len(unknown),'fresh unknown',flush=True)

def tree():
    preserved();assert head()==BASE
    index=ROOT/'.git/index';before=sha(index);temp=ROOT/'tmp-build'/('round21-index-'+datetime.now(UTC).strftime('%Y%m%dT%H%M%S%f'))
    assert not temp.exists();temp.parent.mkdir(exist_ok=True);env=dict(os.environ,GIT_INDEX_FILE=str(temp))
    subprocess.run(['git','read-tree','HEAD'],cwd=ROOT,env=env,check=True)
    subprocess.run(['git','add','--all','--','.'],cwd=ROOT,env=env,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    value=subprocess.check_output(['git','write-tree'],cwd=ROOT,env=env,text=True).strip();assert sha(index)==before
    atomic_json(ROOT/'.codex-context'/('TREE-'+value+'.json'),dict(tree=value,head=BASE,original_index_sha256=before,created_at=now(),temporary_index=temp.relative_to(ROOT).as_posix(),new_commit_created=False))
    print(value,flush=True)

def freeze(value):
    preserved();assert not (OUT/'freeze_manifest.json').exists();assert read(OUT/'pre_freeze_gate.json')['ready_to_freeze']
    assert head()==BASE;assert subprocess.check_output(['git','cat-file','-t',value],cwd=ROOT,text=True).strip()=='tree'
    paths=sorted(set([*ROOT.glob('src/**/*.py'),*ROOT.glob('maintenance/*.py'),*ROOT.glob('benchmarks/*.py'),*ROOT.glob('data/recognition_profiles/*.json'),*ROOT.glob('data/document_recognition_fingerprints*.json'),ROOT/'data/recognition_features.json',ROOT/'app.py',ROOT/'run.py',ROOT/'scripts/benchmark.py',ROOT/REGISTRY,ROOT/RESERVED,ROOT/'data/catalog_seed.sqlite3',ROOT/'data/catalog_manifest.json',ROOT/'docs/ROUND21_EVALUATION_PROTOCOL.md',ROOT/'benchmarks/schemas/round21_observations.schema.json',*OUT.glob('*.json'),*OUT.glob('*.csv')]))
    hashes={};serialization=[]
    for p in paths:
        name=p.relative_to(ROOT).as_posix();raw=p.read_bytes();git=subprocess.check_output(['git','show',value+':'+name],cwd=ROOT)
        assert raw==git or (name=='data/catalog_manifest.json' and raw.replace(b'\r\n',b'\n')==git),name
        if raw!=git:serialization.append(dict(path=name,workspace_sha256=hashlib.sha256(raw).hexdigest(),tree_sha256=hashlib.sha256(git).hexdigest(),reason='Preexisting CRLF/LF serialization only; semantic JSON equal.'))
        hashes[name]=hashlib.sha256(raw).hexdigest()
    with sqlite3.connect((ROOT/'data/catalog_seed.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
        dump='\n'.join(db.iterdump()).encode('utf8')
    f=dict(schema_version=1,created_at=now(),commit=BASE,commit_scope='Original base HEAD only. No new commit authorized or created. Immutable noncommitted Git tree is the semantic source snapshot.',semantic_source_tree=value,new_commit_created=False,recognition_semantic_hash=runtime_hash(),full_code_sha256=code_hash(),decision_v7_sha256=sha('data/recognition_profiles/fingerprint_decision_v7.json'),fingerprint_dataset_sha256=sha('data/document_recognition_fingerprints_v3.json'),catalog_semantic_sha256=hashlib.sha256(dump).hexdigest(),catalog_seed_sha256=sha('data/catalog_seed.sqlite3'),calibration_sha256=sha(OUT/'calibration_v7.json'),registry_v7_sha256=sha(REGISTRY),v6_reserved_pool_sha256=sha(RESERVED),unknown_v4_preflight_sha256=sha(OUT/'unknown_v4_preflight.json'),canonical_sha256=sha(OUT/'canonical.json'),safety_sha256=sha(OUT/'development_safety.json'),performance_sha256=sha(OUT/'performance_stability.json'),tests_sha256=sha(OUT/'pre_freeze_tests.json'),pre_freeze_gate_sha256=sha(OUT/'pre_freeze_gate.json'),frozen_files_sha256=hashes,serialization_differences=serialization,single_shot_policy='Unknown v4 first; only on PASS select/prepare/evaluate fresh V6. No semantic changes, tuning, replay or relabel after freeze.')
    save('freeze_manifest',f)
    checkpoint('Round21 freeze created; unknown4 next','All immutable prerequisites passed and full code/data/truth/registry/reservation bytes verified against noncommitted Git tree '+value,'python -m benchmarks.round21_release select-unknown; then unknown ONCE. On failure stop evaluation, preserve raw and finish NOT READY.')
    print('R21 frozen',value,runtime_hash(),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['prerequisites','tree','freeze']);p.add_argument('value',nargs='?');a=p.parse_args()
    {'prerequisites':prerequisites,'tree':tree,'freeze':lambda:freeze(a.value)}[a.mode]()
