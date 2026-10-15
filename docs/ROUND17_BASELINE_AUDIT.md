# Round17 — baseline verificata

Branch `codex/coverage-benchmark-v0.7.0`, HEAD `19928839d10f762307827935eb2445bcff2787fe`, ingresso pulito (0 modificati,0 non tracciati). Software0.6.1/schema610. Motore, dataset, catalogo e truth identici al freeze Round16.

Ricalcolo dai raw: sette run/2814 tempi, mediana p95 244.9918ms; confronto delle firme complete su1563 casi,0 differenze; canonici980+27=1007/1007; policy1258 contratti confermati e hash verificati. Registry v3 SHA `6a48029bc3b29d804fe1f7893d6a3236538398e7a19b644d63df736ababb13fd`. Test finali ereditati819 passed/0 failed/3 skipped, da rieseguire per questo round.

I95 SHA indipendenti sono elencati in baseline_audit.json e verificati contro i byte ufficiali locali e il registry. Coprono13 fonti,18 enti,13 tipi; massimo20/95=21.0526%. Nessuna predizione v3/v5 avviata.

788 candidati,108 qualifiche automatiche provvisorie: esclusi una relazione MIMIT582 irrisolta e12 rappresentazioni correlate,95 finali. Altri candidati hanno titoli/enti insufficienti, relazioni catalogo/famiglia, limiti formato/pagine o ambiguità. Raccolta limitata a960 richieste; il traversal può arrestarsi quando un intero giro incontra URL già visti pur con elementi successivi in coda. Questo è un limite dell'acquisitore, non del motore. Il Round17 corregge soltanto l'infrastruttura e cerca almeno15 nuovi candidati/10 qualificati prima di misurare e congelare. Nessun tuning autorizzato.
