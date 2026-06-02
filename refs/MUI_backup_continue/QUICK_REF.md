# Quick Reference Card

## Launch Application

```powershell
# Easiest method
.\start.bat

# Or manual method
conda activate matlab312
python run.py
```

## Environment Information

| Item | Value |
|------|-------|
| Python Environment | `matlab312` |
| Python Version | 3.12+ |
| Python Path | See `config.txt: PYTHON_ENV_PATH` |
| Main Application | `Multi_system_spinach_UI.py` |
| Launcher | `run.py` |

## Configuration File

All settings centralized in `config.txt`:

```ini
# Application information
APP_NAME = Multi-System ZULF-NMR Simulator
APP_VERSION = 3.0

# Environment configuration
PYTHON_ENV_PATH = D:/anaconda3/envs/matlab312/python.exe

# Window dimensions
SPLASH_WINDOW_WIDTH = 700
SPLASH_WINDOW_HEIGHT = 550

# Animation paths
VIDEO_ANIMATION = assets/animations/Starting_Animation.mp4
GIF_ANIMATION = assets/animations/Ajoy-Lab-Spin-Animation-Purple.gif
```

## Dependencies

### Required
- PySide6 == 6.7.3
- NumPy
- Matplotlib

### Optional (for simulations)
- MATLAB R2021b+ with Spinach
- MATLAB Engine for Python

## Directory Structure

```
MUI_10_7/
├── start.bat          ← Quick launcher
├── run.py             ← Application launcher
├── config.txt         ← Configuration
├── Multi_system_spinach_UI.py  ← Main application
├── src/               ← Source code
├── docs/              ← Documentation
├── assets/            ← Assets
├── presets/           ← Presets
└── tests/             ← Test scripts
```

## Common Commands

```powershell
# Check environment
python -c "import sys; print(sys.executable)"

# Check PySide6 version
python -c "import PySide6; print(PySide6.__version__)"

# List conda environments
conda env list

# Activate environment
conda activate matlab312

# Run tests
python tests/test_system.py
```

## Test Scripts

```powershell
# Configuration test
python tests/test_config.py

# System integrity test
python tests/test_system.py

# Splash screen test
python tests/test_splash.py
```

## Development Tips

1. **Modify settings**: Edit `config.txt` (no Python restart needed)
2. **View logs**: Application displays loaded configuration path
3. **MATLAB optional**: Application can start without MATLAB (UI-only mode)
4. **Path format**: Use `/` or `\\` in Windows paths (not single `\`)

## Version Information

**Multi-System ZULF-NMR Simulator v3.0**  
October 2025  
Ajoy Lab

---

📖 **Full Documentation**: `docs/` directory  
🔧 **Configuration Guide**: `docs/setup/CONFIGURATION_GUIDE.md`  
🚀 **Quick Start**: `docs/QUICK_START.md`
