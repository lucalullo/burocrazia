# Release truth policy v1

La regressione storica confronta gli expected originali e mostra tutti i mismatch. Il release-gate-fast usa reference truth v3 più l'addendum Round16 motivato: **1258 contratti confermati**, senza cambiare alcun corpus o reference storica. Hash di v3, addendum, policy e input sono registrati.

Confirmed entra sempre; tentare di escluderlo è errore. Ambiguous e insufficient sono esclusi; historical_only resta nel report storico. Obsolete resta escluso finché una nuova versione con evidenza effettiva ne dimostra la riqualificazione. Nessuna scadenza o sostituzione viene inventata.

I domini sono espliciti: identità ufficiale adjudicata; binding tecnico del file canonico/derivato qualificato; contratto sintetico di rifiuto prudente; limite del parser. Un contratto sintetico confermato non diventa truth ufficiale o prova di precisione sugli sconosciuti. R061 e i negativi hard restano contratti di sicurezza anche quando una vecchia interpretazione dell'identità era ambigua. Le versioni v1/v2 e la v3 Round15 restano byte-identiche.

EX02/EX03 sono **INPS CI543/CI544**, revisione1.1 assente nel testo sintetico, già ambiguous in v2. I due INAIL ambigui sono distinti e restano esclusi. Entrambi i gruppi rimangono visibili; nessuno è usato per tuning. Le varianti compat-v2 con expected NO sono contratti espliciti di astensione, non una conferma della versione omessa negli expected storici.

ANAC, già osservato, entra nella regressione confermata grazie all'adjudication ufficiale precedente al fix. Il vecchio release_gate_eligible=false escludeva le risorse osservate dai futuri corpus indipendenti: non viene riscritto; il nuovo addendum dichiara un gate diagnostico distinto e independent_evaluation_eligible=false. Nessun caso storico/diagnostico può entrare come fresco in unknown v3 o evaluation v5.
