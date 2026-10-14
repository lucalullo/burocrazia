# Continuità autonoma di BurOCRazia

Regola permanente richiesta dall'utente il 14 ottobre 2026. Il riferimento iniziale a NeuroTabular è stato corretto esplicitamente dall'utente: l'ambito è questo repository BurOCRazia.

## Ambito e autorizzazioni

Proseguire autonomamente analisi, test, benchmark, documentazione e modifiche sperimentali già autorizzate. Dopo un ciclo completato scegliere la successiva attività giustificata entro l'obiettivo concordato; non inventare un programma infinito o nuovi obiettivi scientifici. Un round che prescrive STOP NOT READY termina con prove, limiti e artefatti completi, senza aprire nuovi held-out o abbassare i gate.

Nessun commit, push, tag, pubblicazione, operazione distruttiva, servizio a pagamento o autorizzazione esterna implicita. Conservare working tree, indice Git originale, risultati negativi/positivi, dati grezzi pubblici, script, decisioni e checkpoint. Non acquisire nuovi permessi, consumare reset di quota o cambiare account/modello per aggirare un limite. Le istruzioni di sicurezza e i protocolli congelati continuano a valere.

## Meccanismi ufficiali verificati

La sessione espone `get_goal`, `create_goal`, `update_goal` e lo strumento ufficiale di pianificazione nella stessa chat. Il 14 ottobre 2026 è stato creato un Goal finito per completare il Round 20, verificare gli artefatti e predisporre questa continuità senza commit. La disponibilità del tool e il risultato positivo costituiscono prova locale; la presenza di un'opzione non dimostra un riavvio del servizio durante un outage.

I [Goals ufficiali](https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex) persistono nella singola chat e consentono continuazioni ai confini sicuri del turno, mentre obiettivo, budget e stato lo permettono. Non costituiscono memoria globale o garanzia di riaccensione dopo ogni arresto. Pausa, quota e interruzioni restano limiti effettivi.

Le [attività pianificate nella stessa chat](https://learn.chatgpt.com/docs/automations?surface=app) consentono un controllo periodico del checkpoint. Per file locali servono computer acceso, app in esecuzione e progetto accessibile; disponibilità e permessi dipendono dal servizio. Utilizzare una sola pianificazione di continuità per questa chat, senza duplicare esperimenti o Goal. Rimanere silenziosi quando lo stato non cambia; notificare completamenti, fallimenti o interventi necessari. Disattivare la pianificazione al completamento verificato o alla revoca dell'utente.

Retry automatici interni del servizio non sono configurabili tramite i tool esposti. Usare soltanto i retry effettivamente supportati. Per errori transitori di un'operazione idempotente, verificare prima l'esito e il checkpoint, poi utilizzare attese progressive e tentativi limitati; nessun replay di una valutazione single-shot già iniziata/conclusa fuori dal suo protocollo di resume. Non creare wrapper di richieste al modello, daemon esterni, cron di sistema o cicli che aggirino auto-review, quota o autorizzazioni.

## Checkpoint privati e storico

`.codex-context/` è esclusa da Git e dai pacchetti pubblici. Conservare un indice corrente `CHECKPOINT.json`, snapshot datati append-only in `history/` e una nota di ripresa. Ogni snapshot deve contenere:

1. Fase, obiettivo e criteri verificabili.
2. Ultimo passaggio completato, esperimento in corso e prossimo comando.
3. Branch, HEAD, elenco delle modifiche e degli artefatti con hash.
4. Processi/sessioni con PID quando disponibile, comando, log, timestamp e stato verificato. Un vecchio PID senza controllo della command line non prova che sia lo stesso processo.
5. Protocollo congelato, seed, dataset/profili, count/ID/hash previsti e held-out chiusi.
6. Errori tecnici, risultati negativi, tentativi preservati e condizione necessaria alla ripresa.
7. Stato Goal/pianificazione e loro limiti reali.

Aggiornare prima dei lavori lunghi, dopo ogni passaggio significativo e prima di un arresto quando il sistema permette ancora scritture. L'indice può cambiare; gli snapshot precedenti non si cancellano. Nessun testo personale caricato, credenziale o dato editoriale privato va inserito in artefatti pubblici.

## Procedura di ripresa

Leggere AGENTS.md, questo documento e il checkpoint. Eseguire `git status`, identificare branch/HEAD, esaminare le modifiche e gli ultimi risultati. Verificare processi, log, artefatti finali, expected count, ID unici e SHA prima di avviare altro. Se un job è attivo, seguirlo; se è completato, verificarne l'esito e passare al primo passo incompleto. Non usare reset, clean, checkout distruttivi o riscritture di risultati per ricominciare.

Se un journal consente resume, mantenere esattamente identità runtime/input/protocollo. In caso di identità diversa preservare l'esperimento e applicare la regola del relativo protocollo; i replay di sviluppo sono separati dalle evaluation indipendenti.

Se un'interruzione impedisce del tutto l'esecuzione, non dichiarare che il lavoro proseguirà sicuramente da solo. Registrare il primo passaggio incompleto e la condizione di sblocco. Una pianificazione ufficiale può tentare un controllo successivo soltanto quando app, quota, Goal e autorizzazioni lo consentono. Chiedere intervento umano solo per un'autorizzazione effettivamente necessaria o quando non esiste un percorso tecnico autorizzato.

## Packaging senza commit

Finché manca autorizzazione specifica al commit, creare eventualmente uno snapshot Git tree con indice temporaneo separato, senza cambiare l'indice originale o creare commit. L'archivio deve dichiarare HEAD di partenza, SHA del tree e stato non committato, e verificare i byte archiviati contro le misure. Non chiamare lo snapshot commit finale o release; non includere cache, checkpoint privati o database di lavoro.

## Stato effettivo osservato nei Round 21–22

Al completamento del Round 21 lo strumento ufficiale ha risposto che l'automazione oraria precedente non esiste più nell'app; non è stata ricreata a lavoro concluso. Il Round 22 utilizza un nuovo Goal ufficiale finito e checkpoint persistenti. Non è attivo un wakeup periodico dichiarabile. La disponibilità dello strumento di automazione resta distinta dall'esistenza di una pianificazione salvata; verificarne lo stato reale prima di attribuirle capacità di ripresa.

Il Round 22 riusa unknown v4 già concluso soltanto perché motore e hash semantici restano identici. Le sue nuove predizioni V6 hanno journal e freeze content-addressed separati; dopo la prima valutazione non si modifica motore, generatore, protocollo, selezione, label o seed. I replay post-V6 di canonical/safety e le sette misure warm sono verifiche espressamente richieste, non tuning. Un'eventuale interruzione riprende soltanto gli ID mancanti nello stesso journal, senza rieseguire unknown v4.
