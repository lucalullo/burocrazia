# Round17 — NOT READY

Software pubblico **0.6.1**, schema **610**; target candidata **0.7.0**, stato **NOT READY**. Branch `codex/coverage-benchmark-v0.7.0`, ingresso `19928839d10f762307827935eb2445bcff2787fe`; freeze `non eseguito`. Commit finale e SHA256 archivio nel verificatore esterno `dist/package-verification-round17.json`. Nessun push, tag o pubblicazione. CI external pending.

## Campione unknown

Partenza95; nuovi candidati acquisiti157; nuovi confermati indipendenti34; pool finale129, fonti13, enti19, tipi15, concentrazione massima32.558140%. Gate minimoFalse, preferitoFalse. **INL42/129=32.5581% supera25%: stop obbligatorio prima di freeze/selezione/predizioni.** Quantità, fonti e categorie passano. Tenendo42 INL, servirebbero almeno39 ulteriori unknown indipendenti da altre fonti per N168/max25%; questa è aritmetica di adeguatezza, non una raccolta eseguita. Hash, ricevute, URL finali, confronto catalogo/codice/titolo/fingerprint/famiglia e revisione primaria precedono le predizioni. I95 precedenti sono conservati; nuove fonti esclusivamente benchmark. Revisione tecnica dell'agente, nessuna verifica editoriale umana attribuita. Lotto400 richieste,157 nuovi file;37 qualificati automatici diventano34 indipendenti dopo1 template ambiguo/2 near-duplicate esclusi. Acquisizione limitata con opt-in, robots e allowlist; nessun catalogo/document_id aggiunto. Il traversal ora scarta tutte le teste già visitate prima di dichiarare la coda esaurita.

## Prerequisiti

Coverage1002/1158=86.528497%; canonici980+27=1007/1007;241 NO sintetici senza accettazioni; ANAC e cinque risorse critiche sicure (4 esatte,1 NO prudente); input safety9/9 senza crash/residui/recognition. Equivalenza corrente1563 casi, differenze0; firme complete incluse score/margine/candidati/reason/ente/versione. Nessun byte motore, scoring, soglie, dataset o catalogo cambiato dal Round16. OCR storico estratto una volta per confronto; Tesseract reale separato nei test.

|Run|p50 ms|p95 ms|
|---|---|---|
|1|55.1585|212.7211|
|2|61.5721|261.1455|
|3|59.9719|249.7815|
|4|45.7581|231.5144|
|5|53.4535|216.0429|
|6|58.6798|199.359|
|7|62.4849|257.06|

Mediana p95 **231.5144ms**; gate<=250True. Stessa suite67 input/402 richieste per run,2814 tempi; sette run predeterminati, nessun rerun favorevole. Estrazione/OCR fuori timing warm; RequestPages nuova a ogni richiesta, cache soltanto catalogo. Windows/Python3.12.10; nessun collaudo Linux/macOS e nessuna garanzia su altri computer. Prestazioni Round16 244.9918ms conservate, non sostituiscono la rimisura.

## Unknown v3 ed evaluation v5

Unknown: {"status": "not_run", "n": null, "correct_no_match": null, "wrong_document_match": null, "wrong_family_match": null, "rejection_rate": null, "false_acceptance_rate": null, "confidence_interval_95": null, "entity_errors": null, "version_errors": null, "recognition_calls": 0}.

Evaluation preflight: non eseguito.
Metriche overall/scan/filled/mix: non misurate.
Retrieval@1/@5/@10/@25: non misurato.

Ogni esecuzione eventualmente avviata è single-shot con journal SQLite, checkpoint, stesso freeze/manifest/hash, ID unici, count/schema e finalizzazione atomica. No tuning/replay come indipendente; label e trasformazioni restano fisse. WRONG FAMILY su unknown è false acceptance. Family: **experimental / insufficiently validated**, esclusa dal useful exact recall.

## Validazione e storico

Test completi **823 passed/0 failed/3 skipped**, 608.74s; log SHA in tests/final_tests.json. Temporaneo nativo Windows; skip piattaforma documentati nei log. Compile, SQLite integrity/FK, migrazione idempotente610/conteggi invariati, fingerprint validators, compat-v2 e truth hash/schema in final_checks.json. Release-gate-fast **1258/1258**, exit0. Historical-regression-fast **1517 casi/15 mismatch**, exit1 atteso, etichette intatte:2 EX02/EX03 sintetici INPS (revisione mancante),10 locked-v1,2 annualità INAIL ambigue,1 NO prudente OH1-047. Non sono nuovi fallimenti né vengono cancellati per dichiarare verde il gate certo. Unknown v2 originale107/114 e tutti gli artifact Round16 preservati byte-per-byte. Registry v3 Round16 conservato separatamente prima dell'aggiornamento aggiuntivo v3 Round17. I contratti canonici/sintetici non sono campioni indipendenti ufficiali.

## Gate e limiti

| Gate | Target | Actual | Esito |
| --- | --- | --- | --- |
| unknown_v3_preflight | PASS | False | FAIL |
| coverage | PASS | True | PASS |
| canonical | PASS | True | PASS |
| confirmed_safety | PASS | True | PASS |
| input_safety | PASS | True | PASS |
| truth_policy | PASS | True | PASS |
| release_gate_fast | PASS | True | PASS |
| semantic_equivalence | PASS | True | PASS |
| tests | PASS | True | PASS |
| performance_median_p95 | <=250 ms | 231.5144 | PASS |
| performance_preferred_stability | >=5/7 | 5 | PASS |
| performance_preferred_latency | <=220 ms | 231.5144 | PENDING |
| release_freeze | after all prerequisites | None | NOT MEASURED |
| unknown_rejection | >=99% | None | NOT MEASURED |
| unknown_false_acceptance | <=1% | None | NOT MEASURED |
| unknown_entity_version | 0 | None | NOT MEASURED |
| v5_preflight | 30IDs/6sources/400known/200scan/50filled/30unknown | None | NOT MEASURED |
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

Blocco misurato: **unknown_v3_preflight**. Freeze e gate v3/v5 restano non misurati per lo stop richiesto dal preflight; non sono risultati negativi di recognition. Se manca il freeze, nessuna predizione release viene eseguita. Nessuna metrica non eseguita è rimpiazzata da un risultato storico. CI external pending; family sperimentale; ambiguità storiche visibili. App locale e deterministica, nessuna rete runtime, LLM o telemetria. Catalogo completo invariato. Il manifest catalogo conserva la serializzazione CRLF workspace/LF Git preesistente: eccezione già provata in Round16, JSON e blob storici identici; nessuna normalizzazione dei byte congelati.

Archivio `dist/BurOCRazia-v0.7.0-candidate-NOT-READY-round17.zip`; SHA256 e verifica esterni in `dist/package-verification-round17.json` e `.zip.sha256` per evitare autoreferenze. Solo file pubblici tracciati, niente cache, file ufficiali binari, DB di lavoro, credenziali o dati personali.
