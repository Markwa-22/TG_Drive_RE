@echo off
REM ============================================================================
REM  TG Drive RE - installer
REM  Installs all dependencies, optionally into an isolated .venv environment,
REM  checks 7-Zip and verifies that the modules really import.
REM  Safe to run again at any time (it updates / re-checks).
REM ============================================================================
title TG Drive RE - Installer
cd /d "%~dp0"
setlocal

echo.
echo ============================================================
echo            TG Drive RE - Installer
echo         Setting up dependencies for Telegram Cloud
echo ============================================================
echo.

REM ---------------- [1/5] Python ----------------
echo [1/5] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [X] Python not found!
    echo     1. Download Python 3.9 or newer: https://www.python.org/downloads/
    echo     2. During setup enable "Add python.exe to PATH"
    echo [X] Python ne nayden! Ustanovite Python 3.9+ s python.org
    echo.
    echo [!] If the Microsoft Store just opened instead, switch off the
    echo     "python.exe" app execution alias in Windows Settings.
    echo.
    pause
    exit /b 1
)
set "PYVER="
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set "PYVER=%%i"
echo [OK] Python %PYVER%

REM ---------------- [2/5] Isolated environment ----------------
echo.
echo [2/5] Isolated environment .venv
echo      Recommended: packages go into .venv and your system Python
echo      stays untouched. Delete the .venv folder to undo it.
echo.
echo Create .venv now? (Y/n)
set "answer=Y"
set /p answer=
set "USE_VENV=1"
if /i "%answer%"=="n" set "USE_VENV=0"
if "%USE_VENV%"=="1" if exist ".venv\Scripts\python.exe" echo [OK] .venv already exists
if "%USE_VENV%"=="1" if not exist ".venv\Scripts\python.exe" python -m venv .venv
if "%USE_VENV%"=="1" if not exist ".venv\Scripts\python.exe" echo [X] Could not create .venv - using system Python
if "%USE_VENV%"=="1" if not exist ".venv\Scripts\python.exe" set "USE_VENV=0"
if "%USE_VENV%"=="0" echo [!] Using system Python

REM ---------------- [3/5] Packages ----------------
set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
echo.
echo [3/5] Installing packages from requirements.txt
echo      interpreter: %PY%
echo.
"%PY%" -m pip install --upgrade pip >nul 2>&1
"%PY%" -m pip install -r requirements.txt
set "PIP_RC=%errorlevel%"
if not "%PIP_RC%"=="0" (
    echo.
    echo [X] Installation failed! ^(pip exit code %PIP_RC%^)
    echo     Check your internet connection or proxy and run install.bat again.
    echo.
    pause
    exit /b 1
)

REM ---------------- [4/5] Verify ----------------
echo.
echo [4/5] Checking installed modules...
"%PY%" -c "import pyrogram, eel, PIL, cv2, bs4, requests, aiofiles" >nul 2>&1
if errorlevel 1 (
    echo [X] Some required modules are missing!
    echo     Try manually: "%PY%" -m pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)
echo [OK] pyrogram, eel, Pillow, opencv, bs4, requests, aiofiles
"%PY%" -c "import TgCrypto" >nul 2>&1
if errorlevel 1 (
    echo [!] TgCrypto missing ^(optional: makes transfers much faster^)
) else (
    echo [OK] TgCrypto ^(fast encryption^)
)

REM ---------------- [5/5] 7-Zip ----------------
echo.
echo [5/5] Checking 7-Zip...
set "HAS_7Z=1"
where 7z >nul 2>&1
if errorlevel 1 set "HAS_7Z=0"
if exist "C:\Program Files\7-Zip\7z.exe" set "HAS_7Z=1"
if exist "C:\Program Files (x86)\7-Zip\7z.exe" set "HAS_7Z=1"
if "%HAS_7Z%"=="1" echo [OK] 7-Zip found
if "%HAS_7Z%"=="1" goto after_7z
echo [!] 7-Zip not found. It is required for files above the Telegram
echo     limit and for packing folders into archives.
echo.
echo Install 7-Zip now with winget? (Y/n)
set "answer7=Y"
set /p answer7=
if /i "%answer7%"=="n" echo [!] Skipped. Later: winget install 7zip.7zip
if /i "%answer7%"=="n" goto after_7z
where winget >nul 2>&1
if errorlevel 1 echo [!] winget not found. Get 7-Zip manually: https://www.7-zip.org/
if not errorlevel 1 winget install 7zip.7zip --accept-source-agreements --accept-package-agreements
if not errorlevel 1 echo [OK] 7-Zip installed
if not errorlevel 1 goto after_7z
echo [!] winget could not install 7-Zip. Get it manually: https://www.7-zip.org/

:after_7z
echo.
echo ============================================================
echo                     SETUP COMPLETE
echo ============================================================
echo.
echo Next steps:
echo   1. start.bat            - launch the application
echo   2. first run asks for phone number, api_id and api_hash
echo      (get them at https://my.telegram.org)
echo.
echo Start the application now? (Y/n)
set "runapp=Y"
set /p runapp=
if /i "%runapp%"=="n" goto done
call start.bat
echo.
echo Application closed.
exit /b 0

:done
echo.
echo Done. Launch the app later with start.bat
pause
exit /b 0
