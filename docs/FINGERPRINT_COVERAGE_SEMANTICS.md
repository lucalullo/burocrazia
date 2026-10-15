# Semantica della fingerprint coverage

La metrica di gate Round 13 è **runtime-usable fingerprint support**. Non è supporto upload legacy. Il denominatore rimane 1158 file-backed operative, totale operativo 1212. La metrica canonical-native viene riportata a parte, senza riscrivere le serie storiche.

## Evidenza storica, esaminata prima dei nuovi risultati

- Round 5, sezione 2: «firme attive 369/1212», target 70%, preferito 85%. Non definisce native-only.
- Round 6, sezione 2 e gate: «firme attive per 948 identità», file-backed >=85%. Il denominatore include gli originali .doc non supportati.
- Round 7, sezione Recupero e copertura: mantiene 1158 e il gate 85%, vietando un denominatore opportunistico delle sole risorse recuperabili.
- Round 8/9 mantengono firme attive e shared separate; nessuna formulazione fondante native-only.
- Round 10, sezione recovery: i derivati sono esclusi perché il bundle v3 allora ammetteva solo PDF/DOCX ufficiali e i candidati non erano attivi. È un limite dell'implementazione, non la definizione iniziale del gate.
- Round 11 autorizza supporto di risorsa shared positivamente associata, separato dall'accuracy univoca.
- Round 12 conserva l'esclusione dei derivati non indicizzati e dichiara 4/5 performance preferito. Il requisito obbligatorio è la mediana p95 <=250 ms.

I documenti Round 5–12 restano intatti; i loro SHA sono in `historical_semantics_sources.json`. Non è stata trovata una definizione storica esplicita «native canonical only». La scelta applica la formulazione funzionale del gate e la precisazione richiesta dal prompt Round 13, senza cambiare soglie o denominatore.

## Definizione bloccata

`benchmarks/reference/fingerprint_support_definition_v1.json`, SHA `7d13aa4fcc7e6b3bb86a2d43c3e8ec203d6628f86cf9e43291176affb2b6c037`, bloccata prima della prima prova legacy R13. Native support e supporto runtime usabile sono conteggi separati. Le 33 associazioni shared storiche già adjudicate restano resource-level; nessuna viene spacciata per exact identity. Nuove ambiguità legacy irrisolte restano escluse.

L'originale legacy conserva URL/SHA/MIME/data. Il PDF derivato è solo una rappresentazione di benchmark e una fonte di statistiche tecniche. La normale pipeline runtime deve riconoscere l'identità tramite fingerprint, senza convertitore e senza attribuire al derivato lo SHA di file ufficiale. Nessuna promozione editoriale. Nessun cambiamento della definizione dopo il totale aggregato.
