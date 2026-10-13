# Round15 — falso positivo confermato

L'adjudication ufficiale è stata completata prima del fix (hash e timestamp nel registro). Il solo caso confermato è U14-d6e51fa8e7f88431: bozza normativa ANAC distinta dal modulo A.7. I due INAIL restano ambigui e non motivano modifiche.

Entity evidence ANAC presente nell'intestazione e coerente con il catalogo. Versione/codice identificativo del modulo assenti; i numeri delle leggi citate non sono codici del modello. Titolo: il testo cita accesso ai documenti e legge241/1990 come oggetto del regolamento, non come identità della domanda individuale. Fingerprint: tier `insufficient_channels`, nessuna accettazione tecnica; il documento viene accettato dal fallback metadati con segnali titolo/ente/similarità generale. Nessuna shared-resource ufficiale con A.7. Il margine numerico del fallback non era registrato nei raw Round14 e non viene inventato o ricostruito retroattivamente. Le soglie e i margini della decisione restano invariati.

La regola `_informational_heading` riconosceva `Regolamento` soltanto all'inizio della riga. L'intestazione `Bozza di Regolamento` la aggirava. I token giuridici comuni potevano così diventare evidenza di identità specifica.

Fix: gli introduttori espliciti bozza/schema/proposta, con di facoltativo, conservano il ruolo dell'intestazione informativa. Finestra iniziale800 caratteri/prime6 righe invariata. Nessun ID, URL, ente, anno, soglia o peso aggiunto alla regola. Le domande che citano una bozza nel corpo e lo schema di domanda restano distinti. Fingerprint e canonici continuano a precedere il fallback. Test del caso ufficiale e differenziale full scan, test degli introduttori e dei controesempi. V2 può essere rieseguito soltanto come development, conservando label e risultato storico.
