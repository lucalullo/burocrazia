# Round18 — NOT READY

Software pubblico **0.6.1**, schema **610**; target candidata **0.7.0**, stato **NOT READY**. Branch `codex/coverage-benchmark-v0.7.0`, ingresso `19807fabafcfe186f14a87f659adb77478e0bcdb`; freeze `aa816782b075c8a27eabb7492d080d1c26fa3119`. Commit finale e SHA256 archivio nel verificatore esterno `dist/package-verification-round18.json`. Nessun push, tag o pubblicazione. CI external pending.

## Campione unknown

Master129,13 fonti,19 enti; INL42/129=32.5581%, ammesso nel master. Capacità per N100=112, massimo sostenibile116/cap29. Nessuna acquisizione aggiuntiva. Subset release116,fonti13,enti19,categorie15,concentrazione25.000000%; seed20261014, policy SHA `33c98e3b98c81112bac00c20a9f2831e542673264527e8e64104c3cda78d7982`. Manifest scelto prima del freeze e di qualsiasi predizione, solo metadata e PRNG; nessuno score/ranking/fingerprint similarity nella selezione. I13 esclusi per quota rimangono freschi nel master. Prove in no_prediction_before_selection.json e unknown_subset_feasibility.json. Truth primaria ereditata immutabile dal Round17, revisione tecnica dell'agente; nessuna verifica editoriale umana attribuita. Nessun catalogo/document_id aggiunto.

## Prerequisiti

Coverage1002/1158=86.528497%; canonici980+27=1007/1007;241 NO sintetici senza accettazioni; ANAC e cinque risorse critiche sicure (4 esatte,1 NO prudente); input safety9/9 senza crash/residui/recognition. Equivalenza corrente1563 casi, differenze0; firme complete incluse score/margine/candidati/reason/ente/versione. Nessun byte motore, scoring, soglie, dataset o catalogo cambiato dal Round16. OCR storico estratto una volta per confronto; Tesseract reale separato nei test.

|Run|p50 ms|p95 ms|
|---|---|---|
|1|50.6836|205.2807|
|2|55.3941|239.5791|
|3|56.1529|239.7647|
|4|59.113|234.4921|
|5|52.448|213.9511|
|6|53.552|243.7782|
|7|55.5465|226.0021|

Mediana p95 **234.4921ms**; gate<=250True. Stessa suite67 input/402 richieste per run,2814 tempi; sette run predeterminati, nessun rerun favorevole. Estrazione/OCR fuori timing warm; RequestPages nuova a ogni richiesta, cache soltanto catalogo. Windows/Python3.12.10; nessun collaudo Linux/macOS e nessuna garanzia su altri computer. Baseline Round17 231.5144ms conservata, distinta dalla rimisura.

## Unknown v3 ed evaluation v5

Unknown: {"status": "complete", "n": 116, "correct_no_match": 116, "wrong_document_match": 0, "wrong_family_match": 0, "rejection_rate": 1.0, "false_acceptance_rate": 0.0, "confidence_interval_95": {"lower": 0.9679454935003613, "method": "Wilson score 95% two sided", "upper": 1}, "entity_errors": 0, "version_errors": 0, "recognition_calls": 116}.

Evaluation preflight: {"attempted_filled": 0, "created_at": "2026-10-14T06:40:02.909761+00:00", "eligible_identities": 351, "eligible_records": 352, "eligible_source_counts": {"14": 3, "16": 15, "2": 195, "3": 134, "5": 5}, "eligible_sources": 5, "failed_gates": ["fresh_known_sources"], "filled_generation_rate": null, "freeze_commit": "aa816782b075c8a27eabb7492d080d1c26fa3119", "generation_status": "not_run", "identities": 36, "known": 0, "minimum_sources": 6, "passed": false, "plan_sha256": "37c9f3dc1a1c08f70609c032db014c82fbe5e723753087ce18b4b8e26a06a32e", "planned_filled": 60, "planned_known": 608, "planned_scans": 476, "planned_unknown_mix": 30, "pool_audit_sha256": "819da021fa52c2ae5d4ba5cfca719a8996d7f428394c9216d4142c19742d6225", "reason": "Entire eligible native/canonical-verified identity pool has only5 sources; minimum6. Stop before representation generation and v5 recognition. No contaminated identities reused.", "recognition_calls": 0, "scans": 0, "sources": 5, "unknown_mix": 0, "valid_filled": 0}.
Il pool nativo ammissibile contiene **351 identità uniche / 352 record, soltanto5 fonti** (INPS,INAIL,Ministero del Lavoro,Garante Privacy,Tribunale di Venezia). La selezione deterministica contiene36 identità, sempre5 fonti. Il minimo6 è impossibile nel pool corrente dopo esclusione di tuning, precedenti evaluation influenti e template/risorse correlate. **STOP v5 prima della generazione/predizione**: nessuna identità contaminata recuperata e nessuna espansione del catalogo.608 rappresentazioni note/476 scan/60filled/30unknown erano soltanto pianificati, non generati né misurati. Il leakage di identità passa senza overlap; il leakage completo delle rappresentazioni resta non misurato. Unknown v3 invece ha PASS116/116,0 false DOCUMENT/FAMILY,0 errori ente/versione/estrazione; Wilson95% [96.7945%,100%] riguarda questo campione, non il confidence score del motore. Il ledger post_evaluation_exposures.json registra i116 SHA ora osservati, conservando immutabili registry pre-freeze, label e manifest.
Metriche overall/scan/filled/mix: non misurate.
Retrieval@1/@5/@10/@25: non misurato.

Ogni esecuzione eventualmente avviata è single-shot con journal SQLite, checkpoint, stesso freeze/manifest/hash, ID unici, count/schema e finalizzazione atomica. No tuning/replay come indipendente; label e trasformazioni restano fisse. WRONG FAMILY su unknown è false acceptance. Family: **experimental / insufficiently validated**, esclusa dal useful exact recall.

## Validazione e storico

Test completi **829 passed/0 failed/3 skipped**, 534.58s; log SHA in tests/final_tests.json. Pre-freeze829 passed/0failed/3skip; suite finale separata sul freeze. Il primo run828pass/1fail/3skip aveva già caricato il vecchio test Round17 che presumeva assente qualsiasi manifest v3; il test è stato isolato con ROOT temporaneo, nessun codice motore modificato. Log iniziale preservato in initial_validation_failure.json. Un tentativo mirato ha incontrato WinError5 nel default pytest-of-<local-user>: con basetemp nativo nuovo10 test mirati PASS, poi suite completa verde. Temporaneo nativo Windows; skip piattaforma documentati nei log. Compile, SQLite integrity/FK, migrazione idempotente610/conteggi invariati, fingerprint validators, compat-v2 e truth hash/schema in final_checks.json. Release-gate-fast **1258/1258**, exit0. Historical-regression-fast **1517 casi/15 mismatch**, exit1 atteso, etichette intatte:2 EX02/EX03 sintetici INPS (revisione mancante),10 locked-v1,2 annualità INAIL ambigue,1 NO prudente OH1-047. Non sono nuovi fallimenti né vengono cancellati per dichiarare verde il gate certo. Unknown v2 originale107/114 e tutti gli artifact Round16/17 preservati byte-per-byte. Registry v3 Round17 conservato separatamente prima dell’aggiornamento aggiuntivo v3 Round18. I contratti canonici/sintetici non sono campioni indipendenti ufficiali.

## Gate e limiti

| Gate | Target | Actual | Esito |
| --- | --- | --- | --- |
| unknown_v3_preflight | PASS | True | PASS |
| coverage | PASS | True | PASS |
| canonical | PASS | True | PASS |
| confirmed_safety | PASS | True | PASS |
| input_safety | PASS | True | PASS |
| truth_policy | PASS | True | PASS |
| release_gate_fast | PASS | True | PASS |
| semantic_equivalence | PASS | True | PASS |
| tests | PASS | True | PASS |
| performance_median_p95 | <=250 ms | 234.4921 | PASS |
| performance_preferred_stability | >=5/7 | 7 | PASS |
| performance_preferred_latency | <=220 ms | 234.4921 | PENDING |
| release_freeze | after all prerequisites | aa816782b075c8a27eabb7492d080d1c26fa3119 | PASS |
| unknown_rejection | >=99% | 1.0 | PASS |
| unknown_false_acceptance | <=1% | 0.0 | PASS |
| unknown_entity_version | 0 | {'entity': 0, 'version': 0} | PASS |
| v5_preflight | 30IDs/6sources/400known/200scan/50filled/30unknown | {'attempted_filled': 0, 'created_at': '2026-10-14T06:40:02.909761+00:00', 'eligible_identities': 351, 'eligible_records': 352, 'eligible_source_counts': {'14': 3, '16': 15, '2': 195, '3': 134, '5': 5}, 'eligible_sources': 5, 'failed_gates': ['fresh_known_sources'], 'filled_generation_rate': None, 'freeze_commit': 'aa816782b075c8a27eabb7492d080d1c26fa3119', 'generation_status': 'not_run', 'identities': 36, 'known': 0, 'minimum_sources': 6, 'passed': False, 'plan_sha256': '37c9f3dc1a1c08f70609c032db014c82fbe5e723753087ce18b4b8e26a06a32e', 'planned_filled': 60, 'planned_known': 608, 'planned_scans': 476, 'planned_unknown_mix': 30, 'pool_audit_sha256': '819da021fa52c2ae5d4ba5cfca719a8996d7f428394c9216d4142c19742d6225', 'reason': 'Entire eligible native/canonical-verified identity pool has only5 sources; minimum6. Stop before representation generation and v5 recognition. No contaminated identities reused.', 'recognition_calls': 0, 'scans': 0, 'sources': 5, 'unknown_mix': 0, 'valid_filled': 0} | FAIL |
| v5_leakage | 0 | None | NOT MEASURED |
| v5_precision | >=99.5% | None | NOT MEASURED |
| v5_exact_recall | >=90% | None | NOT MEASURED |
| v5_scan_precision | >=99.5% | None | NOT MEASURED |
| v5_scan_recall | >=85% | None | NOT MEASURED |
| v5_filled_generation | >=90% | None | NOT MEASURED |
| v5_filled_precision | >=99.5% | None | NOT MEASURED |
| v5_filled_recall | >=90% | None | NOT MEASURED |
| v5_retrieval_at25 | 100% | None | NOT MEASURED |
| v5_retrieval_at1 | >=99% | None | NOT MEASURED |
| v5_entity_version | 0 | None | NOT MEASURED |
| v5_unknown_mix | >=99% | None | NOT MEASURED |
| family | >=5 identity-held-out families | experimental / insufficiently validated | PENDING |
| CI | external matrix | external_pending | PENDING |

Blocco misurato: **v5_preflight**. I gate condizionali non eseguiti restano non misurati; eventuali risultati negativi single-shot sono conservati senza tuning o replay. Se manca il freeze, nessuna predizione release viene eseguita. Nessuna metrica non eseguita è rimpiazzata da un risultato storico. CI external pending; family sperimentale; ambiguità storiche visibili. App locale e deterministica, nessuna rete runtime, LLM o telemetria. Catalogo completo invariato. Il manifest catalogo conserva la serializzazione CRLF workspace/LF Git preesistente: eccezione già provata in Round16, JSON e blob storici identici; nessuna normalizzazione dei byte congelati.

Archivio `dist/BurOCRazia-v0.7.0-candidate-NOT-READY-round18.zip`; SHA256 e verifica esterni in `dist/package-verification-round18.json` e `.zip.sha256` per evitare autoreferenze. Solo file pubblici tracciati, niente cache, file ufficiali binari, DB di lavoro, credenziali o dati personali.
