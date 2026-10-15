# Round 14 — NOT READY

Software pubblico **0.6.1**, schema **610**, candidata 0.7.0. Branch `codex/coverage-benchmark-v0.7.0`. Ingresso `19883ba6a1e0e7360716aa0d9bba5ecb52a569eb`, working tree pulito. Prove pre-freeze committate in `5d659d1`; freeze dedicato **`37a9d1f3125b9e0480d2592f479554fe5ea40a0a`**, creato prima di costruire unknown v2. Manifest registrato subito dopo il commit per evitare autoreferenze. Commit finale e SHA ZIP nel verificatore esterno `dist/package-verification-round14.json`. Nessun push, tag, pubblicazione o RC; README stable e versione pubblica invariati. CI **external_pending**.

## Pre-freeze e invarianti

Tutti i prerequisiti richiesti PASS prima del freeze. Coverage ricalcolata **1002/1158 = 86.528497%**, totale operativo **1002/1212 = 82.673267%**. Native support **975/1158 = 84.196891%**, 27/40 legacy qualificate; 33 associazioni shared storiche di solo supporto risorsa. Definizione SHA `7d13aa4fcc7e6b3bb86a2d43c3e8ec203d6628f86cf9e43291176affb2b6c037` invariata. Canonici **980/980 nativi, 27/27 legacy**, zero errori. Shared ambiguities separati; Unioncamere 617/618/619 ancora shared/ambiguous. Safety **241 NO**, zero false accettazioni; R061, cinque casi ufficiali critici, due casi Round 8 e hard negatives confermati.

Baseline pytest **772 passed, 0 failed, 3 skipped**, 627.20 s. Cinque misure warm pre-freeze: mediana p95 **247.1435 ms**, gate obbligatorio <=250 PASS; **3/5** sotto 250, due run sopra 300, stabilità preferita non raggiunta e policy prudente segnala fragilità. Non si cambia la soglia né si selezionano rerun favorevoli. Il manifest sigilla runtime, catalogo semantic/file hash, dataset fingerprint, definizione, profili, reference truth, registry e hash dei risultati. Nessun byte del motore, scoring, indice, ranking, soglia, peso, veto, family, catalogo o fingerprint modificato. La differenza CRLF/LF preesistente del solo catalog_manifest è registrata separatamente; nessuna variazione di contenuto.

Unknown v1 conserva **105/105** e lo stato **historical_pre_unioncamere_fix**. Il bundle misurato era `d10650139b16d9809f3a08d7065572e4536e4a1094a710039de0ae1888ea423c`, quello corretto `eaac87ac81e03ba838b52d66992db20967e8c50bbcfd88b02d894c42ab68f4bd`. Delta byte ricostruito dai tre record 617/618/619: soltanto status/shared_kind/ocr_metadata. V1 non è stato rieseguito, trasferito o usato per tuning.

## Registro di contaminazione e selezione fresca

Registry v1 SHA `65d6ed850a5067c2ce41ebe9eab9f4a01ca25f8805af1afec6ed14ca5771daa0`, creato prima del freeze: **617 known contaminate**, **416 potenzialmente eleggibili**, 211 unknown con predizione osservata, 105 in release v1, 2341 SHA osservati complessivi e 16 family. Evidenze per identità/caso e hash di tutti gli input storici. La sola verifica canonica/SHA catalog-wide è distinta dal tuning; calibration, development, precedenti robustness/filled/scan/holdout e qualificazione legacy escludono conservativamente. Le 416 identità non sono una preflight v5: leakage ulteriore, capacità di trasformazione e filler non sono stati misurati.

Dopo freeze: 147 allegati in cache mai osservati, prima truth 44. Raccolta maintenance benchmark-only con **400 richieste HTTPS**, robots, allowlist, ricevute, limiti e nessun bypass di blocchi. Nessuna fonte o identità aggiunta al prodotto. Pool finale **348 candidati**: 127 confirmed_unknown, 122 unsupported_truth, 85 ambiguous, 8 possible_family_match, 6 possible_document_match. Criteri di truth invariati: URL/SHA/receipt, entity letterale nell'opening2000, titolo/codice/anno/versione, compatibilità family e overlap tecnico fingerprint; nessuna decisione/confidence di recognition usata per selezionare.

Quota preferita 20/source, seed 2026101314, gruppi near-resource indivisibili: primo subset 97 insufficiente, preservato. Prima di qualsiasi predizione si è applicato il limite obbligatorio consentito di 25/source, senza cambiare truth o seed: **114 casi**, **12 fonti**, **14 enti**, **12 tipi**, massima concentrazione **21.929825%** (preferito <=20 non raggiunto), 10 coded/104 non-coded, 40 versioned/74 unversioned. SHA v2 `a11e4507ec47cc762ee08e19c39c10fde9b2caa393ab1ddc8c9aeec5c559a980`. Intersezione SHA con v1/development/predizioni osservate: **zero**. Fresco significa nuova predizione: alcune ricevute ufficiali in cache precedono il freeze, altre sono state acquisite dopo; nessuna falsa data o indipendenza dal catalogo dei metadati rivendicata.

## Unknown v2 single-shot e STOP

Eseguito **una sola volta**, checkout HEAD uguale al freeze, runtime/dataset sigillati identici. Writer transazionale: expected=actual=unique=114, checkpoint SQLite ignorato, export atomico, schema validato e SHA `5c7a9d9d272ad540efbd70e5cb34aeab476b393313f00f3874205ef4ecc0471d`. **107 correct NO_MATCH /114 = 93.859649%**, **3 wrong DOCUMENT_MATCH**, **0 wrong FAMILY_MATCH**, false acceptance **2.631579%**, **4 extraction errors**, entity errors **0**, explicit version/year contradiction errors **0**. Versione emessa nei tre exact: null; non si inventa una versione nel catalogo. Wilson 95% rejection **87.865706–96.994072%**, descrittivo del set e delle label congelate. Per fonte/ente/tipo nei raw. Escludendo soltanto gli errori di estrazione, 107/110 = **97.272727%**, comunque sotto 99; il gate usa il denominatore integrale 114.

| Caso | Fonte | Esito | Nota |
| --- | --- | --- | --- |
| U14-5f0c017c3d56e6c5 | inail | 1147 | Annualità INAIL / riferimento ambiguo |
| U14-c1fc4765c01dcd62 | inail | 1147 | Annualità INAIL / riferimento ambiguo |
| U14-d6e51fa8e7f88431 | anac | 615 | Regolamento ANAC emesso come modulo A.7 |

I due INAIL sono annualità 2024/2025 dello stesso sottotipo società partecipata pubblica; il canonico 1147 apre con Anno2023 ma il campo versione catalogo è null. La pipeline li ha emessi tramite pagina canonica2, digital0.9293/char0.8600, non tramite SHA. **Limite dell'audit truth:** questa relazione con l'identità già presente richiedeva la classificazione prudente possible_document_match/ambiguous prima della selezione. Dopo i risultati non si correggono label, non si tolgono casi e non si ricalcola un PASS. Sono dubbi di qualificazione del riferimento, oltre al gate osservato fallito. ANAC è una bozza di regolamento su accesso civico, emessa come A.7 modulo richiesta accesso documenti amministrativi l.241/1990 tramite fallback metadati, senza fingerprint sufficiente. I quattro errori sono PDF ufficiali oltre il limite runtime di 100 pagine: rifiuti leggibili per limite, **non** correct NO_MATCH; nessun limite rilassato.

STOP applicato: **NOT READY**, nessun tuning, replay o modifica delle label/fingerprint. Le114 predizioni sono ormai osservate e non potranno diventare un nuovo set indipendente dopo tuning. `failure_audit.json` conserva prove e piano Round15: chiarire annualità/binding con provenance ufficiale, studiare pagine comuni e fallback metadati su development, preflight dei limiti file, nuovi corpus indipendenti. Nessuna correzione del motore effettuata in Round14.

## Evaluation v5, retrieval, scan, filled e family

**Non avviata** perché unknown v2 FAIL. Nessuna selezione known v5, pool audit v5, preflight, generazione, leakage check o prediction. Identità/fonti/rappresentazioni, exact/family/reject/wrong, precision/recall/F1/CI, errori ente/versione, retrieval @1/@5/@10/@25: **non misurati**. Scan N/P/R e transform breakdown non misurati; filled generation/valid N/recognition/end-to-end non misurati; mix unknown v2 end-to-end v5 non costruito. Nessun dato assente trattato come zero/PASS. Family **experimental / insufficiently validated**, non usata per gonfiare useful recall; i test family storici restano verdi e un FAMILY_MATCH errato sarebbe falsa accettazione.

## Performance, canonici e test finali

| Run warm | p50 ms | p95 ms |
| --- | --- | --- |
| 1 | 52.7451 | 243.5416 |
| 2 | 40.9636 | 186.8782 |
| 3 | 60.2337 | 247.1435 |
| 4 | 66.6911 | 300.0547 |
| 5 | 61.8393 | 303.6369 |

Mediana p95 **247.1435 ms**, massimo **303.6369 ms**. 67 input, 402 richieste/run, 5 run/2010 tempi; OCR escluso dal gate warm, estrazione/OCR end-to-end separati nei raw. Questi sono i run pre-freeze che hanno autorizzato il freeze dello stesso identico motore, non una nuova misura dopo lo STOP. Dopo il fallimento non si rieseguono i release benchmark; canonici e performance post-evaluation v5 non eseguiti perché v5 non è iniziata. Verificata invece l'integrità hash/binding dei risultati canonici già eseguiti e dei byte sigillati.

Pytest finale **777 passed, 0 failed, 3 skipped**, 639.41 s, Python 3.12.10, Windows-11-10.0.26300-SP0; SHA log `ba3b4d8ae7fae07366f5d7386b44edfd7693f6e7712c3cdaa9940347b249808d`. Skip: symlink senza privilegio Windows e due FIFO. Compile, SQLite integrity, FK, copia/migrazione schema610 con conteggi invariati, tre validator fingerprint, schema/count/SHA del benchmark PASS. Release-fast eseguito offline: **exit1**, contraddizioni storiche EX02/EX03 preservate; v1 non riscritto e nessuna falsa dichiarazione di CLI/CI tutta verde. Compat v2 CLI exit0. Tutti i dettagli in `final_checks.json`. Test sintetici, Tesseract locale, integrità, qualificazione truth e CI restano ambiti distinti.

## Gate table

| Gate | Target | Risultato | Esito |
| --- | --- | --- | --- |
| fingerprint_coverage | >=85% | 86.52849740932642 | PASS |
| all_operational | >=70% | 82.67326732673267 | PASS |
| pre_freeze_canonical_native | 100% | 980/980 | PASS |
| pre_freeze_canonical_legacy | 100% | 27/27 | PASS |
| historical_safety | 241 NO, 0 false accepts | 0 | PASS |
| performance_median_p95 | <=250ms | 247.1435 | PASS |
| performance_four_of_five | preferred >=4/5 | 3 | FAIL |
| unknown_v2_count | >=100 | 114 | PASS |
| unknown_v2_sources | >=8 | 12 | PASS |
| unknown_v2_max_concentration | <=25% | 21.929824561403507 | PASS |
| unknown_v2_rejection | >=99% | 93.85964912280701 | FAIL |
| unknown_v2_entity_errors | 0 | 0 | PASS |
| unknown_v2_version_errors | 0 | 0 | PASS |
| unknown_v2_reference_qualification | confirmed unknown without unresolved catalog identity overlap | 2 | FAIL |
| v5_preflight | >=30 IDs,6sources,400known,200scan,50filled | non misurato | NON MISURATO |
| v5_leakage | 0 prohibited | non misurato | NON MISURATO |
| v5_precision | >=99.5% | non misurato | NON MISURATO |
| v5_exact_recall | >=90% | non misurato | NON MISURATO |
| v5_wrong_accepted | <=0.5% | non misurato | NON MISURATO |
| v5_entity_errors | 0 | non misurato | NON MISURATO |
| v5_version_errors | 0 | non misurato | NON MISURATO |
| v5_scan_precision | >=99.5% | non misurato | NON MISURATO |
| v5_scan_recall | >=85% | non misurato | NON MISURATO |
| v5_filled_generation | >=90% | non misurato | NON MISURATO |
| v5_filled_precision | >=99.5% | non misurato | NON MISURATO |
| v5_filled_recall | >=90% | non misurato | NON MISURATO |
| v5_retrieval_at25 | 100% | non misurato | NON MISURATO |
| v5_unknown_mix | >=30fresh, rejection>=99% | non misurato | NON MISURATO |
| pytest | 0 failures | {'passed': 777, 'failed': 0, 'skipped': 3} | PASS |
| compile_integrity_FK_migration_schema | 0 failures | True | PASS |
| release_fast_cli | exit0 | 1 | FAIL |
| CI | external pending | external_pending | FAIL |

## Limiti e archivio

Limiti reali: unknown v2 fallito, due riferimenti INAIL da adjudicare, quattro PDF oltre 100 pagine, performance fragile (3/5 sotto 250 ms), release-fast storico exit 1, v5 non misurata, family sperimentale, nessuna nuova dimostrazione RSS, CI esterna pending. Catalogo completo e provenienza conservati; corpus, reference truth, raw e archivi precedenti intatti. Nessun file personale, database di lavoro, convertito o credenziale in Git.

Archivio: `dist/BurOCRazia-v0.7.0-candidate-NOT-READY-round14.zip`, prodotto da HEAD finale. SHA256 e commit finale in `.zip.sha256` e `dist/package-verification-round14.json`, esterni allo ZIP per evitare autoreferenze. Stato locale **NOT READY**, nessuna RC o release pubblicata.
