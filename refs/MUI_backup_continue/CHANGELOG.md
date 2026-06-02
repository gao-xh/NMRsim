# Changelog

All notable changes to the Multi-System ZULF-NMR Simulator will be documented in this file.

## [3.0.0] - 2025-10-09

### Added
- **Configuration System**: Centralized `config.txt` for all application settings
  - Application information (name, version, date, author, description)
  - Python environment path configuration
  - Dependency version management
  - UI settings (window size, animation size)
  - Asset path configuration
- **Configuration Manager**: `src/utils/config.py` module for loading and accessing configuration
- **Environment Verification**: Automatic check of Python environment and dependencies on startup
- **Path-Based Environment Setup**: Support for conda, venv, and system Python via absolute paths
- **Comprehensive Documentation**:
  - Quick Start Guide
  - Configuration Guide
  - Optimization Summary
  - Development documentation
- **Test Scripts**:
  - `test_config.py` - Configuration system test
  - `test_system.py` - Comprehensive system integrity test
- **Professional Project Structure**: Organized into src/, docs/, tests/, examples/

### Changed
- **Parameterized Application Information**: All hardcoded values moved to config.txt
  - Application name and version
  - Window dimensions
  - Asset paths
  - File format version
- **Improved Launcher** (`run.py`):
  - Environment path verification
  - Dependency checking with version validation
  - Better error messages
  - Professional console output
- **Updated UI Components**:
  - Splash screen now uses config for sizes and paths
  - Main window title from config
  - About dialog uses config values
- **Code Quality Improvements**:
  - All Chinese comments translated to English
  - All emoji removed
  - Professional code structure
  - Comprehensive docstrings
  - PEP 8 compliant

### Fixed
- Import path errors in `src/ui/splash_screen.py`
- Corrected module imports to use `src.` prefix
- Fixed configuration loading issues

### Removed
- Hardcoded application name and version strings
- Hardcoded environment configuration
- Chinese text and emoji from core codebase
- Duplicate and outdated documentation files

## [2.0.0] - Previous Release

### Added
- Multi-system parallel simulation support
- System tabs for independent system management
- Weight control for spectrum combination
- Line broadening controls (Gaussian and Lorentzian)
- Enhanced save/load system with multi-system support
- Detailed logging window
- J-Coupling editor improvements

### Changed
- Complete UI refactoring for multi-system architecture
- Save file format updated to version 2.0
- Improved molecule preset system
- Enhanced spectrum visualization

## [1.0.0] - Initial Release

### Added
- Basic ZULF-NMR simulation interface
- MATLAB Spinach integration
- Single system simulation
- Molecule structure editor
- Basic parameter controls
- Spectrum visualization
- Save/load functionality

---

## Version History Summary

| Version | Date | Key Features |
|---------|------|--------------|
| 3.0.0 | 2025-10-09 | Configuration system, parameterization, code cleanup |
| 2.0.0 | Previous | Multi-system support, weight controls, enhanced UI |
| 1.0.0 | Initial | Basic simulation, MATLAB integration, single system |

## Upgrade Notes

### Upgrading to 3.0.0

**New Configuration File**
- Create or update `config.txt` in project root
- Set `PYTHON_ENV_PATH` to your Python interpreter
- Customize other settings as needed

**No Code Changes Required**
- Existing save files compatible
- All functionality preserved
- New features are optional

**Environment Setup**
- Update to path-based environment configuration
- Verify dependencies with `python test_system.py`
- Check configuration with `python test_config.py`

### Upgrading to 2.0.0

**Save File Format**
- Old format automatically detected
- Multi-system data structure
- Backward compatible loading

**UI Changes**
- New multi-system interface
- System tabs for organization
- Weight and broadening controls

## Known Issues

- MATLAB engine first-time startup can take 10-30 seconds
- Large molecular systems may require significant RAM
- File paths with spaces may need quotes in command line

## Future Plans

### Version 3.1 (Planned)
- Configuration profiles (dev/test/prod)
- GUI configuration editor
- Extended logging system
- Performance optimizations

### Version 3.2 (Planned)
- Batch processing automation
- Advanced spectrum analysis tools
- Export improvements
- Internationalization support

## Contributing

See development documentation in `docs/development/` for:
- Code style guidelines
- Testing procedures
- Documentation standards
- Contribution workflow

## Links

- Documentation: `docs/`
- Quick Start: `docs/QUICK_START.md`
- Configuration Guide: `docs/setup/CONFIGURATION_GUIDE.md`
- Development Docs: `docs/development/`

---

*For detailed Chinese changelog, see `docs/development/CHANGELOG_CN.md`*
