"""Dedicated freeze after all current prerequisites, before release selection."""
from scripts.round17_common import *
from benchmarks.round3_audit import catalog
from benchmarks.round4_common import runtime_hash
from src.recognize import catalog_revision
from benchmarks.evaluate import code_hash

def main():
    gate=read(OUT/'pre_freeze_gate.json');assert gate['ready_to_freeze']
    assert gate['identity']['runtime_sha256']==runtime_hash()
    assert not (OUT/'freeze_manifest.json').exists()
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip(),'Commit all prerequisite evidence before freeze'
    subprocess.run(['git','commit','--allow-empty','-m','Freeze Round17 immutable-engine candidate before fresh release selection'],cwd=ROOT,check=True)
    docs,families=catalog()
    save('freeze_manifest',dict(schema_version=1,freeze_git_commit=head(),timestamp=now(),software_version='0.6.1',candidate_target='0.7.0',schema=610,recognition_semantic_sha256=runtime_hash(),runtime_sha256=runtime_hash(),benchmark_runner_code_sha256=code_hash(),infrastructure_sha256=infrastructure_sha256(),fingerprint_dataset_sha256=sha('data/document_recognition_fingerprints_v3.json'),catalog_file_sha256=sha('data/catalog_seed.sqlite3'),catalog_semantic_sha256=catalog_revision(docs,families),decision_policy_sha256=sha('data/recognition_profiles/fingerprint_decision_v5.json'),release_truth_policy_sha256=sha(POLICY),base_truth_v3_sha256=sha(TRUTH),truth_addendum_sha256=sha(ADDENDUM),contamination_registry_sha256=sha(REGISTRY),engine_files_sha256=engine_files(),prerequisite_evidence_sha256={n:sha(OUT/(n+'.json')) for n in ['coverage','canonical','canonical_legacy','historical_safety','input_safety','performance_stability','semantic_equivalence','tests','release_gate_fast','historical_regression_fast','pre_freeze_gate','unknown_v3_preflight','unknown_v3_truth_audit']},scope='Dedicated empty commit binds complete prerequisite parent tree; manifest written immediately afterward before any fresh corpus selection. No semantics, thresholds, policy, catalog or dataset changes authorized after this barrier.'))
    sealed();print('R17 freeze',head(),flush=True)

if __name__=='__main__':main()
