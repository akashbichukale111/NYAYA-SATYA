@echo off
title NYAYA-SATYA OS — Unified Command Center
echo ==========================================================
echo            NYAYA-SATYA OPERATING SYSTEM (OS)              
echo    One Evidence Graph. Any Jurisdiction. Human Gate.      
echo ==========================================================

set VENV_PYTHON=D:\NYAYA-SATYA\unwind-live-verified-main\.venv\Scripts\python.exe
set PYTHONPATH=D:\NYAYA-SATYA\os

if not exist "%VENV_PYTHON%" (
    echo [ERROR] Python virtual environment not found at %VENV_PYTHON%
    pause
    exit /b 1
)

echo [INFO] Mounting 12 Modular Engines into Unified Gateway...
echo [INFO] Starting OS Shell on http://127.0.0.1:8000
echo [INFO] Press Ctrl+C to terminate.

"%VENV_PYTHON%" -m uvicorn gateway.main:app --host 127.0.0.1 --port 8000 --reload
pause
