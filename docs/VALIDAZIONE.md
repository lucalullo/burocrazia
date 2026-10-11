# Validazione BurOCRazia 0.6.1

## Candidata Round 2 — 11 ottobre 2026

Risultati correnti in `BENCHMARK.md`, `validation_latest.json` e `release_gates.json`: 515 test superati, tre skip Windows, zero fallimenti. Tesseract reale disponibile localmente: 7/7 legacy e 14/14 sintetici; nessun mock conteggiato come prova reale. Catalogo schema 610, 1.216 record reali conservati, 1.212 operativi. La candidata resta NOT READY per v1, basso recall reale e CI esterna non eseguita. Le sezioni successive conservano la storia 0.6.1.

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
