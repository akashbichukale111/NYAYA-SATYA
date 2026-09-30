# NYAYA-SATYA OS — Launch Script (PowerShell)
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "           NYAYA-SATYA OPERATING SYSTEM (OS)              " -ForegroundColor Yellow
Write-Host "   One Evidence Graph. Any Jurisdiction. Human Gate.      " -ForegroundColor White
Write-Host "==========================================================" -ForegroundColor Cyan

$VENV_PYTHON = "D:\NYAYA-SATYA\unwind-live-verified-main\.venv\Scripts\python.exe"
$env:PYTHONPATH = "D:\NYAYA-SATYA\os"

if (-not (Test-Path $VENV_PYTHON)) {
    Write-Host "[ERROR] Python virtual environment not found at $VENV_PYTHON" -ForegroundColor Red
    exit 1
}

Write-Host "[INFO] Mounting 12 Modular Engines into Unified Gateway..." -ForegroundColor Green
Write-Host "[INFO] Starting OS Shell & Gateway on http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "[INFO] Press Ctrl+C to terminate." -ForegroundColor Gray

& $VENV_PYTHON -m uvicorn gateway.main:app --host 127.0.0.1 --port 8000 --reload
