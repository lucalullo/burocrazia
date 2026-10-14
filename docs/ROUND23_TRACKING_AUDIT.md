# Round 23 — audit dei file

Ogni file modificato/non tracciato è elencato sotto. Hash e dimensioni nel [registro JSON](../benchmarks/results/round23/tracking_inventory.json). I registri stessi sono artefatti derivati: lo staging finale è controllato nuovamente.

Le evidenze JSON grandi sono eccezioni motivate al criterio di sintesi: conservarle è necessario per verificare freeze, contamination registry, risultati grezzi e tentativi negativi senza rifare esperimenti. Nessun corpus PDF/DOCX/immagini, cache, ZIP, nuovo indice binario o database è aggiunto. Il catalogo seed e gli indici runtime già versionati restano identici. Venv, checkpoint privati, log, cache, work, temporanei e dist sono MUST NOT COMMIT e rimangono ignorati.

| File | Categoria | Byte | Motivazione |
| --- | --- | ---: | --- |
| `.github/workflows/tests.yml` | MUST COMMIT | 1483 | Runtime/policy/test/reproduction harness or release documentation |
| `.gitignore` | MUST COMMIT | 823 | Runtime/policy/test/reproduction harness or release documentation |
| `AGENTS.md` | MUST COMMIT | 3974 | Runtime/policy/test/reproduction harness or release documentation |
| `CHANGELOG.md` | MUST COMMIT | 8647 | Runtime/policy/test/reproduction harness or release documentation |
| `README.md` | MUST COMMIT | 14053 | Runtime/policy/test/reproduction harness or release documentation |
| `README_EN.md` | MUST COMMIT | 13988 | Runtime/policy/test/reproduction harness or release documentation |
| `benchmarks/latest_summary.json` | MUST COMMIT | 47626 | Runtime/policy/test/reproduction harness or release documentation |
| `docs/BENCHMARK.md` | MUST COMMIT | 25954 | Runtime/policy/test/reproduction harness or release documentation |
| `docs/release_gates.json` | MUST COMMIT | 40192 | Runtime/policy/test/reproduction harness or release documentation |
| `pyproject.toml` | MUST COMMIT | 295 | Runtime/policy/test/reproduction harness or release documentation |
| `scripts/package_candidate.py` | MUST COMMIT | 69955 | Runtime/policy/test/reproduction harness or release documentation |
| `src/recognize.py` | MUST COMMIT | 55895 | Runtime/policy/test/reproduction harness or release documentation |
| `tests/test_round16.py` | MUST COMMIT | 8158 | Runtime/policy/test/reproduction harness or release documentation |
| `tests/test_round17.py` | MUST COMMIT | 1856 | Runtime/policy/test/reproduction harness or release documentation |
| `tests/test_round18.py` | MUST COMMIT | 2134 | Runtime/policy/test/reproduction harness or release documentation |
| `tests/test_round19.py` | MUST COMMIT | 2106 | Runtime/policy/test/reproduction harness or release documentation |
| `tests/test_round8.py` | MUST COMMIT | 17401 | Runtime/policy/test/reproduction harness or release documentation |
| `CHANGELOG_CANDIDATE.md` | MUST COMMIT | 473 | Runtime/policy/test/reproduction harness or release documentation |
| `README_CANDIDATE_EN.md` | MUST COMMIT | 804 | Runtime/policy/test/reproduction harness or release documentation |
| `README_CANDIDATE_IT.md` | MUST COMMIT | 830 | Runtime/policy/test/reproduction harness or release documentation |
| `benchmarks/historical_seals.py` | MUST COMMIT | 700 | Runtime/policy/test/reproduction harness or release documentation |
| `benchmarks/manifests/official_unknown_release_v4.json` | MUST COMMIT | 369311 | Runtime/policy/test/reproduction harness or release documentation |
| `benchmarks/manifests/v6_reserved_identity_pool.json` | MUST COMMIT | 369312 | Runtime/policy/test/reproduction harness or release documentation |
| `benchmarks/reference/benchmark_contamination_registry_v5.json` | MUST COMMIT | 11268775 | large public evidence; locked |
| `benchmarks/reference/benchmark_contamination_registry_v6.json` | MUST COMMIT | 11337236 | large public evidence; locked |
| `benchmarks/reference/benchmark_contamination_registry_v7.json` | MUST COMMIT | 11997038 | large public evidence; locked |
| `benchmarks/reference/filled_generation_policy_v2.json` | MUST COMMIT | 3613 | Runtime/policy/test/reproduction harness or release documentation |
| `benchmarks/reference/v5_truth_adjudication_v1.json` | MUST COMMIT | 960416 | Runtime/policy/test/reproduction harness or release documentation |
| `benchmarks/results/round20/baseline_audit.json` | SHOULD COMMIT | 28202 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round20/calibration_v6.json` | SHOULD COMMIT | 5810 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round20/calibration_v6_initial_retry.json` | SHOULD COMMIT | 5490 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round20/calibration_v6_safety_final.json` | SHOULD COMMIT | 5233 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round20/coverage.json` | SHOULD COMMIT | 9740 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round20/development_breakdown.json` | SHOULD COMMIT | 8411 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round20/development_inputs_manifest.json` | SHOULD COMMIT | 1914425 | large public evidence; locked |
| `benchmarks/results/round20/development_observations_v6_initial_retry.json` | SHOULD COMMIT | 10517871 | large public evidence; locked |
| `benchmarks/results/round20/development_observations_v6_safety_final.json` | SHOULD COMMIT | 10567044 | large public evidence; locked |
| `benchmarks/results/round20/development_regression_v5_after_fix.json` | SHOULD COMMIT | 3470260 | large public evidence; locked |
| `benchmarks/results/round20/development_regression_v5_after_fix_v6_initial_retry.json` | SHOULD COMMIT | 3445516 | large public evidence; locked |
| `benchmarks/results/round20/development_regression_v5_after_fix_v6_safety_final.json` | SHOULD COMMIT | 3470260 | large public evidence; locked |
| `benchmarks/results/round20/development_safety.json` | SHOULD COMMIT | 295 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round20/end_to_end_v6.json` | SHOULD COMMIT | 298 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round20/evidence_locks.json` | SHOULD COMMIT | 6511 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round20/filled_v6.json` | SHOULD COMMIT | 298 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round20/final_checks.json` | SHOULD COMMIT | 4065 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round20/final_tests.json` | SHOULD COMMIT | 410 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round20/hard_negatives_development.json` | SHOULD COMMIT | 579294 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round20/historical_independent_v5_round19.json` | SHOULD COMMIT | 11928 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round20/historical_regression_fast.json` | SHOULD COMMIT | 2356415 | large public evidence; locked |
| `benchmarks/results/round20/input_safety.json` | SHOULD COMMIT | 3676 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round20/page_limit_audit.json` | SHOULD COMMIT | 2371 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round20/performance_stability.json` | SHOULD COMMIT | 450734 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round20/pre_freeze_gate.json` | SHOULD COMMIT | 540 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round20/release_gate_fast.json` | SHOULD COMMIT | 506066 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round20/retrieval_v6.json` | SHOULD COMMIT | 298 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round20/robustness_v6.json` | SHOULD COMMIT | 298 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round20/scan_v6.json` | SHOULD COMMIT | 298 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round20/technical_attempt_history.json` | SHOULD COMMIT | 1969 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round20/unknown_v4_not_run.json` | SHOULD COMMIT | 298 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round20/unknown_v4_preflight.json` | SHOULD COMMIT | 71941 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round20/v5_failure_audit.csv` | SHOULD COMMIT | 557059 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round20/v5_failure_summary.json` | SHOULD COMMIT | 1867 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round20/v5_false_accepts.csv` | SHOULD COMMIT | 7239 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round20/v5_false_rejects.csv` | SHOULD COMMIT | 148663 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round20/v5_retrieval_diagnostics.json` | SHOULD COMMIT | 20349 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round20/v5_source_breakdown.json` | SHOULD COMMIT | 6490 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round20/v5_transform_breakdown.json` | SHOULD COMMIT | 5036 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round20/v6_pool_audit.csv` | SHOULD COMMIT | 83173 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round20/v6_preflight.json` | SHOULD COMMIT | 1034 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/baseline_audit.json` | SHOULD COMMIT | 8895 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/calibration_v7.json` | SHOULD COMMIT | 5273 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/calibration_v7_initial.json` | SHOULD COMMIT | 5230 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/calibration_v7_ordered.json` | SHOULD COMMIT | 5228 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/canonical.json` | SHOULD COMMIT | 1448686 | large public evidence; locked |
| `benchmarks/results/round21/coverage.json` | SHOULD COMMIT | 9740 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/dev_false_reject_audit.csv` | SHOULD COMMIT | 67106 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/dev_retrieval_summary.json` | SHOULD COMMIT | 1691 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/development_improvements.json` | SHOULD COMMIT | 1638 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/development_observations_v7_initial.json` | SHOULD COMMIT | 10764200 | large public evidence; locked |
| `benchmarks/results/round21/development_observations_v7_ordered.json` | SHOULD COMMIT | 10767605 | large public evidence; locked |
| `benchmarks/results/round21/development_regression_v5_after_fix.json` | SHOULD COMMIT | 3568292 | large public evidence; locked |
| `benchmarks/results/round21/development_regression_v5_after_fix_v7_initial.json` | SHOULD COMMIT | 3564639 | large public evidence; locked |
| `benchmarks/results/round21/development_regression_v5_after_fix_v7_ordered.json` | SHOULD COMMIT | 3568292 | large public evidence; locked |
| `benchmarks/results/round21/development_safety.json` | SHOULD COMMIT | 2312072 | large public evidence; locked |
| `benchmarks/results/round21/end_to_end_v6.json` | SHOULD COMMIT | 203 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/evaluation_v6_filled_generation_audit.csv` | SHOULD COMMIT | 8310 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/evaluation_v6_generation_failure_summary.json` | SHOULD COMMIT | 7340 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/evaluation_v6_generation_preflight.json` | SHOULD COMMIT | 288 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/evaluation_v6_generation_recovery.json` | SHOULD COMMIT | 32828 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/evaluation_v6_leakage.json` | SHOULD COMMIT | 231 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/evaluation_v6_plan.json` | SHOULD COMMIT | 27033 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/evaluation_v6_prepared.json` | SHOULD COMMIT | 985050 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/evaluation_v6_representation_audit.json` | SHOULD COMMIT | 245113 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/evidence_locks.json` | SHOULD COMMIT | 9445 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/filled_v6.json` | SHOULD COMMIT | 203 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/final_checks.json` | SHOULD COMMIT | 4065 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/final_tests.json` | SHOULD COMMIT | 393 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/final_tests_on_freeze.json` | SHOULD COMMIT | 450 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/final_validation_on_freeze.json` | SHOULD COMMIT | 2557 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/freeze_manifest.json` | SHOULD COMMIT | 27659 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/hard_negatives_development.json` | SHOULD COMMIT | 584830 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/historical_independent_v5_round19.json` | SHOULD COMMIT | 11928 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/historical_regression_fast.json` | SHOULD COMMIT | 2367755 | large public evidence; locked |
| `benchmarks/results/round21/input_safety.json` | SHOULD COMMIT | 3676 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/page_limit_audit.json` | SHOULD COMMIT | 2371 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/performance_stability.json` | SHOULD COMMIT | 450695 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/pre_freeze_gate.json` | SHOULD COMMIT | 722 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/pre_freeze_tests.json` | SHOULD COMMIT | 740 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/release_gate_fast.json` | SHOULD COMMIT | 506066 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/retrieval_v6.json` | SHOULD COMMIT | 203 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/robustness_v6.json` | SHOULD COMMIT | 203 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/scan_v6.json` | SHOULD COMMIT | 203 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/technical_attempt_history.json` | SHOULD COMMIT | 6100 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/unknown_release_v4.json` | SHOULD COMMIT | 8802 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/unknown_release_v4_observations.json` | SHOULD COMMIT | 3837709 | large public evidence; locked |
| `benchmarks/results/round21/unknown_release_v4_started.json` | SHOULD COMMIT | 759 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/unknown_v4_candidates.json` | SHOULD COMMIT | 1280948 | large public evidence; locked |
| `benchmarks/results/round21/unknown_v4_preflight.json` | SHOULD COMMIT | 1611 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/unknown_v4_preflight_initial_auto.json` | SHOULD COMMIT | 944 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/unknown_v4_preflight_primary_initial.json` | SHOULD COMMIT | 1487 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/unknown_v4_selection.json` | SHOULD COMMIT | 4285 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/unknown_v4_truth_audit.json` | SHOULD COMMIT | 1672111 | large public evidence; locked |
| `benchmarks/results/round21/unknown_v4_truth_initial_auto.json` | SHOULD COMMIT | 1819847 | large public evidence; locked |
| `benchmarks/results/round21/unknown_v4_truth_primary_initial.json` | SHOULD COMMIT | 1461983 | large public evidence; locked |
| `benchmarks/results/round21/unknown_v4_truth_primary_v2.json` | SHOULD COMMIT | 1705755 | large public evidence; locked |
| `benchmarks/results/round21/unknown_v4_truth_revision_history.json` | SHOULD COMMIT | 957 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/v6_identity_eligibility.csv` | SHOULD COMMIT | 81991 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/v6_pool_prospects.json` | SHOULD COMMIT | 368595 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/v6_preflight.json` | SHOULD COMMIT | 1030 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round21/v6_source_eligibility.csv` | SHOULD COMMIT | 2603 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round22/archive_serialization_audit.json` | SHOULD COMMIT | 59625 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round22/baseline_audit.json` | SHOULD COMMIT | 197916 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round22/candidate_metadata.json` | SHOULD COMMIT | 179 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round22/canonical_post_v6.json` | SHOULD COMMIT | 1448739 | large public evidence; locked |
| `benchmarks/results/round22/coverage.json` | SHOULD COMMIT | 9740 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round22/end_to_end_v6.json` | SHOULD COMMIT | 23658874 | large public evidence; locked |
| `benchmarks/results/round22/evaluation_freeze_manifest.json` | SHOULD COMMIT | 32147 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round22/evaluation_v6_breakdown.json` | SHOULD COMMIT | 23081 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round22/evaluation_v6_failures.csv` | SHOULD COMMIT | 386769 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round22/evaluation_v6_gate.json` | SHOULD COMMIT | 4917 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round22/evaluation_v6_leakage.json` | SHOULD COMMIT | 670 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round22/evaluation_v6_observations.json` | SHOULD COMMIT | 19819668 | large public evidence; locked |
| `benchmarks/results/round22/evaluation_v6_preflight.json` | SHOULD COMMIT | 451 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round22/evaluation_v6_started.json` | SHOULD COMMIT | 801 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round22/evidence_locks.json` | SHOULD COMMIT | 7481 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round22/filled_failure_geometry.json` | SHOULD COMMIT | 1416 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round22/filled_generation_failure_audit.csv` | SHOULD COMMIT | 15465 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round22/filled_generation_inputs.json` | SHOULD COMMIT | 125434 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round22/filled_generation_v2.json` | SHOULD COMMIT | 579933 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round22/filled_generation_v2_observations.json` | SHOULD COMMIT | 579509 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round22/filled_policy_frozen.json` | SHOULD COMMIT | 209 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round22/filled_v6.json` | SHOULD COMMIT | 3597523 | large public evidence; locked |
| `benchmarks/results/round22/final_checks.json` | SHOULD COMMIT | 2710 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round22/final_tests.json` | SHOULD COMMIT | 504 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round22/generator_change_scope.json` | SHOULD COMMIT | 14709 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round22/historical_independent_v6_round22.json` | SHOULD COMMIT | 1346 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round22/historical_regression_fast.json` | SHOULD COMMIT | 2368022 | large public evidence; locked |
| `benchmarks/results/round22/input_safety.json` | SHOULD COMMIT | 3676 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round22/page_limit_audit.json` | SHOULD COMMIT | 2371 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round22/performance_stability.json` | SHOULD COMMIT | 450525 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round22/post_v6_checks.json` | SHOULD COMMIT | 600 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round22/post_v6_observations.json` | SHOULD COMMIT | 4464898 | large public evidence; locked |
| `benchmarks/results/round22/recognition_freeze_check.json` | SHOULD COMMIT | 9006 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round22/release_gate_fast.json` | SHOULD COMMIT | 505979 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round22/result_hash.json` | SHOULD COMMIT | 414 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round22/retrieval_v6.json` | SHOULD COMMIT | 243 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round22/robustness_v6.json` | SHOULD COMMIT | 19821921 | large public evidence; locked |
| `benchmarks/results/round22/safety_post_v6.json` | SHOULD COMMIT | 2312039 | large public evidence; locked |
| `benchmarks/results/round22/scan_v6.json` | SHOULD COMMIT | 13588184 | large public evidence; locked |
| `benchmarks/results/round22/technical_attempt_history.json` | SHOULD COMMIT | 4496 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round22/v6_representation_manifest.json` | SHOULD COMMIT | 1206743 | large public evidence; locked |
| `benchmarks/results/round22/visual_review_inputs.json` | SHOULD COMMIT | 2257 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round22/visual_review_result.json` | SHOULD COMMIT | 756 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round23/initial_inventory.json` | SHOULD COMMIT | 55702 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round23/legacy_ci_reference.json` | SHOULD COMMIT | 229643 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round23/precommit_validation.json` | SHOULD COMMIT | 3022 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round23/recognition_freeze_verification.json` | SHOULD COMMIT | 24003 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round23/secret_scan.json` | SHOULD COMMIT | 401 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round23/tracking_inventory.json` | SHOULD COMMIT | 104648 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/results/round23/version_occurrences.json` | SHOULD COMMIT | 247447 | Public synthetic/official-source metadata, immutable observations and audit; evidence locks require exact retained files |
| `benchmarks/round20_calibrate.py` | MUST COMMIT | 7311 | Runtime/policy/test/reproduction harness or release documentation |
| `benchmarks/round20_gates.py` | MUST COMMIT | 2321 | Runtime/policy/test/reproduction harness or release documentation |
| `benchmarks/round20_performance.py` | MUST COMMIT | 8332 | Runtime/policy/test/reproduction harness or release documentation |
| `benchmarks/round20_prepare.py` | MUST COMMIT | 7704 | Runtime/policy/test/reproduction harness or release documentation |
| `benchmarks/round21_calibrate.py` | MUST COMMIT | 5747 | Runtime/policy/test/reproduction harness or release documentation |
| `benchmarks/round21_gates.py` | MUST COMMIT | 2321 | Runtime/policy/test/reproduction harness or release documentation |
| `benchmarks/round21_performance.py` | MUST COMMIT | 8332 | Runtime/policy/test/reproduction harness or release documentation |
| `benchmarks/round21_release.py` | MUST COMMIT | 18889 | Runtime/policy/test/reproduction harness or release documentation |
| `benchmarks/round22_fill.py` | MUST COMMIT | 10498 | Runtime/policy/test/reproduction harness or release documentation |
| `benchmarks/round22_performance.py` | MUST COMMIT | 854 | Runtime/policy/test/reproduction harness or release documentation |
| `benchmarks/round22_post.py` | MUST COMMIT | 4211 | Runtime/policy/test/reproduction harness or release documentation |
| `benchmarks/round22_prepare.py` | MUST COMMIT | 12187 | Runtime/policy/test/reproduction harness or release documentation |
| `benchmarks/round22_release.py` | MUST COMMIT | 11056 | Runtime/policy/test/reproduction harness or release documentation |
| `benchmarks/schemas/round21_observations.schema.json` | MUST COMMIT | 1432 | Runtime/policy/test/reproduction harness or release documentation |
| `data/recognition_profiles/fingerprint_decision_v6.json` | MUST COMMIT | 1020 | Runtime/policy/test/reproduction harness or release documentation |
| `data/recognition_profiles/fingerprint_decision_v7.json` | MUST COMMIT | 1102 | Runtime/policy/test/reproduction harness or release documentation |
| `docs/CONTINUITA_OPERATIVA.md` | MUST COMMIT | 6842 | Runtime/policy/test/reproduction harness or release documentation |
| `docs/DECISION_POLICY_V6.md` | MUST COMMIT | 3352 | Runtime/policy/test/reproduction harness or release documentation |
| `docs/DECISION_POLICY_V7.md` | MUST COMMIT | 4733 | Runtime/policy/test/reproduction harness or release documentation |
| `docs/RELEASE_NOTES_v0.7.0-rc1.md` | MUST COMMIT | 3992 | Runtime/policy/test/reproduction harness or release documentation |
| `docs/ROUND20_BASELINE_AUDIT.md` | MUST COMMIT | 1591 | Runtime/policy/test/reproduction harness or release documentation |
| `docs/ROUND20_REPORT.md` | MUST COMMIT | 10778 | Runtime/policy/test/reproduction harness or release documentation |
| `docs/ROUND20_V5_FAILURE_AUDIT.md` | MUST COMMIT | 1709 | Runtime/policy/test/reproduction harness or release documentation |
| `docs/ROUND21_BASELINE_AUDIT.md` | MUST COMMIT | 1189 | Runtime/policy/test/reproduction harness or release documentation |
| `docs/ROUND21_EVALUATION_PROTOCOL.md` | MUST COMMIT | 3175 | Runtime/policy/test/reproduction harness or release documentation |
| `docs/ROUND21_REPORT.md` | MUST COMMIT | 11975 | Runtime/policy/test/reproduction harness or release documentation |
| `docs/ROUND21_V6_SOURCE_AUDIT.md` | MUST COMMIT | 4466 | Runtime/policy/test/reproduction harness or release documentation |
| `docs/ROUND22_BASELINE_AUDIT.md` | MUST COMMIT | 2719 | Runtime/policy/test/reproduction harness or release documentation |
| `docs/ROUND22_FILLED_GENERATION_AUDIT.md` | MUST COMMIT | 1231 | Runtime/policy/test/reproduction harness or release documentation |
| `docs/ROUND22_REPORT.md` | MUST COMMIT | 15843 | Runtime/policy/test/reproduction harness or release documentation |
| `docs/ROUND23_RELEASE_AUDIT.md` | MUST COMMIT | 3274 | Runtime/policy/test/reproduction harness or release documentation |
| `docs/ROUND23_REPORT.md` | MUST COMMIT | 1539 | Runtime/policy/test/reproduction harness or release documentation |
| `docs/ROUND23_TRACKING_AUDIT.md` | MUST COMMIT | 41255 | Runtime/policy/test/reproduction harness or release documentation |
| `maintenance/round21_unknown_acquire.py` | MUST COMMIT | 7509 | Runtime/policy/test/reproduction harness or release documentation |
| `scripts/round20_baseline.py` | MUST COMMIT | 5479 | Runtime/policy/test/reproduction harness or release documentation |
| `scripts/round20_checks.py` | MUST COMMIT | 3715 | Runtime/policy/test/reproduction harness or release documentation |
| `scripts/round20_common.py` | MUST COMMIT | 1555 | Runtime/policy/test/reproduction harness or release documentation |
| `scripts/round20_failure_audit.py` | MUST COMMIT | 11826 | Runtime/policy/test/reproduction harness or release documentation |
| `scripts/round20_finish.py` | MUST COMMIT | 26299 | Runtime/policy/test/reproduction harness or release documentation |
| `scripts/round20_package_verifier.py` | MUST COMMIT | 6443 | Runtime/policy/test/reproduction harness or release documentation |
| `scripts/round20_registry.py` | MUST COMMIT | 7566 | Runtime/policy/test/reproduction harness or release documentation |
| `scripts/round20_unknown_preflight.py` | MUST COMMIT | 1875 | Runtime/policy/test/reproduction harness or release documentation |
| `scripts/round21_audits.py` | MUST COMMIT | 4999 | Runtime/policy/test/reproduction harness or release documentation |
| `scripts/round21_baseline.py` | MUST COMMIT | 4533 | Runtime/policy/test/reproduction harness or release documentation |
| `scripts/round21_checks.py` | MUST COMMIT | 3715 | Runtime/policy/test/reproduction harness or release documentation |
| `scripts/round21_common.py` | MUST COMMIT | 3170 | Runtime/policy/test/reproduction harness or release documentation |
| `scripts/round21_finish.py` | MUST COMMIT | 25345 | Runtime/policy/test/reproduction harness or release documentation |
| `scripts/round21_freshness.py` | MUST COMMIT | 4784 | Runtime/policy/test/reproduction harness or release documentation |
| `scripts/round21_generation_resume.py` | MUST COMMIT | 6486 | Runtime/policy/test/reproduction harness or release documentation |
| `scripts/round21_package_verifier.py` | MUST COMMIT | 9086 | Runtime/policy/test/reproduction harness or release documentation |
| `scripts/round21_prerequisites.py` | MUST COMMIT | 12536 | Runtime/policy/test/reproduction harness or release documentation |
| `scripts/round21_sources.py` | MUST COMMIT | 10277 | Runtime/policy/test/reproduction harness or release documentation |
| `scripts/round21_unknown_truth.py` | MUST COMMIT | 8259 | Runtime/policy/test/reproduction harness or release documentation |
| `scripts/round21_validate_final.py` | MUST COMMIT | 3557 | Runtime/policy/test/reproduction harness or release documentation |
| `scripts/round22_baseline.py` | MUST COMMIT | 7699 | Runtime/policy/test/reproduction harness or release documentation |
| `scripts/round22_common.py` | MUST COMMIT | 4504 | Runtime/policy/test/reproduction harness or release documentation |
| `scripts/round22_finish.py` | MUST COMMIT | 31957 | Runtime/policy/test/reproduction harness or release documentation |
| `scripts/round22_package_verifier.py` | MUST COMMIT | 10527 | Runtime/policy/test/reproduction harness or release documentation |
| `scripts/round22_snapshot.py` | MUST COMMIT | 1682 | Runtime/policy/test/reproduction harness or release documentation |
| `scripts/round22_validate_final.py` | MUST COMMIT | 6097 | Runtime/policy/test/reproduction harness or release documentation |
| `scripts/round23_checkout.py` | MUST COMMIT | 1107 | Runtime/policy/test/reproduction harness or release documentation |
| `scripts/round23_ci.py` | MUST COMMIT | 2768 | Runtime/policy/test/reproduction harness or release documentation |
| `scripts/round23_release.py` | MUST COMMIT | 11400 | Runtime/policy/test/reproduction harness or release documentation |
| `src/fingerprint_decision_v6.py` | MUST COMMIT | 12192 | Runtime/policy/test/reproduction harness or release documentation |
| `src/fingerprint_decision_v7.py` | MUST COMMIT | 17603 | Runtime/policy/test/reproduction harness or release documentation |
| `tests/test_round20.py` | MUST COMMIT | 4021 | Runtime/policy/test/reproduction harness or release documentation |
| `tests/test_round21.py` | MUST COMMIT | 4240 | Runtime/policy/test/reproduction harness or release documentation |
| `tests/test_round21_release.py` | MUST COMMIT | 1917 | Runtime/policy/test/reproduction harness or release documentation |
| `tests/test_round22_generator.py` | MUST COMMIT | 5391 | Runtime/policy/test/reproduction harness or release documentation |
