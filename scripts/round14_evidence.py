"""Verify immutable release inputs/results, historical bytes and final artifacts."""
import subprocess,re
from scripts.round14_common import *
from benchmarks.round14_unknown import validate_release,validate_observations,metrics
from benchmarks.evaluate import code_hash
from src.benchmark_display import load_summary

def main():
    f=sealed();m=validate_release(read('benchmarks/manifests/official_unknown_release_v2.json'));u=read('benchmarks/results/round14/unknown_release_v2.json')
    obs=validate_observations(read('benchmarks/results/round14/unknown_release_v2_observations.json'));rows=obs['cases']
    assert u['manifest_sha256']==sha('benchmarks/manifests/official_unknown_release_v2.json')==read('benchmarks/results/round14/unknown_v2_selection.json')['manifest_sha256']
    assert {c['case_id']:c['SHA256'] for c in m['cases']}=={r['id']:r['input_sha256'] for r in rows}
    assert u['observations_sha256']==sha('benchmarks/results/round14/unknown_release_v2_observations.json')
    assert u['recognition_calls']==u['expected_count']==u['actual_count']==u['unique_case_ids']==114
    assert all(u[k]==v for k,v in metrics(rows).items()) and not u['passed']
    assert u['identity']['code_sha256']==code_hash(),'Benchmark runner changed after single-shot'
    assert u['identity']['runtime_sha256']==f['runtime_sha256'] and u['identity']['fingerprint_sha256']==f['fingerprint_dataset_sha256']
    for c in m['cases']:
        assert sha('benchmarks/cache/'+c['SHA256']+'.body')==c['SHA256']==c['receipt']['sha256']
        if c['audit_evidence'].get('source_evidence',{}).get('listing_sha256'):
            h=c['audit_evidence']['source_evidence']['listing_sha256'];assert sha('benchmarks/cache/'+h+'.body')==h
    registry=read(REGISTRY)
    for p,h in registry['input_sha256'].items():assert sha(p)==h,p
    assert sha(REGISTRY)==f['contamination_registry_sha256']
    archives={}
    for number in range(8,14):
        p=read(f'dist/package-verification-round{number}.json');assert sha('dist/'+p['archive'])==p['sha256'];archives[p['archive']]=p['sha256']
    original_paths=subprocess.check_output(['git','ls-tree','-r','--name-only',BASE,*[f'benchmarks/results/round{n}' for n in range(6,14)],'benchmarks/corpora','benchmarks/manifests','benchmarks/reference/reference_truth_v2.json','benchmarks/reference/reference_truth_v2_round10_addendum.json','benchmarks/reference/reference_truth_v2_round11_addendum.json','docs/ROUND13_REPORT.md'],cwd=ROOT,text=True).splitlines()
    historical={}
    for p in original_paths:
        raw=subprocess.check_output(['git','show',BASE+':'+p],cwd=ROOT);current=(ROOT/p).read_bytes()
        assert raw==current or raw==current.replace(b'\r\n',b'\n'),p
        historical[p]=hashlib.sha256(raw).hexdigest()
    for path,h in read('benchmarks/results/round8/baseline/metrics.json')['prior_raw_sha256'].items():assert sha(path)==h
    latest=load_summary(ROOT/'benchmarks/latest_summary.json')
    assert latest['round']==14 and latest['status']=='NOT READY'
    assert latest['unknown_official']['summary']['metrics']['unknown_correct_rejection_rate']['numerator']==107
    assert latest['unknown_official']['summary']['metrics']['unknown_correct_rejection_rate']['denominator']==114
    for name in ['known_robustness','scan_ocr','filled_forms']:assert latest[name]['status']=='not_run' and not latest[name]['summary']['metrics']
    forbidden=['evaluation_v5_pool_audit.csv','evaluation_v5_preflight.json','evaluation_v5_leakage.json','robustness_v5.json','scan_v5.json','filled_v5.json','retrieval_v5.json','end_to_end_v5.json']
    assert not any((OUT/p).exists() for p in forbidden)
    assert read('docs/release_gates.json')['status']=='NOT READY' and read('docs/release_gates.json')['freeze']==f['freeze_git_commit']
    for p in OUT.iterdir():
        if p.suffix in ['.json','.csv']:assert not re.search(rb'C:\\+(?:Users|users)\\',p.read_bytes()),p.name
    save('prepackage_audit',dict(status='verified',freeze_commit=f['freeze_git_commit'],runtime_and_dataset_identical=True,
        unknown_calls=114,unknown_replays=0,release_v1_replayed=False,release_v2_original_labels_preserved=True,
        official_release_body_hashes_verified=114,prior_archives_sha256=archives,historical_git_blobs_verified=len(historical),
        registry_inputs_verified=len(registry['input_sha256']),v5_recognition_calls=0,summary_end_to_end_rejection='107/114, extraction failures separate',audited_at=now()))
    paths=[p for p in OUT.iterdir() if p.suffix in ['.json','.csv'] and p.name!='evidence_locks.json']
    paths.extend(ROOT/p for p in [REGISTRY,'benchmarks/manifests/official_unknown_release_v2.json','benchmarks/schemas/round14_unknown_observations.schema.json',
          'docs/ROUND14_BASELINE_AUDIT.md','docs/ROUND14_REPORT.md','docs/BENCHMARK.md','docs/release_gates.json','benchmarks/latest_summary.json'])
    save('evidence_locks',dict(schema_version=1,status='NOT READY',freeze_commit=f['freeze_git_commit'],baseline_commit=BASE,
         sha256={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)},historical_original_git_sha256=historical,
         scope='Evidence preservation after failed fresh release, not a new freeze or successful RC. Frozen labels/114 predictions retained. No tuning/replay/v5.'))
    print('R14 evidence verified',len(paths),'current',len(historical),'historical',flush=True)

if __name__=='__main__':main()
