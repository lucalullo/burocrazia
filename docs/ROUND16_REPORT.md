# Round16 — NOT READY

Software 0.6.1, schema610, branch `codex/coverage-benchmark-v0.7.0`; ingresso `d39103d0673b8690816df1f9a3a4499a46f94f45`. Freeze `68a3d7e31996a578b403f5bd815a06218b3a6e95`. Commit finale e SHA archivio nel verificatore esterno `dist/package-verification-round16.json`, per evitare autoreferenze. Nessun push, tag o pubblicazione; CI external_pending.

## Correzione di contesto e truth

EX02/EX03 sono **sintetici INPS CI543/CI544**, record13/12, revisione1.1 omessa. Gli expected originali restano visibili; esclusione dalla truth certa motivata dalla **reference_truth_v2 già esistente**, non dall'errore del prompt. I due INAIL ambigui sono **U14-5f0c017c3d56e6c5** e **U14-c1fc4765c01dcd62**, annualità2025/2024 rispetto al canonico2023. Reference truth v3 li conserva ambiguous: nessun tuning, nessuna identità annuale o sostituzione inventata.

Release truth policy v1 e addendum motivato a v3: **1258 contratti confermati** =1007 binding canonici tecnici+241 contratti sintetici di astensione+1 ANAC ufficiale+9 limiti parser. Non sono1258 esempi indipendenti né verifiche editoriali. Confirmed non può essere escluso; ambiguous/insufficient/historical_only restano fuori dal gate certo e visibili nello storico. Obsolete richiede nuova qualificazione documentata. Originali v1/v2/v3 e corpus immutati. ANAC già osservato è regressione diagnostica confermata, esclusa dai nuovi corpus indipendenti. Policy/hash/evidenze in RELEASE_TRUTH_POLICY.md e truth_policy_audit.json.

## Ottimizzazioni e equivalenza

Due funzioni: deduplicazione per richiesta di trigrammi/ngrammi prima del loro hash; grayscale una volta prima delle quattro rotazioni ortogonali, che trasportano gli stessi pixel. Nessuna cache globale di testi o feature caricate. Scoring, pesi, soglie, candidateK, ranking/tie-break, veto ente/versione, family e reason code invariati; dataset/catalogo/fonti byte-identici. Il fix R15 sull'intestazione rimane.

Confronto completo prima/dopo: **1563 casi, zero differenze**, inclusi risultato pubblico completo, score, runner-up, margine, candidati, ente/versione e reason/tier. Canonici1007, negativi241, hard negatives, R061, ANAC testo+PDF, EX02/EX03, due PDF INAIL, vecchi cinque critici e rappresentazioni scan/filled/R6/R7/R8 già osservate. Primo set1399 più supplemento164, entrambi bloccati prima di cambiare il motore. OCR estratto una volta per isolare il riconoscimento; test finali OCR reali separati. Valori e hash in semantic_equivalence.json; test algoritmici indipendenti per Unicode/clipping e RGB/RGBA/L/palette, dimensioni pari/dispari/minime.

Profiling reale baseline conservato: costi inclusivi sovrapposti, non sommabili. Page scoring/features, hash e visuali rilevanti. Nessun rerun o selezione dei tempi favorevoli.

| Run | p50 ms | p95 ms |
|---|---|---|
| 1 | 62.3783 | 244.9918 |
| 2 | 58.1195 | 231.8317 |
| 3 | 58.1386 | 242.1458 |
| 4 | 59.4299 | 237.4964 |
| 5 | 62.5482 | 270.3926 |
| 6 | 64.8735 | 264.3677 |
| 7 | 65.7 | 269.1808 |

Mediana p95 **244.9918ms** contro263.0707ms R15: **PASS<=250**. **4/7** sotto250; target preferiti >=5/7 e mediana<=220 non raggiunti, non blocker. 67 input fissi,402 richieste/run,2814 tempi, contesti nuovi e cache solo catalogo/index pubblico. Sistema Windows/Python3.12.10, Tesseract5.4 ita+eng locale. L'attività generale del computer può variare; nessun altro benchmark di questo repository è stato avviato in parallelo ai sette run. Non è un collaudo Linux/macOS né una garanzia di latenza su altre macchine.

## Coverage, canonici, safety e storico

Coverage1002/1158 = **86.528497%**, PASS>=85; totale operativo1002/1212=82.673267%, PASS>=70. Definizione e denominatori congelati;33 associazioni shared-only non diventano accuratezza esatta. Canonici **980/980 nativi+27/27 legacy**, PASS100%. **241 NO sintetici,0 accettazioni**; ANAC testo/PDF, R061, due contratti Round8 e cinque critici PASS safety (4 identità esatte,1 NO prudente; quel NO resta mismatch esatto nello storico). Input safety **9/9**,0 crash,0 residui,0 chiamate recognition,0 risultati DOCUMENT/FAMILY. Quattro PDF>100 pagine restano fuori classificazione e dentro safety.

Historical-regression-fast: **15 mismatch conservati su1517 expected**, exit1:2 EX02/EX03,10 locked-v1,2 INAIL ambigui,1 rifiuto prudente sul noto OH1-047. Il vecchio CLI `benchmarks.evaluate --fast` conserva exit1 su EX02/EX03. Il nuovo `python -m benchmarks.round16_gates release-gate-fast` confronta i1258 contratti qualificati con le osservazioni effettive del runtime corrente, controlla hash e produce exit0; non modifica gli expected storici. `historical-regression-fast` è distinto e mostra tutti gli expected originali. Metadati catalog-coverage separati e nessuna accuratezza ufficiale inferita. V2 Round14 resta **107/114**,3DOC,0FAMILY,4 errori, raw/manifest/label immutabili; il replay R15 108/114 resta soltanto sviluppo.

## Unknown v3, evaluation v5 e famiglia

**Non eseguito. Campione indipendente insufficiente: 95/100 casi obbligatori. Nessuna predizione avviata.** Il pool finale contiene95 casi qualificati,13 fonti,18 enti,13 categorie; concentrazione massima21.0526%. Fonti/tipi/concentrazione passano, il numero di casi no: ne mancano5. Corrette rejection, false DOCUMENT/FAMILY ed errori ente/versione **non misurati**,0 chiamate release.

788 candidati da tre lotti; richieste effettive [400, 400, 160], totale 960.108 qualificazioni automatiche provvisorie diventano95 casi indipendenti dopo la revisione:1 relazione irrisolta e12 rappresentazioni molto simili escluse. Il terzo traversal termina naturalmente a160/400 richieste, con soli2 nuovi qualificati rispetto ai93 precedenti. È una raccolta limitata dal protocollo, non un'esplorazione esaustiva dei siti ufficiali. Intestazioni primarie e confronto col catalogo precedono ogni scelta/predizione. La bozza MIMIT2019 collegata al modello582/2020 resta irrisolta ed esclusa. Correzioni di emittenti ricavati da citazioni, coemittenti e tipo primario documentate in unknown_v3_primary_truth_review.json. Nessun metadata/catalogo runtime aggiornato. Nessun falso positivo o precisione vengono inventati su un corpus non eseguito. Il manifest release non viene creato se il minimo non passa; la selezione insufficiente e il risultato not_run restano negli artifact.

Selezione prevista solo dopo freeze, seed2026101316, quote source e gruppi near-resource, senza score; registrazione contaminazione v3 aggiuntiva, SHA e varianti già osservate escluse. Input oltre i limiti e identità non qualificate non entrano come unknown certi. Se un gate fallisce, stop senza tuning/replay sul set. V5 è autorizzata soltanto dopo PASS unknown. Preflight: **non misurata**. Robustezza, scansioni, filled, retrieval@1/@5/@10/@25 e mix unknown sono **non misurati**. Nessuna metrica storica riempie i campi mancanti. Family resta **experimental / insufficiently validated**, nessuna nuova prova su>=5 famiglie reali identity-held-out.

## Test e controlli

Baseline già eseguita786 passed,3skip; finale **819 passed,0 failed,3 skipped**, 677.72s, log SHA registrato. I run completi nel temporaneo del workspace hanno incontrato WinError5 nella pubblicazione atomica delle directory dei test; entrambi restano nei log e negli audit, senza modifiche runtime. La verifica dei pacchetti nel temporaneo nativo Windows ha prodotto24 passed/3skip; suite finale eseguita nello stesso ambiente nativo. Un PASS finale non cancella i fallimenti precedenti e non dimostra la causa del blocco Windows oltre l’errore osservato. Primo run completo810 passed,1failed,2skip; il test isolato symlink raggiunge lo skip previsto per privilegio Windows assente. Dettagli in tests.json/validation_environment.json. Nessun retry nel runtime o modifica IO estranea al vincolo performance-only. Un primo CLI release gate diagnostico confrontava erroneamente i vincoli forbidden_entities come campi osservati: corretto soltanto il comparatore, aggiunti due controesempi; sei NO effettivi non erano falsi positivi. Artifact iniziale preservato,1258 contratti PASS nel gate finale.

Il test storico R15 verifica il suo commit finale d39103d; il nuovo controllo R16 vincola le modifiche correnti alle due funzioni autorizzate e confronta semanticamente gli output. Compile, SQLite integrity/FK, copia/migrazione schema610 e conteggi righe, binding, validator fingerprintv1/v2/v3, compat-v2, schema truth e lock storici PASS. Test sintetici, Tesseract reale, adjudication precedente e CI/collaudo di piattaforma restano separati. Catalogo completo, provenance e famiglia preservati; runtime locale senza LLM/API/telemetria/importazione acquisitori. Acquisizione/truth e predizioni indipendenti hanno stati distinti negli artifact: nessun caso non eseguito viene dichiarato collaudato. La raccolta maintenance è separata, con opt-in rete, robots, allowlist e lotti limitati; non scrive nel catalogo né importa trasporti nel runtime.

## Gate

| Gate | Target | Misurato | Esito | Obbligatorio |
| --- | --- | --- | --- | --- |
| coverage | PASS | True | PASS | sì |
| canonical | PASS | True | PASS | sì |
| confirmed_safety | PASS | True | PASS | sì |
| input_safety | PASS | True | PASS | sì |
| truth_policy | PASS | True | PASS | sì |
| release_gate_fast | PASS | True | PASS | sì |
| semantic_equivalence | PASS | True | PASS | sì |
| tests | PASS | True | PASS | sì |
| performance_median_p95 | <=250ms | 244.9918 | PASS | sì |
| performance_preferred_latency | <=220ms | 244.9918 | PREFERITO NON RAGGIUNTO | no |
| performance_preferred_stability | >=5/7 under250ms | 4 | PREFERITO NON RAGGIUNTO | no |
| release_freeze | Dedicated commit after prerequisites | 68a3d7e31996a578b403f5bd815a06218b3a6e95 | PASS | sì |
| unknown_v3_sample | >=100;8sources;max25%;5types | {'total': 95, 'sources': 13, 'entities': 18, 'max_concentration': 0.21052631578947367, 'type_groups': 13} | FAIL | sì |
| unknown_v3_rejection | >=99% | non misurato | NON MISURATO | sì |
| unknown_v3_false_DOC_plus_FAMILY | <=1% | non misurato | NON MISURATO | sì |
| unknown_v3_entity_version | 0 | non misurato | NON MISURATO | sì |
| unknown_v3_freshness | No prior SHA or obvious near variant | non misurato | NON MISURATO | sì |
| v5_preflight | >=30IDs,6sources,400known,200scan,50filled,30unknown | non misurato | NON MISURATO | sì |
| v5_leakage | 0 | non misurato | NON MISURATO | sì |
| v5_precision | >=99.5% | non misurato | NON MISURATO | sì |
| v5_exact_recall | >=90% | non misurato | NON MISURATO | sì |
| v5_scan_precision | >=99.5% | non misurato | NON MISURATO | sì |
| v5_scan_recall | >=85% | non misurato | NON MISURATO | sì |
| v5_filled_generation | >=90% | non misurato | NON MISURATO | sì |
| v5_filled_precision | >=99.5% | non misurato | NON MISURATO | sì |
| v5_filled_recall | >=90% | non misurato | NON MISURATO | sì |
| v5_retrieval_at25 | 100% | non misurato | NON MISURATO | sì |
| v5_retrieval_at1 | >=99% | non misurato | NON MISURATO | sì |
| v5_entity_version | 0 | non misurato | NON MISURATO | sì |
| v5_unknown_mix | >=99% | non misurato | NON MISURATO | sì |
| family_identity_holdout | >=5 validated real families | experimental / insufficiently validated | PREFERITO NON RAGGIUNTO | no |
| CI | External matrix | external_pending | PENDING | no |

## Archivio e limiti

Verifica archivio: il primo tentativo ha rilevato una sola serializzazione preesistente, data/catalog_manifest.json CRLF nel workspace e LF nel Git originale. Workspace e freeze conservano SHA4649cf9029225906b0f881ac6c1cb6b4418b7cf417c5391b517fa371798eb7cc; il blob Git/ZIP ha SHA5c201eadfcf8fac96f85e7928a2beb8edebec3826689784693d8a39bbd14801d. JSON identico e blob ZIP esattamente uguale al Git precedente al Round16: eccezione limitata a quel file, nessun byte congelato modificato. Catalogo SQLite, runtime e dataset restano byte-identici. Audit e archivio del primo tentativo conservati.

Campione indipendente insufficiente: 95/100 casi obbligatori. Nessuna predizione avviata.; Evaluation v5 non eseguita: richiede il PASS di unknown v3. Prestazioni preferite non raggiunte; ambiguità storiche non risolte; family sperimentale; CI external pending. Archivio `dist/BurOCRazia-v0.7.0-candidate-NOT-READY-round16.zip`. SHA256 e verifica completa esterni al ZIP in `dist/package-verification-round16.json` e `.zip.sha256`. Nessun dato personale, cache, DB di lavoro o credenziale nel pacchetto.
