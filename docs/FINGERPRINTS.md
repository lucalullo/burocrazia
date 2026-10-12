# Deterministic content fingerprints

Software 0.6.1; candidata Round 6 NOT READY. V1 è preservata in `data/document_recognition_fingerprints.json`.
V2 separata in `data/document_recognition_fingerprints_v2.json`, schema JSON dedicato;
nessuna migrazione SQL aggiuntiva (610). Schema rigido, limiti, scrittura atomica e idempotente.

Canali: SHA file esatto, token trigrams digitali e OCR canonico, char 4/5/6-gram,
containment pesato, etichette stabili nei primi 2.000 caratteri, struttura diagnostica,
dHash 256 bit in quattro orientamenti. Struttura non usata come prova autonoma.
IDF deterministico `log((N+1)/(df+1))+1`, snapshot corrispondente allo SHA bundle `1e8771912268b4e46cd564d6b35ad7fd137d354ab365ae2f02751b2d37c10073`.
N e df contano risorse canoniche attive; il ranking viene poi aggregato per identità.
Hash SHA256 separati per dominio, troncati a 64 bit, >=20 sovrapposizioni e corroborazioni;
collisioni isolate non autorizzano accettazione. Nessuna probabilità associata allo score.

Fusion: SHA unico + veto; altrimenti testo/OCR + char + etichette oppure layout,
o testo moderato + char + layout molto vicino + etichette, con margine tra identità.
I segnali complementari non sono dichiarati statisticamente indipendenti.
Conflitti espliciti ente, annualità/modello, revisione, allegato e sottotipo prevalgono sulla somiglianza.
Anno di competenza, citazioni legali e date di revisione non sono automaticamente la versione del modello.
Titoli/emittenti oltre i primi 2.000 caratteri non forniscono prove forti di identità.

OCR canonico PDF: prima pagina a 144 dpi, stesso `src.ocr` del runtime, Tesseract locale.
Solo gli sketch e metadati del motore/lingue/traineddata sono conservati; immagini e testo sono temporanei in memoria.
DOCX: digitale disponibile, OCR/visual indisponibili senza renderer. Nessun download del runtime.
Multiple risorse possono appartenere a un'identità; il ranking aggrega per identità.
Stale e quarantined esclusi; SHA condiviso tra identità non seleziona arbitrariamente un record.
Un aggiornamento necessita nuova acquisizione e riconciliazione; la data di cache non prova attualità sul sito.

Build solo `maintenance/`, rete esplicita `--allow-network`, URL ufficiali/robots/redirect/rate limit.
Runtime offline; nessun import maintenance o benchmark, nessun fetch, API o aggiornamento implicito.
Cache solo di firme canoniche pubbliche; upload features, pixel e testi sono request-local.
Riavviare `run.py` dopo una build: il processo carica una sola versione del bundle pubblico in cache.
Calibrazione congelata: `benchmarks/results/round6/fingerprint_calibration.json`; split per identità separato.
Copertura e limiti misurati: `FINGERPRINT_COVERAGE_AUDIT.md`, `BENCHMARK.md`.
Stati tecnici nel CSV `operational_support.csv` separati da revisione e provenienza storica.
