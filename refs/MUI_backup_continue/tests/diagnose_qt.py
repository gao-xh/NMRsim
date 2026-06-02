"""
Qt Plugin Conflict Diagnostic and Fix Script

This script diagnoses and fixes Qt plugin conflicts between PyQt5 and PySide6
in conda environments.
"""

import sys
import os
from pathlib import Path

print("=" * 70)
print("Qt Plugin Conflict Diagnostic Tool")
print("=" * 70)
print()

# Check Python environment
print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}")
print()

# Check for Qt packages
print("Checking installed Qt packages...")
print("-" * 70)

qt_packages = []
try:
    import importlib.metadata
    for dist in importlib.metadata.distributions():
        name = dist.metadata['Name'].lower()
        if 'qt' in name or 'pyside' in name or 'pyqt' in name:
            qt_packages.append((dist.metadata['Name'], dist.version))
            print(f"  {dist.metadata['Name']}: {dist.version}")
except Exception as e:
    print(f"  Error checking packages: {e}")

if not qt_packages:
    print("  No Qt packages found")
print()

# Check environment variables
print("Qt-related environment variables:")
print("-" * 70)
qt_env_vars = ['QT_PLUGIN_PATH', 'QT_QPA_PLATFORM_PLUGIN_PATH', 
               'QML_IMPORT_PATH', 'QML2_IMPORT_PATH']
for var in qt_env_vars:
    value = os.environ.get(var, '(not set)')
    print(f"  {var}: {value}")
print()

# Try to import PySide6 and get plugin path
print("PySide6 Information:")
print("-" * 70)
try:
    import PySide6
    from PySide6 import QtCore
    
    pyside6_path = Path(PySide6.__file__).parent
    print(f"  PySide6 location: {pyside6_path}")
    print(f"  PySide6 version: {PySide6.__version__}")
    
    # Check for Qt directory
    qt_dir = pyside6_path / "Qt"
    if qt_dir.exists():
        print(f"  Qt directory: {qt_dir} (EXISTS)")
        
        # Check for plugins
        plugins_dir = qt_dir / "plugins"
        if plugins_dir.exists():
            print(f"  Plugins directory: {plugins_dir} (EXISTS)")
            
            # List platform plugins
            platforms_dir = plugins_dir / "platforms"
            if platforms_dir.exists():
                print(f"  Platform plugins:")
                for plugin in platforms_dir.glob("*.dll"):
                    print(f"    - {plugin.name}")
        else:
            print(f"  Plugins directory: {plugins_dir} (NOT FOUND)")
    else:
        print(f"  Qt directory: {qt_dir} (NOT FOUND)")
    
    # Get Qt library info
    print(f"  Qt library paths: {QtCore.QCoreApplication.libraryPaths()}")
    
except ImportError as e:
    print(f"  ERROR: Cannot import PySide6: {e}")
except Exception as e:
    print(f"  ERROR: {e}")
print()

# Check for PyQt5
print("PyQt5 Information:")
print("-" * 70)
try:
    import PyQt5
    from PyQt5 import QtCore
    
    pyqt5_path = Path(PyQt5.__file__).parent
    print(f"  PyQt5 location: {pyqt5_path}")
    print(f"  PyQt5 version: {PyQt5.QtCore.PYQT_VERSION_STR}")
    print(f"  WARNING: PyQt5 is installed and may conflict with PySide6!")
except ImportError:
    print(f"  PyQt5 is NOT installed (good - no conflict)")
except Exception as e:
    print(f"  ERROR: {e}")
print()

# Recommendations
print("=" * 70)
print("RECOMMENDATIONS")
print("=" * 70)

has_pyqt5 = any('pyqt5' in name.lower() for name, _ in qt_packages)
has_pyside6 = any('pyside6' in name.lower() for name, _ in qt_packages)

if has_pyqt5 and has_pyside6:
    print()
    print("⚠ CONFLICT DETECTED: Both PyQt5 and PySide6 are installed!")
    print()
    print("SOLUTION 1 (Recommended): Remove PyQt5 from conda environment")
    print("  conda remove pyqt pyqt5-sip pyqtwebengine qt-main qt-webengine --force")
    print()
    print("SOLUTION 2: Use pip-installed PySide6 in a clean venv")
    print("  python -m venv venv")
    print("  venv\\Scripts\\activate")
    print("  pip install -r requirements.txt")
    print()
elif not has_pyside6:
    print()
    print("⚠ PySide6 is NOT installed!")
    print()
    print("SOLUTION: Install PySide6")
    print("  pip install PySide6==6.7.3")
    print()
else:
    print()
    print("✓ Only PySide6 is installed (good!)")
    print()
    print("If you still have Qt plugin errors, try:")
    print("  1. Reinstall PySide6: pip uninstall PySide6 -y && pip install PySide6==6.7.3")
    print("  2. Clear conda cache: conda clean --all")
    print("  3. Use a fresh venv instead of conda")
    print()

print("=" * 70)
