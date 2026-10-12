# Round 8 — NOT READY

Software pubblico 0.6.1; candidata 0.7.0; schema 610. Branch `codex/coverage-benchmark-v0.7.0`. Freeze `b0e24476db23bb479dadb7f2957d34419d02c9d0`. Il commit finale è quello contenente questo rapporto; il suo SHA e quello dello ZIP sono in `dist/package-verification.json` e nella consegna. Nessun push, tag o release pubblicata. Catalogo invariato: 1.216 identità reali, 1.212 operative, 19 fonti, 16 famiglie. SHA seed `790b690123c82e1cb7bdfa67a10216284022987d50b0abbcc4a1a245785e3e99`.

**Evaluation v4 INCOMPLETA:** una sola invocazione, terminata con `OSError [Errno 22]` durante la scrittura del checkpoint. Salvate 50/356 osservazioni; 306 esiti non disponibili. Nessun riavvio o ritocco del codice congelato. Le metriche del sottoinsieme salvato descrivono soltanto quelle righe e non sono una prova rappresentativa né qualificata di release. Il Round 8 si chiude come candidata NOT READY con requisito di evaluation completa non soddisfatto.

## Verità e limiti delle etichette

9 gruppi contraddittori, 29 occorrenze: {"ambiguous": 25, "historical_fixture_error": 2, "official_truth_confirmed": 2}; zero non classificate. Registro creato prima del tuning. Le due righe confermate passano 2/2. I corpus locked e i 110 raw R6/R7 sono immutati. Le ambiguità restano fuori dai gate principali; i loro NO storici restano vincoli di sicurezza. R6/R7 sono sviluppo. Le etichette dei nuovi casi v4 sono confirmed dalla risorsa canonica ufficiale e dal binding pubblico preesistente; non costituiscono verifica editoriale.

## Implementazione e calibrazione

Stati delle 29 label nel registro: {"confirmed": 2, "historical_only": 0, "ambiguous": 25, "excluded_from_release_gate": 2}. Soltanto le label confirmed alimentano il gate riconciliato; i risultati storici restano diagnostici e i loro NO conservano il contratto di sicurezza.

Fingerprint v1/v2 conservate. V3: 1.027 binding, 1.003 SHA, 3.476 pagine; OCR locale reale su 3.426 pagine PDF, 50 pagine logiche DOCX senza OCR/layout inventati. Hash token stabili, char 3/4/5 con IDF canonico deterministico, ancore e 24 hash visuali per pagina (quattro rotazioni, crop e tile 2x2). Allineamento greedy di massimo due pagine, input fino a cinque pagine. Containment è una stima da sketch campionati, dichiarata nei parametri, non un confronto integrale. Nessuna immagine o testo ufficiale incluso nei dati redistribuiti.

Calibrazione di sviluppo su 103 identità riservate, tipi {"contrast_minus20": 40, "crop_5pct": 40, "digital_exact": 62, "first_page_only": 20, "jpeg_60": 40, "raster_150": 40, "rotation_270": 40, "rotation_90": 40, "grayscale": 20, "jpeg_75": 20, "jpeg_90": 20, "raster_200": 20, "blur_mild": 20, "crop_2pct": 20, "resize_075": 20, "rotation_180": 20, "hard_negative": 130, "valid_filled": 50, "unknown_historical": 137}. Griglia di 18 configurazioni, priorità a zero false accept e zero identità errate. Scelta char 3, aggregazione max, containment True; soglie {"digital": 0.9, "ocr": 0.8, "chars": 0.65, "visual": 0.88, "anchors": 0.25, "margin": 0.04, "overlap": 16, "top_k": 25, "field_text": 0.75, "conflict_content": 0.9, "conflict_chars": 0.8, "conflict_anchors": 0.5, "conflict_margin": 0.1}. Pesi contenuto .50, char .35, ancore .15; visual come canale indipendente condizionale. Criteri SHA univoco, testo+char+identità, OCR+char+visual+ancore, oppure field-set univoco con testo compatibile. Ente/versione espliciti, binding obsoleto e stato non operativo restano veti. Nessuna taratura dopo il freeze.

Il profilo selezionato ottiene 428/532 exact di sviluppo, zero identità errate e 267/267 rifiuti dei negativi. Una verifica finale su tutti i 799 casi prima del freeze conferma zero differenze negli esiti; griglia originale, tentativi falliti e verifica restano separati nei raw.

Memo soltanto nella singola richiesta per sketch e rendering. Cache globali soltanto per dati del catalogo pubblico. Retrieval economico per hash, confronto testuale sui candidati, visual lazy su massimo 25 identità incerte. La normalizzazione del confronto metadati è preparata una volta dal batch RapidFuzz e confrontata con il full scan indipendente nei test. I contatori misurano pagine per initial/text e identità per visual: non sono la stessa unità.

Normalizzazione e segnali di ente sono memoizzati nella richiesta per ciascuna distinta policy (fingerprint e metadati hanno regole di intestazione diverse). Anche i confronti puri per pagina sono memoizzati per parametri e indice; le righe di fusione sono copie, senza trasferire esiti visuali tra configurazioni. Il shortlist limita il visual; il confronto testuale può ancora esaminare molte pagine recuperate. Questo resta un limite reale dell'ottimizzazione, visibile nei contatori, senza cache globale dei testi caricati.

Contatori finali p95: initial 2401.0 pagine canoniche distinte recuperate nell'unione delle query; text 3523.0 coppie pagina input/canonica confrontate; visual 1.0 identità. Le pagine canoniche possono essere confrontate con più pagine dell'input. Totale rendering visuali nei 390 riconoscimenti temporizzati: 60. Il top-K limita il canale visuale, mentre il confronto testuale resta il limite principale indicato dal profilo.

Il primo grid completo aveva zero false accept sui negativi ma un'identità errata in tutte le configurazioni: crop 5% del template ANAC 614. La firma testuale dominante indicava 614, il visual sotto soglia impediva il match, e il fallback lessicale sceglieva 612. La correzione aggiunge un veto generale contro l'identificazione contraria a una firma dominante sicura, senza abbassare la soglia visuale né promuovere automaticamente la firma rifiutata. Tentativo fallito e diagnosi conservati; calibrazione completa ripetuta sul codice corretto prima del freeze.

## Copertura e canonical

941/1212 firme operative (77.64%); 941/1158 con file (81.26%); 0 nuove identità effettivamente recuperate. 33 richieste di rete autorizzate nel solo manutentore hanno recuperato byte per otto ID, senza sufficiente prova per renderli active. Nessun denominatore cambiato. Risorse legacy non supportate, robots e conflitti di identità restano limiti reali. 48 binding condivisi, 24 gruppi classificati in audit; nessuna identità esatta ottenuta dal solo SHA condiviso. Le 979 risorse active unambiguous sono il denominatore canonical; i 1.027 binding complessivi non sono 1.027 identità certe.

Exact-resource lookup: 1027/1027 binding, 1003 SHA distinti, byte della cache verificati prima del lookup. Questa misura include risorse condivise e prova soltanto l'identità dei byte, separatamente dal riconoscimento dell'identità documentale.

## Generazione compilati

Sviluppo: 50/50 generati, riaperti e verificati prima del riconoscimento; QA visiva su dieci template, approfondita sui tre problematici. Campi reali, checkbox Unicode e font automatici corretti; overlay statici in spazi liberi con widget appiattiti, titoli/codici/enti preservati. Solo valori chiaramente fittizi, CF invalido ed email `.invalid`. Non viene rivendicata compilazione completa o validità amministrativa.

Evaluation: 50 tentativi, 50 generati/riaperti/verificati (100.00%); metodi {'real_fields_pypdf_persisted': 50}. I fallimenti di generazione sono separati dal richiamo di riconoscimento, come richiesto per Round 8. Le vecchie metriche R7 restano 9/50 e 41 fallimenti sul piano storico.

La validità dei compilati è meccanica: persistenza di valori sintetici dopo riapertura, non completezza o correttezza amministrativa. QA visuale aggiuntiva prima del riconoscimento sulle prime pagine dei dieci template nuovi (variante 1), approfondita su 360 e 1133; intestazioni e codici conservati. Nel template 1133 una data compare anche nel campo del luogo di nascita; alcuni campi generici comune/indirizzo ripetono una via fittizia. Campi non riconosciuti e controlli radio possono restare vuoti. Limiti registrati in `evaluation_filled_visual_qa.json`, senza cambiare generatore, casi, etichette o denominatori dopo il freeze.

## Nuova evaluation v4 single-shot

Piano: 40 identità, 10 fonti, concentrazione massima per ID 12.50%; distribuzione ID {'2': 5, '3': 5, '5': 5, '10': 5, '12': 4, '14': 1, '15': 5, '16': 5, '18': 4, '19': 1}. Generati tutti i 356 input, incluse 266 scansioni e 50 compilati. Piano, leakage, generazione e unica invocazione sono registrati separatamente con orari e SHA. Controlli di overlap su ID, SHA, URL, titolo/codice/versione, field-set e sketch quasi duplicati: zero leakage proibito secondo le regole dichiarate. Sono trasformazioni sintetiche di file noti, non scansioni di utenti reali. Le varianti sono correlate per template.

Risultati persistiti: 6 identità, 3 fonti, distribuzione ID {'3': 2, '15': 1, '16': 3}, concentrazione per ID 50.00%; distribuzione delle 50 rappresentazioni salvate {'3': 13, '15': 13, '16': 24}. Il sottoinsieme dipende dall'ordine di completamento dei worker e non rappresenta il piano. Il pool ha atteso il lavoro già inviato prima dell'uscita, ma gli esiti assenti dal checkpoint non sono recuperabili: non vengono inventati né classificati come rifiuti o errori di riconoscimento. `evaluation_interruption.json` contiene audit, SHA del log e del checkpoint e gli ID senza osservazioni. Copia byte-identica del checkpoint conservata. Adeguatezza e precisione/richiamo principali restano non qualificati; tabella seguente soltanto descrittiva.

| Misura | N | Exact | Family | Rifiuti | Errati | Precisione | Richiamo |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Canonical unambiguous | 979 | 979 | 0 | 0 | 0 | 100.00% | 100.00% |
| Evaluation v4 PARZIALE | 50 | 36 | 0 | 14 | 0 | 100.00% | 72.00% |
| Scan v4 PARZIALE | 39 | 25 | 0 | 14 | 0 | 100.00% | 64.10% |
| Filled v4 PARZIALE | 5 | 5 | 0 | 0 | 0 | 100.00% | 100.00% |

Richiamo utile di gate = exact recall: 0/16 famiglie valutabili, capacità `insufficiently_validated`. Le osservazioni esplorative non aumentano il richiamo utile.

Retrieval @1/@5/@10/@25: `{"1": {"numerator": 44, "denominator": 50}, "5": {"numerator": 50, "denominator": 50}, "10": {"numerator": 50, "denominator": 50}, "25": {"numerator": 50, "denominator": 50}}`. Il lookup SHA dei file canonici identici conta come rank 1; per le rappresentazioni trasformate il rango proviene dal retrieval per pagina prima della fusione. Fallimenti scan: `{'decision failure': 14}`. CSV con score atteso, OCR, char, visual, ancore, rango, ente/versione, veto, soglie e margine. Un visual non attivato è indicato 0 nella riga numerica e non equivale a uno score visuale misurato.

## Unknown e regressioni

Unknown storici: 137, rifiuti corretti 137, false accept 0; 2 errori di estrazione inclusi come rifiuti prudenziali. Zero nuovi unknown indipendenti. Le label sono historical_only: il gate unknown principale confirmed resta non misurato e blocca la promozione. Il rifiuto storico è una metrica diagnostica separata.

| Corpus storico invariato | Casi | Corretti | Falliti |
| --- | --- | --- | --- |
| catalog_coverage | 1212 | 1169 | 43 |
| development_compat_v2 | 37 | 35 | 2 |
| development_regression | 35 | 35 | 0 |
| family_release_v3 | 161 | 161 | 0 |
| hard_negatives_v1 | 30 | 30 | 0 |
| hard_negatives_v2 | 100 | 100 | 0 |
| release_locked_v1 | 69 | 59 | 10 |
| release_locked_v2 | 69 | 69 | 0 |

R061: NO_MATCH; cinque casi critici 5/5 safe. Tutti gli expected originali sono conservati; discrepanze positive e contraddizioni rimangono visibili. OCR reale: 7/7 storico e 14/14 sintetico, separato da validazione editoriale e da collaudo su altri sistemi.

La compatibilità sintetica v2 conserva due NO storici accettati come documento: EX02MISSINGREV e EX03MISSINGREV, entrambi `ambiguous` nel registro, osservati rispettivamente come ID 13 e 12. Restano false accettazioni rispetto al contratto storico e fanno fallire il gate di sicurezza, anche se le etichette ambigue sono escluse dalla precisione principale. Nessuna correzione dopo l'evaluation. La CLI compatibilità esce con codice 1, come documentato in `ci_local.json`.

## Prestazioni e memoria

Riconoscimento warm in processo isolato: p50 65.97 ms, p95 350.13 ms. Gruppi `{"historical_fixed51": {"n": 306, "p50": 53.9319, "p95": 389.8528, "p99": 496.2293}, "representation:unknown": {"n": 210, "p50": 47.9758, "p95": 71.6188, "p99": 75.4907}, "representation:digital_pdf": {"n": 60, "p50": 128.025, "p95": 503.3517, "p99": 685.4829}, "representation:filled_acroform": {"n": 30, "p50": 257.7035, "p95": 431.4139, "p99": 463.8475}, "representation:docx": {"n": 6, "p50": 137.2658, "p95": 193.1794, "p99": 207.5277}, "historical_scans": {"n": 84, "p50": 111.8861, "p95": 225.053, "p99": 232.5103}, "representation:image": {"n": 84, "p50": 111.8861, "p95": 225.053, "p99": 232.5103}}`. OCR escluso dal gate, generazione sketch e rendering visuale lazy inclusi. Stessi 35 testi sintetici+16 file del profilo storico, più 14 scansioni di sviluppo fissate prima della nuova evaluation. Tempi componenti non additivi in `performance_profile_components.json` e cProfile. E2E scan con OCR sull'unica evaluation: p50 1415.62 ms, p95 4688.56 ms; misura durante tre worker, distinta dalla latenza isolata del motore.

I tempi end-to-end v4 riguardano soltanto le 39 scansioni con osservazioni salvate, con tre worker e regressioni diagnostiche concorrenti: non rappresentano tutte le 266 scansioni preparate. Il profilo isolato usa esclusivamente gli input di sviluppo fissati prima dell'evaluation e non ripete i casi v4.

Nel profilo prestazionale il lookup SHA del file è disattivato, come nella misura R7, per misurare il lavoro effettivo di riconoscimento anche sugli originali. L'estrazione e l'enumerazione preliminare dei campi sono fuori dal cronometro; ogni ripetizione crea una richiesta nuova, senza riuso di firme o rendering dell'input tra ripetizioni.

| Componente (non additivo) | p50 ms | p95 ms |
| --- | --- | --- |
| normalization | 0.0158 | 0.2315 |
| input_fingerprint_generation | 0.5905 | 34.0359 |
| candidate_retrieval | 0.2629 | 2.0554 |
| ocr_sketch_compare | 0.0208 | 11.3725 |
| char_overlap | 0.029 | 14.6634 |
| visual_compare | 0.0029 | 2.3061 |
| decision_fusion_inclusive | 2.0769 | 270.9302 |
| family_fallback | 1.4233 | 9.5739 |

Indice V3 54455205 byte; disco 50850344 byte; RSS `{"before_warm_bytes": 324956160, "after_warm_bytes": 334249984, "samples": [334249984, 338358272, 342237184, 346206208, 351342592, 354979840, 358608896], "growth_after_warm_bytes": 24358912}`. Il limite di 100 MB si riferisce al deep size dell'indice canonico, non alla RSS dell'interprete o al JSON temporaneo di caricamento. Il profilo iniziale pre-ottimizzazione p95 345,30 ms è conservato. La baseline R7 misurata nuovamente prima dei cambiamenti era p95 281,51 ms; l'orfano diagnostico R7 rilevato all'inizio era stato fermato prima di queste misure.

## Test e CI

726 passed, 3 skipped, zero failed; Windows Python 3.12.10. Catalogo, bootstrap separato, hash storici e compileall verificati localmente. CI Ubuntu/macOS/Windows Python3.12 configurata, non eseguita esternamente: `pending_external_gate`. Nessun push. I test normali non richiedono cache ufficiali, Tesseract remoto, dati personali o rete.

Controlli mirati successivi al riepilogo UI: 75 passed; sono un sottoinsieme della suite, non ulteriori test distinti. Le validazioni diagnostiche unknown e family erano rimaste senza artefatto dopo l'interruzione manuale della sessione e sono state completate alla ripresa. La nuova evaluation v4 non è stata riavviata.

## Gate

| Gate | Target | Risultato | Esito |
| --- | --- | --- | --- |
| truth_classified | 0 unclassified | 0 | PASS |
| canonical_resource_lookup | 100% bytes lookup | 1027 | PASS |
| reconciled_confirmed_truth | all confirmed correct | 2 | PASS |
| coverage_file_backed | >=85% | 0.812607944732297 | FAIL |
| coverage_all | >=70% | 0.7764026402640264 | PASS |
| evaluation_complete | all prepared observations persisted | {"prepared": 356, "persisted": 50, "complete": false} | FAIL |
| evaluation_identities | >=25, target40 | 6 | FAIL |
| evaluation_sources | >=5, target8 | 3 | FAIL |
| source_concentration | <=30% | 0.5 | FAIL |
| evaluation_representations | >=350 | 50 | FAIL |
| scan_representations | >=200 | 39 | FAIL |
| filled_valid | >=30, target50 | 5 | FAIL |
| canonical_document_precision | >=100.00% | 1.0 | PASS |
| canonical_document_recall | >=100.00% | 1.0 | PASS |
| robustness_document_precision | >=99.50% | {"partial_observed": 1.0, "qualified": false} | FAIL |
| robustness_document_recall | >=90.00% | {"partial_observed": 0.72, "qualified": false} | FAIL |
| scan_document_precision | >=99.50% | {"partial_observed": 1.0, "qualified": false} | FAIL |
| scan_document_recall | >=85.00% | {"partial_observed": 0.6410256410256411, "qualified": false} | FAIL |
| filled_document_precision | >=99.50% | {"partial_observed": 1.0, "qualified": false} | FAIL |
| filled_document_recall | >=90.00% | {"partial_observed": 1.0, "qualified": false} | FAIL |
| wrong_accepted | <=0.5% | {"partial_observed": 0.0, "qualified": false} | FAIL |
| entity_error_rate | 0 | {"partial_numerator": 0, "qualified": false} | FAIL |
| version_year_error_rate | 0 | {"partial_numerator": 0, "qualified": false} | FAIL |
| filled_generation | >=90% | 1.0 | PASS |
| unknown_confirmed_main | >=99%, confirmed labels | None | FAIL |
| unknown_historical_rejection | >=99% diagnostic | 1.0 | PASS |
| historical_safety | zero historical NO false accepts and wrong identities | {"false_accepts": ["EX02MISSINGREV", "EX03MISSINGREV"], "wrong_identities": []} | FAIL |
| historical_five | 5 safe | 5 | PASS |
| R061 | NO_MATCH | NO_MATCH | PASS |
| real_ocr | 7/7 +14/14 | {"legacy": 7, "synthetic": 14} | PASS |
| performance_p50 | <=150ms | 65.9726 | PASS |
| performance_p95 | <=250ms | 350.1267 | FAIL |
| index_memory | <=100000000 bytes | 54455205 | PASS |
| tests | all green | {"passed": 726, "skipped": 3, "failed": 0, "seconds": 507.93, "log_sha256": "23872aa1bc336c27e9987f3a11b7905e8449aa647a539e5d25d65ead7528d75f", "platform": "Windows-11-10.0.26300-SP0", "python": "3.12.10", "post_report_checks": {"passed": 75, "failed": 0, "seconds": 11.15, "log_sha256": "53aa8566ffb6386c77be33d8b4ead2439427c2cfe3fdfede259c0aa4ac28981f", "scope": "Targeted UI/static-summary checks after reporting; not additional distinct tests."}} | PASS |
| external_ci | pending -> local RC only | pending_external_gate | INFO/PENDING |
| family_validation | >=5 evaluable; otherwise exact useful gate | 0 | INFO/PENDING |

## Archivio

`dist/BurOCRazia-v0.7.0-candidate-NOT-READY-round8.zip`. SHA256 e commit finale in `dist/package-verification.json` e nel file `.zip.sha256`, prodotti dopo il commit del rapporto. Git archive include soltanto i file tracciati. Esclusi PDF/DOCX ufficiali o compilati, cache, binari OCR, database personali, temporanei e credenziali. Stato **NOT READY**: nessun requisito senza prova viene dichiarato completato.

Dei 110 raw storici R6/R7 verificati immutati, 105 sono tracciati e verificati anche nello ZIP. I 5 checkpoint di sviluppo già ignorati restano soltanto nella workspace, con SHA verificato contro la baseline: `["benchmarks/results/round6/acquisition_checkpoint.json", "benchmarks/results/round6/calibration_checkpoint.json", "benchmarks/results/round6/evaluation_checkpoint.json", "benchmarks/results/round7/calibration_checkpoint.json", "benchmarks/results/round7/evaluation_checkpoint.json"]`. Non vengono aggiunti a Git per includere temporanei nell'archivio. Il verificatore riporta separatamente le due coperture.
