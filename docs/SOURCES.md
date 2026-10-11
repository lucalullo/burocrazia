# Censimento delle fonti

Acquisizione del 11/10/2026, sequenziale, senza bypass. Le date/URL/errori/tentativi e ricevute sono in `source_census.json` e nell’audit del pacchetto. I conteggi scoperti comprendono duplicati ed esclusioni. “Importati” significa nuovi record; “già presenti” conserva il record senza sostituzione. Aggiornamenti distruttivi: zero.

| Fonte | Scoperti | Importati | Aggiornati | Già presenti | Duplicati | Esclusi | Stato |
|---|---:|---:|---:|---:|---:|---:|---|
| ade | 0 | 0 | 0 | 0 | 0 | 0 | blocked |
| interno | 0 | 0 | 0 | 0 | 0 | 0 | manual |
| mit | 0 | 0 | 0 | 0 | 0 | 0 | blocked |
| giustizia | 159 | 143 | 0 | 0 | 14 | 2 | complete_for_declared_collection |
| salute | 0 | 0 | 0 | 0 | 0 | 0 | blocked |
| mimit | 472 | 42 | 0 | 0 | 2 | 428 | complete_for_declared_collection |
| ader | 0 | 0 | 0 | 0 | 0 | 0 | blocked |
| funzione_pubblica | 9 | 9 | 0 | 0 | 0 | 0 | complete_for_declared_collection |
| aci | 0 | 0 | 0 | 0 | 0 | 0 | blocked |
| adm | 0 | 0 | 0 | 0 | 0 | 0 | blocked |
| mef | 18 | 15 | 0 | 0 | 1 | 2 | complete_for_declared_collection |
| anac | 18 | 7 | 0 | 0 | 7 | 4 | complete_for_declared_collection |
| agid | 0 | 0 | 0 | 0 | 0 | 0 | manual |
| polizia | 0 | 0 | 0 | 0 | 0 | 0 | manual |
| unioncamere | 12 | 4 | 0 | 0 | 4 | 4 | complete_for_declared_collection |
| registro_imprese | 0 | 0 | 0 | 0 | 0 | 0 | blocked |
| inps | 357 | 259 | 0 | 97 | 1 | 0 | complete_for_declared_collection |
| inail | 567 | 334 | 0 | 16 | 122 | 95 | complete_for_declared_collection |
| lavoro | 133 | 0 | 0 | 102 | 31 | 0 | complete_for_declared_collection |
| garante_privacy | 14 | 1 | 0 | 1 | 0 | 12 | complete_for_declared_collection |
| inl | 146 | 13 | 0 | 33 | 98 | 2 | complete_for_declared_collection |

## Perimetri e lavoro residuo

`complete_for_declared_collection` indica soltanto che la coda dichiarata è esaurita e i metadati classificati, non tutta la burocrazia dell’ente. Sono percorsi tutti i quattro batch INPS italiani (357 elementi), l’indice INAIL, le quattro pagine Lavoro, i servizi INL di entrambe le raccolte, l’elenco Garante, i 16 elenchi Venezia, le sezioni radio/servizi alle imprese MIMIT, i nove moduli commerciali/turistici FP, l’elenco RGS e le pagine accesso ANAC/Unioncamere. Per FP restano edilizia e altre raccolte; per MIMIT restano altri procedimenti; per Giustizia restano altri uffici.

ADE, ADER e ADM: 403 nell’ambiente, senza aggiramento. MIT: verifica TLS fallita; Portale Automobilista ha restituito errore del server. ACI: redirect ufficiale verificato, infrastruttura collegata irraggiungibile. Salute: challenge Gcore HTTP 200, classificata come blocco. AgID e Polizia: pagina pubblica leggibile ma nessun modulo identificabile dal parser nel perimetro; richiedono analisi/manuale. Registro Imprese: URL selezionato 404, non prova che l’intero ente sia inaccessibile. Interno: indice e procedura cittadinanza leggibili, senza file statici acquisibili; non è stata attraversata ogni Prefettura. Nessuna espansione IPA effettuata.

Il Garante espone servizi online, pagine informative e download; dodici risorse non identificate come moduli sono escluse. Alcuni download condivisi nei dati preesistenti richiedono revisione, senza inventare revoche. Le risorse linguistiche INL sono unite per codice esplicito; PDF/DOCX non aumentano le identità. Le categorie HTML derivate restano nell’audit tecnico.
