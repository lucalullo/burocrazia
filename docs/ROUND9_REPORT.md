# Round 9 — NOT READY

Software pubblico 0.6.1, target 0.7.0, schema 610. Branch `codex/coverage-benchmark-v0.7.0`. HEAD al momento della misura/report: `fa2a307fbbb4721ecafa93e6920c909526e00a25`; le modifiche R9 sono identificate anche dai loro hash, non ancora da quel commit. Il commit finale archiviato e lo SHA dello ZIP sono registrati dopo il commit in `dist/package-verification.json` e nella consegna. Nessun freeze R9: prerequisiti non raggiunti. Nessun push, tag o pubblicazione. Catalogo e seed immutati: 1216 reali, 1212 operative, 19 fonti, 16 famiglie.

Round 8: freeze effettivo `b0e24476db23bb479dadb7f2957d34419d02c9d0`, seguito soltanto da report/package. V4 originale 50/356: 36 exact, 14 rifiuti, 0 wrong, 306 esiti indisponibili. Caso A tecnicamente compatibile col completamento storico facoltativo: non effettuato. Originali preservati, nessuna v4 spacciata per nuova prova. Log: errno 22 in Path.open(wb) del checkpoint; causa OS esatta non determinabile dai dati registrati. Corretto il difetto accertato di persistenza, senza inventare lock/antivirus.

## Safety e truth

Due falsi accept storici riparati: EX02MISSINGREV e EX03MISSINGREV, prima documenti 13/12 con score 100, ora NO. Causa: inferenza della revisione 1.1 dalla sola unicità di codice/titolo/ente nel fallback metadata. Correzione v5 generale del fallback metadata: revisione decimale esplicita nei primi 2000 caratteri, senza dedurla dall’unicità. Le firme forti mantengono criteri R8 multicanale, identità e margine; conflitti ente/versione, binding/stato e SHA condivisi mantengono i veti. Test su ID differente esclude blacklist. Audit numerico completo in `historical_false_acceptance_audit.md`.

Truth v2: `{"ambiguous": 25, "confirmed": 1049, "excluded": 2, "historical_only": 829}`, zero contraddizioni non classificate. Include tutte le etichette testuali, le 979 risorse canoniche unambiguous e gli unknown confermati. Solo confirmed entra nei gate di release; i contratti storici sono controllati separatamente e ambigui/esclusi conservano lo storico. Le vecchie label positive EX02/03 prive di revisione ora sono rifiutate: base 33/35, nessun tentativo di nascondere la regressione storica. R061 resta NO. Cinque vecchi casi critici: rifiuto o identità propria corretta, verificati separatamente. Nessuna nuova verifica editoriale.

| Corpus storico | Corretti | Totale |
| --- | --- | --- |
| development_regression | 33 | 35 |
| release_locked_v1 | 59 | 69 |
| release_locked_v2 | 69 | 69 |
| development_compat_v2 | 37 | 37 |
| hard_negatives_v1 | 30 | 30 |
| hard_negatives_v2 | 100 | 100 |
| family_release_v3 | 161 | 161 |
| catalog_coverage | 1169 | 1212 |

## Unknown ufficiali

161 candidati auditati, classificazioni `{"ambiguous": 91, "confirmed_unknown": 68, "duplicate_of_catalog": 1, "possible_catalog_match": 1}`. Confermati 68; fonti 4, distribuzione `{"anac": 1, "inail": 16, "lavoro": 6, "mimit": 45}`, concentrazione 66.18%. Discovery: 45 richieste nella seconda acquisizione (9 nella prima), esclusivamente maintenance con --allow-network/robots/allowlist e fonti esistenti. Non raggiunti i minimi di 100 file, 8 fonti e massimo 25% di concentrazione.

Rifiuti corretti 68/68; false DOCUMENT/FAMILY accept 0/0; errori estrazione 0. FAR 0.00%, CI 95% Wilson `[0, 0.053471336520070537]`. Per-source/per-entity/per-type nei raw. L’ente del manifest deriva dall’autorità che ospita la fonte: non certifica l’emittente storico di ogni decreto o atto UE; nessuna pretesa di 8 emittenti indipendenti. I file storici restano contaminati anche dopo conferma truth; i nuovi candidati sono indicati separatamente. Classificazione fondata su ricevuta/SHA, intestazione informativa, titolo completo, near-duplicate e famiglie, prima delle predizioni. I 91 dubbi sono esclusi, senza convertirli in unknown per migliorare i numeri.

## Coverage e legacy

941/1158 file-backed (81.26%); 941/1212 operative (77.64%); 0 recuperate. Tutti i 217 residui sono censiti in `fingerprint_recovery_v2.csv`. I 1158 ID provengono dall’audit congelato R6, incluso 166 SEGNALAZIONE privo di download_url: il classificatore corrente ne conterebbe 1157, ma il denominatore congelato resta 1158. Recupero: 29 richieste, nessun nuovo binding certo. I formati legacy sono esaminati sui byte cached; nessun convertitore locale sicuro disponibile, nessuna conversione o installazione rivendicata. 403/429/robots rispettati. 1027 binding di risorsa, 979 active unambiguous, 48 condivisi: riconoscimento risorsa separato dall’identità. SHA comune non produce exact univoco.

Canonical 979/979 exact, 0 wrong, P/R 100%; 941 identità distinte. Byte e binding ufficiali già censiti, non una prova di scansioni nuove. Nessun documento o fonte aggiunto.

## Development e evaluation

Decisione `fingerprint-decision-v5`; dati fingerprint-v3 invariati, v1/v2 conservate. Soglie R8 mantenute, nessuna promozione basata sulla v5. Stato calibrazione `development_replay_complete`: 725/725 casi completati, 109 identità riservate al development. Noti: 458/582 exact, recall 78.69%, precision 100.00%; false accept 0, wrong known 0. Compilati validi R8 nel replay finale: 50/50 exact. Queste misure sono retrospettive e non soddisfano il gate di robustezza indipendente. Dati integrali in `calibration_v5.json`, `calibration_observations_v5.json` e `development_summary.json`. R6/R7, compilati validi R8, sole 50 osservazioni R8 salvate ora development, negativi storici e subset unknown confermato. Nessun tuning su nuove identità v5.

Primo tentativo development con veto di revisione mancante anche sulle firme forti: 325/582 exact, 184 rifiuti per revisione, 20/50 filled, 0 wrong. È conservato in `calibration_strict_veto_development_attempt.json` e `calibration_strict_veto_observations.json`. La regola era troppo ampia rispetto alla causa auditata: affinata sul solo fallback metadata prima di qualunque freeze/evaluation, poi replay completo ripetuto. Non si attribuisce indipendenza a nessuno dei due replay.

Generatore filled R8 immutato SHA `144cc2fea24b78718f6b7dc45b44c6a1ae0fe4ccbb209addc808269278dbbc57`. La precedente prova development 50/50 resta storica; nessuna nuova generation success v5 rivendicata. Validità dei valori fittizi meccanica, non amministrativa.

**Evaluation v5 NON ESEGUITA.** Freeze v5 non creato: coverage_file_backed, unknown_truth_adequate. Nessuna identità v5 selezionata e nessun riconoscimento v5 eseguito. Zero identità, fonti, rappresentazioni, scansioni, compilati e chiamate. P/R, entity/version errors e retrieval@1/@5/@10/@25 non misurati, non zero e non passati. File richiesti presenti con `status=not_run` e metriche vuote. Nessuna selezione anticipata o leakage check fittizio. Family: 0/16 valutabili, experimental/insufficiently validated; utile di release = exact soltanto.

Writer realmente usato per development/unknown: journal SQLite con transazioni FULL e case_id univoco, identità byte motore/input vincolata, ripresa soltanto dei mancanti; export temp+flush/fsync+replace atomico, conteggio completo e SHA finale. I JSON parziali non sono fonti di resume. Test crash forzato, duplicati conflittuali, conteggio, corruzione, concorrenza Windows e sharing violation. Nessun testo personale nei journal.

## Performance e memoria

Warm recognition p50 43.08 ms, p95 187.76 ms, p99 322.95 ms. Baseline R9 p95 323.04 ms, R8 finale 350.13 ms. La prima misura R9 dopo l'ottimizzazione delle intersezioni (p95 266.81 ms) è conservata in `performance_initial_optimization.json` e nel relativo profilo. Tra quella misura e la finale sono cambiati sia le regex preparate per richiesta sia l'ambito del veto di revisione: il confronto non è un'ablation pura della sola ottimizzazione. Ogni misura conserva gli hash effettivi del proprio motore.

402 richieste con nuovi contesti, senza cache globale degli input e senza shortcut SHA. Dataset fixed51 conservato, 14 scansioni storiche e 2 immagini incapsulate in PDF con OCR già disponibile; gruppi separati nei raw. OCR end-to-end estrazione `{"n": 14, "p50": 14993.6055, "p95": 15425.669, "p99": 15429.971}` ms separato dal recognition; queste scansioni sintetiche non rappresentano acquisizioni personali reali.

Il dataset fixed51 ha p95 249.88 ms, con margine molto piccolo sul target. I gruppi digital PDF (p95 338.96 ms) e filled AcroForm (p95 290.33 ms) superano 250 ms; il pass del gate aggregato non equivale a un pass di ogni formato.

Per gruppi `{"historical_fixed51": {"n": 306, "p50": 38.8363, "p95": 249.8768, "p99": 338.0568}, "representation:unknown": {"n": 210, "p50": 38.0631, "p95": 48.999, "p99": 56.5113}, "representation:digital_pdf": {"n": 60, "p50": 72.9565, "p95": 338.9603, "p99": 354.4637}, "representation:filled_acroform": {"n": 30, "p50": 159.6982, "p95": 290.3276, "p99": 304.5086}, "representation:docx": {"n": 6, "p50": 100.5391, "p95": 122.2188, "p99": 124.1022}, "historical_scans": {"n": 84, "p50": 97.6907, "p95": 135.7979, "p99": 142.7112}, "representation:image": {"n": 84, "p50": 97.6907, "p95": 135.7979, "p99": 142.7112}, "historical_scans_wrapped_pdf": {"n": 12, "p50": 112.3147, "p95": 119.405, "p99": 125.2088}, "representation:scanned_pdf": {"n": 12, "p50": 112.3147, "p95": 119.405, "p99": 125.2088}}`. Intersezioni native e tuple canoniche evitano boxing/ripetizioni, somma IDF nello stesso ordine del riferimento; regex anno/revisione preparate una volta per richiesta. Nessun pruning semantico: molte pagine restano candidate. Equivalence tests contro percorso indipendente e query dense; niente topK arbitrario che nasconda candidati. Normalizzazione e feature input solo nella richiesta.

Indice 89725169 bytes, 3476 pagine, disco 50850344 bytes. RSS `{"before_warm_bytes": 387149824, "after_warm_bytes": 422449152, "samples": [422449152, 452243456, 482566144, 513859584, 543604736, 573353984, 604073984], "growth_after_warm_bytes": 181624832}`. Il costo memoria delle tuple è dichiarato e resta sotto 100 MB. Component probes non additivi, fusion include altri componenti; entity/version probe su cinque candidati, non misura integrale di tutti i veti.

RSS dopo warm 422449152 bytes, poi crescita di 181624832 bytes nei sei cicli. La stabilità della memoria di processo non è dimostrata; la causa della crescita non è stata isolata. Il gate dei 100 MB riguarda l'indice, non l'intero processo. Questo limite resta esplicito anche con il gate di latenza aggregato superato.

| Componente (probe non additivo) | p50ms | p95ms |
| --- | --- | --- |
| normalization | 0.0152 | 0.2393 |
| input_fingerprint_generation | 0.5958 | 36.9651 |
| candidate_retrieval | 0.2986 | 1.9527 |
| ocr_sketch_compare | 0.059 | 10.745 |
| char_overlap | 0.0646 | 13.9473 |
| anchors | 0.0127 | 2.4265 |
| entity_version_checks | 0.0082 | 0.0154 |
| visual_compare | 0.008 | 2.2758 |
| decision_fusion_inclusive | 2.0209 | 186.7969 |
| family_fallback | 1.3304 | 9.973 |
| representation_classification | 0.0292 | 0.0365 |

## Test, CI e gate

Test `{"status": "passed", "passed": 749, "skipped": 3, "failed": 0, "seconds": 450.65, "log_sha256": "b60c62a1c7652a89a686bcd56da2ea98e735d29a80d223e4b7801d869086c285", "python": "3.12.10", "platform": "Windows-11-10.0.26300-SP0"}`. Verifica seed, hash corpus/raw storici, dichiarazioni del workflow offline Ubuntu/macOS/Windows e cinque critical cases in `verification.json`. CLI locale locked-v2 69/69 e compat-v2 37/37. I comandi storici senza corpus v2 (`scripts/benchmark.py` e `benchmarks.evaluate --fast`) continuano a segnalare i due rifiuti EX02/EX03 rispetto alle label v1: non sono presentati come green. Il workflow esistente li include; la sola verifica sintattica non prova quindi un'esecuzione CI riuscita. CI GitHub `external_pending`, nessun push. Collaudo locale Windows soltanto, nessuna validazione editoriale generale o collaudo su altre piattaforme rivendicato.

| Gate | Target | Risultato | Esito |
| --- | --- | --- | --- |
| historical_safety | 0 false accepts on historical NO | [] | PASS |
| round8_two_false_accepts | 0/2 accepted | 0 | PASS |
| R061 | NO_MATCH | "NO_MATCH" | PASS |
| truth_v2_complete | 0 unclassified | 0 | PASS |
| unknown_confirmed_count | >=100,target150 | 68 | FAIL |
| unknown_sources | >=8 | 4 | FAIL |
| unknown_concentration | <=25% | 0.6617647058823529 | FAIL |
| unknown_rejection | >=99%, no DOCUMENT/FAMILY accept | {"correct": 68, "total": 68, "false_accepts": 0} | PASS |
| coverage_file_backed | >=85% | 0.812607944732297 | FAIL |
| coverage_all | >=70% | 0.7764026402640264 | PASS |
| canonical | 100% P/R | {"exact": 979, "extraction_failed": 0, "family": 0, "reject": 0, "wrong": 0} | PASS |
| v5_identities | >=30 | null | FAIL |
| v5_sources | >=6 | null | FAIL |
| v5_representations | >=400 | null | FAIL |
| v5_scans | >=200 | null | FAIL |
| v5_valid_fills | >=50 | null | FAIL |
| v5_overall | P>=99.5%,R>=90%,entity/version errors0 | null | FAIL |
| v5_scan | P>=99.5%,R>=85% | null | FAIL |
| v5_filled | generation>=90%,P>=99.5%,R>=90% | null | FAIL |
| v5_retrieval_at25 | 100% | null | FAIL |
| performance_p50 | <=150ms | 43.0796 | PASS |
| performance_p95 | <=250ms | 187.7645 | PASS |
| index_memory | <=100000000bytes | 89725169 | PASS |
| process_memory_stability | measurement only; stability not established | {"before_warm_bytes": 387149824, "after_warm_bytes": 422449152, "samples": [422449152, 452243456, 482566144, 513859584, 543604736, 573353984, 604073984], "growth_after_warm_bytes": 181624832} | INFO/PENDING |
| tests | all green | {"status": "passed", "passed": 749, "skipped": 3, "failed": 0, "seconds": 450.65, "log_sha256": "b60c62a1c7652a89a686bcd56da2ea98e735d29a80d223e4b7801d869086c285", "python": "3.12.10", "platform": "Windows-11-10.0.26300-SP0"} | PASS |
| family | >=5 evaluable or experimental | 0 | INFO/PENDING |
| CI | external_pending | "external_pending" | INFO/PENDING |

## Archivio

`dist/BurOCRazia-v0.7.0-candidate-NOT-READY-round9.zip`, creato dal HEAD committato e verificato con hash/igiene/lock. SHA256 e commit esatti in `dist/package-verification.json` e `.zip.sha256`; non inseriti nel proprio contenuto per evitare riferimenti circolari. `evidence_locks.json` vincola le prove R9 e i blob Git storici R6/R7/R8, senza essere un freeze del motore. La versione pubblica rimane 0.6.1. Limiti bloccanti reali: coverage <85%, unknown insufficienti/sbilanciati e nessuna evaluation v5 qualificata; performance giudicata rispetto al gate 250 ms nella tabella, senza modificarlo.
