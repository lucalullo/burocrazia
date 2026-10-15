# Round 19 — NOT READY

Versione software **0.6.1**, pubblico 0.6.1, schema 610. Branch `codex/coverage-benchmark-v0.7.0`; ingresso `b3bd9cc61c6af15e8b3ad9958d6e40dcf34a683b`, freeze candidato **`aa816782b075c8a27eabb7492d080d1c26fa3119`** riusato. Commit finale e SHA256 ZIP nel verificatore esterno `dist/package-verification-round19.json`. CI **external pending**. Nessun push, tag o pubblicazione.

## Integrità e contaminazione

Runtime `8f8a50c679a399623b9bd3964fba090d95b36608cd46e2f149f4752fd3169890`, fingerprint `eaac87ac81e03ba838b52d66992db20967e8c50bbcfd88b02d894c42ab68f4bd`, decision policy `a482397a0f3b2a882fd20cb7ac0af2d19bde69ed7f105da9b7443b2fdb5edcfe`. Motore, catalogo completo, ranking, soglie, policy, truth e dataset immutati dal freeze. Inventario benchmark Round 19 separato in benchmark_seal.json, senza riscrivere il freeze Round 18. Unknown v3 conservato byte per byte: 116/116, 13 fonti, 25% concentrazione, 0 DOCUMENT/FAMILY false accept; risultato SHA `7db456992deb5f477a944745a981b811be9a38b15e86f1020140ccae87d8c77b`, manifest e raw invariati, nessun replay o relabel. Wilson95% [96.7945%,100%] descrive quel campione; il confidence score non è una probabilità.

Audit di 1.019 identità con record fingerprint, una riga per ID, inclusi record non utilizzabili esplicitamente segnalati. Le identità usate in tuning e le storie dirette non risolte restano escluse. Evaluation storica, source_seen e profili source-specific sono distinti; la firma canonica è parte del prodotto. Registry v3 e tutte le prove legacy restano integri nella v4. Politica documentata prima della selezione in ROUND19_CONTAMINATION_AUDIT.md. Il pool Round 18 aveva 351 ID/352 record/5 fonti; il nuovo pool ha **359 ID/6 fonti**, conteggi `{'2': 197, '3': 137, '5': 6, '14': 3, '16': 15, '19': 1}`. Ragioni per ogni esclusione e fonte in CSV/round18_pool_diagnostics.json. Source è il source_id storico catalogo/provenienza: nessuna divisione per hostname, ente o pagina; gate 6 invariato.

Recuperate 8 identità: 286,360,616,684,989,990,994,1212. La sesta fonte è Unioncamere, ID 616, presente nel piano/generazione R8 ma non nelle 50 osservazioni né nel tuning Round 8/9. Il vecchio filtro accostava il suo titolo generico ad ANAC 611 senza emittente comune. Correzione audit prima di selezione/predizioni, primo diagnostico e hash preservati. Rimangono prudenziali le esclusioni per risorsa, campi, aggregate e titoli/codici/versioni dello stesso emittente. Nessun documento/fingerprint aggiunto.

## Preflight, selezione e rappresentazioni

Capacità iniziale teorica nel pool: 359 identità, 6 fonti, 5510 rappresentazioni, 4732 scansioni, 60 compilati, 116 unknown disponibili. Questa capacità non rivendica compilati validi prima della generazione.
Seconda barriera effettiva prima delle predizioni: 38 identità/6 fonti/635 noti/504 scan/55 compilati validi/30 unknown; PASS, generazione 91.6667%.

Selezione fissa seed 2026101419, solo metadata/hash, stratificata per fonte/ID/codice/versione/pagine/formato. 38 identità/6 fonti; source counts `{'2': 10, '3': 10, '5': 6, '14': 1, '16': 10, '19': 1}`, concentrazione massima 26.3158%, limite prospettico 35% (preferito 30%). Target 50 con max10/source e max2DOCX, slot riservati alle fonti disponibili solo DOCX:38 effettive, oltre minimo 30; il preferito 40–50 non raggiunto. Garante e Unioncamere hanno una sola identità selezionata ciascuno: diversità minima ammessa, non robusta generalizzazione alla fonte.

635 rappresentazioni note: 76 derivati digitali strutturali/normalizzati, 504 scan-like con 200/150DPI,grigio,JPEG,blur,contrasto,crop,prima pagina e rotazioni; 55 compilati validi su 60 tentativi,91.6667% generazione. Cinque overlay del documento 470 falliti per assenza di rettangoli liberi, conservati nel denominatore; nessuna sostituzione. Scansioni sintetiche da pagine canoniche con Tesseract reale, non scansioni personali. Novità effettiva dei pixel (0.05%,intensità±2) da seed per caso; compilazione con valori sintetici nuovi e seed registrati. Nessuna novità rivendicata soltanto per metadata/ID. Controlli SHA e chiavi di trasformazione storiche, 0 leakage proibito, 0 duplicati,truth non ambigua nel contratto canonico. CaseJournal SQLite con checkpoint/resume stesso freeze+manifest+inventario, schema/count/ID/SHA finali; una sola esecuzione, nessun tuning dopo gli esiti.

## V5 single-shot

|Gruppo|N|Exact|Family|NO|Wrong|Precisione|Recall|F1|Errori ente|Errori versione|
|---|---|---|---|---|---|---|---|---|---|---|
| robustness_v5 | 635 | 448 | 0 | 179 | 8 | 98.2456% | 70.5512% | 82.1265% | 0 | 0 |
| scan_v5 | 504 | 319 | 0 | 179 | 6 | 98.1538% | 63.2937% | 76.9602% | 0 | 0 |
| filled_v5 | 55 | 55 | 0 | 0 | 0 | 100.0000% | 100.0000% | 100.0000% | 0 | 0 |
| end_to_end_v5 | 665 | 448 | 0 | 209 | 8 | 98.2456% | 70.5512% | 82.1265% | 0 | 0 |

Otto identità errate restano tali: 469→511 in un crop 5%, 470→512 in sette rappresentazioni, incluse entrambe le digitali. Un candidato atteso fuori dalla top25: 802/rotation180. Nessuna riclassificazione retrospettiva come ambiguità e nessun cambiamento delle aspettative; dettagli in failure_diagnostics.json.

Retrieval@1/@5/@10/@25: `{'1': 0.9905511811023622, '10': 0.9984251968503937, '25': 0.9984251968503937, '5': 0.9984251968503937}`. Unknown mix: `{'n': 30, 'exact': 0, 'family': 0, 'reject': 30, 'wrong': 0, 'entity_errors': 0, 'version_errors': 0, 'extraction_failed': 0}`; 30 risorse dal v3 già congelato, verifica end-to-end sullo stesso freeze, non un nuovo campione indipendente. Family resta **experimental / insufficiently validated**, non aumenta exact recall. Ogni FAMILY su unknown è false acceptance. Metriche per fonte/profilo/trasformazione in evaluation_v5_breakdown.json; tutte le osservazioni grezze e i fallimenti restano conservati.

## Validazione finale

Coverage 1002/1158=86.528497%, canonici 980+27=1007/1007. Safety 241 NO sintetici, ANAC e cinque critici storici sicuri;9/9 input safety. Equivalenza corrente 1.563 firme complete/0 differenze rispetto al Round 18, incluse decisioni/score/reason/ente/versione/top25. Nuova verifica effettiva dopo V5 di canonici/equivalenza/input safety in post_v5_validation.json e relativi raw separati; nessun replay di unknown v3 o V5. Sono contratti tecnici e diagnostici, non validazione editoriale o generalizzazione a identità sconosciute.

|Run|p50 ms|p95 ms|
|---|---|---|
|1|55.6425|257.9318|
|2|48.2199|212.5373|
|3|31.6987|135.3276|
|4|50.3489|198.6201|
|5|58.8513|256.7781|
|6|44.8587|174.4674|
|7|53.8106|190.7983|

Mediana p95 **198.6201 ms**, gate<=250 **True**, sette run fissati prima della misura/2.814 richieste, suite 67 input, nessuna ottimizzazione o selezione di rerun. Baseline Round 18 234.4921ms preservata separatamente. Estrazione/OCR fuori timing warm; cache solo catalogo, RequestPages nuova per richiesta. Windows/Python3.12.10, nessun collaudo Linux/macOS o su altri computer.

Pytest finale **834 passed/0 failed/3 skipped**, 624.51s, log SHA `a0e9371aef45989386b353c3f4963c3d5bdf7f6ccdb6ba43d9a02cc9307a647d`. Compile, SQLite integrity/FK, migrazione idempotente610/conteggi invariati, validatori fingerprint 1/2/3, truth/schema, compat-v2 e package verificati. Release-gate-fast 1258/1258 exit 0; historical-regression-fast 1517/15 mismatch exit 1 atteso e preservato: 2 EX02/EX03 INPS revisione mancante, 10 locked v1, 2 annualità INAIL ambigue, 1 NO prudente OH1-047. Legacy-fast mantiene EX02/EX03 e exit 1. Zero nuovi fallimenti nei test e nella regressione confermata; le etichette storiche non cambiano. Unknown v2 storico 107/114 non sostituito da v3. Tre skip Windows: privilegi symlink e FIFO non supportati. Tutti i report/archivi precedenti preservati.

## Gate e limiti

| Gate | Target | Actual | Esito |
| --- | --- | --- | --- |
| freeze_integrity | same aa81678 semantic hash | 8f8a50c679a399623b9bd3964fba090d95b36608cd46e2f149f4752fd3169890 | PASS |
| unknown_v3 | >=99% reject, >=100, >=6 sources | {'n': 116, 'correct': 116, 'false_document': 0, 'false_family': 0} | PASS |
| coverage | >=85% file-backed | 86.52849740932642 | PASS |
| canonical | 1007/1007 | 1007 | PASS |
| confirmed_safety | zero false accepts | 241 | PASS |
| input_safety | safe rejection9/9 | 9 | PASS |
| semantic_equivalence | 1563 / zero differences | {'n': 1563, 'differences': 0} | PASS |
| release_gate_fast | 1258/1258 | 1258 | PASS |
| performance_median_p95 | <=250 ms | 198.6201 | PASS |
| tests | zero failures | {'passed': 834, 'failed': 0, 'skipped': 3} | PASS |
| final_checks | compile/catalog/FK/migration/schema | True | PASS |
| v5_entity_version | 0 | {'entity': 0, 'version': 0} | PASS |
| v5_exact_recall | >=90% | 0.705511811023622 | FAIL |
| v5_filled_generation | >=90% | 0.9166666666666666 | PASS |
| v5_filled_precision | >=99.5% | 1.0 | PASS |
| v5_filled_recall | >=90% | 1.0 | PASS |
| v5_leakage | 0 | 0 | PASS |
| v5_precision | >=99.5% | 0.9824561403508771 | FAIL |
| v5_preflight | 30IDs/6sources/400known/200scan/50filled/30unknown | {'attempted_filled': 60, 'filled_generation_rate': 0.9166666666666666, 'identities': 38, 'known': 635, 'passed': True, 'prepared_sha256': '7f6838286c41ba2e51b7a34d8467f835adbc3b441df6a8539722cfc635905b2c', 'recognition_calls': 0, 'scans': 504, 'sources': 6, 'unknown_mix': 30, 'valid_filled': 55} | PASS |
| v5_retrieval_at1 | >=99% | 0.9905511811023622 | PASS |
| v5_retrieval_at25 | 100% | 0.9984251968503937 | FAIL |
| v5_scan_precision | >=99.5% | 0.9815384615384616 | FAIL |
| v5_scan_recall | >=85% | 0.6329365079365079 | FAIL |
| v5_unknown_mix | >=99% | 1.0 | PASS |
| family | >=5 identity-held-out families | experimental / insufficiently validated | PENDING |
| CI | external matrix | external_pending | PENDING |

Blocchi misurati: **v5_exact_recall, v5_precision, v5_retrieval_at25, v5_scan_precision, v5_scan_recall**. V5 resta single-shot e non sarà rivendicata indipendente dopo tuning. Campioni correlati per identità, poche identità in alcune fonti, family insufficiente, ambiguità storiche, RSS non stabilizzata e CI pending rimangono limiti effettivi. Nessuna consulenza personalizzata o verifica editoriale attribuita. Runtime locale deterministico senza rete, LLM o telemetria. Serializzazione CRLF workspace/LF Git del solo catalog_manifest preesistente e già verificata, senza modificarla.

Archivio `dist/BurOCRazia-v0.7.0-candidate-NOT-READY-round19.zip`; commit finale, SHA256 e verifica in `dist/package-verification-round19.json` e `.zip.sha256`, esterni per evitare autoreferenze. Solo file pubblici tracciati, niente cache/file ufficiali binari/database di lavoro/dati personali.
