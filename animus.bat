@echo off
setlocal enabledelayedexpansion

:: Get the directory where this batch file is located
set "SCRIPT_DIR=%~dp0"
set "ANIMUS_EXE=%SCRIPT_DIR%dist\animus.exe"
set "LOG_DIR=%SCRIPT_DIR%logs"
set "LOG_FILE=%LOG_DIR%\animus_logs.json"

:: Check if the executable exists
if not exist "%ANIMUS_EXE%" (
    echo Error: Animus executable not found at %ANIMUS_EXE%
    echo Please ensure you have built the application using build_installer.bat
    exit /b 1
)

:: Ensure logs directory exists
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

:: Run Animus with explicit output path and interactive mode
"%ANIMUS_EXE%" --output "%LOG_FILE%" --interactive

endlocal