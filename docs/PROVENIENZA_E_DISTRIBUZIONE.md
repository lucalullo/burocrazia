# Provenienza e distribuzione

## Catalogo iniziale

`data/catalog_seed.sqlite3` contiene lo snapshot iniziale del catalogo distribuito con BurOCRazia. `data/catalog_manifest.json` ne registra hash e conteggi per permettere controlli di integrità e continuità dei dati.

Il database operativo viene creato separatamente al primo avvio. Un database già presente viene conservato e migrato secondo le procedure del progetto; i dati personali caricati dall'utente non vengono aggiunti automaticamente al catalogo.

I record conservano, quando disponibili, fonte, URL, data di rilevazione, versione e stato di verifica. **Provenienza registrata e verifica editoriale non sono equivalenti**: un dato proveniente da una fonte istituzionale può essere ancora in attesa di revisione.

## Funzionamento locale

La release 0.6.1 non esegue acquisizioni live dalle fonti istituzionali. Gli URL del catalogo sono trattati come dati testuali di provenienza. Gli aggiornamenti avvengono attraverso pacchetti locali sottoposti a validazione, anteprima, hash e transazione.

La configurazione Streamlit forza l'applicazione sul loopback e disattiva la telemetria prevista dal framework. Il launcher installa inoltre il controllo di rete del progetto. Queste misure non equivalgono a un firewall del sistema operativo.

## Distribuzione

Il repository contiene sorgenti, snapshot del catalogo, test, esempi sintetici e documentazione. Non include:

- Python;
- Tesseract o i relativi dati lingua;
- un ambiente virtuale;
- documenti personali;
- database operativo dell'utente;
- copie ufficiali locali non espressamente incluse nel catalogo.

Per predisporre una macchina completamente scollegata dalla rete consulta [INSTALLAZIONE_OFFLINE.md](INSTALLAZIONE_OFFLINE.md).

## Licenze

Il codice originale del progetto è distribuito con licenza MIT, presente in `LICENSE`. Dipendenze, dati e materiali di terzi conservano le proprie condizioni; la MIT del codice non concede diritti sui documenti istituzionali.

Ogni dipendenza conserva la propria licenza. Il repository sorgente non incorpora automaticamente i relativi binari esterni.

## Confini della release

La presenza di un record nel catalogo non significa che il contenuto sia stato revisionato manualmente. Le famiglie, le spiegazioni e i materiali locali mantengono il proprio stato di verifica. BurOCRazia non inventa metadati mancanti e non attribuisce verifiche automaticamente.

I risultati di test e OCR della v0.6.1 sono riepilogati in [VALIDAZIONE.md](VALIDAZIONE.md).

La candidata successiva aggiunge acquisizione tecnica separata dal runtime. Il pacchetto di soli metadati in `maintenance/releases/2026-10-11/` è stato applicato a una copia dello snapshot iniziale con anteprima, hash e transazione, quindi riapplicato per verificarne l'idempotenza. Le impronte di tutte le righe iniziali sono in `data/baseline_v061_rows.json`: nessuna riga pregressa è stata sostituita. Il database operativo dell'utente non viene aggiornato dal nuovo seed; l'aggiornamento richiede l'importazione esplicita del pacchetto.

Le quattro nuove fonti restano `da_verificare`; la validazione tecnica dei domini non simula una revisione umana. Le categorie ricavate dalla posizione di un titolo di sezione HTML sono conservate come `derived_section_label` nell'audit, senza attribuirle a una tassonomia ufficiale del database. Il dettaglio quantitativo corrente è in [COVERAGE.md](COVERAGE.md).
