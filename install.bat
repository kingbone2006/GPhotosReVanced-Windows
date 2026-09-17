@echo off
chcp 65001 >nul
title Google Photos ReVanced - Automated Installer
cd /d "%~dp0"

echo ===================================================================
echo   Google Photos ReVanced - Setup ^& Dependency Installer
echo ===================================================================
echo.

:: 1. Check for Python
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

echo [INFO] Python not found. Attempting to install Python 3.11 via winget...
winget install Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements >nul 2>&1

if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "SYSTEM_PYTHON=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    goto :PYTHON_READY
)

python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "SYSTEM_PYTHON=python"
    goto :PYTHON_READY
)

echo [ERROR] Python could not be found or installed automatically.
echo Please install Python 3.10+ from https://www.python.org/downloads/
echo (Make sure to check 'Add python.exe to PATH')
pause
exit /b 1

:PYTHON_READY
echo [OK] Using Python:
%SYSTEM_PYTHON% --version
echo.

:: 2. Create Virtual Environment
echo [2/3] Setting up virtual environment (venv)...
if not exist "venv\Scripts\python.exe" (
    %SYSTEM_PYTHON% -m venv venv
)
if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)

:: 3. Install Requirements
echo [3/3] Installing dependencies from requirements.txt...
venv\Scripts\python.exe -m pip install --upgrade pip --quiet
venv\Scripts\pip.exe install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Dependency installation encountered errors.
    pause
    exit /b 1
)

:: 4. Create Desktop Shortcut
echo [INFO] Creating Desktop Shortcut...
powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut([IO.Path]::Combine([Environment]::GetFolderPath('Desktop'), 'Google Photos ReVanced.lnk')); $s.TargetPath = '%~dp0run.bat'; $s.WorkingDirectory = '%~dp0'; if (Test-Path '%~dp0assets\icon.ico') { $s.IconLocation = '%~dp0assets\icon.ico' }; $s.Save()" >nul 2>&1

echo.
echo ===================================================================
echo   [SUCCESS] Setup complete! You can now launch the app:
echo     - Desktop Shortcut: "Google Photos ReVanced"
echo     - Or double-click: run.bat
echo ===================================================================
echo.
pause
