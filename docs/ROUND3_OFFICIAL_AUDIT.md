# Round 3: audit dei 150 positivi ufficiali

`official_development_v2` è pubblico e usato per sviluppo, non indipendente. Audit iniziale di tutti i 150 positivi sul motore Round 2. Le cause automatiche sono integrate da sei osservazioni esplicite sul contenuto, con URL/hash nel raw. Non è una revisione editoriale umana. Le etichette congelate e i denominatori restano invariati, anche per risorse informative; nessun successo artificiale mediante rietichettatura.

## source

| Valore | N |
|---|---:|
| anac | 1 |
| funzione_pubblica | 9 |
| giustizia | 30 |
| inail | 27 |
| inl | 30 |
| lavoro | 29 |
| mef | 1 |
| mimit | 23 |

## entity

| Valore | N |
|---|---:|
| Autorità Nazionale Anticorruzione | 1 |
| Dipartimento della Funzione Pubblica | 9 |
| INAIL | 27 |
| Ispettorato Nazionale del Lavoro | 30 |
| Ministero del Lavoro | 29 |
| Ministero dell'Economia e delle Finanze / RGS | 1 |
| Ministero delle Imprese e del Made in Italy | 23 |
| Tribunale di Venezia | 30 |

## file_type

| Valore | N |
|---|---:|
| docx | 8 |
| pdf | 142 |

## exact_code_found

| Valore | N |
|---|---:|
| False | 133 |
| True | 17 |

## expected_version

| Valore | N |
|---|---:|
| False | 127 |
| True | 23 |

## root_cause

| Valore | N |
|---|---:|
| code_not_present_in_document | 8 |
| entity_not_present_or_indirect | 59 |
| expected_identity_wrong | 6 |
| generic_title | 1 |
| metadata_title_not_present_in_document | 35 |
| near_duplicate | 1 |
| other | 27 |
| recognizer_threshold | 2 |
| source_metadata_wrong | 1 |
| version_not_present | 10 |

## current_result

| Valore | N |
|---|---:|
| DOCUMENT_MATCH | 27 |
| NO_MATCH | 123 |

## Family fallback

Tutti i 123 rifiuti sono in `family_opportunities.csv`. La maggioranza delle 16 famiglie esistenti riguarda ADE/ADER/MIT e non le otto fonti del corpus. Per INAIL e le varianti tutelari mancano famiglie revisionate; aggiungerle come verificate automaticamente violerebbe le istruzioni del progetto. Nessuna nuova verifica attribuita. La regola generale di intestazione completa più ente migliora il fallback delle famiglie già verificate; non identifica emittenti assenti né inventa annualità. Nuove famiglie richiedono fonte, autore/storico e positivi/negativi vicini prima dell’ammissione.
