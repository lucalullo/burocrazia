# Piano Round 4 — nessuna espansione eseguita

La candidata Round 3 conserva software 0.6.1, catalogo e revisioni. Il prossimo ciclo parte dagli esiti della prima misura holdout Round 3; quel campione diventa development e non può essere riutilizzato come prova indipendente dopo correzioni.

Prima priorità: correggere l'accettazione di famiglia R061 (locked v2, 68/69), introdotta dall'evidenza sul nome famiglia. Il freeze è stato effettuato prima che arrivasse questo risultato; non viene riaperto durante l'acquisizione/valutazione indipendente. Mantenere il negativo e richiedere evidenza distintiva oltre al nome ente. Release-fast resta fallito anche se locked v1 è soltanto storico.

La prima misura holdout Round 3 ha 33 esatti/127 positivi, cinque accettazioni errate (OH1-033/047/055/063/098), un errore ente e due versione; 50/50 negativi rifiutati. Precisione 86,84%, recall 25,98%, F1 40%. Questi fallimenti restano immutati in `benchmarks/results/round3/holdout_failures.json`; correggerli richiede un ciclo nuovo. Mancano 23 positivi e due fonti rispetto agli obiettivi; concentrazione 29,13%, oltre 25%. La revisione dei riferimenti incidentali e dei sottotipi non deve sfruttare questi file come nuovo gate indipendente.

1. Revisionare le sei attese improprie e l'ente aggregatore con autore, prove ufficiali e nuova versione di corpus; conservare i byte e le etichette storiche. Esaminare anche i tre gruppi identità e gli otto download condivisi prima di qualunque fusione.
2. Dare priorità ai rifiuti dovuti a emittente o versione non presenti. Separare produttore nazionale, ufficio destinatario e aggregatore senza inferire l'ente dalla sola fonte o l'anno dalla data del file.
3. Proporre famiglie dalle 123 opportunità: nome, emittente, fonti e anchor distintivi. Ogni famiglia candidata richiede almeno tre positivi e cinque negativi vicini indipendenti, revisione attribuita e storico; nessun cambio automatico a `verificato`. Non usare il nome di un ente come unica firma.
4. Migliorare ordine e leggibilità dei PDF con corpus tecnico separato, OCR locale reale, limiti invariati e diagnostica senza testo personale persistito. Misurare tempi di estrazione separatamente dal matching.
5. Congelare il nuovo motore prima di acquisire **official_holdout_v2**: obiettivo 150 positivi, 50 negativi, almeno otto fonti e concentrazione massima 25%, esclusione hash/identità/template/versioni da tutti i development precedenti. Prima valutazione unica, bootstrap per gruppi, stessi gate di precisione/recall e zero errori accettati.
6. Eseguire la matrice CI remota Linux/macOS/Windows soltanto quando autorizzato il push. Attualmente `pending_external_gate`; la sola sintassi YAML e Windows locale non sono collaudo multipiattaforma.

L'espansione resta subordinata ai gate: ADE/ADER/ADM, ACI/PRA, MIT/Portale, Interno/Prefetture, Salute, AgID, Polizia e altri tribunali richiedono nuove acquisizioni ufficiali autorizzate, senza bypass di blocchi. Nessuna espansione IPA o nuova fonte è stata eseguita nel Round 3.
