@echo off
echo Configuring EduraSync to start automatically on login...
echo.

set EXE_PATH=%~dp0..\dist\EduraSync\EduraSync.exe

if not exist "%EXE_PATH%" (
    echo [ERROR] EduraSync.exe not found at %EXE_PATH%
    echo Please build the application first.
    pause
    exit /b 1
)

REM Add to Registry for current user
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "EduraSync" /t REG_SZ /d "\"%EXE_PATH%\" --headless" /f

echo.
echo Configuration complete! EduraSync will start in headless mode when you log in.
pause
