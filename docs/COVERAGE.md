# Copertura della candidata — Round 7 NOT READY

<!-- round7-current-start -->
Stato corrente: 1216 record reali, 1212 operativi e 4 rifiutati; seed e provenienze invariati. Firme attive per 941 identità: 77.64% sul totale e 81.26% sui 1158 documenti con file. Il gate dell'85% con file fallisce. Canonical su file 979/979; autocopertura dei metadati 1169/1212, misura distinta. Dettagli nel [rapporto Round 7](ROUND7_REPORT.md) e nel riepilogo in fondo.

## Archivio delle misure precedenti

Le sezioni seguenti conservano i risultati Round 3 e Round 2 e non costituiscono la copertura corrente.
<!-- round7-current-end -->

Round 3 non modifica il catalogo: 1.216 record reali conservati, 1.212 operativi, quattro rifiutati con storico/provenienza. Nessuna identità o famiglia verificata aggiunta. La copertura canonica del nuovo motore è **1.162/1.212** (prima 1.191/1.212), zero identità errate: i vincoli più prudenti introducono ulteriori rifiuti. È autocopertura sintetica dei metadati, distinta dal development ufficiale 58/150 e dal primo holdout indipendente 33/127 con cinque identificazioni errate. Non si dichiara riconoscibile ogni record censito; gate e dettagli in `BENCHMARK.md`.

Generato da `python scripts/release_report.py`. Catalogo `790b690123c82e1cb7bdfa67a10216284022987d50b0abbcc4a1a245785e3e99`.

| Misura | Baseline 0.6.1 | Candidata |
|---|---:|---:|
| Documenti reali | 389 | 1216 |
| Demo | 10 | 10 |
| Famiglie | 16 | 16 |
| Fonti registrate | 15 | 19 |
| Enti con documenti | 6 | 12 |
| Inventario IPA | 2499 | 2499 |
| Provenienza strutturale | 389 | 1216 |

Crescita: 827 identità (+212.60%). 1.212 record operativi restano da revisionare; quattro record informativi sono rifiutati con storico; nessuna spiegazione aggiunta, tre schede preesistenti conservate. Non si dichiara che ogni identità sia riconoscibile: la prova canonica è in `BENCHMARK.md`.

| Ente | Record |
|---|---:|
| Agenzia delle Entrate | 122 |
| Autorità Nazionale Anticorruzione | 7 |
| Dipartimento della Funzione Pubblica | 9 |
| Garante per la protezione dei dati personali | 17 |
| INAIL | 350 |
| INPS | 359 |
| Ispettorato Nazionale del Lavoro | 46 |
| Ministero del Lavoro | 102 |
| Ministero dell'Economia e delle Finanze / RGS | 15 |
| Ministero delle Imprese e del Made in Italy | 42 |
| Tribunale di Venezia | 143 |
| Unioncamere | 4 |

| Campo | Presente | Assente |
|---|---:|---:|
| codice | 429 | 787 |
| categoria | 546 | 670 |
| descrizione_ufficiale | 496 | 720 |
| versione | 513 | 703 |
| data_pubblicazione | 359 | 857 |
| download_url | 1161 | 55 |
| fonte_url | 1216 | 0 |

Identità, risorse e famiglie sono conteggi distinti: 1078 osservazioni di risorsa; 1181 URL di risorse distinti; zero file ufficiali redistribuiti. Gruppi di possibile identità duplicata: 3; gruppi con download condiviso: 8. Questi segnali includono dati ereditati e non autorizzano cancellazioni. Nessuna revoca o sostituzione automatica.

Tutte le 399 righe documentali iniziali, le 15 fonti, le 16 famiglie, i 2.499 enti, le 389 provenienze e le tre spiegazioni hanno impronte immutate. Le quattro nuove fonti restano `da_verificare`; il dominio ufficiale è verificato tecnicamente, senza attribuire una revisione umana. Record per fonte/categoria e gruppi di duplicazione sono in `coverage.json`.

## Round 2

Nessuna nuova identità: 1.216 record reali conservati, 1.212 operativi e 4 rifiutati (#429, #1077, #1081, #1091). Venezia conserva 143 record, 142 operativi: il file sull’obbligo di pagamento è informativo. Il controllo dei 150 file campionati non equivale a verifica integrale di tutte le 143 identità Venezia. Concentrazione catalogo: INPS 359/1216 (29,52%); nel benchmark ufficiale nessuna fonte supera il 20% dei positivi.

Schema 610, 1.078 osservazioni immutabili da ricevute effettive; 232 differenze di osservazione su record già presenti, senza sovrascrivere metadati o inventare sostituzioni. I campi codice/versione/data/download restano 429/513/359/1161. Tutte le righe v0.6.1 restano invariate; tutte le righe Round 1 sono preservate salvo quattro stati rifiutati esplicitamente documentati. Nessun file ufficiale, database operativo o eseguibile Tesseract incluso nello snapshot.

## Round 7 — NOT READY

Decision policy v3, retrieval v2 e nuova evaluation dopo freeze: 372 tentativi, 331 rappresentazioni generate su 42 identità, 280 scan-like, 9/50 AcroForm generati (41 fallimenti). Copertura 77.64% totale e 81.26% con file; canonical 979/979; richiamo robustness 49.19%, scansioni 47.86%, compilati 14.00% sul piano completo. Rifiuto unknown storico 100.00%; famiglie 0/16 valutabili, capacità non sufficientemente validata. p95 444.65 ms; indice 39832045 byte. Precisione exact 100% sui match emessi. La QA dei compilati mostra errori semantici e testo tagliato: nessuna validità amministrativa o qualità finale dei moduli rivendicata.

R6 ora development; v3 una sola esecuzione, senza retuning. 690 test passati, 3 saltati. CI esterna pending_external_gate. Software 0.6.1, schema 610 e catalogo di 1216 documenti preservati. Report e limiti: [ROUND7_REPORT.md](ROUND7_REPORT.md).


Denominatore con file invariato1158; tutte le acquisizioni fallite restano.14 identità con byte aggiuntivi,2 attive recuperate,9 quarantene per SHA condiviso. Unsupported reale, conflitto canonico e fonti bloccate sono distinguibili negli audit.
