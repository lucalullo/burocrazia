# Round 4 — NOT_READY

Software 0.6.1. Freeze commit `9458c730bf5a25440850320c5f9981f19aeaf06f`, runtime `fd4e96c2dec57f8e4795da814a455693a7e4b5be274b24ed18406041d63d33da`. Nessun push, tag o release. Catalogo e schema 610 invariati. Il motore non cambia dopo la prima valutazione v2.

| Corpus | N | Esatti | Famiglie | Rifiuti positivi | Errati | P doc | R doc | F1 doc | P fam | R fam | F1 fam | Utile |
|---|---:|---:|---:|---:|---:|---|---|---|---|---|---|---|
| Development Round 3 | 162 | 58 | 0 | 92 | 0 | 100.00% (58/58) | 38.67% (58/150) | 55.77% (116/208) | n.d. (0 casi) | 0.00% (0/1) | 0.00% (0/1) | 38.67% (58/150) |
| Development Round 4 | 162 | 46 | 0 | 104 | 0 | 100.00% (46/46) | 30.67% (46/150) | 46.94% (92/196) | n.d. (0 casi) | 0.00% (0/1) | 0.00% (0/1) | 30.67% (46/150) |
| Holdout v1 storico originale | 177 | 33 | 0 | 89 | 5 | 86.84% (33/38) | 25.98% (33/127) | 40.00% (66/165) | n.d. (0 casi) | n.d. (0 casi) | n.d. (0 casi) | 25.98% (33/127) |
| Holdout v1 diagnostico Round 4 | 177 | 32 | 0 | 95 | 0 | 100.00% (32/32) | 25.20% (32/127) | 40.25% (64/159) | n.d. (0 casi) | n.d. (0 casi) | n.d. (0 casi) | 25.20% (32/127) |
| Holdout indipendente v2 | 92 | 2 | 0 | 15 | 0 | 100.00% (2/2) | 11.76% (2/17) | 21.05% (4/19) | n.d. (0 casi) | n.d. (0 casi) | n.d. (0 casi) | 11.76% (2/17) |
| Family v1 storico | 161 | 0 | 80 | 0 | 1 | n.d. (0 casi) | n.d. (0 casi) | n.d. (0 casi) | 98.77% (80/81) | 100.00% (80/80) | 99.38% (160/161) | 100.00% (80/80) |
| Family v3 fixture corretta | 161 | 0 | 80 | 0 | 0 | n.d. (0 casi) | n.d. (0 casi) | n.d. (0 casi) | 100.00% (80/80) | 100.00% (80/80) | 100.00% (160/160) | 100.00% (80/80) |

Il confronto development ripristina l’etichetta ausiliaria congelata `family_id=10` di OR2-101, omessa dall’helper diagnostico. Il report iniziale è conservato con hash; osservazioni, etichette originali documento/ente/versione e motore non cambiano e non si riesegue riconoscimento. Il recall famiglia resta correttamente 0/1.


## Cinque errori e R061

I cinque errori sono ora corretti o rifiutati prudentemente; dettagli, punteggi, runner e test in `../benchmarks/results/round4/false_acceptance_audit.md`. Vincoli generali: codice completo prima del titolo generico, titoli brevi solo in intestazione, peer annuali, sottotipi esclusivi, numero allegato. R061: FAMILY_MATCH errato → NO_MATCH; locked v2 68 →69/69. Locked v1 60 →59/69: la sua etichetta storica di R061 resta incompatibile col rifiuto corretto del v2; non viene sostituita.

## Famiglie

16 famiglie già verificate, nessuna aggiunta. Cinque positivi e cinque negativi sintetici per famiglia, più R061: 161 casi. Due emittenti sintetici per gli ambiti trasversali. Fallback isolato separato dall’end-to-end (nei raw): la precedenza del documento esatto non è un falso positivo di famiglia. V1 e v2 conservano FR01-N4 con emittente presente, erroneamente progettato come assente; il tentativo v2 di rimozione falliva per maiuscole/minuscole. V3 rimuove davvero quella riga, con motivazione e hash separati; nessuna etichetta cambia. Non si nasconde il 98,77% storico della v1.

V3: P/R/F1 100.00% (80/80) / 100.00% (80/80) / 100.00% (160/160); macro P/R/F1 1.0000/1.0000/1.0000; FP 0. Supplemento reale: 0/1, non indipendente. Le varianti sintetiche sono correlate; manca copertura reale per tutte le famiglie.

## Holdout v2

17 positivi, 75 negativi, 1 fonti positive, 1 enti; concentrazione massima 100.00%. Fonti: `{'giustizia': 17}`. Composizione: `{'formats': {'pdf': 17}, 'coded': 0, 'annual': 0, 'scanned': 14, 'title_limits': 'Metadata descriptive/generic classes not independently human adjudicated.'}`. Campione insufficiente e nessuna indipendenza strutturale completa dimostrata. Selezione metadati/SHA prima della lettura; URL canonici, hash, identità, codici/annualità e template territoriali esclusi rispetto a sviluppo e v1 storico. Stessa fonte è correlazione accettabile dichiarata, non prova di identità. Ricevute effettive; acquisizione opt-in, allowlist/robots e limiti, nessun bypass. Errori/tentativi in `holdout_v2_acquisition.json`.

Limite del runner di acquisizione: INAIL è stata chiusa prudenzialmente dopo il diniego robots di un singolo percorso. Questo riduce il campione e **non dimostra** che gli altri percorsi INAIL siano vietati o inaccessibili. Il prossimo ciclo deve distinguere dinieghi per percorso da blocchi di host prima di acquisire il nuovo v3. ADE: 403; INPS e Garante: tre risposte non documentali ciascuno; INL e una risorsa INAIL oltre 8 MiB; MIMIT residuo duplicato/escluso e un 404. Non vengono aggiunti file dopo la prima valutazione per migliorare questo risultato.

Positivi: 12 PDF digitali, 5 con OCR, 0 DOCX; 0 con codice e 0 annuali. Il campo raw `scanned` include anche i negativi (14 file totali), non soltanto i positivi. La composizione richiesta non è raggiunta.

Estrazione: 91/92. Matching condizionato: `{'numerator': 2, 'denominator': 17, 'value': 0.11764705882352941}`; end-to-end: `{'numerator': 2, 'denominator': 17, 'value': 0.11764705882352941}`. Gli errori di estrazione restano nei denominatori; nessun file problematico escluso dopo i risultati. Errori accettati 0 (esatti 0, famiglie 0); ente 0; versione 0. Precisione famiglia senza accettazioni è non definita, non 100%.

| Metrica | IC bootstrap 95% |
|---|---|
| document_precision | 100.00–100.00% |
| document_recall | 0.00–29.41% |
| family_precision | n.d. |
| family_recall | n.d. |
| useful_coverage | 0.00–29.41% |
| unknown_correct_rejection_rate | 100.00–100.00% |

10.000 repliche, seed 20261011, percentile per gruppi identità, descrittivo del campione; intervalli degeneri con zero errori non certificano il rischio reale. V2 fallito resta storico per il prossimo ciclo, che richiede un nuovo v3.

## Negativi e OCR

Sintetici v1 30/30, v2 100/100; ufficiali storici 50/50; nuovi 75/75. Tesseract reale `tesseract v5.4.0.20240606`, ita/eng/osd: legacy 7/7, raster sintetici v2 14/14, residui gate 0. Non equivalgono a scansioni ufficiali o validazione editoriale.

Scansioni ufficiali positive del nuovo holdout: 0/5 riconosciute esattamente; il solo uso di Tesseract non prova accuratezza del testo o della classificazione. Negativi nuovi: 74 estratti, 1 rifiutati per limite/errore di estrazione, sempre inclusi nell’end-to-end.

## Performance e memoria

| Motore | p50 ms | p95 ms | RSS caldo byte | Indici byte | Crescita RSS byte |
|---|---:|---:|---:|---:|---:|
| baseline | 80.6229 | 107.3568 | 30732288 | 0 | 217088 |
| round2 | 74.9871 | 102.5382 | 40271872 | 0 | 180224 |
| candidate | 101.1612 | 133.0268 | 45760512 | 1287273 | 978944 |

Rapporti baseline p50/p95 {'p50': 1.2547452398760153, 'p95': 1.2391092133893709}; caricamento catalogo 10.258 ms; costruzione indici 526.204 ms. Warmup 35, sei iterazioni alternate, 210 campioni/motore. RSS in processi separati, otto passaggi caldi; indici ricorsivi Python escludono cache legacy/native. Cache limitate ai metadati, nessun testo caricato. Riferimento full scan verificato sui corpus e tutte le 1.212 identità operative.

Il gate usa la misura alternata isolata; le latenze diagnostiche dei corpus development/storico sono state raccolte durante altri controlli e non sono un confronto prestazionale isolato.

## Test, CI e gate

584 passed, 0 failed, 3 skip; 605.49 s, Python 3.12.10, Windows. Skip: symlink senza privilegio e due FIFO. SQLite integrità ok/FK zero; 1.216 record conservati, 1.212 operativi, 10 demo, 16 famiglie, 19 fonti, 12 enti, 2.499 IPA, 1.078 osservazioni, zero sostituzioni. Nessuna nuova identità, revisione umana o provenienza inventata.

| Gate | Obiettivo | Risultato | Esito |
|---|---|---|---|
| unit_tests | 0 failed | {'passed': 584, 'failed': 0, 'skipped': 3, 'seconds': 605.49, 'python': '3.12.10', 'environment': 'Windows-11-10.0.26300-SP0', 'log_sha256': 'a760a3cd2be8c0f646f19f7ae8e4250cf6baa3e29e04fae7bd515b10590f9fd1', 'skip_reasons': ['Windows: symlink senza privilegio', 'Windows: due FIFO non disponibili']} | PASS |
| regression | 35/35 | 35 | PASS |
| locked_v2_R061 | 69/69 + R061 NO_MATCH | 69 | PASS |
| five_historical_fixes | 5 safe | 5 | PASS |
| all_historical_wrong_accepts | 0 | 0 | PASS |
| development_wrong_accepts | 0 | 0 | PASS |
| development_recall_regression | >= Round 3 58/150 | 46 | FAIL |
| family_stress_precision | >=99.5%, macro>=99%, FP=0 | {'P': {'numerator': 80, 'denominator': 80, 'value': 1.0}, 'macro': 1.0, 'FP': 0} | PASS |
| family_real_evidence | available official supplement measured | {'passed': 0, 'cases': 1} | PASS |
| positive_sample | >=200 | 17 | FAIL |
| negative_sample | >=75 | 75 | PASS |
| positive_sources | >=8 | 1 | FAIL |
| positive_issuers | >=8 | 1 | FAIL |
| source_concentration | <=20% | 1.0 | FAIL |
| positive_formats | PDF text, scanned PDF, DOCX | {'formats': {'pdf': 17}, 'scanned': 5} | FAIL |
| positive_code_year_mix | coded/uncoded + annual/nonannual | {'coded': 0, 'annual': 0, 'total': 17} | FAIL |
| leakage | 0 prohibited overlaps | True | PASS |
| holdout_document_precision | >=99.5% | {'numerator': 2, 'denominator': 2, 'value': 1.0} | PASS |
| holdout_family_precision | >=99.5% | {'numerator': 0, 'denominator': 0, 'value': None} | FAIL |
| holdout_document_recall | >=75.0% | {'numerator': 2, 'denominator': 17, 'value': 0.11764705882352941} | FAIL |
| holdout_useful_coverage | >=90.0% | {'numerator': 2, 'denominator': 17, 'value': 0.11764705882352941} | FAIL |
| holdout_wrong_accepts | 0 | 0 | PASS |
| holdout_entity_error_rate | 0 | 0 | PASS |
| holdout_version_year_error_rate | 0 | 0 | PASS |
| hard_negatives_synthetic | 100/100 | 100 | PASS |
| hard_negatives_official_v1 | 50/50 | 50 | PASS |
| hard_negatives_official_v2 | 75/75 | 75 | PASS |
| real_ocr | 7/7 +14/14 | {'legacy': 7, 'v2': 14} | PASS |
| latency | p50,p95 <=1.5x | {'p50': 1.2547452398760153, 'p95': 1.2391092133893709} | PASS |
| catalog_integrity | integrity ok; FK=0; catalog unchanged | ok | PASS |

CI esterna Linux/Windows/macOS Python 3.12: `pending_external_gate`, non eseguita. Comandi equivalenti offline verificati localmente; nessun push.

```text
python -m pytest -q
$env:BUROCRAZIA_DB_PATH="tmp-build/temporary-ci.sqlite3"
python scripts/init_db.py
Remove-Item Env:BUROCRAZIA_DB_PATH
python scripts/verify_catalog.py --db data/catalog_seed.sqlite3
python scripts/benchmark.py --output benchmark-results.json
python -m compileall -q src maintenance benchmarks app.py run.py
python -m benchmarks.evaluate --fast --output-dir benchmark-release-results
```

## Limiti residui

Copertura reale insufficiente e ridotta rispetto a Round 3 per i vincoli prudenti sugli emittenti/anni; cluster completi in `development_rejection_clusters.json`. Mancano riscontri robusti per titoli, codici, annualità o emittenti di molti file. Profili tecnici derivati da sviluppo non provano indipendenza né verifica editoriale. Il campione nuovo non raggiunge fonti/dimensione/concentrazione e non rappresenta adeguatamente tutti i formati e scansioni. Famiglie reali poco rappresentate; nessuna attribuzione automatica di nuove famiglie verificate. Etichette congelate da elenchi possono essere incoerenti col file e richiedono revisione separata. Versione software 0.6.1, espansione sospesa.
