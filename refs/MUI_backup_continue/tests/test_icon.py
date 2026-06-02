"""
Test Icon Loading

Quick test to verify icon files load correctly
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

from src.utils.icon_manager import icon_manager
from src.utils.config import config

def test_icons():
    """Test icon loading"""
    app = QApplication(sys.argv)
    
    # Create test window
    window = QWidget()
    window.setWindowTitle("Icon Test - " + config.app_name)
    window.resize(400, 300)
    
    layout = QVBoxLayout(window)
    
    # Test app icon
    print("Testing application icon...")
    app_icon = icon_manager.get_app_icon()
    
    if app_icon.isNull():
        print("❌ Application icon not found or failed to load")
        layout.addWidget(QLabel("❌ Application icon NOT loaded"))
    else:
        print("✅ Application icon loaded successfully")
        window.setWindowIcon(app_icon)
        
        # Show icon info
        sizes = app_icon.availableSizes()
        if sizes:
            print(f"   Available sizes: {[f'{s.width()}x{s.height()}' for s in sizes]}")
            
            # Display icon
            pixmap = app_icon.pixmap(128, 128)
            icon_label = QLabel()
            icon_label.setPixmap(pixmap)
            icon_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(icon_label)
            
            status_label = QLabel(f"✅ Application Icon Loaded\nSize: {pixmap.width()}x{pixmap.height()}")
            status_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(status_label)
        else:
            layout.addWidget(QLabel("⚠️ Icon loaded but no sizes available"))
    
    # Test splash logo
    print("\nTesting splash logo...")
    splash_logo = icon_manager.get_splash_logo()
    
    if splash_logo.isNull():
        print("ℹ️  Splash logo not found (optional)")
        layout.addWidget(QLabel("\nℹ️  Splash logo not set (optional)"))
    else:
        print("✅ Splash logo loaded successfully")
        print(f"   Size: {splash_logo.width()}x{splash_logo.height()}")
        
        logo_label = QLabel()
        logo_label.setPixmap(splash_logo)
        logo_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo_label)
        
        logo_status = QLabel(f"✅ Splash Logo Loaded\nSize: {splash_logo.width()}x{splash_logo.height()}")
        logo_status.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo_status)
    
    print("\n" + "="*50)
    print("Icon paths configured in config.txt:")
    print(f"  APP_ICON: {config.get('APP_ICON', 'NOT SET')}")
    print(f"  APP_ICON_PNG: {config.get('APP_ICON_PNG', 'NOT SET')}")
    print(f"  SPLASH_LOGO: {config.get('SPLASH_LOGO', 'NOT SET')}")
    print("="*50)
    
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    test_icons()
