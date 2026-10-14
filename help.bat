@echo off
title Help Menu - TG Drive RE

:menu
cls
echo.
echo ============================================================
echo              Help Menu - TG Drive RE
echo ============================================================
echo.
echo Choose an action:
echo.
echo 1. Start the program
echo 2. Test connection to Telegram
echo 3. Reset settings (if you have problems)
echo 4. Check system (Python, dependencies, 7-Zip)
echo 5. Open troubleshooting guide
echo 6. Install or update dependencies
echo 7. Exit
echo.
set /p choice="Enter number (1-7): "

if "%choice%"=="1" goto start_app
if "%choice%"=="2" goto test_connection
if "%choice%"=="3" goto reset_settings
if "%choice%"=="4" goto check_system
if "%choice%"=="5" goto open_troubleshooting
if "%choice%"=="6" goto install_deps
if "%choice%"=="7" goto exit

echo.
echo Invalid choice. Try again.
timeout /t 2 >nul
goto menu

:start_app
cls
echo.
echo Starting program...
echo.
call start.bat
goto menu

:test_connection
cls
echo.
echo Testing connection to Telegram...
echo.
call test_connection.bat
goto menu

:reset_settings
cls
call reset_settings.bat
goto menu

:check_system
cls
call start_with_check.bat
goto menu

:open_troubleshooting
cls
echo.
echo Opening troubleshooting guide...
echo.
if exist TROUBLESHOOTING.md (
    start TROUBLESHOOTING.md
    echo [OK] File opened
) else (
    echo [ERROR] TROUBLESHOOTING.md not found
)
echo.
pause
goto menu

:install_deps
cls
echo.
echo Installing / updating dependencies...
echo.
call install.bat
goto menu

:exit
exit
