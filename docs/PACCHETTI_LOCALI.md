# Pacchetti locali e materiali consultabili

Il formato rimane versione 1 nella candidata del 11/10/2026. `maintenance/releases/2026-10-11/manifest.json` e `records.json` formano un pacchetto di soli metadati: inserirli alla radice di uno ZIP, poi eseguire la normale anteprima e confermare il suo hash. Le altre due schede JSON sono audit/risorse osservate, non membri aggiuntivi del pacchetto. Il nuovo seed non aggiorna automaticamente il database operativo. Il pacchetto conserva gli ID iniziali, non sostituisce righe già presenti e non attribuisce stati verificati.

BurOCRazia riceve aggiornamenti solo da file ZIP già presenti sul dispositivo. Non cerca nuove versioni, non scarica documenti e non esegue programmi inclusi nei pacchetti. Il catalogo resta fermo all'ultima importazione registrata. Gli URL sono dati di provenienza, consultabili come testo: non sono copie dei documenti e non vengono aperti dall'applicazione.

Il pacchetto `examples/pacchetto_demo.zip` contiene **un esempio interamente sintetico**, riconoscibile da fonte, documento e materiale in stato `demo`. Non riproduce un documento ufficiale e non estende la copertura reale. I file sorgenti leggibili si trovano in `examples/pacchetto_demo/`.

## Uso: anteprima e conferma

Inizializzare prima il catalogo seguendo il README. Poi, dalla radice del repository:

```bash
python scripts/import_package.py examples/pacchetto_demo.zip
```

L'anteprima non modifica database, registro importazioni o cartella dei materiali. Restituisce versione del formato/pacchetto/catalogo, SHA-256 dell'intero archivio, conteggi dei nuovi record e duplicati, nuove risorse e titoli privi di materiale locale. Un conflitto o una sostituzione non ammessa blocca l'anteprima con un errore esplicito. Il formato 1 supporta **aggiunte e riferimenti a record già esistenti**: non modifica, ritira o cancella implicitamente record.

Per applicare l'anteprima, copiare esattamente l'hash restituito:

```bash
python scripts/import_package.py examples/pacchetto_demo.zip --commit --expected-sha256 HASH_STAMPATO_DALL_ANTEPRIMA
```

Se qualsiasi byte dell'archivio cambia, incluso il manifest, il commit viene rifiutato. Le relazioni e i conflitti vengono ricontrollati nel database corrente sotto transazione: l'hash conferma i byte del pacchetto, non congela il catalogo. Il commit rifiutato registra soltanto il tentativo. La riapplicazione degli stessi byte non duplica record né eventi di revisione e non cambia la versione del catalogo.

Per usare un catalogo separato basta `--db`. È possibile scegliere anche una cartella base dei materiali al primo import:

```bash
python scripts/import_package.py pacchetto.zip --db percorso/catalogo.db --resource-root percorso/materiali
```

Dal primo commit riuscito con risorse, la cartella base assoluta viene registrata nel database (`catalog_metadata.local_resource_root`). Le successive importazioni, la consultazione e la revisione leggono quella configurazione, anche dopo il riavvio; non occorre ripetere `--resource-root`. Un'opzione esplicita diversa dalla radice già registrata è rifiutata, anche in anteprima. Senza configurazione si usa `data/local_resources`.

Per aprire lo stesso catalogo nell'interfaccia, impostare `BUROCRAZIA_DB_PATH` al percorso passato a `--db` prima di avviare `run.py`: la UI risolve la radice dal database selezionato. L'API condivisa è `resolve_resource_root(connection, root=None)`; `read_resource_text(resource, connection=connection)` usa la stessa risoluzione. Resta supportata la lettura esplicita `read_resource_text(resource, root)`.

Due cataloghi possono usare la medesima cartella base. Per i nuovi import la sottocartella deriva da SHA-256 dell'impronta del percorso database e dell'hash del pacchetto, quindi gli stessi byte hanno contenitori distinti nei due cataloghi. Il percorso memorizzato continua a essere relativo e mantiene i limiti precedenti. Lo spazio di nomi è stabile finché il percorso database resta lo stesso; non viene calcolato dal contenuto mutevole del database.

L'importazione operativa dei materiali richiede un database SQLite su file, come quelli usati da applicazione e CLI. Le connessioni SQLite esclusivamente in memoria possono eseguire l'anteprima, ma non pubblicare materiali: il commit è rifiutato prima di scritture a database o filesystem perché manca un'identità persistente del catalogo.

Le risorse della v0.6.0 conservano i loro percorsi e file: non vengono spostate, riscritte o eliminate per adottare il nuovo layout. Se erano nella radice predefinita, restano consultabili subito. Per registrare una radice personalizzata già usata, ripetere anteprima e commit dello stesso pacchetto con `--db` e `--resource-root`: l'operazione resta idempotente sui record e controlla che tutti i materiali registrati siano presenti e integri prima di ricordare la radice. Se erano distribuiti manualmente in più radici, il controllo fallisce esplicitamente: è necessario ricostruire e verificare una cartella coerente, senza sostituzioni automatiche.

## Formato 1

L'archivio contiene solo `manifest.json`, `records.json` e risorse `resources/*.txt` UTF-8. I nomi sono relativi, senza directory esplicite nel file ZIP, collegamenti simbolici o file speciali. I campi sconosciuti, le chiavi JSON duplicate e i file non dichiarati causano rifiuto. Le strutture complete di un pacchetto valido sono nell'esempio leggibile.

| Campo del manifest | Significato |
| --- | --- |
| `format_version` | Intero `1`: formato del pacchetto. |
| `catalog_schema_version` | Intero `1`: contratto di importazione del catalogo, distinto dalla versione software. |
| `package_id` | Identificativo stabile del pacchetto. |
| `package_version` | Versione immutabile di quel pacchetto. Stessa coppia ID/versione con byte diversi: rifiutata. |
| `catalog_version` | Etichetta del catalogo risultante, dichiarata dal curatore. Non viene interpretata come data o numero ordinabile. |
| `created_at` | Data/ora ISO di preparazione. |
| `producer` | Curatore dichiarato; non è una firma digitale. |
| `demo` | Booleano: distingue dati sintetici da dati da sottoporre a revisione. |
| `files` | Per ogni file escluso il manifest: `path`, `size_bytes`, `sha256` dei byte esatti. |
| `resources` | Inventario dei materiali consultabili e delle rispettive relazioni. |

Gli identificativi e le versioni usano da 1 a 80 caratteri ASCII fra lettere, cifre, punto, trattino e underscore; il primo carattere è una lettera o una cifra. Il manifest è coperto dall'hash dell'intero ZIP mostrato nell'anteprima. Non contiene un hash di se stesso.

`records.json` contiene tutte e sei le collezioni seguenti, anche quando vuote:

| Collezione | Destinazione | Identità e relazioni |
| --- | --- | --- |
| `sources` | `sources` | Ente e nome fonte. Nuove fonti non sono considerate verificate. |
| `entities` | `entities` | Codice IPA. Vietati enti demo nell'inventario reale. |
| `documents` | `documents` | Ente, versione e codice oppure titolo; `source_key` obbligatoria. |
| `families` | `document_families` | Fonte, ente e nome; fonte eventualmente assente. |
| `explanations` | `document_explanations` | Documento e versione; `document_key` obbligatoria. |
| `provenance` | `document_provenance` | Un record per documento; `document_key` e `source_key` obbligatorie. |

Ogni record ha una `key` univoca nella propria collezione. I riferimenti `source_key` e `document_key` rimandano alle chiavi del medesimo pacchetto, non a nomi di file o URL. Si possono usare record della forma `{"key": "fonte-esistente", "existing_id": 2}` per collegare un record già presente nel catalogo destinatario: l'ID deve esistere e non viene modificato. Questi riferimenti sono specifici di quel catalogo e devono essere controllati dal curatore nell'anteprima.

I nomi degli altri campi corrispondono a quelli del modello SQLite, riportati nelle costanti `FIELDS` e `REQUIRED` di `src/local_packages.py`; le colonne numeriche `source_id` e `document_id` sono sostituite dalle rispettive chiavi. Gli elenchi (`parole_chiave`, `keywords`, `facts_from_source`, ecc.) sono array JSON di stringhe. I campi facoltativi non disponibili vengono conservati come `null`; non vengono ricostruiti. Date `data_*` e `source_access_date` usano `YYYY-MM-DD`; timestamp usano ISO 8601.

Ogni nuovo documento richiede la provenienza nello stesso pacchetto, compresi i demo. Ente/fonte/documento/risorsa devono essere coerenti. Documenti e famiglie di enti o versioni differenti non vengono fusi per somiglianza. Un duplicato di identità è accettato soltanto se i dati coincidono; qualsiasi differenza richiede un intervento editoriale esplicito fuori dall'importatore. Un contenuto già verificato non viene sovrascritto.

`significato_semplice` nei nuovi documenti deve essere `null`: i contenuti editoriali appartengono a `explanations`. Nuove spiegazioni sono solo `bozza` o `da_verificare`, con almeno un fatto dalla fonte e senza `verified_by`/`verified_at`. Il pacchetto non assegna revisioni né attribuisce verifiche pregresse. Gli stati `verificato` e `rifiutato` delle risorse possono essere assegnati soltanto attraverso revisione umana tracciata.

Le spiegazioni applicano lo stesso validatore dell'editor: riferimenti appartenenti ai domini istituzionali supportati in `src/official_urls.py`, date valide e note di revisione entro 1000 caratteri. Un nuovo dominio richiede un'estensione esplicita della configurazione nel codice; il pacchetto non può ampliare autonomamente l'elenco dei domini ammessi.

## Materiali locali

Ogni elemento `resources` richiede `path`, `document_key`, `source_key`, `title`, `media_type`, `provenance`, `acquired_at`, `version`, `reuse_conditions` e `verification_status`. `version` può essere `null`; gli altri campi sono espliciti. `media_type` è soltanto `text/plain`. I materiali reali entrano come `da_verificare`; i sintetici come `demo`.

Includere soltanto testi la cui redistribuzione è consentita e documentarne le condizioni in `reuse_conditions`. Se i diritti non sono chiariti, mantenere il riferimento senza inserire il materiale. Il controllo automatico verifica struttura e integrità, non accerta il titolo giuridico né l'autenticità istituzionale. L'origine dichiarata deve essere verificata dal curatore.

La UI usa testo inerte, senza Markdown o HTML attivi: anche URL, tag e script presenti nei byte vengono mostrati come caratteri. Non vengono eseguiti né caricati. File PDF e HTML originali non sono incorporati nella visualizzazione; per il formato 1 il curatore prepara una rappresentazione testuale locale, ne dichiara trasformazione e origine e ne conserva le condizioni di riuso. BurOCRazia non promette fedeltà a un originale non incluso.

La lettura ricontrolla percorso, tipo, dimensione e SHA-256 rispetto al registro. File assenti, sostituiti o collegamenti simbolici sono rifiutati. Le risorse ritirate dopo revisione restano nel registro, ma la normale consultazione è bloccata. Il riesame esplicito controlla nuovamente i byte e conserva lo storico.

## Limiti e recupero

| Controllo | Limite |
| --- | --- |
| ZIP compresso | 20 MiB |
| File nell'archivio | 1000 |
| Totale espanso dichiarato | 50 MiB |
| Manifest o record JSON | 8 MiB ciascuno |
| Singola risorsa testuale | 2 MiB |
| Rapporto espansione/compressione | 100:1 |
| Record complessivi | 5000 |
| Elementi per elenco testuale | 100 |
| Percorso relativo finale | 240 caratteri, inclusa cartella SHA-256 |

Questi limiti sono prudenziali: anche un file legittimo molto comprimibile può essere rifiutato. Non sono supportati ZIP cifrati, archivi annidati, compressioni diverse da STORE/DEFLATE, file eseguibili, percorsi assoluti, `..`, backslash, nomi riservati Windows, symlink o file speciali.

Il commit apre una transazione SQLite `BEGIN IMMEDIATE`, ricontrolla e inserisce i dati, prepara i materiali in una cartella temporanea sotto il contenitore locale, sincronizza i byte e rinomina la cartella prima di registrare versione e operazione. Database, provenienza, risorse registrate e versione sono confermati nella stessa transazione. In caso di errore intercettato vengono annullati i dati e rimossi i file predisposti; rimane solo il tentativo fallito.

Database e filesystem non hanno una transazione distribuita. Se il processo si interrompe bruscamente prima del commit SQLite, possono restare cartelle orfane non visibili dal catalogo: il successivo import le elimina sotto blocco del database, solo se il marcatore le associa allo stesso percorso di database. Il recupero riconosce layout precedente e nuovo; una cartella appartenente a un altro database non viene eliminata e una destinazione già occupata da file non recuperabili causa rifiuto, senza sovrascrittura. Anche la configurazione della radice viene confermata nella transazione: un errore non lascia una configurazione parziale.

Se il database è stato spostato dopo l'interruzione, il recupero automatico non elimina le vecchie cartelle: ripristinare il backup o farle controllare manualmente. I materiali già registrati restano accessibili finché la radice assoluta registrata esiste; per un trasferimento su un altro computer occorre conservare database e cartella materiali insieme e verificare esplicitamente i percorsi. Non eliminare materiali registrati. Un danneggiamento del disco dopo un commit viene rilevato dalla verifica di lettura, ma richiede ripristino da backup.

`package_imports` registra le operazioni riuscite con ID/versione, formato, versione catalogo, hash, data e riepilogo. `package_import_attempts` registra commit riusciti, rifiutati e riapplicazioni; una semplice anteprima non scrive. Le date di pubblicazione, acquisizione, preparazione pacchetto, importazione e revisione sono distinte e non vengono aggiornate all'apertura dell'applicazione.

## Verifiche automatiche

```bash
python -m pytest tests/test_local_packages.py tests/test_review_audit.py tests/test_v061_resources.py -q
```

La suite esercita anteprima senza scritture, binding dell'hash, idempotenza, relazioni e provenienza obbligatorie, conflitti con record verificati, conservazione del catalogo, archivi ostili, rollback su errore DB/filesystem, recupero orfani e lettura con verifica dei byte. Le regressioni A05 verificano inoltre due database con base comune, la configurazione al riavvio e tramite CLI, compatibilità dei file v0.6.0, proprietà delle cartelle e assenza di interferenze in caso di errore. I test di revisione controllano decisioni manuali e tracciabilità dei materiali, inclusa la lettura dalla radice persistita.
