# Unknown release sampling policy v1

Il master contiene tutti gli unknown confermati, freschi e indipendenti, anche se sbilanciati. Solo il subset release deve rispettare N>=100,8 fonti,concentrazione<=25%,5 categorie. La qualifica di truth/freshness precede il sampling.

Seed20261014. Si cerca il più grande N sostenibile con cap floor(N/4); ordinamento iniziale per case_id, round-robin delle fonti e interleaving secondario tipo/ente/codificato/versionato. PRNG per fonte derivato da SHA256(seed:source), senza dipendenza dall'ordine dei file. Vietati score, predizioni, ranking, difficoltà o fingerprint similarity per la scelta. Il codice e la policy sono sigillati prima delle predizioni.

Master129, capacità per N100=112; massimo116 con cap29,13 fonti. Nessuna acquisizione aggiuntiva. I13 casi esclusi rimangono confirmed fresh nel master: esclusione per quota, nessuna reinterpretazione di truth o difficoltà. Il manifest è scritto prima del freeze, che ne registra l'hash; non contiene risultati di recognition. Il precedente preflight fallito Round17 è conservato. V3 single-shot sul freeze, nessuna riselezione/tuning dopo il primo risultato; v5 condizionale al PASS v3.
