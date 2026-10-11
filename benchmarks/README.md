# Valutazioni riproducibili

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
