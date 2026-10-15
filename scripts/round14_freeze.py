"""Record a dedicated freeze commit, without a self-referential manifest hash."""
import subprocess
from scripts.round14_common import *
from benchmarks.round3_audit import catalog
from src.recognize import catalog_revision
from benchmarks.round4_common import runtime_hash

def main():
    assert_baseline_engine();gate=read('benchmarks/results/round14/pre_freeze_gate.json')
    assert gate['passed'],'Failed prerequisite: no freeze allowed'
    assert not (OUT/'freeze_manifest.json').exists(),'Already frozen'
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip(),'Commit registry and prerequisite evidence first'
    subprocess.run(['git','commit','--allow-empty','-m','Freeze corrected Round 14 candidate before fresh release selection'],cwd=ROOT,check=True)
    commit=head();docs,families=catalog()
    value=dict(schema_version=1,freeze_git_commit=commit,software_version='0.6.1',candidate_target='0.7.0',schema=610,timestamp=now(),
               catalog_semantic_sha256=catalog_revision(docs,families),catalog_file_sha256=sha('data/catalog_seed.sqlite3'),
               fingerprint_dataset_sha256=sha('data/document_recognition_fingerprints_v3.json'),fingerprint_support_definition_sha256=sha('benchmarks/reference/fingerprint_support_definition_v1.json'),
               decision_policy_sha256=sha('data/recognition_profiles/fingerprint_decision_v5.json'),
               source_profiles_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in sorted((ROOT/'data/recognition_profiles').glob('*.json'))},
               reference_truth_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in sorted((ROOT/'benchmarks/reference').glob('reference_truth*.json'))},
               contamination_registry_sha256=sha(REGISTRY),canonical_result_sha256=sha('benchmarks/results/round14/canonical.json'),
               canonical_legacy_result_sha256=sha('benchmarks/results/round14/canonical_legacy.json'),historical_safety_result_sha256=sha('benchmarks/results/round14/historical_safety.json'),
               performance_result_sha256=sha('benchmarks/results/round14/performance_pre_freeze.json'),test_result_sha256=sha('benchmarks/results/round14/baseline_tests.json'),
               pre_freeze_gate_sha256=sha('benchmarks/results/round14/pre_freeze_gate.json'),runtime_sha256=runtime_hash(),engine_files_sha256=engine_files(),
               preexisting_serialization_differences=read('benchmarks/results/round14/baseline_audit.json')['preexisting_serialization_differences'],
               scope='Dedicated empty Git commit seals the complete parent tree and engine. Manifest recorded immediately after commit, before fresh corpus selection/acquisition; cannot contain its own commit hash. Later infrastructure/evidence commits may descend without changing sealed engine bytes.')
    save('freeze_manifest',value);sealed();print('R14 freeze',commit,flush=True)

if __name__=='__main__':main()
