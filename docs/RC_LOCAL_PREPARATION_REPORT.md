# Preparazione locale BurOCRazia — REPOSITORY READY FOR MANUAL COMMIT/PUSH

## Repository e Git

Repository locale collegato a `https://github.com/lucalullo/burocrazia.git`, branch **main**, HEAD **d747d0ff663bbf5ac89f5ba1de71d2cdce22018c**. Branch, history, remote/configurazione e voci dell'indice sono rimasti invariati. La directory `.git` della copia di riferimento non è stata copiata; nessun ref o commit è stato importato nella destinazione. Il diff è fisicamente presente in questo working tree e visibile a GitHub Desktop.

## Sincronizzazione selettiva

Confrontati1636 file della copia validata: **1512 trasferiti**, **111 già identici**, **13 esclusi o aggiornati nel formato della destinazione**. I README, il CHANGELOG e le release notes della destinazione non sono stati sovrascritti con quelli della copia di ricerca. Confronto per file/SHA e motivazioni nel [transfer audit](../benchmarks/results/local_rc/transfer_audit.json).

Esclusi venv, cache Tesseract/Codex/runtime e risorse, PDF/DOCX/immagini ufficiali scaricati, temporanei, database operativi, log, checkpoint privati, credenziali/env/auth e archivi dist della copia di riferimento. Il seed pubblico necessario alla RC è trasferito con provenance e hash; LICENSE resta identica. Il fingerprint v3 di circa52MB è un indice runtime intenzionale già validato, non un corpus ufficiale.

Differenze residue intenzionali: documentazione conservata nello stile della destinazione; fixture storiche portabili e relativo setup test; attributi binari per pack/indice; metadata operativi resi portabili con derivazione versionata; limite dell'autorizzazione locale in AGENTS.md. Nessuna differenza residua nei file recognition o nel codice misurato. Le prove storiche sono spiegate in [HISTORICAL_SOURCE_PROOFS.md](HISTORICAL_SOURCE_PROOFS.md).

## Candidate e recognition

Versione **0.7.0-rc1**, schema **610**, stable pubblica **v0.6.1**. Recognition v7 invariato dopo il trasferimento: **PASS**. Hash recognition `c077552055c25b0bc128e1a5c607afc434fb3bd074e6da165f3d8333145abf15`; hash dell'intero codice misurato identico al freeze. Tutti i215 file congelati, gli input recognition, catalogo/profili/fingerprint e le osservazioni V6/unknown v4 coincidono. Nessun tuning o replay dei due single-shot.

Metriche congelate: V6 exact560/597, precisione100%, recall93,80%, scan93,33%, filled generation100/100 e filled recall95%; retrieval@1 99,33%, @25 100%; unknown v4 120/120; errori ente/versione0/0; canonical1007/1007; safety705 negativi/0FA; coverage86,53%; mediana di sette p95 warm186,09ms. Prove RC locali, non certificazione. Family matching sperimentale/insufficientemente validato.

## README IT/EN e documentazione

Coerenza **PASS**: stessi valori nelle tabelle, stessa versione/limiti/funzioni, comandi equivalenti e link reciproci originali. Titoli, ordine, stile, esempi e sezioni dei due README sono conservati; nessun badge o nuova struttura introdotto. Aggiornati soltanto catalogo, fingerprint/UI, prove RC, limiti pertinenti e dipendenza necessaria ai test. I dati RC sono nella sezione Validazione esistente. La cronologia originale del CHANGELOG è immutata: aggiunta soltanto0.7.0-rc1 nel formato esistente.

BENCHMARK conserva integralmente le sezioni storiche e distingue V5 originale, development/tuning, unknown v4, V6 indipendente, canonical, safety e performance. Release notes concise, coerenti con README/CHANGELOG, senza percorsi personali, debug o istruzioni operative interne.

## Validazione nel repository corretto

**889 passed, 0 failed, 3 skipped**, **659,14s**. Tre skip Windows per symlink senza privilegio e FIFO. Anche i test storici eseguono le asserzioni originali usando le fixture pubbliche verificate: nessun nuovo skip o indebolimento delle prove.

Compileall, SQLite integrity/FK, doppia migrazione idempotente a610/conteggi invariati, schemi benchmark, versione, confronto frozen canonical1007/1007 e safety705/0FA: **PASS**. Validatori fingerprint v1/v2/v3, compat-v2 e adattatore CI locale: **PASS**. Quest'ultimo conserva tutti i mismatch storici originali e fallisce su qualsiasi esito diverso; non equivale a GitHub Actions verde. CI remota non eseguita né interrogata in questa attività.

## Pacchetto locale

Verifica **PASS**, **1633 membri**, SHA256 `f3aa84fa5b9cbb1850b48c22792382fbae3078e178aef3fbc82154e6cea3a383`. Ogni membro è confrontato con i byte correnti della destinazione e tutti gli hash congelati; CRC e unicità dei nomi validi. Il pacchetto è uno snapshot fisico non committato, non un archivio di un commit Git. Runtime, dati, test, prove storiche e documentazione pubblica sono inclusi. Il report finale e le ricevute di consegna `local_rc/` sono esterni all'archivio per evitare hash circolari; non sono componenti runtime mancanti. Il pacchetto e il sidecar rimangono locali e ignorati in dist, senza upload.

## Privacy

**PASS: confirmed secrets0, improper local paths0, dati privati inutili0**. Ispezionati anche tutti i113 oggetti delle fixture storiche decompresse. Otto segnalazioni classificate: sette riferimenti a href malformati già pubblicati da una fonte istituzionale, conservati come provenance immutabile di fetch rifiutati e mai aperti; una password esclusivamente sintetica usata per il PDF cifrato di un test già pubblico. Nessuna credenziale reale. Riferimenti operativi personali rimossi con ricevuta versionata, senza cambiare risultati o label. [Scan completo](../benchmarks/results/local_rc/privacy_scan.json).

## Git status finale

**32 modificati, 1499 non tracciati, 0 staged**. Elenco esatto integrale nel [git_status.txt](../benchmarks/results/local_rc/git_status.txt) e negli array `final_git_status` del transfer audit. Tutte le nuove modifiche sono nel working tree corretto; nessuno staging nuovo o precedente.

File modificati:

- `.gitattributes`
- `.github/workflows/tests.yml`
- `.gitignore`
- `AGENTS.md`
- `CHANGELOG.md`
- `DATA_NOTICE.md`
- `README.md`
- `README_EN.md`
- `app.py`
- `data/acquisition_plan.json`
- `data/catalog_manifest.json`
- `data/catalog_seed.sqlite3`
- `docs/INSTALLAZIONE_OFFLINE.md`
- `docs/PACCHETTI_LOCALI.md`
- `docs/PROVENIENZA_E_DISTRIBUZIONE.md`
- `docs/VALIDAZIONE.md`
- `pyproject.toml`
- `scripts/benchmark.py`
- `scripts/verify_catalog.py`
- `src/database.py`
- `src/extract.py`
- `src/models.py`
- `src/official_urls.py`
- `src/recognize.py`
- `tests/conftest.py`
- `tests/test_acquisition_plan.py`
- `tests/test_benchmark.py`
- `tests/test_database.py`
- `tests/test_offline_runtime.py`
- `tests/test_review_audit.py`
- `tests/test_v061_recognition.py`
- `tests/test_windows_database_lifecycle.py`

I file non tracciati comprendono i nuovi sorgenti/profili/catalog metadata, harness e risultati storici pubblicabili necessari alla riproducibilità, test e fixture, documentazione RC e ricevute. Ogni percorso è elencato integralmente nel file di stato collegato, senza includere file ignorati.

## Operazioni non eseguite e prossimo passo

Nessun git add, commit/amend, push, tag, PR, release/pre-release, merge, force push o operazione remota. Nessuna modifica della stable v0.6.1. Le operazioni svolte in precedenza nella diversa copia di ricerca non sono state ripetute o annullate qui.

**Commit e push manuale tramite GitHub Desktop.** L'autorizzazione eccezionale termina con questa preparazione: successive modifiche autonome richiedono nuova autorizzazione dell'utente. Il checkpoint privato conserva lo stato senza abilitare pubblicazioni o continuazioni non autorizzate.
