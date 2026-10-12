# Round 7 — NOT READY

## Stato e provenienza

Software pubblico 0.6.1, candidata 0.7.0; schema 610. Nessun push, tag o release.
Ingresso d3dd53bbc2e97047d7eadbe379c31bb920929c7b; codice sorgente sviluppo 649e61cccc4de4380e0fbade3d0894d977da7b2f; freeze effettivo d7af5a4fb38e117ebba5b415462dde877ed98012.
Runtime SHA `d747fe708bc204df65b84f02b40beeb544adaae56c49d4264696a4c26574aa56`; codice/runner SHA `f0a9547f017f63dd8d6109956fcd437a8c75bbba4f76f979432f251897807585`; bundle SHA `d0bd34e9d55fa7dc72708346a021c7d762ca5ba42d6cc90e280a756337ce7d26`.
La calibrazione originale è immutata. `decision_calibration_reference_fix.json` attesta l'unica correzione successiva, limitata alla diagnostica full scan: ricostruisce l'hash originale dai byte Git e verifica tutti gli altri byte runtime/profilo. Nessun esito, soglia o vincolo produttivo è cambiato. Il freeze comprende anche l'hash di questa prova.
Il commit nell'artefatto di calibrazione identifica HEAD durante lo sviluppo; profilo e runtime sono identificati dai rispettivi byte/hash, inclusi poi nel freeze.
Il commit di distribuzione include anche i report; ZIP/hash in `dist/package-verification.json`, prodotti dopo il commit per evitare riferimenti circolari.

## Baseline e decisione

Baseline R6: canonical 987/987, robustness 150/192, scan 128/168, retrieval 100%, unknown 137/137; full suite 655+3skip.
EX02/EX03 erano i due rifiuti che lasciavano 33/35; ora 35/35.
Tutti i 50 raw JSON R6 sono conservati e verificati per hash, oltre ai corpus v1/v2 immutati.
Audit dei 42 NO rank1 in `docs/ROUND7_DECISION_AUDIT.md` e CSV R6 dedicato: 28 ruoli ente, 13 OCR score, 1 canali.
R6 ora development: replay 155/192; nessuna pretesa di indipendenza dopo il tuning.
Calibrazione 320 rappresentazioni note e 348 controlli negativi storici: 130 hard negatives e 137 unknown nel motore completo, 81 controlli nel solo fallback family secondo il contratto originale del corpus. Obiettivo zero false accept nell'ambito corretto e massimo richiamo exact.
Il primo tentativo development era fallito perché trattava gli 81 controlli family come negativi del motore completo e conteggiava FAMILY_MATCH come identità sbagliata. FR10-N4/FR12-N4 identificano documenti 143/167 nel motore completo, ma restano NO nel fallback family. L'audit iniziale resta conservato; nessuna soglia del runtime è stata modificata per eliminare questi due esiti. La calibrazione finale verifica ogni configurazione con il runtime effettivo, riusando solo l'estrazione storica degli unknown development; la misura finale unknown riestrae i file.
Profilo congelato `ebf7e4444f040afe0e560f5b04c6767f7d40cd73f2dc9a866321e8d62208e0a8`: `{"anchor_strong": 0.45, "anchors": 0.12, "char_floor": 0.1, "char_strong": 0.3, "exceptional": 0.97, "margin": 0.04, "ocr_visual": 0.8, "overlap": 24, "text_char": 0.85, "text_visual": 0.55, "visual": 0.94}`.
Tier A/B/C/D e diagnostica sono request-local; nessun testo caricato, sketch o risultato personale entra nelle cache pubbliche.

## Recupero e copertura

Zero nuove identità/fonti. 82 richieste di rete nel solo strumento maintenance opt-in, con robots, allowlist e limiti; 403/429 non aggirati.
14 identità hanno ulteriori byte ufficiali; solo [175, 589] aggiungono un'identità attiva.
Quarantena delle identità prima attive [166, 584, 586, 587, 590, 1150, 1184, 1187, 1196]: risorse con SHA condiviso fra identità; nessuna scelta arbitraria.
941/1212 attive, totale 77.64%; 941/1158 con file, 81.26%; metadata-only 54.
Il denominatore 1158 resta invariato. Il gate 85% resta FAIL. Un eventuale futuro gate sulle sole risorse recuperabili richiede una decisione esplicita e non è applicato.
DOC/DOCX senza renderer, XLSX/ZIP/PPTX reali, blocchi ufficiali e conflitti canonici sono limiti distinti; nessuna conversione non sicura.
Il riconoscimento MIME ZIP ora distingue Word/Excel/PowerPoint; 36 etichette MIME precedenti erano errate. Non si eseguono macro/formule.
Resolver con fixture per le 12 fonti, meta-refresh ufficiali e attachment senza estensione; final URL validato. Tutti i 264 missing iniziali più 9 nuove quarantene sono nel CSV di recupero.

| Fonte | Operativi | Con file | Firme attive |
|---|---:|---:|---:|
| ade | 122 | 90 | 0 |
| anac | 7 | 7 | 7 |
| funzione_pubblica | 9 | 9 | 6 |
| garante_privacy | 17 | 10 | 4 |
| giustizia | 142 | 142 | 126 |
| inail | 347 | 347 | 304 |
| inl | 46 | 45 | 43 |
| inps | 359 | 359 | 351 |
| lavoro | 102 | 102 | 74 |
| mef | 15 | 1 | 1 |
| mimit | 42 | 42 | 24 |
| unioncamere | 4 | 4 | 1 |

## Valutazione nuova, una sola esecuzione

Piano generato dopo freeze, seed 2026101207; 42 identità nuove rispetto alla calibrazione, 372 tentativi pianificati, 331 rappresentazioni effettivamente generate, 280 scan-like. Compilazione: 9/50 PDF realmente generati su 10 template; 41 fallimenti mantenuti nel denominatore. Il minimo 50 compilati non è raggiunto: FAIL esplicito, senza correggere il generatore dopo l'evaluation.
Nessun overlap ID/SHA/URL/titolo-codice-versione né quasi duplicati secondo la regola pubblicata; `evaluation_v3_leakage.json` zero leakage proibito.
Firme canoniche note presenti per le identità evaluation: si misura generalizzazione alle rappresentazioni, non a identità sconosciute.
Nessuna modifica del runtime, soglie, template selection o etichette dopo risultati. Piano/started/freeze e raw conservati.
La prima preparazione del piano era terminata prima di plan/start/casi per backend AES mancante; `evaluation_environment_preflight.json` conserva la prova. Dipendenze locali già disponibili cryptography 50.0.2 / cffi 2.1.1 aggiunte solo al benchmark ignorato; codice/seed invariati. Requisiti riproducibili in `benchmarks/requirements-round7.txt`.
Scansioni generate dalla prima pagina, DPI 150/200, JPEG 90/75/60, contrasto, blur, crop, resize e rotazioni; non scansioni reali di utenti.
Compilazione interattiva con dati fittizi: /AcroForm/Fields, /V, widget e /AP/N verificati, checkbox variate; ambiguità/fallimenti inclusi nel denominatore.
L'associazione semantica dei campi con etichette vicine è euristica (es. luogo di nascita può ricevere data): prova di perturbazione del riconoscimento, senza validità amministrativa.
La QA visiva di tre PDF generati, ricostruiti con SHA identico senza nuovo riconoscimento, mostra anche campi assegnati in modo errato e testo tagliato nei segmenti data. /V, widget e /AP/N coerenti non equivalgono a compilazione semanticamente o graficamente valida. Nessun PDF viene consegnato o incluso nello ZIP; limite da correggere prima di un nuovo freeze Round 8.

| Misura | Casi | Exact | Family | NO | Wrong | Precisione exact | Recall exact |
|---|---:|---:|---:|---:|---:|---|---|
| Canonical | 979 | 979 | 0 | 0 | 0 | 100.00% (979/979) | 100.00% (979/979) |
| Robustness v3 | 372 | 183 | 0 | 189 | 0 | 100.00% (183/183) | 49.19% (183/372) |
| Scan v3 | 280 | 134 | 0 | 146 | 0 | 100.00% (134/134) | 47.86% (134/280) |
| Filled v3 | 50 | 7 | 0 | 43 | 0 | 100.00% (7/7) | 14.00% (7/50) |
| Unknown storico | 137 | 0 | 0 | 137 | 0 | n.d. | n.d. |

| Trasformazione | Casi | Corretti | Recall exact |
|---|---:|---:|---|
| blur_mild | 20 | 10 | 50.00% (10/20) |
| contrast_minus20 | 20 | 9 | 45.00% (9/20) |
| crop_2pct | 20 | 8 | 40.00% (8/20) |
| crop_5pct | 20 | 4 | 20.00% (4/20) |
| digital_exact | 42 | 42 | 100.00% (42/42) |
| filled_0 | 10 | 1 | 10.00% (1/10) |
| filled_1 | 10 | 2 | 20.00% (2/10) |
| filled_2 | 10 | 1 | 10.00% (1/10) |
| filled_3 | 10 | 2 | 20.00% (2/10) |
| filled_4 | 10 | 1 | 10.00% (1/10) |
| grayscale | 20 | 10 | 50.00% (10/20) |
| jpeg_60 | 20 | 10 | 50.00% (10/20) |
| jpeg_75 | 20 | 11 | 55.00% (11/20) |
| jpeg_90 | 20 | 9 | 45.00% (9/20) |
| raster_150 | 20 | 10 | 50.00% (10/20) |
| raster_200 | 20 | 12 | 60.00% (12/20) |
| resize_075 | 20 | 10 | 50.00% (10/20) |
| rotation_180 | 20 | 10 | 50.00% (10/20) |
| rotation_270 | 20 | 11 | 55.00% (11/20) |
| rotation_90 | 20 | 10 | 50.00% (10/20) |

Retrieval @1/5/10/25: `{"1": {"denominator": 372, "numerator": 331}, "10": {"denominator": 372, "numerator": 331}, "25": {"denominator": 372, "numerator": 331}, "5": {"denominator": 372, "numerator": 331}}`.
Sulle sole 331 rappresentazioni disponibili retrieval 100% (331/331 anche@1); gli stessi risultati raw restano immutati. Il gate conservativo pianificato resta 331/372 per i 41 input non generati: non viene sostituito con il denominatore favorevole. I 280 scan-like hanno retrieval@1/25 100%, ma soltanto 134 exact; il problema decisionale resta distinto dal fallimento del generatore filled.
Cause NO aggregate dai raw: `{"Candidati specifici troppo vicini: identità ambigua.": 5, "Conflitti di ente o annualità impediscono l'identificazione specifica.": 7, "Evidenze insufficienti per identificare un documento specifico.": 96, "generation_failed": 41, "missing_model_revision": 40}`. Nessun tuning dopo questa lettura.
Wrong/NO, enti/versioni, tempi estrazione/visual/matching/end-to-end sono nelle osservazioni; extraction/generation failed restano nel denominatore.

## Family, unknown e regressioni

16 famiglie, 0 valutabili con almeno 2 identità sviluppo e 3 holdout; `not_sufficiently_validated`, non bloccante per RC documenti noti. Dettaglio per famiglia nel CSV e JSON.
Unknown: 137 file ufficiali storici distinti, usati anche nella calibrazione di sicurezza; 0 nuovi unknown adjudicati indipendentemente. Tasso 100.00% (137/137), nessuna pretesa di test unknown nuovo.
Storici v1/v2 preservati: 35 originali 35/35; locked v1 59/69; locked v2 69/69; 130 negativi 130/130; family sintetico 161/161.
R061 NO_MATCH; cinque casi critici 5/5 safe.
Fixture 37 immutata 35/37: expected opposti per due testi identici ai 35 originali. Il gate storico stretto resta FAIL, senza cambiare etichette per farlo passare.
OCR locale reale: 7/7 storico + 14/14 sintetico. Non sono validazione editoriale o collaudo multipiattaforma.

## Performance e memoria

Baseline p50/p95 112.9562/799.1129 ms; configurazione finale 76.3465/444.6542 ms, p99 525.8341 ms, 306 osservazioni su 35 sintetici e gli stessi 16 file ufficiali.
Processo nuovo, warmup 51; esclusi estrazione, OCR e visual, separati nei raw v3. Nessuna cache di input.
Profilo baseline e sviluppo per fase/funzione conservato. Denominatori IDF precomputati su solo catalogo; fuzzy title saltato soltanto quando il coverage cap garantisce contributo zero; conflitti per ente riusati nella singola richiesta. Full scan resta disponibile.
Equivalenza testata su score/ranking e risultati completi document/entity/version/family/NO; nessuna potatura rischiosa dei candidati metadata.
Bundle 27493120 byte; indice ricorsivo 39832045 byte; load catalogo 11.883 ms, build indice 1517.722 ms.
RSS dopo warm 267243520 byte; crescita successiva 12288 byte, separata dalla misura indice.

I tempi end-to-end scan-like, comprensivi di OCR reale, sono p50 1820.08 ms e p95 6831.83 ms su 280 casi. Provengono dai worker paralleli della singola evaluation e sono diagnostici; il gate di riconoscimento usa la misura isolata precedente. Dettaglio di estrazione, visual e matching in `phase_timings.json`.

## Test, piattaforme e gate

Full suite: 690 passed, 0 failed, 3 skip Windows, 337.74 s. Log SHA `8e1bb8eaa0b6f56a64a30ecb9aa1041588c2caf97af34435907bf9cb0f8baf11`.
Controllo mirato dopo aggiornamento dei riepiloghi: 113 test passati, 0 falliti. Sono ripetizioni della suite, non test aggiuntivi da sommare ai 690.
Il primo tentativo completo aveva 687 passed, 3 failed, 3 skip (151.36 s): soltanto stringhe diagnostiche diverse fra indice e full scan. Log/hash conservati e correzione prima della nuova evaluation; nessun expected o corpus cambiato.
Bootstrap su database temporaneo separato, integrity/FK, snapshot/migrazioni storiche e lock verificati; seed pubblico invariato, database personale non modificato.
CI Python 3.12 Linux/Windows/macOS configurata; solo Windows eseguito localmente. Stato esterno pending_external_gate fino al push dell'utente.

| Gate | Target | Risultato | Esito | Bloccante |
|---|---|---|---|---|
| coverage_file_backed | >=85% | 0.812607944732297 | FAIL | sì |
| coverage_all | >=70% | 0.7764026402640264 | PASS | sì |
| evaluation_minimum_generated_representations | >=300 | 331 | PASS | sì |
| scan_minimum_cases | >=200 | 280 | PASS | sì |
| filled_minimum_actual_generated | >=50 | 9 | FAIL | sì |
| canonical_document_precision | 100% | 1.0 | PASS | sì |
| canonical_document_recall | 100% | 1.0 | PASS | sì |
| canonical_wrong | 0 | 0 | PASS | sì |
| robustness_precision | >=99.5% | 1.0 | PASS | sì |
| robustness_exact_recall | >=90% | 0.49193548387096775 | FAIL | sì |
| scan_precision | >=99.5% | 1.0 | PASS | sì |
| scan_exact_recall | >=85% | 0.4785714285714286 | FAIL | sì |
| filled_precision | >=99.5% | 1.0 | PASS | sì |
| filled_exact_recall | >=90% | 0.14 | FAIL | sì |
| scan_useful_recall | >=95% (conservative section17 gate retained) | 0.4785714285714286 | FAIL | sì |
| retrieval_at_1 | >=99% | 0.8897849462365591 | FAIL | sì |
| retrieval_at_25 | >=100% | 0.8897849462365591 | FAIL | sì |
| unknown_historical_rejection | >=99% | 1.0 | PASS | sì |
| family_capability_validation | >=5 evaluable families | 0 | FAIL | no |
| R061 | NO_MATCH | NO_MATCH | PASS | sì |
| historical_five | 5 safe | 5 | PASS | sì |
| historical_negatives | 130/130 | 130 | PASS | sì |
| historical_family_negatives | 0 false accepts | 0 | PASS | sì |
| historical_development | 35/35 unchanged labels | 35 | PASS | sì |
| historical_locked_v2 | 69/69 | 69 | PASS | sì |
| historical_all_frozen_expectations | All historical expectations green, including contradictory v2 fixture | {'locked_v1': 59, 'compat_v2': 35} | FAIL | sì |
| real_ocr | 7/7 +14/14 | {'legacy': 7, 'synthetic': 14} | PASS | sì |
| warm_p50 | <=150ms | 76.3465 | PASS | sì |
| warm_p95 | <=250ms | 444.6542 | FAIL | sì |
| index_memory | <=100MB | 39832045 | PASS | sì |
| tests | 0 failures | 690 | PASS | sì |
| catalog_unchanged | Original seed/schema610 | 790b690123c82e1cb7bdfa67a10216284022987d50b0abbcc4a1a245785e3e99 | PASS | sì |

## Distribuzione e limiti residui

Verdetto locale **NOT READY**. Software/versione pubblica invariati; nessuna pubblicazione.
Archivio `dist/BurOCRazia-v0.7.0-candidate-NOT-READY-round7.zip`; verifica hash/byte/lock/hygiene in dist.
Nessun file ufficiale, PDF compilato, testo OCR, cache, binario Tesseract, credenziale o database personale redistribuito.
Un Round 8 deve usare nuove identità evaluation dopo un nuovo freeze, senza riutilizzare v3 per rivendicare indipendenza; risolvere copertura, gate falliti e contraddizioni delle etichette con una nuova versione motivata, senza alterare lo storico.
