# Acquisizione tecnica separata dal runtime

Riferimento: 11 ottobre 2026. L'applicazione avviata con `run.py` resta locale; i trasporti degli importatori legacy restano disabilitati. Nessun codice di rete di `maintenance/` viene importato dall'app. Il seed non sostituisce un database operativo già presente.

## Ripetere un censimento

```powershell
python -m maintenance.acquire --source inps
python -m maintenance.acquire --allow-network --source inps --output maintenance/staging/inps.json
```

Il primo comando stampa il piano e non tenta rete. Il secondo usa HTTPS verificato, User-Agent trasparente, robots, almeno un secondo tra richieste, timeout di 12 secondi, un solo retry per errori di trasporto, massimo cinque redirect, 8 MiB per risposta e 400 richieste per sessione. Ogni redirect è validato prima di seguirlo. 403/429 fermano la fonte, senza proxy, cambio di identità o bypass. Le challenge HTTP 200 non sono raccolte vuote. Un totale INPS incoerente, una pagina ripetuta o una fine anticipata impediscono lo stato di raccolta completa.

`maintenance/sources.json` dichiara raccolte e prefissi ammessi; non è un crawler generale. Le raccolte dichiarate sono più strette dell'intera attività dell'ente. INPS è esaurito rispetto al totale italiano dichiarato dal server; l'indice INAIL è attraversato ricorsivamente soltanto sotto `moduli-e-modelli`; Venezia copre il solo elenco Moduli per cittadini. MIMIT copre le sezioni radio e servizi alle imprese. La Funzione Pubblica copre i nove moduli commerciali/turistici individuati, non tutta l'edilizia nazionale.

## Parser e input locali

Fetch e parsing sono separati. `maintenance.parsers.parse(raw_bytes, source, receipt)` lavora anche su HTML/JSON ufficiale salvato manualmente, senza rete. La receipt deve dichiarare URL ufficiale, data effettiva di acquisizione e SHA-256 dei byte. Per ADE/ADER/ADM bloccate è disponibile questo percorso locale e restano disponibili i parser legacy per fixture/input locali. Un HTML fornito manualmente non costituisce, da solo, prova di autenticità del contenuto.

Tier A: allowlist per ente con confini di dominio, HTTPS, niente credenziali, IP o porte arbitrarie. L'infrastruttura `t-acigov.serviziaci.it` è documentata dai collegamenti dell'indice ACI; non è stata acquisita quando irraggiungibile. Tier B: `validate_url(..., 'ipa_territorial', ipa_site=...)` verifica il sito IPA dell'ente e i suoi sottodomini, senza concedere fiducia a domini somiglianti. Nessun nuovo modulo territoriale IPA è stato importato: le priorità nazionali hanno ancora blocchi e perimetri incompleti.

## Deduplicazione e pubblicazione

Titolo, ente, codice esplicito e versione distinguono le identità. PDF/DOCX e traduzioni INL diventano risorse alternative; un codice INL comprende i suffissi. Un'osservazione senza versione non crea una copia del record storico con lo stesso titolo/codice/file. Una revisione esplicita diversa può creare una nuova identità. Non si inferiscono revisioni da anni di leggi. Manuali, istruzioni, direttive, elenchi e allegati senza titolo identificabile sono esclusi. Le etichette di sezione derivate dalla posizione HTML restano nell'audit, senza essere inventate come categorie ufficiali.

`python -m maintenance.build_catalog --baseline PERCORSO --reports REPORT1 REPORT2 --output maintenance/staging/NUOVO` rilegge i byte con hash, crea il pacchetto, esegue anteprima/applicazione transazionale su una copia, controlla idempotenza e tutte le impronte storiche. `maintenance.publish_snapshot` è dry-run finché non si passa `--apply`; valida continuità, URL, provenienza, integrità e FK prima di pubblicare il seed. Non apre il database operativo.

Il pacchetto riproducibile contiene `manifest.json` e `records.json`, senza file ufficiali. Per un'installazione esistente, creare uno ZIP con questi due file e usare il normale importatore locale con anteprima/hash. I file del pacchetto devono avere quei nomi alla radice. `docs/PACCHETTI_LOCALI.md` descrive il formato invariato.

## Limiti osservati

Nessuna cancellazione, revoca o sostituzione automatica dello storico. Un file non scaricato non ha un hash di contenuto: gli hash delle risposte di elenco sono separati dai file. Le lingue sono classificate soltanto dove esplicitate. Non sono state verificate equivalenze sostanziali fra tribunali diversi. Mancano una revisione editoriale umana, un censimento territoriale IPA e diversi procedimenti nazionali; `SOURCES.md` elenca blocchi e raccolte manuali. Cache, staging, PDF/DOC e testo estratto non entrano in Git.

## Storico Round 2

Schema 610 conserva osservazioni tecniche immutabili e relazioni di sostituzione con autore/prova; nessuna sostituzione è stata dedotta. `maintenance.record_observations` rigioca offline ricevute reali in staging; `maintenance.publish_history_snapshot` confronta le righe prima della pubblicazione. `maintenance.quarantine_round2` prepara i rifiuti tecnici documentati di #429 e delle FAQ #1077/#1081/#1091. Nessuna verifica umana automatica. Il seed non sovrascrive il database operativo esistente: eventuali decisioni locali devono passare dalla revisione con autore e storico. La nuova espansione è sospesa finché i gate restano aperti.
