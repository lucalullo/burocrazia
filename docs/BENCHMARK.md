# Benchmark — Round 3

Stato: **NOT_READY**. Software **0.6.1**, obiettivo 0.7.0. Nessun push, tag o release. Generato con `python scripts/release_report.py` da raw locali, senza eseguire riconoscimento.

La prima valutazione indipendente dopo il congelamento contiene **127 positivi e 50 negativi**, 6 fonti / 6 enti; concentrazione massima 29.13%. Esatti 33, famiglie corrette 0, accettazioni errate 5; estratti 176/177. Il campione non raggiunto resta un limite e non viene sostituito con sviluppo. Il motore non è stato corretto dopo questa misura.

| Corpus | N | Passati | Precisione doc. | Recall doc. | F1 doc. | Precisione fam. | Recall fam. | F1 fam. | Utile |
|---|---:|---:|---|---|---|---|---|---|---|
| Regressione sintetica | 35 | 35 | 100.00% (11/11) | 100.00% (11/11) | 100.00% (22/22) | 100.00% (14/14) | 87.50% (14/16) | 93.33% (28/30) | 100.00% (25/25) |
| Locked v1 storico | 69 | 60 | 96.43% (54/56) | 90.00% (54/60) | 93.10% (108/116) | 100.00% (6/6) | 66.67% (6/9) | 80.00% (12/15) | 86.96% (60/69) |
| Locked v2 sviluppo | 69 | 68 | 100.00% (56/56) | 100.00% (56/56) | 100.00% (112/112) | 83.33% (5/6) | 100.00% (5/5) | 90.91% (10/11) | 100.00% (61/61) |
| Hard negatives v1 | 30 | 30 | n.d. (denominatore zero) | n.d. (denominatore zero) | n.d. (denominatore zero) | n.d. (denominatore zero) | n.d. (denominatore zero) | n.d. (denominatore zero) | n.d. (denominatore zero) |
| Hard negatives v2 | 100 | 100 | n.d. (denominatore zero) | n.d. (denominatore zero) | n.d. (denominatore zero) | n.d. (denominatore zero) | n.d. (denominatore zero) | n.d. (denominatore zero) | n.d. (denominatore zero) |
| Canonico metadati | 1212 | 1162 | 100.00% (1162/1162) | 95.87% (1162/1212) | 97.89% (2324/2374) | n.d. (denominatore zero) | n.d. (denominatore zero) | n.d. (denominatore zero) | 95.87% (1162/1212) |
| Official development v2 | 162 | 70 | 100.00% (58/58) | 38.67% (58/150) | 55.77% (116/208) | n.d. (denominatore zero) | 0.00% (0/1) | 0.00% (0/1) | 38.67% (58/150) |
| Holdout indipendente v1 | 177 | 83 | 86.84% (33/38) | 25.98% (33/127) | 40.00% (66/165) | n.d. (denominatore zero) | n.d. (denominatore zero) | n.d. (denominatore zero) | 25.98% (33/127) |

Holdout: rifiuti dei positivi 70.08% (89/127); rifiuti corretti negativi 100.00% (50/50); errori ente 2.63% (1/38); errori versione 5.26% (2/38). Questi errori rimangono tali rispetto alle etichette fissate: nessuna reinterpretazione dopo la misura.

## Significato dei corpus

| Categoria | Scopo e provenienza | Indipendente | Limite |
|---|---|---|---|
| Regressione | 35 testi sintetici pubblici congelati | No | Compatibilità storica |
| Locked v1 | 69 etichette storiche immutate | No | Ambiguità note, riportate senza blocco automatico |
| Locked v2 | 69 etichette riconciliate con motivazioni Round 2 | No | Corpus di sviluppo, non promuove la release |
| Hard negatives | 30 v1 e 100 v2 sintetici difficili | No | Nessuna stima del rischio reale |
| Canonico | Una prova per ogni identità operativa, da metadati | No | Autocopertura, non lettura di moduli reali |
| Official development | 150 positivi e 12 negativi ufficiali, URL/hash/data congelati Round 2 | No | Usato ripetutamente; sei attese improprie e un ente aggregatore documentati |
| Holdout v1 | Nuove risorse dopo freeze, scelta metadata/SHA, esclusioni hash/URL/identità/codice/template | Sì rispetto ai file development | Etichette da elenco ufficiale, nessuna adjudication editoriale umana completa; possibili equivalenze non rilevate |
| OCR legacy | 7 gate con Tesseract reale | No | Orientamenti, timeout, PDF vuoto/digitale e pulizia |
| OCR v2 | 14 raster sintetici con Tesseract reale | No | Degradazioni riproducibili, non corpus di scansioni personali |

Gli errori di estrazione holdout restano nel denominatore. Precisione famiglia senza accettazioni è non definita e il gate rimane non dimostrato. `official_breakdowns.json` separa fonte, formato, metodo e OCR; ogni raw contiene confusion matrix e numeratori/denominatori. Bootstrap percentile al 95% per identità: 500 repliche sviluppo, 2.000 holdout; seed fisso, intervalli descrittivi che possono degenerare con zero errori. Il gruppo esclude già le versioni/template individuati dal controllo leakage; le identità canoniche restano note al catalogo.

### Intervalli Development

| Metrica | Stima | IC 95% per gruppi |
|---|---|---|
| document_precision | 100.00% (58/58) | 100.00–100.00% |
| document_recall | 38.67% (58/150) | 31.02–45.70% |
| document_f1 | 55.77% (116/208) | 47.35–62.73% |
| family_precision | n.d. (denominatore zero) | n.d. |
| family_recall | 0.00% (0/1) | 0.00–0.00% |
| family_f1 | 0.00% (0/1) | 0.00–0.00% |
| useful_coverage | 38.67% (58/150) | 31.02–45.70% |
### Intervalli Holdout

| Metrica | Stima | IC 95% per gruppi |
|---|---|---|
| document_precision | 86.84% (33/38) | 74.29–96.88% |
| document_recall | 25.98% (33/127) | 18.60–33.63% |
| document_f1 | 40.00% (66/165) | 30.07–49.40% |
| family_precision | n.d. (denominatore zero) | n.d. |
| family_recall | n.d. (denominatore zero) | n.d. |
| family_f1 | n.d. (denominatore zero) | n.d. |
| useful_coverage | 25.98% (33/127) | 18.60–33.63% |

## Cause e correzioni

| Causa iniziale | N | Esatti prima | Esatti dopo | Famiglia dopo | Rifiuti residui |
|---|---:|---:|---:|---:|---:|
| code_not_present_in_document | 8 | 0 | 2 | 0 | 6 |
| entity_not_present_or_indirect | 59 | 0 | 6 | 0 | 53 |
| expected_identity_wrong | 6 | 0 | 0 | 0 | 6 |
| generic_title | 1 | 0 | 1 | 0 | 0 |
| metadata_title_not_present_in_document | 35 | 0 | 24 | 0 | 11 |
| near_duplicate | 1 | 0 | 0 | 0 | 1 |
| other | 27 | 27 | 24 | 0 | 3 |
| recognizer_threshold | 2 | 0 | 1 | 0 | 1 |
| source_metadata_wrong | 1 | 0 | 0 | 0 | 1 |
| version_not_present | 10 | 0 | 0 | 0 | 10 |

Audit iniziale completo: 150 righe, 123 opportunità di fallback. Esatti **27 → 58**, zero identificazioni errate nel development finale. Titoli in finestre limitate, codici con segmenti numerici, intestazione emittente separata dal destinatario, versioni esplicite e rifiuto di sottotipi ambigui. Soglie globali invariate. Otto URL non ASCII corretti con conversione generale IRI→URI; non dimostra l’accessibilità dei server.

88 profili tecnici sparsi (otto token normalizzati ciascuno) provengono esclusivamente dal development, con URL/hash/data, fingerprint catalogo, schema e generatore deterministico; non sono metadati ufficiali né verifiche editoriali. Nessun testo personale viene cacheato. Le cache pubbliche del catalogo sono limitate; il full scan conserva il percorso di riferimento senza indici. Nessun documento ufficiale o testo estratto è redistribuito.

## Famiglie

Le 16 famiglie pregresse restano operative solo se già verificate. Migliorato il riconoscimento del titolo distintivo con emittente esplicito, senza attribuire anno o versione. Il development finale non produce fallback corretti: **0**, recall delle sole attese esplicitamente etichettate **0/1**, precisione non definita. Le 123 opportunità sono in CSV; non vengono inventate nuove famiglie verificate, né riclassificate automaticamente tre prove positive e cinque negative come revisione umana. Il gap di famiglie nelle nuove fonti rimane aperto.

## Estrazione e OCR

Diagnostica per file: caratteri, token, rapporto stampabili, frammentazione, pagine, OCR, warning; ordine `not_measurable` quando non deducibile. Layer non utilizzabile → OCR locale entro limiti esistenti; layer valido resta digitale. Il test mock del fallback verifica il percorso ma non conta come OCR reale.

Tesseract reale: **7/7 legacy**, **14/14 v2**, residui temporanei **0**. Versione `tesseract v5.4.0.20240606`, lingue eng, ita, osd; hash traineddata e similarità testo per degradazione nei raw.

## Prestazioni e memoria

| Motore | p50 ms | p95 ms | RSS caldo byte | Picco Python caldo byte | Catalogo byte | Indici tecnici byte | Crescita RSS caldo byte |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline | 74.8199 | 97.8367 | 30367744 | 299575 | 486406 | 0 | 143360 |
| round2 | 70.7431 | 106.9926 | 39624704 | 879746 | 1383437 | 0 | 876544 |
| candidate | 85.8425 | 118.23 | 43925504 | 881022 | 1383437 | 1281168 | 0 |

Warmup 35, sei iterazioni alternate su 35 casi (210 per motore); ordine invertito, stesso processo per latenza, processi separati per memoria. Rapporti candidata/baseline: **p50 1.147×, p95 1.208×**, entro 1,5×. Candidata/Round 2: 1.213× / 1.105×. RSS caldo/Round 2 1.109×; catalogo 1.000×. Current working set/RSS in separate fresh processes. Eight repeated warm passes; 16 MiB growth ceiling is a stability guard, not a general RAM certification. Gli indici escludono le altre cache legacy, il picco Python non equivale a RSS.

## Qualità, test e gate

Catalogo byte invariati: **1.216 conservati, 1.212 operativi, quattro rifiutati**, 10 demo, 19 fonti, 12 enti, 16 famiglie, 2.499 IPA, 1.216 provenienze. Integrità SQLite ok/FK zero. Tre gruppi identità e otto URL condivisi auditati in `DUPLICATES_AUDIT.md`; ambiguità residue esplicite, zero fusioni/cancellazioni automatiche. Quattro rifiuti tecnici conservano autore, motivazione, storico e provenienza, visibili nel filtro UI: non sono revoche ufficiali.

Suite: **547 passati, 0 falliti, 3 skip**, 385.8 s; Python 3.12.10, Windows-11-10.0.26300-SP0. Release-fast esclude dal gate soltanto locked v1 storico e conserva i suoi risultati. CI YAML verificata localmente; comandi portabili eseguiti in Windows. Linux/macOS/Windows GitHub: **pending_external_gate**, nessun push richiesto o effettuato. `release_gates.json` distingue ogni requisito: non sono dichiarati pronti i gate non provati.

La UI presenta nell’ordine holdout indipendente, hard negatives, OCR e performance; regressioni e development seguono nei dettagli. Tutti i dati dinamici restano testo inerte. Espansione sospesa, piano in `ROUND4_PLAN.md`.

## Regressione di famiglia da risolvere

Il benchmark locked v2 rileva **R061**, atteso NO_MATCH, accettato erroneamente come famiglia 4 ADER. Locked v2 passa **68/69** e release-fast restituisce **1**; il fallimento non è attribuito al v1 storico. Il freeze è stato effettuato prima che arrivasse questo risultato. Il motore viene conservato durante il protocollo indipendente e la correzione passa al prossimo ciclo, con un nuovo holdout. Questo è un ulteriore blocco di release.

Memoria candidata/baseline: RSS caldo 1.446×, oggetti catalogo 2.844×, picco Python caldo 2.941×. Rapporto indici non definito rispetto a zero byte baseline; valori assoluti e ambito nella tabella, dettagli in `memory_ratios_round3.json`.

Acquisizione holdout in due lotti prima di qualunque lettura/classificazione: la coda positivi ha esaurito il budget senza arrivare ai negativi; un solo lotto informativo aggiuntivo, massimo 65 richieste, ha acquisito 50 negativi con 60 richieste. Manifest iniziale e hash prima/dopo conservati; selezione originale metadata/SHA, nessun ritentativo di fonti bloccate, nessun cambiamento del motore. La quota di positivi/fonti resta esplicitamente insufficiente.
