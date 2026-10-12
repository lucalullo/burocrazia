# Round 10 — NOT READY

Software pubblico 0.6.1, target 0.7.0, schema 610. Branch `codex/coverage-benchmark-v0.7.0`; ingresso HEAD `8c13da270fe2c4db212ca3611fb5ce0ddef7b0d8`, working tree pulito. HEAD durante il report `8c13da270fe2c4db212ca3611fb5ce0ddef7b0d8`; commit finale e SHA archivio sono registrati dopo il commit in `dist/package-verification-round10.json` e nella consegna. Nessun push, tag o release. CI `external_pending`.

## Decisione e prerequisiti

`ready_to_freeze=false`. Coverage file-backed 941/1158 = 81.260794%, target 85%: necessari 985, mancano ancora 44. Coverage operative 941/1212 = 77.640264%, target70% superato. Unknown 107 confermati, 7 fonti e 7 autorità ospitanti; concentrazione massima 42.06%. Conteggio minimo superato, diversità e bilanciamento insufficienti. Nessun freeze e nessuna evaluation v5, come richiesto quando A o B fallisce. Nessuna modifica a motore, pesi, soglie, fusion tiers, scoring, decision policy o fingerprint attive.

## Recovery

Piano completo dei 217 residui in `fingerprint_recovery_plan.csv`: tier `{"1": 27, "2": 63, "3": 32, "4": 95}`. Fonti, ente, URL primario/alternativo, stato precedente, formato, azione ed esito per ogni ID. Alternative wrapper/multipart/redirect/IRI e osservazioni già esplorate R8/R9 riesaminate dai byte e dalle ricevute cached; nessun retry di 403/429 o aggiramento robots. Il limite 8 MiB non è stato aumentato per recuperare il file INL29-3 da 8.42 MB. Risorse con conflitto ente, apertura insufficiente o identità condivisa restano escluse dal conteggio univoco.

Il controllo PATH del Round 9 non trovava LibreOffice, ma l’installazione standard esiste: probe reale LibreOffice 26.8.0.3. Correzione della diagnosi, senza riscrivere il raw storico. Nuovo convertitore maintenance-only: preflight contenuti attivi/relazioni esterne, profilo temporaneo senza macro/aggiornamento link, processo headless nascosto senza shell, timeout 45 s, byte 8 MiB, pagine 100, testo 1M. Profilo separato non equivale a sandbox OS; non si dichiara una garanzia contro documenti ostili arbitrari. Nessuna installazione e nessuna conversione nel runtime.

Analizzate 63 risorse legacy distinte, 47 conversioni PDF valide; contenuto rappresentato da sketch digitali pubblici in `legacy_resource_fingerprints.json`, senza OCR dei derivati e senza PDF temporanei in Git. 2 candidati univoci superano il controllo d’identità d’apertura invariato: ID `[422, 1101]`. I restanti hanno prove insufficienti/conflitti/condivisioni o sono rifiutati dal preflight/limiti/conversione. Original SHA, derived SHA, ricevuta effettiva e SHA convertitore restano distinti. Il bundle v3 ammette soltanto PDF/DOCX ufficiali: nessun PDF derivato presentato come byte ufficiale. Questi candidati non sono attivi e non aumentano la coverage; anche tutti i 2 candidati non colmerebbero il delta 44. Non sono state allentate le prove d’identità per trasformare nomi di file in titoli forti.

L’audit iniziale del profilo maintenance è conservato in `legacy_resource_fingerprints_initial_profile.json`. Nel controllo finale i tipi del registro installato hanno mostrato Writer/Link booleano errato, Calc/Link=0 (always) e una proprietà Common/Load non dichiarata: correzione motivata in `legacy_profile_correction.json`, con fonti primarie LibreOffice. Profilo finale con blocco esplicito macro/OLE/DDE/referer e valori tipizzati never; conversioni ripetute, nessun dato promosso da quel tentativo iniziale. Anche performance e osservazioni development antecedenti alla correzione maintenance sono conservate con i propri hash; i risultati principali sono quelli finali rieseguiti. Nessuna modifica al runtime.

Restano 1027 binding di risorsa: 979 active unambiguous per 941 identità e 48 condivisi. Canonical resource e identity recognition distinti; SHA comune non dà identità univoca. Native upload DOC/RTF/XLS/XLSX/ODT resta unsupported. Seed invariato, 1216 reali/1212 operative/19 fonti/16 famiglie. Nessun nuovo document_id, fonte del catalogo o stato editoriale.

## Unknown e truth

Acquisizione separata nel solo maintenance con --allow-network, HTTPS/robots/allowlist, budget 300 richieste iniziali più 7 effettive nel tentativo di bilanciamento (budget 60). 154 candidati acquisiti da nuove fonti istituzionali fuori dal catalogo; 153 nuovi SHA auditati, uno già nel manifestv1. Classificazioni `{"ambiguous": 94, "confirmed_unknown": 39, "duplicate_of_catalog": 8, "possible_family_match": 7, "unsupported_truth": 5}`. Nessuna promozione automatica da discovery a truth.

Distribuzione confermati `{"agid": 15, "anac": 9, "inail": 16, "lavoro": 6, "mef": 13, "mimit": 45, "mit": 3}`. Tipi `{"circolare": 28, "comunicato": 1, "decreto": 27, "delibera": 2, "direttiva": 2, "guida": 31, "istruzioni": 3, "manuale": 6, "modulo": 2, "regolamento": 5}`. Con codice/numero documento o protocollo esplicito 19, senza 88; con versione/revisione/edizione/anno esplicito 26, senza 81. Un anno citato in una legge non rende versionato il documento; il primo audit lessicale è conservato separatamente, nessuna truth label cambiata. `entity` indica l’autorità che ospita la fonte e non certifica ogni emittente storico: nessuna pretesa di 8 emittenti indipendenti. I corpus comprendono circolari, istruzioni, guide e moduli veri; non si dichiara una copertura rappresentativa di tutti gli hard unknown.

Audit prima delle predizioni: titolo e tipo sostenuti dall’apertura 2000 caratteri, codice, ente/fonte, revisione/anno osservato, URL/final URL/ricevute/date effettive, SHA, full catalog titles/codes, contenuto near-duplicate e alias delle 16 famiglie. Dubbi esclusi. Tutti 68 unknownR9 conservati nello sviluppo, compresi quelli nominalmente evaluation nel vecchio manifest, perché già riconosciuti. Split corrente `{"unknown_dev": 75, "unknown_eval": 32}`; SHA e gruppi near disgiunti. Due coppie near trattate come componenti con lo stesso split; audit separato `unknown_resource_split_audit.json`. È una prova del resource split, non un certificato leakage di evaluation congelata; duplicati semantici fuori dagli sketch restano un limite.

V2 base del reference truth e manifest unknown v1 immutati; nuovo addendum motivato con 39 conferme e SHA del registro base. Le vecchie etichette locked/v1, ambiguità e motivazioni restano disponibili. Manifest unknown v2 contiene ricevute e prove, nessun percorso locale assoluto. Non sono stati eliminati i 45 MIMIT per abbassare artificialmente la concentrazione. Dopo il primo audit è stato tentato Salute/PNES/PNRR con 7 richieste ulteriori: risposte senza file acquisibili, non contate come unknown. L’aggiunta necessaria a una concentrazione 25% con 45 MIMIT richiede almeno 180 confermati, quindi altri 73 rispetto ai 107 attuali.

Development misurato 75/75, ID univoci 75, rifiuti corretti 75, false accept 0, errori estrazione 0. Writer R9 transazionale realmente usato, journal ignorato, export finale SHA `e50bee7a352b2aa64890daf246959c23b09203ff78d42e9c4db80d007693ad1e`. Nessun tuning. Unknown_eval 32 riservati, zero chiamate di riconoscimento e nessuna stima della loro rejection. Selezione delle identità note v5 mai avvenuta.

## Safety e canonical

NO storici 241 osservazioni, false accept 0. R061 NO; EX02MISSINGREV/EX03MISSINGREV NO; cinque vecchi falsi accept ufficiali verdi (rifiuto o propria identità corretta). Canonical 979/979, wrong 0, estrazioni fallite 0. Nessuna label ambigua v1 promossa per migliorare i gate. Base 33/35 e locked v1 59/69 restano visibili; v2 69/69, compat 37/37. Canonical è verifica delle risorse censite, non generalizzazione.

| Corpus | Corretti | Totale |
| --- | --- | --- |
| development_regression | 33 | 35 |
| release_locked_v1 | 59 | 69 |
| release_locked_v2 | 69 | 69 |
| hard_negatives_v1 | 30 | 30 |
| hard_negatives_v2 | 100 | 100 |
| family_release_v3 | 161 | 161 |
| development_compat_v2 | 37 | 37 |
| catalog_coverage | 1169 | 1212 |

## Performance

Protocollo R9 rieseguito in processo isolato: 402 richieste warm con nuovi contesti, p50 25.58ms, p95 146.09ms, p99 211.55ms, gate p95≤250ms PASS. Digital PDF p95 214.51ms; scan con OCR già disponibile p95 92.40ms; scannedPDF wrapper p95 92.12ms. OCR estrazione 14 input sintetici misurato separatamente: `{"n": 14, "p50": 14649.7186, "p95": 15010.0855, "p99": 15046.8726}`ms. Nessuna cache globale degli input e nessun shortcut SHA nella misura.

Indice 89725169bytes; RSS afterwarm 422141952bytes, crescita successiva 182915072bytes. Il gate aggregato non garantisce ogni formato; vedere distribuzioni e componenti non additivi nei raw. La stabilità RSS non è dimostrata, causa non isolata. Nessuna ulteriore ottimizzazione del motore effettuata.

## Freeze, evaluation, family, test e CI

Freeze no; commit freeze assente. Evaluation v5, retrieval@1/@5/@10/@25, robustezza scansioni/compilati e unknown_eval non misurati; nessun file di evaluationv5 fabbricato. Generator filled R8 e 50/356 raw v4 interrotti preservati. Family experimental/insufficiently validated (0 famiglie reali valutabili nella misuraR9 invariata); non entra nel useful recall. Test writer R9 interruption/resume/dedupe/finalizzazione atomica/count/SHA conservati e rieseguiti nella suite.

Suite locale `{"status": "passed", "passed": 758, "skipped": 3, "failed": 0, "seconds": 514.23, "log_sha256": "0f2023306ca44ed0eb898ed2bbf1671170ad9fa9c3ad41c587e66f80566af387", "python": "3.12.10", "platform": "Windows-11-10.0.26300-SP0", "skip_reasons": "Windows: one symlink privilege and two FIFO unsupported cases; see preserved local pytest log.", "post_correction_targeted": {"passed": 9, "failed": 0, "seconds": 0.71, "log_sha256": "f2317bd1550b555fd2439ee1eddc1d6065741ff2113740c6e2a0e3108ed60cd9", "scope": "Profile values and timeout/provenance contracts retested after maintenance profile correction; not added a second time to full-suite count."}}`. Test offline aggiunti per contenuti attivi, relazioni esterne, traversal, profilo/timeout/provenance e unknownv2; Tesseract reale ita+eng nei controlli esistenti. Catalogo, corpus/hash, cinque casi critici e workflow verificati. Solo collaudo Windows, nessuna validazione editoriale o di altre piattaforme rivendicata. CI esterna pending; comandi legacyv1 del workflow conservano i due rifiuti rispetto alle labelpositive ambigue e non vengono presentati come greenCI.

| Gate | Target | Actual | Esito |
| --- | --- | --- | --- |
| coverage_file_backed | >=85% | 0.812607944732297 | FAIL / non misurato |
| coverage_all | >=70% | 0.7764026402640264 | PASS |
| unknown_count | >=100,target150 | 107 | PASS |
| unknown_sources | >=8,target10+ | 7 | FAIL / non misurato |
| unknown_balance | <=25% | 0.4205607476635514 | FAIL / non misurato |
| historical_safety | 0 historical NO accepts | [] | PASS |
| canonical | 100% unambiguous | {"exact": 979, "extraction_failed": 0, "family": 0, "reject": 0, "wrong": 0} | PASS |
| performance | p95<=250ms | {"n": 402, "p50": 25.5838, "p95": 146.0866, "p99": 211.5491} | PASS |
| unknown_development | observed separately | {"total": 75, "false_accepts": 0, "extraction_failed": 0} | PASS |
| v5_identities | >=30 | null | FAIL / non misurato |
| v5_sources | >=6 | null | FAIL / non misurato |
| v5_concentration | <=30% | null | FAIL / non misurato |
| v5_representations | >=400 | null | FAIL / non misurato |
| v5_scans | >=200 | null | FAIL / non misurato |
| v5_fills | >=50 valid | null | FAIL / non misurato |
| v5_unknown_eval | >=30 | null | FAIL / non misurato |
| v5_precision | >=99.5% | null | FAIL / non misurato |
| v5_exact_recall | >=90% | null | FAIL / non misurato |
| v5_entity_version_errors | 0 | null | FAIL / non misurato |
| v5_scan | P>=99.5%,R>=85% | null | FAIL / non misurato |
| v5_filled | P>=99.5%,R>=90% | null | FAIL / non misurato |
| v5_unknown_rejection | >=99% | null | FAIL / non misurato |
| v5_retrieval_at25 | 100% | null | FAIL / non misurato |
| tests | all pass | {"status": "passed", "passed": 758, "skipped": 3, "failed": 0, "seconds": 514.23, "log_sha256": "0f2023306ca44ed0eb898ed2bbf1671170ad9fa9c3ad41c587e66f80566af387", "python": "3.12.10", "platform": "Windows-11-10.0.26300-SP0", "skip_reasons": "Windows: one symlink privilege and two FIFO unsupported cases; see preserved local pytest log.", "post_correction_targeted": {"passed": 9, "failed": 0, "seconds": 0.71, "log_sha256": "f2317bd1550b555fd2439ee1eddc1d6065741ff2113740c6e2a0e3108ed60cd9", "scope": "Profile values and timeout/provenance contracts retested after maintenance profile correction; not added a second time to full-suite count."}} | PASS |
| family | >=5 real evaluable families | "experimental / insufficiently validated" | INFO / PENDING |
| CI | external_pending | "external_pending" | INFO / PENDING |

## Archivio

`dist/BurOCRazia-v0.7.0-candidate-NOT-READY-round10.zip`, da HEAD committato con verifica seed/corpus/hash byte sorgenti, raw storici e igiene. Commit e SHA256 finali in `dist/package-verification-round10.json` e `.zip.sha256`, fuori dal proprio contenuto per evitare autoreferenze. Archivi R8/R9 e checksum conservati. Limiti bloccanti: coverage 81.26%,7 fonti unknown,concentrazione 42.06%,nessuna evaluation indipendente. Versione pubblica 0.6.1.
