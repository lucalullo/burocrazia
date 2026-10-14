# Round22 — audit del generatore

Audit25/25 fallimenti originali su cinquePDF statici: riquadri fissi larghi su prima pagina,nessun widget. Dati nel CSV,geometry JSON e immagini private. Policy v2 fissata prima della generazione; input20ID/5varianti e seed invariati. Nessuna recognition durante audit/generazione.

Nuovo risultato **100/100**,40native/60static,tutti60static con7valori verificati;0fallback effettivi (fallback malformato testato su fixture). Reopen/widget/valori/template/raster144DPI/SHA/parser/riferimenti controllati su ogni file. Sei campioni Poppler visualizzati: cinque vecchi casi problematici più native; nessun overlap/clipping del contenuto originale. Overlay in whitespace non rappresenta una compilazione semanticamente corretta. Vecchi75output e25failure restano intatti; tre normalized DOCX non riparati. Nessun resampling o cambioidentity.

Test iniziale1failure/10pass: URI inline annidato non rilevato,risolto prima dell'aggregazione con visita ricorsiva limitata; finale11pass. Recognition files hash prima/dopo uguali,decisionv7/catalogo/dataset immutati. Dopo freeze/primaV6 nessun cambiamento a generator o protocollo. V6 e ogni successiva metrica sono separati dalla generation success.
