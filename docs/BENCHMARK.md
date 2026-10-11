# Benchmark della candidata

Generato da `python scripts/release_report.py`. Stato: **NON PRONTO**. Versione software mantenuta a 0.6.1; obiettivo 0.7.0. Nessun tag/push/release. Il commit valutato e tutte le impronte sono nei risultati raw; il commit finale può aggiungere report/documentazione senza cambiare il codice misurato.

| Corpus | Casi | Passati | Precisione documento | Recall documento | F1 documento | Precisione famiglia | Recall famiglia | F1 famiglia | Copertura utile |
|---|---:|---:|---|---|---|---|---|---|---|
| burocrazia-synthetic-text-regression-2026-09-05 | 35 | 35 | 100.00% (11/11) | 100.00% (11/11) | 100.00% (22/22) | 100.00% (14/14) | 87.50% (14/16) | 93.33% (28/30) | 100.00% (25/25) |
| burocrazia-release-locked-v1 | 69 | 59 | 96.43% (54/56) | 90.00% (54/60) | 93.10% (108/116) | 100.00% (5/5) | 55.56% (5/9) | 71.43% (10/14) | 85.51% (59/69) |
| burocrazia-hard-negatives-v1 | 30 | 30 | n.d. (0 casi) | n.d. (0 casi) | n.d. (0 casi) | n.d. (0 casi) | n.d. (0 casi) | n.d. (0 casi) | n.d. (0 casi) |
| catalog-canonical-coverage-v1 | 1216 | 1146 | 100.00% (1146/1146) | 94.24% (1146/1216) | 97.04% (2292/2362) | n.d. (0 casi) | n.d. (0 casi) | n.d. (0 casi) | 94.24% (1146/1216) |
| official-local-v1 | 8 | 4 | 100.00% (4/4) | 50.00% (4/8) | 66.67% (8/12) | n.d. (0 casi) | n.d. (0 casi) | n.d. (0 casi) | 50.00% (4/8) |

## Rifiuti ed errori

| Corpus | False accettazioni sconosciuti | Rifiuti corretti sconosciuti | Rifiuto supportati | Errori ente | Errori versione |
|---|---|---|---|---|---|
| burocrazia-synthetic-text-regression-2026-09-05 | 0.00% (0/10) | 100.00% (10/10) | 0.00% (0/25) | 0.00% (0/23) | 0.00% (0/11) |
| burocrazia-release-locked-v1 | n.d. (0 casi) | n.d. (0 casi) | 11.59% (8/69) | 0.00% (0/61) | 0.00% (0/54) |
| burocrazia-hard-negatives-v1 | 0.00% (0/30) | 100.00% (30/30) | n.d. (0 casi) | n.d. (0 casi) | n.d. (0 casi) |
| catalog-canonical-coverage-v1 | n.d. (0 casi) | n.d. (0 casi) | 5.76% (70/1216) | 0.00% (0/1146) | 0.00% (0/1146) |
| official-local-v1 | n.d. (0 casi) | n.d. (0 casi) | 50.00% (4/8) | 0.00% (0/4) | 0.00% (0/4) |

Copertura canonica: `{"documents_tested": 1216, "exact": 1146, "family_fallback": 0, "no_match": 70, "wrong_identity": 0, "entity_errors": 0, "version_errors": 0}`. Questa è autocopertura dei metadati, non qualità su scansioni. Le confusion matrix, il macro per fonte, i breakdown per categoria/rumore e gli intervalli bootstrap al 95% per gruppi sono nei JSON raw. Denominatore zero significa non definito.

Il locked v1 contiene sei casi con titoli generici senza evidenza distintiva, due famiglie con evidenza insufficiente e due attese di famiglia per testi che identificano documenti già censiti. Le etichette non sono cambiate per far passare il candidato. Il corpus è pubblico/sintetico, con possibile sovrapposizione fra famiglie di sviluppo e release: non è indipendente. Il vecchio motore passava 49/69 e accettava 11/30 negativi difficili; i dettagli restano in `benchmarks/results/baseline_v061/`.

Campione ufficiale: 9 file tentati, 8 estratti e valutati, 4 identificati correttamente. Non esiste una prova di generalizzazione ampia. Il PDF INPS non leggibile rimane un errore di estrazione, separato dal matching. Le etichette emittente FP descrivono il produttore del modello nazionale, che il file destinato al SUAP può non riportare; si preferisce il rifiuto. Nessun testo estratto o PDF entra nel repository.

OCR reale: `not_run`, 0/12 eseguiti. Tesseract assente in questo ambiente; i 12 raster sono generabili ma non costituiscono una prova OCR. Il precedente 7/7 della 0.6.1 è una misura storica, non una verifica corrente.

## Prestazioni

| Corpus | p50 ms | p95 ms | p99 ms |
|---|---:|---:|---:|
| burocrazia-synthetic-text-regression-2026-09-05 (389 reali) | 30.688 | 34.3771 | None |
| burocrazia-synthetic-text-regression-2026-09-05 (1216 reali) | 70.752 | 103.4272 | None |
| burocrazia-release-locked-v1 (1216 reali) | 138.43 | 202.9798 | None |
| burocrazia-hard-negatives-v1 (1216 reali) | 148.5535 | 170.7585 | None |
| catalog-canonical-coverage-v1 (1216 reali) | 137.86 | 187.3132 | 227.8935 |

Baseline e candidata usano full scan; la candidata prepara/cachea solo metadati del catalogo, con limite 4.096 elementi. I 134 testi congelati hanno un test differenziale tra cache e preparazione senza cache. Nessun testo caricato viene cacheato. I tempi di preparazione, caricamento e picchi Python sono nei raw; la memoria candidata include una cache fredda, mentre la baseline originaria misurava la singola inferenza senza questa cache: non sono confronti di RSS/processo. Nessun prefiltraggio dei candidati, nessun indice semantico, nessuna prova di equivalenza con un motore indicizzato dichiarata. Il p99 è pubblicato soltanto con almeno 100 casi.

## Gate e verifiche

Suite: 488 passati, 0 fallimenti, 3 skip; Python 3.12.10, Windows locale. Integrità SQLite ok, FK zero, provenienza 100% delle aggiunte, continuità storica e runtime offline verificati dai test. Il comando release fast restituisce 1 per i casi locked non passati: la CI conserva questo fallimento. La matrice Linux/macOS/Windows remota non è stata eseguita. Il gate di precisione documentale >=99%, l'OCR reale e la CI multipiattaforma impediscono la promozione. Vedere `release_gates.json` e `validation_latest.json`.
