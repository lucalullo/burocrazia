# Firme di riconoscimento — fingerprint-v1

Il bundle `data/document_recognition_fingerprints.json` aggiunge conoscenza tecnica alle identità esistenti. Non cambia documenti, provenienza storica, revisioni editoriali o schema SQLite 610. Il catalogo pubblico e i suoi hash restano invariati. La compatibilità dei vecchi snapshot e le migrazioni già esistenti sono provate separatamente; non è necessaria una migrazione 611 perché non vengono aggiunte tabelle.

## Build e provenienza

`python -m maintenance.build_fingerprints` opera offline sulla cache verificata. `--allow-network` abilita esplicitamente il manutentore HTTPS con allowlist, robots, limiti di dimensione, richieste, redirect e tempo. `--source` limita le fonti per una sessione. Un diniego robots riguarda il percorso; HTTP 403/429 blocca l'host nella sessione. Dopo tre risposte non documentali il manutentore interrompe gli ulteriori tentativi su quell'host e registra questo limite, senza aggirare challenge. La cache precedente viene riutilizzata soltanto dopo verifica di ricevuta, dimensione e SHA. Il runtime non importa il manutentore.

Ogni record contiene identificativo documento e fonte, SHA canonico, MIME, numero pagine PDF, metodo di estrazione, data effettiva di acquisizione e generazione, parametri e conteggi, stato e legame crittografico con i metadati del record. Il numero pagine DOCX è sconosciuto (`null`), perché non viene inventata un'impaginazione. Il manifest `benchmarks/manifests/official_fingerprint_cache_v1.json` contiene URL, URL finale, SHA, dimensione, MIME, date e condizioni di riuso, senza percorsi locali.

L'output è validato prima e dopo la scrittura temporanea; `fsync` e sostituzione atomica pubblicano l'intero bundle. La versione precedente viene salvata nella cache ignorata. Il build ordinario conserva `generated_at` per firme identiche ed è idempotente byte per byte. `--rebuild` rigenera esplicitamente le firme. Il catalogo non viene modificato. File con emittente/sottotipo incompatibile, hash assegnato a identità diverse o etichetta negativa congelata incompatibile richiedono accertamento editoriale e non ricevono una firma attiva. Non c'è fusione automatica.

## Rappresentazione minimizzata

Si applicano Unicode NFKC, casefold, ricomposizione delle parole spezzate con trattino a fine riga, separazione della punteggiatura e trattamento circoscritto delle lettere OCR spaziate. Le righe ripetute vengono rimosse soltanto ai confini espliciti di pagina; le ripetizioni dei campi all'interno della stessa pagina restano valide. Se l'estrattore non conserva il separatore di pagina, non si presume di conoscere header e footer ripetuti.

Sono disponibili due stream temporanei: lessicale, con numeri lunghi non annuali mascherati, e sensibile a codici/versioni, con tutti i numeri conservati. Anni e codice 730 non vengono cancellati dal lessicale. I token non sono salvati. Ogni shingle di quattro token viene hashato con SHA-256 troncato a 128 bit e prefisso di dominio/versione. Non viene usato `hash()` Python. Il testo è limitato a 50.000 token per stream: la coda non viene usata per la fingerprint.

Si salvano al massimo 512 hash lessicali bottom-k, 128 hash dello stream numerico, 256 hash dell'intestazione nei primi 2.000 caratteri, 64 anchor hash da righe brevi e 128 hash di nomi di campi. Le anchor sono sequenze funzionali di quattro token, senza frasi pubblicate. I campi PDF sono letti dai widget; quelli DOCX da controlli strutturati e campi legacy, dopo validazione ZIP/XML. La versione, l'ente e il legame con codice/titolo/fonte sono hashati; il catalogo contiene già i metadati ufficiali leggibili. La derivazione dei campi è un segnale diagnostico aggiuntivo: il percorso UI corrente usa SHA e contenuto, senza una seconda apertura del file per estrarre i nomi dei campi.

`fingerprint-v1` identifica tokenizer, normalizzazione, shingle, algoritmo hash, dimensioni e derivazione anchor. Una modifica successiva di questi parametri richiede una nuova versione; i correttivi fatti durante lo sviluppo iniziale di questo round precedono la pubblicazione del primo bundle v1. Schema JSON e validatore runtime rifiutano versioni/chiavi sconosciute, duplicati, array/hash non validi, quantità e percorsi oltre i limiti. Non viene distribuito testo ufficiale, immagini, PDF o DOCX.

## Retrieval e metriche

L'indice invertito mappa hash lessicali/intestazione a tuple di document ID. Non tronca una top-N: mantiene tutti i candidati con almeno 16 hash condivisi. Il riferimento full scan visita tutte le firme e permette il controllo differenziale. L'indice e le cache contengono solo il bundle pubblico e metadati del catalogo; nessun upload o derivato di upload viene conservato.

Siano H(A) gli shingle distinti canonici, S(A) i k hash minori e H(B) gli hash del testo caricato. La stima di containment canonico è c = |S(A) ∩ H(B)| / |S(A)|. Lo hash crittografico fornisce un ordinamento deterministico assimilabile a un campionamento uniforme, senza garanzia statistica sul singolo modulo. La stima Jaccard è c·|H(A)| / (|H(A)| + |H(B)| − c·|H(A)|). Il bottom-k Jaccard aggiuntivo usa l'intersezione dei due sketch nel campione bottom-k della loro unione. Queste stime non sono probabilità di identità.

Per attenuare template comuni, ciascun hash ha peso 1/df(h), dove df è il numero di identità nel catalogo fingerprinted. L'overlap pesato è la somma dei pesi degli hash canonici osservati divisa per la somma dei pesi dello sketch canonico. Si riportano anche containment dell'intestazione, anchor e campi. Il containment dell'intestazione permette una prima pagina o un documento parziale senza presumere che tutte le pagine siano presenti.

La regola iniziale v1 richiede almeno 24 hash condivisi, containment e overlap pesato almeno 0,80 e intestazione almeno 0,65 oppure anchor almeno 0,80. Il percorso per sottoinsiemi richiede intestazione almeno 0,90, almeno 32 hash condivisi e almeno 80 token dell'upload. I candidati devono avere margine almeno 0,08 sul punteggio tecnico. Questi valori sono regole deterministiche iniziali, non soglie calibrate su una popolazione né probabilità. Le collisioni artificiali non consentono di accettare un documento sulla base di un solo hash; hash/file condivisi tra identità sono ambigui.

## Decisione e vincoli

La UI applica prima limiti, validazione ed estrazione del file. Solo allora passa il suo SHA a `recognize_catalog`. L'API testuale con `file_sha256` presuppone questo contratto: non è un'interfaccia per autenticare hash dichiarati dall'utente. Il percorso SHA restituisce `official_file_sha256_exact` per un solo record operativo e coerente con il catalogo. Non misura generalizzazione.

Segue la shortlist per contenuto, con reason `content_fingerprint_match`. Ente esplicito incompatibile, qualificatori esclusivi, numero allegato e versione leggibile incompatibile restano bloccanti. Per una firma annuale senza anno leggibile la somiglianza non basta: si torna a famiglia o NO_MATCH. Per revisioni semantiche è necessaria una revisione esplicita corrispondente. Lo SHA canonico può risolvere un anno assente, senza superare una contraddizione esplicita. Il riconoscitore storico di metadati e il fallback famiglia restano disponibili.

La fase fingerprint non modifica né apprende i pattern family. Il debug distingue file ufficiale identico, firma del contenuto, metadati e famiglia; il percorso normale conserva la spiegazione leggibile. Tutto il testo dei dati viene mostrato con `st.text`, senza rendering Markdown o risorse remote.

Il profilo di sicurezza Round 5 distingue anche vendita/acquisto. Quando l'intestazione presenta un qualificatore esclusivo, un riferimento all'altro sottotipo nel corpo non lo annulla. La regola è simmetrica e vale per scoring metadati e firme; non contiene identificativi di casi del benchmark. È stata introdotta dopo due false accettazioni del fallback metadati sulle scansioni, i cui risultati iniziali restano conservati.

## Valutazione e limiti

Known canonical, rappresentazioni trasformate, compilazione fittizia, split per identità family e sconosciuti hanno report distinti. Un documento canonico usato per costruire una firma fa parte della conoscenza del prodotto, non di un test di identità indipendente. Le trasformazioni sono un holdout di rappresentazioni. Il confronto family esclude il percorso exact/fingerprint e tiene indivisibili le risorse con stesso SHA. Le identità disponibili sono già state osservate nei round precedenti: il relativo split è retrospettivo e non dimostra generalizzazione prospettica.

Il benchmark manuale richiede cache locale, Tesseract effettivo e `pypdf` per compilare i PDF. La CI normale valida schema e fixture sintetiche, senza cache ufficiale e senza rete. Le prove OCR opzionali sono saltate quando Tesseract manca; i gate di release OCR sono esecuzioni manuali obbligatorie con Tesseract configurato. Le firme da sole non correggono metadati errati, non identificano nuovi moduli e non certificano la validità giuridica del documento.
