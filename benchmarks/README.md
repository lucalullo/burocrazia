# Valutazioni riproducibili

Round 3: i file ufficiali v2 sono **official_development_v2**, già usati per sviluppare il motore; locked v1 è storico immutabile e locked v2 è sviluppo riconciliato. Nessuno dei due è un gate indipendente. La prima misura `official_holdout_v1` richiede un runtime congelato prima dell'acquisizione e non è rieseguibile per migliorare i risultati.

```powershell
python -m pytest -q
python scripts/verify_catalog.py
python -m benchmarks.evaluate --coverage --output-dir benchmarks/results/round3/final
python -m benchmarks.evaluate --fast --output-dir tmp-build/release-fast
python -m benchmarks.files ocr --manifest benchmarks/corpora/ocr_synthetic_v2.json --output benchmarks/results/round3/ocr_synthetic_v2.json
python -m benchmarks.ocr_gate --output benchmarks/results/round3/ocr_legacy_gate.json
python -m benchmarks.round3_performance
python scripts/release_report.py
```

Il development e il generatore feature richiedono la cache locale verificata dei file congelati, che non è redistribuita. `round3_audit` descrive il motore Round 2 iniziale; per riprodurlo occorre quel checkout, senza sovrascrivere l'audit baseline con risultati del motore nuovo. `build_recognition_features` produce solo otto token tecnici per profilo, URL/hash/data e fingerprint catalogo; nessuna verifica editoriale viene attribuita.

Protocollo holdout: `python -m benchmarks.round3_holdout plan`, poi `freeze`, poi `acquire --allow-network`, infine **una sola volta** `evaluate`. Il freeze e la prima valutazione non possono essere sovrascritti. Il controllo automatico esclude hash, URL, identità, codici/versioni e template equivalenti; le etichette provengono dagli elenchi ufficiali, non dal risultato del motore. Errori di acquisizione e obiettivi non raggiunti restano nei report; errori di estrazione del manifest restano nel denominatore. Qualunque correzione successiva richiede un nuovo ciclo e un nuovo holdout.

La CI fast è offline: regressione, locked v2 e hard negatives devono passare, locked v1 viene comunque riportato. OCR completo è un workflow manuale separato. La CI remota non è stata eseguita: `pending_external_gate`. I report per fonte/formato/metodo/OCR e IC95% sono nei raw Round 3; vedere `docs/BENCHMARK.md` per le nove categorie, le metriche e i limiti.

```powershell
python -m benchmarks.evaluate --coverage
python -m benchmarks.evaluate --fast
python -m benchmarks.files ocr --output benchmarks/results/ocr_synthetic_v1.json
python -m benchmarks.files official --output benchmarks/results/official_documents_v1.json
```

I test testuali sono offline. Il runner ufficiale riusa una cache con receipt e hash; `--allow-network` abilita esplicitamente l'acquisizione controllata. L'OCR richiede Tesseract reale: nessun mock viene conteggiato come prova OCR. Un exit code non zero conserva comunque i risultati e segnala errori, casi non passati o esecuzione incompleta.

- `development_regression.json`: 35 casi pubblici originari, byte invariati; regressione di sviluppo.
- `release_locked_v1.json`: 69 casi sintetici pubblici congelati prima delle modifiche alle regole. Non è una valutazione indipendente; contiene casi generici e due attese di famiglia per testi che identificano anche documenti specifici. Le etichette restano congelate e gli errori sono riportati. Le famiglie possono sovrapporsi alla regressione: la separazione dei gruppi documentali non dimostra indipendenza fra famiglie.
- `hard_negatives_v1.json`: 30 negativi sintetici difficili, distinti dalla regressione.
- copertura canonica: una prova per ogni identità reale non rifiutata, derivata dai metadati; non misura scansioni o generalizzazione.
- `ocr_synthetic_v1.json`: 12 immagini/PDF riproducibili senza dati personali; orientamenti, contrasto, blur, JPEG, crop, scale e piccoli errori testuali. La riproducibilità dei raster dipende dalle versioni Pillow/MuPDF registrate.
- `official_documents_v1.json`: nove PDF reali, campione di convenienza per fonte; URL, identità attesa, hash effettivo e data. File non redistribuiti. Gli errori di acquisizione/estrazione sono negli `attempts`, esclusi dai denominatori del solo matching.

Gli hash sono in `manifests/*locks_v1.json`. Per correggere un'etichetta serve un corpus nuovo con motivazione. I risultati raw includono confusion matrix, numeratori/denominatori, breakdown per fonte/categoria/rumore, bootstrap per gruppi, latenza, ambiente e impronte. Il bootstrap è descrittivo: zero errori in un piccolo corpus pubblico non dimostra un rischio reale nullo. Latenza di matching e tempi di estrazione/acquisizione sono separati.

`latest_summary.json` è un artefatto statico di sola lettura nell'app. Il caricamento non lancia test e segnala quando il catalogo locale differisce da quello misurato. Risultati e limiti sono in `docs/BENCHMARK.md`. La candidata resta non pronta finché i gate riportati in `docs/release_gates.json` non sono tutti dimostrati.
