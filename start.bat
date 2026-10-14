@echo off
title TG Drive RE - Telegram Cloud Storage (Async Edition)

echo.
echo ============================================================
echo            TG Drive RE - Remastered Edition
echo         Secure Cloud Storage powered by Telegram
echo              [ASYNC OPTIMIZED - 2-5x FASTER]
echo ============================================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Install Python 3.8 or newer.
    echo [ERROR] Python ne nayden! Ustanovite Python 3.8 ili novee.
    echo.
    pause
    exit /b 1
)

echo [INFO] Starting TG Drive RE with async optimizations...
echo [INFO] Zapusk TG Drive RE s async optimizatsiyami...
echo.

REM Start application
python main.py

REM If error occurred
if errorlevel 1 (
    echo.
    echo [ERROR] Program terminated with error!
    echo [ERROR] Programma zavershilas s oshibkoy!
    echo.
    echo Possible causes / Vozmozhnye prichiny:
    echo - Dependencies not installed / Zavisimosti ne ustanovleny
    echo   Solution / Reshenie: pip install -r requirements.txt
    echo.
    echo - Telegram API not configured / Telegram API ne nastroyen
    echo   Solution / Reshenie: Follow instructions on first run
    echo.
    pause
)
