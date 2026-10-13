<!-- round12-current -->
# Round 12

Round 12 **NOT READY**, pubblico 0.6.1/schema 610. Coverage 975/1158 = 84.196891%, recuperi 0, deficit 10. Unknown release: 105 selezionati e immutati, zero chiamate per STOP coverage. Median p95 217.8340 ms, 3/5 run <=250 ms. Test 767 passed/3 skipped. Safety/canonical R11 conservati su byte invariati; nessun freeze/v5. Dettagli: [report Round 12](ROUND12_REPORT.md). Le sezioni successive restano storiche.
<!-- /round12-current -->

<!-- round11-current -->
# Round 11

Round 11 **NOT READY**, pubblico 0.6.1/schema 610. Coverage supporto risorsa 975/1158=84.196891%, di cui 942 unambiguous e 33 shared-only; non confondere con canonical 980/980. Master unknown 125, release 105/10 fonti/max 23.809524%, senza predizioni release R11. p95 248.23ms; tests 762 passati/3 skip. Nessun freeze/v5. Dettagli: [rapporto Round 11](ROUND11_REPORT.md). Le sezioni successive restano storiche.
<!-- /round11-current -->

<!-- round10-current -->
# Coverage Round10

Coverage attuale941/1158=81.26% e941/1212=77.64%. Minimo985, delta44. 217residui auditati,47derivazioni temporanee,2candidati univoci non attivi; PDF derivati e risorse condivise esclusi dal conteggio. Dati nel pianoR10 e rapporto. Le misure Round6 seguenti restano storiche.
<!-- /round10-current -->

# Fingerprint coverage audit — Round 6

A declared download remains file-backed despite 403/404, unsupported .doc, extraction failure or shared bytes. Detail-only records become file-backed only after an actual supported attachment. No failed fetch is reclassified as a service.

Identità operative: 1212. File-backed: 1158. Identità fingerprinted: 948.
Copertura totale 78.22%; copertura file-backed 81.87%.

Le 843 assenze v1 sono conservate nel CSV richiesto con il risultato tecnico Round 6; il CSV final contiene le assenze residue.
Stato tecnico e stato editoriale restano separati. Seed SQLite e tutte le identità invariati. Le date sono ricevute effettive, senza inventare attualità della risorsa.

| Fonte | Operativi | File-backed | Fingerprinted |
|---|---:|---:|---:|
| inps | 359 | 359 | 351 |
| inail | 347 | 347 | 308 |
| ade | 122 | 90 | 0 |
| lavoro | 102 | 102 | 74 |
| mimit | 42 | 42 | 25 |
| funzione_pubblica | 9 | 9 | 8 |
| garante_privacy | 17 | 10 | 4 |
| inl | 46 | 45 | 43 |
| giustizia | 142 | 142 | 126 |
| mef | 15 | 1 | 1 |
| anac | 7 | 7 | 7 |
| unioncamere | 4 | 4 | 1 |

Assenze residue: `{"shared_resource": 26, "unsupported_mime": 34, "source_changed": 19, "robots_or_policy_block": 127, "detail_page_only": 27, "extraction_failure": 24, "http_404": 1, "download_url_html": 6}`.

INPS: MIME multipart con un solo allegato PDF validato; hash del contenitore e del payload distinti nel manifest. Nessun bypass.
Resolver: una pagina ufficiale e al massimo sei allegati correlati a titolo/codice. Redirect con allowlist; fixture offline per ciascuna fonte.
HTTP 403/429 pregressi non ritentati. Robots per percorso, attese >=1 s e budget per sessione. HTML ordinario non chiude più arbitrariamente tutta la fonte.
DOC binario legacy resta non supportato, e resta nel denominatore. DOCX privo di renderer locale: firma digitale disponibile, OCR canonico non dichiarato.
Le quarantene tecniche non revocano né modificano automaticamente i record editoriali.
