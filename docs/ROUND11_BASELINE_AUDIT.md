# Round 11 baseline audit

Branch `codex/coverage-benchmark-v0.7.0`, HEAD `d19547f458e46d38c11a84ffd9e2f735510ac5bc`, working tree pulito all’ingresso. Pubblico 0.6.1, schema 610; fingerprint-v3 e decision-v5. Verificati tutti i 46 lock R10. Nessun freeze o evaluation v5, CI external_pending.

Denominatore congelato R6: 1158; identità unambiguous 941; coverage 81.260794%. Minimo per l’85%: 985, delta 44. Operative 1212, coverage 77.640264%. I 38 candidati shared-only sono un limite superiore da auditare, non un aumento automatico della metrica. Nessun cambio di denominatore.

Canonical ricalcolato 979/979, wrong 0; 241 osservazioni NO storiche, false accept 0. R061, due casi R8 e cinque casi ufficiali critici verdi nei raw R10. Base 33/35 e locked v1 59/69 preservati, v2 69/69, compat 37/37, hard negatives 30/30 e 100/100. Rerun baseline suite: 758 passati, 3 skipped, 0 failed (486.1 s), Tesseract locale reale.

Performance R10 p50 25.5838 ms, p95 146.0866 ms, 402 richieste, legata agli hash correnti. Il raw conserva i quantili del protocollo, non tutti i tempi individuali: il quantile è verificato come misura persistita, senza inventare una nuova ricostruzione dei campioni.

Unknown master 107, 7 fonti: `{"mimit": 45, "anac": 9, "inail": 16, "lavoro": 6, "mef": 13, "agid": 15, "mit": 3}`. Dominante mimit=45, concentrazione 42.056075%; altri 62. Subset N=100: al massimo 25 dal dominante, quindi servono esattamente 13 nuovi casi non dominanti e almeno 1 nuova fonte. Tutto il master resta conservato. Dati e hash integrali nei raw R11.
