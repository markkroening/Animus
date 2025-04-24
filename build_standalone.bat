@echo off
setlocal enabledelayedexpansion

echo Animus CLI Standalone Builder
echo ===========================
echo.

:: Check for Python
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Python not found in PATH.
    echo Please install Python and add it to your PATH.
    goto error
)

:: Check for pip
pip --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Pip not found in PATH.
    echo Please install pip and add it to your PATH.
    goto error
)

:: Install PyInstaller if not already installed
pip show pyinstaller >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Installing PyInstaller...
    pip install pyinstaller
    if %ERRORLEVEL% neq 0 goto error
)

:: Create output directory
if not exist "output" mkdir output

:: Build the standalone executable
echo Building standalone executable...
pyinstaller --onefile --name animus --icon=NONE --add-data "animus_cli;animus_cli" --add-data "powershell;powershell" --add-data "requirements.txt;." animus_cli.py

:: Check if build was successful
if not exist "dist\animus.exe" (
    echo Build failed. Executable not found.
    goto error
)

:: Copy the executable to the output directory
copy "dist\animus.exe" "output\animus.exe" >nul
if %ERRORLEVEL% neq 0 goto error

:: Create a simple batch file to run the executable
echo @echo off > "output\animus.bat"
echo "%~dp0animus.exe" %%* >> "output\animus.bat"

echo.
echo Build completed successfully!
echo Standalone executable created at: output\animus.exe
echo Batch file created at: output\animus.bat
echo.
goto end

:error
echo.
echo Build failed. Please fix the errors above and try again.

:end
endlocal 