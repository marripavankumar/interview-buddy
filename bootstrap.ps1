$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

# Clear inherited Python settings that can poison the interpreter and break venv creation.
Remove-Item Env:PYTHONHOME, Env:PYTHONPATH -ErrorAction SilentlyContinue

$pythonLauncher = Get-Command py -ErrorAction SilentlyContinue
if (-not $pythonLauncher) {
    throw "Python launcher 'py' was not found on PATH. Install Python for Windows or use the official launcher first."
}

if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..."
    & py -m venv .venv
}

Write-Host "Upgrading pip..."
& .\.venv\Scripts\python.exe -m pip install --upgrade pip

Write-Host "Installing project dependencies..."
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt

Write-Host "Starting Interview Buddy..."
& .\.venv\Scripts\python.exe -E main.py
