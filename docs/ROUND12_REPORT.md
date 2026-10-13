# Round 12 — NOT READY

Software pubblico **0.6.1**, schema **610**, target candidata **0.7.0**. Branch `codex/coverage-benchmark-v0.7.0`. HEAD iniziale `d911fccae4042c5c720a22d9e8767793a9aec61d`, working tree pulito. Commit finale e SHA dell'archivio sono registrati dopo il commit in `dist/package-verification-round12.json`, evitando autoreferenze. Nessun push, tag o release. CI external_pending.

## Decisione e coverage

La copertura resta **975/1158 = 84.196891%**, inferiore all'85%. Minimo matematico 985, iniziali 975, recuperati **0**, deficit **10**. Sul totale operativo: 975/1212 = 80.445545%. Il denominatore R6 è invariato; 942 identità univoche e 33 shared-only, separate dalla canonical accuracy.

Il pass ha esaminato tutti i 183 residui, riusando cache, osservazioni e audit R6–11. Le 5 richieste maintenance restano entro il budget di 24, con allowlist, robots e URL finali verificati. Due osservazioni di URL alternativi INAIL sono state rifiutate dai robots; nessun aggiramento. I formati ZIP sono ammessi solo come contenitore limitato con un unico documento nativo, senza percorsi pericolosi o payload aggiuntivi. Nessun nuovo PDF/DOCX ufficiale ha superato tutte le guardie d'identità.

Sono riuscite 40 conversioni locali di legacy primari già acquisiti. Le fingerprint di contenuto derivate sono registrate separatamente con SHA originale, derivato e ricevuta ufficiale; OCR non richiesto per questi sketch digitali. I file convertiti temporanei sono stati eliminati: `True`. Nessun testo integrale o file convertito è in Git. Queste conversioni non rendono il MIME originale supportato dal runtime congelato. Il contratto v3 non rappresenta una derivazione come byte canonici ufficiali nativi: non si etichetta il PDF derivato come file ufficiale, né si aggiungono questi sketch al numeratore.

Le nuove associazioni Garante 174/177 richiederebbero una valutazione completa dei gruppi già associati a 175/1213; non sono state promosse soltanto per aumentare il conteggio. Le associazioni shared non pertinenti restano escluse. Il controllo diretto Round 12 sulle risorse shared non osserva tier `A_exact_sha`.

Nel Round 11 il runner canonical aveva riscritto `shared_resource_audit.json` con l'audit generico dei gruppi. Tale raw storico è conservato. Il nuovo `shared_eligibility_audit.json`, con nome distinto, conserva regole pubblicate, binding, gruppi, motivazioni e prove dirette senza essere sovrascritto dal runner.

| Fonte | File-backed | Supportate | Residue |
| --- | --- | --- | --- |
| ade | 90 | 0 | 90 |
| anac | 7 | 7 | 0 |
| funzione_pubblica | 9 | 9 | 0 |
| garante_privacy | 10 | 6 | 4 |
| giustizia | 142 | 130 | 12 |
| inail | 347 | 315 | 32 |
| inl | 45 | 44 | 1 |
| inps | 359 | 359 | 0 |
| lavoro | 102 | 76 | 26 |
| mef | 1 | 1 | 0 |
| mimit | 42 | 27 | 15 |
| unioncamere | 4 | 1 | 3 |

## Unknown release

Master **125**, release **105**, **10 fonti**, concentrazione massima **23.809524%**, 12 tipi. Manifest immutato SHA `60246fc4e63f41f55b367141ec4ab5b45c08fc42db7d30d5a2551e8c19ad70be`; seed di selezione **2026101311**. Selezione deterministica per quote e gruppi, ricalcolata identica, indipendente da score o predizioni. Audit confirmed_unknown e relazioni catalogo/famiglie conservati; nessuna risorsa usata per tuning Round 12. L'esposizione storica resta esplicita: **55 già riconosciuti nei round precedenti, 50 mai riconosciuti**.

**Non eseguito**: il punto 7 del prompt vieta di iniziare il single-shot con coverage sotto l'85%. `unknown_release_v1.json` registra status not_run, zero chiamate e metriche null. N selezionato 105, N eseguito 0; correct NO_MATCH, wrong DOCUMENT_MATCH, wrong FAMILY_MATCH, false acceptance rate, rejection rate, CI 95%, metriche per fonte e tipo **non misurate**. Non si usa il risultato development per riempire questo vuoto.

## Historical safety e canonical

Prove misurate Round 11 conservate: **241 NO storici, zero false accept**, R061 e i due NO Round 8 corretti, cinque vecchi casi critici sicuri; canonical **980/980**. Non sono presentate come nuovo rerun post-unknown Round 12: quello stadio non è stato aperto. Runtime, catalogo, fingerprint, soglie, pesi, scoring, ranking, tier, veti e family restano identici byte per byte al Round 11. I nuovi test infrastrutturali e il rerun pytest sono misure separate. Le divergenze storiche delle label v1 rimangono visibili (base 33/35, locked v1 59/69; locked v2 69/69), senza tuning.

## Stabilità performance

Baseline prima delle modifiche: p50 58.4073 ms, p95 **275.5781 ms**, N=402, worker R9 invariato. Seguono esattamente cinque run warm predeterminati nello stesso processo isolato, stesso hardware/corpus: 67 input, sei passaggi accoppiati avanti/indietro per run. Nessuna selezione dei run favorevoli o ottimizzazione del motore. Ogni richiesta ricrea RequestPages, feature e memo locali; solo indice/catalogo pubblici restano warm.

| Run warm | N | p50 ms | p95 ms | Digital p95 ms | Scan p95 ms | <=250 ms |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 402 | 43.2193 | 195.6687 | 341.5812 | 140.4222 | PASS |
| 2 | 402 | 59.7579 | 261.1139 | 376.807 | 165.4827 | FAIL |
| 3 | 402 | 62.574 | 259.0858 | 376.3929 | 167.4023 | FAIL |
| 4 | 402 | 45.7215 | 217.834 | 348.3414 | 147.2383 | PASS |
| 5 | 402 | 42.1705 | 202.9763 | 340.1499 | 150.5436 | PASS |

**Median p95: 217.8340 ms**; gate obbligatorio <=250 ms: **PASS**. Run sotto soglia: **3/5**; stabilità preferita >=4/5: **FAIL**. Run oltre 275 ms: 0; fragilità prudenziale dichiarata prima della misura: False. Il valore mediano è la mediana dei cinque p95, non un quantile pooled. Tutti i 2010 tempi individuali, ambiente CPU/processo e marker warm sono nel raw.

Recognition-only esclude estrazione/OCR e include fingerprint dell'input e rendering visuale lazy. Digital e scan recognition-only sono separati nei gruppi di ogni run. OCR end-to-end sui 14 input sintetici storici, in ms: `{"n": 14, "p50": 14883.5728, "p95": 15401.5472, "p99": 15501.6007}`. Il tempo Tesseract non entra nel gate dei 250 ms. Il cambiamento rispetto al p95 Round 11 di 248.23 ms non è attribuito a modifiche semantiche; le condizioni di scheduling e la variazione non sono state isolate sperimentalmente. Nessun collaudo su scansioni personali o altre piattaforme rivendicato.

## Prerequisiti, freeze ed evaluation v5

Tutti i campi richiesti sono in `prerequisite_gate.json`: `{"coverage_file_backed_percent": 84.19689119170984, "coverage_file_backed_pass": false, "coverage_all_percent": 80.44554455445545, "coverage_all_pass": true, "unknown_release_count": 105, "unknown_release_sources": 10, "unknown_release_max_concentration": 0.23809523809523808, "unknown_rejection_rate": null, "unknown_rejection_pass": false, "historical_safety_pass": true, "canonical_pass": true, "performance_median_p95": 217.834, "performance_pass": true, "performance_stability_pass": false, "tests_pass": true, "ready_to_freeze": false}`. Il gate unknown è non misurato; il suo pass=false non indica una rejection osservata insufficiente. Safety/canonical sono prove conservate su byte invariati. La stabilità 4/5 è preferita, la mediana è obbligatoria. `ready_to_freeze=false`.

Freeze **non eseguito**, commit freeze assente. Evaluation v5 **non costruita né eseguita**: adeguatezza del pool, known identities/fonti/rappresentazioni/scansioni/compilazioni valide/unknown mix non misurati. Exact, family, reject, wrong, precision, recall, errori ente/versione, retrieval @1/@5/@10/@25, scan e filled generation/recognition, unknown end-to-end non misurati. Nessun risultato assente trattato come zero o PASS. Nessuna RC. Family: **experimental / insufficiently validated**, zero famiglie reali identity-held-out qualificabili nel benchmark R9 conservato; non usata per useful recall.

| Gate | Target | Risultato | Esito |
| --- | --- | --- | --- |
| coverage_file_backed | >=85% | 84.196891% | FAIL |
| coverage_all | >=70% | 80.445545% | PASS |
| unknown_release_count | >=100 selected | 105 | PASS |
| unknown_release_sources | >=8 | 10 | PASS |
| unknown_release_concentration | <=25% | 23.809524% | PASS |
| unknown_rejection | >=99% | non misurato | NON MISURATO |
| historical_safety | 0 confirmed false accepts | 0 | PASS R11 / BYTE INVARIATI |
| canonical | 100% unambiguous | 980/980 | PASS R11 / BYTE INVARIATI |
| performance_median_p95 | <=250 ms | 217.8340 ms | PASS |
| performance_stability | >=4/5 p95<=250 ms preferred | 3 | FAIL |
| tests | 0 failures | {"passed": 767, "failed": 0, "skipped": 3} | PASS |
| v5_known_identities | >=30 | non misurato | NON MISURATO |
| v5_sources | >=6 | non misurato | NON MISURATO |
| v5_representations | >=400 | non misurato | NON MISURATO |
| v5_scans | >=200 | non misurato | NON MISURATO |
| v5_valid_fills | >=50 | non misurato | NON MISURATO |
| v5_unknown_mix | >=30 | non misurato | NON MISURATO |
| v5_leakage | 0 prohibited | non misurato | NON MISURATO |
| v5_validity | expected==actual==unique; atomic/schema/SHA | non misurato | NON MISURATO |
| v5_precision | >=99.5% | non misurato | NON MISURATO |
| v5_exact_recall | >=90% | non misurato | NON MISURATO |
| v5_wrong_accepted | <=0.5% | non misurato | NON MISURATO |
| v5_entity_errors | 0 | non misurato | NON MISURATO |
| v5_version_errors | 0 | non misurato | NON MISURATO |
| v5_scan | precision>=99.5%, recall>=85% | non misurato | NON MISURATO |
| v5_filled_generation | >=90% | non misurato | NON MISURATO |
| v5_filled_recognition | precision>=99.5%, recall>=90% | non misurato | NON MISURATO |
| v5_retrieval_at25 | 100%; @1 preferred99% | non misurato | NON MISURATO |
| v5_unknown_end_to_end | >=99% rejection | non misurato | NON MISURATO |
| family | >=5 real identity-held-out families or experimental | experimental / insufficiently validated | INFO |
| CI | external pending | external_pending | PENDING |

## Test e integrità

Suite completa: **767 passed, 0 failed, 3 skipped**, 396.91 s; Python 3.12.10, Windows-11-10.0.26300-SP0. Skip: privilegio symlink Windows e due FIFO. Log SHA `cdba6fe75e2eba4ffdeb1d6335f88761e497075ad3af73a12fc0c50caddd6af9`. Cinque nuovi test coprono archivi pericolosi, fallimenti permanenti, isolamento delle feature per richiesta, mediana/stabilità e blocco unknown prima del gate coverage. Il writer transazionale già presente è rieseguito nella suite (interruzione, resume, duplicati, count, rename atomico e SHA), senza iniziare evaluation.

Catalog integrity OK, zero violazioni FK, zero documenti reali senza provenance; seed SHA `790b690123c82e1cb7bdfa67a10216284022987d50b0abbcc4a1a245785e3e99`. 1216 reali, 1212 operativi, 19 fonti, 16 famiglie. Nessuna nuova identità/fonte o versione pubblica. CI **external_pending**; soltanto Windows locale verificato. Nessuna validazione editoriale o verifica automatica attribuita ai record.

## Archivio e limiti residui

`dist/BurOCRazia-v0.7.0-candidate-NOT-READY-round12.zip`, da commit locale. Commit finale e SHA256 in `dist/package-verification-round12.json` e `.zip.sha256`, esterni al proprio contenuto. Verifica per byte sorgenti misurati, catalogo, corpus congelati, raw storici, manifest unknown, fingerprint e igiene; archivi Round 8–11 conservati e verificati.

Limiti effettivi: deficit di 10 supporti file-backed; nessuna nuova fingerprint nativa valida; legacy fuori dal contratto runtime; rejection release non misurata per STOP coverage; performance come riportata nei cinque run, senza margine presunto; stabilità RSS non rimisurata e limite Round 11 ancora aperto; nessuna evaluation v5; family sperimentale; CI pending. Il Round 12 non ha chiuso i prerequisiti e conserva lo stato **NOT READY**.
