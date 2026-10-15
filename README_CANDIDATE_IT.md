# BurOCRazia 0.7.0-rc1 — candidata locale

**READY LOCALLY**, Round22. Pacchetto candidato0.7.0-rc1; la versione software pubblica e i byte runtime restano0.6.1, schema610. Il motore v7 è identico al Round21; migliora soltanto il generatore benchmark filled-form.

V6 single-shot: precisione100%, recall93.80%, scan93.33%, filled95.00%; generazione100/100, unknown4 originale120/120 preservato senza replay. Limiti,CI nominali e raw nel [report](docs/ROUND22_REPORT.md). CI esterna pending;questa RC locale non è una release pubblica né una garanzia su scansioni reali.

Avvio locale: `python run.py`, su loopback. OCR Tesseract locale,nessun LLM/cloud/telemetria. Conserva il catalogo completo,le provenienze e i limiti parser. Gli output PDF compilati sono fixture sintetiche private,non documenti da presentare agli enti.
