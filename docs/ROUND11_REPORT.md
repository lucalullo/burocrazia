# Round 11 — NOT READY

Software pubblico **0.6.1**, target **0.7.0**, schema **610**. Branch `codex/coverage-benchmark-v0.7.0`. All'ingresso HEAD era `d19547f458e46d38c11a84ffd9e2f735510ac5bc` e il working tree era pulito. HEAD durante la generazione del report: `d19547f458e46d38c11a84ffd9e2f735510ac5bc`. Commit finale e SHA dell'archivio sono registrati dopo il commit in `dist/package-verification-round11.json` e nella consegna, per evitare autoreferenze. Nessun push, tag, release o freeze. CI `external_pending`.

## Decisione

Il benchmark unknown supera i minimi per conteggio, fonti, bilanciamento e tipi. La copertura file-backed resta **84.196891%**, inferiore all'85%: `ready_to_freeze=false`. Per questo non sono stati eseguiti freeze, evaluation v5 o preparazione RC.

Motore, soglie, pesi, tier, veti ente/versione, family e profili restano invariati. È stata aggiunta una sola fingerprint ufficiale, per l'ID 178. Tutti i 1027 record v3 originari sono conservati; la serializzazione del loro prefisso ricostruisce esattamente il bundle Round 10. Il nuovo dataset ha un proprio SHA, distinto da quello dei byte semantici del motore.

## Coverage: target e risultato

Baseline ricalcolata: **1158 file-backed**, **941 identità con supporto univoco**, minimo **985** per l'85%, deficit iniziale **44**. Il target prudenziale era di 49–54 recuperi, se disponibili. Il denominatore R6 include ancora l'ID 166, anche senza `download_url`; non è stato ridotto per blocchi, formati o errori. Baseline: 758 test passati e 3 skipped, canonical 979/979, 241 NO storici correttamente rifiutati, p95 Round 10 di 146.0866 ms.

Risultato: **975/1158 = 84.196891%**; sul totale operativo, **975/1212 = 80.445545%**. Il recupero rispetto alla metrica iniziale è di 34: una nuova firma e 33 identità già associate a risorse condivise, dichiarate eleggibili dopo audit. Il totale comprende **942 identità con supporto univoco** e **33 con solo supporto condiviso**. La copertura univoca da sola è 81.347150%. Restano 183 record senza supporto eleggibile e **10 identità mancanti** rispetto al minimo di 985.

Round 11 autorizza esplicitamente il supporto da risorsa condivisa. Questa metrica è separata dalle serie unambiguous R6–10, che restano immutate. Il risultato non rappresenta 34 nuove fingerprint o 34 nuove identità esatte. Nessuna risorsa condivisa entra nella canonical accuracy univoca.

| Fonte | Operative | File-backed | Supportate | Univoche | Shared-only | Residue |
| --- | --- | --- | --- | --- | --- | --- |
| ade | 122 | 90 | 0 | 0 | 0 | 90 |
| anac | 7 | 7 | 7 | 7 | 0 | 0 |
| funzione_pubblica | 9 | 9 | 9 | 6 | 3 | 0 |
| garante_privacy | 17 | 10 | 6 | 5 | 1 | 4 |
| giustizia | 142 | 142 | 130 | 126 | 4 | 12 |
| inail | 347 | 347 | 315 | 304 | 11 | 32 |
| inl | 46 | 45 | 44 | 43 | 1 | 1 |
| inps | 359 | 359 | 359 | 351 | 8 | 0 |
| lavoro | 102 | 102 | 76 | 74 | 2 | 26 |
| mef | 15 | 1 | 1 | 1 | 0 | 0 |
| mimit | 42 | 42 | 27 | 24 | 3 | 15 |
| unioncamere | 4 | 4 | 1 | 1 | 0 | 3 |

Pass finale sui 217 residui delle fonti catalogate: 21 richieste maintenance, con robots, allowlist, URL finale e SHA verificati; nessun nuovo tentativo sui blocchi 403/429/404/robots già noti, né aumento dei limiti. MEF e ANAC non hanno residui file-backed da riprovare. Il resolver segue soltanto pagine Garante con etichetta correlata e relativi allegati ufficiali; i test offline escludono navigazione generica e domini estranei.

I record 174 e 177 hanno byte già associati ad altre identità: le nuove associazioni richiederebbero una nuova valutazione del gruppo e non sono contate senza integrazione shared sicura. Il record 178 ha titolo completo e guardie d'identità esistenti compatibili ed è aggiunto come DOCX originale ufficiale.

Audit manuale delle 48 associazioni shared storiche: URL, SHA, binding e scopo effettivo. Sono escluse dalla nuova copertura le associazioni 176 (TFTP rispetto alla scheda Segnalazione), 583 (Allegato 2 rispetto all'Allegato 3), 921 (lista nazionale rispetto alla domanda regionale), 983 (Libro unico rispetto a Stati paga), 1151 (allegato rispetto alla domanda principale). Il binding 1186 ai parametri statistici è escluso; altri modelli 20SM pertinenti restano resource-only. L'ID 166 è soltanto una scheda informativa associata alla procedura Segnalazione, non un modulo univoco. Nessuna correzione retroattiva della provenienza storica o modifica automatica del catalogo.

Il runtime mantiene `status=shared`, gruppi per SHA e requisiti di codice univoco, ente/versione e margine. Il test diretto della fingerprint policy sulle risorse condivise non osserva alcun tier `A_exact_sha`. Gli input senza disambiguazione restano ambigui; non si attribuisce capacità di identificazione univoca a questi 33 ID.

Legacy: 63 risorse già esaminate nel Round 10, con tentativi deduplicati. Sono stati riprovati solo i due candidati utili 422/1101 con il profilo corretto LibreOffice: conversioni e fingerprint di contenuto restano maintenance-only, con SHA originale e derivato separati e output temporanei eliminati. Nessun file convertito è in Git. Il contratto MIME del runtime non ammette gli originali RTF/XLSX; nessuna firma derivata è presentata come PDF ufficiale, né si rivendica supporto per upload legacy.

## Unknown: master e release

Matematica iniziale: 107 casi, 7 fonti, 45 MIMIT e 62 da altre fonti. Con N=100 il cap MIMIT è 25: servivano almeno 13 nuovi non dominanti e una nuova fonte. Master finale: **125 casi, 10 fonti e 10 enti/autorità ospitanti**, concentrazione massima **36.00%**. Tutti i 107 precedenti sono conservati. Le 18 nuove conferme provengono da Interno (14), Giustizia (2) e Piemonte (2). Nessun documento o fonte è stato aggiunto al catalogo.

Conteggi master per fonte: `{"agid": 15, "anac": 9, "giustizia": 2, "inail": 16, "interno": 14, "lavoro": 6, "mef": 13, "mimit": 45, "mit": 3, "regione_piemonte": 2}`. Tipi: `{"atto_indirizzo": 1, "circolare": 39, "comunicato": 1, "decreto": 28, "delibera": 2, "direttiva": 2, "domanda": 3, "guida": 31, "istruzioni": 3, "manuale": 7, "modulo": 3, "regolamento": 5}`. Con codice: 21; senza codice: 104; con versione: 28; senza versione: 97.

Release: **105 casi, 10 fonti, 10 enti, concentrazione massima 23.809524%, 12 categorie**. Seed `2026101311`, cap di 25 per fonte, gruppi near interi ordinati per SHA256(seed:group); nessuna selezione per score, facilità o esito. Tutti i minimi sono superati; i target preferiti di 120 casi release e concentrazione al 20% non sono raggiunti. I 20 MIMIT esclusi dal subset restano nel master come unknown_dev, senza cancellazioni.

Conteggi release per fonte: `{"agid": 15, "anac": 9, "giustizia": 2, "inail": 16, "interno": 14, "lavoro": 6, "mef": 13, "mimit": 25, "mit": 3, "regione_piemonte": 2}`. Tipi: `{"atto_indirizzo": 1, "circolare": 29, "comunicato": 1, "decreto": 22, "delibera": 2, "direttiva": 1, "domanda": 3, "guida": 31, "istruzioni": 3, "manuale": 7, "modulo": 3, "regolamento": 2}`. Con codice: 16; senza codice: 89; con versione: 27; senza versione: 78.

Acquisizione: 109 richieste maintenance entro un budget di 140; nuove fonti verificate live e contesto delle pagine già in cache. Etichette generiche come «La circolare» sono integrate con titolo della pagina dettaglio e ricevuta HTML; un modulo allegato conserva il proprio tipo, senza ereditare automaticamente «circolare». Regione Piemonte è ammessa solo nella policy maintenance, con prove primarie in SOURCES.md.

L'audit confronta SHA, titoli, codici, ente/fonte, anno/versione, URL finale, near-duplicate, fingerprint e famiglie prima delle predizioni. Le date provengono dalle ricevute. Nessun anno di legge è trasformato in versione documentale. Il corpus contiene moduli, circolari e istruzioni; non garantisce rappresentatività di ogni unknown reale.

Registro truth v2 base e addendum R10 immutati. Addendum R11 separato con 19 prove motivate (nuovi unknown e nuova risorsa canonica), hash del registro base, ricevute effettive e nessuna promozione editoriale. Le vecchie classificazioni R10 restano disponibili nel loro audit; il nuovo contesto documenta perché alcuni candidati prima ambigui sono confermati ora.

SHA e gruppi near release/dev sono disgiunti. Esposizione storica: **55 casi release già riconosciuti in round precedenti, 50 mai riconosciuti prima**; nessuno è stato riconosciuto nel Round 11. La selezione non rende indipendenti i casi già visti. In un eventuale futuro mix end-to-end si dovrebbero usare almeno 30 dei 50 casi freschi, senza tuning. La rejection release resta **non misurata**.

Sono stati rieseguiti soltanto i 20 development: false accept 0, errori di estrazione 0. È stato usato il writer transazionale R9, con count, unique IDs, SHA e journal escluso da Git; export SHA `149459c248f887e6eea31187c2d2df383e3a9b35e1f16817676728d9f197adbd`.

## Safety, canonical e performance

NO storici: **241 osservazioni, zero false accept**. R061 e i due casi Round 8 sono NO; i cinque vecchi casi ufficiali critici sono correttamente gestiti. Canonical: **980/980** (979 originari più il nuovo 178), zero wrong e zero estrazioni fallite, su 942 identità unambiguous. Le label v1 ambigue restano visibili: base 33/35 e locked v1 59/69. Nessun tuning per migliorarle.

| Corpus | Corretti | Totale |
| --- | --- | --- |
| development_regression | 33 | 35 |
| release_locked_v1 | 59 | 69 |
| release_locked_v2 | 69 | 69 |
| hard_negatives_v1 | 30 | 30 |
| hard_negatives_v2 | 100 | 100 |
| family_release_v3 | 161 | 161 |
| development_compat_v2 | 37 | 37 |
| catalog_coverage | 1169 | 1212 |

Recognition-only: 402 richieste nel medesimo protocollo isolato R9/R10. **p50 55.8256 ms; p95 248.2326 ms**, gate 250 ms PASS. PDF digitali: p95 417.9735 ms; scansioni con testo OCR già disponibile: 167.0102 ms. Tempi dell'estrazione OCR separata, in ms: `{"n": 14, "p50": 15778.1281, "p95": 17657.4934, "p99": 18310.7032}`. Sono scansioni sintetiche, non un collaudo generalizzato su acquisizioni personali. Nessuna ottimizzazione o cache globale degli input aggiunta.

Il p95 è superiore ai 146.09 ms del Round 10 e il margine sul gate è soltanto **1.7674 ms**. Non è stata isolata la causa della variazione tra esecuzioni; non si attribuisce un cambiamento semantico al motore né si sostituisce la misura finale con una ripetizione più favorevole.

Indice: 89746066 bytes. RSS dopo il warm-up: 420073472 bytes, crescita 181252096 bytes; stabilità della memoria di processo ancora non dimostrata. Il gate aggregato non implica che ogni formato sia sotto 250 ms.

## Prerequisiti, freeze ed evaluation

Il file `benchmarks/results/round11/prerequisite_gate.json` registra tutti i campi del gate. Solo `coverage_file_backed_pass` è false tra i prerequisiti; `ready_to_freeze=false`. Freeze non eseguito, commit freeze assente.

Evaluation v5 non costruita né eseguita: identità note non selezionate; rappresentazioni, scansioni, compilazioni valide, unknown mix e retrieval @1/@5/@10/@25 non misurati. Nessun risultato mancante è trattato come zero o PASS. I raw interrotti Round 8 e tutti gli storici sono conservati. Family: **experimental / insufficiently validated**, zero famiglie reali identity-held-out qualificabili nella misura R9 invariata; non usata per useful recall.

Suite finale: **762 passed, 0 failed, 3 skipped**, 506.06 secondi, Python 3.12.10 su Windows-11-10.0.26300-SP0. I tre skip riguardano il privilegio Windows per symlink e due test FIFO. SHA del log: `fd0fa5646fd548dedce492340a419a9fdbdc906557f72b7298ab512899103718`. I 4 test infrastrutturali finali sono passati anche separatamente, senza sommarli due volte. Baseline 758/3 e suite finale restano distinte. Test offline di resolver, quote, titoli e writer R9 (interruzione, resume, dedupe, schema, count, SHA) rieseguiti.

Seed immutato: 1216 record reali, 1212 operativi, 19 fonti, 16 famiglie; integrità e provenance verificate. La verifica riguarda Windows locale; non si rivendicano validazione editoriale o collaudi su altre piattaforme. CI **external_pending**: i comandi legacy v1 conservano le divergenze note dalle label positive ambigue, quindi non si dichiara CI verde.

| Gate | Target | Risultato | Esito |
| --- | --- | --- | --- |
| coverage_file_backed | >=85% | 84.196891% | FAIL |
| coverage_all | >=70% | 80.445545% | PASS |
| unknown_count | >=100 | 105 | PASS |
| unknown_sources | >=8 | 10 | PASS |
| unknown_balance | <=25% | 23.809524% | PASS |
| unknown_types | >=5 | 12 | PASS |
| historical_safety | 0 false accepts | 0 false accept / 241 NO storici | PASS |
| canonical | 100% unambiguous | 980/980; wrong 0 | PASS |
| performance | p95<=250ms | p50 55.8256 ms; p95 248.2326 ms | PASS |
| master_pool | >=120 preferred | 125 | PASS |
| tests | 0 failures | 762 passed / 0 failed / 3 skipped | PASS |
| v5_known_identities | >=30 | non misurato | NON MISURATO |
| v5_known_sources | >=6 | non misurato | NON MISURATO |
| v5_representations | >=400 | non misurato | NON MISURATO |
| v5_scan_count | >=200 | non misurato | NON MISURATO |
| v5_valid_fills | >=50 | non misurato | NON MISURATO |
| v5_unknown_mix | >=30 | non misurato | NON MISURATO |
| v5_validity | count==unique==expected; schema/atomic/SHA | non misurato | NON MISURATO |
| v5_precision | >=99.5% | non misurato | NON MISURATO |
| v5_exact_recall | >=90% | non misurato | NON MISURATO |
| v5_entity_errors | 0 | non misurato | NON MISURATO |
| v5_version_errors | 0 | non misurato | NON MISURATO |
| v5_scan_recall | >=85%,P>=99.5% | non misurato | NON MISURATO |
| v5_filled_recall | >=90%,P>=99.5% | non misurato | NON MISURATO |
| unknown_release_rejection | >=99% | non misurato | NON MISURATO |
| v5_retrieval_at25 | 100%;@1 target99% | non misurato | NON MISURATO |
| family | >=5 real families or experimental | experimental / insufficiently validated | INFO/PENDING |
| CI | external_pending | external_pending | INFO/PENDING |

## Archivio e limiti

Archivio: `dist/BurOCRazia-v0.7.0-candidate-NOT-READY-round11.zip`, prodotto da HEAD committato. Commit finale e SHA256 sono in `dist/package-verification-round11.json` e `.zip.sha256`, esterni al proprio contenuto per evitare autoreferenze. Verifica del package: seed, corpus, byte sorgenti, raw storici, record fingerprint precedenti e igiene. Archivi Round 8/9/10 conservati.

Unico prerequisito rimasto insufficiente: copertura 84.20%, deficit di 10 identità. Ulteriori limiti: nessuna v5 indipendente, 55 unknown release già visti, family sperimentale, legacy non integrati, RSS non stabilizzata, margine prestazionale ridotto e CI pending. Software pubblico invariato a **0.6.1**.
