# Round15 — adjudication indipendente

Tre risorse distinte; i due dubbi INAIL sono inclusi nelle tre accettazioni. Decisioni basate sui contenuti e sui collegamenti ufficiali, completate prima di cambiare il motore. I segnali del riconoscitore servono soltanto alla successiva diagnosi.

| Caso | Esito | Motivo |
|---|---|---|
| U14-5f0c017c3d56e6c5 | ambiguous_truth | Modulo società partecipata pubblica, Anno2025, Allegato8 alla circolare36/2026; relazione annuale con record1147, versione catalogo nulla, canonico Anno2023. |
| U14-c1fc4765c01dcd62 | ambiguous_truth | Stesso sottotipo, Anno2024, Allegato5 alla circolare36/2026; l'equivalenza di identità tra annualità non è dimostrata. |
| U14-d6e51fa8e7f88431 | confirmed_unknown | Bozza di regolamento ANAC di17 pagine distinta dal modulo individuale A.7; non è un documento o una famiglia supportati dal catalogo. |

Fonti: [circolare INAIL36/2026](https://www.inail.it/portale/it/atti-e-documenti/note-provvedimenti-e-istruzioni-operative/normativa-circolari-inail/dettaglio.2026.08.circolare-n-36-del-7-ago-2026.html), [moduli INAIL del fondo](https://www.inail.it/portale/it/atti-e-documenti/moduli-e-modelli/assicurazione/moduli-prestazioni/prestazioni-economiche/fondo-vittime-amianto-lavoratori-di-societa-partecipate-pubblich.html), [pagina ANAC con allegati distinti](https://www.anticorruzione.it/-/accesso-civico-e-accesso-civico-generalizzato). Download, hash, titoli, ricevute e date effettive sono nei due JSON reference e official_truth_evidence.json. Le ricevute cache ANAC del12 ottobre restano tali: il403 del consultatore web non è aggirato e l'ispezione odierna non inventa un nuovo download.

**1 falso positivo confermato, 0 match esatti confermati, 2 ambigui.** Nessun errore di truth esatta è dichiarato dimostrato per INAIL; è dimostrato l'errore di qualificazione come confirmed_unknown senza risolvere la relazione annuale. Non si forza il motore a rifiutarli. La pagina testuale condivisa spiega tecnicamente il match ma non prova equivalenza tra annualità. Nessun evento di sostituzione o verifica editoriale aggiunto.

Reference truth v3 è aggiuntiva. Tutti i casi sono esclusi dai futuri gate indipendenti perché già osservati; i quattro oltre limite sono esclusi anche dal dominio di classificazione, con stato insufficiente per una decisione di riconoscimento. Il Round14 resta107/114, 3 DOCUMENT_MATCH, 0 FAMILY_MATCH, 4 errori: manifest, raw, label e metriche intatti. Il solo caso ANAC autorizza il fix generalizzabile dell'intestazione informativa.
