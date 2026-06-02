"""
Test Configuration and Imports (without MATLAB)

This test verifies the configuration system and imports
without requiring MATLAB to be installed.
"""

import sys
from pathlib import Path

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

print("=" * 60)
print("Configuration and Import Test")
print("=" * 60)
print()

# Test 1: Configuration Module
print("1. Testing configuration module...")
try:
    from src.utils.config import config
    print(f"   ✓ Config loaded successfully")
    print(f"   - App Name: {config.app_name}")
    print(f"   - Version: {config.app_version}")
    print(f"   - Python Env: {config.get('PYTHON_ENV_PATH')}")
    print()
except Exception as e:
    print(f"   ✗ Config failed: {e}")
    sys.exit(1)

# Test 2: Splash Screen Module
print("2. Testing splash screen module...")
try:
    from src.ui.splash_screen import SplashScreen, AnimatedLoadingWidget
    print(f"   ✓ Splash screen imported successfully")
    print()
except Exception as e:
    print(f"   ✗ Splash screen failed: {e}")
    sys.exit(1)

# Test 3: Save/Load Module
print("3. Testing save/load module...")
try:
    from src.utils.Save_Load import SaveLoad, MoleculeData, ParameterData
    print(f"   ✓ Save/Load imported successfully")
    print()
except Exception as e:
    print(f"   ✗ Save/Load failed: {e}")
    sys.exit(1)

# Test 4: File Structure
print("4. Checking file structure...")
required_dirs = [
    'src/core',
    'src/ui',
    'src/utils',
    'assets/animations',
    'presets/molecules',
    'presets/parameters',
    'user_save/molecules',
    'user_save/parameters',
    'docs',
]

project_root = Path(__file__).parent.parent  # Go up to MUI_10_7
all_exist = True

for dir_path in required_dirs:
    full_path = project_root / dir_path
    if full_path.exists():
        print(f"   ✓ {dir_path}")
    else:
        print(f"   ✗ {dir_path} - MISSING")
        all_exist = False

print()

# Test 5: Required Files
print("5. Checking required files...")
required_files = [
    'config.txt',
    'run.py',
    'requirements.txt',
    'Multi_system_spinach_UI.py',
    'src/__init__.py',
    'src/utils/config.py',
    'src/ui/splash_screen.py',
]

for file_path in required_files:
    full_path = project_root / file_path
    if full_path.exists():
        print(f"   ✓ {file_path}")
    else:
        print(f"   ✗ {file_path} - MISSING")
        all_exist = False

print()

# Test 6: Animation Assets
print("6. Checking animation assets...")
video_path = config.get('VIDEO_ANIMATION', 'assets/animations/Starting_Animation.mp4')
gif_path = config.get('GIF_ANIMATION', 'assets/animations/Ajoy-Lab-Spin-Animation-Purple.gif')

video_file = project_root / video_path
gif_file = project_root / gif_path

if video_file.exists():
    print(f"   ✓ Video: {video_path}")
else:
    print(f"   ! Video: {video_path} - Not found (optional)")

if gif_file.exists():
    print(f"   ✓ GIF: {gif_path}")
else:
    print(f"   ! GIF: {gif_path} - Not found (optional)")

print()

# Summary
print("=" * 60)
if all_exist:
    print("✓ All tests passed!")
    print("  Configuration system is working correctly")
    print("  File structure is complete")
    print()
    print("Note: MATLAB engine test skipped (requires MATLAB installation)")
else:
    print("✗ Some tests failed")
    print("  Please check the errors above")

print("=" * 60)
