"""Recompute frozen generator/V6 proofs and preserve the complete Round21 tree."""
import csv,hashlib,json,statistics,subprocess,zipfile
from collections import Counter
from scripts.round22_common import ROOT,BASE,ROUND21_TREE
from benchmarks.round22_release import rates
from benchmarks.round9_performance import describe
from benchmarks.round17_unknown import metrics as unknown_metrics

def verify(archive,names,gates):
    def raw(p):return archive.read('BurOCRazia/'+p)
    def digest(p):return hashlib.sha256(raw(p)).hexdigest()
    def data(p):return json.loads(raw(p))
    def r(n):return data('benchmarks/results/round22/'+n+'.json')
    b=r('baseline_audit');assert b['entry_head']==BASE and b['original_index_sha256']==hashlib.sha256((ROOT/'.git/index').read_bytes()).hexdigest()
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==BASE
    serialization=r('archive_serialization_audit');assert serialization['passed']
    allowed_serial={c['path']:c for c in serialization['differences']};serial=[]
    previous=ROOT/'dist/BurOCRazia-v0.7.0-candidate-NOT-READY-round21.zip'
    assert hashlib.sha256(previous.read_bytes()).hexdigest()==b['round21_archive_sha256']==serialization['prior_archive_sha256']
    old_archive=zipfile.ZipFile(previous)
    for p,h in b['protected_sha256'].items():
        actual=(ROOT/p).read_bytes();assert hashlib.sha256(actual).hexdigest()==h,p
        if digest(p)!=h:
            s=allowed_serial[p];git=subprocess.check_output(['git','show',ROUND21_TREE+':'+p],cwd=ROOT)
            assert s['workspace_sha256']==h and s['archive_sha256']==digest(p)==s['prior_Round21_archive_sha256']
            assert raw(p)==old_archive.read('BurOCRazia/'+p)
            assert raw(p).replace(b'\r\n',b'\n')==actual.replace(b'\r\n',b'\n')==git.replace(b'\r\n',b'\n')
            assert hashlib.sha256(git).hexdigest()==s['prior_Round21_Git_blob_sha256']
            serial.append(p)
    old_archive.close();assert set(serial)==set(allowed_serial)
    # Shared latest-summary/release/BENCHMARK pointers are allowed to advance;
    # their original Round21 versions and all evidence locks remain in its tree.
    old=data('benchmarks/results/round21/evidence_locks.json')
    for p,h in old['sha256'].items():
        if p in ['docs/BENCHMARK.md','docs/release_gates.json','benchmarks/latest_summary.json']:
            assert hashlib.sha256(subprocess.check_output(['git','show',ROUND21_TREE+':'+p],cwd=ROOT)).hexdigest()==h,p
        else:assert digest(p)==h,p
    for p,h in r('evidence_locks')['sha256'].items():assert digest(p)==h,p
    f=r('evaluation_freeze_manifest');assert f==gates['freeze'] and f['HEAD_commit']==BASE and not f['new_commit_created']
    for p,h in f['frozen_files_sha256'].items():assert digest(p)==h,p
    for p,h in f['recognition_files_sha256'].items():
        assert digest(p)==h or (p=='data/catalog_manifest.json' and p in serial),p
        assert h==data('benchmarks/results/round21/freeze_manifest.json')['frozen_files_sha256'][p]
    assert f['working_tree_recognition_hash']==gates['identity']['runtime_sha256']==r('recognition_freeze_check')['recognition_semantic_sha256']
    scope=r('generator_change_scope');assert not scope['recognition_semantics_changed'] and scope['recognition_files_before']==scope['recognition_files_after']==f['recognition_files_sha256']
    assert digest('benchmarks/reference/filled_generation_policy_v2.json')==f['filled_policy_sha256']==r('filled_policy_frozen')['policy_sha256']
    gen=r('filled_generation_v2');genraw=r('filled_generation_v2_observations');assert digest('benchmarks/results/round22/filled_generation_v2_observations.json')==gen['observations_sha256']
    assert gen['passed'] and gen['generation_attempted']==gen['generation_valid']==len(gen['cases'])==100 and gen['generation_success_rate']==1
    assert genraw['complete'] and genraw['expected_count']==genraw['completed']==100 and len({c['case_id'] for c in gen['cases']})==100
    assert gen['mode_counts']=={'acroform_native':40,'static_overlay':60} and not gen['failures']
    for c in gen['cases']:
        a=c['audit'];assert c['valid_generated'] and c['written_and_readback_verified'] and a['reopened'] and a['synthetic_values_verified'] and a['template_integrity_ok'] and a['safety_parser_pass'] and not a['external_references_introduced']
        assert all(p['outside_changed_pixel_fraction']<=.0001 for p in a['render_checks'])
        if c['mode']=='static_overlay':assert len(a['written_values'])==a['fields_verified']==7
        assert hashlib.sha256((ROOT/c['path']).read_bytes()).hexdigest()==c['generated_sha256']
    audit=list(csv.DictReader(raw('benchmarks/results/round22/filled_generation_failure_audit.csv').decode('utf8').splitlines()));assert len(audit)==25 and len({c['case_id'] for c in audit})==25
    assert all(c['root_cause']=='static_overlay_failure' for c in audit) and r('visual_review_result')['passed']
    pre=r('evaluation_v6_preflight');m=r('v6_representation_manifest');rows=m['representations'];leak=r('evaluation_v6_leakage')
    assert pre['passed'] and pre['identities']==40 and pre['sources']==8 and pre['known_representations']==m['expected_count']==len(rows)==597
    assert pre['scan_like']==m['scan_count']==sum(c['scan_like'] for c in rows)==420
    assert pre['valid_filled']==m['filled_valid']==sum(c['filled'] for c in rows)==100
    assert m['carried_nonfilled']==497 and pre['unknown_v4_available']==120
    assert leak['passed'] and leak['prohibited_leakage']==0 and not leak['seed_reuse_in_predictions']
    assert not any(leak[k] for k in ['identity_tuning_overlap','unreserved_overlap','V5_overlap','prior_observed_representation_overlap','unknown_overlap','duplicate_case_ids','duplicate_SHA','truth_ambiguity'])
    assert len({c['case']['id'] for c in rows})==len({c['sha256'] for c in rows})==597
    oldreps={c['case']['id']:c for c in data('benchmarks/results/round21/evaluation_v6_prepared.json')['representations'] if not c['filled']}
    for c in rows:
        assert hashlib.sha256((ROOT/c['path']).read_bytes()).hexdigest()==c['sha256']
        if not c['filled']:assert oldreps[c['case']['id']]==c
    v=r('evaluation_v6_gate');obs=r('evaluation_v6_observations');actual=obs['cases']
    assert obs['complete'] and obs['expected_count']==obs['completed']==v['expected_count']==v['actual_count']==v['unique_case_ids']==len(actual)==597
    assert digest('benchmarks/results/round22/evaluation_v6_observations.json')==v['observations_sha256']
    assert {c['id']:c['input_sha256'] for c in actual}=={c['case']['id']:c['sha256'] for c in rows}
    assert rates(actual)==v['metrics'] and rates([r for r in actual if r['scan_like']])==v['scan'] and rates([r for r in actual if r['filled']])==v['filled']
    assert v['metrics']['exact']==560 and v['metrics']['wrong']==0 and v['scan']['exact']==392 and v['filled']['exact']==95
    retrieval={str(k):sum(c['candidate_recall_at_k'][str(k)] for c in actual)/597 for k in [1,5,10,25]};assert retrieval==v['retrieval'] and retrieval['25']==1 and retrieval['1']>=.99
    assert v['passed'] and all(g['passed'] for g in v['gates'].values()) and v['known_recognition_calls']==597 and v['unknown_recognition_calls']==0
    unknown=data('benchmarks/results/round21/unknown_release_v4.json');uobs=data('benchmarks/results/round21/unknown_release_v4_observations.json')
    assert digest('benchmarks/manifests/official_unknown_release_v4.json')==f['unknown_v4_manifest_sha256']==unknown['manifest_sha256']
    assert digest('benchmarks/results/round21/unknown_release_v4_observations.json')==f['unknown_v4_raw_result_sha256']==unknown['observations_sha256']
    assert all(unknown[k]==x for k,x in unknown_metrics(uobs['cases']).items())
    assert unknown['correct_no_match']==unknown['n']==120 and unknown['identity']['runtime_sha256']==f['working_tree_recognition_hash']
    combined=r('end_to_end_v6')['cases'];assert len(combined)==717
    assert {c['id']:c for c in combined if c['unknown']}=={c['id']:c for c in uobs['cases']}
    assert {c['id']:c for c in combined if not c['unknown']}=={c['id']:c for c in actual}
    assert r('historical_independent_v6_round22')['original_observations_sha256']==v['observations_sha256']
    canonical=r('canonical_post_v6');safety=r('safety_post_v6');assert canonical['passed'] and canonical['n']==canonical['exact']==1007 and safety['passed'] and safety['n']==705 and not safety['false_accepts']
    assert safety['old_false_accept_cases']==8 and safety['hard_negatives']==safety['hard_correct_rejects']==260
    assert r('post_v6_checks')['passed'] and r('input_safety')['passed'] and r('coverage')['file_backed_percent']>=85 and r('final_checks')['passed']
    assert r('release_gate_fast')['passed'] and r('release_gate_fast')['n']==1258
    hist=r('historical_regression_fast');assert hist['n']==1517 and len(hist['mismatches'])==15 and hist['exit_code']==1 and not hist['expected_changed']
    perf=r('performance_stability');assert len(perf['runs'])==7
    for run in perf['runs']:
        assert len(run['samples'])==402 and len({c['case_id'] for c in run['samples']})==67
        assert describe([c['milliseconds'] for c in run['samples']])==run['latency_ms']
    assert perf['median_p95']==statistics.median(run['latency_ms']['p95'] for run in perf['runs'])
    assert perf['required_pass']==(perf['median_p95']<=250)
    assert perf['identity']['runtime_sha256']==f['working_tree_recognition_hash'] and perf['identity']['code_sha256']==f['full_code_sha256']
    tests=r('final_tests');assert tests==gates['tests'] and tests['passed']==889 and tests['failed']==0 and tests['skipped']==3
    ready=all(g['passed'] for g in gates['gates'] if g['blocking']);assert gates['local_gates_passed']==ready and gates['status']==('READY LOCALLY' if ready else 'NOT READY')
    assert set(gates['reasons'])=={g['gate'] for g in gates['gates'] if g['blocking'] and not g['passed']}
    latest=data('benchmarks/latest_summary.json');assert latest['round']==22 and latest['status']==gates['status'] and not latest['recognition_semantics_changed']
    assert all(latest[n]['status']=='executed' for n in ['known_robustness','scan_ocr','filled_forms','unknown_official'])
    if ready:
        for name in ['README_CANDIDATE_IT.md','README_CANDIDATE_EN.md','CHANGELOG_CANDIDATE.md']:assert raw(name)
        assert r('candidate_metadata')['candidate_version']=='0.7.0-rc1' and r('candidate_metadata')['public_stable_version']=='0.6.1'
    return len(b['protected_sha256'])
