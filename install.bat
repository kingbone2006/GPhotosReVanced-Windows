@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title Google Photos ReVanced - Automated Setup & Installer
cd /d "%~dp0"

echo ===================================================================
echo   Google Photos ReVanced - Windows Edition
echo   Automated Setup & Dependency Installer for Any Windows PC
echo ===================================================================
echo.

:: 1. Detect Python
set "PYTHON_EXE="

python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_EXE=python"
    goto :PYTHON_FOUND
)

py -3 --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_EXE=py -3"
    goto :PYTHON_FOUND
)

:: Check common default installation paths
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    goto :PYTHON_FOUND
)
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    goto :PYTHON_FOUND
)
if exist "%ProgramFiles%\Python311\python.exe" (
    set "PYTHON_EXE=%ProgramFiles%\Python311\python.exe"
    goto :PYTHON_FOUND
)

:: 2. Python not found: Automatic download and installation
echo [INFO] Python was not detected on this machine.
echo [INFO] Starting automatic Python 3.11 silent installation...
echo.

:: Try winget first if available
winget --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [Step] Installing Python 3.11 via Windows Package Manager (winget)...
    winget install Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements
    timeout /t 3 /nobreak >nul
)

:: Re-check if winget succeeded
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    goto :PYTHON_FOUND
)

:: Fallback: Download official python installer via PowerShell
echo [Step] Downloading official Python 3.11 64-bit installer...
set "INSTALLER_FILE=%TEMP%\python-3.11.9-amd64.exe"
powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe', '%INSTALLER_FILE%')"

if exist "%INSTALLER_FILE%" (
    echo [Step] Installing Python 3.11 quietly (Adding to PATH)...
    start /wait "" "%INSTALLER_FILE%" /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_test=0
    del /f /q "%INSTALLER_FILE%" >nul 2>&1
    timeout /t 3 /nobreak >nul
)

:: Refresh path variables
set "PATH=%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts;%PATH%"

if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    goto :PYTHON_FOUND
)

python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_EXE=python"
    goto :PYTHON_FOUND
)

echo.
echo [ERROR] Could not install Python automatically.
echo Please download and install Python manually from: https://www.python.org/downloads/
echo Make sure to check "Add python.exe to PATH" during installation.
pause
exit /b 1

:PYTHON_FOUND
echo [OK] Python detected:
%PYTHON_EXE% --version
echo.

:: 3. Setup Virtual Environment (venv)
if not exist "venv\Scripts\python.exe" (
    echo [1/3] Creating dedicated virtual environment (venv)...
    %PYTHON_EXE% -m venv venv
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created successfully.
) else (
    echo [1/3] Dedicated virtual environment (venv) already exists.
)
echo.

:: 4. Upgrade pip and install requirements
echo [2/3] Upgrading pip package manager...
venv\Scripts\python.exe -m pip install --upgrade pip --quiet

echo.
echo [3/3] Installing application dependencies from requirements.txt...
venv\Scripts\pip.exe install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] An error occurred while installing dependencies.
    echo Please check internet connection and try running install.bat again.
    pause
    exit /b 1
)

:: 5. Create Desktop Shortcut
echo.
echo Creating Desktop shortcut...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ws = New-Object -ComObject WScript.Shell; " ^
  "$s = $ws.CreateShortcut([IO.Path]::Combine([Environment]::GetFolderPath('Desktop'), 'Google Photos ReVanced.lnk')); " ^
  "$s.TargetPath = [IO.Path]::Combine('%~dp0', 'run.bat'); " ^
  "$s.WorkingDirectory = '%~dp0'; " ^
  "$s.Description = 'Google Photos ReVanced - Unlimited Pixel XL Backup'; " ^
  "$s.Save()" >nul 2>&1

echo.
echo ===================================================================
echo   [SUCCESS] INSTALLATION COMPLETED SUCCESSFULLY!
echo   [THANH CONG] CAI DAT HOAN TAT VA SAN SANG SU DUNG!
echo.
echo   - Virtual environment: %~dp0venv
echo   - Desktop shortcut: Google Photos ReVanced
echo.
echo   You can now launch the application by running run.bat
echo ===================================================================
echo.
pause
