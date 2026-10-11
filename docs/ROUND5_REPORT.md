# Round 5 — NOT READY

Software **0.6.1**, target 0.7.0, schema **610**, branch `codex/coverage-benchmark-v0.7.0`. Commit di riferimento al momento delle misure `f9e1fa06821907da53f75417555bd3cbdd50c7d0`; il commit locale finale include gli stessi sorgenti, identificati dai digest sotto. Nessun push, tag o release. CI esterna `pending_external_gate`.

## 1. Catalog coverage

1.216 record reali, 1.212 operativi, quattro rifiutati, 1.216 provenance; nessuna nuova fonte o identità. Snapshot invariato; integrità/FK verificati. Copertura sintetica dei metadati: {'documents_tested': 1212, 'exact': 1169, 'family_fallback': 0, 'no_match': 43, 'wrong_identity': 0, 'entity_errors': 0, 'version_errors': 0}. Non è riconoscimento di file reali.

## 2. Fingerprint coverage

Canonici disponibili 409; firme attive 369/1212 (30.45%). Target70%, preferito85%: fallito. Provenienza effettiva per ogni firma, nessun file ufficiale distribuito.

| Fonte | Operativi | Canonici | Firme | Bloccati | Senza download | Acquisizione fallita | Ambigui |
|---|---:|---:|---:|---:|---:|---:|---:|
| inps | 359 | 0 | 0 | 0 | 0 | 359 | 0 |
| inail | 347 | 121 | 119 | 0 | 0 | 228 | 0 |
| ade | 122 | 0 | 0 | 90 | 32 | 0 | 0 |
| lavoro | 102 | 91 | 72 | 0 | 0 | 28 | 2 |
| giustizia | 142 | 110 | 100 | 0 | 0 | 40 | 2 |
| inl | 46 | 44 | 44 | 0 | 1 | 1 | 0 |
| mimit | 42 | 32 | 24 | 0 | 0 | 16 | 2 |
| garante_privacy | 17 | 0 | 0 | 0 | 8 | 9 | 0 |
| mef | 15 | 1 | 1 | 0 | 14 | 0 | 0 |
| funzione_pubblica | 9 | 9 | 8 | 0 | 0 | 1 | 0 |
| anac | 7 | 1 | 1 | 0 | 0 | 6 | 0 |
| unioncamere | 4 | 0 | 0 | 0 | 0 | 4 | 0 |

L’acquisizione ha riutilizzato la cache verificata e fatto 138 richieste nella prima sessione opt-in. Le ricostruzioni successive sono offline. ADE: diniego403; INPS/Garante: risposte200 non documentali; diverse fonti sono state fermate dopo tre risposte non documentali. Questa chiusura prudenziale è un limite del runner: non prova che ogni percorso successivo sia inaccessibile. I percorsi non richiesti sono riportati come acquisizione fallita, non come diniego dell’host. Nessun aggiramento. DOCX con estensione dichiarata ma contenuto legacy non valido, conflitti di emittente e allegati condivisi restano esclusi.

## 3. Canonical exact-file recognition

N=369; esatti 362, famiglie 0, rifiuti 7, errati 0; precisione 100.00% (362/362); recall exact 98.10% (362/369); utile 98.10% (362/369).

## 4. Robustness recognition

N=196; esatti 48, famiglie 0, rifiuti 148, errati 0; precisione 100.00% (48/48); recall exact 24.49% (48/196); utile 24.49% (48/196).

## 5. Filled-form robustness

N=14; esatti 10, famiglie 0, rifiuti 4, errati 0; precisione 100.00% (10/10); recall exact 71.43% (10/14); utile 71.43% (10/14).

Canonici: SHA riconosciuti 362/369; 7 rifiuti per vincoli su annualità/revisioni, sottotipo o interpretazione dell’emittente. Nessun errore di estrazione nel run finale. Sono identità note dal canonico, non generalizzazione indipendente.

Moduli compilati: 4 casi AcroForm completati e verificati; 2 fallimenti di generazione inclusi come rifiuti. Gli altri sono overlay di dati fittizi nel margine, prova più debole della compilazione dei campi. Un’ulteriore fixture PDF AcroForm sintetica prova nomi/data/indirizzo/importo reali nei widget, riapertura dei valori e matching del contenuto, in CI. Nessun dato personale reale.

## 6. Scan/OCR robustness

Due PDF disponibili per fonte, dove possibile; 14 identità, prima pagina, 14 trasformazioni: raster150/200DPI, grigio, JPEG60/75/90, blur, contrasto, crop1%, rotazioni90/180/270, resize down/up e prima pagina digitale. Seed20261011; selezione SHA(document_id) dentro fonte prima dei risultati. Trasformazioni dopo il canonico, holdout di rappresentazioni. Nessuna trasformazione scansione DOCX.

| Trasformazione | N | Exact | P | R exact | Utile |
|---|---:|---:|---|---|---|
| raster_150 | 14 | 3 | 100.00% (3/3) | 21.43% (3/14) | 21.43% (3/14) |
| raster_200 | 14 | 3 | 100.00% (3/3) | 21.43% (3/14) | 21.43% (3/14) |
| grayscale | 14 | 3 | 100.00% (3/3) | 21.43% (3/14) | 21.43% (3/14) |
| jpeg_60 | 14 | 3 | 100.00% (3/3) | 21.43% (3/14) | 21.43% (3/14) |
| jpeg_75 | 14 | 3 | 100.00% (3/3) | 21.43% (3/14) | 21.43% (3/14) |
| jpeg_90 | 14 | 4 | 100.00% (4/4) | 28.57% (4/14) | 28.57% (4/14) |
| blur | 14 | 4 | 100.00% (4/4) | 28.57% (4/14) | 28.57% (4/14) |
| low_contrast | 14 | 3 | 100.00% (3/3) | 21.43% (3/14) | 21.43% (3/14) |
| crop_margins | 14 | 3 | 100.00% (3/3) | 21.43% (3/14) | 21.43% (3/14) |
| rotate_90 | 14 | 3 | 100.00% (3/3) | 21.43% (3/14) | 21.43% (3/14) |
| rotate_180 | 14 | 3 | 100.00% (3/3) | 21.43% (3/14) | 21.43% (3/14) |
| rotate_270 | 14 | 3 | 100.00% (3/3) | 21.43% (3/14) | 21.43% (3/14) |
| resize_down_up | 14 | 3 | 100.00% (3/3) | 21.43% (3/14) | 21.43% (3/14) |
| first_page_only | 14 | 7 | 100.00% (7/7) | 50.00% (7/14) | 50.00% (7/14) |

OCR condizionato: 22.53% (41/182) exact. Errori di estrazione esclusi solo da questa tabella condizionata, sempre inclusi nel risultato end-to-end. OCR reale legacy7/7 e raster sintetico v2 14/14 restano separati. Scansioni sparse, ordine dei campi, testi brevi e versioni non leggibili limitano ancora v1; nessuna accuracy OCR annotata sul testo ufficiale è stata inventata.

## 7. Family identity-holdout

Famiglie testate 1, valutabili con ≥3 held-out 0; identità sviluppo 0, held-out 1. P/R/F1: n.d. / 0.00% (0/1) / 0.00% (0/1); macro {'family_precision': None, 'family_recall': 0.0, 'family_f1': 0.0}.

Pattern verificati preesistenti invariati, nessun pattern nuovo costruito sulle identità held-out; SHA condivisi indivisibili e percorso exact disattivato. Split retrospettivo su file già osservati, insufficiente per generalizzazione prospettica. Target cinque famiglie non raggiunto: mancano identità/file ufficiali pertinenti. Nessuna famiglia inventata o aggiunta. Sintetici v3 161/161, macro100%, zero false accettazioni sugli81 negativi; v1/v2 storici160/161 restano invariati.

## 8. Unknown official rejection

137 hash ufficiali distinti fuori dagli ambiti supportati, 137 rifiuti corretti, 0 false accettazioni; 2 fallimenti di estrazione inclusi. 100.00% (137/137). Campione storico, non nuovi sconosciuti indipendenti.

## 9. Historical regressions

Cinque errori v1 tutti corretti o rifiutati; R061 NO_MATCH; regressione35/35, lockedv2 69/69, hard negatives30/30+100/100. Lockedv1 59/69 conserva le etichette storiche incompatibili. Corpus v1/v2 e holdout Round3/4 non modificati; i loro risultati originali rimangono distinguibili. Il primo benchmark di rappresentazioni aveva48 exact e2 errati: il fallback metadati confondeva vendita/acquisto, con un riferimento nel corpo che annullava il sottotipo dell’intestazione. Il correttivo generale dà precedenza al qualificatore dell’intestazione rispetto ai riferimenti nel corpo; due test simmetrici lo coprono. Risultati precedenti conservati in before_transaction_fix, senza cambio di soglie. Gli artefatti iniziali con OCR impedito dal sandbox e l’esecuzione interrotta non vengono usati come misura finale. Le etichette ausiliarie ente/versione dei primi casi noti sono aggiunte dal medesimo document ID del catalogo, senza cambiare identità o osservazioni.

## 10. Performance

Confronto alternato con motore Round4 `f9e1fa06821907da53f75417555bd3cbdd50c7d0`, stesso catalogo, 35 input sintetici, 210 campioni/motore. Round4 p50/p95 81.7499/110.7892ms; candidato 91.2146/128.1624ms; rapporti {'p50': 1.115776288411362, 'p95': 1.1568131189682749}. Catalog load 8.40ms, index build inclusa lettura fingerprint 747.42ms. Estrazione/OCR esclusi dalla warm inference e misurati separatamente nei raw.

## 11. Memory

Fingerprint {'disk_bytes': 12188225, 'index_bytes': 28676242, 'records': 369, 'average_disk_bytes_per_document': 33030.42005420054, 'average_index_bytes_per_document': 77713.39295392953, 'projected_index_bytes_for_1200': 93256071.54471545, 'memory_scope': 'Recursive Python size of canonical signature records and tuple posting lists; process RSS reported separately.'}. RSS candidato prima/dopo warm 30318592/77123584byte, crescita su8 ripetizioni 569344byte. Scope: dimensione ricorsiva Python separata dal working set del processo, non attribuzione perfetta delle allocazioni native. Posting list in tuple riducono overhead.

## Test e CI

Suite completa: 615 passed, 3 skipped, zero failed, 600.83s. Include730/CU quasi identici, widget PDF compilati e qualificatori vendita/acquisto. Dopo il refresh dei risultati statici e dell’aspettativa UI sulle categorie Round5, controlli UI21/21. Tre skip Windows symlink/FIFO. Windows Python 3.12.10. Non è un collaudo su tre piattaforme. CI normale include schema fingerprint e fixture sintetiche, senza cache ufficiale; esecuzioni equivalenti locali registrate, CI esterna pending.

## Gate

| Gate | Obiettivo | Risultato | Esito |
|---|---|---|---|
| catalog_provenance | 1216/1216; unchanged snapshot | 1212 | PASS |
| fingerprint_coverage | >=70% | 0.30445544554455445 | FAIL |
| canonical_precision | 100% | 1.0 | PASS |
| canonical_recall | >=99% | 0.981029810298103 | FAIL |
| robustness_precision | >=99.5% | 1.0 | PASS |
| robustness_exact_recall | >=90% | 0.24489795918367346 | FAIL |
| degraded_scans_useful_when_family_relevant | >=95%; N/A if no labelled pertinent family | {'value': None, 'cases': 0} | PASS |
| family_evaluable_sample | >=5 families, >=3 held out identities when possible | 0 | FAIL |
| family_precision | >=99% | None | FAIL |
| family_macro_precision | >=99% | None | FAIL |
| family_recall | >=80% | 0.0 | FAIL |
| family_hard_negatives | 0 false accepts | 0 | PASS |
| unknown_rejection | >=99%, target100% | 1.0 | PASS |
| historical_five | 5 safe | 5 | PASS |
| R061 | NO_MATCH | NO_MATCH | PASS |
| historical_hard_negatives | 130/130 | 130 | PASS |
| entity_errors | 0 | 0 | PASS |
| version_errors | 0 | 0 | PASS |
| real_ocr | 7/7 and14/14 | {'legacy': 7, 'v2': 14} | PASS |
| performance | p50/p95 <=1.5x paired Round4; preferred p95<=150ms | {'p50': 1.115776288411362, 'p95': 1.1568131189682749} | PASS |
| fingerprint_memory | <=100MiB index for1200 projected | {'disk_bytes': 12188225, 'index_bytes': 28676242, 'records': 369, 'average_disk_bytes_per_document': 33030.42005420054, 'average_index_bytes_per_document': 77713.39295392953, 'projected_index_bytes_for_1200': 93256071.54471545, 'memory_scope': 'Recursive Python size of canonical signature records and tuple posting lists; process RSS reported separately.'} | PASS |
| tests | 0 failed | 615 | PASS |

## Riproducibilità e archivio

Runtime SHA `75534cbc873074122cfec958847f8648fc728e6a5b5caba362df5e522a181f12`; codice/bundle SHA `8b93a7d9eb5909c74bc111541cc9985589194d70a1391d594647969ff946240e`; fingerprint SHA `56279630f94c5a5e7457e082e5c238a9b9c38ca8be64c5e42f2f6d27214117a2`. Raw: `benchmarks/results/round5/`. Parametri e comandi: `docs/FINGERPRINTS.md`, `scripts/round5_full.ps1`.

Archivio locale: `dist/BurOCRazia-v0.7.0-candidate-NOT-READY-round5.zip`. SHA-256 e commit finale in `dist/package-verification.json` e file `.zip.sha256`, generati dopo il commit. Non si incorpora l’hash dello ZIP nel suo stesso contenuto.
