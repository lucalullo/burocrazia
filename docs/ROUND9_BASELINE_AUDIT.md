# Round 9 baseline audit

Branch `codex/coverage-benchmark-v0.7.0`, HEAD `fa2a307fbbb4721ecafa93e6920c909526e00a25`; working tree pulito all’ingresso. Freeze motore R8 `b0e24476db23bb479dadb7f2957d34419d02c9d0`. Nessun file del motore, profilo, generatore filled o runner evaluation è cambiato dopo il freeze; i commit successivi riguardano report, audit e package. Elenco completo e metriche ricalcolate: `benchmarks/results/round9/baseline_audit.json`.

Canonical 979/979. V4 originale: 50/356 salvati, 36 exact, 0 wrong, 306 osservazioni indisponibili; non sono fallimenti dedotti. I due falsi accept sono EX02MISSINGREV e EX03MISSINGREV (INPS 13/12, revisione 1.1 assente). La causa è l’inferenza della revisione dalla sola unicità nel catalogo nel fallback metadata; truth ufficiale degli input sintetici ambigua, contratto storico NO mantenuto.

Il log prova OSError errno 22 in Path.open(wb), durante riscrittura evaluation_checkpoint.json. La causa OS esatta non è ricostruibile: mancano winerror, traccia OS e stato dei lock. Il difetto accertato dell’infrastruttura è la riscrittura non atomica, senza fsync/resume. Non viene inventata una causa antivirus. Caso A: completamento storico consentito, facoltativo, non effettuato; originali intatti e nessuna indipendenza R9 attribuita.

Profilo baseline nuovo, processo isolato e input R8 fissi: recognition warm p50 47.07 ms / p95 323.04 ms. Componenti e cProfile integrali nel raw; probes non additivi. Il profilo R8 dichiarava p95 350.13 ms; i confronti pagina dominano il costo. OCR/estrazione esclusi dai tempi recognition.

Ripresa: writer transazionale con prove d’interruzione, correzione generale del fallback metadata sulla revisione mancante, truth/unknown verificabili, recupero residui e ottimizzazione equivalente prima di qualsiasi freeze v5. Il primo tentativo esteso anche alle firme forti e il successivo replay affinato sono entrambi conservati e descritti nel report finale.
