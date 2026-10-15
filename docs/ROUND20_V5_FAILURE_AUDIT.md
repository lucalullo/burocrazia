# Round 20 — audit V5 storico

665 casi originali preservati:635 noti e30 unknown mix. Otto false accept documentali,179 false reject,0 errori ente/versione,0 family false accept. CSV completo una riga per caso; campi non raccolti rimangono vuoti. OCR_score indica similarità del canale OCR, non confidence di Tesseract.

Truth audit tecnico: {'confirmed_expected': 665}. Le risorse ufficiali locali e ricevute effettive provano identità e trasformazione; nessuna verifica editoriale umana o visita live odierna inventata. Tutti gli otto false accept confermati: i moduli469/470 per genitori e511/512 per tutori hanno intestazioni, ruoli e SHA distinti. La pagina allegata comune non autorizza il cambio di identità. L'originale V5 non viene aggiustato.

Root cause dei soli fallimenti: {'OCR_degradation': 47, 'visual_underuse': 53, 'retrieval_rank_low': 5, 'shared_template': 24, 'entity_conflict_false': 57, 'retrieval_miss': 1}. I57 veto di ente includono intestazioni dipartimentali non corrispondenti a un ente noto e frammenti OCR generici di tribunale: queste stringhe non dimostrano un altro emittente. La policy attuale può rifiutare firme per margine e poi accettare un'identità differente tramite metadati. Una correzione generale deve rispettare l'ambiguità, conservare i conflitti espliciti e usare canali indipendenti; non basta abbassare una soglia.

I rifiuti top1 sono principalmente decision/channel gating; solo un caso fuori top25 (802/rotation180, OCR degradato). Retrieval non sarà modificato per risolvere i veto decisionali. Breakdown per fonte e trasformazione in JSON separati, sempre legati ai raw originali. Ogni replay successivo è development_regression_v5_after_fix.
