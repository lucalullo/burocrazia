"""Report local dependencies without making network requests."""
from __future__ import annotations
import importlib.metadata
import os
import shutil
import subprocess
import sys


def main() -> int:
    errors = 0
    print(f"Python: {sys.version.split()[0]}")
    if sys.version_info[:2] != (3, 12):
        print("Ambiente supportato: Python 3.12.")
        errors += 1
    for name in ("streamlit", "PyMuPDF", "python-docx", "Pillow", "pytesseract", "RapidFuzz"):
        try:
            print(f"{name}: {importlib.metadata.version(name)}")
        except importlib.metadata.PackageNotFoundError:
            print(f"{name}: MANCANTE")
            errors += 1
    command = os.environ.get("BUROCRAZIA_TESSERACT_CMD") or shutil.which("tesseract")
    if command:
        try:
            result = subprocess.run([command, "--list-langs"], capture_output=True, text=True, timeout=10)
            print(result.stdout.strip())
            if result.returncode:
                print("Tesseract non eseguibile: OCR non disponibile.")
            elif "ita" not in result.stdout.splitlines():
                print("Italiano OCR assente: installare localmente ita.traineddata. Con eng disponibile si usa il fallback.")
        except (OSError, subprocess.TimeoutExpired):
            print("Tesseract non utilizzabile: PDF testuali, DOCX e TXT restano disponibili.")
    else:
        print("OCR non disponibile: installare Tesseract e i dati lingua. PDF testuali, DOCX e TXT restano disponibili.")
    return int(errors > 0)


if __name__ == "__main__":
    raise SystemExit(main())
