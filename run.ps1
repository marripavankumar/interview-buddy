$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

# Remove inherited Python path values so the venv interpreter uses its own stdlib cleanly.
Remove-Item Env:PYTHONHOME, Env:PYTHONPATH -ErrorAction SilentlyContinue

$pythonExe = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    throw "Virtual environment not found. Run .\bootstrap.ps1 first to create .venv and install dependencies."
}

& $pythonExe -E main.py
