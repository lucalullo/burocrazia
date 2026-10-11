# Round 4 — false acceptance audit

Historical holdout v1 is now development diagnostics. Original bytes and labels are retained. Listing/file discrepancies below require human adjudication; a refusal is the safe result. Scores are evidence points, not probabilities.

## OH1-033

Expected: `{'match_type': 'DOCUMENT_MATCH', 'document_id': 1222, 'entity': 'Ispettorato Nazionale del Lavoro', 'version': None}`. Before: `{'match_type': 'DOCUMENT_MATCH', 'document_id': 142, 'family_id': None, 'entity': 'Ispettorato Nazionale del Lavoro', 'version': None}`. Score 95.0; runner `{'document_id': 1222, 'score': 100.0}`; margin 95.0. Strong signals: ['titolo', 'ente']; weak: ['similarità generale']. Ignored/unrepresented contradictions: not represented by old scoring; see rule below.

Cause: `shared_code_pattern`. A complete segmented model code outranks a generic onorificenza title, subject to issuer/version gates. Fix: Prioritize exact code; preserve shared-code ambiguity. Test: `test_segmented_code_over_generic_title`. After: `{'match_type': 'DOCUMENT_MATCH', 'document_id': 1222, 'family_id': None, 'entity': 'Ispettorato Nazionale del Lavoro', 'version': None}`; safe: True.

## OH1-047

Expected: `{'match_type': 'DOCUMENT_MATCH', 'document_id': 428, 'entity': 'Tribunale di Venezia', 'version': None}`. Before: `{'match_type': 'DOCUMENT_MATCH', 'document_id': 77, 'family_id': None, 'entity': 'Agenzia delle Entrate', 'version': None}`. Score 95.0; runner `None`; margin 95.0. Strong signals: ['titolo', 'ente']; weak: ['similarità generale']. Ignored/unrepresented contradictions: not represented by old scoring; see rule below.

Cause: `generic_title_overmatch`. A short body phrase is not a form title even when its issuer is mentioned. The frozen judicial label and ADE file heading are inconsistent; neither is silently relabelled. Fix: Require a short title in the heading or an exact code. Test: `test_generic_body_title_not_identity`. After: `{'match_type': 'NO_MATCH', 'document_id': None, 'family_id': None, 'entity': None, 'version': None}`; safe: True.

## OH1-055

Expected: `{'match_type': 'DOCUMENT_MATCH', 'document_id': 1054, 'entity': 'INAIL', 'version': '2026'}`. Before: `{'match_type': 'DOCUMENT_MATCH', 'document_id': 1193, 'family_id': None, 'entity': 'INAIL', 'version': None}`. Score 84.3; runner `None`; margin 84.3. Strong signals: ['titolo']; weak: ['similarità generale']. Ignored/unrepresented contradictions: not represented by old scoring; see rule below.

Cause: `wrong_year_tolerated`. An unversioned title must not absorb an explicitly annual peer with unsupported table years. Fix: Catalog-derived annual-peer gate; no year inferred from a three-year table. Test: `test_unversioned_annual_peer_refuses_table_years`. After: `{'match_type': 'NO_MATCH', 'document_id': None, 'family_id': None, 'entity': None, 'version': None}`; safe: True.

## OH1-063

Expected: `{'match_type': 'DOCUMENT_MATCH', 'document_id': 1202, 'entity': 'INAIL', 'version': '2022'}`. Before: `{'match_type': 'DOCUMENT_MATCH', 'document_id': 989, 'family_id': None, 'entity': 'INAIL', 'version': None}`. Score 95.0; runner `None`; margin 95.0. Strong signals: ['titolo', 'ente']; weak: ['similarità generale']. Ignored/unrepresented contradictions: not represented by old scoring; see rule below.

Cause: `generic_title_overmatch`. A referenced Quadro C is not the heading of the annual rate communication. Fix: Require a heading/code for short titles. Test: `test_generic_body_title_not_identity`. After: `{'match_type': 'NO_MATCH', 'document_id': None, 'family_id': None, 'entity': None, 'version': None}`; safe: True.

## OH1-098

Expected: `{'match_type': 'DOCUMENT_MATCH', 'document_id': 534, 'entity': 'Tribunale di Venezia', 'version': None}`. Before: `{'match_type': 'DOCUMENT_MATCH', 'document_id': 441, 'family_id': None, 'entity': 'Tribunale di Venezia', 'version': None}`. Score 92.9; runner `None`; margin 92.9. Strong signals: ['titolo', 'ente']; weak: ['anchor tecnici derivati da file ufficiale development', 'similarità generale']. Ignored/unrepresented contradictions: not represented by old scoring; see rule below.

Cause: `technical_anchor_overfit`. Shared blank-form anchors cannot override an incompatible tutore/curatore subtype. Fix: Declarative exclusive subtype contradiction gate. Test: `test_exclusive_qualifiers_override_technical_anchors`. After: `{'match_type': 'NO_MATCH', 'document_id': None, 'family_id': None, 'entity': None, 'version': None}`; safe: True.


## Interpretazione del margine storico

Il margine riportato è quello effettivo del motore entro lo stesso rango di evidenza. Il runner elencato dall’audit è il miglior candidato alternativo anche di rango inferiore: per OH1-033 il codice corretto aveva 100 punti ma perdeva contro il titolo generico a rango superiore. Quindi il margine 95 non è la sottrazione 95−100; documenta proprio la priorità errata. Gli anchor tecnici sono riportati come segnali supplementari: il motore precedente li promuoveva come titolo, senza prova autonoma del sottotipo.
