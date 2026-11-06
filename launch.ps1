$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
Set-Location -LiteralPath $PSScriptRoot
$runtimePython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if (Test-Path -LiteralPath $runtimePython) {
    & $runtimePython (Join-Path $PSScriptRoot 'server.py')
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    py -3 (Join-Path $PSScriptRoot 'server.py')
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    python (Join-Path $PSScriptRoot 'server.py')
} else {
    Write-Host 'Python 3.10+ is required. Install Python, then run this launcher again.'
    Read-Host 'Press Enter to exit'
}
