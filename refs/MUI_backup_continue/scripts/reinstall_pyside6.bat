@echo off
REM Complete Qt Fix for matlab312 Environment

echo ============================================================
echo Complete Qt Plugin Fix
echo ============================================================
echo.

echo Step 1: Activate matlab312 environment
call D:\anaconda3\Scripts\activate.bat matlab312

echo.
echo Step 2: Check current Qt packages
conda list | findstr -i "qt pyside pyqt"

echo.
echo Step 3: Reinstall PySide6 cleanly
echo.

echo Uninstalling existing PySide6...
pip uninstall PySide6 PySide6-Addons PySide6-Essentials shiboken6 -y

echo.
echo Installing PySide6 6.7.3...
pip install --no-cache-dir PySide6==6.7.3

echo.
echo Step 4: Verify installation
echo.

python -c "import sys; print('Python:', sys.executable)"
python -c "import PySide6; print('PySide6:', PySide6.__version__)"
python -c "from PySide6.QtWidgets import QApplication; app = QApplication([]); print('QApplication created successfully!'); app.quit()"

echo.
echo ============================================================
echo Fix complete! Try running: .\start.bat
echo ============================================================
pause
