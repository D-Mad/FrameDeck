$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Venv = Join-Path $ProjectRoot ".venv-build"
$Python = Join-Path $Venv "Scripts\python.exe"

if (-not (Test-Path $Python)) {
    py -3.10 -m venv $Venv
}

& $Python -m pip install --upgrade pip
& $Python -m pip install -r (Join-Path $ProjectRoot "requirements-windows.txt")
& $Python (Join-Path $ProjectRoot "scripts\fetch_aces12.py")
& $Python -m PyInstaller --noconfirm --clean (Join-Path $ProjectRoot "framedeck.spec")

Write-Host "Built: $ProjectRoot\dist\FrameDeck\FrameDeck.exe"
