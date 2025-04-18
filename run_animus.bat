@echo off
setlocal enabledelayedexpansion

:: Initial setup - keep title visible
echo Animus Event Log Analyzer
echo ===========================
echo.

:: Set codepage silently
chcp 65001 > nul

:: --- Model Check --- > nul directs stdout to nul
echo Checking for model file...
set "MODEL_DIR=%~dp0models"
set "MODEL_SHA_PATH=%MODEL_DIR%\sha256-dde5aa3fc5ffc17176b5e8bdc82f587b24b2678c6c66101bf7da77af9f7ccdff"
set "MODEL_EXPECTED_PATH=%MODEL_DIR%\llama-3.2-3b-instruct.Q4_0.gguf"

if not exist "%MODEL_DIR%" (
    echo Creating models directory...
    mkdir "%MODEL_DIR%" > nul
)

set "MODEL_OK=0"
if exist "%MODEL_EXPECTED_PATH%" (
    set "MODEL_OK=1"
) else (
    if exist "%MODEL_SHA_PATH%" (
        copy "%MODEL_SHA_PATH%" "%MODEL_EXPECTED_PATH%" > nul
        if not errorlevel 1 (
            set "MODEL_OK=1"
        ) else (
            echo Failed to copy model file from SHA path. Permissions?
            echo   From: %MODEL_SHA_PATH%
            echo   To:   %MODEL_EXPECTED_PATH%
            goto error
        )
    ) else (
        set "FOUND_MODEL="
        for /f "delims=" %%f in ('dir /b "%MODEL_DIR%\*.gguf" 2^>nul') do (
            set "FOUND_MODEL=%MODEL_DIR%\%%f"
        )
        if defined FOUND_MODEL (
            if not "!FOUND_MODEL!"=="%MODEL_EXPECTED_PATH%" (
                copy "!FOUND_MODEL!" "%MODEL_EXPECTED_PATH%" > nul
                if not errorlevel 1 (
                    set "MODEL_OK=1"
                ) else (
                    echo Failed to copy found model file. Permissions?
                    echo   From: !FOUND_MODEL!
                    echo   To:   %MODEL_EXPECTED_PATH%
                    goto error
                )
            ) else (
                 set "MODEL_OK=1"
            )
        )
    )
)

if %MODEL_OK% equ 0 (
    echo Model file not found or could not be prepared.
    where ollama > nul 2>&1
    if not errorlevel 1 (
        echo Ollama is installed. You could use it to download the model.
        echo Run: ollama pull llama3.2:3b
    ) else (
        echo Ollama is not installed. Please install from https://ollama.ai/download
    )
    echo Or manually place the model file at: %MODEL_EXPECTED_PATH%
    goto error
)

:: --- Python Check --- > nul
echo Checking Python installation...
python --version > nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH.
    echo Please install Python 3.8 or higher from https://www.python.org/downloads/
    goto error
)

:: --- Install Packages Check --- > nul
echo Installing required Python packages...
python -m pip install colorama tabulate pyreadline3 llama-cpp-python > nul
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

:: --- Run log collection --- (Hide output unless error)
echo Collecting Windows Event Logs...
PowerShell -NoProfile -ExecutionPolicy Bypass -Command "& '%~dp0powershell\collect_logs.ps1' -OutputFile '%~dp0animus_logs.json'" > nul
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
:: - Wait for the AI to respond after each question (Implied)
:: - Type 'exit' or 'quit' when you want to end the session (Standard CLI behavior)
:: Remove example questions
:: Remove pause command

:: --- Run the analysis --- (Keep output visible)
cls
echo Animus Event Log Analyzer
echo =====================================
echo Analyzing logs. This may take a few minutes...
echo.

cd /d "%~dp0"
python "animus_cli.py" --output "animus_logs.json" --model-path "%MODEL_EXPECTED_PATH%" --qa

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
pause