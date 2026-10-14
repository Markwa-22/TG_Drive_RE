@echo off
title Reset Settings - TG Drive RE

echo.
echo ============================================================
echo          Reset Settings - TG Drive RE
echo ============================================================
echo.
echo WARNING! This will delete all settings and authorization.
echo You will need to enter again:
echo   - API ID and API Hash
echo   - Phone number
echo   - Code from Telegram
echo.
echo Files to be deleted:
echo   - config.ini (API keys)
echo   - TelegramCloud.session (session)
echo   - settings.json (settings)
echo.
echo Database files (path.bd) will NOT be deleted.
echo.
set /p confirm="Continue? (y/n): "

if /i not "%confirm%"=="y" (
    echo.
    echo Cancelled.
    pause
    exit /b
)

echo.
echo Deleting files...
echo.

if exist config.ini (
    del config.ini
    echo [OK] config.ini deleted
) else (
    echo [SKIP] config.ini not found
)

if exist TelegramCloud.session (
    del TelegramCloud.session
    echo [OK] TelegramCloud.session deleted
) else (
    echo [SKIP] TelegramCloud.session not found
)

if exist settings.json (
    del settings.json
    echo [OK] settings.json deleted
) else (
    echo [SKIP] settings.json not found
)

echo.
echo ============================================================
echo Reset completed!
echo ============================================================
echo.
echo Now run: start.bat
echo And enter your credentials again.
echo.
pause
