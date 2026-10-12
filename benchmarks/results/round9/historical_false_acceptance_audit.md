# Historical false acceptance audit — Round 9

Contratto storico NO; truth degli input senza revisione ambigua. Non vengono promossi a confirmed NO per migliorare i gate.

## EX02MISSINGREV

```json
{
  "case_id": "EX02MISSINGREV",
  "corpus": "tests/fixtures/benchmark_v2.json",
  "historical_expected": {
    "match_type": "NO_MATCH"
  },
  "reference_truth_status": "ambiguous",
  "predicted_document": 13,
  "predicted_family": null,
  "score": 100.0,
  "metadata_score": 100.0,
  "runner_up": 0.0,
  "margin": 100.0,
  "entities": [
    "inps"
  ],
  "version_evidence": [],
  "fingerprint_channels": [
    {
      "document_id": 13,
      "canonical_page": 1,
      "digital": 0.8169046458688718,
      "ocr": 0.6522999205107258,
      "chars": 0.37315551143063613,
      "anchors": 0.0,
      "visual": 0.0,
      "overlap": 6,
      "score": 0.5390567519351586,
      "max_similarity": 0.5390567519351586,
      "top2_average": 0.5390567519351586
    },
    {
      "document_id": 12,
      "canonical_page": 1,
      "digital": 0.5349638151394186,
      "ocr": 0.7366143392947315,
      "chars": 0.4017370397346641,
      "anchors": 0.0,
      "visual": 0.0,
      "overlap": 6,
      "score": 0.5089151335544981,
      "max_similarity": 0.5089151335544981,
      "top2_average": 0.5089151335544981
    }
  ],
  "tier": "insufficient_channels",
  "signals": [
    "codice esatto",
    "ente",
    "similarità generale"
  ],
  "metadata_revision_inferred": true,
  "root_cause": "Catalog-unique title/code/issuer treated as evidence of a missing revision in metadata_revision_supported; metadata fallback bypasses missing_model_revision veto.",
  "category": "version_conflict_not_enforced"
}
```

Veto mancato: `missing_model_revision` aggirato da `metadata_revision_supported`. Correzione generale del fallback metadata: titolo/codice/ente unici non provano una revisione decimale; occorre revisione esplicita nei primi2000 caratteri. Le firme forti v5 mantengono i criteri R8 multicanale, ancore di identità e margine; conflitti espliciti e risorse condivise conservano i veti. Nessuna blacklist. Dopo: `NO_MATCH`. Test: `tests/test_round9_engine.py::test_historical_missing_revision_is_conservative_for_any_id` include ID sintetico differente e controllo positivo con revisione esplicita. Canonical:979/979; hard negatives:130/130; nessuna nuova accettazione sui NO storici.

## EX03MISSINGREV

```json
{
  "case_id": "EX03MISSINGREV",
  "corpus": "tests/fixtures/benchmark_v2.json",
  "historical_expected": {
    "match_type": "NO_MATCH"
  },
  "reference_truth_status": "ambiguous",
  "predicted_document": 12,
  "predicted_family": null,
  "score": 100.0,
  "metadata_score": 100.0,
  "runner_up": 0.0,
  "margin": 100.0,
  "entities": [
    "inps"
  ],
  "version_evidence": [],
  "fingerprint_channels": [
    {
      "document_id": 13,
      "canonical_page": 1,
      "digital": 0.7739096645073522,
      "ocr": 0.6179683457470034,
      "chars": 0.41209968564713706,
      "anchors": 0.0,
      "visual": 0.0,
      "overlap": 6,
      "score": 0.531189722230174,
      "max_similarity": 0.531189722230174,
      "top2_average": 0.531189722230174
    },
    {
      "document_id": 12,
      "canonical_page": 1,
      "digital": 0.506807824868923,
      "ocr": 0.6978451635423771,
      "chars": 0.44366410977756865,
      "anchors": 0.0,
      "visual": 0.0,
      "overlap": 6,
      "score": 0.5042050201933376,
      "max_similarity": 0.5042050201933376,
      "top2_average": 0.5042050201933376
    }
  ],
  "tier": "insufficient_channels",
  "signals": [
    "codice esatto",
    "ente",
    "similarità generale"
  ],
  "metadata_revision_inferred": true,
  "root_cause": "Catalog-unique title/code/issuer treated as evidence of a missing revision in metadata_revision_supported; metadata fallback bypasses missing_model_revision veto.",
  "category": "version_conflict_not_enforced"
}
```

Veto mancato: `missing_model_revision` aggirato da `metadata_revision_supported`. Correzione generale del fallback metadata: titolo/codice/ente unici non provano una revisione decimale; occorre revisione esplicita nei primi2000 caratteri. Le firme forti v5 mantengono i criteri R8 multicanale, ancore di identità e margine; conflitti espliciti e risorse condivise conservano i veti. Nessuna blacklist. Dopo: `NO_MATCH`. Test: `tests/test_round9_engine.py::test_historical_missing_revision_is_conservative_for_any_id` include ID sintetico differente e controllo positivo con revisione esplicita. Canonical:979/979; hard negatives:130/130; nessuna nuova accettazione sui NO storici.
