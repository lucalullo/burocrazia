@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Ambiente non installato. Segui README.md per creare .venv.
  pause
  exit /b 1
)
echo Apri http://127.0.0.1:8501 nel browser. Ctrl+C per chiudere.
".venv\Scripts\python.exe" run.py
pause
