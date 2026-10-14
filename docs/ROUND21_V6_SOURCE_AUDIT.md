# Round 21 — audit fonti V6

Audit di tutte le19 fonti catalogate e1.019 identità con fingerprint, senza predizioni o trasformazioni. Il pool passa da316/4 del Round20 a **639/8**, conteggi `{3: 231, 5: 28, 15: 12, 14: 3, 2: 302, 16: 52, 10: 8, 18: 3}`. Fonte è sempre il source_id storico: nessuna divisione artificiale.

La precedente incertezza includeva centinaia di ID presenti come candidati nei diagnostici legacy Round13: ciascuno dei due file contiene soltanto40 identità input effettive. L'audit distingue questi input, che restano esclusi conservativamente, dai candidati del catalogo. La restante esposizione a holdout storico/costruzione canonica non dimostra tuning secondo la regola esplicita Round21. Nessuna identità con identity_seen_in_tuning, provenienza diretta di calibrazione, V5 o development Round20/21 viene recuperata. V6 deve comunque usare rappresentazioni/seed/SHA nuovi. Tutti i flag e registry precedenti restano immutati; gli ID riclassificati e i file di prova/hash sono in v6_pool_prospects.json.

Controlli aggiuntivi preservati: binding, formato, canonical verificato, risorsa/URL effettivamente condivisi, titolo/codice/versione dello stesso emittente, campi e aggregate vicini a identità contaminate. Un profilo di fonte e la costruzione di una fingerprint non contaminano automaticamente tutte le sue identità. Le fonti senza risorse qualificate restano escluse con ragione esplicita; non serve costruire nuove fingerprint se il gate viene già dimostrato con quelle esistenti.

| Fonte | Nome | Fingerprint ID | Fresh ID | Motivo esclusione |
| --- | --- | --- | --- | --- |
| 1 | Registro IPA | 0 | 0 | No supported canonical fingerprint; official resources would require separate identity/provenance qualification. |
| 2 | Fonte istituzionale INPS | 359 | 302 |  |
| 3 | Fonte istituzionale INAIL | 326 | 231 |  |
| 4 | Fonte istituzionale Agenzia delle Entrate | 0 | 0 | No supported canonical fingerprint; official resources would require separate identity/provenance qualification. |
| 5 | Fonte istituzionale Ministero del Lavoro | 91 | 28 |  |
| 6 | Fonte istituzionale Ministero dell'Interno | 0 | 0 | No supported canonical fingerprint; official resources would require separate identity/provenance qualification. |
| 7 | Fonte istituzionale Ministero dei Trasporti | 0 | 0 | No supported canonical fingerprint; official resources would require separate identity/provenance qualification. |
| 8 | Fonte istituzionale Ministero della Giustizia | 0 | 0 | No supported canonical fingerprint; official resources would require separate identity/provenance qualification. |
| 9 | Fonte istituzionale Ministero della Salute | 0 | 0 | No supported canonical fingerprint; official resources would require separate identity/provenance qualification. |
| 10 | Fonte istituzionale MIMIT | 37 | 8 |  |
| 11 | Fonte istituzionale ADER | 0 | 0 | No supported canonical fingerprint; official resources would require separate identity/provenance qualification. |
| 12 | Modulistica standardizzata Funzione Pubblica | 9 | 0 | {"Round20_21_development_identity": 3, "historical_tuning_identity": 6} |
| 13 | Modulistica ufficiale PRA | 0 | 0 | No supported canonical fingerprint; official resources would require separate identity/provenance qualification. |
| 14 | Modulistica e servizi online Garante Privacy | 7 | 3 |  |
| 15 | Servizi e modulistica INL | 44 | 12 |  |
| 16 | Raccolta ufficiale Tribunale di Venezia | 134 | 52 |  |
| 17 | Raccolta ufficiale Ministero dell'Economia e delle Finanze / RGS | 1 | 0 | {"Round20_21_development_identity": 1} |
| 18 | Raccolta ufficiale Autorità Nazionale Anticorruzione | 7 | 3 |  |
| 19 | Raccolta ufficiale Unioncamere | 4 | 0 | {"V5_identity_seen": 1, "canonical_qualification_conservative_guard_not_claimed_tuning": 3} |

Capacità teoriche: `{'identities': {'actual': 639, 'minimum': 30, 'passed': True}, 'sources': {'actual': 8, 'minimum': 6, 'passed': True}, 'representations': {'actual': 9906, 'minimum': 400, 'passed': True}, 'scans': {'actual': 8568, 'minimum': 200, 'passed': True}, 'fills': {'actual': 60, 'minimum': 50, 'passed': True}}`. Non si rivendicano compilati validi prima della generazione. La prenotazione finale sarà fissata dopo il tuning, prima del freeze; nessuna trasformazione/predizione sulle identità riservate prima del freeze. Le verifiche canoniche del prodotto avvengono prima della prenotazione e non guidano soglie sulle future identità.
