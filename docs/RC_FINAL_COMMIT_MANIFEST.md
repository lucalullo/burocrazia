# RC — manifest definitivo dei file per il commit manuale

## Esito del confronto Git

**SAFE TO COMMIT ALL VISIBLE RC FILES** — verdetto sul set di file locale, non autorizzazione a eseguire commit/push o prova di CI remota.

Fonte autorevole: `git ls-files` della sorgente validata. Nessuna classificazione dipende soltanto da estensione JSON, directory benchmarks o numero del Round. Sono creati esclusivamente questo documento e il manifest JSON richiesto; ogni file preesistente resta invariato.

## Repository osservati

| Ruolo | Cartella relativa alla home dell operatore | Branch | HEAD | Tracked |
| --- | --- | --- | --- | ---: |
| Sorgente validata | `Desktop/burocrazia` | `codex/coverage-benchmark-v0.7.0` | `21370532345effe7d117132bc6f3c77f02d66f4c` | 1636 |
| Destinazione | `Documents/GitHub/burocrazia` | `main` | `d747d0ff663bbf5ac89f5ba1de71d2cdce22018c` | 142 |

Osservazione UTC: `2026-10-15T05:39:56.067900+00:00`. Nessuna modifica staged in entrambi i repository.

## Partizione esatta dei 1496 untracked iniziali

| Insieme | File | Motivo |
| --- | ---: | --- |
| TRACKED_IN_SOURCE | **1485** | Gia versionati nella sorgente; percorso, blob Git e SHA verificati. |
| RC_NEW_INTENTIONAL | **11** | Funzione concreta e provenienza individuale documentate sotto. |
| LOCAL_ONLY | **0** | Nessun artefatto esclusivamente locale fra i 1496 visibili. |
| AMBIGUOUS | **0** | Nessun percorso visibile senza provenienza o funzione verificabile. |
| Totale | **1496** | Partizione disgiunta ed esaustiva dell elenco Git iniziale. |

TRACKED_IN_SOURCE completo contiene **1636 file**; **1485** e la sua intersezione con i soli untracked della destinazione. Il conteggio elevato deriva dal trasferimento della RC e della storia scientifica gia versionata nella sorgente a una destinazione che parte dalla stable.

## Set finale per il commit manuale

| Componente | File |
| --- | ---: |
| File gia modificati all ingresso | 32 |
| Untracked all ingresso | 1496 |
| Due manifest richiesti da questo controllo | 2 |
| Totale modifiche visibili finali da includere | **1530** |

**Di cui: 1517 gia tracked nella sorgente (1485+32), 13 nuovi RC intenzionali (11+2 manifest). Stato finale: 32 modificati, 1498 untracked, 0 staged.** I 110 file tracked e invariati della destinazione sono gia nel tree e non contano come nuove modifiche.

## Nuovi RC intenzionali: giustificazione individuale

| File | Funzione verificata |
| --- | --- |
| `benchmarks/reference/local_metadata_privacy_v1.json` | Dipendenza diretta di scripts/round20_common.py: lega SHA originali/portabili e protegge i campi storici non modificati. Riferimento: `scripts/round20_common.py:preserved; docs/HISTORICAL_SOURCE_PROOFS.md`. |
| `benchmarks/results/local_rc/git_status.txt` | Ricevuta storica pubblica collegata dal report RC; corrisponde esattamente agli array final_git_status del transfer audit. Non descrive lo stato Git attuale. Riferimento: `docs/RC_LOCAL_PREPARATION_REPORT.md; benchmarks/results/local_rc/transfer_audit.json`. |
| `benchmarks/results/local_rc/local_validation.json` | Ricevuta della validazione effettiva nella destinazione: 889 passed/0 failed/3 skipped e SHA verificato del log; non sostituibile con i risultati della sorgente. Riferimento: `docs/RC_LOCAL_PREPARATION_REPORT.md; reports/local-rc-full-tests.log (ignorato)`. |
| `benchmarks/results/local_rc/privacy_scan.json` | Ricevuta pubblica della scansione dei file trasferiti e dei 113 oggetti storici, con falsi positivi motivati; collegata dal report RC. Riferimento: `docs/RC_LOCAL_PREPARATION_REPORT.md`. |
| `benchmarks/results/local_rc/transfer_audit.json` | Manifest di provenienza del trasferimento selettivo: SHA, esclusioni e differenze intenzionali; ricostruisce la RC preparata nella destinazione. Riferimento: `docs/RC_LOCAL_PREPARATION_REPORT.md`. |
| `docs/HISTORICAL_SOURCE_PROOFS.md` | Documentazione pubblica della fixture storica e delle derivazioni portabili; spiega perimetro, hash e uso nei test senza importare history in .git. Riferimento: `tests/conftest.py; docs/RC_LOCAL_PREPARATION_REPORT.md`. |
| `docs/RC_COMMIT_FILE_AUDIT.md` | Audit pubblico richiesto nella precedente pulizia: elenco completo, hash, esclusioni puntuali e motivazioni; conserva la traccia delle decisioni. Riferimento: `Richiesta utente PULIZIA FINALE PRE-COMMIT; .gitignore`. |
| `docs/RC_LOCAL_PREPARATION_REPORT.md` | Rapporto pubblico della preparazione locale RC, con provenienza, validazione e riferimenti alle ricevute. Riferimento: `Preparazione locale RC autorizzata nella destinazione`. |
| `tests/fixtures/historical_git_objects/manifest.json` | Dipendenza diretta di tests/conftest.py: descrive 113 oggetti e 201 prove; vincola SHA del pack e dell indice. Riferimento: `tests/conftest.py; docs/HISTORICAL_SOURCE_PROOFS.md`. |
| `tests/fixtures/historical_git_objects/objects/pack/pack-db9cf576dde7d3f471f61d5df2f47d7392b34979.idx` | Fixture pubblica immutabile richiesta da manifest e tests/conftest.py per le asserzioni su sorgenti storici; SHA verificato. Non e una cache Git locale. Riferimento: `tests/fixtures/historical_git_objects/manifest.json; tests/conftest.py`. |
| `tests/fixtures/historical_git_objects/objects/pack/pack-db9cf576dde7d3f471f61d5df2f47d7392b34979.pack` | Fixture pubblica immutabile richiesta da manifest e tests/conftest.py per le asserzioni su sorgenti storici; SHA verificato. Non e una cache Git locale. Riferimento: `tests/fixtures/historical_git_objects/manifest.json; tests/conftest.py`. |

I due ulteriori metadati `docs/RC_FINAL_COMMIT_MANIFEST.md` e `benchmarks/results/local_rc/final_commit_manifest.json` sono richiesti esplicitamente da questo controllo e sono separati dai 1496 iniziali.

## Directory da includere fra i 1496 iniziali

Le righe contano soltanto i percorsi dell elenco Git iniziale. Non autorizzano a includere indiscriminatamente futuri file delle stesse directory. Il JSON elenca ogni percorso.

| Directory/gruppo | TRACKED_IN_SOURCE | RC_NEW_INTENTIONAL |
| --- | ---: | ---: |
| `(root)` | 3 | 0 |
| `.github` | 1 | 0 |
| `benchmarks` | 175 | 1 |
| `benchmarks/results/baseline_v061` | 4 | 0 |
| `benchmarks/results/candidate` | 5 | 0 |
| `benchmarks/results/local_rc` | 0 | 4 |
| `benchmarks/results/round10` | 38 | 0 |
| `benchmarks/results/round11` | 33 | 0 |
| `benchmarks/results/round12` | 16 | 0 |
| `benchmarks/results/round13` | 40 | 0 |
| `benchmarks/results/round14` | 38 | 0 |
| `benchmarks/results/round15` | 40 | 0 |
| `benchmarks/results/round16` | 72 | 0 |
| `benchmarks/results/round17` | 53 | 0 |
| `benchmarks/results/round18` | 59 | 0 |
| `benchmarks/results/round19` | 86 | 0 |
| `benchmarks/results/round2` | 17 | 0 |
| `benchmarks/results/round20` | 41 | 0 |
| `benchmarks/results/round21` | 61 | 0 |
| `benchmarks/results/round22` | 43 | 0 |
| `benchmarks/results/round23` | 2 | 0 |
| `benchmarks/results/round3` | 25 | 0 |
| `benchmarks/results/round4` | 37 | 0 |
| `benchmarks/results/round5` | 43 | 0 |
| `benchmarks/results/round6` | 53 | 0 |
| `benchmarks/results/round7` | 61 | 0 |
| `benchmarks/results/round8` | 66 | 0 |
| `benchmarks/results/round9` | 45 | 0 |
| `data` | 17 | 0 |
| `docs` | 80 | 3 |
| `maintenance` | 43 | 0 |
| `scripts` | 140 | 0 |
| `src` | 18 | 0 |
| `tests` | 30 | 3 |

## Confronto dei byte

Dei 1485 untracked gia versionati nella sorgente, **1478 sono byte-identici** e **7 hanno differenze intenzionali documentate**. Includendo i 32 modificati: **1503 identici e 14 differenti**. SHA delle due copie e motivazioni per ogni percorso sono nel JSON.

| Percorso differente | Motivo |
| --- | --- |
| `.gitattributes` | Attributi binari per la fixture storica portabile; differenza registrata nel transfer audit. |
| `.gitignore` | Quattro esclusioni puntuali della pulizia precedente; nessuna nuova esclusione in questo controllo. |
| `AGENTS.md` | Limite dell autorizzazione alla preparazione locale, registrato nel transfer audit. |
| `CHANGELOG.md` | Sezione RC nel formato originale della destinazione; documento approvato preservato. |
| `README.md` | Aggiornamento RC conservando il README italiano originale della destinazione; documento approvato preservato. |
| `README_EN.md` | Controparte inglese nel formato originale della destinazione; documento approvato preservato. |
| `benchmarks/results/round18/initial_validation_failure.json` | Replace unnecessary local temporary-directory operator identifier; no metric/label/protocol/result changed; SHA originale e portabile verificati nel reference dedicato. |
| `docs/BENCHMARK.md` | Contesto di preparazione locale e sezioni metodologiche conservate; differenza registrata nel transfer audit. |
| `docs/RELEASE_NOTES_v0.7.0-rc1.md` | Note RC nello stile della destinazione, secondo la richiesta documentale. |
| `docs/ROUND18_REPORT.md` | Replace unnecessary local temporary-directory operator identifier; no metric/label/protocol/result changed; SHA originale e portabile verificati nel reference dedicato. |
| `scripts/round18_finish.py` | Replace unnecessary local temporary-directory operator identifier; no metric/label/protocol/result changed; SHA originale e portabile verificati nel reference dedicato. |
| `scripts/round20_common.py` | Validate explicit portable note derivative against unchanged original baseline hash and unaffected historical fields; all other SHA checks unchanged; SHA originale e portabile verificati nel reference dedicato. |
| `scripts/round8_baseline.py` | Optional explicit prompt environment path replaces an operator-specific hardcoded location; no recognition change; SHA originale e portabile verificati nel reference dedicato. |
| `tests/conftest.py` | Lookup degli oggetti storici limitata al processo test, con verifica SHA della fixture; differenza registrata nel transfer audit. |

La derivazione del diagnostico Round18 modifica solo temp_note: tutti gli altri campi JSON sono identici. Le ricevute di portabilita/trasferimento e gli SHA della fixture storica corrispondono ai byte osservati. Nessun motore, policy, catalogo, test, metrica o risultato congelato V6/unknown v4 viene modificato in questo controllo.

I quattro file dal nome checkpoint dell audit precedente sono TRACKED_IN_SOURCE e byte-identici: journal scientifici storici pubblici, non checkpoint privati. Pack/idx sono fixture vincolate da SHA, non cache o copia della directory .git. Il catalog_seed.sqlite3 gia tracked e il seed pubblico della RC, non un database operativo.

## File da escludere: insieme separato dagli untracked

**436 file fisici gia ignorati**, tutti lasciati intatti; nessuna nuova regola .gitignore. LOCAL_ONLY non implica cancellabilita: anche log e checkpoint possono essere evidenze locali da preservare.

| Classe locale | File |
| --- | ---: |
| `DERIVED_LOCAL_PROJECTION` | 3 |
| `LOCAL_DELIVERY_ARCHIVE` | 2 |
| `LOCAL_REPLAY_OUTPUT` | 7 |
| `LOCAL_VALIDATION_LOG` | 7 |
| `OPTIONAL_REVERSE_INDEX` | 1 |
| `PRIVATE_CHECKPOINT` | 12 |
| `PYTHON_BYTECODE` | 400 |
| `TEST_CACHE` | 4 |

Esclusioni: bytecode nelle directory __pycache__; `.pytest_cache/`; `.codex-context/`; `benchmark-release-results/`; `reports/`; ZIP/sidecar in `dist/`; le tre proiezioni `benchmarks/results/local_rc/documentation_consistency.json`, `recognition_freeze_verification.json`, `version_consistency.json`; il solo `.rev` della fixture storica. Elenco esatto e motivazione per ogni file nel JSON.

Fra i 1496 untracked non compaiono PDF/DOCX/JPG/PNG ufficiali, ZIP, credenziali, file personali o database operativi. I due soli binari untracked sono pack e idx della fixture documentata. Venv, cache download, raw corpus ufficiali, database di lavoro e checkpoint privati restano fuori dal set.

## Stato della sorgente e file non trasferiti

Round20/21/22 non hanno untracked nella sorgente: i loro file necessari sono gia tracked. La sorgente conserva tre report Round23 modificati e sei aggiunte untracked riferiti al proprio branch di ricerca. Sono registrati nel JSON, preservati e non copiati nella destinazione; non entrano nei 1496.

Nove percorsi tracked della sorgente non esistono nella destinazione: audit operativi Round23 e helper di pubblicazione della copia di ricerca, gia esclusi nel transfer audit. Il confronto non propone di importarli solo perche tracked.

## Verifiche e limiti

Il JSON contiene gli output Git richiesti e gli inventari SHA. Controlli alla creazione: partizione esatta; tutti i file preesistenti nelle due copie invariati; HEAD/branch/ref/configurazione/indice invariati; soltanto due nuovi manifest; nessun file staged; `git diff --check` senza errori.

I test non sono rieseguiti per questo audit: la ricevuta precedente riporta 889 passed/0 failed/3 skipped e il relativo SHA del log e verificato. Nessuna nuova valutazione V6/unknown v4, misura, richiesta di rete o verifica CI remota. Le ricevute precedenti mantengono i loro conteggi storici (1499 al trasferimento): questo manifest e il riferimento corrente.

Nessun git add, commit, push, tag, release, merge, reset, cancellazione o operazione remota eseguito.

[Manifest JSON completo](../benchmarks/results/local_rc/final_commit_manifest.json)
