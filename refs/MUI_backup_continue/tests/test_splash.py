"""
Test splash screen animation
"""
import sys
from PySide6.QtWidgets import QApplication
from src.ui.splash_screen import SplashScreen

def main():
    app = QApplication(sys.argv)
    
    # Create and show splash screen
    splash = SplashScreen()
    splash.show()
    
    print("Splash screen shown")
    print("Close the window to exit")
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
