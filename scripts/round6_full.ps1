# Offline manual reproduction. Acquisition is a separate explicit command.
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
if (-not (Test-Path -LiteralPath 'benchmarks/cache')) { throw 'Prepare the verified official cache through maintenance/round6_acquire --allow-network.' }
if (-not $env:BUROCRAZIA_TESSERACT_CMD) { throw 'Configure the actual local Tesseract executable.' }
$taskPython = '.venv/Scripts/python.exe'
& $taskPython -m maintenance.build_fingerprints_v2 --validate-only
if ($LASTEXITCODE) { throw 'Signature validation failed.' }
foreach ($kind in @('canonical','evaluate','filled','unknown')) {
    & $taskPython -m benchmarks.round6_recognition $kind
    if ($LASTEXITCODE) { throw "Benchmark $kind failed to execute." }
}
& $taskPython -m benchmarks.round6_family
if ($LASTEXITCODE) { throw 'Family benchmark execution failed.' }
& $taskPython -m benchmarks.evaluate --fast --coverage --output-dir benchmarks/results/round6/final
if ($LASTEXITCODE) { throw 'Historical gate failed.' }
& $taskPython -m benchmarks.ocr_gate --output benchmarks/results/round6/ocr_legacy_gate.json
if ($LASTEXITCODE) { throw 'Historical OCR failed.' }
& $taskPython -m benchmarks.files ocr --manifest benchmarks/corpora/ocr_synthetic_v2.json --output benchmarks/results/round6/ocr_synthetic_v2.json
if ($LASTEXITCODE) { throw 'Synthetic OCR failed.' }
& $taskPython -m benchmarks.round6_performance
if ($LASTEXITCODE) { throw 'Performance execution failed.' }
# Calibration is deliberately excluded: a frozen profile cannot be retuned.
