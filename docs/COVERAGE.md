# Copertura della candidata

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
