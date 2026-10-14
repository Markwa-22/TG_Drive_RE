@echo off
title Test Connection - TG Drive RE
cd /d "%~dp0"

REM Use the .venv created by install.bat, otherwise the system Python
set "PY=python"
if exist "%~dp0.venv\Scripts\python.exe" set "PY=%~dp0.venv\Scripts\python.exe"

echo.
echo ============================================================
echo            Test Connection - TG Drive RE
echo ============================================================
echo.

"%PY%" scripts\test_auth.py

pause
