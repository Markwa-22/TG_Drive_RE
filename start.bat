@echo off
title TG Drive RE - Telegram Cloud Storage (Async Edition)
cd /d "%~dp0"

REM Use the .venv created by install.bat, otherwise the system Python
set "PY=python"
if exist "%~dp0.venv\Scripts\python.exe" set "PY=%~dp0.venv\Scripts\python.exe"

echo.
echo ============================================================
echo            TG Drive RE - Remastered Edition
echo         Secure Cloud Storage powered by Telegram
echo              [ASYNC OPTIMIZED - 2-5x FASTER]
echo ============================================================
echo.

REM Check Python
"%PY%" --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Install Python 3.9 or newer.
    echo [ERROR] Python ne nayden! Ustanovite Python 3.9 ili novee.
    echo [ERROR] Or run install.bat - it sets everything up automatically.
    echo.
    pause
    exit /b 1
)

echo [INFO] Starting TG Drive RE with async optimizations...
echo [INFO] Zapusk TG Drive RE s async optimizatsiyami...
echo.

REM Start application
"%PY%" main.py

REM If error occurred
if errorlevel 1 (
    echo.
    echo [ERROR] Program terminated with error!
    echo [ERROR] Programma zavershilas s oshibkoy!
    echo.
    echo Possible causes / Vozmozhnye prichiny:
    echo - Dependencies not installed / Zavisimosti ne ustanovleny
    echo   Solution / Reshenie: run install.bat
    echo.
    echo - Telegram API not configured / Telegram API ne nastroyen
    echo   Solution / Reshenie: Follow instructions on first run
    echo.
    pause
)
