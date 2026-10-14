# BurOCRazia v0.7.0-rc1

## Highlights

Release candidate pre-1.0 per il riconoscimento prudente e deterministico di documenti amministrativi italiani. Runtime locale su loopback con `python run.py`, nessun LLM, API cloud o telemetria applicativa. PDF, DOCX, TXT e immagini; OCR locale Tesseract quando necessario.

Il catalogo completo conserva 1.216 documenti reali, 19 fonti, 16 famiglie, identificativi e provenienze. La copertura delle identità con file è 1.002/1.158 (86,53%): riguarda le firme disponibili, non l'intera amministrazione italiana. Fingerprint locali, confronto per pagina e decision policy v7 migliorano la robustezza su scansioni e moduli compilati rispetto al precedente percorso pubblico. Il Round 23 conserva esattamente il motore congelato e misurato nel Round 22.

## RC benchmark

Prove locali Round 22 su Windows/Python 3.12, con OCR Tesseract reale su trasformazioni sintetiche di template ufficiali. Sono risultati sperimentali, non certificazioni o garanzie di accuratezza su documenti futuri.

| Prova | Risultato |
| --- | ---: |
| V6 indipendente, singola esecuzione | 560/597 exact, 40 identità, 8 fonti |
| Precisione exact / recall exact | 100% / 93,80% |
| Scan recall | 392/420 (93,33%) |
| Generazione compilati | 100/100 (40 AcroForm, 60 overlay statici) |
| Filled recall | 95/100 (95%) |
| Errori ente / versione | 0 / 0 |
| Retrieval @1 / @25 | 99,33% / 100% |
| Unknown v4, singola esecuzione Round 21 | 120/120 rifiuti corretti, 15 fonti |
| Canonical | 1007/1007 |
| Safety | 705 negativi confermati, 0 false accept |
| Warm recognition: mediana di sette p95 | 186,09 ms |
| Suite Round 22 | 889 pass, 0 fail, 3 skip Windows |

V5 originale rimane evidenza indipendente storica del vecchio motore. I successivi replay V5 sono development contaminato dal tuning e non costituiscono una nuova prova indipendente. V6 e unknown v4 non sono rieseguiti nel Round 23. Le osservazioni originali e gli hash sono conservati. I 15 mismatch delle etichette storiche non vengono eliminati: il gate tecnico versionato distingue quelle ambiguità dai 705 negativi confermati. Denominatori, intervalli nominali, protocolli e limiti in [BENCHMARK.md](BENCHMARK.md) e [ROUND22_REPORT.md](ROUND22_REPORT.md).

## Safety and limitations

RC pre-1.0, senza consulenza legale o personalizzata, non certificata per produzione con dati sensibili. Un confidence score non è una probabilità. Family matching è sperimentale e insufficientemente validato. Catalogo e schede editoriali non risultano automaticamente verificati; i documenti ufficiali possono cambiare.

OCR e riconoscimento dipendono da Tesseract, lingue installate, qualità, ritaglio e leggibilità dell'input. I benchmark sintetici non equivalgono a scansioni reali raccolte sul campo. Gli overlay compilati sono fixture sperimentali, senza validità amministrativa. Limiti parser, ZIP, pagine, pixel, testo e tempo restano attivi; dati e pacchetti sono inerti nell'interfaccia. Nessun documento personale viene incluso nel repository, nelle cache di riconoscimento o in questa release.

## Upgrade notes

La stable pubblica `v0.6.1` resta disponibile e non viene sostituita. Questa versione è una **pre-release `v0.7.0-rc1`**, mai `v0.7.0` stable. Schema SQLite invariato a 610; migrazioni idempotenti verificate su copia. Conservare un backup privato del database locale prima di aggiornare; non sostituire un database editoriale con lo snapshot pubblico. Installazione e avvio nei [README](../README.md) e [README EN](../README_EN.md).

Gli archivi sorgente GitHub sono sufficienti: nessun corpus ufficiale scaricato o grande asset manuale è allegato. Il ZIP Round 22 resta evidenza locale, SHA256 `bc9e3aa49b1c05b2a773f4c605e1b79569ec21a0339fab6adef42dac8de27f26`.

## License

Creato da Luca Lullo, software sotto licenza [MIT](../LICENSE). Per dati e materiali di terze parti vedere [DATA_NOTICE.md](../DATA_NOTICE.md); la licenza software non attribuisce diritti sui documenti ufficiali.
