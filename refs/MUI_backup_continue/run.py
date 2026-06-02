"""
Main Launcher for Multi-System ZULF-NMR Simulator

This script configures the environment and launches the application
with a splash screen and initialization sequence.
"""

import sys
import os
import subprocess
from pathlib import Path

# CRITICAL: Clear Qt plugin paths BEFORE any Qt imports
# This prevents conflicts between conda's PyQt5 and our PySide6
os.environ.pop('QT_PLUGIN_PATH', None)
os.environ.pop('QT_QPA_PLATFORM_PLUGIN_PATH', None)
os.environ.pop('QML_IMPORT_PATH', None)
os.environ.pop('QML2_IMPORT_PATH', None)

# Disable hardware video acceleration to prevent buffer pool issues
# Force software decoding for video playback
os.environ['QT_OPENGL'] = 'software'
os.environ['QT_D3D11_ADAPTER'] = '-1'
os.environ['QT_ANGLE_PLATFORM'] = 'software'
os.environ['LIBVA_DRIVER_NAME'] = 'i965'

# Force PySide6 to use its own Qt libraries
# Get PySide6 installation path and set Qt plugin path explicitly
try:
    import PySide6
    pyside6_path = Path(PySide6.__file__).parent
    plugins_path = pyside6_path / "Qt" / "plugins"
    if plugins_path.exists():
        os.environ['QT_PLUGIN_PATH'] = str(plugins_path)
except Exception as e:
    pass  # If we can't set it, let PySide6 use defaults

from PySide6.QtWidgets import QApplication, QMessageBox

# Import configuration
from src.utils.config import config

# Import icon manager
from src.utils.icon_manager import icon_manager


# Environment Configuration (loaded from config.txt)
PYTHON_ENV_PATH = config.get('PYTHON_ENV_PATH')
PROJECT_ROOT = Path(__file__).parent.absolute()


def check_environment():
    """Check Python environment and display information"""
    current_python = sys.executable
    print(f"Python interpreter: {current_python}")
    
    # Check if running expected environment
    if PYTHON_ENV_PATH is not None:
        expected_path = Path(PYTHON_ENV_PATH).resolve()
        actual_path = Path(current_python).resolve()
        
        if expected_path != actual_path:
            print(f"\nWarning: Not using expected Python environment")
            print(f"Expected: {expected_path}")
            print(f"Actual:   {actual_path}")
            print(f"\nPlease run with the correct Python:")
            print(f"  {expected_path} run.py")
            
            response = input("\nContinue anyway? (y/n): ")
            if response.lower() != 'y':
                sys.exit(1)
        else:
            print(f"Environment path: OK")
    else:
        print(f"Environment: Using current Python")
    
    # Show conda environment if applicable
    conda_env = os.environ.get('CONDA_DEFAULT_ENV', '')
    if conda_env:
        print(f"Conda environment: {conda_env}")
    
    print(f"Python version: {sys.version.split()[0]}")
    
    return True


def setup_python_path():
    """Add project root to Python path"""
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    print(f"Project root: {PROJECT_ROOT}")


def verify_dependencies():
    """Verify critical dependencies are installed"""
    required_version = config.get('PYSIDE6_VERSION', '6.7.3')
    
    try:
        import PySide6
        print(f"PySide6: {PySide6.__version__} - OK")
        if PySide6.__version__ != required_version:
            print(f"  Note: Expected version {required_version}")
    except ImportError:
        print("Error: PySide6 not installed")
        print(f"Install with: pip install PySide6=={required_version}")
        sys.exit(1)
    
    if config.get('NUMPY_REQUIRED', True):
        try:
            import numpy
            print(f"NumPy: {numpy.__version__} - OK")
        except ImportError:
            print("Error: NumPy not installed")
            print("Install with: pip install numpy")
            sys.exit(1)
    
    if config.get('MATPLOTLIB_REQUIRED', True):
        try:
            import matplotlib
            print(f"Matplotlib: {matplotlib.__version__} - OK")
        except ImportError:
            print("Error: Matplotlib not installed")
            print("Install with: pip install matplotlib")
            sys.exit(1)
    
    print("All dependencies verified\n")


def main():
    """Main entry point with environment setup and splash screen"""
    
    print("=" * 60)
    print(config.app_name)
    print(config.app_full_version)
    print("=" * 60)
    print()
    
    # Environment setup
    print("Checking environment...")
    check_environment()
    setup_python_path()
    verify_dependencies()
    
    print("Starting application...\n")
    
    # Create Qt Application
    app = QApplication(sys.argv)
    
    # Set application-wide icon
    app_icon = icon_manager.get_app_icon()
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)
    
    # Show splash screen
    from src.ui.splash_screen import SplashScreen
    splash = SplashScreen()
    splash.show()
    
    # Process events to show splash immediately
    app.processEvents()
    
    # Start initialization
    splash.start_initialization()
    
    # Variable to hold main window
    main_window = None
    
    def on_splash_closed():
        """Called when splash screen closes"""
        nonlocal main_window
        
        if splash.init_success:
            # Import and create main window
            from Multi_system_spinach_UI import MultiSystemSpinachUI
            main_window = MultiSystemSpinachUI()
            main_window.show()
        else:
            # Show error and exit
            QMessageBox.critical(
                None,
                "Initialization Failed",
                "Failed to initialize MATLAB engine or validation system.\n"
                "Please check your MATLAB installation and try again."
            )
            app.quit()
    
    # Connect splash closed signal
    splash.closed.connect(on_splash_closed)
    
    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
