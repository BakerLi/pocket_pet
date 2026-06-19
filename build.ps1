# Build a standalone PocketPet.exe that end users can run WITHOUT installing
# Python. Output: dist\PocketPet.exe  (single file, no console window).
#
#   Usage:  ./build.ps1
#
# Hand the resulting dist\PocketPet.exe to anyone on Windows; they just
# double-click it. State is saved under %APPDATA%\pocket_pet (see README for
# uninstall).

$ErrorActionPreference = "Stop"
$py = ".venv\Scripts\python.exe"

if (-not (Test-Path $py)) {
    throw "Virtualenv not found. Run:  python -m venv .venv  first."
}

Write-Host "==> Installing build dependencies (PyInstaller + app)..."
& $py -m pip install -e ".[dev]" | Out-Host

# A running instance locks dist\PocketPet.exe (PyInstaller can't overwrite it).
$running = Get-Process PocketPet -ErrorAction SilentlyContinue
if ($running) {
    Write-Host "==> Stopping running PocketPet.exe so it can be rebuilt..."
    $running | Stop-Process -Force
    Start-Sleep -Milliseconds 400
}

Write-Host "==> Building single-file exe..."
# No --add-data: sprite + tray icon are drawn procedurally, no asset files.
& $py -m PyInstaller --noconfirm --clean `
    --onefile --windowed `
    --name PocketPet `
    --paths src `
    packaging\launcher.py | Out-Host
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed (exit $LASTEXITCODE)."
}

$exe = "dist\PocketPet.exe"
if (Test-Path $exe) {
    Write-Host "`n==> Done. Built: $exe"
} else {
    throw "Build finished but $exe was not produced."
}
