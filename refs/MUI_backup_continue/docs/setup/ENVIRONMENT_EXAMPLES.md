# Environment Configuration Examples

This document provides examples of configuring different Python environment types in `config.txt`.

## Conda Environment (Current Default)

```ini
# Conda environment example
PYTHON_ENV_PATH = D:/anaconda3/envs/matlab312/python.exe
```

**Detection**: Script automatically detects "anaconda", "conda", or "miniconda" in path.

**Behavior**:
- Extracts environment name (`matlab312`)
- Activates conda environment
- Runs `python run.py` in activated environment

---

## Virtual Environment (venv)

### Windows
```ini
# venv on Windows
PYTHON_ENV_PATH = C:/Users/YourName/Desktop/MUI_10_7/venv/Scripts/python.exe
```

### Linux/Mac
```ini
# venv on Linux/Mac
PYTHON_ENV_PATH = /home/username/MUI_10_7/venv/bin/python
```

**Detection**: No conda-related keywords in path.

**Behavior**:
- Detects as venv/system Python
- Runs directly: `"C:/path/to/python.exe" run.py`
- No environment activation needed

---

## System Python

### Windows
```ini
# System Python on Windows
PYTHON_ENV_PATH = C:/Python312/python.exe
```

### Linux/Mac
```ini
# System Python on Linux/Mac
PYTHON_ENV_PATH = /usr/bin/python3
```

**Detection**: No conda-related keywords in path.

**Behavior**:
- Same as venv
- Direct execution
- No activation step

---

## How Launcher Scripts Detect Environment Type

### start.bat (Windows Batch)
```batch
REM Check if path contains conda-related keywords
echo !PYTHON_PATH! | findstr /C:"anaconda" /C:"conda" /C:"miniconda" >nul

if %errorlevel%==0 (
    REM This is a conda environment
    REM Extract environment name and activate
    call D:\anaconda3\Scripts\activate.bat !ENV_NAME!
    python run.py
) else (
    REM This is venv or system Python
    REM Use direct path
    "!PYTHON_PATH!" run.py
)
```

### start.ps1 (PowerShell)
```powershell
# Check if path contains conda-related keywords
$isConda = $pythonPath -match 'anaconda|conda|miniconda'

if ($isConda) {
    # This is a conda environment
    conda activate $envName
    python run.py
}
else {
    # This is venv or system Python
    & $pythonPath run.py
}
```

---

## Creating Different Environment Types

### Conda Environment
```powershell
# Create new conda environment
conda create -n myproject python=3.12

# Activate
conda activate myproject

# Install dependencies
pip install -r requirements.txt

# Configure
# config.txt: PYTHON_ENV_PATH = D:/anaconda3/envs/myproject/python.exe
```

### Virtual Environment (venv)
```powershell
# Create venv
python -m venv venv

# Activate (Windows)
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Configure
# config.txt: PYTHON_ENV_PATH = C:/path/to/project/venv/Scripts/python.exe
```

### Pipenv
```powershell
# Create pipenv environment
pipenv install -r requirements.txt

# Find Python path
pipenv --py

# Configure (use the path from above command)
# config.txt: PYTHON_ENV_PATH = C:/Users/.../.virtualenvs/.../Scripts/python.exe
```

### Poetry
```powershell
# Create poetry environment
poetry install

# Find Python path
poetry env info --path

# Configure (use path + \Scripts\python.exe on Windows)
# config.txt: PYTHON_ENV_PATH = C:/path/to/poetry/env/Scripts/python.exe
```

---

## Switching Between Environments

Simply edit `config.txt` and change `PYTHON_ENV_PATH`:

### From conda to venv
```ini
# Before
PYTHON_ENV_PATH = D:/anaconda3/envs/matlab312/python.exe

# After
PYTHON_ENV_PATH = C:/Users/YourName/Desktop/MUI_10_7/venv/Scripts/python.exe
```

### From venv to system Python
```ini
# Before
PYTHON_ENV_PATH = C:/Users/YourName/Desktop/MUI_10_7/venv/Scripts/python.exe

# After
PYTHON_ENV_PATH = C:/Python312/python.exe
```

**No code changes needed** - launcher scripts automatically adapt!

---

## Verification

After changing `PYTHON_ENV_PATH`, verify with:

```powershell
# Run the launcher
.\start.bat

# Check which Python is used
python -c "import sys; print(sys.executable)"
```

The launcher will display:
- **Conda environment**: "Python Environment: matlab312 (conda)"
- **venv/system**: "Environment Type: venv/system Python"

---

## Troubleshooting

### Conda environment not found
**Symptom**: "Failed to activate conda environment"

**Solution**:
1. Check environment exists: `conda env list`
2. Verify path in config.txt matches actual location
3. If conda not found, script will fallback to direct Python path

### Python not found
**Symptom**: "python.exe is not recognized"

**Solution**:
1. Verify `PYTHON_ENV_PATH` in config.txt is correct
2. Test path manually: `"D:/anaconda3/envs/matlab312/python.exe" --version`
3. Use absolute path, not relative path

### Wrong Python version
**Symptom**: Dependencies not found

**Solution**:
1. Check Python version: `python --version`
2. Ensure environment has correct Python 3.12+
3. Reinstall dependencies in correct environment

---

## Best Practices

### 1. Always Use Absolute Paths
```ini
# Good
PYTHON_ENV_PATH = D:/anaconda3/envs/matlab312/python.exe

# Bad
PYTHON_ENV_PATH = ../venv/Scripts/python.exe
```

### 2. Use Forward Slashes or Double Backslashes
```ini
# Good - forward slashes (scripts convert to backslashes)
PYTHON_ENV_PATH = D:/anaconda3/envs/matlab312/python.exe

# Good - double backslashes
PYTHON_ENV_PATH = D:\\anaconda3\\envs\\matlab312\\python.exe

# Bad - single backslashes (parsing error)
PYTHON_ENV_PATH = D:\anaconda3\envs\matlab312\python.exe
```

### 3. Test After Changes
```powershell
# Test launcher
.\start.bat

# Verify Python
python -c "import sys; print(sys.executable)"

# Check dependencies
python -c "import PySide6; print(PySide6.__version__)"
```

---

## Summary

✅ **Supports all Python environment types**:
- Conda environments
- Virtual environments (venv)
- Pipenv
- Poetry
- System Python

✅ **Automatic detection**: Scripts detect environment type from path

✅ **No code changes needed**: Just update `PYTHON_ENV_PATH` in config.txt

✅ **Graceful fallback**: If conda activation fails, uses direct Python path

---

**Recommendation**: Use conda for development (better package management), but any Python environment works!
