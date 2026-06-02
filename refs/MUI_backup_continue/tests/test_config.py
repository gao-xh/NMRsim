"""Test configuration loading"""

from src.utils.config import config

print("Configuration Test")
print("=" * 60)
print(f"App Name: {config.app_name}")
print(f"Version: {config.app_version}")
print(f"Date: {config.app_date}")
print(f"Full Version: {config.app_full_version}")
print(f"Description: {config.get('APP_DESCRIPTION')}")
print(f"Python Env: {config.get('PYTHON_ENV_PATH')}")
print(f"PySide6 Version: {config.get('PYSIDE6_VERSION')}")
print(f"Animation Size: {config.get('ANIMATION_SIZE')}")
print(f"Splash Window: {config.get('SPLASH_WINDOW_WIDTH')}x{config.get('SPLASH_WINDOW_HEIGHT')}")
print("=" * 60)
