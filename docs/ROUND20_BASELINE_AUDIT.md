# Round 20 — baseline verificata

Branch `codex/coverage-benchmark-v0.7.0`, HEAD `7da8b10f3d7c8ea302d7a3dd565f265bf5c5f370`, working tree pulito all'ingresso:0 modificati/0 non tracciati. Software pubblico0.6.1, schema610.

Freeze storico V5 `aa816782b075c8a27eabb7492d080d1c26fa3119`, runtime `8f8a50c679a399623b9bd3964fba090d95b36608cd46e2f149f4752fd3169890`. Tutti i raw V5 caricati, count665/665/665 ID unici,635 noti/504 scan/55 compilati/30 unknown mix;38 identità/6 fonti. SHA selection/leakage/raw/gate/matrice trasformazioni verificati e preservati. Leakage0. Metriche originali ricalcolate sui raw prima delle modifiche e classificate historical_independent_v5_round19: P98.2456%, R70.5512%, scan R63.2937%. Gate falliti:v5_exact_recall, v5_precision, v5_retrieval_at25, v5_scan_precision, v5_scan_recall.

Suite completa nuova prima delle modifiche semantiche:834 passed/0 failed/3 skipped,488.84s; log SHA `db5f9146abf9ec4a840d7c4ab48159115b716418c9c5a10fab9bdc400ab4d233`. Dati/catalogo/schema/profili/truth congelati integri; prove canoniche1007/1007,coverage1002/1158,safety9/9,release-fast1258/1258,equivalenza1563/0diff e sette timing raw Round19 verificati sul medesimo runtime. Mediana p95 storica198.6201ms. Nuova validazione dopo eventuali modifiche rimane obbligatoria e separata.

Unknown v3 originale116/116,13 fonti,0 false accept viene preservato come storico: dopo tuning non valida il nuovo motore. Nessun replay è presentato come indipendente. I successivi registry v5/v6 escluderanno le38 identità V5,635 rappresentazioni e tutte le risorse unknown v1-v3.
