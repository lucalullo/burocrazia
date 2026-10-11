# Benchmark Round 2

**NOT READY**, software 0.6.1, target 0.7.0. Nessun push, tag o release. Misure sul commit `9cdd96f797d705632d0b6684230ebc2487d317a3`; i successivi aggiornamenti di report non cambiano il motore. Corpus pubblici usati durante lo sviluppo: nessuna indipendenza o generalizzazione dimostrata.

## Riconoscimento testuale

| Corpus | Pass/casi | Doc precision | Doc recall | Doc F1 | Fam precision | Fam recall | Fam F1 | Utile |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| burocrazia-synthetic-text-regression-2026-09-05 | 35/35 | 100.00% (11/11) | 100.00% (11/11) | 100.00% (22/22) | 100.00% (14/14) | 87.50% (14/16) | 93.33% (28/30) | 100.00% (25/25) |
| burocrazia-release-locked-v1 | 59/69 | 96.43% (54/56) | 90.00% (54/60) | 93.10% (108/116) | 100.00% (5/5) | 55.56% (5/9) | 71.43% (10/14) | 85.51% (59/69) |
| burocrazia-release-locked-v2 | 69/69 | 100.00% (56/56) | 100.00% (56/56) | 100.00% (112/112) | 100.00% (5/5) | 100.00% (5/5) | 100.00% (10/10) | 100.00% (61/61) |
| burocrazia-hard-negatives-v1 | 30/30 | n.d. (0 casi) | n.d. (0 casi) | n.d. (0 casi) | n.d. (0 casi) | n.d. (0 casi) | n.d. (0 casi) | n.d. (0 casi) |
| burocrazia-hard-negatives-v2 | 100/100 | n.d. (0 casi) | n.d. (0 casi) | n.d. (0 casi) | n.d. (0 casi) | n.d. (0 casi) | n.d. (0 casi) | n.d. (0 casi) |
| catalog-canonical-coverage-v1 | 1191/1212 | 100.00% (1191/1191) | 98.27% (1191/1212) | 99.13% (2382/2403) | n.d. (0 casi) | n.d. (0 casi) | n.d. (0 casi) | 98.27% (1191/1212) |

V1 resta 59/69: sei intestazioni di una parola non provano un modulo; due fixture ADER attribuiscono al riscossore atti del creditore; due testi attesi come famiglia identificano documenti specifici. V2 corregge esplicitamente queste dieci attese: `corpus_locks_v2.json` conserva vecchia/nuova etichetta, motivo e fonti ufficiali. Il 69/69 v2 non cancella il risultato v1 né risolve da solo il gate >=99%. Le due famiglie ADER restano storiche, senza nuova verifica automatica. Non sono state introdotte nuove famiglie operative non revisionate.

Copertura canonica finale: 1191/1212 identità operative; #429 e le FAQ #1077/#1081/#1091 sono esclusi perché rifiutati con autore e storico. Dei 70 rifiuti iniziali, 49 sono corretti e 21 persistono; dettaglio in `canonical_rejections_round2.csv`, con risultato finale e azione. I metadati canonici non simulano file reali.

Hard negatives v2: 100/100 rifiutati, zero false acceptance. Sono conservati i 30 casi v1; i 70 aggiunti combinano sette intestazioni informative con dieci enti/moduli. Sono varianti di template correlate, non 100 documenti indipendenti. I 12 negativi ufficiali acquisiti sono misurati separatamente.

## Official-real

Acquisizione: 234 tentativi, 162 file distinti scaricati, 2 contenuti duplicati e 70 fallimenti. Il manifest comprende soltanto i 162 file acquisiti: non rappresenta un tasso di download del 100% su tutti i tentativi. Fallimenti: 30 risposte ADE non nel formato dichiarato, un 403 INPS e 29 rifiuti successivi della fonte nella sessione, due divieti robots e otto errori di codifica URL non ASCII. Questi ultimi restano un limite del runner di acquisizione. Prove nel raw `official_acquisition.json`.

150 moduli attesi e 12 negativi: 162/162 estratti, 27 exact corretti, 0 family, 123 rifiuti dei positivi, 0 identificazioni errate accettate. Negativi: 12/12 rifiutati. Precisione 100.00% (27/27); recall 18.00% (27/150); F1 30.51% (54/177); errori ente 0.00% (0/27); versione 0.00% (0/27). OCR usato su 4 file.

Otto fonti; concentrazione massima positivi 20.00%, totale 19.14%. {'mimit': 28, 'mef': 3, 'anac': 2, 'inail': 31, 'funzione_pubblica': 9, 'giustizia': 30, 'inl': 30, 'lavoro': 29}. Ordine SHA-256 entro fonte e round-robin, senza selezione sui successi. PDF e DOCX; annuali fiscali ADE e INPS non rappresentati adeguatamente per risposte non PDF e blocchi di acquisizione. Etichette derivate dagli elenchi ufficiali, non tutte adjudicate: 429 era un file informativo, conservato nel manifest congelato e poi escluso dal catalogo operativo. Il suo rifiuto resta un fallimento rispetto alla vecchia etichetta.

Il campione ufficiale è stato usato per sviluppare le correzioni: non è un hold-out indipendente. La prima esecuzione aveva 9 identificazioni errate (5 di ente): conservata in `official_documents_v2_before_safety_fix.json`. Dopo correzioni generali, due sottocodici sono identificati correttamente e gli altri sette casi rifiutati. La precisione migliora sacrificando alcuni match deboli; il recall reale resta un limite serio. I file, gli eseguibili OCR e il testo estratto non sono redistribuiti.

| Fonte | Estratti | Exact corretti | NO_MATCH | Wrong accettati |
|---|---:|---:|---:|---:|
| Autorità Nazionale Anticorruzione | 2 | 0 | 2 | 0 |
| Dipartimento della Funzione Pubblica | 9 | 0 | 9 | 0 |
| INAIL | 31 | 5 | 26 | 0 |
| Ispettorato Nazionale del Lavoro | 30 | 16 | 14 | 0 |
| Ministero del Lavoro | 29 | 0 | 29 | 0 |
| Ministero dell'Economia e delle Finanze / RGS | 3 | 1 | 2 | 0 |
| Ministero delle Imprese e del Made in Italy | 28 | 3 | 25 | 0 |
| Tribunale di Venezia | 30 | 2 | 28 | 0 |

## OCR reale e performance

tesseract v5.4.0.20240606, ita/eng/osd; 7/7 legacy (0°,90°,180°,270°, blank PDF, timeout nativo, PDF digitale senza OCR), residui 0. OCR sintetico v1 12/12, v2 14/14: contrasto, blur, JPEG, crop, scale, rumore con seed e PDF due pagine. Similarità OCR per caso nel raw; queste 14 prove riguardano un solo modello demo, non 14 modelli reali né tutte le scansioni amministrative. Nessun mock conteggiato come OCR reale.

Prestazioni alternate, stessa macchina/Python, warm-up 35 casi e 6 iterazioni (210 misure per motore): baseline 49.2871/72.3086 ms; candidata 50.8552/75.6706 ms; rapporti p50/p95 1.032x/1.046x. Memoria Python warm: {'baseline': 299649, 'candidate': 880599} byte, rapporto 2.939x. Non è RSS/native heap. Il confronto storico Round 1 baseline 30,7/34,4 ms e candidata 70,8/103,4 ms resta riportato, ma il gate usa la baseline rieseguita in alternanza; tempi assoluti variano con carico e ambiente. Nessuna shortlist: full scan conservato, eliminata analisi ripetuta dei metadati. Percorso di riferimento confrontato su tutti i corpus testuali e canonici. Le durate dei componenti sono strumentate e sovrapposte: non vanno sommate né confrontate con la latenza non strumentata. Dettagli in `performance_profile_round2.json`.

## Statistica e gate

N e numeratori/denominatori sono in ogni metrica raw. Bootstrap percentile per gruppi, 95%, seed 20261011, 500 iterazioni; meno di cinque gruppi non produce intervalli. Intervalli descrittivi dei corpus pubblici, spesso degeneri con zero errori: non dimostrano rischio nullo.

| Corpus | Metrica | N denominatore | Stima | CI95 |
|---|---|---:|---:|---|
| burocrazia-release-locked-v1 | document_precision | 56 | 96.43% (54/56) | [0.898, 1.0] |
| burocrazia-release-locked-v1 | document_recall | 60 | 90.00% (54/60) | [0.7702, 1.0] |
| burocrazia-release-locked-v1 | family_precision | 5 | 100.00% (5/5) | [1.0, 1.0] |
| burocrazia-release-locked-v1 | family_recall | 9 | 55.56% (5/9) | [0.2, 0.9604] |
| burocrazia-release-locked-v1 | unknown_correct_rejection_rate | 0 | n.d. (0 casi) | n.d. |
| burocrazia-release-locked-v2 | document_precision | 56 | 100.00% (56/56) | [1.0, 1.0] |
| burocrazia-release-locked-v2 | document_recall | 56 | 100.00% (56/56) | [1.0, 1.0] |
| burocrazia-release-locked-v2 | family_precision | 5 | 100.00% (5/5) | [1.0, 1.0] |
| burocrazia-release-locked-v2 | family_recall | 5 | 100.00% (5/5) | [1.0, 1.0] |
| burocrazia-release-locked-v2 | unknown_correct_rejection_rate | 8 | 100.00% (8/8) | [1.0, 1.0] |
| burocrazia-hard-negatives-v2 | document_precision | 0 | n.d. (0 casi) | n.d. |
| burocrazia-hard-negatives-v2 | document_recall | 0 | n.d. (0 casi) | n.d. |
| burocrazia-hard-negatives-v2 | family_precision | 0 | n.d. (0 casi) | n.d. |
| burocrazia-hard-negatives-v2 | family_recall | 0 | n.d. (0 casi) | n.d. |
| burocrazia-hard-negatives-v2 | unknown_correct_rejection_rate | 100 | 100.00% (100/100) | [1.0, 1.0] |
| official-local-v2 | document_precision | 27 | 100.00% (27/27) | [1.0, 1.0] |
| official-local-v2 | document_recall | 150 | 18.00% (27/150) | [0.122, 0.2425] |
| official-local-v2 | family_precision | 0 | n.d. (0 casi) | n.d. |
| official-local-v2 | family_recall | 0 | n.d. (0 casi) | n.d. |
| official-local-v2 | unknown_correct_rejection_rate | 12 | 100.00% (12/12) | [1.0, 1.0] |

Suite: 515 passed, 0 failed, 3 skipped, 334.14 s, Windows-11-10.0.26300-SP0, Python 3.12.10. A01–A05 inclusi nella suite; OCR reale separato. SQLite integrity ok, zero FK, migrazione aggiuntiva idempotente, provenienza strutturale 100%, continuità v0.6.1. Uniche modifiche alle righe Round 1: stato di 429 e delle tre FAQ INAIL 1077/1081/1091, con autore/storico; nessuna modifica a dati verificati. CI GitHub multipiattaforma non eseguita. Il comando fast conserva exit 1 per v1: non viene mascherato. Gate: `release_gates.json`.
