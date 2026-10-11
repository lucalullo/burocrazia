# Validazione BurOCRazia 0.6.1

## Candidata successiva — 11 ottobre 2026

I risultati correnti sono generati in [BENCHMARK.md](BENCHMARK.md), `validation_latest.json`, `catalog_verification.json` e `release_gates.json`. La baseline locale è 453 passati/3 skip e regressione 35/35. La suite corrente aggiunge policy di acquisizione, paginazione incoerente, continuità di tutte le righe, cache differenziale e riferimenti privacy. L'OCR reale non è eseguibile qui perché Tesseract non è disponibile; il 7/7 riportato nelle sezioni successive è storico. La candidata non è pronta: il corpus locked mantiene i propri fallimenti e la CI remota Linux/macOS/Windows non è stata eseguita. Nessuna nuova verifica editoriale umana.

Le sezioni seguenti conservano la validazione storica 0.6.1, senza attribuirla alla candidata.

Questa pagina riassume i controlli finali eseguiti sulla candidata Windows prima della rifinitura dell'interfaccia e del repository.

## Ambiente Windows

- Windows 11
- Python 3.12.10
- Tesseract 5.5.3.20260724
- lingue rilevate: `eng`, `ita`, `ita_old`, `osd`

## Suite automatica

Esecuzione con directory temporanea dedicata al progetto:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --tb=short --color=no --basetemp=.\.pytest_tmp_nuovo_01
```

Risultato:

- **453 passed**
- **3 skipped**
- **0 failed**

I tre skip riguardano la creazione di symlink senza il privilegio Windows necessario e due controlli FIFO non disponibili sulla piattaforma. Non sono fallimenti applicativi.

## OCR reale

Runner con Tesseract reale e file sintetici:

- scansione 0°: pass
- scansione 90°: pass
- scansione 180°: pass
- scansione 270°: pass
- timeout nativo: pass
- PDF vuoto: pass
- PDF digitale senza OCR: pass
- residui temporanei finali: **0**

Gate OCR: **7/7**, `full_gate_passed = true`.

## Browser offline

Con Internet disattivato, l'applicazione è stata aperta su `127.0.0.1` e sono stati provati i tre esempi sintetici inclusi:

- SR211 INPS → `DOCUMENT_MATCH`
- Modello 730/2024 → `FAMILY_MATCH`
- testo non amministrativo → `NO_MATCH`

Il collaudo non costituisce un benchmark indipendente su documenti reali e non certifica il software per dati personali o sensibili.

## Dopo la rifinitura GitHub

La rifinitura successiva modifica esclusivamente presentazione, documentazione e pulizia del repository. Il motore di riconoscimento, l'OCR, il catalogo, il database e le regole A01–A05 non vengono intenzionalmente modificati.

Prima del tag pubblico è comunque consigliato un ultimo smoke test dell'interfaccia rifinita, in particolare del selettore Chiaro/Scuro.
