#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  echo "Ambiente non installato. Segui README.md per creare .venv."
  exit 1
fi
echo "Apri http://127.0.0.1:8501 nel browser. Ctrl+C per chiudere."
exec .venv/bin/python run.py
