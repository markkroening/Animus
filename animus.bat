@echo off
setlocal enabledelayedexpansion

:: Get the directory where this batch file is located
set "SCRIPT_DIR=%~dp0"
set "ANIMUS_EXE=%SCRIPT_DIR%animus_cli\main.py"
set "LOG_DIR=%LOCALAPPDATA%\Animus\logs"
set "LOG_FILE=%LOG_DIR%\animus_logs.json"
set "PS_SCRIPT=%SCRIPT_DIR%powershell\collect_logs.ps1"

:: Check if Python is installed
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python and try again
    pause
    exit /b 1
)

:: Check if the main script exists
if not exist "%ANIMUS_EXE%" (
    echo Error: Animus main script not found at "%ANIMUS_EXE%"
    echo Please ensure the application is properly installed
    pause
    exit /b 1
)

:: Ensure logs directory exists
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

:: Add the installation directory to PYTHONPATH
set "PYTHONPATH=%SCRIPT_DIR%;%PYTHONPATH%"

:: Run PowerShell script to collect logs
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" -OutputFile "%LOG_FILE%"

:: Check if log file was created and has content
if not exist "%LOG_FILE%" (
    echo Error: Log file was not created at "%LOG_FILE%"
    pause
    exit /b 1
)

:: Run Animus with explicit output path and interactive mode
python "%ANIMUS_EXE%" --output "%LOG_FILE%" --interactive

endlocal