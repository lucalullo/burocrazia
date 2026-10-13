"""Archive tracked HEAD and verify release hygiene and frozen bytes."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

def verify_round12(archive, names, gates):
    """Verify the stopped R12 path and all five measured performance runs."""
    from collections import Counter
    import csv
    import math
    import statistics
    from benchmarks.unknown_release import validate as validate_unknown, select
    from benchmarks.round9_performance import describe
    from src.fingerprint_v3 import validate as validate_v3
    def read12(name):
        return json.loads(archive.read('BurOCRazia/benchmarks/results/round12/' + name + '.json'))
    prefix = 'BurOCRazia/'
    fp_bytes = archive.read(prefix + 'data/document_recognition_fingerprints_v3.json')
    fp = validate_v3(json.loads(fp_bytes))
    assert fp_bytes == subprocess.check_output(['git', 'show', 'd911fcc:data/document_recognition_fingerprints_v3.json'], cwd=ROOT)
    assert hashlib.sha256(fp_bytes).hexdigest() == gates['identity']['fingerprint_sha256']
    master = validate_unknown(json.loads(archive.read(prefix + 'benchmarks/manifests/official_unknown_master_v1.json')))
    release_bytes = archive.read(prefix + 'benchmarks/manifests/official_unknown_release_v1.json')
    release = validate_unknown(json.loads(release_bytes))
    assert release_bytes == subprocess.check_output(['git', 'show', 'd911fcc:benchmarks/manifests/official_unknown_release_v1.json'], cwd=ROOT)
    assert [c['case_id'] for c in select(master['cases'])] == [c['case_id'] for c in release['cases']]
    locks = read12('evidence_locks')
    for path, digest in locks['sha256'].items():
        assert hashlib.sha256(archive.read(prefix + path)).hexdigest() == digest, path
    for path, digest in locks['historical_original_git_sha256'].items():
        assert hashlib.sha256(archive.read(prefix + path)).hexdigest() == digest, path
    target, coverage, prerequisite = read12('coverage_target'), read12('coverage_final'), read12('prerequisite_gate')
    fixed = {c['document_id'] for c in json.loads(archive.read(prefix + 'benchmarks/results/round6/resource_audit.json'))['cases'] if c['expected_resource_type'] == 'file_backed_document'}
    shared = {c['document_id'] for c in read12('shared_eligibility_audit')['cases'] if c['eligible']}
    active = {r['document_id'] for r in fp['records'] if r['status'] == 'active'}
    supported = (active | shared) & fixed
    assert target['minimum_required'] == math.ceil(.85 * len(fixed)) == 985
    assert target['current_fingerprinted'] == coverage['fingerprinted_file_backed'] == len(supported) == 975
    assert set(coverage['eligible_ids']) == supported and coverage['recovered_round12'] == 0
    assert not prerequisite['ready_to_freeze'] and not prerequisite['coverage_file_backed_pass']
    assert gates['status'] == 'NOT READY' and gates['freeze'] is None and not gates['local_gates_passed']
    unknown = read12('unknown_release_v1')
    assert unknown['manifest_sha256'] == hashlib.sha256(release_bytes).hexdigest()
    assert unknown['status'] == 'not_run' and unknown['actual_count'] == unknown['recognition_calls'] == 0 and not unknown['cases']
    for key in ['correct_no_match', 'wrong_document_match', 'wrong_family_match', 'rejection_rate', 'false_acceptance_rate', 'confidence_interval_95']:
        assert unknown[key] is None
    perf = read12('performance_stability')
    assert perf['status'] == 'complete' and len(perf['runs']) == 5
    ids = {c['id'] for c in perf['corpus']}
    assert len(ids) == 67
    for run in perf['runs']:
        assert run['sample_count'] == len(run['samples']) == 402
        assert Counter(s['case_id'] for s in run['samples']) == Counter({i: 6 for i in ids})
        assert describe([s['milliseconds'] for s in run['samples']]) == run['latency_ms']
    assert perf['median_p95'] == statistics.median(r['latency_ms']['p95'] for r in perf['runs']) == prerequisite['performance_median_p95']
    assert perf['identity']['code_sha256'] == gates['identity']['code_sha256']
    recovery = read12('recovery_attempts')
    assert not recovery['native_additions'] and recovery['temporary_converted_outputs_deleted']
    rows = list(csv.DictReader(archive.read(prefix + 'benchmarks/results/round12/fingerprint_recovery.csv').decode().splitlines()))
    assert len(rows) == len(fixed - supported) == 183 and {int(r['document_id']) for r in rows} == fixed - supported
    tests = read12('tests')
    assert tests['status'] == 'passed' and tests['failed'] == 0 and tests['passed'] == gates['tests']['passed']
    latest = json.loads(archive.read(prefix + 'benchmarks/latest_summary.json'))
    assert latest['round'] == 12 and latest['status'] == 'NOT READY'
    for name in ['known_robustness', 'scan_ocr', 'filled_forms', 'unknown_official']:
        assert latest[name]['status'] == 'not_run' and not latest[name]['summary']['metrics']
    for name in ['freeze', 'freeze_manifest', 'robustness_v5', 'scan_v5', 'filled_v5', 'unknown_eval_v5', 'retrieval_v5', 'end_to_end_v5', 'evaluation_v5_leakage']:
        assert prefix + 'benchmarks/results/round12/' + name + '.json' not in names
    for path in ['docs/ROUND12_BASELINE_AUDIT.md', 'docs/ROUND12_REPORT.md', 'benchmarks/results/round12/catalog_verification.json', 'benchmarks/results/round12/retained_safety_canonical.json']:
        assert archive.read(prefix + path), path
    return len(locks['historical_original_git_sha256'])

def verify_round13(archive,names,gates):
    from src.fingerprint_v3 import validate as validate_v3
    from benchmarks.unknown_release import validate as validate_unknown,select
    from benchmarks.round9_performance import describe
    import statistics
    prefix='BurOCRazia/'
    def r(name):return json.loads(archive.read(prefix+'benchmarks/results/round13/'+name+'.json'))
    raw=archive.read(prefix+'data/document_recognition_fingerprints_v3.json');fp=validate_v3(json.loads(raw))
    assert hashlib.sha256(raw).hexdigest()==gates['identity']['fingerprint_sha256']
    old=subprocess.check_output(['git','show','77bbe149:data/document_recognition_fingerprints_v3.json'],cwd=ROOT)
    assert fp['records'][:1028]==json.loads(old)['records']
    assert (json.dumps(dict(fp,records=fp['records'][:1028]),ensure_ascii=False,indent=2)+'\n').encode()==old
    restore=r('pre_adjudication_bundle_restore');prior=json.loads(json.dumps(fp))
    for change in restore['records']:
        for i,item in enumerate(prior['records']):
            if item['document_id']==change['document_id'] and item['ocr_metadata'].get('source_kind')=='maintenance_derived_legacy':prior['records'][i]=json.loads(change['record_json_before']);break
    assert hashlib.sha256((json.dumps(prior,ensure_ascii=False,indent=2)+'\n').encode()).hexdigest()==restore['bundle_sha256_before']
    unknown=r('unknown_release_v1');observed=r('unknown_release_observations')
    assert unknown['identity']['fingerprint_sha256']==restore['bundle_sha256_before']!=gates['identity']['fingerprint_sha256']
    assert observed['complete'] and observed['expected_count']==observed['completed']==len(observed['cases'])==105
    assert len({c['id'] for c in observed['cases']})==105
    assert hashlib.sha256(archive.read(prefix+'benchmarks/results/round13/unknown_release_observations.json')).hexdigest()==unknown['observations_sha256']
    master=validate_unknown(json.loads(archive.read(prefix+'benchmarks/manifests/official_unknown_master_v1.json')))
    release_bytes=archive.read(prefix+'benchmarks/manifests/official_unknown_release_v1.json');release=validate_unknown(json.loads(release_bytes))
    assert hashlib.sha256(release_bytes).hexdigest()==unknown['manifest_sha256']
    assert [c['case_id'] for c in select(master['cases'])]==[c['case_id'] for c in release['cases']]
    assert {c['case_id'] for c in release['cases']}=={c['id'] for c in observed['cases']}
    definition=archive.read(prefix+'benchmarks/reference/fingerprint_support_definition_v1.json')
    assert hashlib.sha256(definition).hexdigest()==r('support_definition_lock')['sha256']==r('coverage_final')['definition_sha256']
    cov=r('coverage_final');assert cov['native_fingerprint_supported']==975 and cov['legacy_eligible_count']==27 and cov['runtime_usable_fingerprint_supported']==1002
    assert r('prerequisite_gate')['ready_to_freeze'] is False and r('prerequisite_gate')['unknown_binding_current'] is False
    assert r('unknown_binding_invalidation')['release_replay'] is False
    assert not r('legacy_adjudication_observations')['wrong_document_accepts']
    assert gates['status']=='NOT READY' and gates['freeze'] is None and not gates['local_gates_passed']
    for item in fp['records'][1028:]:
        assert item['mime_type'] not in ['application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document']
        assert item['canonical_file_sha256']==item['ocr_metadata']['original_sha256']!=item['ocr_metadata']['derived_sha256']
        if item['document_id'] in [617,618,619]:assert item['status']=='shared' and item['shared_kind']=='ambiguous'
    perf=r('performance_confirmation');assert perf['status']=='complete' and len(perf['runs'])==5
    assert perf['identity']['fingerprint_sha256']==gates['identity']['fingerprint_sha256']
    for run in perf['runs']:assert len(run['samples'])==402 and describe([c['milliseconds'] for c in run['samples']])==run['latency_ms']
    assert statistics.median(run['latency_ms']['p95'] for run in perf['runs'])==perf['median_p95']
    locks=r('evidence_locks')
    for path,digest in locks['sha256'].items():assert hashlib.sha256(archive.read(prefix+path)).hexdigest()==digest,path
    for path,digest in locks['historical_original_git_sha256'].items():assert hashlib.sha256(archive.read(prefix+path)).hexdigest()==digest,path
    for name in ['freeze','freeze_manifest','evaluation_v5_preflight','evaluation_v5_leakage','robustness_v5','scan_v5','filled_v5','retrieval_v5','end_to_end_v5']:assert prefix+'benchmarks/results/round13/'+name+'.json' not in names
    for path in ['docs/ROUND13_BASELINE_AUDIT.md','docs/FINGERPRINT_COVERAGE_SEMANTICS.md','docs/ROUND13_REPORT.md','benchmarks/results/round13/legacy_fingerprint_audit.csv','benchmarks/results/round13/final_recovery.csv','benchmarks/results/round13/tests.json']:assert archive.read(prefix+path),path
    latest=json.loads(archive.read(prefix+'benchmarks/latest_summary.json'));assert latest['round']==13
    assert latest['unknown_official']['status']=='not_run' and not latest['unknown_official']['summary']['metrics']
    return len(locks['historical_original_git_sha256'])

def main():
    gates=json.loads((ROOT/'docs/release_gates.json').read_text(encoding='utf-8'))
    round_number=gates.get('round',5)
    name=f'BurOCRazia-v0.7.0-RC1-round{round_number}.zip' if gates.get('local_gates_passed') else f'BurOCRazia-v0.7.0-candidate-NOT-READY-round{round_number}.zip'
    output=ROOT/'dist'/name;output.parent.mkdir(exist_ok=True)
    subprocess.run(['git','archive','--format=zip','--prefix=BurOCRazia/','-o',str(output),'HEAD'],cwd=ROOT,check=True)
    forbidden={'.git','.venv','__pycache__','.pytest_cache','cache','staging','tmp-build','work','node_modules'}
    prior_raw_archive_count=0;prior_raw_workspace_only=[];prior_raw_serialization_differences=[]
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        names=archive.namelist();violations=[]
        for name in names:
            parts=Path(name).parts
            if forbidden.intersection(parts) or re.search(r'\.(?:pdf|docx|exe|traineddata|db|db-wal|db-shm|pyc)$',name,re.I):violations.append(name)
            if name.endswith(('.py','.md','.json','.toml','.yml','.txt','.ps1')):
                raw=archive.read(name)
                if re.search(rb'C:\\+(?:Users|users)\\',raw,re.I) or re.search(rb'\b'+b'Chi'+b'arIA'+rb'\b',raw,re.I):violations.append(name+': user path/old name')
                if re.search(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|sk-[A-Za-z0-9]{32,}',raw):violations.append(name+': secret pattern')
        assert not violations,violations
        manifest=json.loads(archive.read('BurOCRazia/data/catalog_manifest.json'))
        assert hashlib.sha256(archive.read('BurOCRazia/data/catalog_seed.sqlite3')).hexdigest()==manifest['sha256']
        for locks in ['corpus_locks_v1.json','corpus_locks_v2.json','file_corpus_locks_v1.json','file_corpus_locks_v2.json','family_release_locks_v1.json','family_release_locks_v2.json','family_release_locks_v3.json','development_compat_locks_v2.json']:
            values=json.loads(archive.read('BurOCRazia/benchmarks/manifests/'+locks))['sha256']
            for key,digest in values.items():
                path=key if '/' in key else 'benchmarks/corpora/'+key
                assert hashlib.sha256(archive.read('BurOCRazia/'+path)).hexdigest()==digest,path
        frozen=json.loads(archive.read('BurOCRazia/benchmarks/manifests/official_holdout_locks_v1.json'))
        for path,digest in frozen['sha256'].items():
            assert hashlib.sha256(archive.read('BurOCRazia/'+path)).hexdigest()==digest,path
        frozen2=json.loads(archive.read('BurOCRazia/benchmarks/manifests/official_holdout_locks_v2.json'))
        for path,digest in frozen2['sha256'].items():
            assert hashlib.sha256(archive.read('BurOCRazia/'+path)).hexdigest()==digest,path
        package=json.loads(archive.read('BurOCRazia/maintenance/releases/2026-10-11/manifest.json'))
        for item in package['files']:
            raw=archive.read('BurOCRazia/maintenance/releases/2026-10-11/'+item['path'])
            assert len(raw)==item['size_bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256']
        from benchmarks.evaluate import code_hash
        relevant=sorted([*ROOT.glob('src/**/*.py'),*ROOT.glob('maintenance/*.py'),*ROOT.glob('benchmarks/*.py'),*ROOT.glob('data/recognition_profiles/*.json'),*ROOT.glob('data/document_recognition_fingerprints*.json'),ROOT/'scripts/benchmark.py',ROOT/'app.py',ROOT/'run.py',ROOT/'data/recognition_features.json'])
        for file in relevant:assert archive.read('BurOCRazia/'+file.relative_to(ROOT).as_posix())==file.read_bytes(),file.relative_to(ROOT)
        assert gates['identity']['code_sha256']==code_hash()
        from benchmarks.round4_common import runtime_hash
        assert gates['identity']['runtime_sha256']==runtime_hash()
        from src.document_fingerprints import validate
        fp=archive.read('BurOCRazia/data/document_recognition_fingerprints.json')
        validate(json.loads(fp))
        if round_number<6:assert hashlib.sha256(fp).hexdigest()==gates['identity']['fingerprint_sha256']
        if round_number>=6:
            from src.fingerprint_v2 import validate as validate_v2
            fp2=archive.read('BurOCRazia/data/document_recognition_fingerprints_v2.json')
            validate_v2(json.loads(fp2))
            if round_number<8:assert hashlib.sha256(fp2).hexdigest()==gates['identity']['fingerprint_sha256']
        if round_number==8:
            from src.fingerprint_v3 import validate as validate_v3
            fp3=archive.read('BurOCRazia/data/document_recognition_fingerprints_v3.json');validate_v3(json.loads(fp3))
            assert hashlib.sha256(fp3).hexdigest()==gates['identity']['fingerprint_sha256']
            freeze=json.loads(archive.read('BurOCRazia/benchmarks/results/round8/freeze.json'))
            for key in ['runtime_sha256','code_sha256','fingerprint_sha256']:assert freeze[key]==gates['identity'][key]
            for path,key in [('benchmarks/results/round8/calibration_v4.json','calibration_sha256'),('benchmarks/reference/reference_truth_v1.json','truth_sha256'),('data/recognition_profiles/fingerprint_decision_v4.json','profile_sha256')]:assert hashlib.sha256(archive.read('BurOCRazia/'+path)).hexdigest()==freeze[key]
            locks=json.loads(archive.read('BurOCRazia/benchmarks/results/round8/evaluation_locks.json'))
            for path,digest in locks['sha256'].items():assert hashlib.sha256(archive.read('BurOCRazia/'+path)).hexdigest()==digest,path
            baseline=json.loads(archive.read('BurOCRazia/benchmarks/results/round8/baseline/metrics.json'))
            historical_audit=json.loads(archive.read('BurOCRazia/benchmarks/results/round8/historical_serialization_audit.json'))
            historical_rows={r['path']:r for r in historical_audit['cases']}
            assert historical_audit['baseline_commit']==baseline['commit']
            for path,digest in baseline['prior_raw_sha256'].items():
                workspace_raw=(ROOT/path).read_bytes();assert hashlib.sha256(workspace_raw).hexdigest()==digest,path
                member='BurOCRazia/'+path
                if member in names:
                    original=archive.read(member);archived_sha=hashlib.sha256(original).hexdigest()
                    assert archived_sha==historical_rows[path]['original_git_sha256'],path
                    if archived_sha!=digest:
                        assert historical_rows[path]['relationship']=='preexisting_workspace_CRLF_original_Git_LF',path
                        assert workspace_raw.replace(b'\r\n',b'\n')==original and json.loads(workspace_raw)==json.loads(original),path
                        prior_raw_serialization_differences.append(path)
                    prior_raw_archive_count+=1
                else:
                    assert path.startswith(('benchmarks/results/round6/','benchmarks/results/round7/')) and path.endswith('_checkpoint.json'),path
                    assert subprocess.run(['git','check-ignore','-q','--',path],cwd=ROOT).returncode==0,path
                    prior_raw_workspace_only.append(path)
            def evidence(name):return json.loads(archive.read('BurOCRazia/benchmarks/results/round8/'+name+'.json'))
            plan=evidence('robustness_v4_evaluation_plan');leak=evidence('evaluation_v4_leakage')
            assert not set(plan['calibration_identities'])&set(plan['evaluation_identities'])
            assert leak['prohibited_leakage']==0 and not any(leak[k] for k in ['identity_overlap','resource_sha_overlap','url_overlap','title_code_version_or_near_template_overlap'])
            prepared=evidence('evaluation_prepared');started=evidence('evaluation_started')
            assert started['freeze']==freeze
            assert prepared['plan_sha256']==hashlib.sha256(archive.read('BurOCRazia/benchmarks/results/round8/robustness_v4_evaluation_plan.json')).hexdigest()
            assert started['prepared_sha256']==hashlib.sha256(archive.read('BurOCRazia/benchmarks/results/round8/evaluation_prepared.json')).hexdigest()
            rob=evidence('robustness_v4')
            if not rob.get('completion',{}).get('complete',False):
                interruption=evidence('evaluation_interruption');checkpoint=evidence('evaluation_checkpoint')
                saved=archive.read('BurOCRazia/benchmarks/results/round8/evaluation_checkpoint.json')
                assert saved==archive.read('BurOCRazia/benchmarks/results/round8/evaluation_checkpoint_preserved.json')
                assert hashlib.sha256(saved).hexdigest()==interruption['checkpoint_sha256']
                assert not interruption['rerun'] and interruption['recognition_calls_during_preservation']==0
                assert rob['cases']==sorted(checkpoint['cases'],key=lambda r:r['id'])
                assert len(rob['cases'])==checkpoint['completed']==interruption['persisted']
                assert len(prepared['representations'])==interruption['planned']
                assert interruption['unavailable']==interruption['planned']-interruption['persisted']
                assert evidence('scan_v4')['cases']==[r for r in rob['cases'] if r['scan_like']]
                assert evidence('filled_v4')['cases']==[r for r in rob['cases'] if r['filled']]
                assert evidence('retrieval_v4')['cases']==rob['cases']
                assert gates['status']=='NOT READY' and not gates['local_gates_passed']
                latest=json.loads(archive.read('BurOCRazia/benchmarks/latest_summary.json'))
                for key in ['known_robustness','scan_ocr','filled_forms']:
                    assert latest[key]['status']=='incomplete' and not latest[key]['summary']['metrics']
            for path in ['docs/ROUND8_BASELINE_AUDIT.md','docs/REFERENCE_TRUTH_AUDIT.md','docs/ROUND8_REPORT.md','docs/BENCHMARK.md','benchmarks/reference/reference_truth_v1.json','data/document_recognition_fingerprints_v3.schema.json','benchmarks/latest_summary.json']:
                assert archive.read('BurOCRazia/'+path),path
            for name in ['performance','performance_profile_components','unknown_v4','calibration_v4']:
                assert evidence(name)
            for name in ['filled_generation_audit','scan_failure_decomposition']:
                assert archive.read('BurOCRazia/benchmarks/results/round8/'+name+'.csv')
        if round_number==11:
            from src.fingerprint_v3 import validate as validate_v3
            from benchmarks.unknown_release import validate as validate_unknown11,select
            from benchmarks.truth_v2 import validate_registry
            validate_registry(json.loads(archive.read('BurOCRazia/benchmarks/reference/reference_truth_v2_round11_addendum.json')))
            fp11=json.loads(archive.read('BurOCRazia/data/document_recognition_fingerprints_v3.json'));validate_v3(fp11)
            assert hashlib.sha256(archive.read('BurOCRazia/data/document_recognition_fingerprints_v3.json')).hexdigest()==gates['identity']['fingerprint_sha256']
            original_fp=json.loads(subprocess.check_output(['git','show','d19547f:data/document_recognition_fingerprints_v3.json'],cwd=ROOT))
            assert fp11['records'][:len(original_fp['records'])]==original_fp['records']
            restored=dict(fp11,records=fp11['records'][:len(original_fp['records'])])
            assert hashlib.sha256((json.dumps(restored,ensure_ascii=False,indent=2)+'\n').encode()).hexdigest()=='378d3d3ff05a91a03328d708288c7a21095e60ecb6a7755665818c010da1bfe6'
            master11=validate_unknown11(json.loads(archive.read('BurOCRazia/benchmarks/manifests/official_unknown_master_v1.json')))
            release11=validate_unknown11(json.loads(archive.read('BurOCRazia/benchmarks/manifests/official_unknown_release_v1.json')))
            assert {c['case_id'] for c in select(master11['cases'])}=={c['case_id'] for c in release11['cases']}
            assert {c['case_id'] for c in json.loads(archive.read('BurOCRazia/benchmarks/manifests/official_unknown_v2.json'))['cases']}<={c['case_id'] for c in master11['cases']}
            locks11=json.loads(archive.read('BurOCRazia/benchmarks/results/round11/evidence_locks.json'))
            for path,digest in locks11['sha256'].items():assert hashlib.sha256(archive.read('BurOCRazia/'+path)).hexdigest()==digest,path
            for path,digest in locks11['historical_original_git_sha256'].items():assert hashlib.sha256(archive.read('BurOCRazia/'+path)).hexdigest()==digest,path
            prior_raw_archive_count=len(locks11['historical_original_git_sha256'])
            pre11=json.loads(archive.read('BurOCRazia/benchmarks/results/round11/prerequisite_gate.json'))
            assert not pre11['ready_to_freeze'] and gates['status']=='NOT READY' and gates['freeze'] is None
            for name in ['freeze','robustness_v5','scan_v5','filled_v5','unknown_eval_v5','retrieval_v5','evaluation_v5_leakage']:assert 'BurOCRazia/benchmarks/results/round11/'+name+'.json' not in names
            dev11=json.loads(archive.read('BurOCRazia/benchmarks/results/round11/unknown_development.json'))
            assert {r['id'] for r in dev11['cases']}=={c['case_id'] for c in master11['cases'] if c['split']=='unknown_dev'}
            assert dev11['actual_count']==dev11['expected_count']==dev11['unique_case_ids'] and dev11['release_recognition_calls']==0
            assert hashlib.sha256(archive.read('BurOCRazia/benchmarks/results/round11/unknown_development_observations.json')).hexdigest()==dev11['observations_sha256']
            latest11=json.loads(archive.read('BurOCRazia/benchmarks/latest_summary.json'))
            for name in ['known_robustness','scan_ocr','filled_forms','unknown_official']:assert latest11[name]['status']=='not_run' and not latest11[name]['summary']['metrics']
            for path in ['docs/ROUND11_BASELINE_AUDIT.md','docs/ROUND11_REPORT.md','benchmarks/results/round11/coverage_target.json','benchmarks/results/round11/coverage_final.json','benchmarks/results/round11/fingerprint_recovery_plan.csv','benchmarks/results/round11/unknown_balance_target.json','benchmarks/results/round11/unknown_truth_audit.csv','benchmarks/results/round11/unknown_balance_final.json','benchmarks/results/round11/tests.json']:assert archive.read('BurOCRazia/'+path),path
        if round_number==12:
            prior_raw_archive_count=verify_round12(archive,names,gates)
        if round_number==13:
            prior_raw_archive_count=verify_round13(archive,names,gates)
        if round_number==10:
            from src.fingerprint_v3 import validate as validate_v3
            from benchmarks.unknown_v2 import validate as validate_unknown_v2
            from benchmarks.truth_v2 import validate_registry
            fp10=archive.read('BurOCRazia/data/document_recognition_fingerprints_v3.json');validate_v3(json.loads(fp10))
            assert hashlib.sha256(fp10).hexdigest()==gates['identity']['fingerprint_sha256']
            validate_registry(json.loads(archive.read('BurOCRazia/benchmarks/reference/reference_truth_v2.json')))
            validate_registry(json.loads(archive.read('BurOCRazia/benchmarks/reference/reference_truth_v2_round10_addendum.json')))
            manifest10=validate_unknown_v2(json.loads(archive.read('BurOCRazia/benchmarks/manifests/official_unknown_v2.json')))
            locks10=json.loads(archive.read('BurOCRazia/benchmarks/results/round10/evidence_locks.json'))
            for path,digest in locks10['sha256'].items():assert hashlib.sha256(archive.read('BurOCRazia/'+path)).hexdigest()==digest,path
            for path,digest in locks10['historical_original_git_sha256'].items():assert hashlib.sha256(archive.read('BurOCRazia/'+path)).hexdigest()==digest,path
            prior_raw_archive_count=len(locks10['historical_original_git_sha256'])
            prereq=json.loads(archive.read('BurOCRazia/benchmarks/results/round10/prerequisite_gate.json'))
            assert not prereq['ready_to_freeze'] and gates['status']=='NOT READY' and gates['freeze'] is None and not gates['local_gates_passed']
            for name in ['freeze','robustness_v5','scan_v5','filled_v5','unknown_eval_v5','retrieval_v5','evaluation_v5_leakage']:assert 'BurOCRazia/benchmarks/results/round10/'+name+'.json' not in names
            unknown10=json.loads(archive.read('BurOCRazia/benchmarks/results/round10/unknown_development.json'))
            expected={c['case_id'] for c in manifest10['cases'] if c['split']=='unknown_dev'}
            assert expected=={c['id'] for c in unknown10['cases']}
            assert unknown10['expected_count']==unknown10['actual_count']==unknown10['unique_case_ids']==len(expected)
            assert unknown10['evaluation_recognition_calls']==0
            observed10=archive.read('BurOCRazia/benchmarks/results/round10/unknown_development_observations.json')
            assert hashlib.sha256(observed10).hexdigest()==unknown10['observations_sha256']
            latest10=json.loads(archive.read('BurOCRazia/benchmarks/latest_summary.json'))
            for name in ['known_robustness','scan_ocr','filled_forms']:assert latest10[name]['status']=='not_run' and not latest10[name]['summary']['metrics']
            assert archive.read('BurOCRazia/benchmarks/round8_fill.py')==subprocess.check_output(['git','show','8c13da2:benchmarks/round8_fill.py'],cwd=ROOT)
            checkpoint10=archive.read('BurOCRazia/benchmarks/results/round8/evaluation_checkpoint.json')
            assert checkpoint10==archive.read('BurOCRazia/benchmarks/results/round8/evaluation_checkpoint_preserved.json')
            assert hashlib.sha256(checkpoint10).hexdigest()=='0ab7fa7827bd6c1674a518bd127131866b62a8b48195273ecbc6cbed2c2585d2'
            for path in ['docs/ROUND10_BASELINE_AUDIT.md','docs/ROUND10_REPORT.md','docs/FINGERPRINT_COVERAGE_AUDIT.md','docs/REFERENCE_TRUTH_V2.md','benchmarks/results/round10/coverage_target.json','benchmarks/results/round10/fingerprint_recovery_plan.csv','benchmarks/results/round10/unknown_balance.json','benchmarks/results/round10/tests.json','benchmarks/results/round10/verification.json']:assert archive.read('BurOCRazia/'+path),path
        if round_number==9:
            from src.fingerprint_v3 import validate as validate_v3
            from benchmarks.truth_v2 import validate_registry,validate_unknown
            validate_v3(json.loads(archive.read('BurOCRazia/data/document_recognition_fingerprints_v3.json')))
            assert hashlib.sha256(archive.read('BurOCRazia/data/document_recognition_fingerprints_v3.json')).hexdigest()==gates['identity']['fingerprint_sha256']
            validate_registry(json.loads(archive.read('BurOCRazia/benchmarks/reference/reference_truth_v2.json')))
            manifest9=validate_unknown(json.loads(archive.read('BurOCRazia/benchmarks/manifests/official_unknown_v1.json')))
            assert gates['status']=='NOT READY' and gates['freeze'] is None and not gates['local_gates_passed']
            assert 'BurOCRazia/benchmarks/results/round9/freeze.json' not in names
            locks9=json.loads(archive.read('BurOCRazia/benchmarks/results/round9/evidence_locks.json'))
            for path,digest in locks9['sha256'].items():assert hashlib.sha256(archive.read('BurOCRazia/'+path)).hexdigest()==digest,path
            for path,digest in locks9['historical_original_git_sha256'].items():assert hashlib.sha256(archive.read('BurOCRazia/'+path)).hexdigest()==digest,path
            prior_raw_archive_count=len(locks9['historical_original_git_sha256'])
            for name in ['robustness_v5','scan_v5','filled_v5','retrieval_v5','evaluation_v5_leakage']:
                r=json.loads(archive.read('BurOCRazia/benchmarks/results/round9/'+name+'.json'))
                assert r['status']=='not_run' and r['cases']==[] and r['summary']['metrics']=={} and r['recognition_calls']==0
            unknown9=json.loads(archive.read('BurOCRazia/benchmarks/results/round9/unknown_v1.json'))
            assert {c['case_id'] for c in manifest9['cases']}=={c['id'] for c in unknown9['cases']}
            latest9=json.loads(archive.read('BurOCRazia/benchmarks/latest_summary.json'))
            for name in ['known_robustness','scan_ocr','filled_forms']:assert latest9[name]['status']=='not_run' and not latest9[name]['summary']['metrics']
            assert archive.read('BurOCRazia/benchmarks/round8_fill.py')==subprocess.check_output(['git','show','fa2a307:benchmarks/round8_fill.py'],cwd=ROOT)
            checkpoint9=archive.read('BurOCRazia/benchmarks/results/round8/evaluation_checkpoint.json')
            assert checkpoint9==archive.read('BurOCRazia/benchmarks/results/round8/evaluation_checkpoint_preserved.json')
            assert hashlib.sha256(checkpoint9).hexdigest()=='0ab7fa7827bd6c1674a518bd127131866b62a8b48195273ecbc6cbed2c2585d2'
            for path in ['docs/ROUND9_BASELINE_AUDIT.md','docs/REFERENCE_TRUTH_V2.md','docs/ROUND9_REPORT.md','docs/BENCHMARK.md','benchmarks/results/round9/unknown_truth_audit.csv','benchmarks/results/round9/fingerprint_recovery_v2.csv','benchmarks/results/round9/historical_false_acceptance_audit.md','benchmarks/results/round9/performance_profile_v2.json','benchmarks/results/round9/calibration_v5.json','benchmarks/results/round9/tests.json']:assert archive.read('BurOCRazia/'+path),path
        if round_number==7:
            freeze=json.loads(archive.read('BurOCRazia/benchmarks/results/round7/freeze.json'))
            for key in ['runtime_sha256','code_sha256','fingerprint_sha256']:assert freeze[key]==gates['identity'][key]
            assert hashlib.sha256(archive.read('BurOCRazia/benchmarks/results/round7/decision_calibration.json')).hexdigest()==freeze['calibration_sha256']
            if freeze.get('calibration_reference_fix_sha256'):assert hashlib.sha256(archive.read('BurOCRazia/benchmarks/results/round7/decision_calibration_reference_fix.json')).hexdigest()==freeze['calibration_reference_fix_sha256']
            assert hashlib.sha256(archive.read('BurOCRazia/data/recognition_profiles/fingerprint_decision_v3.json')).hexdigest()==freeze['profile_sha256']
            leakage=json.loads(archive.read('BurOCRazia/benchmarks/results/round7/evaluation_v3_leakage.json'))
            assert leakage['prohibited_leakage']==0 and not any(leakage[k] for k in ['identity_overlap','resource_sha_overlap','canonical_url_overlap','title_code_version_overlap'])
            plan=json.loads(archive.read('BurOCRazia/benchmarks/results/round7/robustness_v3_evaluation_plan.json'))
            assert not set(plan['calibration_identities'])&set(plan['evaluation_identities'])
            locks=json.loads(archive.read('BurOCRazia/benchmarks/results/round7/evaluation_locks.json'))
            for path,digest in locks['sha256'].items():
                assert hashlib.sha256(archive.read('BurOCRazia/'+path)).hexdigest()==digest,path
        if round_number==6:
            calibration=json.loads(archive.read('BurOCRazia/benchmarks/results/round6/fingerprint_calibration.json'))
            assert hashlib.sha256(archive.read('BurOCRazia/data/recognition_profiles/fingerprint_v2.json')).hexdigest()==calibration['profile_sha256']
            assert not set(calibration['calibration_identities'])&set(calibration['evaluation_identities'])
            locks=json.loads(archive.read('BurOCRazia/benchmarks/results/round6/evaluation_locks.json'))
            for path,digest in locks['sha256'].items():
                assert hashlib.sha256(archive.read('BurOCRazia/'+path)).hexdigest()==digest,path
            assert locks['runtime_sha256']==gates['identity']['runtime_sha256']
        assert archive.read('BurOCRazia/docs/release_gates.json')==(ROOT/'docs/release_gates.json').read_bytes()
    historical_scope='Original R6/R7/R8/R9 Git blobs unchanged from the Round10 baseline, plus immutable v1 unknown/v2 truth/fingerprint/decision data. All R6/R7 physical baseline hashes separately verified. No old evaluation result rewritten.' if round_number==10 else 'Original R6/R7/R8 tracked Git blobs unchanged from the Round9 baseline; evidence_locks.json lists their byte hashes. All 110 R6/R7 physical workspace hashes separately verified. Historical ignored checkpoints intentionally excluded. Locked corpus byte hashes verified without normalization.' if round_number==9 else '105 tracked historical Git blobs unchanged from the initial Round7 commit, including 18 preexisting LF Git/CRLF workspace differences with identical JSON. All 110 workspace raw hashes unchanged; five historically ignored development checkpoints intentionally excluded from Git archive. Locked corpus byte hashes verified separately without normalization.'
    if round_number==11:historical_scope='Original R6-R10 Git evidence blobs unchanged. All1027 prior fingerprint records preserved and original R10 bundle byte SHA reconstructible from that prefix with UTF8/indent2/trailing LF. Corpus locks, seed and prior archives separately verified.'
    if round_number==12:historical_scope='Original R6-R11 Git evidence unchanged. Full R11 fingerprint bundle, seed and release unknown manifest byte-identical; prior archives preserved. All five warm runs/2010 timings verified. Coverage stop enforced: zero unknown release predictions, no freeze or evaluation v5.'
    if round_number==13:historical_scope='Original R6-R12 evidence preserved; 1028 prior fingerprint records byte-restorable. Initial R13 single-shot bundle exactly restorable using the three adjudicated record snapshots. 105 unknown predictions preserved without replay; current candidate binding marked unmeasured. Corrected common-page ambiguity, five performance runs and current source bytes verified. No freeze or v5.'
    report=dict(schema_version=1,commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True,cwd=ROOT).strip(),archive=output.name,bytes=output.stat().st_size,members=len(names),sha256=hashlib.sha256(output.read_bytes()).hexdigest(),catalog_sha256=manifest['sha256'],frozen_locks_verified=True,code_bytes_match_measurements=True,hygiene_violations=[],prior_round_raw_in_archive=prior_raw_archive_count,prior_round_raw_workspace_only=sorted(prior_raw_workspace_only),prior_round_raw_serialization_differences=sorted(prior_raw_serialization_differences),prior_round_raw_scope=historical_scope)
    (output.parent/'package-verification.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
    if round_number==10:(output.parent/'package-verification-round10.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
    if round_number==11:(output.parent/'package-verification-round11.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
    if round_number==12:(output.parent/'package-verification-round12.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
    if round_number==13:(output.parent/'package-verification-round13.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
    output.with_suffix('.zip.sha256').write_bytes((report['sha256']+'  '+output.name+'\n').encode())
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
