# Round 13 baseline audit

Branch `codex/coverage-benchmark-v0.7.0`, HEAD `77bbe149a52102d5ca42743702c5b39f5a475326`, working tree pulito all'ingresso. Pubblico 0.6.1/schema 610. Verificati 21 lock R12 prima delle modifiche.

Coverage ricalcolata: 975/1158 = 84.196891%, minimo 985, deficit 10. Le 40 conversioni R12 corrispondono a **40 identità distinte e 40 SHA originali distinti**. Formati: `{".xlsx": 9, ".xls": 8, ".doc": 22, ".rtf": 1}`. Tutte hanno sketch tecnici persistiti nei raw maintenance, ma **zero sono nel dataset/indice runtime**. Il limite non è equivalente a un divieto metodologico di derivare fingerprint da legacy.

Manifest release invariato SHA `60246fc4e63f41f55b367141ec4ab5b45c08fc42db7d30d5a2551e8c19ad70be`, seed 2026101311, 105 casi/10 fonti/max 23.809524%. Nessuna predizione R12. Performance R12 verificata: cinque p95 [195.6687, 261.1139, 259.0858, 217.834, 202.9763], mediana 217.8340 ms, 3/5 sotto soglia; 4/5 è preferito. Test precedenti 767 passed/0 failed/3 skipped, senza presentarli come rerun R13.

Definizione fissata prima dei nuovi risultati: `7d13aa4fcc7e6b3bb86a2d43c3e8ec203d6628f86cf9e43291176affb2b6c037`. Ogni nuovo supporto legacy dovrà superare l'intero audit e una prova runtime normale su formato supportato; conversione e persistenza da sole non bastano.
