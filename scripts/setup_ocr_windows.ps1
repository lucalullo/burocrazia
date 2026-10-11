param(
    [switch]$AllowNetwork,
    [string]$SevenZip = "$env:ProgramFiles\7-Zip\7z.exe"
)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path $PSScriptRoot -Parent
$taskWork = Join-Path $taskRoot 'benchmarks\work\tesseract'
$taskDownload = Join-Path $taskRoot 'tmp-build\tesseract-install'
$taskInstaller = Join-Path $taskDownload 'tesseract-5.4.0.exe'
$taskUrl = 'https://github.com/UB-Mannheim/tesseract/releases/download/v5.4.0.20240606/tesseract-ocr-w64-setup-5.4.0.20240606.exe'
$taskHash = 'c885fff6998e0608ba4bb8ab51436e1c6775c2bafc2559a19b423e18678b60c9'
if (-not (Test-Path -LiteralPath $SevenZip)) { throw '7-Zip is required to extract the pinned installer without installing globally.' }
New-Item -ItemType Directory -Path $taskDownload,$taskWork -Force | Out-Null
if (-not (Test-Path -LiteralPath $taskInstaller)) {
    if (-not $AllowNetwork) { throw 'Missing local installer; use -AllowNetwork to acquire the pinned package.' }
    Invoke-WebRequest -Uri $taskUrl -OutFile $taskInstaller -TimeoutSec 120
}
if ((Get-FileHash -LiteralPath $taskInstaller -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskHash) { throw 'Installer SHA-256 mismatch.' }
& $SevenZip x $taskInstaller "-o$taskWork" -y | Out-Null
if ($LASTEXITCODE -ne 0) { throw '7-Zip extraction failed.' }
$taskLanguages = @{
    ita = 'b8f89e1e785118dac4d51ae042c029a64edb5c3ee42ef73027a6d412748d8827'
    eng = '7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2'
    osd = '9cf5d576fcc47564f11265841e5ca839001e7e6f38ff7f7aacf46d15a96b00ff'
}
foreach ($taskLanguage in $taskLanguages.Keys) {
    $taskData = Join-Path $taskWork "tessdata\$taskLanguage.traineddata"
    if (-not (Test-Path -LiteralPath $taskData)) {
        if (-not $AllowNetwork) { throw "Missing $taskLanguage language; use -AllowNetwork." }
        Invoke-WebRequest -Uri "https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/$taskLanguage.traineddata" -OutFile $taskData -TimeoutSec 45
    }
    if ((Get-FileHash -LiteralPath $taskData -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskLanguages[$taskLanguage]) { throw "Language SHA-256 mismatch: $taskLanguage. A reviewed setup update is required." }
}
$env:BUROCRAZIA_TESSERACT_CMD = Join-Path $taskWork 'tesseract.exe'
& $env:BUROCRAZIA_TESSERACT_CMD --version
& $env:BUROCRAZIA_TESSERACT_CMD --list-langs
Write-Output 'Configured in this PowerShell session. Binaries and language data remain in ignored local work/cache directories.'
