"""
Icon Manager for Application

Handles loading and caching of application icons
"""

import sys
from pathlib import Path
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import QSize

from src.utils.config import config


class IconManager:
    """Manages application icons with fallback support"""
    
    _instance = None
    _icon_cache = {}
    
    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize icon manager"""
        if self._initialized:
            return
        
        self.project_root = Path(__file__).parent.parent.parent
        self._initialized = True
    
    def get_app_icon(self) -> QIcon:
        """
        Get main application icon
        
        Returns:
            QIcon: Application icon (or empty icon if not found)
        """
        if 'app_icon' in self._icon_cache:
            return self._icon_cache['app_icon']
        
        icon = QIcon()
        
        # Try ICO first (Windows native, multi-resolution)
        ico_path = config.get('APP_ICON', 'assets/icons/app_icon.ico')
        ico_file = self.project_root / ico_path
        
        if ico_file.exists():
            icon = QIcon(str(ico_file))
            self._icon_cache['app_icon'] = icon
            return icon
        
        # Fallback to PNG
        png_path = config.get('APP_ICON_PNG', 'assets/icons/app_icon.png')
        png_file = self.project_root / png_path
        
        if png_file.exists():
            icon = QIcon(str(png_file))
            self._icon_cache['app_icon'] = icon
            return icon
        
        # No icon found - return empty icon (app will use system default)
        print(f"Warning: Application icon not found at {ico_file} or {png_file}")
        print("Using system default icon. See assets/icons/README.md for icon setup guide.")
        
        self._icon_cache['app_icon'] = icon
        return icon
    
    def get_splash_logo(self) -> QPixmap:
        """
        Get splash screen logo
        
        Returns:
            QPixmap: Logo pixmap (or null pixmap if not found)
        """
        if 'splash_logo' in self._icon_cache:
            return self._icon_cache['splash_logo']
        
        logo_path = config.get('SPLASH_LOGO', 'assets/icons/splash_logo.png')
        logo_file = self.project_root / logo_path
        
        pixmap = QPixmap()
        
        if logo_file.exists():
            pixmap = QPixmap(str(logo_file))
            # Scale to reasonable size if too large
            if pixmap.width() > 256 or pixmap.height() > 256:
                pixmap = pixmap.scaled(256, 256, 
                                      aspectRatioMode=1,  # Qt.KeepAspectRatio
                                      transformMode=1)    # Qt.SmoothTransformation
        else:
            print(f"Info: Splash logo not found at {logo_file}")
            print("Splash screen will display without logo.")
        
        self._icon_cache['splash_logo'] = pixmap
        return pixmap
    
    def get_icon(self, name: str, size: int = 24) -> QIcon:
        """
        Get a named icon from assets/icons directory
        
        Args:
            name: Icon name (without extension)
            size: Preferred icon size (default: 24)
        
        Returns:
            QIcon: Icon (or empty icon if not found)
        """
        cache_key = f"{name}_{size}"
        
        if cache_key in self._icon_cache:
            return self._icon_cache[cache_key]
        
        icon = QIcon()
        
        # Try to find icon file with size suffix
        icon_file = self.project_root / "assets" / "icons" / f"{name}_{size}.png"
        
        if not icon_file.exists():
            # Try without size suffix
            icon_file = self.project_root / "assets" / "icons" / f"{name}.png"
        
        if icon_file.exists():
            icon = QIcon(str(icon_file))
        
        self._icon_cache[cache_key] = icon
        return icon
    
    def clear_cache(self):
        """Clear icon cache (useful for hot-reloading icons during development)"""
        self._icon_cache.clear()


# Global instance
icon_manager = IconManager()
