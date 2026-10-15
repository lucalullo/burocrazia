# BurOCRazia — note per i contributori

Queste istruzioni seguono la relazione R2 e la distribuzione locale 0.6.1.

La candidata successiva conserva questi vincoli. La rete è ammessa soltanto negli strumenti separati `maintenance/` e nel runner ufficiale `benchmarks/files.py`, con `--allow-network` esplicito, robots e allowlist. Il runtime non li importa. I trasporti legacy restano disabilitati.

Conserva i corpus congelati e i loro hash; una correzione delle etichette richiede una nuova versione motivata. Misura separatamente regressione, copertura canonica, negativi, OCR sintetico con Tesseract reale e file ufficiali. I titoli/emittenti oltre i primi 2.000 caratteri non costituiscono prove forti di identità; la cache del motore contiene soltanto metadati del catalogo.

Round 2 conserva v1 e pubblica v2 con motivazioni esplicite; non sostituire le metriche v1 con quelle v2. Schema 610: osservazioni tecniche e prove di sostituzione sono aggiuntive e immutabili; non modificano automaticamente documento, provenienza storica o stato editoriale. Le date provengono dalle ricevute effettive, senza inventare eventi precedenti. Il percorso di riferimento full scan resta disponibile per i test differenziali; nessun testo caricato entra nelle cache.

- Mantieni l'applicazione locale e deterministica: nessun LLM, API esterna, telemetria, trasporto HTTP operativo, browser automation applicativa o autenticazione cloud.
- Conserva OCR locale, catalogo completo, identificativi, fonti, famiglie e provenienza. Non sostituire il progetto con una demo ridotta.
- Usa `run.py` per avviare su loopback. Non riattivare gli importatori live: i parser accettano soltanto fixture o input locali; gli aggiornamenti passano da pacchetti con anteprima/hash/transazioni.
- Separa estrazione, OCR, persistenza, riconoscimento e UI. Conserva i limiti su file/ZIP/pixel/pagine/testo/tempo e gli errori leggibili.
- Non inventare metadati o spiegazioni. Mantieni fatti ufficiali, spiegazione editoriale, lacune e revisione distinti. Non attribuire verifiche automaticamente.
- Privilegia il rifiuto prudente rispetto a documento/ente/annualità non sostenuti; registra diagnostica in sessione senza conservare il testo personale.
- Non fornire consulenza personalizzata. Il confidence score non è una probabilità.
- Tutto il testo proveniente da utenti, catalogo o pacchetti deve essere inerte nell'interfaccia: niente Markdown, link, HTML o risorse remote implicite.
- Revisioni e revoche richiedono autore e storico; i contenuti verificati cambiano soltanto con una nuova versione. Non inventare eventi pregressi.
- Non aggiungere file personali, database di lavoro, temporanei, credenziali o export editoriali a Git. Aggiorna lo snapshot pubblico soltanto con provenance e confronto delle righe.
- Esegui `python -m pytest -q`, verifica catalogo e benchmark dopo modifiche. Distingui test sintetici, OCR reale, validazione editoriale e collaudo su piattaforme.
- Non dichiarare completato un requisito privo di prova. Aggiorna documentazione e limiti della release quando il comportamento cambia.

## Continuità operativa permanente

Applica [CONTINUITA_OPERATIVA.md](docs/CONTINUITA_OPERATIVA.md). Prosegui le attività ordinarie già autorizzate senza conferme intermedie; mantieni checkpoint privati aggiornati in `.codex-context/` dopo ogni passaggio significativo e prima delle operazioni lunghe. A ogni ripresa verifica Git, processi, output e hash prima di eseguire, evitando duplicati e sovrascritture. Preserva anche tentativi negativi e protocolli congelati. Non promettere riprese dopo arresti o quote se il meccanismo ufficiale non le garantisce. Rispetta pause, held-out, quote e approvazioni; nessun aggiramento. Nessun commit, push, tag, pubblicazione, servizio a pagamento o operazione distruttiva senza autorizzazione specifica dell'utente. La conclusione scientifica NOT READY con gate invariati e prove complete è distinta da un'interruzione tecnica.

## Limite della preparazione locale RC

L’autorizzazione eccezionale al trasferimento e alla preparazione locale della RC termina con questa attività. Le successive modifiche autonome richiedono una nuova autorizzazione dell’utente. Nessuno staging, commit, push, tag, PR, merge o pubblicazione è autorizzato da questa preparazione; commit e push spettano all’utente tramite GitHub Desktop.
