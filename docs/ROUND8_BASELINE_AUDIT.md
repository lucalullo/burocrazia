# Round 8 — audit baseline prima delle modifiche runtime

Branch `codex/coverage-benchmark-v0.7.0`, ingresso `034eb37fdec09a18291117872b093c9a9480dc0d`. Working tree iniziale pulito prima della creazione dello script di audit. Software 0.6.1, schema 610; catalogo e corpus congelati invariati. Nessun push/tag/release.

Raw Round 7 ricalcolati dai casi: canonical 979/979; robustness 183/372 (49.1935%); scansioni 134/280 (47.8571%); filled 7/50, con soltanto 9 generati e 41 generation failures. Zero wrong accepted. I risultati R6/R7 diventano development; non sono prova indipendente Round 8. File coverage 941/1158 (81.2608%), totale 941/1212 (77.6403%). Il vecchio p95 registrato era 444.6542 ms.

Suite completa iniziale: 690 passati, 3 saltati, 0 falliti, 546.29 s; log SHA `83d925e71ae311e2bf43b93498bc11578a7957ed6c1bd8d353bc919112534994`. 110 JSON R6/R7 conservati per hash. Le misure non vengono sostituite.

Inventario etichette prima del tuning: 9 gruppi con testo normalizzato identico e expected discordanti; 10 case_id con expected differenti, inclusi cambi di input intenzionali da distinguere dalle contraddizioni. Registro riconciliato separato, mai riscrittura dei locked.

## Profilo warm per componente

51 input fissi (35 sintetici e 16 risorse ufficiali già usate in R7), 6 ripetizioni. Probes dei componenti non additivi: ripetono la primitiva fuori dalla misura totale, senza costo Tesseract o rendering. cProfile separato per la diagnosi delle funzioni.

| Componente | p50 ms | p95 ms |
|---|---:|---:|
| recognition_total | 45.265 | 281.510 |
| normalization | 0.022 | 0.210 |
| input_fingerprint_generation | 0.680 | 36.516 |
| candidate_retrieval | 0.023 | 15.110 |
| ocr_sketch_compare | 0.001 | 7.572 |
| char_overlap | 0.001 | 12.573 |
| visual_compare | 0.000 | 7.269 |
| decision_fusion_inclusive | 1.083 | 106.189 |
| family_fallback | 1.286 | 7.424 |

Raw: `benchmarks/results/round8/baseline/`; full scan e sicurezza storica restano i riferimenti. Nessuna nuova identità o fonte autorizzata.

## Interferenza individuata

Un helper diagnostico di questa stessa attività, avviato nel Round 7 con `run_benchmark()` da stdin, era rimasto attivo e consumava CPU. La sua identità e gerarchia di processi sono state verificate prima di terminarlo. La suite iniziale ha condiviso parte della CPU con questo helper; il profilo warm riportato sopra è stato eseguito dopo la sua terminazione e dopo la suite. Le precedenti misure R7 sono conservate, ma l'interferenza limita il confronto dei tempi assoluti. Non vengono sostituite con il nuovo numero.
