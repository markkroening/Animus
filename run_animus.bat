@echo off
echo Animus Security Log Analyzer
echo ===========================
echo This tool collects and analyzes Windows event logs for security incidents.
echo Administrator privileges are required to access security logs.
echo.

:: Set codepage to UTF-8 for proper JSON encoding
chcp 65001 > nul

:: Check for admin rights
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo WARNING: Not running with administrator privileges. Security logs may be inaccessible.
    echo For full functionality, please run as Administrator.
    echo.
)

:: Check for Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in the PATH.
    echo Please install Python 3.8 or higher from https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Install required packages directly
echo Installing required Python packages...
python -m pip install colorama tabulate pyreadline3
if %errorlevel% neq 0 (
    echo Failed to install required packages.
    pause
    exit /b 1
)

:: Run log collection
echo.
echo Collecting Windows Event Logs...
PowerShell -NoProfile -ExecutionPolicy Bypass -Command "& '%~dp0powershell\collect_logs.ps1' -OutputFile '%~dp0animus_logs.json'"
if %errorlevel% neq 0 (
    echo Failed to collect logs. Please check the error messages above.
    pause
    exit /b 1
)

:: Run the analysis
echo.
echo Starting log analysis...
python "%~dp0animus_cli\main.py" --output "%~dp0animus_logs.json" --interactive
if %errorlevel% neq 0 (
    echo The analysis process exited with an error. Please check the error messages above.
    pause
    exit /b 1
)

echo.
echo Analysis complete.
pause 