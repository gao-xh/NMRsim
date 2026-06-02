"""
Configuration Manager

Loads and manages application configuration from config.txt
"""

import os
from pathlib import Path


class Config:
    """Application configuration singleton"""
    
    _instance = None
    _config = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self):
        """Load configuration from config.txt"""
        config_path = Path(__file__).parent.parent.parent / 'config.txt'
        
        if not config_path.exists():
            print(f"Warning: Config file not found at {config_path}")
            self._set_defaults()
            return
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    
                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse KEY = VALUE
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Convert boolean strings
                        if value.lower() == 'true':
                            value = True
                        elif value.lower() == 'false':
                            value = False
                        # Convert numeric strings
                        elif value.replace('.', '', 1).isdigit():
                            value = float(value) if '.' in value else int(value)
                        
                        self._config[key] = value
            
            print(f"Configuration loaded from {config_path}")
            
        except Exception as e:
            print(f"Error loading config: {e}")
            self._set_defaults()
    
    def _set_defaults(self):
        """Set default configuration values"""
        self._config = {
            'APP_NAME': 'Multi-System ZULF-NMR Simulator',
            'APP_VERSION': '3.0',
            'APP_DATE': 'October 2025',
            'APP_AUTHOR': 'Ajoy Lab',
            'APP_DESCRIPTION': 'Advanced ZULF-NMR simulation tool',
            'PYTHON_ENV_PATH': None,
            'PYSIDE6_VERSION': '6.7.3',
            'MATLAB_MIN_VERSION': 'R2021b',
            'FILE_FORMAT_VERSION': '2.0',
            'SPLASH_WINDOW_WIDTH': 700,
            'SPLASH_WINDOW_HEIGHT': 550,
            'ANIMATION_SIZE': 400,
        }
    
    def get(self, key, default=None):
        """Get configuration value"""
        return self._config.get(key, default)
    
    def __getattr__(self, key):
        """Allow attribute access to config values"""
        if key.startswith('_'):
            return object.__getattribute__(self, key)
        return self._config.get(key)
    
    def __getitem__(self, key):
        """Allow dictionary access to config values"""
        return self._config[key]
    
    @property
    def app_name(self):
        """Application name"""
        return self.get('APP_NAME', 'Multi-System ZULF-NMR Simulator')
    
    @property
    def app_version(self):
        """Application version"""
        return self.get('APP_VERSION', '3.0')
    
    @property
    def app_date(self):
        """Application date"""
        return self.get('APP_DATE', 'October 2025')
    
    @property
    def app_full_version(self):
        """Full version string"""
        return f"Version {self.app_version} ({self.app_date})"
    
    @property
    def app_title(self):
        """Full application title"""
        return f"{self.app_name} - {self.app_full_version}"
    
    def reload(self):
        """Reload configuration from file"""
        self._load_config()


# Global config instance
config = Config()


# Convenience functions
def get_config(key, default=None):
    """Get configuration value"""
    return config.get(key, default)


def reload_config():
    """Reload configuration"""
    config.reload()
