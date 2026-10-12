# Registro delle modifiche

## Non rilasciato — candidata 0.7.0, 11 ottobre 2026

La versione software resta 0.6.1. Il Round 4 conserva i corpus precedenti e richiede una nuova valutazione indipendente; risultati correnti e gate esterni sono in `docs/BENCHMARK.md` e `docs/ROUND4_REPORT.md`. Nessun tag o release.

- Round 4: audit dei cinque errori accettati, codici segmentati prioritari senza eliminare le ambiguità, titoli generici nel corpo non sufficienti, vincoli su peer annuali, sottotipi e numeri di allegato; emittente esplicito distinto da destinatari/riferimenti deboli;
- R061 rifiutato con contesto indipendente per la famiglia di addebito; test positivi e negativi vicini, soglie globali conservate; 16 famiglie pregresse senza nuove verifiche editoriali;
- stress famiglie con corpus v1 conservato e correzioni di fixture in v2/v3 motivate, più supplemento ufficiale disponibile; precisione sintetica separata dalla copertura reale;
- freeze del motore dopo le verifiche locali, acquisizione ufficiale v2 separata e opt-in, controllo leakage canonico e unica valutazione con bootstrap 10.000; nessuna correzione del motore dopo i risultati;
- nuova misura di latenza/RSS, OCR reale e matrice CI offline; UI richiede v2 per l'holdout indipendente e presenta v1 come storico. Nessuna espansione del catalogo.

- Round 3: audit di tutti i 150 positivi ufficiali e 123 rifiuti; il campione Round 2 è development e locked v1 resta storico. Titoli in finestre, codici segmentati, vincoli espliciti di ente/versione e 88 profili tecnici riproducibili portano gli esatti da 27 a 58/150, senza accettazioni errate nel development finale;
- conversione generale IRI→URI, diagnostica della qualità estratta e fallback OCR limitato per layer inutilizzabile; nessun trasporto operativo o cache di testo personale;
- protocollo holdout con congelamento del runtime prima dell'acquisizione, controllo leakage e unica prima valutazione, compresi gli errori di estrazione nei denominatori; nessuna nuova identità o famiglia verificata;
- misure alternate di latenza e processi distinti per RSS, catalogo e indici; audit dei tre gruppi identità e otto URL condivisi, senza fusioni automatiche;
- UI con precedenza a holdout, negativi, OCR e prestazioni; CI multipiattaforma resta un gate esterno non eseguito. Limiti, raw e piano Round 4 pubblicati nella candidata.
- gate testuale v2 68/69: R061 è un'accettazione di famiglia errata; il risultato è arrivato dopo il freeze ed è conservato come blocco aggiuntivo, con release-fast exit 1. Nessuna etichetta o soglia viene cambiata per rimuoverlo.

- Round 2: audit della baseline e dei dieci fallimenti locked; v1 immutato, v2 con dieci etichette motivate; 100 hard negatives sintetici e campione di 150 moduli più 12 negativi ufficiali, senza redistribuire file;
- disambiguazione dei titoli completi rispetto ai loro sottotitoli letterali; analisi annualità per richiesta e cache dei soli metadati; riferimento full scan e test differenziale anche canonico;
- Tesseract reale 5.4 con ita/eng/osd: 7/7 gate storici e 14/14 OCR sintetici, zero residui del gate; configurazione locale riproducibile con hash;
- schema 610 aggiuntivo: 1.078 osservazioni tecniche, 232 differenze conservate senza sovrascrittura, quattro rifiuti tecnici tracciati (un file informativo Venezia e tre FAQ INAIL), zero verifiche umane o sostituzioni inventate; tutte le altre righe Round 1 preservate;
- catalogo fermo a 1.216 identità reali: l'espansione ulteriore è subordinata ai gate di qualità.

- catalogo: 1.216 documenti reali (+827), 10 demo, 16 famiglie, 19 fonti e 2.499 enti IPA; tutte le righe preesistenti conservate;
- manutenzione HTTPS separata e opt-in, policy domini/robots/redirect, parser offline, ricevute con hash e import tramite pacchetto transazionale;
- riconoscimento più prudente per guide/manuali, ente nell'intestazione, riferimenti incidentali ai codici, revisioni e anni di leggi; titoli forti limitati ai primi 2.000 caratteri; demo operative soltanto con il loro codice esplicito;
- cache limitata ai metadati del catalogo, con prova differenziale sui corpus testuali;
- valutazioni separate, corpus congelati, benchmark ufficiale locale, generatore OCR riproducibile e pagina Benchmark statica/inerte;
- documentazione quantitativa e workflow offline rafforzati. Risultati e gate reali in `docs/BENCHMARK.md`, senza dichiarare superato ciò che non è stato eseguito.

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

## Round 5 — candidate NOT READY

Fingerprint v1 minimizzate, lookup SHA e shortlist locale; nessuna nuova identità o migrazione SQL. Benchmark separati e gate non superati. Suite 615 test completa, zero falliti,3 skip. Vedi docs/ROUND5_REPORT.md.

## Round 6 — NOT READY

Firme v2 e benchmark separati per copertura, canonical, robustezza, compilazione, OCR, family, unknown, regressioni, memoria e latenza. Zero nuove identità; seed/schema 610 invariati. V1 e corpus storici conservati. Tutti i dati sintetici compilati sono fittizi; nessun file ufficiale o testo OCR redistribuito. Dettagli e limiti in `docs/ROUND6_REPORT.md`.
