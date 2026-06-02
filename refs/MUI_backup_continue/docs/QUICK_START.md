# Quick Start Guide

## Prerequisites

### Required Software

1. **Python 3.12+** (conda environment recommended)
2. **MATLAB R2021b+** with Spinach toolbox (optional, for simulations)
3. **Git** (optional, for version control)

### Python Packages

- PySide6 == 6.7.3
- NumPy
- Matplotlib
- MATLAB Engine for Python (optional, for simulations)

## Installation

### Step 1: Clone/Download Project

```powershell
cd C:\Users\YourName\Desktop
# Download or clone the project
```

### Step 2: Set Up Python Environment

#### Option A: Conda (Recommended)

```powershell
# Create conda environment
conda create -n matlab312 python=3.12

# Activate environment
conda activate matlab312

# Install dependencies
pip install -r requirements.txt
```

#### Option B: venv

```powershell
# Create virtual environment
python -m venv venv

# Activate (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Install MATLAB Engine (Optional)

**Required only for NMR simulations. Skip this step for UI testing/development.**

```powershell
# Navigate to MATLAB engine folder (adjust version number)
cd "C:\Program Files\MATLAB\R2023b\extern\engines\python"

# Install
python setup.py install
```

### Step 4: Configure Environment

Edit `config.txt` in project root:

```ini
PYTHON_ENV_PATH = D:/anaconda3/envs/matlab312/python.exe
```

## Running the Application

### Method 1: Launcher Script (Easiest)

Simply double-click `start.bat` in the project folder, or:

```powershell
.\start.bat
```

This automatically:
- Activates the `matlab312` environment
- Runs the application
- Shows any errors

### Method 2: Manual Launch

```powershell
# Activate environment
conda activate matlab312

# Run application
python run.py
```

### Method 3: Direct Python (No Activation Needed)

```powershell
# Use environment Python directly
D:\anaconda3\envs\matlab312\python.exe run.py
```

### What Happens on Launch

1. **Environment Check**: Verifies Python environment and dependencies
2. **Splash Screen**: Displays loading animation
3. **MATLAB Initialization** (if available): Starts MATLAB engine and runs validation
   - First-time launch: ~10-15 seconds
   - Subsequent launches: ~3-5 seconds
   - If MATLAB not installed: Skips to main window (UI-only mode)
4. **Main Window**: Opens application interface

## Project Structure

```
MUI_10_7/
├── config.txt                 # Configuration file
├── start.bat                  # Quick launcher (Windows)
├── start.ps1                  # PowerShell launcher
├── run.py                     # Application launcher
├── requirements.txt           # Python dependencies
├── Multi_system_spinach_UI.py # Main application
│
├── src/                       # Source code
│   ├── core/                  # Core modules
│   │   └── spinach_bridge.py # MATLAB bridge
│   ├── ui/                    # UI components
│   │   └── splash_screen.py  # Splash screen
│   └── utils/                 # Utilities
│       ├── config.py          # Configuration manager
│       ├── Save_Load.py       # Save/Load system
│       └── read_mol.py        # Molecule reader
│
├── assets/                    # Assets
│   └── animations/            # Animation files
│       ├── Starting_Animation.mp4
│       └── Ajoy-Lab-Spin-Animation-Purple.gif
│
├── presets/                   # Preset data
│   ├── molecules/             # Molecule presets
│   ├── parameters/            # Parameter presets
│   └── spectrum/              # Spectrum presets
│
├── user_save/                 # User saved data
│   ├── molecules/
│   └── parameters/
│
├── docs/                      # Documentation
│   ├── setup/                 # Setup guides
│   ├── features/              # Feature documentation
│   └── development/           # Development docs
│
├── examples/                  # Example scripts
└── tests/                     # Test scripts
```

## Basic Usage

### 1. System Management

- **Add System**: Click "Add System" button
- **Select System**: Use system tabs or dropdown
- **Remove System**: Select system → Menu → Remove

### 2. Loading Molecules

- **Preset**: Select from dropdown → "Load Preset"
- **Saved**: "Load Molecule" → Browse user_save/molecules/
- **Manual**: Edit structure table directly

### 3. Setting Parameters

- **Magnetic Field**: B0_X, B0_Y, B0_Z (Tesla)
- **Simulation Range**: frequency_range, time_offset, time_step, n_points
- **Weight**: Adjust system contribution to combined spectrum
- **Line Broadening**: Set Gaussian/Lorentzian broadening

### 4. Running Simulation

1. Configure all parameters
2. Click "Run Simulation"
3. Wait for MATLAB processing
4. View results in Spectrum tab

### 5. Viewing Results

- **Spectrum Plot**: Combined and individual system spectra
- **Controls**: Zoom, pan, save plot
- **Export**: Save spectrum data as CSV

### 6. Multi-System Analysis

- Add multiple systems (different molecules)
- Adjust weights for each system
- Compare individual vs combined spectra
- Modify broadening independently

## Keyboard Shortcuts

Currently not implemented. Feature planned for future release.

## Common Tasks

### Save Current Configuration

Menu → File → Save Parameters → Choose location → Save

### Load Previous Configuration

Menu → File → Load Parameters → Browse → Select file → Open

### Export Spectrum Data

Spectrum tab → Export → Choose format → Save

### Change Application Settings

Edit `config.txt` → Restart application

## Troubleshooting

### Application won't start

1. Check Python environment is activated
2. Verify all dependencies installed: `python test_config.py`
3. Check MATLAB installation and license
4. Review console output for errors

### MATLAB engine fails

1. Verify MATLAB R2021b+ is installed
2. Check Spinach toolbox is in MATLAB path
3. Reinstall MATLAB Engine for Python
4. Try running MATLAB separately to verify license

### Simulation errors

1. Check molecule structure is valid
2. Verify all parameters are set
3. Review detailed logs (Menu → View → Detailed Logs)
4. Check MATLAB workspace for errors

### Import errors

1. Ensure running from project root
2. Check `src/` directory structure intact
3. Verify `__init__.py` files exist
4. Reinstall dependencies: `pip install -r requirements.txt --force-reinstall`

### Performance issues

1. Reduce `n_points` for faster simulation
2. Close other MATLAB instances
3. Increase system RAM allocation
4. Simplify molecule structure

## Getting Help

### Documentation

- `docs/setup/` - Installation and configuration
- `docs/features/` - Feature explanations
- `docs/development/` - Development guides

### Log Files

- Console output during launch
- Detailed logs window (Menu → View → Detailed Logs)
- MATLAB workspace variables

### Reporting Issues

When reporting problems, include:

1. Python version: `python --version`
2. Environment: `conda env list` or `pip list`
3. MATLAB version
4. Error messages (full text)
5. Steps to reproduce
6. Configuration file (`config.txt`)

## Next Steps

1. **Tutorial**: Follow examples in `examples/` directory
2. **Customize**: Modify `config.txt` for your setup
3. **Explore**: Try different molecules from presets
4. **Advanced**: Read feature documentation in `docs/features/`

## Tips

- **First Run**: Initial MATLAB startup takes 10-30 seconds
- **Save Often**: Use File → Save Parameters regularly
- **Presets**: Explore preset molecules for quick testing
- **Logs**: Check detailed logs for MATLAB output
- **Weights**: Set to 0 to exclude system from combined spectrum
- **Broadening**: Adjust for peak visibility
