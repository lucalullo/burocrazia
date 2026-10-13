# Round 12 baseline audit

Branch `codex/coverage-benchmark-v0.7.0`, HEAD `d911fccae4042c5c720a22d9e8767793a9aec61d`, working tree pulito all'ingresso, prima della misura e della creazione di questo script. Pubblico 0.6.1, schema 610. Verificati 43 lock delle prove Round 11.

Denominatore ricalcolato dai raw R6: 1158. Supportate 975 (942 univoche e 33 shared-only); minimo `ceil(0.85 * 1158)` = 985, deficit 10. Nessuna riclassificazione del denominatore.

Master unknown 125, release 105, 10 fonti, concentrazione massima 23.809524%. Seed 2026101311; selezione ricalcolata identica, manifest SHA `60246fc4e63f41f55b367141ec4ab5b45c08fc42db7d30d5a2551e8c19ad70be`. Tutti confirmed_unknown; audit preesistente e esposizione storica conservati. Nessuna predizione release eseguita.

Canonical raw 980/980; 241 NO storici, zero false accept. R061, i due NO Round 8 e i cinque critici sono documentati nei raw Round 11. Suite precedente 762 passed / 0 failed / 3 skipped: è una misura storica, non il rerun Round 12.

Baseline performance ripetuta **prima delle modifiche** con il worker isolato R9 invariato: 402 richieste warm, p50 58.4073 ms, p95 275.5781 ms. OCR separato, stesso corpus storico e stesso hardware. I dettagli e gli hash di motore/dataset sono in `baseline_performance.json`; la stabilità su cinque run richiede una misura ulteriore e non è dedotta da questo singolo valore.

Nessun freeze o evaluation v5. CI external_pending. Le successive attività rispettano l'ordine coverage → unknown single-shot → safety → prerequisiti.
