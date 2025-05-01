@echo off
setlocal enabledelayedexpansion

:: Parse command line arguments
set "VERBOSE_MODE=0"

:parse_args
if "%~1"=="" goto :args_done
if /i "%~1"=="--verbose" (
    set "VERBOSE_MODE=1"
)
shift
goto :parse_args
:args_done

:: Get the directory where this batch file is located
set "SCRIPT_DIR=%~dp0"
set "ANIMUS_EXE=%SCRIPT_DIR%animus_cli\main.py"
set "LOG_DIR=%LOCALAPPDATA%\Animus\logs"
set "LOG_FILE=%LOG_DIR%\animus_logs.json"

:: Set Python path
set "PYTHONPATH=%SCRIPT_DIR%;%PYTHONPATH%"

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

:: Create log directory if it doesn't exist
if not exist "%LOG_DIR%" (
    mkdir "%LOG_DIR%"
)

:: Run Animus with the appropriate arguments
if %VERBOSE_MODE%==1 (
    python "%ANIMUS_EXE%" --verbose
) else (
    python "%ANIMUS_EXE%"
)

:: Check the exit code
if %ERRORLEVEL% neq 0 (
    echo Animus exited with error code %ERRORLEVEL%
    pause
)

exit /b %ERRORLEVEL%
endlocal