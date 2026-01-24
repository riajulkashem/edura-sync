@echo off
echo Uninstalling EduraSync Windows Service...
echo This requires Administrative privileges.
echo.

REM Check for admin privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Please run this script as Administrator.
    pause
    exit /b 1
)

REM Stop the service
python scripts\install_service.py stop

REM Remove the service
python scripts\install_service.py remove

echo.
echo Uninstallation complete!
pause
