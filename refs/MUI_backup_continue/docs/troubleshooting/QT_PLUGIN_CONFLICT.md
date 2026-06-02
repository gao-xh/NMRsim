# Qt Plugin Conflict Resolution Guide

**Issue**: "Could not load the Qt platform plugin 'windows'"  
**Cause**: Conda Qt packages conflict with pip-installed PySide6  
**Solution**: Remove conda Qt packages, use pip PySide6 only

---

## Problem Description

When running the application in a conda environment (e.g., `matlab312`), you may encounter:

```
qt.qpa.plugin: Could not load the Qt platform plugin "windows" in "" even though it was found.
This application failed to start because no Qt platform plugin could be initialized.
Available platform plugins are: direct2d, minimal, offscreen, windows.
```

---

## Root Cause

Conda and pip can both install Qt libraries:
- **Conda**: Installs system Qt6 packages (`qtbase`, `qtdeclarative`, etc.)
- **Pip**: Installs PySide6 with bundled Qt libraries

When both are present, they conflict because:
1. Environment variables may point to conda's Qt
2. Plugin paths get mixed between conda Qt and PySide6 Qt
3. DLL dependencies clash

---

## Solution: Remove Conda Qt Packages

### Step 1: Diagnose the Issue

Run the diagnostic script:
```powershell
python tests/diagnose_qt.py
```

This will show:
- Which Qt packages are installed (conda vs pip)
- Environment variables affecting Qt
- PySide6 plugin paths

### Step 2: Activate Correct Environment

**CRITICAL**: Always work in the target environment (e.g., `matlab312`), NOT `base`!

```powershell
conda activate matlab312
```

### Step 3: Remove Conflicting Packages

Remove **all** conda Qt packages:

```powershell
# Remove PyQt5 (if present)
conda remove pyqt pyqt5-sip pyqtwebengine qt-main qt-webengine --force -y

# Remove PyQt6 (if present)
conda remove pyqt pyqt6-sip --force -y

# Remove Qt6 system packages
conda remove qtbase qtdeclarative qtshadertools qtsvg qttools qtwebchannel qtwebengine qtwebsockets --force -y
```

### Step 4: Reinstall PySide6 via Pip

```powershell
pip uninstall PySide6 PySide6-Addons PySide6-Essentials shiboken6 -y
pip install --no-cache-dir PySide6==6.7.3
```

### Step 5: Verify

```powershell
python -c "from PySide6.QtWidgets import QApplication; app = QApplication([]); print('Success!'); app.quit()"
```

Should print "Success!" without errors.

---

## Automated Fix Script

Use the provided script:

```powershell
.\fix_qt_environment.bat
```

This script:
1. Activates `matlab312` environment
2. Removes all conflicting Qt packages
3. Reinstalls PySide6 cleanly
4. Verifies installation

---

## Prevention

### For New Conda Environments

When creating a new conda environment for this project:

```powershell
# Create environment
conda create -n myenv python=3.12

# Activate
conda activate myenv

# Install ONLY via pip (not conda)
pip install -r requirements.txt
```

**Do NOT install** these via conda:
- ❌ `conda install pyqt`
- ❌ `conda install pyside6`
- ❌ `conda install qt`

### For Existing Environments

Check for Qt packages:
```powershell
conda list | findstr -i qt
```

If you see `qtbase`, `pyqt`, or other Qt packages from conda → **remove them**!

---

## Why This Happens

### Common Scenarios

1. **Anaconda Base Environment**
   - Anaconda includes PyQt5 and Qt libraries by default
   - These get inherited or conflict when using conda envs

2. **Package Dependencies**
   - Some conda packages (e.g., `spyder`, `jupyter`, `matplotlib-qt`) pull in Qt
   - These install conda's Qt, which conflicts with PySide6

3. **Mixed Installation**
   - User runs `conda install package` which pulls Qt dependencies
   - Later runs `pip install PySide6`
   - Both Qt installations conflict

### Technical Details

**Environment Variables**:
- `QT_PLUGIN_PATH`: Points to Qt plugins directory
- `QT_QPA_PLATFORM_PLUGIN_PATH`: Platform-specific plugins

When conda Qt is installed, these may point to conda's location.  
When PySide6 tries to load, it looks in wrong location → plugin not found.

**DLL Search Order**:
1. Application directory
2. System PATH directories
3. Qt plugin paths

Conda adds its `Library/bin` to PATH, which contains Qt DLLs.  
PySide6's bundled Qt DLLs may be shadowed by conda's.

---

## Troubleshooting

### Still Getting Error After Fix?

1. **Check you're in correct environment**:
   ```powershell
   python -c "import sys; print(sys.executable)"
   ```
   Should show: `D:\anaconda3\envs\matlab312\python.exe`

2. **Verify no conda Qt remains**:
   ```powershell
   conda list | findstr -i "qt "
   ```
   Should only show: `qtconsole`, `qtpy`, `qtawesome` (these are Python packages, not Qt itself)

3. **Check environment variables**:
   ```powershell
   $env:QT_PLUGIN_PATH
   $env:QT_QPA_PLATFORM_PLUGIN_PATH
   ```
   Should be empty or point to PySide6's plugins

4. **Reinstall PySide6 completely**:
   ```powershell
   pip uninstall PySide6 PySide6-Addons PySide6-Essentials shiboken6 -y
   pip cache purge
   pip install --no-cache-dir PySide6==6.7.3
   ```

### Alternative: Use Virtual Environment (venv)

If conda continues to cause issues, switch to venv:

```powershell
# Create venv
python -m venv venv

# Activate
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Update config.txt
# PYTHON_ENV_PATH = C:/Users/YourName/Desktop/MUI_10_7/venv/Scripts/python.exe
```

Venv doesn't have conda's Qt package conflicts.

---

## Summary

✅ **Problem**: Conda Qt packages conflict with pip PySide6  
✅ **Solution**: Remove all conda Qt, use pip PySide6 only  
✅ **Prevention**: Never mix conda Qt and pip PySide6  
✅ **Alternative**: Use venv instead of conda  

---

## Quick Reference

### Check Current Environment
```powershell
conda env list
python -c "import sys; print(sys.executable)"
```

### Check Qt Packages
```powershell
conda list | findstr -i qt
python tests/diagnose_qt.py
```

### Remove Conda Qt (matlab312)
```powershell
conda activate matlab312
conda remove qtbase qtdeclarative qtshadertools qtsvg qttools qtwebchannel qtwebengine qtwebsockets pyqt pyqt6-sip --force -y
```

### Reinstall PySide6
```powershell
pip uninstall PySide6 PySide6-Addons PySide6-Essentials shiboken6 -y
pip install --no-cache-dir PySide6==6.7.3
```

### Test
```powershell
.\start.bat
```

---

**Last Updated**: October 9, 2025  
**Tested**: Windows 10/11, Anaconda3, Python 3.12, PySide6 6.7.3
