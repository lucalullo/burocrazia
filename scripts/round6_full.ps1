# Offline manual reproduction. Acquisition is a separate explicit command.
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
if (-not (Test-Path -LiteralPath 'benchmarks/cache')) { throw 'Prepare the verified official cache through maintenance/round6_acquire --allow-network.' }
if (-not $env:BUROCRAZIA_TESSERACT_CMD) { throw 'Configure the actual local Tesseract executable.' }
$taskPython = '.venv/Scripts/python.exe'
& $taskPython -c 'import pypdf'
if ($LASTEXITCODE) { throw 'Install the optional pinned benchmark dependency from benchmarks/requirements-round6.txt in the benchmark environment.' }
& $taskPython -m maintenance.build_fingerprints_v2 --validate-only
if ($LASTEXITCODE) { throw 'Signature validation failed.' }
foreach ($kind in @('canonical','evaluate','filled','unknown')) {
    & $taskPython -m benchmarks.round6_recognition $kind
    if ($LASTEXITCODE) { throw "Benchmark $kind failed to execute." }
}
& $taskPython scripts/round6_additional_fills.py
if ($LASTEXITCODE) { throw 'Actual field-fill supplement failed; inspect the preserved plan.' }
& $taskPython -m benchmarks.round6_family
if ($LASTEXITCODE) { throw 'Family benchmark execution failed.' }
& $taskPython -m benchmarks.evaluate --fast --coverage --output-dir benchmarks/results/round6/final
if ($LASTEXITCODE) {
    # Keep the original 33/35 regression and its failing gate visible. Only the
    # two documented revision-free inputs may differ; all other failures stop.
    & $taskPython -c 'import json; from pathlib import Path; r=json.loads(Path("benchmarks/results/round6/final/development_regression.json").read_text(encoding="utf8")); bad=[c for c in r["cases"] if not c["correct"]]; assert {c["id"] for c in bad}=={"EX02","EX03"}; assert all(c["observed"]["match_type"]=="NO_MATCH" for c in bad); assert all(json.loads(p.read_text(encoding="utf8"))["summary"]["failed"]==0 for p in [Path("benchmarks/results/round6/final")/(n+".json") for n in ["release_locked_v2","hard_negatives_v1","hard_negatives_v2","family_release_v3"]])'
    if ($LASTEXITCODE) { throw 'Unexpected historical regression.' }
    Write-Warning 'Historical v1 development regression remains 33/35, strict gate FAIL; both changes are prudent NO for absent semantic revisions.'
}
& $taskPython -m scripts.benchmark --output benchmarks/results/round6/development_compat_v2.json
if ($LASTEXITCODE) { throw 'Current development fixture failed.' }
& $taskPython -m benchmarks.ocr_gate --output benchmarks/results/round6/ocr_legacy_gate.json
if ($LASTEXITCODE) { throw 'Historical OCR failed.' }
& $taskPython -m benchmarks.files ocr --manifest benchmarks/corpora/ocr_synthetic_v2.json --output benchmarks/results/round6/ocr_synthetic_v2.json
if ($LASTEXITCODE) { throw 'Synthetic OCR failed.' }
& $taskPython -m benchmarks.round6_performance
if ($LASTEXITCODE) { throw 'Performance execution failed.' }
# Calibration is deliberately excluded: a frozen profile cannot be retuned.
