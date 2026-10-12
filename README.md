# BurOCRazia

**Capire la burocrazia, più chiaramente.**

BurOCRazia è un'applicazione locale e deterministica per il riconoscimento prudente di documenti amministrativi italiani. Riceve PDF, DOCX, TXT e immagini, estrae il testo, usa OCR locale quando necessario e confronta il contenuto con un catalogo SQLite installato sul computer.

[English version](README_EN.md)

## Obiettivo

BurOCRazia nasce per rispondere a una domanda semplice:

> **Che documento ho ricevuto?**

Il sistema prova a identificare il documento senza forzare una risposta quando le evidenze non sono sufficienti. I tre esiti possibili sono:

- `DOCUMENT_MATCH` - documento specifico riconosciuto;
- `FAMILY_MATCH` - famiglia documentale riconosciuta, ma documento/versione specifici non confermati;
- `NO_MATCH` - evidenze insufficienti per un'identificazione affidabile.

Un `NO_MATCH` corretto è preferibile a un falso positivo.

## Funzioni principali

- riconoscimento locale di documenti amministrativi;
- estrazione testo da PDF, DOCX e TXT;
- OCR locale con Tesseract per immagini e PDF scannerizzati;
- autorotazione OCR a 0°, 90°, 180° e 270°;
- controllo di ente, codice, titolo, versione e annualità;
- riconoscimento per famiglie documentali quando il record specifico non è sufficientemente certo;
- catalogo SQLite con documenti, enti, fonti, famiglie, provenienza e spiegazioni editoriali;
- consultazione locale di catalogo e fonti;
- revisione editoriale con storico delle decisioni;
- pacchetti locali versionati per aggiornare i dati senza acquisizioni live;
- esecuzione sul solo loopback locale;
- nessun invio dei documenti a LLM, API cloud o servizi esterni nel normale flusso applicativo.

## Cosa contiene questa candidata

Lo snapshot distribuito con questa candidata contiene:

| Contenuto | Quantità |
| --- | ---: |
| Record documentali reali | 1216 |
| Record dimostrativi | 10 |
| Famiglie documentali | 16 |
| Enti rappresentati dai documenti reali | 12 |
| Enti IPA censiti nell'inventario | 2.499 |
| Fonti registrate (15 verificate pregresse, 4 da verificare) | 19 |
| Provenienze dei documenti reali | 1216/1216 |
| Schede esplicative | 3 |
| Materiali ufficiali locali inclusi | 0 |

I 1216 record reali sono presenti nel catalogo, ma non risultano automaticamente revisionati manualmente. Le 3 schede esplicative incluse sono ancora in stato di verifica.

**Questi numeri descrivono il catalogo, non garantiscono che ogni possibile file venga riconosciuto.** Il risultato dipende dalla qualità del testo estratto e dalla presenza di evidenze sufficienti.

Ai sei enti originari elencati sotto si aggiungono MIMIT, Funzione Pubblica, Tribunale di Venezia, MEF/RGS, ANAC e Unioncamere. Gli enti originari sono:

- INPS;
- INAIL;
- Agenzia delle Entrate;
- Ministero del Lavoro;
- Ispettorato Nazionale del Lavoro;
- Garante per la protezione dei dati personali.

L'inventario IPA contiene inoltre 2.499 enti, ma non equivale a una copertura documentale di tutti quegli enti.

## Come funziona

```text
PDF / DOCX / TXT / immagine
          ↓
estrazione del testo
          ↓
OCR locale se necessario
          ↓
normalizzazione e segnali deterministici
          ↓
documento specifico / famiglia / rifiuto prudente
          ↓
catalogo, provenienza e spiegazione disponibile
```

Il motore considera, tra gli altri segnali:

- codice esatto;
- titolo;
- ente;
- parole chiave;
- similarità testuale;
- versione e annualità;
- frasi identificative delle famiglie;
- contraddizioni tra ente o versione;
- margine tra i candidati migliori.

Il punteggio interno mostrato nell'interfaccia è un indicatore del motore e **non è una probabilità statistica di correttezza**.

## Interfaccia

La navigazione principale comprende:

- **Riconosci** - carica e analizza un documento;
- **Catalogo** - consulta i record installati;
- **Fonti e provenienza** - consulta le informazioni di origine;
- **Revisione editoriale** - strumenti per la manutenzione dei contenuti.
- **Benchmark** - consulta i risultati statici delle valutazioni.

La barra laterale mostra anche un selettore **Chiaro / Scuro** e un riepilogo compatto del catalogo locale.

Le date visualizzate nell'interfaccia sono formattate in stile italiano `GG/MM/AAAA`.

## Requisiti

- Python `3.12` a 64 bit;
- dipendenze Python del progetto;
- Tesseract 5 per immagini e PDF scannerizzati;
- dati lingua Tesseract `ita` consigliati;
- browser moderno per l'interfaccia Streamlit.

Tesseract è necessario solo per il percorso OCR. PDF, DOCX e TXT con testo già estraibile possono essere elaborati senza OCR.

## Installazione

### Windows

Dalla cartella del progetto:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe scripts\check_environment.py
```

Se Tesseract è installato nel percorso standard ma non è nel `PATH`:

```powershell
$env:BUROCRAZIA_TESSERACT_CMD = "C:\Program Files\Tesseract-OCR\tesseract.exe"
```

Avvio:

```powershell
.\.venv\Scripts\python.exe run.py
```

Dopo la prima configurazione puoi usare anche:

```text
avvia.bat
```

`avvia.bat` non sostituisce l'installazione iniziale dell'ambiente Python.

### Linux / macOS

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python scripts/check_environment.py
.venv/bin/python run.py
```

Tesseract e i relativi dati lingua devono essere installati separatamente sul sistema.

## Utilizzo

Per impostazione predefinita BurOCRazia viene servita localmente su:

```text
http://127.0.0.1:8501/
```

Il launcher vincola il server al loopback locale. Per usare una porta diversa:

```bash
python run.py --port 8510
```

Per terminare l'applicazione usa `Ctrl+C` nel terminale.

### Demo inclusa

In `examples/riconoscimento/` sono inclusi tre file sintetici:

| Caso | Esito atteso |
| --- | --- |
| SR211 INPS | `DOCUMENT_MATCH` |
| Modello 730/2024 | `FAMILY_MATCH` |
| Testo non amministrativo | `NO_MATCH` |

Gli esempi non contengono dati personali.

## Offline e privacy

Il normale flusso applicativo è progettato per funzionare localmente:

- server su `127.0.0.1`;
- OCR locale;
- nessun LLM;
- nessuna API cloud;
- telemetria Streamlit disattivata;
- trasporti live del progetto disabilitati nella release locale;
- file caricati non aggiunti automaticamente al catalogo;
- temporanei OCR rimossi dal normale percorso applicativo.

BurOCRazia non equivale però a un sistema operativo isolato o a un firewall. Browser, sistema operativo, estensioni, backup, swap e altri processi restano fuori dal controllo dell'applicazione.

Per prove e sviluppo usa file sintetici o privi di dati personali.

## Limiti di acquisizione

La release applica limiti espliciti:

- file fino a 20 MiB;
- PDF fino a 100 pagine;
- OCR fino a 5 pagine;
- testo fino a 1.000.000 di caratteri.

I limiti servono a mantenere il comportamento prevedibile e a ridurre il rischio di elaborazioni eccessive.

## Aggiornamenti del catalogo

La release locale non esegue acquisizioni live dalle fonti istituzionali durante il normale utilizzo.

Gli aggiornamenti possono essere importati tramite pacchetti locali validati:

```bash
python scripts/import_package.py examples/pacchetto_demo.zip
```

L'importazione usa anteprima, hash e transazioni. Gli URL presenti nel catalogo sono conservati come riferimenti di provenienza e non implicano un controllo automatico della loro attualità.

Vedi [docs/PACCHETTI_LOCALI.md](docs/PACCHETTI_LOCALI.md).

## Validazione

La validazione di riferimento della v0.6.1 su Windows 11 / Python 3.12 ha registrato:

- **453 test superati**;
- **3 test saltati** per funzionalità di sistema non disponibili sulla piattaforma o senza privilegi;
- **0 fallimenti**;
- benchmark sintetico di regressione: **35/35**;
- OCR reale con Tesseract: **7/7**;
- rotazioni 0°, 90°, 180° e 270° verificate;
- nessun residuo temporaneo finale nel runner OCR;
- prova manuale offline dei tre esiti `DOCUMENT_MATCH`, `FAMILY_MATCH` e `NO_MATCH`.

Questa validazione protegge le regressioni note. **Non è un benchmark indipendente dell'accuratezza generale sui documenti reali e non certifica BurOCRazia per l'uso in produzione con dati sensibili.**

Dettagli: [docs/VALIDAZIONE.md](docs/VALIDAZIONE.md).

## Benchmark

Candidata Round 6 **NOT READY**, software pubblico 0.6.1. Catalogo: 1.216 identità reali, 1.212 operative, zero nuove identità nel Round 6. Copertura firme: 948/1212 (78.22%); canonical 987/987; robustness 150/192. Gate, denominatori e limiti in [BENCHMARK.md](docs/BENCHMARK.md) e [ROUND6_REPORT.md](docs/ROUND6_REPORT.md). CI esterna non eseguita.

## Test

```bash
python -m pytest -q
python scripts/verify_catalog.py
python scripts/catalog_status.py
python scripts/benchmark.py --output benchmark-results.json
```

La CI in `.github/workflows/tests.yml` esegue i controlli su Linux, Windows e macOS con Python 3.12.

## Struttura del repository

```text
BurOCRazia/
├── app.py                  # interfaccia Streamlit
├── run.py                  # launcher locale
├── src/                    # logica applicativa
├── tests/                  # suite automatica e regressioni
├── data/                   # snapshot e manifest del catalogo
├── examples/               # esempi sintetici
├── scripts/                # strumenti locali
├── docs/                   # documentazione tecnica
└── .github/workflows/      # CI
```

## Principi del progetto

1. Un `NO_MATCH` corretto è preferibile a un falso positivo.
2. Documento, ente e annualità devono essere sostenuti da evidenze sufficienti.
3. Provenienza ufficiale e revisione editoriale sono concetti distinti.
4. Una spiegazione non revisionata non viene presentata come validata.
5. Un documento rifiutato resta nello storico ma viene escluso dal riconoscimento operativo.
6. I campi mancanti non vengono completati per supposizione.
7. L'espansione del catalogo non deve ridurre le protezioni contro riconoscimenti errati.
8. Le funzioni online non fanno parte del normale runtime locale.

## Limiti attuali

- la copertura non rappresenta l'intera burocrazia italiana;
- i 1216 record reali richiedono ancora revisione editoriale;
- le 3 spiegazioni incluse non sono ancora validate;
- non sono incluse copie locali dei documenti ufficiali;
- il catalogo può diventare obsoleto perché BurOCRazia non controlla aggiornamenti online;
- fotografie sfocate, ritagliate o con OCR insufficiente possono produrre `NO_MATCH`;
- il sistema non sostituisce la lettura del documento originale né le informazioni dell'ente competente;
- la release non è certificata per l'uso con documenti personali o sensibili in ambienti di produzione.

## Contribuire

Prima di proporre una modifica:

```bash
python -m pytest -q
python scripts/benchmark.py --output benchmark-results.json
```

Le modifiche al riconoscimento devono mantenere il comportamento prudente del sistema e non ridurre artificialmente i `NO_MATCH` aumentando i falsi positivi.

Le indicazioni operative per gli agenti e i contributori sono in [AGENTS.md](AGENTS.md).

## License

BurOCRazia è creato da Luca Lullo e distribuito con licenza [MIT](LICENSE).

Per i dati del catalogo e i materiali di terze parti, consulta [DATA_NOTICE.md](DATA_NOTICE.md).

## Author

Creato da [Luca Lullo](https://github.com/lucalullo).

## Round 7 — NOT READY

Decision policy v3, retrieval v2 e nuova evaluation dopo freeze: 372 tentativi, 331 rappresentazioni generate su 42 identità, 280 scan-like, 9/50 AcroForm generati (41 fallimenti). Copertura 77.64% totale e 81.26% con file; canonical 979/979; richiamo robustness 49.19%, scansioni 47.86%, compilati 14.00% sul piano completo. Rifiuto unknown storico 100.00%; famiglie 0/16 valutabili, capacità non sufficientemente validata. p95 444.65 ms; indice 39832045 byte. Precisione exact 100% sui match emessi. La QA dei compilati mostra errori semantici e testo tagliato: nessuna validità amministrativa o qualità finale dei moduli rivendicata.

R6 ora development; v3 una sola esecuzione, senza retuning. 690 test passati, 3 saltati. CI esterna pending_external_gate. Software 0.6.1, schema 610 e catalogo di 1216 documenti preservati. Report e limiti: [ROUND7_REPORT.md](docs/ROUND7_REPORT.md).
