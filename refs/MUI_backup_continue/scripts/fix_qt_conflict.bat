@echo off
REM Fix Qt Plugin Conflict in matlab312 Environment
REM This script removes PyQt5 packages that conflict with PySide6

echo ============================================================
echo Qt Plugin Conflict Fix for matlab312 Environment
echo ============================================================
echo.

echo Activating matlab312 environment...
call D:\anaconda3\Scripts\activate.bat matlab312

if errorlevel 1 (
    echo ERROR: Failed to activate matlab312 environment
    pause
    exit /b 1
)

echo.
echo Current environment: matlab312
echo.

echo Checking for PyQt5 packages...
conda list | findstr -i "pyqt qt-main qt-webengine"

echo.
echo Removing PyQt5, PyQt6 and conflicting Qt packages...
echo.

REM Try to remove PyQt5 packages
conda remove pyqt pyqt5-sip pyqtwebengine qt-main qt-webengine --force -y 2>nul

REM Try to remove PyQt6 packages
conda remove pyqt6 pyqt6-sip pyqt6-webengine qt6-main --force -y

if errorlevel 1 (
    echo.
    echo WARNING: Some packages may not exist, continuing...
)

echo.
echo ============================================================
echo Verifying installation...
echo ============================================================
echo.

echo Remaining Qt packages:
conda list | findstr -i qt

echo.
echo ============================================================
echo Testing PySide6...
echo ============================================================
echo.

python -c "import PySide6; print('PySide6 version:', PySide6.__version__); from PySide6.QtWidgets import QApplication; print('Qt import successful!')"

if errorlevel 1 (
    echo.
    echo ERROR: PySide6 test failed
    echo.
    echo Reinstalling PySide6...
    pip uninstall PySide6 PySide6-Addons PySide6-Essentials shiboken6 -y
    pip install --no-cache-dir PySide6==6.7.3
)

echo.
echo ============================================================
echo Fix complete!
echo ============================================================
echo.
echo Next steps:
echo   1. Close this window
echo   2. Run: .\start.bat
echo.

pause
