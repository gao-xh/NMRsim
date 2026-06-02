# Configuration Guide

## Overview

The application uses a centralized configuration system via `config.txt` for easy management of all application parameters.

## Configuration File: `config.txt`

Located at the project root, this file contains all configurable parameters.

### Format

```
# Lines starting with # are comments
KEY = VALUE
```

### Available Configuration Options

#### Application Information

```
APP_NAME = Multi-System ZULF-NMR Simulator
APP_VERSION = 3.0
APP_DATE = October 2025
APP_AUTHOR = Ajoy Lab
APP_DESCRIPTION = Advanced ZULF-NMR simulation tool with multi-system support
```

#### Python Environment

```
PYTHON_ENV_PATH = D:/anaconda3/envs/matlab312/python.exe
```

- Set to Python interpreter path (conda, venv, or system Python)
- Set to empty or leave blank to use current Python
- Examples:
  - Conda: `D:/anaconda3/envs/matlab312/python.exe`
  - venv: `C:/Projects/myenv/Scripts/python.exe`
  - System: Leave blank or set to `None`

#### Dependencies

```
PYSIDE6_VERSION = 6.7.3
NUMPY_REQUIRED = True
MATPLOTLIB_REQUIRED = True
MATLAB_REQUIRED = True
```

#### MATLAB Configuration

```
MATLAB_MIN_VERSION = R2021b
MATLAB_TOOLBOX = Spinach
```

#### File Format

```
FILE_FORMAT_VERSION = 2.0
```

Used for save/load file compatibility tracking.

#### UI Settings

```
SPLASH_WINDOW_WIDTH = 700
SPLASH_WINDOW_HEIGHT = 550
ANIMATION_SIZE = 400
```

#### Animation Assets

```
VIDEO_ANIMATION = assets/animations/Starting_Animation.mp4
GIF_ANIMATION = assets/animations/Ajoy-Lab-Spin-Animation-Purple.gif
```

## Using Configuration in Code

### Import Configuration

```python
from src.utils.config import config
```

### Access Configuration Values

```python
# Method 1: Direct property access
app_name = config.app_name
app_version = config.app_version

# Method 2: Dictionary-style access
app_name = config['APP_NAME']

# Method 3: Get with default
value = config.get('SOME_KEY', default_value)
```

### Pre-defined Properties

The config object provides convenient properties:

- `config.app_name` - Application name
- `config.app_version` - Version number
- `config.app_date` - Release date
- `config.app_full_version` - "Version X.X (Date)"
- `config.app_title` - Full title with version

### Reload Configuration

```python
from src.utils.config import reload_config

# Reload config.txt after modifications
reload_config()
```

## Environment Setup

### Option 1: Using Conda Environment

1. Edit `config.txt`:
   ```
   PYTHON_ENV_PATH = D:/anaconda3/envs/matlab312/python.exe
   ```

2. Activate environment and run:
   ```powershell
   conda activate matlab312
   python run.py
   ```

### Option 2: Using venv

1. Create venv:
   ```powershell
   python -m venv venv
   ```

2. Edit `config.txt`:
   ```
   PYTHON_ENV_PATH = C:/Users/YourName/Desktop/MUI_10_7/venv/Scripts/python.exe
   ```

3. Activate and run:
   ```powershell
   .\venv\Scripts\Activate.ps1
   python run.py
   ```

### Option 3: System Python

1. Edit `config.txt`:
   ```
   PYTHON_ENV_PATH = 
   ```
   (Leave blank or omit the line)

2. Run directly:
   ```powershell
   python run.py
   ```

## Verification

The launcher (`run.py`) automatically:

1. Checks if running in expected Python environment
2. Verifies all required dependencies are installed
3. Shows version information for each package
4. Provides helpful error messages if something is missing

## Modifying Configuration

1. **Edit `config.txt`** - Change any parameter
2. **No code changes needed** - Application reads config on startup
3. **Restart application** - Changes take effect immediately

## Best Practices

1. **Version Control**: Keep `config.txt` in version control with default values
2. **Local Overrides**: Use `.gitignore` for local configuration if needed
3. **Documentation**: Update this guide when adding new configuration options
4. **Validation**: Add validation in `config.py` for critical parameters

## Troubleshooting

### Configuration not loading

- Check `config.txt` exists in project root
- Verify file encoding is UTF-8
- Check for syntax errors (missing `=`, etc.)

### Environment path issues

- Use forward slashes `/` or escaped backslashes `\\`
- Use absolute paths, not relative paths
- Verify Python executable exists at specified path

### Import errors

```python
# Always import from the config module
from src.utils.config import config

# Not recommended:
# from config import *
```

## Future Enhancements

Potential additions to the configuration system:

- [ ] Multiple configuration profiles (dev, prod, test)
- [ ] Environment variable overrides
- [ ] Configuration validation with schema
- [ ] GUI configuration editor
- [ ] Configuration migration tools
