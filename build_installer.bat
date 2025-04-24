@echo off
setlocal enabledelayedexpansion

echo Animus CLI Installer Builder
echo ===========================
echo.

:: Check if Inno Setup is installed
where iscc >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Inno Setup not found. Downloading and installing...
    
    :: Create temp directory
    set "TEMP_DIR=%TEMP%\InnoSetup"
    if not exist "!TEMP_DIR!" mkdir "!TEMP_DIR!"
    
    :: Download Inno Setup
    powershell -Command "& { Invoke-WebRequest -Uri 'https://files.jrsoftware.org/is/6/innosetup-6.2.2.exe' -OutFile '!TEMP_DIR!\innosetup.exe' }"
    if !ERRORLEVEL! NEQ 0 (
        echo Failed to download Inno Setup.
        exit /b 1
    )
    
    :: Install Inno Setup silently
    "!TEMP_DIR!\innosetup.exe" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-
    if !ERRORLEVEL! NEQ 0 (
        echo Failed to install Inno Setup.
        exit /b 1
    )
    
    :: Clean up
    rmdir /s /q "!TEMP_DIR!"
    
    :: Add Inno Setup to PATH for this session
    set "PATH=%PATH%;%ProgramFiles(x86)%\Inno Setup 6"
)

:: Check for required files
if not exist "animus_cli\main.py" (
    echo Error: animus_cli\main.py not found
    exit /b 1
)

if not exist "powershell\collect_logs.ps1" (
    echo Error: powershell\collect_logs.ps1 not found
    exit /b 1
)

if not exist "requirements.txt" (
    echo Error: requirements.txt not found
    exit /b 1
)

:: Create output directory if it doesn't exist
if not exist "output" mkdir "output"

echo Building Animus installer...
iscc "Animus.iss"
if %ERRORLEVEL% NEQ 0 (
    echo Failed to build installer.
    exit /b 1
)

echo.
echo Build completed successfully!
echo Installer created at: output\AnimusSetup.exe
echo.

:end
endlocal 