@echo off
setlocal enabledelayedexpansion

:: --- Define Python Path ---
:: Try to find Python in common locations
set "PYTHON_EXE="
for %%p in (
    "%ProgramFiles%\Python313\python.exe"
    "%ProgramFiles%\Python312\python.exe"
    "%ProgramFiles%\Python311\python.exe"
    "%ProgramFiles%\Python310\python.exe"
    "%ProgramFiles(x86)%\Python313\python.exe"
    "%ProgramFiles(x86)%\Python312\python.exe"
    "%ProgramFiles(x86)%\Python311\python.exe"
    "%ProgramFiles(x86)%\Python310\python.exe"
    "%LocalAppData%\Programs\Python\Python313\python.exe"
    "%LocalAppData%\Programs\Python\Python312\python.exe"
    "%LocalAppData%\Programs\Python\Python311\python.exe"
    "%LocalAppData%\Programs\Python\Python310\python.exe"
) do (
    if exist %%p (
        set "PYTHON_EXE=%%p"
        goto :found_python
    )
)

:found_python
if not defined PYTHON_EXE (
    echo Python not found in common locations.
    echo Please install Python 3.10 or later and try again.
    goto error
)

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
    echo Please check your Python installation.
    goto error
)

:: --- Install Packages Check ---
echo Installing required Python packages...
"%PYTHON_EXE%" -m pip install -r "%~dp0requirements.txt"
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
echo.

cd /d "%~dp0"
"%PYTHON_EXE%" -m animus_cli.main --qa

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
pause

:end
endlocal