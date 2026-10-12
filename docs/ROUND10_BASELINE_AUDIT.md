# Round 10 baseline audit

Branch `codex/coverage-benchmark-v0.7.0`, HEAD `8c13da270fe2c4db212ca3611fb5ce0ddef7b0d8`, working tree pulito all'ingresso. Software 0.6.1, schema 610. Fingerprint-v3 e fingerprint-decision-v5 attive; hash motore e dati corrispondenti al profilo finale R9. Verificati tutti i 57 lock R9 prima delle modifiche. Nessun freeze R9 o evaluation v5.

Canonical ricalcolato dai 979 raw: 979/979; nessun wrong. Storici base 33/35, locked-v1 59/69, locked-v2 69/69, compat-v2 37/37, negativi 30/30 e 100/100. Tutti i NO storici verdi. EX02MISSINGREV/EX03MISSINGREV rieseguiti: NO. Etichette ambigue v1 preservate, senza nascondere i rifiuti EX02/EX03. I cinque casi ufficiali critici sono verdi nei raw di verification R9.

Performance R9 confermata dai raw legati agli hash correnti: p50 43.0796 ms, p95 187.7645 ms (402 recognition-only richieste). Fixed51 p95 249.8768 ms; digital PDF 338.9603 ms; scan con testo OCR disponibile 135.7979 ms. Limiti per formato e crescita RSS R9 restano dichiarati. Suite R9: 749 passed, 3 skipped, 0 failed. CI esterna pending.

File-backed fissi 1158, fingerprinted unambiguous 941, coverage 81.260794%; minimi per 85%: 985, delta esatto 44. Operative 1212, fingerprinted 941, coverage 77.640264%. Nessun denominatore ridotto.

Unknown confermati 68: MIMIT 45, INAIL 16, Lavoro 6, ANAC 1. Quattro fonti, concentrazione 66.176471%; corpus insufficiente. Nessuna promozione a catalogo. Le misure e gli hash integrali sono in `benchmarks/results/round10/baseline_audit.json`.

LibreOffice è presente nel percorso standard di installazione, fuori dal PATH. Il probe R9 basato sul PATH non lo rilevava: verificare il convertitore prima di dichiarare unsupported. Motore, soglie, pesi e fusion tiers restano invariati.
