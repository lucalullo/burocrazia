# Prove storiche dei sorgenti

Alcuni test confrontano byte o AST di commit storici, per proteggere le garanzie originali dopo successive modifiche autorizzate. Una copia della stable ha una history diversa dalla copia di ricerca: i commit necessari possono non essere raggiungibili. Saltare quei controlli o sostituire i sorgenti storici con quelli attuali indebolirebbe le prove.

`tests/fixtures/historical_git_objects/manifest.json` descrive 201 richieste di sorgenti e 113 oggetti pubblici commit/tree/blob, esportati selettivamente in un pack di circa22MB. Contiene soltanto sorgenti originali del progetto, snapshot pubblici del catalogo, fingerprint, profili e truth già pubblicabili; nessun corpus ufficiale PDF/DOCX/immagini, database operativo, credenziale o file personale.

Prima dei test `tests/conftest.py` verifica gli SHA256 del pack e dell'indice e configura una lookup Git alternativa limitata al processo di test. Git verifica gli identificativi degli oggetti; le asserzioni storiche su byte/AST rimangono invariate. Nessun oggetto, ref, branch o commit viene importato nella directory `.git` della destinazione. Nessuna dipendenza dal percorso della copia di ricerca o da una connessione di rete.

Le sole ulteriori derivazioni di portabilità sono registrate in `benchmarks/reference/local_metadata_privacy_v1.json`: eliminazione del nome della directory temporanea dell'operatore nelle note diagnostiche e sostituzione di un percorso personale al prompt con input opzionale esplicito. Hash originali e derivati sono distinti. Il controllo storico conserva il parent hash e verifica tutti i campi non modificati; non sostituisce label, metriche o risultati. Gli originali rimangono preservati nella copia di riferimento.

Motore v7, tutti i215 file del codice misurato, catalogo, profili e risultati V6/unknown v4 restano byte-identici al freeze. Le fixture rendono portabili le prove storiche e non costituiscono nuovo tuning o nuove valutazioni indipendenti.
