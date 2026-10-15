# Manual local benchmark; official cache and OCR are intentionally absent from CI.
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
if (-not (Test-Path -LiteralPath 'benchmarks/cache')) { throw 'Prepare verified official cache with maintenance/build_fingerprints first.' }
if (-not $env:BUROCRAZIA_TESSERACT_CMD) { throw 'Configure BUROCRAZIA_TESSERACT_CMD for actual local OCR.' }
$python = '.venv/Scripts/python.exe'
& $python -m maintenance.build_fingerprints --validate-only
if ($LASTEXITCODE) { throw 'Fingerprint validation failed.' }
foreach ($kind in @('canonical','robustness','family','unknown')) {
    & $python -m benchmarks.round5_recognition $kind
    if ($LASTEXITCODE) { throw "Benchmark $kind failed to execute." }
}
& $python -m benchmarks.evaluate --fast --coverage --output-dir benchmarks/results/round5/final
if ($LASTEXITCODE) { throw 'Historical benchmark gate failed.' }
& $python -m benchmarks.ocr_gate --output benchmarks/results/round5/ocr_legacy_gate.json
if ($LASTEXITCODE) { throw 'Historical OCR gate failed.' }
& $python -m benchmarks.files ocr --manifest benchmarks/corpora/ocr_synthetic_v2.json --output benchmarks/results/round5/ocr_synthetic_v2.json
if ($LASTEXITCODE) { throw 'Synthetic OCR gate failed.' }
& $python -m benchmarks.round5_performance
if ($LASTEXITCODE) { throw 'Performance measurement failed.' }
# Unit tests and report generation are kept explicit; never downloads implicitly.
