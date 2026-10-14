@echo off
title TG Drive RE - Startup with Checks

echo.
echo ============================================================
echo            TG Drive RE - Remastered Edition
echo              Startup with System Checks
echo ============================================================
echo.

REM Check Python
echo [1/4] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [X] Python not found!
    echo     Install Python 3.8+ from https://www.python.org/
    pause
    exit /b 1
) else (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do echo [OK] Python %%i installed
)

REM Check dependencies
echo [2/4] Checking dependencies...
python -c "import pyrogram, eel, aiofiles" >nul 2>&1
if errorlevel 1 (
    echo [X] Dependencies not installed!
    echo.
    echo Install now? (Y/N)
    set /p install_deps=
    if /i "%install_deps%"=="Y" (
        echo Installing dependencies...
        pip install -r requirements.txt
        if errorlevel 1 (
            echo [X] Installation error!
            pause
            exit /b 1
        )
        echo [OK] Dependencies installed!
    ) else (
        echo Run: pip install -r requirements.txt
        pause
        exit /b 1
    )
) else (
    echo [OK] All dependencies installed
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
python main.py

if errorlevel 1 (
    echo.
    echo [ERROR] Program terminated with error!
    pause
)
