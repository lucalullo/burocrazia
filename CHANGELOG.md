# Registro delle modifiche

## 0.7.0-rc1 — 14 ottobre 2026

Release candidate pre-1.0; la stable pubblica resta v0.6.1 e lo schema SQLite resta 610.

### Affidabilità

- catalogo ampliato da 389 a 1216 record reali, con 12 enti, 19 fonti e provenienze conservate; copertura delle identità con file 1002/1158 (86,53%);
- fingerprint deterministici locali, confronto per pagina e decision policy v7; rifiuti prudenti e veto per conflitti di ente/versione;
- robustezza su scansioni e compilati verificata senza modificare il motore dopo il congelamento;
- truth e contamination policy versionate; V5 originale storico, replay development e nuovi single-shot tenuti distinti;
- protezioni parser, persistenza e rendering dei dati conservate; nessun LLM o API cloud nel runtime locale.

### Interfaccia

- risultati statici delle valutazioni disponibili nella sezione Benchmark;
- funzionamento su loopback e OCR Tesseract locale; family matching sperimentale e insufficientemente validato.

### Validazione

V6 indipendente: **560/597 exact**, precisione **100%**, recall **93,80%**; scan recall **93,33%**, filled recall **95%**, generazione compilati **100/100**. Retrieval@1 **99,33%**, @25 **100%**; errori ente/versione **0/0**. Unknown v4 single-shot **120/120**; canonical **1007/1007**; safety **705 negativi, 0 false accept**. Mediana di sette p95 warm **186,09 ms**; suite RC di riferimento **889 pass, 0 fail, 3 skip**.

Benchmark locali su template ufficiali e trasformazioni sintetiche con OCR reale, non certificazione. V6 e unknown v4 restano congelati senza replay. Dettagli in [docs/BENCHMARK.md](docs/BENCHMARK.md) e [release notes](docs/RELEASE_NOTES_v0.7.0-rc1.md).

## 0.6.1 — 5 settembre 2026

Release di consolidamento e rifinitura dell'MVP locale.

### Affidabilità

- documenti rifiutati esclusi dal matching operativo, con record e storico conservati;
- verifica delle spiegazioni bloccata quando manca il testo minimo o il documento è rifiutato;
- impronta del contesto di riconoscimento allineata agli stati che influenzano i candidati;
- autorotazione OCR applicata anche ai PDF scannerizzati;
- risorse locali isolate correttamente tra database distinti;
- correzioni Windows su lifecycle SQLite, fixture DOCX, subprocess OCR e test symlink;
- benchmark di regressione sintetico invariato.

### Interfaccia

- selettore **Chiaro / Scuro** visibile nella barra laterale;
- navigazione rinominata in modo più chiaro senza eliminare Catalogo, Fonti e Revisione;
- stato del catalogo ridotto alle informazioni utili e spostato in un riquadro chiuso;
- testo iniziale e reset della sessione semplificati;
- dettagli tecnici mantenuti nelle aree dedicate invece di occupare la vista principale.

### Validazione

Sul collaudo Windows 11 / Python 3.12 sono stati registrati **453 test superati e 3 saltati**, senza fallimenti. Il runner con Tesseract reale ha superato **7/7** casi e non ha lasciato residui temporanei finali. La prova browser offline sui tre esempi sintetici ha prodotto `DOCUMENT_MATCH`, `FAMILY_MATCH` e `NO_MATCH` come previsto.

Vedi [docs/VALIDAZIONE.md](docs/VALIDAZIONE.md).

Catalogo, identificativi, enti, famiglie, provenienza, dipendenze principali e schema restano preservati.

## 0.6.0 — 5 settembre 2026

Consolidamento incrementale della base v0.5.3.2:

- snapshot completo del catalogo con manifest SHA-256 e ripristino idempotente;
- avvio locale su loopback, telemetria disattivata e trasporti live disabilitati;
- limiti di acquisizione, OCR locale e gestione prudente di annualità ed enti;
- migrazioni, backup, revisione append-only e pacchetti locali;
- famiglie documentali, provenienza, spiegazioni editoriali e regressioni sintetiche;
- workflow CI e documentazione per installazione e funzionamento offline.

Nessuna verifica editoriale è stata attribuita automaticamente e nessun contenuto mancante è stato inventato.
