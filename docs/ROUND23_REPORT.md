# Round 23 — preparazione della pre-release

Versione candidata `0.7.0-rc1`, schema 610. Il motore resta byte-identico al freeze Round 22; V6 e unknown v4 sono chiusi e non rieseguiti. Audit iniziale e classificazione dei file nei [release audit](ROUND23_RELEASE_AUDIT.md) e [tracking audit](ROUND23_TRACKING_AUDIT.md). Metriche e limiti nelle [release notes](RELEASE_NOTES_v0.7.0-rc1.md).

Questo rapporto entra nel commit preparatorio prima che il suo SHA e le conclusioni CI possano esistere. Commit, push, run ID, tag e pre-release saranno registrati soltanto dopo averne osservato l'esito; nessuna pubblicazione è attestata in anticipo. Il checkpoint privato conserva la progressione e impedisce duplicazioni. Una ricevuta finale successiva conserverà SHA e URL effettivi.

La stable pubblica `v0.6.1` deve restare invariata. La creazione del tag e della pre-release richiede working tree pulito, HEAD verificato verde su tutta la matrice e assenza del tag. Nessun merge o release stable è autorizzato.

## Validazione locale pre-commit

889 test superati, 0 fallimenti, 3 skip Windows; 485,15 secondi. Compileall, SQLite integrity/FK, doppia migrazione a schema610 con righe invariate, schemi benchmark, freeze e pacchetto PASS. Canonical1007/1007 e safety705/0FA sono verificati sulle osservazioni originali legate agli hash, senza replay held-out. Adattatore CI provato localmente: tutte le righe legacy identiche, inclusi i mismatch previsti e l’exit1 storico. Nessuna modifica semantica del recognition engine.
