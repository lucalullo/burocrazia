# Round 20 — NOT READY

Software pubblico **0.6.1**, schema **610**, branch `codex/coverage-benchmark-v0.7.0`. Ingresso `7da8b10f3d7c8ea302d7a3dd565f265bf5c5f370` pulito; nessun freeze Round 20. Freeze storico `aa816782b075c8a27eabb7492d080d1c26fa3119` preservato. Per la successiva regola permanente dell'utente non viene creato alcun commit: HEAD resta quello d'ingresso e le modifiche restano nel working tree. Lo ZIP usa un Git tree con indice temporaneo separato; HEAD, SHA del tree, SHA256 e verifica sono nel sidecar `dist/package-verification-round20.json`. Nessun push, tag o pubblicazione; CI esterna pending.

## V5 storica e truth audit

**historical_independent_v5_round19** conserva integralmente selezione, matrice, leakage, 665 raw, metriche ed etichette. Originale: 448 exact/8 wrong/179 NO su 635 noti; **P 98.2456%, R 70.5512%, scan R 63.2937%**. Cinque gate falliti: precisione, exact recall, scan precision, scan recall e retrieval@25. Unknown v3 originale 116/116, 13 fonti, 0 false accept resta storico e **non valida il motore v6**. Il replay corrente non sostituisce alcuna misura storica.

Audit 665/665: `{'confirmed_expected': 665}`; 0 label_error/0 ambiguous/0 obsolete/0 insufficient_evidence nel contratto tecnico delle rappresentazioni canoniche. Verifica locale di byte ufficiali, ricevute effettive, binding e trasformazioni deterministiche; non è una nuova verifica editoriale umana né un controllo live. Otto false accept confermati e 179 false reject; documenti 469/511 e 470/512 distinguono genitori e tutore, anche se condividono allegati. Categorie failure: `{'OCR_degradation': 47, 'entity_conflict_false': 57, 'retrieval_miss': 1, 'retrieval_rank_low': 5, 'shared_template': 24, 'visual_underuse': 53}`. Unico expected fuori top25: 802/rotation180; nessuna modifica all'indice motivata da questo caso isolato. Campi diagnostici mancanti restano vuoti, senza score inventati.

## Motore e sviluppo dopo correzioni

Politica `fingerprint-decision-v6`, runtime `549096bb454b1bcecf321791a2331018c817c2dcbaea3202e7347060db502e59`, profilo `6111853da8c0fee57650395839f674e30f90774bf97465a769d918b694b97742`. Regole generali in DECISION_POLICY_V6.md: ambiguità fingerprint non superabile dai soli metadati; etichette subordinate/prefissi OCR non trasformati in emittenti contrari; scan corroborati da char/OCR/anchor/layout; margine multipagina corroborato da due allineamenti distinti; veto dei metadati che contraddicono contenuto corroborato, senza trasformare quest'ultimo in match positivo. Exact SHA, hard conflict, revisione/anno/territorio, catalogo, dataset e vecchi profili preservati. Nessun ID/URL/case-specific hack e nessuna modifica a retrieval o pesi. Applicabilità, esempi positivi, hard negative, fallback e test nel documento della policy.

3.160 input pubblici/sintetici preparati: 1.007 canonici, 635 V5 development, 556 storici, 630 precedenti development, 332 unknown osservati. **development_regression_v5_after_fix**: `542` exact, `0` wrong, `93` non exact su 635; **P 100.0000%, R85.3543%**. Scan 504: `413` exact/`0` wrong, P100.0000%, R81.9444%. Compilati 55: `55` exact, P100.0000%, R100.0000%; generazione storica 55/60, 91.6667%, 5 fallimenti originali invariati. Combined known: `{'accepted': 1967, 'exact': 1967, 'n': 2137, 'precision': 1.0, 'recall': 0.9204492278895648, 'wrong': 0}`. Safety confermata: `705` negativi, `0` false accept complessivi; FAMILY su unknown è errore. Nessuna metrica fresca indipendente è ricavata da questi dati contaminati.

Retrieval sviluppo @1/@5/@10/@25: `{'1': 0.9905511811023622, '5': 0.9984251968503937, '10': 0.9984251968503937, '25': 0.9984251968503937}`. Dettagli per fonte/trasformazione e input non estraibili in development_breakdown.json. Input oltre i limiti PDF conservati come extraction failure, mai conteggiati come rifiuto unknown riuscito. Tutti i tentativi e log tecnici sono preservati; technical_attempt_history.json distingue errori di fixture/runner e risultati finali. L'estrazione usa Tesseract locale reale; immagini/compilati sono sintetici, non scansioni personali. Nessun testo personale entra in cache.

## Pool fresco e stop prima del freeze

Registry v4 preservato; v5 registra esposizione V5 prima delle modifiche; v6 aggiunge tutte le identità viste in calibrazione/tentativi e risorse unknown v1-v3. Audit 1.019 ID fingerprint, inclusi 51 non utilizzabili. Pool fresco dimostrabile con registry vincolante: **316 identità/4 fonti**, `{'2': 186, '3': 124, '14': 2, '16': 4}`, concentrazione 58.8608%. Capacità soltanto teorica: `4850` rappresentazioni/`4158` scan/`60` compilati potenziali; **0 compilati freschi validati**, nessuna selezione V6. La V5 ha esaurito tutte le identità eleggibili di due fonti: 6 MinLavoro e 1 Unioncamere; restano al massimo 4 fonti prima degli ulteriori controlli. Il requisito 6 non viene abbassato e le provenienze storiche non vengono divise artificialmente.

Preflight unknown v4: `13` risorse ufficiali confermate non osservate nel master esistente, `1` fonte, concentrazione 100.00%; richiesti 100/8/max25%. Acquisizione nuova non eseguita perché il prerequisito congiunto delle fonti V6 è irraggiungibile nel pool vincolante corrente. Questo è un inventario del master disponibile, non una dichiarazione che altri unknown ufficiali non esistano. Zero predizioni su unknown v4; nessun manifest release, freeze o selezione V6.

**V6 non eseguita**: 0 chiamate, 0 identità selezionate, 0 rappresentazioni; exact/wrong/P/R/F1/errori ente/versione/retrieval/scan/filled/unknown end-to-end non misurati (`null`), non zero prestazioni. Family resta **experimental / insufficiently validated** e non aumenta exact recall. Una RC richiede prima prerequisiti soddisfatti e poi nuove unknown v4/V6 single-shot su identità fresche.

## Verifiche finali

Coverage **86.528497%** (1002/1158), canonical **1007/1007**. Negativi sintetici di sviluppo: **260/260 rifiuti corretti**, 0 false accept (hard_negatives_development.json); contratti correlati, non campione indipendente. Input safety 9/9, zero chiamate di riconoscimento dopo parser refusal. Compile, SQLite integrity/FK, migrazione idempotente 610/conteggi invariati, profilo/truth/schema e validatori fingerprint 1/2/3 verificati sul runtime corrente. Release diagnostic `1258` contratti, PASS `True`; storico `1517` con `15` mismatch ed exit 1 conservato, etichette immutate. La nuova semantica non rivendica equivalenza con il vecchio runtime: conserva i contratti confermati, mentre i risultati originali restano separati.

| Run | p50 ms | p95 ms |
| --- | --- | --- |
| 1 | 28.2859 | 129.5635 |
| 2 | 27.5862 | 113.4597 |
| 3 | 26.8616 | 132.2424 |
| 4 | 27.8373 | 123.6941 |
| 5 | 28.282 | 116.4151 |
| 6 | 26.228 | 121.5593 |
| 7 | 29.3574 | 136.1821 |

Sette run warm predeterminati, 67 input/402 richieste ciascuno/2.814 timing; mediana p95 **123.6941 ms**, gate 250 ms **True**, target 220 ms `True`, `7/7` sotto 250. Estrazione/OCR fuori timing; nuove RequestPages per richiesta, cache solo metadata catalogo. Baseline storica Round 19 198.6201 ms separata. Tutti i run mantenuti, nessuna scelta di rerun favorevoli.

Full pytest finale **856 passed/0 failed/3 skipped**, 573.23s, log SHA `67db33059888e47aa9d895a2990dba4ef23bb348ff1f4fba502f9663806c599c`. Baseline pre-modifica 834/0/3 conservata. Tre skip Windows: symlink senza privilegio e FIFO non disponibili. Test sui sigilli storici verificano gli originali alberi Git; il test sul veto dei metadati intercetta ora il modulo v6 attivo mantenendo le medesime asserzioni. Collaudo soltanto Windows/Python 3.12.10; Linux/macOS e CI esterna non eseguiti.

## Gate RC

| Gate | Target | Actual | Esito |
| --- | --- | --- | --- |
| dev_precision_pass | >=99.5% | 1.0 | PASS |
| dev_recall_pass | V5 development >=90% | 0.8535433070866142 | FAIL |
| dev_scan_pass | >=85% | 0.8194444444444444 | FAIL |
| dev_filled_pass | >=90% | 1.0 | PASS |
| confirmed_safety_pass | zero confirmed false accepts | 0 | PASS |
| canonical_pass | 1007/1007 | 1007 | PASS |
| coverage_pass | >=85% | 86.52849740932642 | PASS |
| input_safety_pass | 9/9 safe rejection | 9 | PASS |
| performance_pass | 7 runs; median p95<=250ms | 123.6941 | PASS |
| tests_pass | zero failures | {'passed': 856, 'failed': 0, 'skipped': 3} | PASS |
| V6_pool_pass | 30 IDs/6 sources/400 reps/200 scans/50 valid filled | 316 IDs/4 sources | FAIL |
| unknown_v4_preflight_pass | 100 fresh/8 sources/max25% | {'N': 13, 'sources': 1, 'concentration': 1.0} | FAIL |
| final_checks | compile/catalog/FK/idempotent610/schemas | True | PASS |
| confirmed_release_diagnostic | 1258/1258 | 1258 | PASS |
| unknown_v4 | >=99% correct rejection, <=1% false acceptance, zero entity/version errors | None | NOT RUN |
| v6_precision | >=99.5% | None | NOT RUN |
| v6_recall | >=90% | None | NOT RUN |
| v6_scan_precision | >=99.5% | None | NOT RUN |
| v6_scan_recall | >=85% | None | NOT RUN |
| v6_filled_generation | >=90% | None | NOT RUN |
| v6_filled_precision | >=99.5% | None | NOT RUN |
| v6_filled_recall | >=90% | None | NOT RUN |
| v6_retrieval_at25 | 100% | None | NOT RUN |
| v6_retrieval_at1 | >=99% target | None | NOT RUN |
| v6_entity_version | zero | None | NOT RUN |
| unknown_end_to_end | >=99% fresh rejection | None | NOT RUN |
| family | >=5 validated held-out families | experimental / insufficiently validated | PENDING |
| CI | external matrix | external_pending | PENDING |

Limiti effettivi: sviluppo contaminato e trasformazioni correlate per identità, pool fresco con fonti insufficienti, unknown v4 non acquisita/eseguita, V6 non eseguita, family insufficiente, CI pending. Nessuna attribuzione automatica di verifica editoriale o consulenza personalizzata. Applicazione locale deterministica; rete runtime/LLM/telemetria assenti. Catalogo completo e provenienze invariati; eccezione di serializzazione preesistente CRLF workspace/LF Git del solo catalog_manifest verificata senza normalizzazione del file.

Archivio: `dist/BurOCRazia-v0.7.0-candidate-NOT-READY-round20.zip`. Snapshot dei file pubblici attraverso indice temporaneo separato, senza creare commit o cambiare l'indice originale. Cache, checkpoint privati, testo estratto, fixture binarie ufficiali, database di lavoro e log locali esclusi. HEAD di partenza/tree SHA/SHA256/verifica nel sidecar esterno `dist/package-verification-round20.json`; hash storico di tutti gli artefatti protetti e misure correnti controllati durante il packaging. Continuità permanente in CONTINUITA_OPERATIVA.md, Goal ufficiale e controllo orario nella stessa chat; checkpoint privati append-only. La pianificazione viene disattivata al completamento verificato del Round 20; quota, app spenta e permessi possono comunque impedire una ripresa automatica.
