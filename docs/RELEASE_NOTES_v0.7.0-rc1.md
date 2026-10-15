# BurOCRazia 0.7.0-rc1

Release candidate pre-1.0 per il riconoscimento prudente di documenti amministrativi italiani. La stable pubblica resta v0.6.1; questa candidata non è una release stable.

## Novità

- catalogo completo di 1216 documenti reali, 12 enti, 19 fonti e 16 famiglie, con identificativi e provenienze;
- fingerprint deterministici locali, confronto per pagina e decision policy v7;
- migliorata robustezza su scansioni e moduli compilati, con truth/contamination policy e prove indipendenti distinte dai replay di sviluppo;
- PDF, DOCX, TXT e immagini, OCR Tesseract locale e SQLite; nessun LLM, cloud API o telemetria nel normale runtime su loopback.

## Benchmark RC

Prove locali Windows / Python3.12 su template ufficiali e trasformazioni sintetiche con OCR reale.

| Prova | Risultato |
| --- | ---: |
| V6 indipendente | 560/597 exact; precisione100%, recall93,80% |
| Scan recall / filled recall | 93,33% / 95% |
| Generazione compilati | 100/100 |
| Retrieval@1 / @25 | 99,33% / 100% |
| Unknown v4 single-shot | 120/120 rifiuti corretti |
| Errori ente / versione | 0 / 0 |
| Canonical / safety | 1007/1007; 705 negativi, 0 false accept |
| Copertura identità con file | 1002/1158 (86,53%) |
| Mediana di sette p95 warm | 186,09ms |
| Suite RC di riferimento | 889 pass, 0 fail, 3 skip |

V5 originale è evidenza storica indipendente del vecchio motore; i replay successivi sono development/tuning. V6 e unknown v4 non vengono ripetuti. Protocolli e denominatori in [BENCHMARK.md](BENCHMARK.md).

## Limiti e aggiornamento

Benchmark locali, non certificazione né consulenza legale o personalizzata. RC non certificata per produzione con dati sensibili. Family matching sperimentale e insufficientemente validato; catalogo e schede non risultano automaticamente verificati. I documenti ufficiali possono evolvere e l'OCR dipende da Tesseract e qualità dell'input. Le trasformazioni sintetiche non equivalgono a scansioni raccolte sul campo; i compilati benchmark non hanno validità amministrativa.

Schema SQLite610 invariato, con migrazioni idempotenti verificate su copia. Conservare un backup privato del database operativo prima dell'aggiornamento e non sostituire i dati editoriali con il seed pubblico. Installazione, limiti e privacy nei [README italiano](../README.md) e [README inglese](../README_EN.md).

## Licenza

Creato da Luca Lullo, software MIT: [LICENSE](../LICENSE). Dati e materiali di terze parti conservano le proprie condizioni: [DATA_NOTICE.md](../DATA_NOTICE.md). Nessun documento personale o corpus ufficiale scaricato è distribuito con la candidata.
