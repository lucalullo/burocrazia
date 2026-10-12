# Benchmark Round 7 — NOT READY

<!-- round7-current-start -->
Stato corrente: **NOT READY**. Copertura con file 81.26%; canonical 979/979; nuova robustness 183/372 (49.19%), scansioni 134/280 (47.86%), AcroForm generati 9/50 (41 fallimenti). p95 444.65 ms; 690 test passati e 3 saltati. Il [rapporto Round 7](ROUND7_REPORT.md) contiene i gate correnti, i raw v3 e i limiti. CI esterna pending_external_gate.

## Archivio Round 6 — ora development

Le sezioni numerate seguenti conservano la misura storica Round 6, con i suoi hash e denominatori. Non descrivono il comportamento corrente; il riepilogo Round 7 è anche in fondo a questo documento.
<!-- round7-current-end -->

## Stato, versione e prove

Software **0.6.1**, target **0.7.0**, schema **610**. Branch `codex/coverage-benchmark-v0.7.0`.
Commit di congelamento runtime/calibrazione **`ce6fa61f432c204e3d4c8029ef370ff27e429455`**; HEAD alla generazione `1e922eaa5b81d7a6c1cafccdac4c66e376226683`.
Il runtime e il profilo sono invariati dopo l'apertura dell'evaluation. Gli hash dei byte identificano ciascuna misura;
nessun push, tag o rilascio. Runtime SHA `4c59473be34e313b119e45bca42f483ed43ffc37858a16920727a88083a10f08`; bundle v2 SHA `1e8771912268b4e46cd564d6b35ad7fd137d354ab365ae2f02751b2d37c10073`.
Baseline: 615 passed, 3 skip; dati storici v1 e Round 5 conservati, senza sostituire metriche o etichette.

## 1. Catalog coverage

1.216 reali, 1.212 operativi, quattro rifiutati; **zero nuove identità**. Seed SHA `790b690123c82e1cb7bdfa67a10216284022987d50b0abbcc4a1a245785e3e99`,
integrity/FK OK e provenienze 1.216/1.216. Nessuna nuova verifica editoriale.
Copertura da soli metadati: 1169/1212, distinta dal riconoscimento di file reali.

## 2. Fingerprint coverage

File-backed 1158; firme attive per 948 identità;
copertura totale 78.22%, file-backed 81.87%.
Risorse canoniche 1015, attive 987, in quarantena 28.
Servizi dinamici 0; metadata-only 54.
Denominatore: A declared download remains file-backed despite 403/404, unsupported .doc, extraction failure or shared bytes. Detail-only records become file-backed only after an actual supported attachment. No failed fetch is reclassified as a service.

| Fonte | Operativi | File-backed | Fingerprinted identities |
|---|---:|---:|---:|
| inps | 359 | 359 | 351 |
| inail | 347 | 347 | 308 |
| ade | 122 | 90 | 0 |
| lavoro | 102 | 102 | 74 |
| mimit | 42 | 42 | 25 |
| funzione_pubblica | 9 | 9 | 8 |
| garante_privacy | 17 | 10 | 4 |
| inl | 46 | 45 | 43 |
| giustizia | 142 | 142 | 126 |
| mef | 15 | 1 | 1 |
| anac | 7 | 7 | 7 |
| unioncamere | 4 | 4 | 1 |

Assenze: `{"shared_resource": 26, "unsupported_mime": 34, "source_changed": 19, "robots_or_policy_block": 127, "detail_page_only": 27, "extraction_failure": 24, "http_404": 1, "download_url_html": 6}`.
I CSV contengono le 843 assenze iniziali, le assenze finali e tutti gli stati tecnici.
Nuove firme tra le assenze v1: 582; firme v1 conservate attive anche in v2: 366.
Identità v1 escluse dalla v2 attiva: `[152, 536, 921]`; motivi tecnici nel CSV final. Il bundle v1 resta invariato.
669 richieste sequenziali complessive, robots/allowlist/redirect verificati; nessun bypass.
Multipart INPS: derivazione MIME tracciata con hash del contenitore e del payload.
Formati e lingue alternativi provengono dalle osservazioni immutabili già associate alle identità.

## 3. Canonical exact-file recognition

| Prova | N | Exact | Family | NO | Wrong | Precision | Exact recall |
|---|---:|---:|---:|---:|---:|---|---|
| Canonical exact-file | 987 | 987 | 0 | 0 | 0 | 100.00% (987/987) | 100.00% (987/987) |
| Robustness evaluation | 192 | 150 | 0 | 42 | 0 | 100.00% (150/150) | 78.12% (150/192) |
| Interactive AcroForms (5 templates) | 100 | 100 | 0 | 0 | 0 | 100.00% (100/100) | 100.00% (100/100) |
| Static overlays (weaker perturbation) | 70 | 70 | 0 | 0 | 0 | 100.00% (70/70) | 100.00% (70/70) |
| Scan/OCR | 168 | 128 | 0 | 40 | 0 | 100.00% (128/128) | 76.19% (128/168) |

Canonical misura ogni risorsa attiva, comprese alternative della stessa identità; non generalizzazione a identità sconosciute.
Subset cross-format: 22/22 risorse PDF/DOCX di 11 identità;
prova SHA dei file canonici, senza claim di generalizzazione scan cross-format DOCX.
I sette NO Round 5 hanno cause contestuali documentate in `canonical_failures.csv`:
anno del comunicato/competenza, anno della delibera/contributo, data di revisione, COMUNE come campo e qualificatori nel corpo.
Le correzioni sono generali; nessuna whitelist di ID o bypass di conflitti espliciti di ente/versione.
Risorse in conflitto sono escluse tecnicamente e conservate nell'audit, senza revoche editoriali.

## 4. Robustness recognition

Calibration identities: `[1055, 681, 403, 345, 661, 405, 507, 28]`. Evaluation identities: `[109, 120, 149, 159, 550, 546, 586, 591, 610, 166, 615, 601]`.
Split e SHA delle risorse congelati prima delle rappresentazioni. Soglie/pesi tarati solo sulle identità di calibration;
il profilo congelato e lo SHA runtime sono verificati prima dell'evaluation. Nessuna ritara dopo i risultati.
La prima taratura e il relativo profilo sono conservati in `calibration_initial/`:
prima di aprire evaluation sono state ampliate le soglie di containment caratteri (pagina singola contro documento intero)
e corretto il veto della revisione mancante nel fallback metadata. La revisione finale usa ancora soltanto gli otto ID calibration.
Soglie finali: text 0,75, char containment 0,15, anchors 0,60, visual 0,88, margine 0,02,
almeno 20 sovrapposizioni. Pesi 0,50/0,25/0,15/0,10. L'obiettivo della griglia dà 116/128 corretti
e zero wrong **prima dei veto di sicurezza**; non è un richiamo osservato end-to-end di 116/128.
Le fingerprints delle identità evaluation esistono: prova di rappresentazione dello stesso documento, non identity holdout.

| Trasformazione | N | Exact correct | Precision | Recall |
|---|---:|---:|---|---|
| digital_exact | 12 | 12 | 100.00% (12/12) | 100.00% (12/12) |
| raster_200 | 12 | 9 | 100.00% (9/9) | 75.00% (9/12) |
| raster_150 | 12 | 10 | 100.00% (10/10) | 83.33% (10/12) |
| jpeg_90 | 12 | 10 | 100.00% (10/10) | 83.33% (10/12) |
| jpeg_75 | 12 | 9 | 100.00% (9/9) | 75.00% (9/12) |
| jpeg_60 | 12 | 9 | 100.00% (9/9) | 75.00% (9/12) |
| grayscale | 12 | 10 | 100.00% (10/10) | 83.33% (10/12) |
| contrast_minus20 | 12 | 8 | 100.00% (8/8) | 66.67% (8/12) |
| blur_mild | 12 | 9 | 100.00% (9/9) | 75.00% (9/12) |
| crop_2pct | 12 | 8 | 100.00% (8/8) | 66.67% (8/12) |
| crop_5pct | 12 | 8 | 100.00% (8/8) | 66.67% (8/12) |
| resize_075 | 12 | 8 | 100.00% (8/8) | 66.67% (8/12) |
| first_page_only | 12 | 10 | 100.00% (10/10) | 83.33% (10/12) |
| rotation_90 | 12 | 10 | 100.00% (10/10) | 83.33% (10/12) |
| rotation_180 | 12 | 10 | 100.00% (10/10) | 83.33% (10/12) |
| rotation_270 | 12 | 10 | 100.00% (10/10) | 83.33% (10/12) |

Candidate retrieval@K: `{"1": {"numerator": 192, "denominator": 192}, "5": {"numerator": 192, "denominator": 192}, "10": {"numerator": 192, "denominator": 192}, "25": {"numerator": 192, "denominator": 192}}`.
Il ranking diagnostico non applica SHA né veto; il runtime conserva tutti i candidati con evidenza minima.
`rejection_diagnostics.json` distingue fusion insufficiente da candidati eleggibili poi rifiutati;
un motivo generico non viene attribuito arbitrariamente a un particolare veto.
`evaluation_locks.json` verifica a posteriori l'uguaglianza dei byte col commit di congelamento,
senza inventare un evento di lock precedente. Il pacchetto controlla anche questi hash.
Expected fuori top25 indica un problema di recupero; dentro top25 e NO indica scoring/veto/margine.
Righe di scoring diagnostico limitate a top25, rank atteso calcolato sull'intera lista.
Il seed del helper storico nei metadati dei casi è riconciliato con il piano Round6 (20261012);
il valore ereditato 20261011 è conservato separatamente. Nessuna osservazione, etichetta o metrica è cambiata.
Runner scansioni con tre worker disgiunti e `OMP_THREAD_LIMIT=1`; ordine finale deterministico.

## 5. Filled-form robustness

170 casi totali: **100 AcroForm reali su cinque template**, venti varianti ciascuno;
**70 overlay statici**, dieci varianti su sette risorse. Gli overlay includono documenti non compilabili e sono
perturbazioni di contenuto più deboli: non costituiscono 70 moduli compilati. Il gate usa separatamente i 100 AcroForm.
La matrice originale 120 casi è conservata; un supplemento di 50 AcroForm è pianificato prima della generazione,
selezionando tutti i cinque template evaluation con campi presenti, senza cambiare soglie o consultare esiti per selezionarli.
Il generatore usa nomi, CF non validi, indirizzi, date, importi, testo e checkbox sintetici quando i campi sono identificabili.
Casi correlati entro template.
Le verifiche richiedono `/V` nel field tree, valore del widget e appearance riaperta;
ambiguità/orfani non riparati automaticamente. Campi sintetici non costituiscono compilazione legale.
Quando il nome del campo è generico, il filler usa `EsempioN`: la prova dimostra la modifica di campi reali,
senza garantire plausibilità semantica o correttezza di date/CF in tutti i campi. Questo limite resta aperto.
Dipendenza facoltativa del benchmark: `pypdf==6.10.0` in `benchmarks/requirements-round6.txt`, non importata dal runtime.

## 6. Scan/OCR robustness

168 scansioni generate; OCR estratto con successo 168.
Exact recall 76.19% (128/168); useful recall 76.19% (128/168).
Ogni errore di estrazione resta nel denominatore. Prime pagine PDF a 150/200 dpi, JPEG, crop, blur,
contrasto, resize e rotazioni. Non sono scansioni reali di utenti, manoscritti o foto da telefono.
OCR canonico: prima pagina PDF 144 dpi, stesso Tesseract/lingue del runtime, senza persistere testo o immagini.
DOCX: canale digitale; renderer locale non disponibile, nessun claim OCR/visual o scan cross-format per DOCX.

## 7. Family identity-holdout

16 famiglie totali; 0 valutabili. Held-out reali osservati in via esplorativa:
2; casi con numerosità release-grade 0.
Identità held-out esplorative: `[167, 143]`;
split per tutte le 16 famiglie in `family_evaluability.csv` e `family_release.json`.
Nel solo subset esplorativo: 1/2 corretti,
recall 50.00% (1/2); non confluisce nelle macro release-grade.
Precision n.d., recall n.d.,
macro `{'family_precision': None, 'family_recall': None, 'family_f1': None}`, false accepts 0.
Capability `not_sufficiently_validated`; meno di cinque famiglie non blocca la RC known-document, ma non valida family.
Nessuna nuova frase imparata dalle identità held-out. Hard negatives sintetici famiglia separati: 81,
0 false accept; non sostituiscono file ufficiali di identità nuove.

## 8. Unknown official rejection

137 SHA ufficiali storici distinti, 137 NO,
0 accettazioni erronee; rifiuto corretto 100.00% (137/137).
Tutti i negativi storici conservati. Zero ulteriori unknown non visti: la cache aggiuntiva contiene risorse di identità note
o file privi di etichette unknown adjudicate; non si assegnano etichette negative automaticamente dal titolo.

## 9. Historical regressions

Regressione storica immutata **33/35**: EX02/EX03 ora NO perché
non esplicitano revisione 1.1; il gate storico stretto resta FAIL. Nuova fixture di sviluppo `tests/fixtures/benchmark_v2.json`
**37/37**: revisioni aggiunte a due nuovi input positivi, testi originali mantenuti in due nuovi negativi,
parent SHA e motivazioni nel file. Non sostituisce il 33/35 storico e non è evaluation indipendente.
Locked v2 69/69;
locked v1 storico 59/69, senza sostituzione delle etichette.
Negativi storici 130/130; R061 NO_MATCH; cinque false accettazioni storiche sicure 5/5.
OCR reale storico 7/7 e sintetico 14/14; test mock, OCR reale ed editoria restano distinti.

## 10. Performance

Startup catalogo 9.88 ms, indice 1667.57 ms;
warm p50 112.96 ms, p95 799.11 ms,
306 campioni, 35 sintetici + 16 file ufficiali.
Inferenza warm esclude estrazione/OCR e generazione visual, misurati separatamente per caso.
Il p95 Round 5 era 128,16 ms: il nuovo indice aumenta copertura ma questa misura Round 6 peggiora la coda
oltre il limite. Non viene presentato come ottimizzazione prestazionale conclusa.
Ambiente Windows-11-10.0.26300-SP0, Python 3.12.10; nessuna certificazione Linux/macOS.

## 11. Memory, test, CI e gate

Bundle v2 27182244 byte; indice 39852804 byte.
RSS dopo warm 286887936 byte; crescita warm 45056 byte.
Array, posting e pesi IDF sono nella misura ricorsiva Python; RSS dell'intero processo è separato.
V1 resta su disco per compatibilità/storico e non viene caricata nel percorso v2 operativo.
Nessun upload o suo sketch viene conservato in cache.

Test completi: 655 passed, 0 failed, 3 skip Windows,
581.88 s. Migrazioni ripetute su copie di v0.6.1, Round4 e Round5, integrity/FK;
Primo tentativo finale: 650 passed, quattro failed, tre skip (613,79 s), log/hash conservati.
Le quattro asserzioni dipendevano dai due input storici senza revisione e dal test storico SR211;
risolte con fixture v2 e revisione esplicita nel test dello storico editoriale, senza indebolire il runtime congelato.
schema invariato 610. Bootstrap/CLI/benchmark locali documentati in `ci_local.json`.
Sottoinsiemi ripetuti dopo gli ultimi aggiornamenti: 7 test CLI/protezione fixture;
71 test UI/fingerprint dopo il nuovo riepilogo statico. Non sono nuovi test aggiunti al totale 655.
CI esterna **pending_external_gate**: anche READY LOCALLY consentirebbe solo RC locale.
Il comando storico `benchmarks.evaluate --fast` termina con codice 1 per EX02/EX03;
il wrapper di riproduzione conserva quel FAIL e verifica che siano gli unici due rifiuti aggiunti prima delle altre prove.
La CLI corrente sulla fixture di sviluppo v2 passa; non rende verde il gate storico.
Il primo lancio del wrapper performance non ha scritto risultati perché un avviso PDF nativo contaminava stdout;
è stata corretta soltanto la lettura della singola riga JSON e ripetuta la misura isolata, senza cambiare il protocollo.

| Gate | Target | Risultato | Esito | Bloccante |
|---|---|---|---|---|
| coverage_file_backed | >=85% | 0.8186528497409327 | FAIL | sì |
| coverage_all | >=70% | 0.7821782178217822 | PASS | sì |
| canonical_precision | 100% | 1.0 | PASS | sì |
| canonical_recall | 100% | 1.0 | PASS | sì |
| canonical_wrong | 0 | 0 | PASS | sì |
| robustness_precision | >=99.5% | 1.0 | PASS | sì |
| robustness_exact_recall | >=90% | 0.78125 | FAIL | sì |
| filled_acroform_precision | >=99.5% | 1.0 | PASS | sì |
| filled_acroform_exact_recall | >=90% | 1.0 | PASS | sì |
| scan_precision | >=99.5% | 1.0 | PASS | sì |
| scan_exact_recall | >=85% | 0.7619047619047619 | FAIL | sì |
| scan_useful_recall | >=95% | 0.7619047619047619 | FAIL | sì |
| family_capability_validation | >=5 evaluable families | 0 | FAIL | no |
| unknown_rejection | >=99% | 1.0 | PASS | sì |
| R061 | NO_MATCH | NO_MATCH | PASS | sì |
| historical_five | 5 safe | 5 | PASS | sì |
| historical_negatives | 130/130 | 130 | PASS | sì |
| historical_family_negatives | 0 false accepts | 0 | PASS | sì |
| historical_development_regression | 35/35 unchanged labels | 33 | FAIL | sì |
| development_compat_v2 | 37/37 new representations | 37 | PASS | sì |
| real_ocr | 7/7 +14/14 | {'legacy': 7, 'synthetic': 14} | PASS | sì |
| warm_p95 | <=250ms | 799.1129 | FAIL | sì |
| warm_p50 | <=150ms | 112.9562 | PASS | sì |
| index_memory | <=100MB | 39852804 | PASS | sì |
| tests | 0 failures | 655 | PASS | sì |
| unchanged_catalog | 1216 identities, same seed SHA | 790b690123c82e1cb7bdfa67a10216284022987d50b0abbcc4a1a245785e3e99 | PASS | sì |

Limiti: OCR/visual solo prima pagina PDF; DOCX senza renderer; scansioni e dati compilati sintetici;
unknown e family non sono una nuova prova prospettica; fonti bloccate/legacy non aggirate;
nessuna nuova revisione editoriale o nuova spiegazione. Le metriche non sono una probabilità né un consiglio personalizzato.

Archivio locale: `dist/BurOCRazia-v0.7.0-candidate-NOT-READY-round6.zip`.
SHA256 e verifica byte/lock/hygiene in `dist/package-verification.json` e nel file `.zip.sha256`,
generati dopo il commit per evitare riferimenti circolari. Nessun cache ufficiale, database personale o documento di terzi nello ZIP.

## Round 7 — NOT READY

Decision policy v3, retrieval v2 e nuova evaluation dopo freeze: 372 tentativi, 331 rappresentazioni generate su 42 identità, 280 scan-like, 9/50 AcroForm generati (41 fallimenti). Copertura 77.64% totale e 81.26% con file; canonical 979/979; richiamo robustness 49.19%, scansioni 47.86%, compilati 14.00% sul piano completo. Rifiuto unknown storico 100.00%; famiglie 0/16 valutabili, capacità non sufficientemente validata. p95 444.65 ms; indice 39832045 byte. Precisione exact 100% sui match emessi. La QA dei compilati mostra errori semantici e testo tagliato: nessuna validità amministrativa o qualità finale dei moduli rivendicata.

R6 ora development; v3 una sola esecuzione, senza retuning. 690 test passati, 3 saltati. CI esterna pending_external_gate. Software 0.6.1, schema 610 e catalogo di 1216 documenti preservati. Report e limiti: [ROUND7_REPORT.md](ROUND7_REPORT.md).


Coverage, canonical, robustness, filled, scan/OCR, family, unknown e regressioni sono metriche separate. V1/v2 raw e label restano visibili; R6 evaluation è development, v3 è il solo nuovo test di rappresentazioni. Unknown è storico/calibrato, non indipendente. I gate non vengono ridefiniti quando falliscono.
