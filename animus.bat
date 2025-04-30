@echo off
setlocal enabledelayedexpansion

:: Parse command line arguments
set "SILENT_MODE=1"
set "INTERACTIVE_MODE=0"
set "VERBOSE_MODE=0"

:parse_args
if "%~1"=="" goto :args_done
if /i "%~1"=="--silent" (
    set "SILENT_MODE=1"
    set "INTERACTIVE_MODE=0"
) else if /i "%~1"=="--interactive" (
    set "SILENT_MODE=0"
    set "INTERACTIVE_MODE=1"
) else if /i "%~1"=="--verbose" (
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
    if %SILENT_MODE%==0 (
        echo Error: Python is not installed or not in PATH
        echo Please install Python and try again
        pause
    )
    exit /b 1
)

:: Check if the main script exists
if not exist "%ANIMUS_EXE%" (
    if %SILENT_MODE%==0 (
        echo Error: Animus main script not found at "%ANIMUS_EXE%"
        echo Please ensure the application is properly installed
        pause
    )
    exit /b 1
)

:: Ensure logs directory exists
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

:: Run Animus with appropriate mode and logging
if %INTERACTIVE_MODE%==1 (
    if %VERBOSE_MODE%==1 (
        python "%ANIMUS_EXE%" --output "%LOG_FILE%" --interactive --verbose
    ) else (
        python "%ANIMUS_EXE%" --output "%LOG_FILE%" --interactive
    )
) else (
    if %VERBOSE_MODE%==1 (
        python "%ANIMUS_EXE%" --output "%LOG_FILE%" --silent --verbose
    ) else (
        python "%ANIMUS_EXE%" --output "%LOG_FILE%" --silent
    )
)

endlocal