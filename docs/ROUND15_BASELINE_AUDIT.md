# Round15 — baseline

Branch `codex/coverage-benchmark-v0.7.0`; HEAD `425fa010063692d5d8ed090431068ad014d86ee6`; working tree pulito all'ingresso, 0 modificati e 0 non tracciati. Software pubblico 0.6.1, schema610. Freeze Round14 `37a9d1f3125b9e0480d2592f479554fe5ea40a0a` verificato: byte motore/profili/dataset/catalogo e truth storiche invariati, incluso il precedente dettaglio di serializzazione del manifest.

Verificati 45 lock Round14 e 434 blob storici. Baseline pytest: **777 passed, 0 failed, 3 skipped**, 654.65s; hash del log nel JSON.

Unknown v2 è `historical_unknown_release_v2_round14`: **107/114**, 3 DOCUMENT_MATCH, 0 FAMILY_MATCH e 4 errori di estrazione. Accettazioni: U14-5f0c017c3d56e6c5 e U14-c1fc4765c01dcd62 (INAIL, record1147); U14-d6e51fa8e7f88431 (ANAC, record615). I due INAIL sono compresi nei tre, non cinque casi distinti. I quattro PDF oltre limite sono elencati in page_limit_audit.json; restano nel denominatore114.

Il limite100 pagine esiste da `059c3168041dbd0fb33a7fba89dee22f4d0b1968 2026-09-06T07:50:41+02:00 Upload BurOCRazia` ed è antenato del freeze. README ed ESTRAZIONE lo documentavano. L'audit Round14 non lo aveva separato in preflight: questo difetto metodologico non viene cancellato. Soltanto i futuri gate separano classificazione e input-safety.

Stato ereditato: coverage1002/1158=86.528497%, canonici980/980+27/27, historicalNO241 senza accettazioni, mediana warm p95 247.1435ms, pytest777/0/3. Nessuno di questi esiti sostituisce le nuove verifiche dopo l'eventuale fix. Prossima attività: adjudication ufficiale completata prima di qualsiasi modifica al motore.
