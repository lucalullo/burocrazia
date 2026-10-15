# Round 7 — baseline audit

Ingresso `d3dd53bbc2e97047d7eadbe379c31bb920929c7b`, branch `codex/coverage-benchmark-v0.7.0`, working tree iniziale pulito.
Software 0.6.1, schema 610; 1.216 reali, 1.212 operativi. Seed integrity/FK e hash invariati.
Seed SHA `790b690123c82e1cb7bdfa67a10216284022987d50b0abbcc4a1a245785e3e99`.

Firme: 948/1212; file-backed 1158; totale 78.22%, file-backed 81.87%.
Canonical 987/987, robustness 150/192, scansioni 128/168; zero wrong in questi tre corpus.
Candidate recall@1/5/10/25 100% sul corpus Round6. Filled: 100 AcroForm +70 overlay, tutti corretti; scope distinti.
Performance effettiva: p50 112.9562 ms, p95 799.1129 ms (gate <=250 ms fallito), indice 39852804 byte.
Test Round6 verificati: 655 passed, 3 skip, zero failed; nessuna nuova esecuzione baseline dichiarata.

Regressione esatta: EX02 (CI543) ed EX03 (CI544), versione catalogata 1.1 assente dal testo; veto globale `missing_model_revision` nel fallback metadata. Storico 33/35, expected immutati.
Locked v1 59/69 storico; locked v2 69/69. R061 NO, cinque safety cases 5/5, negativi 130/130, family sintetica 161/161.
Gate falliti: coverage_file_backed, robustness_exact_recall, scan_exact_recall, scan_useful_recall, historical_development_regression, warm_p95.

Tutti i raw JSON Round6 sono hashati nel baseline audit; metriche per caso ricalcolate con il rispettivo schema. Nessun artefatto storico modificato.
Da questo momento Round6 evaluation è development; non verrà presentata come nuova evaluation indipendente.
