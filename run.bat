@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1
title Google Photos ReVanced - Windows Edition
cd /d "%~dp0"

echo ===================================================================
echo   Google Photos ReVanced - All-in-One Launcher
echo   Unlimited Original Quality Cloud Backup (Pixel XL Emulation)
echo ===================================================================
echo.

:: 1. If virtual environment already exists and works, launch app immediately
if exist "venv\Scripts\python.exe" goto :RUN_APP

:: 2. If venv does not exist, detect Python on the system
echo [1/3] Checking for Python installation...
set "SYSTEM_PYTHON="

python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "SYSTEM_PYTHON=python"
    goto :PYTHON_READY
)

py -3 --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "SYSTEM_PYTHON=py -3"
    goto :PYTHON_READY
)

:: Check common default installation paths
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "SYSTEM_PYTHON=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    goto :PYTHON_READY
)
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "SYSTEM_PYTHON=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    goto :PYTHON_READY
)
if exist "%ProgramFiles%\Python311\python.exe" (
    set "SYSTEM_PYTHON=%ProgramFiles%\Python311\python.exe"
    goto :PYTHON_READY
)

:: 3. Python is missing: Automatically download and install Python 3.11
echo [INFO] Python not found on this system.
echo [INFO] Starting automatic background installation of Python 3.11...
echo.

:: Try winget first if available
winget --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [Step] Installing Python 3.11 via Windows Package Manager (winget)...
    winget install Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements
    timeout /t 3 /nobreak >nul
)

if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "SYSTEM_PYTHON=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    goto :PYTHON_READY
)

:: Fallback: Download official Python installer via PowerShell
echo [Step] Downloading official Python 3.11 installer...
set "INSTALLER_FILE=%TEMP%\python-3.11.9-amd64.exe"
powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe', '%INSTALLER_FILE%')"

if exist "%INSTALLER_FILE%" (
    echo [Step] Installing Python 3.11 quietly (Adding to PATH)...
    start /wait "" "%INSTALLER_FILE%" /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_test=0
    del /f /q "%INSTALLER_FILE%" >nul 2>&1
    timeout /t 3 /nobreak >nul
)

set "PATH=%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts;%PATH%"

if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "SYSTEM_PYTHON=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    goto :PYTHON_READY
)

python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "SYSTEM_PYTHON=python"
    goto :PYTHON_READY
)

echo.
echo [ERROR] Could not install Python automatically.
echo Please install Python manually from: https://www.python.org/downloads/
echo (Remember to check "Add python.exe to PATH")
pause
exit /b 1

:PYTHON_READY
echo [OK] Python detected:
%SYSTEM_PYTHON% --version
echo.

:: 4. Create Virtual Environment
echo [2/3] Setting up virtual environment (venv)...
%SYSTEM_PYTHON% -m venv venv
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)

:: 5. Install all required dependencies from requirements.txt
echo [3/3] Installing all required libraries from requirements.txt...
venv\Scripts\python.exe -m pip install --upgrade pip --quiet
venv\Scripts\pip.exe install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Failed to install required libraries.
    echo Please check internet connection and try running run.bat again.
    pause
    exit /b 1
)
echo.
echo ===================================================================
echo   [OK] All dependencies installed successfully!
echo   Launching application now...
echo ===================================================================
echo.

:RUN_APP
echo Starting Google Photos ReVanced engine...
echo.
venv\Scripts\python.exe main.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ===================================================================
    echo [ERROR] Application exited with code: %ERRORLEVEL%
    echo Check error trace above for details.
    echo ===================================================================
    pause
) else (
    echo.
    echo Application closed normally.
)
