# Registro delle modifiche

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
