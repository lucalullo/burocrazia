# Round 21 — NOT READY

Pubblico **0.6.1**, schema **610**. Branch `codex/coverage-benchmark-v0.7.0`, HEAD originale `7da8b10f3d7c8ea302d7a3dd565f265bf5c5f370`. Tutto il working tree Round 20 preservato. Nessun commit/push/tag/release. Il campo commit del freeze indica soltanto la base; il vero snapshot semantico è il **Git tree non committato `9d08feb84dd6980ba374b3a3069d5c785e27b73c`**. Archivio finale e SHA nel sidecar `dist/package-verification-round21.json`. CI esterna pending; nessun collaudo Linux/macOS.

## Sviluppo, audit e policy v7

V5 indipendente Round 19 immutata: **P98,2456%, R70,5512%, scan R63,2937%**,448 exact/8 wrong/179 NO su 635 noti,665 raw con mix unknown. Il replay non sostituisce questi numeri. Round 20 development v6 P100%, R85,3543%, scan R81,9444%, filled 100% resta storico. Unknown v3 originale 116/116/13 fonti non valida automaticamente v7.

Audit di 170 miss complessivi confermati,93 V5: **87/93 rank1 (93,5484%)**; dettagli/rank5/10/25/rootcause in dev_false_reject_audit.csv e dev_retrieval_summary.json. Retrieval/pesi/global threshold/margin invariati. Policy v7 aggiuntiva, vecchia v6 immutata: rank1 OCR/page+char+anchor forti, strict layout+contenuto corroborato, heading esclusivo completo e ordinato nella finestra iniziale. Heading disambigua soltanto un candidato già primo; non crea un match da un ID atteso. Entity/version confirmed/unknown/conflict separati, conflitto esplicito hard veto; anno fiscale distinto da versione. Titoli/codici catalogo, provenienze e input oltre 2000 caratteri rispettano i vincoli. Canali/condizioni/reason codes/limiti/test in DECISION_POLICY_V7.md.

Cause originali sui 170 miss: `{'scan_OCR_low': 35, 'other': 3, 'first_page_partial': 3, 'candidate_rank1_but_margin': 61, 'visual_support_high_but_unused': 18, 'char_overlap_high_but_unused': 15, 'shared_template': 6, 'extraction_noise': 29}`. Recuperati **32 casi V5**, nessun caso prima corretto perso; tier effettivi `{'B_scan_strong_multichannel': 9, 'B_page_char_strict_layout': 6, 'B_complete_heading_layout': 17}`.

Entrambe le iterazioni restano: v7_initial R88,8189% fallita; v7_ordered finale **574/635, P100.0000%, R90.3937%**; scan **445/504, P100.0000%, R88.2937%**; filled **55/55, P/R100%**. Nessun wrong document confermato. **705 negativi confermati,0 false accept**; hard negative sintetici **260/260**, FAMILY su unknown sempre errore. Canonical **1007/1007**. Due casi INAIL storicamente ambigui mantengono etichette/raw originali, non entrano nella safety confermata; ID osservato1147 escluso dal pool fresco. Quattro extraction refusal development non sono credited unknown success. Tutto è development contaminato, non evidenza indipendente.

## Capacità fresca e registry

Audit di tutte 19 fonti/1019 ID fingerprint: pool **639 identità/8 fonti**, conteggi `{'10': 8, '14': 3, '15': 12, '16': 52, '18': 3, '2': 302, '3': 231, '5': 28}`. Nessuna nuova identità, fonte, fingerprint o modifica al seed. Le 357 incertezze originali includevano candidati recuperati nei diagnostici di soli 40 input legacy; 324 flag sono risolti con prova dei file/ID effettivamente input. Esposizione canonica/qualificazione/evaluation storica sola non è tuning secondo Round 21. I 40 input di qualificazione rimangono esclusi conservativamente, senza attribuire tuning non dimostrato. Ogni ID realmente usato in tuning, V5, development Round 20/21 (inclusi observed errati/ambigui) resta escluso. Source profile/source seen non elimina automaticamente tutta una fonte. Registry v7 conserva legacy e flag v6 precedenti; parent hash e audit per identità. Prenotazione 639 ID dopo tutte le misure development/canonical/performance e prima del freeze. Nessuna predizione/trasformazione fra prenotazione e freeze.

Selezione V6 fissata dopo freeze e unknownPASS: `{'2': 6, '3': 5, '5': 5, '10': 6, '14': 3, '15': 6, '16': 6, '18': 3}`, seed 202610142106,40 ID/8 fonti, max15%, strati fonte/formato/versione/codice/pagine;20 PDF filler con 5 varianti fisse. Fonti Garante e ANAC hanno soltanto 3 identità ciascuna, limite esplicito. Rappresentazioni digitali, scan 200/150DPI, JPEG 90/75/60, grayscale, blur, contrast, crop 2/5%, first-page e rotazioni; rumore minimo con seed nuovo. Riempimento sintetico verificato con campi/checkbox/data/numeri/testo o overlay statico. Generazione/preflight: `{'attempted_filled': 100, 'filled_generation_rate': 0.75, 'identities': 40, 'known': 572, 'passed': False, 'prepared_sha256': '3b1c72a936f8d02e7170cdcabb7ec8e3e8d44499275b84a29e4c03879d5215b7', 'recognition_calls': 0, 'scans': 420, 'sources': 8, 'valid_filled': 75}`. Non sono scansioni o dati personali reali.

## Unknown v4, freeze e single-shot

829 candidati da cache ufficiale con ricevute e SHA effettivi, **zero richieste di rete Round 21**. Revisioni truth pre-freeze413→266→236→213, tutte preservate: heading primario invece di citazioni nel corpo, esclusione raw/URL canonici noti, form heading/collisioni, emittente primario separato da fonte,23 duplicati con apertura nativa normalizzata identica esclusi. Audit tecnico riproducibile, non nuova validazione editoriale umana. Codice/versione non determinabili restano null. Nessuna predizione durante discovery/truth/preflight. Master finale **213/15 fonti**; source balance/format support/freshness passano.

Freeze lega runtime `c077552055c25b0bc128e1a5c607afc434fb3bd074e6da165f3d8333145abf15`, profilo `410b19049b368d8b74a0ea1c80798db68737a23ab4164d4364062aad56d75c5b`, dataset `eaac87ac81e03ba838b52d66992db20967e8c50bbcfd88b02d894c42ab68f4bd`, catalog semantic/calibrazione/registry/prenotazione/truth/gate/canonical/safety/timing/test/schema e tutti i file di codice. L'infrastruttura benchmark fu completata dopo il timing, con full-code hash distinto; il runtime misurato è identico. Solo catalog_manifest conserva una differenza CRLF workspace/LF Git preesistente verificata semanticamente, senza riscriverlo.

Selezione metadata-only post-freeze, seed 202610142104: **120 unknown/15 fonti/18 emittenti**, max10,8333%,6 tipi. Prima e unica valutazione: **120/120 correct NO**, 0 DOCUMENT/FAMILY false accept,0 extraction failure,0 errori ente/versione. Wilson95% `{'lower': 0.9689808335812966, 'method': 'Wilson score 95% two sided', 'upper': 1}`; non è garanzia sulla popolazione. Tutte le osservazioni e conteggi/schema/SHA sono finalizzati atomicamente. Il protocollo end-to-end prevede il riuso di queste stesse righe; essendo V6 bloccata, nessun end-to-end V6 è stato eseguito. Zero seconde predizioni unknown.

**V6 non eseguita**, 0 predizioni: il solo requisito misurato fallito è la generazione filled **75% < 90%**. Leakage **0, PASS**. Precisione, recall, F1, errori ente/versione, retrieval @1/@5/@10/@25, scan e filled V6 restano non misurati. Unknown end-to-end V6 non eseguito; la misura fresh unknown v4 separata resta 120/120. I 25 compilati falliti riguardano ID484/264/263/558/414 (5 varianti ciascuno); tre normalized DOCX falliscono per ID113/1121/1074. Nessun ID o variante sostitutiva. Metriche P/R/F1/retrieval non misurate, mai rappresentate come zero prestazioni. Tutti i fallimenti di generazione restano agli atti; il leakage passa.

Il runner generazione iniziale ha lasciato 133 file prima di C14NError DOCX non intercettato. Adapter operativo in scripts/round21_generation_resume.py conserva byte/hash e riusa gli output già riusciti; traduce l'eccezione in generazione fallita, senza riparare XML, cambiare generatore/seed/varianti, selezione o engine. L'errore originale, guardia di ripresa iniziale e audit della ripresa rimangono. Le chiamate fallite prima dell'interruzione prive di receipt durevole possono essere state ritentate con gli stessi parametri; non vengono scelte varianti alternative o rimossi fallimenti per migliorare il tasso. I vecchi compilati riusciti sono riaperti con verifica concreta di marker sintetici (lower bound), oltre alla verifica già eseguita dal generatore prima del salvataggio. Nessuna predizione V6 precede il gate di generazione/leakage. I file semantici congelati restano invariati.

## Verifiche e limiti

Coverage **86.528497% (1002/1158)**. Input safety9/9,0recognition dopo rifiuto parser. Catalogo1216 documenti,19 fonti,16famiglie, integrity/FK/migrazione610 idempotente/conteggi invariati. Compile, profili, dataset/schema verificati. Release diagnostic1258/1258PASS; historical regression1517 contratti/15mismatch/exit1 resta come prova originale incompatibilità etichette, non viene spacciato perzero mismatch. Canonical/safety/diagnostici legati allo stesso runtime del freeze, senza replay ridondanti.

| Run | p50 ms | p95 ms |
| --- | --- | --- |
| 1 | 29.9572 | 138.3219 |
| 2 | 37.2116 | 175.8304 |
| 3 | 41.4568 | 190.7672 |
| 4 | 41.4656 | 207.9117 |
| 5 | 46.3497 | 176.6788 |
| 6 | 41.3975 | 213.4513 |
| 7 | 29.8087 | 165.2469 |

Tutti7 run predeterminati,67 input/402 richieste per run/2814 timing. **p95 mediano 176.6788 ms**,7/7≤250, preferito180PASS. Solo matching warm, estrazione/OCR esclusi; RequestPages nuove, cache solo metadati. Baseline Round 20 123,6941 ms separata. Nessun rerun selezionato favorevolmente.

Baseline 856/0/3; full v7 pre-freeze876/0/3 più2 test infrastruttura. **Full suite sul freeze 878 passed/0 failed/3 skipped**,553.19s, log SHA`ae8d251f5b52ceaa6375817c1208a183584c949fd808b6876b453de9f5615783`. Skip Windows: symlink senza privilegio e FIFO non disponibili. Collaudo Windows/Python3.12.10, Tesseract locale reale; benchmark scan/filled sintetici e correlati per identità. Nessun test su dati personali, nessuna equivalenza statistica con scansioni di campo. Family **experimental / insufficiently validated**, non contribuisce exact recall. CI esterna pending.

## Esito

**NOT READY**. Gate falliti: `['v6_generation_and_leakage', 'fresh_v6_evaluation']`. Nessun tuning dopo fresh unknown/V6; qualunque sviluppo futuro che usi questi risultati li rende development e richiede nuovi held-out. Pubblico resta0.6.1. Archivio `dist/BurOCRazia-v0.7.0-candidate-NOT-READY-round21.zip` con verifica storici/freeze/raw/conteggi/hash/hygiene. Cache, binari ufficiali, checkpoint privati, testo estratto, DB di lavoro e log esclusi; risultati pubblici e script inclusi. Goal e heartbeat nativi supportano ripresa entro i limiti reali dell'app e quota, senza servizi esterni; checkpoint persistenti privati append-only. Al completamento verificato Round 21 il heartbeat viene disattivato.

| Gate | Actual | Esito |
| --- | --- | --- |
| dev_precision_pass | True | PASS |
| dev_recall_pass | True | PASS |
| dev_scan_pass | True | PASS |
| dev_filled_pass | True | PASS |
| confirmed_safety_pass | True | PASS |
| canonical_pass | True | PASS |
| hard_negatives_pass | True | PASS |
| coverage_pass | True | PASS |
| input_safety_pass | True | PASS |
| performance_pass | True | PASS |
| tests_pass | True | PASS |
| V6_pool_pass | True | PASS |
| unknown_v4_preflight_pass | True | PASS |
| entity_version_pass | True | PASS |
| final_checks_pass | True | PASS |
| unknown_v4 | {"n": 120, "correct_rejects": 120, "false_accepts": 0, "rejection_rate": 1.0, "entity_errors": 0, "version_errors": 0} | PASS |
| v6_generation_and_leakage | {"attempted_filled": 100, "filled_generation_rate": 0.75, "identities": 40, "known": 572, "passed": false, "prepared_sha256": "3b1c72a936f8d02e7170cdcabb7ec8e3e8d44499275b84a29e4c03879d5215b7", "recognition_calls": 0, "scans": 420, "sources": 8, "valid_filled": 75} | FAIL |
| fresh_v6_evaluation | None | FAIL |
| final_frozen_validation | {"failed": 0, "freeze_manifest_sha256": "28a3026dcf0b7a8ee40168d28420975a5b103dc0e4dd8db68a7d553fa2b7aa59", "log_sha256": "ae8d251f5b52ceaa6375817c1208a183584c949fd808b6876b453de9f5615783", "passed": 878, "runtime_sha256": "c077552055c25b0bc128e1a5c607afc434fb3bd074e6da165f3d8333145abf15", "scope": "Full suite on frozen runtime/runner/dataset; Windows platform skips only.", "seconds": 553.19, "skipped": 3, "status": "passed"} | PASS |
