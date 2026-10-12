# Round 7 — decision audit

Round6 evaluation è ora development. Tutti i 42 rifiuti rank 1 sono ricostruiti da byte verificati.

Cluster: `{"OCR score low": 13, "channel count requirement": 1, "identity veto too strict": 28}`.

Veto: `{"none": 14, "explicit_entity_conflict": 28}`.

Score per canale, evidenza ente/versione, margine e soglie nel CSV `benchmarks/results/round6/decision_rejections.csv`. Nessun testo OCR personale conservato.

## Round 7 — esito sviluppo

Replay effettivo: 155/192 contro 150/192. Decision policy v3, retrieval v2 con identica formula; il bundle attivo cambia per recuperi/quarantene. Campione R6 riclassificato development. Dettaglio per caso in `decision_audit_after.json`.

A: SHA identico e vincoli; B: testo con visual o caratteri/anchor; C: contenuto eccezionale e anchor d'identità; D: family già supportata o NO. Nessuna accettazione visual-only, soglie globali prossime a zero o margine nullo. I conflitti espliciti restano veto. SUAP destinatario e sottodipartimento MIMIT sono distinti dall'emittente. La revisione mancante può essere sostenuta da codice, titolo completo nella lingua iniziale e ente, soltanto per un'unica identità/revisione.

EX02/EX03 e EX02MISSINGREV/EX03MISSINGREV hanno testi identici ma expected opposti: gli hash e le etichette di entrambe le fixture restano invariati. Default CLI usa i 35 originali; la fixture37 resta visibile con i suoi fallimenti. Non esiste una decisione deterministica che soddisfi entrambe le etichette.
