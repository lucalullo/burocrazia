# Round 23 — audit iniziale della release

Branch `codex/coverage-benchmark-v0.7.0`; HEAD iniziale `7da8b10f3d7c8ea302d7a3dd565f265bf5c5f370`. Remote `origin`: `https://github.com/lucalullo/burocrazia.git`. All'ingresso: 12 file modificati, 218 non tracciati. Il diff contiene il lavoro già concluso nei Round 20–22; nessuna modifica viene annullata. Log e stato iniziale sono conservati nel checkpoint privato; l'inventario pubblico registra ogni file e SHA.

Il verificatore originale Round 22 è stato eseguito prima di ogni modifica ai metadata: PASS su 1.554 file protetti, prove frozen, generazione, canonical, safety e performance. ZIP locale `dist/BurOCRazia-v0.7.0-RC1-round22.zip`: SHA256 `bc9e3aa49b1c05b2a773f4c605e1b79569ec21a0339fab6adef42dac8de27f26`. Non è un asset da aggiungere a Git.

Recognition hash `c077552055c25b0bc128e1a5c607afc434fb3bd074e6da165f3d8333145abf15`, schema 610, catalogo e fingerprint invariati. Tutti i file del freeze e gli evidence lock Round 22 coincidono. V6 originale SHA `6a230f43e2e98e4633520c8de5e99075af15c51b9d5090ce7a86217b10d19afe`; unknown v4 originale SHA `50dc1ac906d095b33a145ee27ef74c6462dca31c758d84af5671f0ee25fe2191`. Zero nuove predizioni dei due held-out nel Round 23.

GitHub CLI autenticato tramite keyring. Stable iniziale: release ID 383485645, tag `v0.6.1`, tag object `80ca62c8e4ec3c81d1b98e8751beeab5acfadedd`, pubblicata il 6 settembre 2026; latest stabile. Nessun tag RC iniziale. Workflow automatico esistente `Test locali` (`.github/workflows/tests.yml`), matrice Ubuntu/Windows/macOS Python 3.12. `benchmark-full.yml` è un workflow manuale, non un gate automatico; non si avviano held-out.

Il prompt Round 23 autorizza staging, commit, push del branch corrente e, soltanto con CI verde, tag e pre-release `v0.7.0-rc1`. Vietati merge, force push, riscrittura tag, modifica stable o motore. Metadata candidato aggiornabili in `pyproject.toml`, fuori dall'inventario del recognition engine; le occorrenze 0.6.1 nei freeze e nelle prove storiche restano immutabili.

Le 81 differenze di serializzazione storiche LF/CRLF sono già provate nel Round 22 contro archivio precedente e Git. Nessuna normalizzazione dei corpus o dei file locali viene introdotta. Il pacchetto Round 22 descrive il suo snapshot originario; i README e metadata Round 23 costituiscono una successiva modifica di release, non una nuova misura del motore.

## Adeguamenti CI della release

La CI installa ora la dipendenza benchmark opzionale già versionata `pypdf==6.10.0`, necessaria per i test del generatore. Il benchmark sintetico usa esplicitamente il corpus v2 già approvato. Il runner legacy continua a produrre gli esiti originali e il suo exit 1: un adattatore confronta tutte le righe con le osservazioni Round 22, inclusi ogni mismatch, errore ente e versione. Qualsiasi differenza fallisce; nessuna etichetta, soglia o metrica è corretta per ottenere verde.

Su checkout Linux/macOS il manifest catalogo storico è serializzato LF da Git. Un passaggio preparatorio ammette soltanto i due SHA già provati nel Round 22 e ripristina l'esatta rappresentazione fisica CRLF congelata prima dei test. Non normalizza altri file e non modifica contenuto o motore. I risultati temporanei CI locali rimangono ignorati.
