# Dieci fallimenti locked Round 1

V1 resta immutato. Queste schede riproducono il motore Round 1 prima delle modifiche. Score = punti di evidenza, non probabilità.

## R010

```text
Garante per la protezione dei dati personali
RECLAMO
```

Fonte: Garante per la protezione dei dati personali. Expected: `{'match_type': 'DOCUMENT_MATCH', 'document_id': 165, 'entity': 'Garante per la protezione dei dati personali', 'version': None}`. Actual: `{'match_type': 'NO_MATCH', 'document_id': None, 'family_id': None, 'entity': None, 'version': None}`.

Primi due candidati (rank, score, segnali): `[{'id': 165, 'title': 'RECLAMO', 'score': 95.0, 'rank': 0, 'signals': ('titolo', 'ente', 'similarità generale'), 'conflicts': ()}, {'id': 166, 'title': 'SEGNALAZIONE', 'score': 23.8, 'rank': 0, 'signals': ('ente', 'similarità generale'), 'conflicts': ()}]`. Margine: None; ente: ['garante per la protezione dei dati personali']; versione/anno e famiglia: vedere expected/actual.

Causa: titolo di una sola parola: non distingue modulo, categoria o servizio. Classificazione: fixture ambigua. Azione: Conservare rifiuto e v1; nuova etichetta documentata in v2. [Evidenza ufficiale](https://www.garanteprivacy.it/home/modulistica-e-servizi-online).

## R011

```text
Garante  per  la  protezione  dei  dati  personali

RECLAMO
```

Fonte: Garante per la protezione dei dati personali. Expected: `{'match_type': 'DOCUMENT_MATCH', 'document_id': 165, 'entity': 'Garante per la protezione dei dati personali', 'version': None}`. Actual: `{'match_type': 'NO_MATCH', 'document_id': None, 'family_id': None, 'entity': None, 'version': None}`.

Primi due candidati (rank, score, segnali): `[{'id': 165, 'title': 'RECLAMO', 'score': 95.0, 'rank': 0, 'signals': ('titolo', 'ente', 'similarità generale'), 'conflicts': ()}, {'id': 166, 'title': 'SEGNALAZIONE', 'score': 23.8, 'rank': 0, 'signals': ('ente', 'similarità generale'), 'conflicts': ()}]`. Margine: None; ente: ['garante per la protezione dei dati personali']; versione/anno e famiglia: vedere expected/actual.

Causa: titolo di una sola parola: non distingue modulo, categoria o servizio. Classificazione: fixture ambigua. Azione: Conservare rifiuto e v1; nuova etichetta documentata in v2. [Evidenza ufficiale](https://www.garanteprivacy.it/home/modulistica-e-servizi-online).

## R012

```text
Garante per la protezione dei dati personali
SEGNALAZIONE
```

Fonte: Garante per la protezione dei dati personali. Expected: `{'match_type': 'DOCUMENT_MATCH', 'document_id': 166, 'entity': 'Garante per la protezione dei dati personali', 'version': None}`. Actual: `{'match_type': 'NO_MATCH', 'document_id': None, 'family_id': None, 'entity': None, 'version': None}`.

Primi due candidati (rank, score, segnali): `[{'id': 166, 'title': 'SEGNALAZIONE', 'score': 95.0, 'rank': 0, 'signals': ('titolo', 'ente', 'similarità generale'), 'conflicts': ()}, {'id': 165, 'title': 'RECLAMO', 'score': 23.8, 'rank': 0, 'signals': ('ente', 'similarità generale'), 'conflicts': ()}]`. Margine: None; ente: ['garante per la protezione dei dati personali']; versione/anno e famiglia: vedere expected/actual.

Causa: titolo di una sola parola: non distingue modulo, categoria o servizio. Classificazione: fixture ambigua. Azione: Conservare rifiuto e v1; nuova etichetta documentata in v2. [Evidenza ufficiale](https://www.garanteprivacy.it/home/modulistica-e-servizi-online).

## R013

```text
Garante  per  la  protezione  dei  dati  personali

SEGNALAZIONE
```

Fonte: Garante per la protezione dei dati personali. Expected: `{'match_type': 'DOCUMENT_MATCH', 'document_id': 166, 'entity': 'Garante per la protezione dei dati personali', 'version': None}`. Actual: `{'match_type': 'NO_MATCH', 'document_id': None, 'family_id': None, 'entity': None, 'version': None}`.

Primi due candidati (rank, score, segnali): `[{'id': 166, 'title': 'SEGNALAZIONE', 'score': 95.0, 'rank': 0, 'signals': ('titolo', 'ente', 'similarità generale'), 'conflicts': ()}, {'id': 165, 'title': 'RECLAMO', 'score': 23.8, 'rank': 0, 'signals': ('ente', 'similarità generale'), 'conflicts': ()}]`. Margine: None; ente: ['garante per la protezione dei dati personali']; versione/anno e famiglia: vedere expected/actual.

Causa: titolo di una sola parola: non distingue modulo, categoria o servizio. Classificazione: fixture ambigua. Azione: Conservare rifiuto e v1; nuova etichetta documentata in v2. [Evidenza ufficiale](https://www.garanteprivacy.it/home/modulistica-e-servizi-online).

## R028

```text
INAIL
Avvocati
```

Fonte: INAIL. Expected: `{'match_type': 'DOCUMENT_MATCH', 'document_id': 20, 'entity': 'INAIL', 'version': None}`. Actual: `{'match_type': 'NO_MATCH', 'document_id': None, 'family_id': None, 'entity': None, 'version': None}`.

Primi due candidati (rank, score, segnali): `[{'id': 20, 'title': 'Avvocati', 'score': 95.0, 'rank': 0, 'signals': ('titolo', 'ente', 'similarità generale'), 'conflicts': ()}, {'id': 896, 'title': "Stp - Società tra professionisti iscritta all'albo degli avvocati", 'score': 25.0, 'rank': 0, 'signals': ('ente', 'similarità generale'), 'conflicts': ()}]`. Margine: None; ente: ['inail']; versione/anno e famiglia: vedere expected/actual.

Causa: titolo di una sola parola: non distingue modulo, categoria o servizio. Classificazione: fixture ambigua. Azione: Conservare rifiuto e v1; nuova etichetta documentata in v2. [Evidenza ufficiale](https://www.inail.it/portale/it/atti-e-documenti/moduli-e-modelli/altri-moduli/abilitazione-ai-servizi-online.html).

## R029

```text
INAIL

Avvocati
```

Fonte: INAIL. Expected: `{'match_type': 'DOCUMENT_MATCH', 'document_id': 20, 'entity': 'INAIL', 'version': None}`. Actual: `{'match_type': 'NO_MATCH', 'document_id': None, 'family_id': None, 'entity': None, 'version': None}`.

Primi due candidati (rank, score, segnali): `[{'id': 20, 'title': 'Avvocati', 'score': 95.0, 'rank': 0, 'signals': ('titolo', 'ente', 'similarità generale'), 'conflicts': ()}, {'id': 896, 'title': "Stp - Società tra professionisti iscritta all'albo degli avvocati", 'score': 25.0, 'rank': 0, 'signals': ('ente', 'similarità generale'), 'conflicts': ()}]`. Margine: None; ente: ['inail']; versione/anno e famiglia: vedere expected/actual.

Causa: titolo di una sola parola: non distingue modulo, categoria o servizio. Classificazione: fixture ambigua. Azione: Conservare rifiuto e v1; nuova etichetta documentata in v2. [Evidenza ufficiale](https://www.inail.it/portale/it/atti-e-documenti/moduli-e-modelli/altri-moduli/abilitazione-ai-servizi-online.html).

## R060

```text
Agenzia delle Entrate-Riscossione
Accertamento esecutivo
avviso di accertamento esecutivo
accertamento esecutivo
```

Fonte: Agenzia delle Entrate-Riscossione. Expected: `{'match_type': 'FAMILY_MATCH', 'family_id': 3, 'entity': 'Agenzia delle Entrate-Riscossione'}`. Actual: `{'match_type': 'NO_MATCH', 'document_id': None, 'family_id': None, 'entity': None, 'version': None}`.

Primi due candidati (rank, score, segnali): `[{'id': 11, 'title': 'RINUNCIA DEI BENEFICIARI ALLA CARTA ACQUISTI', 'score': 0.0, 'rank': 0, 'signals': ('similarità generale',), 'conflicts': ()}, {'id': 12, 'title': 'CERTIFICATO DI OPZIONE CONTRIBUTIVA - ACCORDO TRA LA REPUBBLICA ITALIANA E LA REPUBBLICA DI ALBANIA IN MATERIA DI SICUREZZA SOCIALE / CERTIFIKATA E ZGJEDHJES SË SKEMËS PËR PAGESËN E KONTRIBUTEVE - MARRËVESHJE NDËRMJET REPUBLIKËS ITALIANE DHE REPUBLIKËS SË SHQIPËRISË NË FUSHËN E SIGURIMEVE SHOQËRORE [CI544 - IT/AL 103]', 'score': 0.0, 'rank': 0, 'signals': ('similarità generale',), 'conflicts': ()}]`. Margine: None; ente: ['agenzia delle entrate riscossione']; versione/anno e famiglia: vedere expected/actual.

Causa: due frasi anche annidate non raggiungono soglia; ente creditore e riscossore confusi nel catalogo/fixture. Classificazione: expected probabilmente errato. Azione: Conservare rifiuto: non attribuire automaticamente una verifica alla famiglia. [Evidenza ufficiale](https://www.agenziaentrateriscossione.gov.it/it/Per-saperne-di-piu/documenti-della-riscossione/accertamento-esecutivo-e-avviso-di-addebito-inps/index.html).

## R061

```text
Agenzia delle Entrate-Riscossione
Avviso di addebito INPS
avviso di addebito inps
avviso di addebito
```

Fonte: Agenzia delle Entrate-Riscossione. Expected: `{'match_type': 'FAMILY_MATCH', 'family_id': 4, 'entity': 'Agenzia delle Entrate-Riscossione'}`. Actual: `{'match_type': 'NO_MATCH', 'document_id': None, 'family_id': None, 'entity': None, 'version': None}`.

Primi due candidati (rank, score, segnali): `[{'id': 11, 'title': 'RINUNCIA DEI BENEFICIARI ALLA CARTA ACQUISTI', 'score': 0.0, 'rank': 0, 'signals': ('similarità generale',), 'conflicts': ()}, {'id': 12, 'title': 'CERTIFICATO DI OPZIONE CONTRIBUTIVA - ACCORDO TRA LA REPUBBLICA ITALIANA E LA REPUBBLICA DI ALBANIA IN MATERIA DI SICUREZZA SOCIALE / CERTIFIKATA E ZGJEDHJES SË SKEMËS PËR PAGESËN E KONTRIBUTEVE - MARRËVESHJE NDËRMJET REPUBLIKËS ITALIANE DHE REPUBLIKËS SË SHQIPËRISË NË FUSHËN E SIGURIMEVE SHOQËRORE [CI544 - IT/AL 103]', 'score': 0.0, 'rank': 0, 'signals': ('similarità generale',), 'conflicts': ()}]`. Margine: None; ente: ['agenzia delle entrate riscossione']; versione/anno e famiglia: vedere expected/actual.

Causa: due frasi anche annidate non raggiungono soglia; ente creditore e riscossore confusi nel catalogo/fixture. Classificazione: expected probabilmente errato. Azione: Conservare rifiuto: non attribuire automaticamente una verifica alla famiglia. [Evidenza ufficiale](https://www.agenziaentrateriscossione.gov.it/it/Per-saperne-di-piu/documenti-della-riscossione/accertamento-esecutivo-e-avviso-di-addebito-inps/index.html).

## R066

```text
Ispettorato Nazionale del Lavoro
Richiesta di intervento ispettivo
richiesta di intervento ispettivo
modulo INL 31
```

Fonte: Ispettorato Nazionale del Lavoro. Expected: `{'match_type': 'FAMILY_MATCH', 'family_id': 10, 'entity': 'Ispettorato Nazionale del Lavoro'}`. Actual: `{'match_type': 'DOCUMENT_MATCH', 'document_id': 143, 'family_id': None, 'entity': 'Ispettorato Nazionale del Lavoro', 'version': None}`.

Primi due candidati (rank, score, segnali): `[{'id': 143, 'title': 'Richiesta di intervento ispettivo', 'score': 100.0, 'rank': 4, 'signals': ('codice esatto', 'titolo', 'ente', 'similarità generale'), 'conflicts': ()}, {'id': 141, 'title': 'Potere di transigere', 'score': 21.9, 'rank': 0, 'signals': ('ente', 'similarità generale'), 'conflicts': ()}]`. Margine: 100.0; ente: ['ispettorato nazionale del lavoro']; versione/anno e famiglia: vedere expected/actual.

Causa: fixture di famiglia contiene identità specifica presente nel catalogo. Classificazione: expected probabilmente errato. Azione: Conservare rifiuto e v1; nuova etichetta documentata in v2. [Evidenza ufficiale](https://www.ispettorato.gov.it/servizio/richiesta-di-intervento-ispettivo/).

## R068

```text
Garante per la protezione dei dati personali
Esercizio dei diritti privacy
esercizio dei diritti in materia di protezione dei dati personali
modello per l'esercizio dei diritti
```

Fonte: Garante per la protezione dei dati personali. Expected: `{'match_type': 'FAMILY_MATCH', 'family_id': 12, 'entity': 'Garante per la protezione dei dati personali'}`. Actual: `{'match_type': 'DOCUMENT_MATCH', 'document_id': 167, 'family_id': None, 'entity': 'Garante per la protezione dei dati personali', 'version': None}`.

Primi due candidati (rank, score, segnali): `[{'id': 167, 'title': 'ESERCIZIO DEI DIRITTI IN MATERIA DI PROTEZIONE DEI DATI PERSONALI', 'score': 95.0, 'rank': 3, 'signals': ('titolo', 'ente', 'similarità generale'), 'conflicts': ()}, {'id': 165, 'title': 'RECLAMO', 'score': 23.8, 'rank': 0, 'signals': ('ente', 'similarità generale'), 'conflicts': ()}]`. Margine: 95.0; ente: ['garante per la protezione dei dati personali']; versione/anno e famiglia: vedere expected/actual.

Causa: fixture di famiglia contiene identità specifica presente nel catalogo. Classificazione: expected probabilmente errato. Azione: Conservare rifiuto e v1; nuova etichetta documentata in v2. [Evidenza ufficiale](https://www.garanteprivacy.it/home/modulistica-e-servizi-online).
