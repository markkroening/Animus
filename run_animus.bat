@echo off
setlocal enabledelayedexpansion

:: --- Define Python Path ---
:: Explicitly set the path to the correct Python installation
set "PYTHON_EXE=C:\Python313\python.exe"

:: Initial setup - keep title visible
echo Animus Event Log Analyzer
echo ===========================
echo.

:: Set codepage silently
chcp 65001

:: --- Python Check ---
echo Checking Python installation...
"%PYTHON_EXE%" --version
if errorlevel 1 (
    echo Python not found at %PYTHON_EXE%.
    echo Please check the PYTHON_EXE variable in this script.
    goto error
)

:: --- Install Packages Check ---
echo Installing required Python packages using %PYTHON_EXE%...
"%PYTHON_EXE%" -m pip install colorama tabulate pyreadline3 google-genai python-dotenv
if errorlevel 1 (
    echo Failed to install required packages.
    echo Please check your internet connection and pip configuration.
    goto error
)

:: --- Clear initial checks and proceed ---
cls
echo Animus Event Log Analyzer
echo ===========================
echo All checks passed. Preparing to analyze logs...
echo.

:: --- Run log collection ---
echo Collecting Windows Event Logs...
PowerShell -NoProfile -ExecutionPolicy Bypass -Command "& '%~dp0powershell\collect_logs.ps1' -OutputFile '%~dp0logs\animus_logs.json'"
if errorlevel 1 (
    echo Failed to collect logs. Please check the error messages above.
    goto error
)

:: Display simplified instructions for interactive mode
echo.
echo ===================================================
echo Entering interactive Q^&A mode...
echo ===================================================
echo.
echo - Type your questions about the logs

:: --- Run the analysis --- (Keep output visible)
cls
echo Animus Event Log Analyzer
echo =====================================
echo Analyzing logs. This may take a few minutes...
echo.

cd /d "%~dp0"
"%PYTHON_EXE%" "animus_cli.py" --qa

:: --- Completion ---
echo.
echo Analysis complete.
goto end

:error
echo.
echo ===================================================
echo          SETUP ERROR DETECTED
echo ===================================================
echo Error occurred. Please fix the issues listed above and try again.

:end
endlocal