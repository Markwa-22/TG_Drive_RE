@echo off
title TG Drive RE - Startup with Checks
cd /d "%~dp0"

REM Use the .venv created by install.bat, otherwise the system Python
set "PY=python"
if exist "%~dp0.venv\Scripts\python.exe" set "PY=%~dp0.venv\Scripts\python.exe"

echo.
echo ============================================================
echo            TG Drive RE - Remastered Edition
echo              Startup with System Checks
echo ============================================================
echo.

REM Check Python
echo [1/4] Checking Python...
"%PY%" --version >nul 2>&1
if errorlevel 1 (
    echo [X] Python not found!
    echo     Install Python 3.9+ from https://www.python.org/
    echo     Or run install.bat - it sets everything up automatically.
    pause
    exit /b 1
) else (
    for /f "tokens=2" %%i in ('"%PY%" --version 2^>^&1') do echo [OK] Python %%i installed
)

REM Check dependencies
echo [2/4] Checking dependencies...
"%PY%" -c "import pyrogram, eel, aiofiles" >nul 2>&1
if not errorlevel 1 echo [OK] All dependencies installed
if errorlevel 1 call install.bat
REM install.bat may have created .venv - switch to it from now on
set "PY=python"
if exist "%~dp0.venv\Scripts\python.exe" set "PY=%~dp0.venv\Scripts\python.exe"
"%PY%" -c "import pyrogram, eel, aiofiles" >nul 2>&1
if errorlevel 1 (
    echo [X] Dependencies still missing!
    echo     Run install.bat, then start the application again.
    pause
    exit /b 1
)

REM Check 7-Zip
echo [3/4] Checking 7-Zip...
where 7z >nul 2>&1
if errorlevel 1 (
    echo [!] 7-Zip not found (optional for files ^>2GB)
    echo     Install: winget install 7zip.7zip
) else (
    echo [OK] 7-Zip installed
)

REM Check data file
echo [4/4] Checking data file...
if exist "path.bd" (
    echo [OK] path.bd found
) else (
    echo [OK] Fresh installation ^(path.bd will be created on the first upload^)
)

echo.
echo ============================================================
echo All checks passed! Starting application...
echo ============================================================
echo.
timeout /t 2 >nul

REM Start application
"%PY%" main.py

if errorlevel 1 (
    echo.
    echo [ERROR] Program terminated with error!
    pause
)
