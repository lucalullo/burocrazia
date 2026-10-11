# Nove identificazioni ufficiali errate: analisi e correzioni

Il primo raw resta immutato. Score/margini riprodotti dal motore Round 1, verificando la stessa previsione errata; non sono probabilità. I testi dei file non sono conservati.

## OR2-023

Expected 1215; prima {'match_type': 'DOCUMENT_MATCH', 'document_id': 133, 'family_id': None, 'entity': 'Ispettorato Nazionale del Lavoro', 'version': None}; score 100.0, margine 10.8, secondo {'id': 1215, 'score': 89.2, 'signals': ('codice esatto', 'similarità generale')}; segnali ('codice esatto', 'titolo', 'similarità generale'), ente rilevato []. Causa: numeric code prefix was accepted despite a subtype suffix. Dopo: {'match_type': 'DOCUMENT_MATCH', 'document_id': 1215, 'family_id': None, 'entity': 'Ispettorato Nazionale del Lavoro', 'version': None}. Fixture: `tests/test_round2_recognition.py:OR2-023`. [Fonte ufficiale](https://www.ispettorato.gov.it/files/2025/11/Modulo-INL-29-2-Istanza-duplicato-formato-word-patentino-generatori-vapore_new-1.pdf); SHA-256 `23b5650a730c18fea32b753f0640c467d705acf62e0e62a5061c9c3d42937e0b`.

## OR2-030

Expected 290; prima {'match_type': 'DOCUMENT_MATCH', 'document_id': 178, 'family_id': None, 'entity': 'Garante per la protezione dei dati personali', 'version': None}; score 82.7, margine 82.7, secondo None; segnali ('titolo', 'similarità generale'), ente rilevato []. Causa: body citation of a generic title without the proper issuer. Dopo: {'match_type': 'NO_MATCH', 'document_id': None, 'family_id': None, 'entity': None, 'version': None}. Fixture: `tests/test_round2_recognition.py:OR2-030`. [Fonte ufficiale](https://www.lavoro.gov.it/strumenti-e-servizi/Modulistica/Documents/Richiesta%20Patrocinio%20da%20parte%20di%20Soggetti%20Privati/Modulo-Richiesta-Patrocinio-Soggetto-Privato.pdf); SHA-256 `725dd63e73d2c12b4ce63c86952e582a7aaa40e673684150bf81f32a4dd3ca91`.

## OR2-031

Expected 550; prima {'match_type': 'DOCUMENT_MATCH', 'document_id': 544, 'family_id': None, 'entity': 'Ministero delle Imprese e del Made in Italy', 'version': None}; score 88.3, margine 88.3, secondo None; segnali ('titolo', 'ente', 'similarità generale'), ente rilevato ['ministero delle imprese e del made in italy']. Causa: missing distinctive acronym allowed a different certificate. Dopo: {'match_type': 'NO_MATCH', 'document_id': None, 'family_id': None, 'entity': None, 'version': None}. Fixture: `tests/test_round2_recognition.py:OR2-031`. [Fonte ufficiale](https://www.mimit.gov.it/images/stories/documenti/radio/2024/DOMANDA_DUPLICATO.pdf); SHA-256 `3500858fcbc4610bbf3973b8871a81fcb910b440723ecb9f6507a1c615b9b568`.

## OR2-070

Expected 1225; prima {'match_type': 'DOCUMENT_MATCH', 'document_id': 153, 'family_id': None, 'entity': 'Ispettorato Nazionale del Lavoro', 'version': None}; score 100.0, margine 14.7, secondo {'id': 1225, 'score': 85.3, 'signals': ('codice esatto', 'similarità generale')}; segnali ('codice esatto', 'titolo', 'similarità generale'), ente rilevato []. Causa: numeric code prefix was accepted despite a subtype suffix. Dopo: {'match_type': 'DOCUMENT_MATCH', 'document_id': 1225, 'family_id': None, 'entity': 'Ispettorato Nazionale del Lavoro', 'version': None}. Fixture: `tests/test_round2_recognition.py:OR2-070`. [Fonte ufficiale](https://www.ispettorato.gov.it/files/2023/01/INL-1.4-Autodichiarazione-Marca-da-Bollo-INL_.pdf); SHA-256 `36ea0ea98d7d644c03754d68ec5b190f9b2eb0ba13316be8d75e922b6d3eb0a1`.

## OR2-098

Expected 149; prima {'match_type': 'DOCUMENT_MATCH', 'document_id': 146, 'family_id': None, 'entity': 'Ispettorato Nazionale del Lavoro', 'version': None}; score 83.4, margine 83.4, secondo None; segnali ('codice esatto', 'similarità generale'), ente rilevato []. Causa: page/line boundary assembled an incidental code. Dopo: {'match_type': 'NO_MATCH', 'document_id': None, 'family_id': None, 'entity': None, 'version': None}. Fixture: `tests/test_round2_recognition.py:OR2-098`. [Fonte ufficiale](https://www.ispettorato.gov.it/files/2025/05/Modello-comunicazione-art.-26-comma-7-bis-D.Lgs_.-n.-151-2015-2.pdf); SHA-256 `51d81d2e2b5bdf8ba85cdf106a62abadb1b7628528141958200e31deb8d8a956`.

## OR2-136

Expected 409; prima {'match_type': 'DOCUMENT_MATCH', 'document_id': 77, 'family_id': None, 'entity': 'Agenzia delle Entrate', 'version': None}; score 81.5, margine 81.5, secondo None; segnali ('titolo', 'similarità generale'), ente rilevato []. Causa: body citation of a generic title without the proper issuer. Dopo: {'match_type': 'NO_MATCH', 'document_id': None, 'family_id': None, 'entity': None, 'version': None}. Fixture: `tests/test_round2_recognition.py:OR2-136`. [Fonte ufficiale](https://tribunale-venezia.giustizia.it/resources/cms/documents/2adsiscrizionearuolo_5.pdf); SHA-256 `e29acb39a717d7f43c68dcd4ca7763ef9b518ffb62fb724a1fa033563d45ff18`.

## OR2-145

Expected 429; prima {'match_type': 'DOCUMENT_MATCH', 'document_id': 77, 'family_id': None, 'entity': 'Agenzia delle Entrate', 'version': None}; score 81.5, margine 81.5, secondo None; segnali ('titolo', 'similarità generale'), ente rilevato []. Causa: body citation of a generic title without the proper issuer. Dopo: {'match_type': 'NO_MATCH', 'document_id': None, 'family_id': None, 'entity': None, 'version': None}. Fixture: `tests/test_round2_recognition.py:OR2-145`. [Fonte ufficiale](https://tribunale-venezia.giustizia.it/resources/cms/documents/Contributo_UnificatoObbligo_pagamento.pdf); SHA-256 `5ac25ccbbd7e2291e50966bae831977383b7bfe65d1b468f97dde0ca46cd607a`.

## OR2-147

Expected 150; prima {'match_type': 'DOCUMENT_MATCH', 'document_id': 80, 'family_id': None, 'entity': 'Agenzia delle Entrate', 'version': None}; score 82.9, margine 82.9, secondo None; segnali ('codice esatto', 'similarità generale'), ente rilevato []. Causa: payment code appeared late in another form. Dopo: {'match_type': 'NO_MATCH', 'document_id': None, 'family_id': None, 'entity': None, 'version': None}. Fixture: `tests/test_round2_recognition.py:OR2-147`. [Fonte ufficiale](https://www.ispettorato.gov.it/files/2023/01/INL-33-Istanza-di-revoca-del-provvedimento-di-sospensione-1.pdf); SHA-256 `645a17fae238198df6f49a1f5e382324926763cdf5326739ea780c0f0df207a8`.

## OR2-161

Expected 289; prima {'match_type': 'DOCUMENT_MATCH', 'document_id': 178, 'family_id': None, 'entity': 'Garante per la protezione dei dati personali', 'version': None}; score 82.7, margine 82.7, secondo None; segnali ('titolo', 'similarità generale'), ente rilevato []. Causa: body citation of a generic title without the proper issuer. Dopo: {'match_type': 'NO_MATCH', 'document_id': None, 'family_id': None, 'entity': None, 'version': None}. Fixture: `tests/test_round2_recognition.py:OR2-161`. [Fonte ufficiale](https://www.lavoro.gov.it/strumenti-e-servizi/Modulistica/Documents/Richiesta%20Patrocinio%20da%20parte%20di%20Enti%20Pubblici/Modulo-Richiesta-Patrocinio-Ente-Pubblico.pdf); SHA-256 `c64ea462a3b541ee05370461c53ebbe9b68fd8af99e0bef77b8a3d26e8c02a2b`.
