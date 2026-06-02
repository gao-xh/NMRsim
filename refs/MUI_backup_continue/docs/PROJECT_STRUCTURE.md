# Project Structure# Multi-System ZULF-NMR Simulator



Multi-System ZULF-NMR Simulator - Professional OrganizationA professional NMR simulation tool with multi-system support and advanced features.



## Root Directory (Clean)## Quick Start



``````powershell

MUI_10_7/# Activate environment

├── README.md                     # Project overviewconda activate matlab312

├── CHANGELOG.md                  # Version history

├── config.txt                    # Configuration# Run the application

├── requirements.txt              # Dependenciespython run.py

├── run.py                        # Launcher```

├── Multi_system_spinach_UI.py    # Main application

│## Project Structure

├── src/                          # Source code

├── assets/                       # Assets```

├── docs/                         # DocumentationMUI_10_7/

├── tests/                        # Tests├── run.py                          # Main launcher with splash screen

├── presets/                      # Presets├── Multi_system_spinach_UI.py      # Main application

├── user_save/                    # User data├── requirements.txt                # Dependencies

└── network_interface/            # Network (optional)├── CHANGELOG.md                    # Version history

```├── QUICK_REFERENCE.md              # Quick reference

│

## Quick Navigation├── src/                            # Source code

│   ├── core/                       # Business logic

- **Users**: Start with `README.md` → `docs/QUICK_START.md`│   ├── ui/                         # UI components

- **Developers**: See `src/` → `docs/development/`│   │   └── splash_screen.py        # Initialization splash screen

- **Configuration**: Edit `config.txt` → Read `docs/setup/CONFIGURATION_GUIDE.md`│   └── utils/                      # Utilities

│

## Design Principles├── docs/                           # Documentation

│   ├── INDEX.md                    # Documentation index

✓ Clean root (6 files only)  │   ├── setup/                      # Setup guides

✓ Modular source code  │   ├── features/                   # Feature documentation

✓ Organized documentation  │   └── development/                # Development notes

✓ Isolated test scripts  │

✓ Professional structure├── assets/                         # Resources

│   └── animations/                 # Loading animations

See full details in documentation.│       ├── Starting_Animation.mp4

│       └── Ajoy-Lab-Spin-Animation-Purple.gif
│
├── network_interface/              # Cloud/local backend
├── presets/                        # Built-in presets
├── user_save/                      # User data
└── spectrum/                       # Exported spectra
```

## Features

- Multi-system simulation support
- Advanced J-coupling editor with scrolling
- Gaussian line broadening
- Real-time weight control
- Detailed logging window
- Professional splash screen with animations
- Save/Load functionality
- Network interface for cloud computing

## Requirements

- Python 3.8+
- PySide6 6.7.3
- NumPy
- Matplotlib
- MATLAB R2021b+ with Spinach toolbox

## Documentation

See [docs/INDEX.md](docs/INDEX.md) for complete documentation.

## Version

Version 3.0 (October 2025)

## License

Research use only.
