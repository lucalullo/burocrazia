# BurOCRazia

**Making Italian bureaucracy easier to understand.**

BurOCRazia is a local, deterministic application for cautious recognition of Italian administrative documents. It accepts PDF, DOCX, TXT and image files, extracts text, uses local OCR when needed, and compares the content against a SQLite catalog installed on the user's computer.

[Versione italiana](README.md)

## Goal

BurOCRazia is designed to answer a simple question:

> **What document did I receive?**

The system tries to identify the document without forcing an answer when the available evidence is insufficient. It can return three outcomes:

- `DOCUMENT_MATCH` - a specific document is recognized;
- `FAMILY_MATCH` - a document family is recognized, but the exact document/version is not confirmed;
- `NO_MATCH` - there is not enough evidence for a reliable identification.

A correct `NO_MATCH` is preferred over a false positive.

## Main features

- local recognition of Italian administrative documents;
- text extraction from PDF, DOCX and TXT files;
- local Tesseract OCR for images and scanned PDFs;
- OCR autorotation at 0°, 90°, 180° and 270°;
- checks for issuing authority, code, title, version and year;
- family-level recognition when a specific record cannot be identified safely;
- SQLite catalog for documents, entities, sources, families, provenance and editorial explanations;
- local catalog and provenance browsing;
- editorial review with decision history;
- versioned local packages for catalog updates without live acquisition;
- loopback-only application server;
- no document upload to LLMs, cloud APIs or external services in the normal application flow.

## What this candidate includes

The catalog snapshot distributed with this candidate contains:

| Content | Count |
| --- | ---: |
| Real document records | 1216 |
| Demo records | 10 |
| Document families | 16 |
| Authorities represented by real document records | 12 |
| IPA entities in the local inventory | 2,499 |
| Registered sources (15 legacy verified, 4 pending) | 19 |
| Provenance records for real documents | 1216/1216 |
| Editorial explanation records | 3 |
| Local copies of official materials | 0 |

The 1216 real records are present in the catalog, but they are not automatically considered manually reviewed. The 3 included explanation records are still pending review.

**These numbers describe catalog coverage; they do not guarantee that every possible input file will be recognized.** Recognition depends on extraction quality and on the evidence available in the document.

The six original issuers below are joined by MIMIT, the Department for Public Administration, Venice Court, MEF/RGS, ANAC and Unioncamere. The original issuers are:

- INPS;
- INAIL;
- Italian Revenue Agency (Agenzia delle Entrate);
- Ministry of Labour (Ministero del Lavoro);
- National Labour Inspectorate (Ispettorato Nazionale del Lavoro);
- Italian Data Protection Authority (Garante per la protezione dei dati personali).

The IPA inventory also contains 2,499 entity records, but this does not mean that BurOCRazia has document coverage for all of them.

## How it works

```text
PDF / DOCX / TXT / image
          ↓
text extraction
          ↓
local OCR when needed
          ↓
normalization and deterministic signals
          ↓
specific document / family / cautious rejection
          ↓
catalog, provenance and available explanation
```

The recognition engine uses signals including:

- exact document code;
- title;
- issuing authority;
- keywords;
- text similarity;
- version and year;
- family-identifying phrases;
- authority/version contradictions;
- score margin between competing candidates.

The internal score shown by the interface is an engine diagnostic and **is not a calibrated probability of correctness**.

## Interface

The main navigation includes:

- **Recognize** - upload and analyze a document;
- **Catalog** - browse installed records;
- **Sources and provenance** - inspect origin information;
- **Editorial review** - maintain local content.
- **Benchmark** - inspect static evaluation results.

The sidebar also includes a visible **Light / Dark** appearance selector and a compact local-catalog summary.

Dates are displayed in the Italian `DD/MM/YYYY` format.

## Requirements

- 64-bit Python `3.12`;
- the project's Python dependencies;
- Tesseract 5 for images and scanned PDFs;
- Tesseract `ita` language data recommended;
- a modern browser for the Streamlit interface.

Tesseract is only required for the OCR path. PDF, DOCX and TXT files containing extractable text can be processed without OCR.

## Installation

### Windows

From the project directory:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe scripts\check_environment.py
```

If Tesseract is installed in the standard location but is not available in `PATH`:

```powershell
$env:BUROCRAZIA_TESSERACT_CMD = "C:\Program Files\Tesseract-OCR\tesseract.exe"
```

Start the application:

```powershell
.\.venv\Scripts\python.exe run.py
```

After the initial environment setup you can also use:

```text
avvia.bat
```

`avvia.bat` does not replace the initial Python environment installation.

### Linux / macOS

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python scripts/check_environment.py
.venv/bin/python run.py
```

Tesseract and the required language data must be installed separately on the host system.

## Usage

By default, BurOCRazia is served locally at:

```text
http://127.0.0.1:8501/
```

The launcher binds the server to loopback only. To choose a different port:

```bash
python run.py --port 8510
```

Stop the application with `Ctrl+C` in the terminal.

### Included demo

`examples/riconoscimento/` contains three synthetic files:

| Case | Expected result |
| --- | --- |
| INPS SR211 | `DOCUMENT_MATCH` |
| Model 730/2024 | `FAMILY_MATCH` |
| Non-administrative text | `NO_MATCH` |

The examples contain no personal data.

## Offline operation and privacy

The normal application flow is designed to run locally:

- server bound to `127.0.0.1`;
- local OCR;
- no LLM;
- no cloud API;
- Streamlit telemetry disabled;
- live project transports disabled in the local release;
- uploaded files are not automatically added to the catalog;
- OCR temporary files are removed by the normal application path.

BurOCRazia is not an operating-system sandbox or firewall. The browser, operating system, extensions, backups, swap and other processes remain outside the application's control.

Use synthetic or non-personal files for testing and development.

## Input limits

The release applies explicit limits:

- files up to 20 MiB;
- PDFs up to 100 pages;
- OCR on up to 5 pages;
- extracted text up to 1,000,000 characters.

These limits keep execution predictable and reduce excessive processing.

## Catalog updates

The local release does not perform live acquisition from institutional websites during normal use.

Catalog updates can be imported through validated local packages:

```bash
python scripts/import_package.py examples/pacchetto_demo.zip
```

Imports use preview, package hashing and transactions. URLs stored in the catalog are provenance references and do not imply automatic freshness checks.

See [docs/PACCHETTI_LOCALI.md](docs/PACCHETTI_LOCALI.md).

## Validation

The reference validation for v0.6.1 on Windows 11 / Python 3.12 recorded:

- **453 tests passed**;
- **3 tests skipped** because of platform-specific functionality or missing privileges;
- **0 failures**;
- synthetic regression benchmark: **35/35**;
- real Tesseract OCR runner: **7/7**;
- verified rotations at 0°, 90°, 180° and 270°;
- no final OCR temporary-file residue;
- manual offline test of `DOCUMENT_MATCH`, `FAMILY_MATCH` and `NO_MATCH`.

This validation protects known regressions. **It is not an independent benchmark of general accuracy on real-world documents and does not certify BurOCRazia for production use with sensitive data.**

See [docs/VALIDAZIONE.md](docs/VALIDAZIONE.md).

## Benchmark

Round 2 remains **NOT READY**; software version stays 0.6.1. The catalog retains 1,216 real records: 1,212 active and four technically rejected with author/history. Frozen v1 is 59/69; explicitly reconciled v2 is 69/69; hard negatives 100/100. Real Tesseract: 7/7 legacy and 14/14 synthetic OCR. The official sample contains 150 expected forms plus 12 real negatives; zero wrong identifications after safety fixes, with low recall. Paired performance, raw results, statistics and remaining gates are in [docs/BENCHMARK.md](docs/BENCHMARK.md). GitHub CI has not run; release-fast keeps its v1 failure. Further catalog expansion is deferred.

## Tests

```bash
python -m pytest -q
python scripts/verify_catalog.py
python scripts/catalog_status.py
python scripts/benchmark.py --output benchmark-results.json
```

The workflow in `.github/workflows/tests.yml` runs checks on Linux, Windows and macOS with Python 3.12.

## Repository structure

```text
BurOCRazia/
├── app.py                  # Streamlit interface
├── run.py                  # local launcher
├── src/                    # application logic
├── tests/                  # automated tests and regressions
├── data/                   # catalog snapshot and manifest
├── examples/               # synthetic examples
├── scripts/                # local utilities
├── docs/                   # technical documentation
└── .github/workflows/      # CI
```

## Project principles

1. A correct `NO_MATCH` is better than a false positive.
2. Document identity, authority and year must be supported by sufficient evidence.
3. Official provenance and editorial review are separate concepts.
4. An unreviewed explanation is never presented as validated.
5. Rejected documents remain in history but are excluded from operational matching.
6. Missing fields are not filled by assumption.
7. Catalog growth must not weaken false-positive protections.
8. Online acquisition is not part of the normal local runtime.

## Current limitations

- coverage does not represent all Italian public administration documents;
- all 1216 real document records still require editorial review;
- the 3 included explanations are not yet validated;
- no local copies of official documents are bundled;
- the catalog may become outdated because BurOCRazia does not check external updates;
- blurred, cropped or low-quality scans may produce `NO_MATCH`;
- the system does not replace the original document or information from the competent authority;
- this release is not certified for production use with personal or sensitive documents.

## Contributing

Before proposing a change:

```bash
python -m pytest -q
python scripts/benchmark.py --output benchmark-results.json
```

Recognition changes should preserve the project's cautious behavior and must not reduce `NO_MATCH` rates by simply increasing false positives.

Operational guidance for agents and contributors is available in [AGENTS.md](AGENTS.md).

## License

BurOCRazia is created by Luca Lullo and released under the [MIT License](LICENSE).

For catalog data and third-party materials, see [DATA_NOTICE.md](DATA_NOTICE.md).

## Author

Created by [Luca Lullo](https://github.com/lucalullo).
