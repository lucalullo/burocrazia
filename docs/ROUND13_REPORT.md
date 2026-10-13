# Round 13 — NOT READY

Software pubblico **0.6.1**, schema **610**, target candidata **0.7.0**. Branch `codex/coverage-benchmark-v0.7.0`, ingresso HEAD `77bbe149a52102d5ca42743702c5b39f5a475326`, working tree pulito. Commit finale e SHA ZIP sono in `dist/package-verification-round13.json`, esterni all'archivio per evitare autoreferenze. Nessun push, tag o release. CI external_pending.

## Audit legacy e semantica della coverage

40 tentativi su 40 identità e 40 originali distinti: 22 DOC, 1 RTF, 8 XLS, 9 XLSX. Tutte le conversioni sono state ripetute due volte. Normalizzazione di metadati, ID e ordine del grafo degli oggetti PDF; SHA normalizzati uguali nello stesso ambiente/converter/profilo. I PDF restano temporanei e non sono committati; original URL/SHA/MIME/data e derived SHA sono distinti nel manifest ufficiale legacy. Le fingerprint di massimo cinque pagine digital/layout sono persistite; OCR non richiesto e dichiarato come tale. Il runtime non importa il convertitore e non accetta nuovi formati di upload.

La sola validazione del contratto source/provenance v3 è estesa per gli originali legacy. MIME e SHA restano quelli originali, non quelli di un falso PDF ufficiale. Il PDF di test ha SHA derivato diverso: nessun caso legacy passa con `official_file_sha256_exact`. Feature, indice, scoring, ranking, soglie, pesi, fusion, veti e parametri hanno AST/byte invariati rispetto al Round 12, come verificato in `semantic_invariance.json`. Il digest runtime dei byte cambia per il validatore; non si dichiara identità byte del modulo modificato.

Definizione **fissata prima dell'aggregato**: SHA `7d13aa4fcc7e6b3bb86a2d43c3e8ec203d6628f86cf9e43291176affb2b6c037`. I report Round 5–12 parlano di firme attive/supporto, senza una definizione fondante native-only. Round 10–12 escludevano derivati non indicizzati: limite implementativo, distinto dal supporto upload. Decisione e prove sono in `FINGERPRINT_COVERAGE_SEMANTICS.md`; nessun denominatore ridotto e nessun cambio della definizione dopo i risultati.

Qualificazione iniziale: 28/40. L'adjudicazione incrociata ha poi rilevato due exact errati: 617 e 619 riconosciuti come 618 tramite pagina canonica 2, con canali digital/char/anchor saturati. Sono tre domande diverse con pagina comune; tutti i tre binding sono ora **shared/ambiguous**. Le osservazioni iniziali, CSV iniziale e bundle precedente sono preservati (ricostruzione byte-esatta dai tre record originali). Dopo la correzione: **27 legacy runtime-usable**, **13 esclusi**, zero wrong document nei 40 controlli finali. I casi riconosciuti soltanto dal fallback metadati non sono contati come fingerprint support. Ambiguità irrisolte restano escluse.

Native coverage: **975/1158 = 84.196891%**. Runtime-usable coverage: **1002/1158 = 86.528497%**, incluse 33 associazioni shared storiche di solo supporto risorsa e 27 nuove identità legacy qualificate. Sul totale operativo: 82.673267%. Minimo 985, deficit 0. Gate coverage PASS; native-only resta separato e sotto 85%. Nessun nuovo crawling necessario: `final_recovery.csv` conserva il solo schema perché il deficit è zero. Nessuna nuova fonte o identità di catalogo.

## Unknown release e motivo dello STOP

Manifest immutato SHA `60246fc4e63f41f55b367141ec4ab5b45c08fc42db7d30d5a2551e8c19ad70be`, seed 2026101311: 105 confirmed unknown, 10 fonti, max 23.809524%, 12 categorie. 55 erano già osservati nei round precedenti, 50 non lo erano; nessuna falsa indipendenza rivendicata. Primo single-shot R13 sul bundle **prima** dell'adjudicazione: **105/105 NO_MATCH**, 0 DOCUMENT_MATCH errati, 0 FAMILY_MATCH errati, 0 errori di estrazione, 0 errori ente; rejection 100%, false acceptance 0%. Wilson 95% **96.470592–100%**. Metriche per fonte/categoria nei raw; l'intervallo è descrittivo del set, non una garanzia di popolazione.

Errore nell'ordine del lavoro: il single-shot è stato avviato prima di chiudere il controllo incrociato delle ambiguità legacy. La correzione, motivata esclusivamente dai casi legacy e non dagli esiti unknown, cambia il dataset fingerprint. Bundle misurato `d10650139b16d9809f3a08d7065572e4536e4a1094a710039de0ae1888ea423c`; bundle corretto `eaac87ac81e03ba838b52d66992db20967e8c50bbcfd88b02d894c42ab68f4bd`. Il risultato resta valido per il primo bundle e viene conservato integralmente. **Non è stato ripetuto né trasferito al bundle corretto.** Il prerequisito unknown per la candidata corrente è quindi non misurato, `unknown_pass=false`, pur con il precedente rate osservato del 100%. Questo è il blocco del freeze.

Writer transazionale: expected=actual=unique=105, export atomico e SHA `c5ad5d858ad7af9ff2b9e6d68d12873c4527831a3cc89bc9811717bc15f70fdb`. Zero duplicati; journal ignorato da Git. Il risultato e il manifest non sono stati modificati dopo l'apertura degli esiti. Nessuna modifica al motore, alle etichette o alla selezione unknown.

## Safety, canonical e performance

Rerun sulla candidata corretta: **241 NO storici, false accept 0**; R061 NO, due casi Round 8 NO, cinque vecchi critici sicuri. Canonical native **980/980**, legacy qualificati **27/27**; shared separate. Le etichette ambigue storiche v1 restano visibili: base 33/35, locked v1 59/69; locked v2 69/69. Nessuna nuova etichetta inventata o promozione editoriale.

Gate storico performance: **mediana p95<=250 ms** obbligatoria; 4/5 run<=250 è preferito, non trasformato in blocker. Cinque run warm confermati sulla candidata corretta, 67 input e 402 richieste per run, passaggi accoppiati avanti/indietro, nuovi RequestPages e feature per richiesta. Stesso corpus/hardware, OCR escluso dal gate.

| Run warm | p50 ms | p95 ms | Digital p95 | Scan p95 |
| --- | --- | --- | --- | --- |
| 1 | 48.3701 | 207.0979 | 338.4964 | 149.1394 |
| 2 | 46.1169 | 215.5789 | 346.3508 | 160.5881 |
| 3 | 48.748 | 216.2203 | 335.8493 | 143.5693 |
| 4 | 58.6483 | 216.6899 | 360.3352 | 151.2189 |
| 5 | 40.2919 | 202.6467 | 299.4206 | 118.8434 |

Mediana p95 **215.5789 ms**, massimo **216.6899 ms**, 5/5 sotto 250; gate obbligatorio **PASS**. Nessun run favorevole selezionato, nessun tuning. OCR end-to-end separato sui 14 input sintetici, in ms: `{"n": 14, "p50": 16047.0557, "p95": 18262.9901, "p99": 19123.8956}`. Nessun collaudo su scansioni personali o altre piattaforme rivendicato. Stabilità RSS non dimostrata; limite precedente ancora aperto.

## Prerequisiti, freeze ed evaluation

`{"coverage_definition": "runtime_usable_fingerprint_supported", "coverage_percent": 86.52849740932642, "coverage_pass": true, "unknown_release_count": 105, "unknown_sources": 10, "unknown_max_concentration": 0.23809523809523808, "unknown_rejection_rate": 1.0, "unknown_pass": false, "canonical_pass": true, "historical_safety_pass": true, "performance_median_p95": 215.5789, "performance_pass": true, "tests_pass": true, "ready_to_freeze": false}`. `unknown_binding_current=false`: rate storico misurato e requisito corrente sono distinti. **Nessun freeze, nessun commit freeze, nessuna RC.** Evaluation v5 non selezionata, costruita o eseguita; preflight pool/identità/fonti/rappresentazioni/scansioni/filled/unknown mix non misurati. Exact/family/reject/wrong/P/R, errori ente/versione, retrieval @1/@5/@10/@25, scan, filled generation/recognition e unknown end-to-end non misurati. Nessun valore assente trattato come zero/PASS. Family **experimental / insufficiently validated**, meno di 5 famiglie reali qualificate; non usata per useful recall.

| Gate | Target | Risultato | Esito |
| --- | --- | --- | --- |
| runtime_usable_coverage | >=85% | 86.52849740932642 | PASS |
| all_operational_coverage | >=70% | 82.67326732673267 | PASS |
| unknown_count | >=100 | 105 | PASS |
| unknown_sources | >=8 | 10 | PASS |
| unknown_concentration | <=25% | 23.809523809523807 | PASS |
| unknown_measured_earlier_candidate | >=99% | 100.0 | PASS |
| unknown_current_candidate | >=99%, exact dataset binding | non misurato | BINDING INVALIDATED / NON MISURATO |
| historical_safety | 0 false accepts | 0 | PASS |
| canonical_native | 100% | "980/980" | PASS |
| canonical_legacy | 100% qualified | "27/27" | PASS |
| performance_median_p95 | <=250ms | 215.5789 | PASS |
| performance_four_of_five | preferred>=4/5 | 5 | PASS |
| tests | 0 failures | {"passed": 772, "failed": 0, "skipped": 3} | PASS |
| v5_known_identities | >=30 | non misurato | NON MISURATO |
| v5_sources | >=6 | non misurato | NON MISURATO |
| v5_known_representations | >=400 | non misurato | NON MISURATO |
| v5_scans | >=200 | non misurato | NON MISURATO |
| v5_valid_fills | >=50 | non misurato | NON MISURATO |
| v5_unknown_mix | >=30 | non misurato | NON MISURATO |
| v5_leakage | 0 prohibited | non misurato | NON MISURATO |
| v5_validity | expected==actual==unique, atomic/schema/SHA | non misurato | NON MISURATO |
| v5_precision | >=99.5% | non misurato | NON MISURATO |
| v5_exact_recall | >=90% | non misurato | NON MISURATO |
| v5_entity_errors | 0 | non misurato | NON MISURATO |
| v5_version_errors | 0 | non misurato | NON MISURATO |
| v5_scan | P>=99.5%,R>=85% | non misurato | NON MISURATO |
| v5_filled | generation>=90%,P>=99.5%,R>=90% | non misurato | NON MISURATO |
| v5_retrieval | @25=100%, @1 preferred99% | non misurato | NON MISURATO |
| v5_unknown_end_to_end | rejection>=99% | non misurato | NON MISURATO |
| family | >=5 qualified real families or experimental | "experimental / insufficiently validated" | INFO |
| CI | external pending | "external_pending" | PENDING |

## Test, integrità, archivio e limiti

Pytest completo: **772 passed, 0 failed, 3 skipped**, 395.9s; Python 3.12.10, Windows-11-10.0.26300-SP0. Log SHA `6856e714554eaa5101b83a35f7bf7edfe1bc1e9ab6a3bbaaed2a8a19e523b32d`. Skip Windows: symlink senza privilegio e due FIFO. Test di provenance, input legacy ancora rifiutato, normalizzazione PDF, invarianza scoring e controllo shared; writer interruption/resume/dedupe/count/atomic/SHA coperti dalla suite. Solo verifiche locali; CI external_pending.

Catalog integrity/FK OK, provenance complete; seed SHA `790b690123c82e1cb7bdfa67a10216284022987d50b0abbcc4a1a245785e3e99` invariato, 1216 reali/1212 operativi, 19 fonti, 16 famiglie. I 1028 record fingerprint pre-R13 sono intatti. Corpus e raw storici preservati, archivi Round 8–12 conservati e verificati. Nessun file personale, convertito, database di lavoro o credenziale in Git.

ZIP: `dist/BurOCRazia-v0.7.0-candidate-NOT-READY-round13.zip`. Commit finale/SHA256 nel verificatore esterno e `.zip.sha256`. Limiti effettivi: 13 legacy non qualificati, gruppo Unioncamere ambiguo, unknown corrente senza misura valida legata al dataset, nessuna evaluation v5, family sperimentale, RSS non stabilizzata, CI pending. La coverage metodologicamente corretta passa; la validazione congiunta della candidata resta **NOT READY**.
