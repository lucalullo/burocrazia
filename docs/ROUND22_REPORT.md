# Round 22 — READY LOCALLY

**READY LOCALLY**. Gate bloccanti falliti: `[]`. Il generatore passa; la decisione RC dipende dalle misure V6 effettive e dalle verifiche finali. Nessun tuning dopo la V6.

## Versione e confini

Pubblico **0.6.1**, schema **610**, branch `codex/coverage-benchmark-v0.7.0`, HEAD `7da8b10f3d7c8ea302d7a3dd565f265bf5c5f370`. Nessun commit, push, tag o pubblicazione. Freeze content-addressed `8c2a50e2dd31dbb2110d1fc4b41ebf56c3bc5eb58f221857515c92edeec9d273`, non un commit Git. Il Git tree storico di riferimento del solo motore è `9d08feb84dd6980ba374b3a3069d5c785e27b73c`; lo snapshot finale di packaging è distinto e riportato nel sidecar.

Recognition engine changed: **no**. Hash Round 21 = Round 22: `c077552055c25b0bc128e1a5c607afc434fb3bd074e6da165f3d8333145abf15`. Ogni file recognition, decision v7, soglia, peso, ranking, veto ente/versione, family logic, source profile, catalogo e fingerprint è identico. Nuovi file soltanto generator/validation/runner/checkpoint/docs e11 test infrastrutturali; test recognition preesistenti immutati. Proof prima/dopo in recognition_freeze_check.json e generator_change_scope.json. Dataset `eaac87ac81e03ba838b52d66992db20967e8c50bbcfd88b02d894c42ab68f4bd`, profilo v7 `410b19049b368d8b74a0ea1c80798db68737a23ab4164d4364062aad56d75c5b`, catalog semantic `b66ca13ee71f0a5a7e5c3dd8aec9888a7fcef1899b005f5bff1a079a962153df`.

## Evidenza preservata

V5 indipendente Round 19 originale: **P98,2456%, R70,5512%, scan R63,2937%**, immutata. Development v7 Round 21: **P100%, R90,3937%, scan R88,2937%, filled100%,0 false accept confermati**, invariato e separato dalla V6 indipendente.

Unknown4 originale Round 21 **120/120**,15 fonti,0 DOCUMENT/0 FAMILY false accept,0 errori ente/versione. Manifest `28d22c62765587e3d749772c4dfb19ac3b05d8244b4de71b8d01bc1356b82676`, raw `50dc1ac906d095b33a145ee27ef74c6462dca31c758d84af5671f0ee25fe2191`. Compatibilità con identico motore verificata; **zero nuove predizioni unknown4**, nessun resampling/relabel/tuning. Nel mix end-to-end sono riusate tutte le120 righe originali.

## Filled generation prima

Round 21: **100 tentativi,75 validi,25 falliti**,75% sotto90%. Cinque varianti ciascuna per ID484/264/263/558/414, tutti statici senza widget. Causa: `static_overlay_failure / No safe blank overlay rectangle`, ricerca sulla sola prima pagina di sette riquadri larghi fissi. Audit25/25 senza recognition, CSV e rendering originali conservati. Le tre varianti digital normalized DOCX fallite (113/1121/1074, C14NError) restano agli atti e non vengono corrette in questo round.

## Generatore v2 e validazione

Policy `filled-generation-v2-round22` congelata prima dell'aggregazione: `303eb7d925918d2f0346d61ff598cb7b50901999aa791d241026351819fe0732`. AcroForm-native con persistenza dei valori widget e `/AP /N`; static overlay a larghezza misurata, griglia deterministica, ricerca multipagina, protezione di parole/inchiostro/linee/titolo/codice/emittente/anno. Fallback statico per AcroForm malformato/non salvabile su PDF valido, registrato senza inventare o ricostruire campi. Nessuna nuova pagina, resize, canvas esteso o testo invisibile; dati esclusivamente fittizi, seed/varianti originali.

File scritto atomicamente e riletto con SHA; non vuoto, riaperto, pagine/geometria coerenti, nessuna corruzione, valori sintetici verificati, template presente, parser locale sicuro e nessun riferimento attivo/esterno introdotto. Confronto raster144DPI fuori dai rettangoli compilati: frazione pixel diversi oltre8 livelli ≤0,0001, per ogni pagina di tutti100 file. Confronto testi originali e valori persistiti aggiuntivo. Controllo link/azioni include dizionari annidati; il test negativo che lo ha motivato è stato corretto prima della generazione aggregata.

QA visiva Poppler144DPI su tutte le cinque vecchie identità problematiche più un AcroForm: valori leggibili, template/titoli/annualità conservati, nessun overlap o clipping del contenuto originale. Gli overlay sono perturbazioni sintetiche in spazi liberi, **non una compilazione semantica dei campi né documenti da presentare a un ente**. I valori restano nella copia benchmark privata. Tutti60 overlay hanno conservato e verificato le sette stringhe previste; minimo policy1 non usato per gonfiare il conteggio.

## Filled generation dopo

**100 tentativi / 100 validi = 100.00%**, gate90% PASS e target95% PASS. Modalità `{'acroform_native': 40, 'static_overlay': 60}`, fallback effettivi `10`, fallimenti `0`. Medesime20 identità e5 varianti/case ID/seed ciascuna; rigenerazione coerente di tutti100 autorizzata prima di qualunque predizione. I75 output vecchi rimangono intatti. Nessuna sostituzione più facile o selezione basata su score.

## Preflight e freeze V6

**40 identità / 8 fonti / 597 noti / 420 scan / 100 filled**, concentrazione massima15%. Selezione originale `{'2': 6, '3': 5, '5': 5, '10': 6, '14': 3, '15': 6, '16': 6, '18': 3}`,639 ID/8 fonti prenotati, nessuna espansione catalogo. Le fonti Garante e ANAC sono rappresentate da sole3 identità ciascuna, limite esplicito.

I497 nonfilled Round 21 sono riusati byte-identici, mai predetti prima; i100 filled sono v2. Le3 digital normalized fallite sono escluse con prova del fallimento, non conteggiate come recognition failures. Leakage **0**: nessun tuning identity/V5/observed SHA/equivalent transform/unknown overlap/duplicato/ambiguità vietati. I seed riservati Round 21 sono gli stessi perché mai usati in predizioni V6; non è una nuova realizzazione selezionata a posteriori. Unknown4 disponibile120 compatibile.

Ogni representation è vincolata da case ID, expected identity, SHA, path, transform metadata e validation status. Freeze content-addressed lega motore/catalogo/dataset/registry/identità/trasformazioni/policy filled/unknown manifest+raw/leakage/generator result/manifest byte e codice. Zero commit. Dopo il freeze e il primo risultato: nessuna modifica a recognition, generatore, policy, label, selezione o seed.

## V6 single-shot

Transactional journal, expected count **597**, actual **597**, ID unici **597**, raw SHA `6a230f43e2e98e4633520c8de5e99075af15c51b9d5090ce7a86217b10d19afe`. Resume soltanto pending ID con identico freeze/input/code; nessun replay completato.

Noti **597**: TP/exact **560**, FP/wrong **0**, FN **37**, family **0**, reject **37**, extraction failures **0**. **P100.0000%, R93.8023%, F196.8021%**. Errori ente **0**, versione **0**. CI95 nominali Wilson: precisione `{'lower': 0.9931869876530032, 'method': 'Nominal Wilson95%; representation rows are correlated by40 selected identities,not a population guarantee.', 'upper': 1}`, recall `{'lower': 0.9157414400337474, 'method': 'Nominal Wilson95%; representation rows are correlated by40 selected identities,not a population guarantee.', 'upper': 0.9547044859623082}`. Le righe sono correlate per40 identità; questi intervalli descrittivi non forniscono una garanzia di generalizzazione alla popolazione.

Failure audit e breakdown per fonte/trasformazione preservati; nessuna correzione dopo il risultato. Da un futuro round che usi questi errori per tuning, la V6 resta storico indipendente del motore congelato e non può essere ripresentata come held-out del nuovo motore.

## Retrieval

@1 **99.3300%**, @5 **99.3300%**, @10 **100.0000%**, @25 **100.0000%**. Gate obbligatorio @25=100%; @1≥99% è il target distinto previsto dal Round 22, non viene trasformato in un gate diverso.

## Scan

**N420, exact392, wrong0, P100.0000%, R93.3333%**. Gate P99,5%/R85%. Tesseract locale reale; immagini sintetiche correlate agli originali ufficiali, non scansioni personali raccolte sul campo.

| Trasformazione | N | Exact | Wrong | P | R |
| --- | --- | --- | --- | --- | --- |
| blur_mild | 30 | 28 | 0 | 100.0000% | 93.3333% |
| contrast_minus20 | 30 | 29 | 0 | 100.0000% | 96.6667% |
| crop_2pct | 30 | 27 | 0 | 100.0000% | 90.0000% |
| crop_5pct | 30 | 24 | 0 | 100.0000% | 80.0000% |
| digital_canonical_derivative | 40 | 38 | 0 | 100.0000% | 95.0000% |
| digital_normalized | 37 | 35 | 0 | 100.0000% | 94.5946% |
| filled_0 | 20 | 19 | 0 | 100.0000% | 95.0000% |
| filled_1 | 20 | 19 | 0 | 100.0000% | 95.0000% |
| filled_2 | 20 | 19 | 0 | 100.0000% | 95.0000% |
| filled_3 | 20 | 19 | 0 | 100.0000% | 95.0000% |
| filled_4 | 20 | 19 | 0 | 100.0000% | 95.0000% |
| first_page_only | 30 | 29 | 0 | 100.0000% | 96.6667% |
| grayscale | 30 | 28 | 0 | 100.0000% | 93.3333% |
| jpeg_60 | 30 | 29 | 0 | 100.0000% | 96.6667% |
| jpeg_75 | 30 | 30 | 0 | 100.0000% | 100.0000% |
| jpeg_90 | 30 | 28 | 0 | 100.0000% | 93.3333% |
| raster_150 | 30 | 29 | 0 | 100.0000% | 96.6667% |
| raster_200 | 30 | 28 | 0 | 100.0000% | 93.3333% |
| rotation_180 | 30 | 28 | 0 | 100.0000% | 93.3333% |
| rotation_270 | 30 | 27 | 0 | 100.0000% | 90.0000% |
| rotation_90 | 30 | 28 | 0 | 100.0000% | 93.3333% |

## Filled conditional e end-to-end

Generation100/100 =100%; recognition conditional **N100, exact95, wrong0, P100.0000%, R95.0000%**. End-to-end **95/100 = 95.0000%**. Generazione e recognition restano metriche separate; nessun failure generator viene passato al motore o contato come errore recognition.

## Unknown mix e family

Mix end-to-end: 597known + **120unknown originali**,120correct reject,0 false accept,0 nuove chiamate unknown. Wrong FAMILY su unknown è false accept. Family logic invariata, **experimental / insufficiently validated**; non contribuisce exact recall.

## Canonical, coverage, safety

Canonical post-V6 **1007/1007**, P/R100% se gatePASS. Coverage **86.528497% (1002/1158)**, catalogo1216 documenti/19 fonti/16 famiglie invariati. Safety post-V6 **705 negativi confermati, FA `[]`**, hard negative **260/260**. Vecchi8 falseaccept valutati, ANAC/R061/EX02/EX03 secondo truth policy nei contratti storici. Input safety9/9, rifiuti parser prima di recognition, nessuna falsa attribuzione di successo unknown a input non supportati.

Release diagnostic **1258 contratti PASS**; storico originale **1517**, **15 mismatch/exit1** mantenuti come evidenza di etichette ambigue/incompatibili, non azzerati o nascosti. Le verifiche post-V6 sono replay di validazione espressamente richiesti, non tuning.

## Performance post-V6

| Run | p50 ms | p95 ms |
| --- | --- | --- |
| 1 | 44.1393 | 201.5051 |
| 2 | 38.0953 | 186.2339 |
| 3 | 39.0171 | 186.0883 |
| 4 | 38.1614 | 200.2265 |
| 5 | 46.0415 | 182.9508 |
| 6 | 39.4022 | 185.3854 |
| 7 | 38.5286 | 184.7144 |

Tutti7 run predeterminati e isolati,67 input/402 richieste per run/2814 timing. **p95 mediano 186.0883ms**, `7/7`≤250ms. Nessuna ottimizzazione dopo V6. Baseline Round 21 176,6788ms separata. Matching warm, estrazione/OCR fuori timing, RequestPages nuove, cache soltanto metadati catalogo.

## Test e collaudo

Baseline precedente878/0/3 preservata. Nuovi11 test generator: native/malformed fallback/static, multipagina, riapertura, valori/checkbox/date/numeri, seed, template, cleanup, riferimenti/failure receipts. **Full post-V6 889pass/0fail/3skip**,589.18s, log SHA `dad1f5d45253a9d18c4b1794639ec3dcadda625fdce6386d9bb77b3afd223398`. Test recognition vecchi immutati. Compile, SQLite integrity/FK, migrazione610idempotente/conteggi, profili/fingerprint/truth/observations schema e CLI verificati sul freeze. Skip Windows symlink/FIFO; collaudo Windows/Python3.12.10, nessun collaudo Linux/macOS. CI **external pending**.

## Breakdown fonti

| Fonte | N | Exact | Wrong | P | R |
| --- | --- | --- | --- | --- | --- |
| 2 | 116 | 109 | 0 | 100.0000% | 93.9655% |
| 3 | 65 | 45 | 0 | 100.0000% | 69.2308% |
| 5 | 61 | 57 | 0 | 100.0000% | 93.4426% |
| 10 | 111 | 110 | 0 | 100.0000% | 99.0991% |
| 14 | 6 | 6 | 0 | 100.0000% | 100.0000% |
| 15 | 116 | 115 | 0 | 100.0000% | 99.1379% |
| 16 | 64 | 62 | 0 | 100.0000% | 96.8750% |
| 18 | 58 | 56 | 0 | 100.0000% | 96.5517% |

## Gate RC

| Gate | Actual | Target | Esito |
| --- | --- | --- | --- |
| recognition_engine_unchanged | c077552055c25b0bc128e1a5c607afc434fb3bd074e6da165f3d8333145abf15 | Equal Round 21 semantic hash and every recognition/profile/catalog/dataset byte | PASS |
| dev_precision | 1.0 | >=99.5% | PASS |
| dev_recall | 0.9039370078740158 | >=90% | PASS |
| dev_scan_recall | 0.8829365079365079 | >=85% | PASS |
| dev_confirmed_false_accepts | 0 | 0 | PASS |
| filled_generation | 1.0 | >=90%, >=50valid | PASS |
| fresh_preflight | See linked artifact | 40 IDs/8sources, >=400known/200scan/50filled, leakage0 | PASS |
| unknown_v4_preserved | 120 | 120/120, no replay | PASS |
| unknown_end_to_end | 1.0 | Frozen V6 requirement | PASS |
| v6_entity_version | See linked artifact | Frozen V6 requirement | PASS |
| v6_exact_recall | 0.9380234505862647 | Frozen V6 requirement | PASS |
| v6_filled_generation | 1.0 | Frozen V6 requirement | PASS |
| v6_filled_precision | 1.0 | Frozen V6 requirement | PASS |
| v6_filled_recall | 0.95 | Frozen V6 requirement | PASS |
| v6_precision | 1.0 | Frozen V6 requirement | PASS |
| v6_retrieval_at1_target | 0.9932998324958124 | Frozen V6 requirement | PASS |
| v6_retrieval_at25 | 1.0 | Frozen V6 requirement | PASS |
| v6_scan_precision | 1.0 | Frozen V6 requirement | PASS |
| v6_scan_recall | 0.9333333333333333 | Frozen V6 requirement | PASS |
| canonical_post_v6 | See linked artifact | 1007/1007 | PASS |
| confirmed_safety_post_v6 | See linked artifact | 0 confirmed false accepts | PASS |
| input_safety | See linked artifact | 100% safe refusal | PASS |
| coverage | 86.52849740932642 | >=85% | PASS |
| performance_median_p95 | 186.0883 | 7runs, medianp95<=250ms | PASS |
| full_tests | See linked artifact | 0 failures | PASS |
| final_checks | True | compile, catalog, FK, migration610, release contracts, schemas | PASS |

## Limiti e archivio

**READY LOCALLY**, gate bloccanti falliti `[]`. Campione40 identità e trasformazioni correlate; QA sintetica filled overlay non equivale a compilazione semanticamente corretta o a scansioni di utenti. Fonti minori3ID, tre digital normalized non generabili conservate, family insufficiente, CI multipiattaforma esterna pending. Nessun LLM/rete/telemetria nel runtime, nessun dato personale, nessuna attribuzione editoriale automatica o consulenza personalizzata.

Archivio `dist/BurOCRazia-v0.7.0-RC1-round22.zip`. SHA256 e Git tree finale nel sidecar `dist/package-verification-round22.json`; riportati anche nella consegna finale, evitando autoreferenza dell'hash dentro lo ZIP. Verifica raw storici, freeze, conteggi, SHA, manifest, gen-v2 e hygiene; cache/work/PDF ufficiali/compilati/checkpoint/DB di lavoro/log esclusi. Tutte le evidenze negative rimangono. HEAD e indice originale immutati, nessun commit/push/tag/release.

Goal ufficiale finito Round 22 e checkpoint privati append-only; a ogni ripresa si verificano processi/journal/output per evitare duplicati. Automazione oraria assente nell'app, nessun wakeup periodico dichiarato. Il Goal termina soltanto dopo il packaging verificato.

## Serializzazione storica verificata

Il controllo esteso dei1554 file protetti ha individuato **81 differenze preesistenti LF/CRLF/miste** tra byte fisici,Git blob e archivio. Ogni file locale conserva il suo SHA di ingresso; ogni file ZIP interessato è byte-identico al precedente ZIP Round21 e tutte le forme differiscono esclusivamente per CRLF/LF. Nessun file locale è stato normalizzato. I corpus congelati e i file semantici restano verificati separatamente con i loro hash originali. Allowlist e hash delle tre forme in archive_serialization_audit.json. Il primo ZIP rifiutato dal verificatore è preservato in `dist/attempts/round22-package-initial-381b3cad17244607770fe5b44d3db76d909b2d68f4880a047811bc473c34becf.zip`,SHA `381b3cad17244607770fe5b44d3db76d909b2d68f4880a047811bc473c34becf`; nessuna predizione o misura scientifica è stata ripetuta per correggere questo controllo di packaging.
