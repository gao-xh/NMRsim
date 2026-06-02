@echo off
REM ZULF-NMR Simulator Launcher
REM Reads configuration from config.txt and launches application

setlocal enabledelayedexpansion

echo ============================================================
echo.

REM Read APP_NAME from config.txt
for /f "usebackq tokens=1,* delims==" %%a in ("config.txt") do (
    set "key=%%a"
    set "value=%%b"
    set "key=!key: =!"
    set "value=!value: =!"
    if "!key!"=="APP_NAME" (
        for /f "tokens=* delims= " %%c in ("%%b") do set "APP_NAME=%%c"
    )
    if "!key!"=="APP_VERSION" (
        for /f "tokens=* delims= " %%c in ("%%b") do set "APP_VERSION=%%c"
    )
    if "!key!"=="PYTHON_ENV_PATH" (
        for /f "tokens=* delims= " %%c in ("%%b") do set "PYTHON_PATH=%%c"
    )
)

echo   !APP_NAME!
echo   Version !APP_VERSION!
echo.
echo ============================================================
echo.

REM Convert path format
set "PYTHON_PATH=!PYTHON_PATH:/=\!"

REM Check if this is a conda environment
echo !PYTHON_PATH! | findstr /C:"anaconda" /C:"conda" /C:"miniconda" >nul
if !errorlevel!==0 (
    REM Extract conda environment name
    for %%i in ("!PYTHON_PATH!") do set "ENV_DIR=%%~dpi"
    set "ENV_DIR=!ENV_DIR:~0,-1!"
    for %%i in ("!ENV_DIR!") do set "ENV_NAME=%%~nxi"
    
    echo Python Environment: !ENV_NAME! (conda)
    echo.
    echo Activating conda environment...
    
    call D:\anaconda3\Scripts\activate.bat !ENV_NAME!
    
    if !errorlevel! NEQ 0 (
        echo.
        echo ERROR: Failed to activate conda environment: !ENV_NAME!
        echo Trying direct Python path instead...
        set "USE_DIRECT_PATH=1"
    ) else (
        echo Environment activated successfully
        echo.
        set "USE_DIRECT_PATH=0"
    )
) else (
    REM Not a conda environment, use direct Python path
    echo Python Path: !PYTHON_PATH!
    echo Environment Type: venv/system Python
    echo.
    set "USE_DIRECT_PATH=1"
)

REM Clear Qt environment variables to avoid conflicts
set "QT_PLUGIN_PATH="
set "QT_QPA_PLATFORM_PLUGIN_PATH="
set "QML_IMPORT_PATH="
set "QML2_IMPORT_PATH="

REM Run the application
echo Starting application...
echo.

if "!USE_DIRECT_PATH!"=="1" (
    REM Use direct Python path
    "!PYTHON_PATH!" run.py
) else (
    REM Use activated environment
    python run.py
)

REM Keep window open if there's an error
if errorlevel 1 (
    echo.
    echo Application exited with errors
    pause
)

endlocal
