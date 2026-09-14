@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1
title Google Photos ReVanced - Console Debug
cd /d "%~dp0"

:: Check if virtual environment exists; if not, auto-run install.bat
if not exist "venv\Scripts\python.exe" (
    echo ===================================================================
    echo   [INFO] Virtual environment not found.
    echo   Running automated setup first...
    echo ===================================================================
    echo.
    call install.bat
    if not exist "venv\Scripts\python.exe" (
        echo [ERROR] Installation failed or was aborted. Cannot start application.
        pause
        exit /b 1
    )
)

echo ===================================================================
echo   Google Photos ReVanced - Windows Edition (Console Debug Mode)
echo   Real-time multi-threaded upload and synchronization engine
echo ===================================================================
echo.

venv\Scripts\python.exe main.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ===================================================================
    echo [ERROR] Application exited with error code: %ERRORLEVEL%
    echo Check the error trace above for debugging.
    echo ===================================================================
    pause
) else (
    echo.
    echo Application closed normally.
)
