# Audit iniziale Round 2

Stato di ingresso verificato prima di modificare il motore.

```json
{
  "commit": "21bede9e72ef09ed89ce47d6473f833671a4c1e9",
  "branch": "codex/coverage-benchmark-v0.7.0",
  "schema": 600,
  "verification": {
    "integrity": "ok",
    "foreign_key_violations": [],
    "tables": {
      "document_explanations": 3,
      "document_families": 16,
      "document_provenance": 1216,
      "documents": 1226,
      "entities": 2499,
      "local_resources": 0,
      "package_import_attempts": 2,
      "package_imports": 1,
      "review_events": 0,
      "schema_migrations": 1,
      "sources": 19
    },
    "real_documents": 1216,
    "demo_documents": 10,
    "real_documents_without_provenance": 0,
    "unverified_explanations": 3,
    "sha256": "8db623d55bb9c17ca2488cbdd6f91b9149af872552279baae0e0e30fc2e97121"
  },
  "quality": {
    "code": 429,
    "version": 513,
    "dates": 359,
    "downloads": 1161
  },
  "corpus_locks_verified": true,
  "baseline_rows_unchanged": true,
  "canonical_rejections": 70,
  "locked_failures": 10,
  "record_identity_review": "Technical metadata checks only; 827 additions not individually editor-reviewed."
}
```

I report raw Round 1 restano in `benchmarks/results/candidate/`: 35/35 regressione, 59/69 locked, 30/30 negativi, 1146/1216 canonici. Il report suite storico registra 488 passati e 3 skip; la suite viene rieseguita separatamente nel Round 2. Hash catalogo/lock e continuità di tutte le righe v0.6.1 verificati in sola lettura.

Le 143 identità Venezia pesano 11,76% del catalogo reale; derivano da 159 osservazioni, 14 risorse duplicate e 2 esclusioni. Questo controllo tecnico non certifica tutti i contenuti dei file. Il campione ufficiale Round 1 contiene un solo Venezia. Provenienza e URL non equivalgono a revisione umana. Nessuna nuova fonte o identità viene importata durante la chiusura dei gate.

## Esito successivo dell audit

Il controllo ampliato ha individuato quattro risorse informative erroneamente incluse nel Round 1: Venezia #429 e FAQ INAIL #1077/#1081/#1091. Restano conservate con identificativi e metadati, ma lo stato è rifiutato con autore tecnico Codex, data effettiva e storico prima/dopo. Nessuna verifica umana o revoca ufficiale attribuita. Il confronto cumulativo delle righe è in `round1_continuity_round2.json`: queste sono le sole quattro differenze di stato; tutte le righe v0.6.1 restano immutate. 1.216 record reali conservati, 1.212 operativi. La suite di ingresso è stata rieseguita: 488 passed, 3 skipped; il collaudo finale è separato.
