# Round 5 — audit di ingresso

Ingresso verificato: commit f9e1fa06821907da53f75417555bd3cbdd50c7d0, branch codex/coverage-benchmark-v0.7.0, software 0.6.1, schema 610. Snapshot pubblico SHA-256 790b690123c82e1cb7bdfa67a10216284022987d50b0abbcc4a1a245785e3e99.

Integrità SQLite ok, FK zero; 1.216 reali, 1.212 operativi, quattro rifiutati, provenance 1.216/1.216. Nessun database personale letto o aggiornato.

Prima di integrare il nuovo riconoscitore sono stati rieseguiti sviluppo ufficiale e holdout storici dalla cache verificata, con metriche uguali ai raw Round 4: sviluppo 46 exact /150 positivi, 104 rifiuti, zero errati; holdout v1 diagnostico 32/127, zero errati; v2 2/17, 15 rifiuti, zero errati, 75 negativi corretti. Ripristinata l'etichetta ausiliaria famiglia 10 di OR2-101 dal report riconciliato Round 4, senza cambiare corpus.

Rieseguiti i corpus testuali: regressione 35/35, locked v2 69/69 con R061 NO_MATCH, hard negatives 30/30 e 100/100; locked v1 storico 59/69 mantenuto separatamente.

Suite di ingresso: 584 passed, 0 failed, 3 skipped, 460.78 secondi, Windows Python 3.12.10. I tre skip sono quelli storici symlink/FIFO. Log locale ignorato SHA-256 60f9702837ba3f0a2546a809979fb5cad7aacbc464ac0a8228c7410c62e3fa31.

Metriche Round 4 controllate dai raw e conservate: OCR reale legacy 7/7, raster sintetico v2 14/14; family supplement 0/1; performance p50 101.1612 ms e p95 133.0268 ms entro 1.5x baseline; RSS caldo 45.760.512 byte. Queste misure OCR/performance sono verifiche dei raw storici, non nuove misure temporali; il round corrente le riesegue separatamente.

I report e le ricevute Round 4 restano invariati. I nuovi moduli non ancora importati durante l'audit modificavano il digest dell'albero sorgenti, non il comportamento del motore di ingresso; commit e hash storici restano quelli registrati nei raw originali. Evidenza ricalcolata: benchmarks/results/round5/baseline/.
