# Censimento delle fonti

Round 3 non espande fonti, identità o IPA. Il campione ufficiale Round 2 è development; il nuovo holdout viene acquisito dopo il freeze con manifest, hash e controllo leakage separati. Gli esiti attuali sono in `BENCHMARK.md`: v1 storico non è più un gate indipendente; restano i limiti reali, R061 del locked v2 e la CI esterna. I censimenti seguenti conservano la provenienza Round 1/2.

Round 2 riconcilia le osservazioni Round 1; non dichiara nuovi censimenti. Le sette colonne da `already_present` a `excluded_other` costituiscono una partizione delle voci osservate: la somma deve uguagliare `discovered_total`. `final_active_identities` è uno stock separato. Una risorsa PDF/DOCX o una traduzione duplicata non aumenta le identità. `updated_existing` misura sostituzioni applicate nella raccolta Round 1, non le differenze osservate né le decisioni tecniche successive.

| source_key | discovered_total | already_present | new_identity | updated_existing | duplicate_resource | excluded_non_document | excluded_untrusted | excluded_other | final_active_identities |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ade | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 122 |
| interno | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| mit | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| giustizia | 159 | 0 | 143 | 0 | 14 | 2 | 0 | 0 | 142 |
| salute | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| mimit | 472 | 0 | 42 | 0 | 2 | 428 | 0 | 0 | 42 |
| ader | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| funzione_pubblica | 9 | 0 | 9 | 0 | 0 | 0 | 0 | 0 | 9 |
| aci | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| adm | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| mef | 18 | 0 | 15 | 0 | 1 | 2 | 0 | 0 | 15 |
| anac | 18 | 0 | 7 | 0 | 7 | 4 | 0 | 0 | 7 |
| agid | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| polizia | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| unioncamere | 12 | 0 | 4 | 0 | 4 | 4 | 0 | 0 | 4 |
| registro_imprese | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| inps | 357 | 97 | 259 | 0 | 1 | 0 | 0 | 0 | 359 |
| inail | 567 | 16 | 334 | 0 | 122 | 95 | 0 | 0 | 347 |
| lavoro | 133 | 102 | 0 | 0 | 31 | 0 | 0 | 0 | 102 |
| garante_privacy | 14 | 1 | 1 | 0 | 0 | 12 | 0 | 0 | 17 |
| inl | 146 | 33 | 13 | 0 | 98 | 2 | 0 | 0 | 46 |

232 osservazioni di record già presenti differiscono in almeno un campo; registrate senza sovrascrivere i metadati. Sono differenze di osservazione (incluse assenze e formati), non 232 revisioni certe. Quattro rifiuti tecnici sono eventi Round 2 separati: Venezia #429 lascia 143 record conservati e 142 operativi; le FAQ INAIL #1077/#1081/#1091 lasciano 350 record conservati e 347 operativi. Autore `Codex - audit tecnico automatico Round 2`, motivazione e prima/dopo nel database; nessuna verifica umana attribuita.

## Perimetri e lavoro residuo

`complete_for_declared_collection` indica soltanto che la coda dichiarata è esaurita e i metadati classificati, non tutta la burocrazia dell’ente. Sono percorsi tutti i quattro batch INPS italiani (357 elementi), l’indice INAIL, le quattro pagine Lavoro, i servizi INL di entrambe le raccolte, l’elenco Garante, i 16 elenchi Venezia, le sezioni radio/servizi alle imprese MIMIT, i nove moduli commerciali/turistici FP, l’elenco RGS e le pagine accesso ANAC/Unioncamere. Per FP restano edilizia e altre raccolte; per MIMIT restano altri procedimenti; per Giustizia restano altri uffici.

ADE, ADER e ADM: 403 nell’ambiente, senza aggiramento. MIT: verifica TLS fallita; Portale Automobilista ha restituito errore del server. ACI: redirect ufficiale verificato, infrastruttura collegata irraggiungibile. Salute: challenge Gcore HTTP 200, classificata come blocco. AgID e Polizia: pagina pubblica leggibile ma nessun modulo identificabile dal parser nel perimetro; richiedono analisi/manuale. Registro Imprese: URL selezionato 404, non prova che l’intero ente sia inaccessibile. Interno: indice e procedura cittadinanza leggibili, senza file statici acquisibili; non è stata attraversata ogni Prefettura. Nessuna espansione IPA effettuata.

Il Garante espone servizi online, pagine informative e download; dodici risorse non identificate come moduli sono escluse. Alcuni download condivisi nei dati preesistenti richiedono revisione, senza inventare revoche. Le risorse linguistiche INL sono unite per codice esplicito; PDF/DOCX non aumentano le identità. Le categorie HTML derivate restano nell’audit tecnico.

## Stato delle priorità Round 2

### Integrazione benchmark Round 11

Regione Piemonte è ammessa solo negli strumenti maintenance per il benchmark unknown, sul dominio istituzionale `regione.piemonte.it` e suoi sottodomini. Prove primarie: [Bandi Regione Piemonte](https://bandi.regione.piemonte.it/contributi-finanziamenti/progetti-i-giovani-ambito-sportivo), [Servizionline regionale](https://servizi.regione.piemonte.it/catalogo/presentazione-domanda-flaidom) e [modulo sul portale Trasparenza](https://trasparenza.regione.piemonte.it/media/27859/download). Le ricevute effettive, redirect e SHA sono nell’acquisizione R11; nessuna fonte o documento aggiunto al catalogo. HTML challenge e file non acquisibili non costituiscono prove documentali. Interno/Prefetture e Giustizia fuori Venezia restano benchmark-only; il titolo della pagina dettaglio è distinto dall’etichetta generica dell’allegato. Le dichiarazioni Round 2 seguenti restano storiche.

La seconda espansione non è stata avviata: precisione locked v1, copertura reale e gate CI restano insufficienti. Le prove Round 1 sono conservate in `source_census.json`; non sono spacciate per richieste Round 2. Il campione ufficiale è una valutazione dei record esistenti, non un import. ADE/ADER/ADM, ACI/PRA, MIT, Interno/Prefetture, Salute, AgID, Polizia, altri tribunali e IPA restano nel perimetro residuo. Nessun bypass di 403/429.
