# Round 16 — baseline

Branch `codex/coverage-benchmark-v0.7.0`, HEAD `d39103d0673b8690816df1f9a3a4499a46f94f45`, working tree pulito all'ingresso. Software0.6.1/schema610. 481 blob storici e tutti i lock Round15 verificati prima delle modifiche al motore.

Metriche ricalcolate dai raw: canonici980/980+27/27;241 righe NO storiche senza accettazioni; input-safety9/9; coverage1002/1158=86.528497%. Cinque run/2010 tempi: mediana p95 263.0707ms. V2 storico107/114,3 DOCUMENT_MATCH,0 FAMILY_MATCH,4 errori, denominatore e label intatti. Nessun freeze/v3 indipendente/v5 Round15.

**Correzione fattuale del prompt:** EX02/EX03 sono INPS CI543/CI544 (record13/12), input sintetici privi della revisione1.1, già ambiguous in reference_truth_v2. I due INAIL ambigui sono U14-5f0c017c3d56e6c5 e U14-c1fc4765c01dcd62, record1147, annualità2025/2024 rispetto al canonico2023. Sono quattro risorse/casi distinti. Non vengono equiparati né usati per tuning. La release-fast preesistente ha soltanto EX02/EX03 come mismatch obbligatori; locked-v1 conserva separatamente i suoi10 mismatch storici.

Baseline completa: 786 passed,0 failed,3 skipped. Profilo reale dei67 input storici in performance_profile.json, prima di ogni ottimizzazione; misure cProfile/tracing diagnostiche, non sostituiscono i sette run warm finali. Nessun cambio a scoring, tiers, soglie, pesi, veto, famiglie, dataset o catalogo autorizzato. La release truth verrà estesa tramite addendum motivato, preservando v1/v2/v3 e distinguendo prove ufficiali, binding canonici tecnici e contratti sintetici di sicurezza.
