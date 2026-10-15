# Reference truth audit v1

Audit precedente al tuning Round 8. I corpus locked e tutte le etichette storiche restano invariati. R6/R7 sono development. Le contraddizioni sono classificate per input normalizzato, senza scegliere l'expected in funzione del riconoscitore.

9 gruppi contraddittori, 29 occorrenze, 0 non classificati. Stati: `{"ambiguous": 25, "historical_fixture_error": 2, "official_truth_confirmed": 2}`. Soltanto `official_truth_confirmed` con `label_status=confirmed` entra nei gate riconciliati. I casi ambigui restano esclusi; le regressioni storiche di sicurezza sono comunque riportate separatamente, senza sostituire v1 con v2.

| Gruppo | Casi | Stato riconciliato | Motivazione |
|---|---|---|---|
| TRUTH-01 | EX02, EX02MISSINGREV | ambiguous | Official bytes confirm code/title and version 1.1, but the synthetic input omits the revision. It cannot establish that revision independently of catalog uniqueness. Both historical expectations are preserved; release truth is ambiguous. |
| TRUTH-02 | EX03, EX03MISSINGREV | ambiguous | Official bytes confirm code/title and version 1.1, but the synthetic input omits the revision. It cannot establish that revision independently of catalog uniqueness. Both historical expectations are preserved; release truth is ambiguous. |
| TRUTH-03 | R061 | ambiguous | Issuer/function conflict was intentionally corrected in locked v2. Runtime safety keeps NO, but absent official source bytes this registry does not certify the label as official truth. |
| TRUTH-04 | R010, R011 | ambiguous | Bare category or profession label is insufficient to establish a unique form/version. Official evidence distinguishes a full form heading or informational shared attachment; the short synthetic input remains ambiguous. |
| TRUTH-05 | R012, R013 | ambiguous | Bare category or profession label is insufficient to establish a unique form/version. Official evidence distinguishes a full form heading or informational shared attachment; the short synthetic input remains ambiguous. |
| TRUTH-06 | R028, R029 | ambiguous | Bare category or profession label is insufficient to establish a unique form/version. Official evidence distinguishes a full form heading or informational shared attachment; the short synthetic input remains ambiguous. |
| TRUTH-07 | R060 | ambiguous | Issuer/function conflict was intentionally corrected in locked v2. Runtime safety keeps NO, but absent official source bytes this registry does not certify the label as official truth. |
| TRUTH-08 | R066 | official_truth_confirmed | Full official heading and compatible issuing authority are present. R066 additionally states INL 31. Official local PDF/DOCX confirms a specific catalog identity; old family-only label was less specific. |
| TRUTH-09 | R068 | official_truth_confirmed | Full official heading and compatible issuing authority are present. R066 additionally states INL 31. Official local PDF/DOCX confirms a specific catalog identity; old family-only label was less specific. |

Le prove registrano URL, ricevuta effettiva, SHA dei byte ufficiali, identità e hash dell'intestazione ispezionata. Nessun evento pregresso inventato e nessuna nuova verifica editoriale attribuita. I PDF/DOCX ufficiali restano nella cache ignorata. La mancanza di byte ufficiali è dichiarata, non sostituita con un URL come prova di contenuto.

I nuovi casi canonical/evaluation ereditano `confirmed` soltanto da una risorsa ufficiale SHA-verificata, binding catalogo valido e identità non ambigua. Le risorse condivise sono escluse dall'identità exact se metadata/code/ente non disambiguano. Gli unknown storici mantengono `historical_only`; nessuna indipendenza nuova rivendicata.

Registro: `benchmarks/reference/reference_truth_v1.json`. Una revisione richiede un nuovo registro/versione con motivazione, non la sovrascrittura di v1.
