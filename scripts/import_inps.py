"""Comando storico disattivato nella distribuzione offline R2."""
from __future__ import annotations
import sys

def main(argv: list[str] | None = None) -> int:
    print("Acquisizione online disattivata. Usa python scripts/import_package.py per un pacchetto locale tracciato.", file=sys.stderr)
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
