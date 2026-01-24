@echo off
echo Installing EduraSync Windows Service...
echo This requires Administrative privileges.
echo.

REM Check for admin privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Please run this script as Administrator.
    pause
    exit /b 1
)

REM Install the service
python scripts\install_service.py install

REM Set to auto-start
python scripts\install_service.py update --start auto

REM Start the service
python scripts\install_service.py start

echo.
echo Installation complete! 
echo Service "EduraSyncService" is now running in the background.
pause
