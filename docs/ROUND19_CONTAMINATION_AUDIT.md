# Round19 — semantica prospettica della contaminazione

Questa policy precede la ricostruzione del pool e qualsiasi nuova predizione V5. V5 misura rappresentazioni nuove di documenti noti, con identità mai usate per calibrare il decision layer. Le sei fonti sono un requisito di diversità, non un source holdout.

`identity_seen_in_tuning` esclude la precisa identità usata in calibration/development del decision layer. Le prove sono collegate a corpus, piani e osservazioni; una storia di sviluppo non risolta resta esclusa con motivo distinto, senza dichiararla fresca. `representation_seen` esclude file/SHA e trasformazioni già osservate o usate nel tuning. Una identity altrimenti ammissibile richiede derivati nuovi: aggiungere solo metadata a una trasformazione identica non dimostra novità.

`historical_evaluation_seen` da solo non esclude. Le liste prospettiche e valutazioni storiche non usate nel tuning sono registrate separatamente dai risultati effettivamente entrati nei replay di sviluppo. Il registry v1 attribuiva tuning automaticamente a tutti i piani/evaluation; v2/v3 anche ai diagnostici storici e di equivalenza. Questi flag legacy e tutte le loro prove vengono conservati integralmente nella v4; l'ammissibilità usa la classificazione granulare, senza riscrivere v3.

`source_seen` e `source_specific_rule_tuned` sono flag di correlazione e stratificazione, non motivi per escludere tutte le identità di una fonte. `exact_identity_feature_built` indica le firme canoniche del prodotto e non costituisce tuning del decision layer. Verifica canonica tecnica e costruzione delle firme non attribuiscono revisione editoriale umana.

La fonte è esclusivamente il `source_id` storico del catalogo e della provenienza fingerprint. Nessuna divisione per hostname, ente, pagina o sezione. Il gate resta almeno30 identità e6 fonti; nessuna eccezione per raggiungerlo.

Controllo di identità correlate: SHA/URL comuni, campi AcroForm Jaccard>=.90 e aggregate>=.85 restano esclusioni prudenziali. Titoli/codici/versioni simili richiedono lo stesso emittente: un titolo amministrativo generico tra enti diversi non dimostra la stessa identità. La prima ricostruzione replicava il filtro globale Round18 e accostava Unioncamere616 ad ANAC611 soltanto per «Modulo richiesta accesso civico generalizzato», senza codice/versione o fonte comune. Questo falso collegamento è corretto prima di selezione/generazione/predizioni; il diagnostico iniziale e i suoi hash restano conservati. Il source_id del gate non cambia.

Per616: presente nel piano e nella generazione Round8, assente dalle50 osservazioni salvate e dai replay di calibration Round8/9; la sola firma canonica resta parte del prodotto. I dati617/618/619 Unioncamere modificati nel Round13 riguardano risorse condivise distinte, non regole tarate su616. Il risultato canonico tecnico di616 è corretto sul freeze corrente.

Per gli SHA si conserva l'unione registry v3, osservazioni storiche e ledger post-evaluation Round18. Il riuso esplicito di almeno30 unknown v3 nel mix è una verifica sullo stesso freeze, non un nuovo test unknown indipendente. La loro eccezione non si applica alle rappresentazioni note V5.
