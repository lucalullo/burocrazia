# Round15 — NOT READY

Software pubblico **0.6.1**, schema **610**, branch `codex/coverage-benchmark-v0.7.0`. Ingresso `425fa010063692d5d8ed090431068ad014d86ee6`, working tree pulito. **Nessun freeze Round15**: il prerequisito performance è fallito. Il freeze Round14 `37a9d1f3125b9e0480d2592f479554fe5ea40a0a` resta storico. Commit finale e SHA dell'archivio nel verificatore esterno `dist/package-verification-round15.json`, per evitare autoreferenze. Nessun push, tag, pubblicazione o RC. CI **external_pending**.

## Adjudication ufficiale

Tre DOCUMENT_MATCH storici, con i due INAIL inclusi nelle tre risorse. **1 confirmed_unknown / falso positivo confermato** (ANAC), **0 actually_catalog_document confermati**, **2 ambiguous_truth** (INAIL), 0 errori di truth esatta dichiarati dimostrati. Per INAIL è dimostrata la qualificazione storica insufficiente come confirmed_unknown: stesso sottotipo di domanda del fondo amianto, annualità2024/2025 diverse dal canonico2023, versione catalogo nulla. Non è dimostrata l'equivalenza di identità tra anni, né una sostituzione ufficiale. Nessuna regola del motore è stata modificata sulla base dei due dubbi. Il fingerprint della pagina condivisa spiega il match, non decide la truth.

La fonte ANAC distingue la bozza normativa di17 pagine dal modulo individuale A.7: nessuna identità/famiglia del catalogo rappresenta la bozza. Fonti, titoli, codici assenti, anni, URL, ricevute SHA e date effettive in `round15_truth_adjudication.json`, `reference_truth_v3.json`, `official_truth_evidence.json`; [adjudication dettagliata](ROUND15_TRUTH_ADJUDICATION.md). ANAC cache HTTP200 del12 ottobre; nessun bypass del403 web o nuova data di download inventata. INAIL pagina moduli acquisita il13 ottobre. Decisioni completate prima del fix, hash del motore di partenza registrato. Tutte le risorse osservate/ambigue escluse dai futuri gate indipendenti.

## Contratto pagine e input-safety

Limite100 pagine preesistente dal commit `059c3168041dbd0fb33a7fba89dee22f4d0b1968`, 6 settembre2026, antenato del freeze Round14; documentato da README/ESTRAZIONE. Rifiuto ExtractionError prima di OCR/riconoscimento. I quattro file Round14 di218/275/217/166 pagine restano nel risultato storico114. Solo nei futuri benchmark si separano classificazione entro i limiti e input-safety fuori limite. L'assenza di preflight adeguato Round14 non viene cancellata.

Input-safety v1: **9/9**, PASS. Quattro PDF ufficiali oltre100 pagine; upload oltre20MiB; formato non supportato; testo oltre1M caratteri; MIME incompatibile; percorso ZIP/DOCX non valido. **0 crash, 0 residui nella directory temporanea isolata, 0 risultati documento, 0 chiamate recognition**. Ricevute o generatori deterministici e SHA nel manifest; raw degli errori distinti dai NO_MATCH di classificazione. Non è una dimostrazione esaustiva di ogni combinazione dei parser; gli altri limiti restano coperti dai test automatici.

## Fix e regressione

Unica modifica runtime: `_informational_heading` riconosce gli introduttori bozza/schema/proposta, con di facoltativo, prima di un'intestazione informativa esplicita. Risolve la bozza di regolamento accettata tramite fallback titolo/ente. Finestre800 caratteri/prime6 righe, fingerprint, soglie, pesi, ranking, catalogo, fonti, dataset e policy invariati. Nessuna blacklist ID/URL. [Root cause](../benchmarks/results/round15/false_acceptance_root_causes.md). Test del testo ufficiale sul percorso normale/full scan e controesempi di modulo che cita una bozza nel corpo; test mirati16/16.

V2 resta **historical_unknown_release_v2_round14**: **107/114**, 3 DOCUMENT_MATCH, 0 FAMILY_MATCH, 4 errori, con manifest/raw/label/metriche originali intatti. Replay autorizzato separato **development_regression_after_round15_fix**: **108/114** sulle label storiche, **2 DOCUMENT_MATCH** (due INAIL ambigui), 0 FAMILY_MATCH, 4 errori; ANAC ora NO_MATCH. Non è un release gate, non corregge il107/114 e non trasforma i due ambigui in errori confermati del motore.

Historical safety: **241 NO, 0 false acceptance**, R061, cinque ufficiali critici, due casi Round8 e hard negatives PASS. V1/v2 storici distinti, inclusi development33/35 e locked v1 59/69; nessuna etichetta riscritta per ottenere un PASS. Compat v2 37/37; hard negatives30/30 e100/100; family storico161/161.

## Coverage e canonici

Coverage **1002/1158 = 86.528497%**, PASS>=85. Totale operativo **1002/1212 = 82.673267%**, PASS>=70. Denominatori e definizione congelati. 975 supporti nativi/associazioni storiche più27 legacy qualificate; 33 shared di solo supporto risorsa, non nuova accuratezza di identità. Bundle e catalogo byte-identici all'ingresso. Canonici rieseguiti dopo il fix: **980/980 nativi, 27/27 legacy**, PASS100%, binding e derivazioni verificati.

## Performance e arresto prima del freeze

| Run | p50 ms | p95 ms |
|---|---|---|
| 1 | 48.7097 | 215.0934 |
| 2 | 66.9108 | 263.0707 |
| 3 | 66.4942 | 259.0395 |
| 4 | 66.5482 | 283.8871 |
| 5 | 63.6686 | 285.658 |

Mediana p95 **263.0707ms**, FAIL<=250. **1/5** run sotto250; due oltre275, fragilità prudente segnalata. Cinque run prefissati, 402 richieste ciascuno, 67 input/2010 tempi. Warm recognition con contesti nuovi per richiesta, OCR/estrazione separati nei raw; processo isolato durante la misura. Nessun campione eliminato, ottimizzazione o rerun favorevole. Runtime del risultato verificato contro quello finale. Il fallimento impedisce il freeze: la misura non viene sostituita dai247.14ms storici Round14.

## Unknown v3 ed evaluation v5

**Non selezionati e non eseguiti**: stop prima del freeze per prerequisito performance FAIL. Unknown v3 N/fonti/concentrazione/correctreject/falseDOC/falseFAMILY/rate/CI **non misurati**, 0 chiamate release, nessun manifest finale o freeze fittizio. Non si usa v2 development come benchmark indipendente. Registro contaminazione v2 aggiuntivo: 617 identità known escluse, 416 potenzialmente eleggibili, 114 SHA v2 storici, 2460 SHA osservati complessivi. Le potenzialmente eleggibili non sono una preflight v5: non ne dimostrano fonti, trasformazioni o validità dei filled.

V5 preflight identità/fonti/rappresentazioni/scans/filled **non misurata**; nessuna selezione/generazione/leakage check/predizione. V5 exact/family/reject/wrong/P/R/errori ente/versione, retrieval@1/@5/@10/@25, scan, filled generation/P/R e unknown end-to-end **non misurati**. Family **experimental / insufficiently validated**: nessuna nuova dimostrazione su>=5 famiglie reali identity-held-out, nessun useful recall gonfiato. Condizione “unknown v3 passa” non soddisfatta; output v5 condizionali non fabbricati.

## Verifiche finali

Baseline pytest **777 passed, 0 failed, 3 skipped**; finale **786 passed, 0 failed, 3 skipped**, 531.32s. Il primo run completo (784 passed, 1 failed, 3 skipped) è preservato in initial_validation_failure.json: il test Round13 applicava ancora il vincolo dei byte storici al motore corrente. Ora verifica esattamente il commit finale Round13, senza checkout, e un nuovo test AST/byte verifica che il motore corrente differisca soltanto nella funzione di intestazione autorizzata. Nessun cambiamento runtime o di performance per risolvere il test. Un successivo comando mirato ometteva PYTHONPATH dei tool QA (pypdf assente nel solo venv): log preservato, ambiente completo ripristinato per la suite finale. Skip Windows: symlink senza privilegio e due FIFO. SHA log nel test report; Python 3.12.10. Test sintetici, Tesseract locale, integrità e adjudication editoriale distinti; nessun nuovo collaudo Linux/macOS o CI esterna rivendicato.

Compile, SQLite integrity/FK, copia/migrazione schema610 con conteggi invariati, binding, tre validator fingerprint, compat-v2 CLI, schema truth v3 e count/SHA input-safety PASS. Riepilogo finale verificato anche con AppTest: navigazione Benchmark/Catalogo e storico rifiutati, 1/1 PASS. Release-fast effettivo **exit1**, storici EX02/EX03 invariati: **FAIL del requisito zero failures**, nessuna dichiarazione di CLI tutta verde. Verificati 434 blob storici e gli archivi Round8–14. Package verification separata controlla ZIP, sorgenti misurati, catalogo, lock storici, nuovi artifact e assenza di file personali/cache/DB di lavoro. I risultati finali sono sul candidato corrente; un freeze Round15 non è stato autorizzato.

## Gate table

| Gate | Target | Actual | Esito | Obbligatorio |
| --- | --- | --- | --- | --- |
| truth_adjudication | 3 official decisions before engine edit; ambiguous excluded | {'confirmed_unknown': 1, 'actual_catalog_document': 0, 'ambiguous': 2, 'release_eligible': 0} | PASS | sì |
| fingerprint_coverage | >=85% | 86.52849740932642 | PASS | sì |
| all_operational | >=70% | 82.67326732673267 | PASS | sì |
| canonical_native | 100% | 980/980 | PASS | sì |
| canonical_legacy | 100% | 27/27 | PASS | sì |
| historical_safety | 241 NO; 0 false accepts | {'n': 241, 'false_accepts': 0} | PASS | sì |
| confirmed_ANAC_regression | NO_MATCH | NO_MATCH | PASS | sì |
| input_safety | all safe rejects/no crash/no residue | 9/9 | PASS | sì |
| performance_median_p95 | <=250ms | 263.0707 | FAIL | sì |
| performance_four_of_five | preferred>=4/5 | 1 | PREFERITO NON RAGGIUNTO | no |
| unknown_v3_sample | >=100 confirmed unknown,8sources,max25% | non misurato | NON MISURATO | sì |
| unknown_v3_rejection | >=99% | non misurato | NON MISURATO | sì |
| unknown_v3_wrong_document | <=1% | non misurato | NON MISURATO | sì |
| unknown_v3_entity_version | 0 | non misurato | NON MISURATO | sì |
| v5_preflight | >=30IDs,6sources,400reps,200scan,50filled,30unknown | non misurato | NON MISURATO | sì |
| v5_leakage | 0 prohibited | non misurato | NON MISURATO | sì |
| v5_precision | >=99.5% | non misurato | NON MISURATO | sì |
| v5_exact_recall | >=90% | non misurato | NON MISURATO | sì |
| v5_entity_version | 0 | non misurato | NON MISURATO | sì |
| v5_scan_precision | >=99.5% | non misurato | NON MISURATO | sì |
| v5_scan_recall | >=85% | non misurato | NON MISURATO | sì |
| v5_filled_generation | >=90% | non misurato | NON MISURATO | sì |
| v5_filled_precision | >=99.5% | non misurato | NON MISURATO | sì |
| v5_filled_recall | >=90% | non misurato | NON MISURATO | sì |
| v5_retrieval_at25 | 100% | non misurato | NON MISURATO | sì |
| v5_retrieval_at1 | target>=99% | non misurato | NON MISURATO | sì |
| v5_unknown_mix | >=99% rejection | non misurato | NON MISURATO | sì |
| release_freeze | Dedicated commit after all prerequisites | non misurato | NON MISURATO | sì |
| unknown_v3_freshness | 0 prior SHA or obvious near-resource reuse | non misurato | NON MISURATO | sì |
| unknown_v3_supported_truth | Confirmed unknown, supported input only | non misurato | NON MISURATO | sì |
| unknown_v3_types | >=5 types | non misurato | NON MISURATO | sì |
| unknown_v3_family_acceptance | Counts as false acceptance | non misurato | NON MISURATO | sì |
| pytest | 0 failures | {'passed': 786, 'failed': 0, 'skipped': 3} | PASS | sì |
| compile_integrity_FK_migrations_schema | 0 failures | True | PASS | sì |
| release_fast_cli | exit0 | 1 | FAIL | sì |
| family_identity_holdout | >=5 real families | experimental / insufficiently validated | EXPERIMENTAL | no |
| CI | external pending | external_pending | PENDING | no |

## Limiti e archivio

Limiti reali: performance mandatory FAIL e fragilità, release-fast storico nonzero, due annualità INAIL irrisolte/escluse dai gate, unknown v3 e v5 non misurati, family sperimentale, CI pending. Nessun nuovo catalog record/fonte, nessuna data editoriale inventata; applicazione locale e deterministica, rete confinata al collector maintenance esplicito. Per proseguire in un round successivo servono nuova validazione dei prerequisiti e nuovi corpus indipendenti; il presente round non nasconde il fallimento.

Archivio **dist/BurOCRazia-v0.7.0-candidate-NOT-READY-round15.zip**. SHA256, commit finale e verifica in **dist/package-verification-round15.json** e **.zip.sha256**, esterni al contenuto per evitare autoreferenze. Versione pubblica0.6.1 conservata. Nessuna RC.
