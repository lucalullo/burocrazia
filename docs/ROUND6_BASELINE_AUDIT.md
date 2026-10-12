# Round 6 — baseline audit

Ingresso verificato prima delle modifiche al runtime: `0204970bc2b58e6332b7dfe73b358f118e252010`, branch
`codex/coverage-benchmark-v0.7.0`.
Working tree iniziale pulito. Software 0.6.1, target 0.7.0, SQLite 610,
firma fingerprint-v1. Catalogo: 1.216 reali, 1.212 operativi, quattro rifiutati.
SHA seed `790b690123c82e1cb7bdfa67a10216284022987d50b0abbcc4a1a245785e3e99`; integrity/FK e lock storici verificati.

369/1.212 firme (30,4455%). Tutte le metriche per caso sono ricalcolate dai raw Round 5
con confronto esatto con le metriche pubblicate. Hash, numeratori e denominatori sono in
`benchmarks/results/round6/baseline/audit.json`. Nessun raw storico modificato.

| Prova | Exact | Family | NO | Wrong |
|---|---:|---:|---:|---:|
| canonical | 362 | 0 | 7 | 0 |
| robustness | 48 | 0 | 148 | 0 |
| filled_forms | 10 | 0 | 4 | 0 |
| unknown_official | 0 | 0 | 137 | 0 |
| family_identity_holdout | 0 | 0 | 1 | 0 |

Canonical: 362/369, precision 100%, recall 98,103%. Robustness: 48/196, recall 24,49%.
Filled: 10/14. Unknown: 137/137 rifiutati. Famiglia: un caso, nessuna famiglia valutabile.
I sette canonical NO sono 89, 107, 112, 254, 440, 942, 1079.

Performance storica verificata dai raw: p50 91,2146 ms, p95 128,1624 ms;
indice 28.676.242 byte, bundle 12.188.225 byte. OCR storico 7/7 e sintetico v2 14/14.
Test Round 5: 615 passed, 3 skip Windows; baseline fresca Round 6:
615 passed, 3 skipped,
zero fallimenti, 567.37 s. Lo SHA del log è nel raw audit.

Candidata iniziale NOT READY. CI esterna non eseguita. Le misure sopra sono storiche
o baseline locale e non costituiscono risultati del nuovo motore.
