# Estrazione e OCR locale

Verifica del 5 settembre 2026. L'estrazione precede il riconoscimento: un file non leggibile o oltre i limiti produce `ExtractionError`, mai un risultato `NO_MATCH` inventato. I file caricati non vengono salvati nel catalogo. Il codice non effettua richieste di rete.

## Limiti applicati

| Risorsa | Limite effettivo |
| --- | --- |
| File caricato, ogni formato | 20 MiB; gli stream vengono letti al massimo per 20 MiB + 1 byte |
| PDF | 100 pagine; rifiuto oltre la soglia |
| OCR dei PDF | Solo pagine prive di testo, tra le prime 5 pagine |
| Testo estratto | 1.000.000 di caratteri prima della normalizzazione |
| Immagine caricata | 50.000.000 di pixel; JPEG e PNG |
| Immagine elaborata dall'OCR | Ridotta a massimo 16.000.000 di pixel |
| Rendering pagina PDF | Massimo 16.000.000 di pixel e 32.768 pixel per lato; scala massima 2× |
| Archivio DOCX | 2.000 membri, 50 MiB decompressi complessivi, 10 MiB per membro |
| Compressione DOCX | Rapporto massimo 200:1 per membro |
| XML nel DOCX | 200.000 elementi complessivi; DTD ed entità dichiarate rifiutati |
| Singolo comando OCR | 20 secondi |
| Ricerca lingue e orientamento OSD | Massimo 5 secondi per comando, ridotto al budget residuo |
| OCR immagine, tentativi di orientamento compresi | Budget condiviso 60 secondi, ridotto al tempo residuo del PDF se presente |
| Estrazione PDF/DOCX | Budget cooperativo 120 secondi, controllato tra pagine/membri/paragrafi |
| Uscite native OCR TXT/TSV | Massimo 4.000.000 byte per file prima della lettura |

Le soglie sono prudenziali, non un dimensionamento certificato su tutti i sistemi. Non sono limiti rigidi di memoria RAM. `MAX_*` e i timeout sono dichiarati in `src/extract.py` e `src/ocr.py`.

## Comportamenti verificati

- Estensione, firma binaria e formato interno sono confrontati; il MIME, quando fornito dall'interfaccia, deve essere coerente. `application/octet-stream` è ammesso come valore generico: la firma interna resta obbligatoria.
- PDF protetti da password, documenti corrotti e formati camuffati ricevono errori comprensibili.
- I PDF misti vengono elaborati in ordine di pagina: testo digitale dove presente, OCR nelle pagine senza testo entro la copertura indicata. `total_pages`, `pages_processed`, `ocr_pages` e `warning` permettono all'interfaccia di dichiarare cosa è stato letto. Le pagine testuali oltre la quinta continuano a essere lette. Le scansioni oltre la quinta sono escluse con avviso.
- Se l'OCR manca in un PDF misto, il testo digitale resta disponibile con avviso e numeri delle pagine non acquisite. Un timeout produce invece un errore di estrazione.
- Nei DOCX vengono letti paragrafi e celle delle tabelle, anche annidate, nell'ordine del corpo. L'archivio viene verificato in memoria senza estrarlo sul disco: CRC, dimensioni, nomi duplicati, percorsi sospetti e dichiarazioni XML pericolose vengono rifiutati.
- L'OCR conserva EXIF, scala di grigi, contrasto e rotazioni multiple. Dalla v0.6.1 anche le pagine PDF rasterizzate attivano `auto_orient=True` nello stesso motore delle immagini. Il backend locale sceglie l'orientamento usando le confidenze Tesseract TSV; il conteggio del testo resta un criterio secondario deterministico. Ricerca lingue, OSD e rotazioni condividono la scadenza residua: ogni rotazione non riavvia il budget.
- I comandi Tesseract usano `subprocess.run` con timeout esplicito, senza shell. Ogni operazione su immagini ha una `TemporaryDirectory` privata, rimossa anche su errore, timeout e interruzione Python. Le immagini Pillow vengono chiuse al termine. Le lingue vengono cercate con timeout: la funzione originale `pytesseract.get_languages` non lo espone. Il percorso configurabile `BUROCRAZIA_TESSERACT_CMD` resta disponibile.

## Evidenze riproducibili

```bash
python -m pytest tests/test_extract.py tests/test_ocr.py tests/test_extraction_safety.py tests/test_v061_pdf_ocr.py -q
```

I test usano file sintetici e includono subprocess reali fittizi per verificare timeout e pulizia. Non richiedono servizi remoti o dati personali. Il test UI sul vecchio oggetto Streamlit simulato è sostituito dai controlli dell'interfaccia in `tests/test_offline_ui.py`.

Smoke test locale su Linux x86_64, Python 3.12.13 e Tesseract 5.3.4: immagine sintetica 1400×360, due righe «INPS SR211 RINUNCIA DEI BENEFICIARI / ALLA CARTA ACQUISTI». Testo letto correttamente e rotazione 0°, circa 3,4 secondi incluso il confronto degli orientamenti. In questo ambiente è disponibile solo la lingua `eng`, quindi l'avviso di fallback dall'italiano è atteso. La prova non certifica qualità OCR generale o supporto a tutte le piattaforme.

I test v0.6.1 distinguono simulazioni (parametro, quattro orientamenti, scadenze, chiusura immagini e temporanei) da scansioni PDF sintetiche elaborate con Tesseract reale. Il collaudo Windows ha superato 7/7 casi con zero residui temporanei finali; ambiente e limiti sono riepilogati in [VALIDAZIONE.md](VALIDAZIONE.md), senza estendere il risultato alla qualità generale dell'OCR.

## Limiti residui dichiarati

- Il budget 120 secondi è cooperativo: una singola chiamata nativa PDF/XML può terminare dopo la soglia. Non esiste ancora isolamento dell'intero parser in un processo con quote di CPU/RAM. Anche il controllo del testo avviene dopo l'estrazione nativa della singola pagina.
- Una pagina con testo digitale e un'immagine contenente altro testo viene trattata come testuale; non viene eseguito OCR selettivo delle sole aree immagine. Le prime cinque pagine senza testo possono includere pagine realmente vuote.
- DOCX: non vengono letti con OCR immagini incorporate, intestazioni/piè di pagina, caselle di testo fuori dal corpo, note o contenuti di allegati. Le tabelle diventano righe di testo e non mantengono una struttura tabellare nell'esito.
- L'OCR può leggere male numeri, codici e annualità. La confidenza non equivale a correttezza; il riconoscimento deve continuare a rifiutare casi ambigui.
- La directory privata riduce l'esposizione dei temporanei; non garantisce cancellazione forense, protezione da un sistema compromesso o pulizia dopo arresto forzato dell'intero processo/sistema. L'assenza di residui in RAM, swap e backup non è promessa.
- Il motore Tesseract e i pacchetti lingua devono già essere presenti sul dispositivo. Il codice non li scarica.
