@echo off
setlocal enabledelayedexpansion

:: Get the directory where this batch file is located
set "SCRIPT_DIR=%~dp0"
set "ANIMUS_EXE=%SCRIPT_DIR%dist\animus.exe"

:: Check if the executable exists
if not exist "%ANIMUS_EXE%" (
    echo Error: Animus executable not found at %ANIMUS_EXE%
    echo Please ensure you have built the application using build_installer.bat
    exit /b 1
)

:: Run Animus with all passed arguments
"%ANIMUS_EXE%" %*

endlocal