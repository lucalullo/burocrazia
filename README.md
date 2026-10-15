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

- riconoscimento locale di documenti amministrativi con fingerprint deterministici e confronto per pagina;
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

## Cosa contiene la v0.7.0-rc1

Lo snapshot distribuito con questa release candidate contiene:

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

I 1216 record reali sono presenti nel catalogo, ma non risultano automaticamente revisionati manualmente. Le 3 schede esplicative incluse sono ancora in stato di verifica. I 4 record rifiutati conservano lo storico e sono esclusi dal matching operativo: i record reali operativi sono 1212.

**Questi numeri descrivono il catalogo, non garantiscono che ogni possibile file venga riconosciuto.** Il risultato dipende dalla qualità del testo estratto e dalla presenza di evidenze sufficienti.

Gli enti attualmente rappresentati dai record reali sono:

- INPS;
- INAIL;
- Agenzia delle Entrate;
- Ministero del Lavoro;
- Ispettorato Nazionale del Lavoro;
- Garante per la protezione dei dati personali;
- MIMIT;
- Dipartimento della Funzione Pubblica;
- Tribunale di Venezia;
- MEF/RGS;
- ANAC;
- Unioncamere.

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
- **Revisione editoriale** - strumenti per la manutenzione dei contenuti;
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

La candidata **0.7.0-rc1** è pre-1.0, usa lo schema SQLite **610** e conserva la stable pubblica **v0.6.1**. La validazione locale RC su Windows / Python 3.12 ha registrato:

| Prova | Risultato |
| --- | ---: |
| V6 indipendente, singola esecuzione | 560/597 exact, 40 identità, 8 fonti |
| Precisione exact / recall exact | 100% / 93,80% |
| Scan recall | 392/420 (93,33%) |
| Generazione compilati / filled recall | 100/100 / 95% |
| Retrieval @1 / @25 | 99,33% / 100% |
| Unknown v4, singola esecuzione | 120/120 rifiuti corretti, 15 fonti |
| Errori ente / versione | 0 / 0 |
| Canonical | 1007/1007 |
| Safety | 705 negativi confermati, 0 false accept |
| Copertura delle identità con file | 1002/1158 (86,53%) |
| Warm recognition: mediana di sette p95 | 186,09 ms |
| Suite automatica RC di riferimento | 889 superati, 0 fallimenti, 3 saltati |

V6 misura trasformazioni sintetiche di template ufficiali con OCR Tesseract reale; non equivale a scansioni raccolte sul campo. Il p95 riguarda il solo riconoscimento warm, esclusi estrazione e OCR. V5 originale rimane benchmark indipendente storico del vecchio motore; i replay successivi sono development/tuning. V6 e unknown v4 restano congelati senza nuove esecuzioni. Family matching è sperimentale e insufficientemente validato.

Protocolli, denominatori e limiti in [docs/BENCHMARK.md](docs/BENCHMARK.md); novità e aggiornamento nelle [release notes](docs/RELEASE_NOTES_v0.7.0-rc1.md). Queste prove locali non certificano l'accuratezza generale o l'uso con dati sensibili, non forniscono consulenza legale o personalizzata. I documenti ufficiali possono evolvere e l'OCR dipende da Tesseract e dalla qualità dell'input.

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

## Test

```bash
python -m pip install -r benchmarks/requirements-round6.txt
python -m pytest -q
python scripts/verify_catalog.py
python scripts/catalog_status.py
python scripts/benchmark.py --corpus tests/fixtures/benchmark_v2.json --output benchmark-results.json
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
- il riconoscimento per famiglie è sperimentale e insufficientemente validato;
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
python -m pip install -r benchmarks/requirements-round6.txt
python -m pytest -q
python scripts/benchmark.py --corpus tests/fixtures/benchmark_v2.json --output benchmark-results.json
```

Le modifiche al riconoscimento devono mantenere il comportamento prudente del sistema e non ridurre artificialmente i `NO_MATCH` aumentando i falsi positivi.

Le indicazioni operative per gli agenti e i contributori sono in [AGENTS.md](AGENTS.md).

## License

BurOCRazia è creato da Luca Lullo e distribuito con licenza [MIT](LICENSE).

Per i dati del catalogo e i materiali di terze parti, consulta [DATA_NOTICE.md](DATA_NOTICE.md).

## Author

Creato da [Luca Lullo](https://github.com/lucalullo).
