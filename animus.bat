@echo off
setlocal enabledelayedexpansion

:: Get the directory where this batch file is located
set "SCRIPT_DIR=%~dp0"

:: Call the main Animus script with all arguments passed through
"%SCRIPT_DIR%run_animus.bat" %*

endlocal 