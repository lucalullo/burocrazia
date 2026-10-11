# Installazione su un computer senza Internet

La candidata del 11/10/2026 mantiene Python 3.12 e il lock esistente. Il normale avvio resta `python run.py`, su loopback, senza acquisizione live. Gli strumenti `maintenance/` non sono necessari all'utente finale. Il benchmark statico nell'app non scarica file né avvia test.

Per il benchmark OCR reale serve Tesseract locale configurato con `BUROCRAZIA_TESSERACT_CMD`, se non nel PATH. In sua assenza il runner registra `not_run`; questo stato non equivale a un OCR superato. I file ufficiali possono essere preparati nella cache locale fuori Git; la rete del runner è abilitata soltanto con `--allow-network`. Vedere [ACQUISITION.md](ACQUISITION.md) e [BENCHMARK.md](BENCHMARK.md).

Il repository funziona localmente dopo l'installazione delle dipendenze. Per un'installazione senza rete occorre preparare i componenti su un computer con **stesso sistema operativo, architettura e Python 3.12** del destinatario.

## Preparazione

1. Procurati l'installer Python 3.12 a 64 bit per il sistema di destinazione.
2. Procurati Tesseract 5, tutte le sue dipendenze native e i dati `ita`, `eng` e `osd`. Su Linux un singolo `.deb` non basta se mancano librerie; prepara un deposito dei pacchetti e delle dipendenze compatibili. Su Windows usa una distribuzione verificabile del motore con i dati lingua inclusi.
3. Prepara le wheel Python sul sistema compatibile:

```bash
python -m pip download --only-binary=:all: --dest wheelhouse -r requirements-lock.txt
```

`requirements-lock.txt` inventaria le versioni transitive collaudate su Linux/Python 3.12. La disponibilità dei pacchetti binari va verificata separatamente sul sistema scelto. Non ignorare errori di dipendenze o assenza di wheel; non riutilizzare una wheel Linux su Windows.

4. Copia repository, wheelhouse, installer e dati lingua sul computer scollegato, insieme a licenze e informazioni di provenienza. Registra SHA-256 dei file trasferiti. Il download non è una verifica dell'autenticità del produttore.

## Installazione locale

Installa Python e Tesseract dai pacchetti predisposti, crea `.venv` e usa l'interprete dell'ambiente:

```bash
python -m pip install --no-index --find-links=wheelhouse -r requirements-lock.txt
python scripts/check_environment.py
python -m pytest -q
python run.py
```

L'opzione `--no-index` impedisce a pip di cercare pacchetti online. Le librerie Python non installano l'eseguibile Tesseract né scaricano automaticamente lingue.

## Verifica sul dispositivo

Apri il loopback nel browser e prova: un TXT leggibile, un documento sconosciuto, un'immagine di prova, le quattro pagine, la revisione su dati sintetici e un pacchetto locale in anteprima. Controlla anche la pulizia dei temporanei dopo errore/timeout. Usa il monitor delle connessioni del sistema per contare sia accessi sia tentativi esterni del processo e del browser.

Il blocco Python copre le chiamate socket del processo supportato; non è un firewall del sistema né un controllo delle estensioni del browser. Per isolare integralmente il dispositivo serve una policy di rete a livello di sistema. Non sono state prodotte immagini disco o installer completi multipiattaforma in questa consegna.
