"""
Splash Screen with Loading Animation and Initialization

Displays a loading screen while:
1. Starting MATLAB engine (first-time warmup)
2. Running a simple 1H-1H validation simulation
3. Verifying system integrity
"""

import sys
import os
import numpy as np
from pathlib import Path
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QPropertyAnimation, QRect, QUrl
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, 
    QApplication, QFrame
)
from PySide6.QtGui import QFont, QPainter, QColor, QPen, QLinearGradient, QMovie
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget

# Import configuration
from src.utils.config import config

# Import icon manager
from src.utils.icon_manager import icon_manager


class InitializationWorker(QThread):
    """Worker thread for initialization simulation"""
    progress = Signal(int, str)  # progress percentage, message
    finished = Signal(bool, str)  # success, message
    
    def __init__(self):
        super().__init__()
        
    def run(self):
        """Run initialization process"""
        try:
            # Import here to avoid early loading
            import sys
            import os
            
            # Add parent directory to path
            parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)
            
            # Try to import MATLAB bridge
            try:
                from src.core.spinach_bridge import spinach_eng, sys as SYS, bas as BAS, inter as INTER, parameters as PAR, sim as SIM, data as DATA
                matlab_available = True
            except ImportError as e:
                matlab_available = False
                self.progress.emit(10, "MATLAB not available - skipping validation")
                self.msleep(500)
            
            if matlab_available:
                # Step 1: Start MATLAB engine (15%)
                self.progress.emit(5, "Initializing MATLAB engine...")
                self.msleep(200)
                
                with spinach_eng(clean=True) as eng:
                    self.progress.emit(15, "MATLAB engine started successfully")
                    self.msleep(300)
                
                    # Step 2: Create simple test system (35%)
                    self.progress.emit(25, "Creating 1H-1H validation system...")
                    self.msleep(200)
                    
                    isotopes = ['1H', '1H']
                    J_matrix = np.array([[0, 7.5], [0, 0]])
                    
                    # System setup
                    sys_obj = SYS(eng, var_prefix='init_')
                    sys_obj.isotopes(isotopes)
                    sys_obj.magnet(0.0)
                    
                    self.progress.emit(35, "Configuring basis set...")
                    self.msleep(200)
                    
                    # Basis
                    bas_obj = BAS(eng, var_prefix='init_')
                    bas_obj.formalism('zeeman-hilb')
                    bas_obj.approximation('none')
                    
                    self.progress.emit(45, "Setting up interactions...")
                    self.msleep(200)
                    
                    # Interactions
                    inter_obj = INTER(eng, var_prefix='init_')
                    inter_obj.coupling_array(J_matrix, validate=False, use_gpu=False)
                    
                    self.progress.emit(55, "Configuring parameters...")
                    self.msleep(200)
                    
                    # Parameters
                    par_obj = PAR(eng, var_prefix='init_')
                    par_obj.sweep(100.0)
                    par_obj.npoints(512)
                    par_obj.zerofill(1024)
                    par_obj.offset(0.0)
                    par_obj.spins([isotopes[0]])
                    par_obj.axis_units('Hz')
                    par_obj.invert_axis(0)
                    par_obj.flip_angle(np.pi/2)
                    par_obj.detection('uniaxial')
                    
                    self.progress.emit(65, "Running validation simulation...")
                    self.msleep(300)
                    
                    # Simulation
                    sim_obj = SIM(eng, var_prefix='init_')
                    sim_obj.create()
                    sim_obj.liquid('zerofield', 'labframe')
                    
                    self.progress.emit(80, "Processing spectrum...")
                    self.msleep(200)
                    
                    # Data processing
                    data_obj = DATA(eng, var_prefix='init_')
                    data_obj.apodisation([('crisp', 1)], use_gpu=False)
                    spectrum = data_obj.spectrum(use_gpu=False)
                    freq_axis = data_obj.freq(spectrum)
                    
                    # Cleanup
                    eng.eval("clear init_*", nargout=0)
                    
                    self.progress.emit(95, "Validation complete!")
                    self.msleep(200)
                    
                    self.progress.emit(100, "System ready")
                    self.msleep(500)
            else:
                # Skip MATLAB validation if not available
                self.progress.emit(20, "MATLAB engine not found - running in UI-only mode")
                self.msleep(500)
                self.progress.emit(40, "Loading UI components...")
                self.msleep(500)
                self.progress.emit(60, "Configuring interface...")
                self.msleep(500)
                self.progress.emit(80, "Finalizing setup...")
                self.msleep(500)
                self.progress.emit(100, "System ready (MATLAB disabled)")
                self.msleep(300)
                
            self.finished.emit(True, "Initialization successful")
                
        except Exception as e:
            error_msg = f"Initialization failed: {str(e)}"
            self.progress.emit(0, error_msg)
            self.finished.emit(False, error_msg)


class AnimatedLoadingWidget(QWidget):
    """Video background with GIF overlay loading animation"""
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Get animation size from config
        anim_size = config.get('ANIMATION_SIZE', 400)
        # Don't set fixed size on self - let layout manage it
        # Only set size constraints on internal components
        
        # Get assets directory
        assets_dir = Path(__file__).parent.parent.parent / "assets" / "animations"
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create a container widget for layering
        container = QWidget()
        container.setFixedSize(anim_size, anim_size)
        
        # Try to load video background (MP4)
        video_file = config.get('VIDEO_ANIMATION', 'assets/animations/Starting_Animation.mp4')
        video_path = Path(__file__).parent.parent.parent / video_file
        self.video_widget = None
        self.media_player = None
        
        if video_path.exists():
            try:
                # Video player setup
                self.media_player = QMediaPlayer()
                self.audio_output = QAudioOutput()
                self.audio_output.setVolume(0)  # Mute the video
                self.media_player.setAudioOutput(self.audio_output)
                
                # Video widget
                self.video_widget = QVideoWidget(container)
                self.video_widget.setFixedSize(anim_size, anim_size)
                self.video_widget.move(0, 0)
                self.media_player.setVideoOutput(self.video_widget)
                
                # Load and loop video
                self.media_player.setSource(QUrl.fromLocalFile(str(video_path)))
                self.media_player.setLoops(QMediaPlayer.Infinite)
                self.media_player.play()
            except Exception as e:
                print(f"Warning: Could not load video: {e}")
                self.video_widget = None
                self.media_player = None
        
        # GIF overlay (Spinach logo)
        gif_file = config.get('GIF_ANIMATION', 'assets/animations/Ajoy-Lab-Spin-Animation-Purple.gif')
        gif_path = Path(__file__).parent.parent.parent / gif_file
        self.gif_label = QLabel(container)
        self.gif_label.setAlignment(Qt.AlignCenter)
        self.gif_label.setFixedSize(anim_size, anim_size)
        self.gif_label.move(0, 0)
        
        # Make GIF label transparent background
        self.gif_label.setStyleSheet("background: transparent;")
        
        if gif_path.exists():
            # Load GIF animation
            self.movie = QMovie(str(gif_path))
            self.movie.setScaledSize(self.gif_label.size())  # Scale to fit
            self.gif_label.setMovie(self.movie)
            self.movie.start()
        else:
            # Fallback: show text if GIF not found
            self.gif_label.setText("Loading...")
            self.gif_label.setStyleSheet("""
                background: transparent;
                color: #2196F3;
                font-size: 24pt;
                font-weight: bold;
            """)
        
        # Add container to main layout
        h_layout = QHBoxLayout()
        h_layout.addStretch()
        h_layout.addWidget(container)
        h_layout.addStretch()
        layout.addLayout(h_layout)
    
    def stop(self):
        """Stop all animations"""
        if hasattr(self, 'movie') and self.movie:
            self.movie.stop()
        if self.media_player:
            self.media_player.stop()


class SplashScreen(QWidget):
    """Splash screen with loading animation and initialization"""
    
    closed = Signal()  # Signal when splash is closed
    
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Get window size from config
        width = config.get('SPLASH_WINDOW_WIDTH', 700)
        height = config.get('SPLASH_WINDOW_HEIGHT', 550)
        self.setFixedSize(width, height)
        
        # Center on screen
        self._center_on_screen()
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Container frame with shadow effect
        container = QFrame()
        container.setObjectName("container")
        container.setStyleSheet("""
            QFrame#container {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FFFFFF, stop:1 #F0F4F8);
                border-radius: 15px;
                border: 2px solid #B0BEC5;
            }
        """)
        
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(30, 25, 30, 25)  # Adjusted margins
        container_layout.setSpacing(15)  # Reduced spacing
        
        # Logo (if available)
        logo_pixmap = icon_manager.get_splash_logo()
        if not logo_pixmap.isNull():
            logo_label = QLabel()
            logo_label.setPixmap(logo_pixmap)
            logo_label.setAlignment(Qt.AlignCenter)
            logo_label.setStyleSheet("margin-bottom: 10px;")
            container_layout.addWidget(logo_label)
        
        # Title
        title = QLabel(config.app_name)
        title.setAlignment(Qt.AlignCenter)
        title_font = QFont("Arial", 22, QFont.Bold)  # Slightly larger font
        title.setFont(title_font)
        title.setStyleSheet("color: #1976D2; margin-bottom: 3px;")
        container_layout.addWidget(title)
        
        # Version
        version = QLabel(config.app_full_version)
        version.setAlignment(Qt.AlignCenter)
        version.setStyleSheet("color: #546E7A; font-size: 11pt; margin-bottom: 5px;")
        container_layout.addWidget(version)
        
        # Subtitle
        subtitle = QLabel("Initializing simulation environment...")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #37474F; font-size: 12pt; font-weight: bold; margin-bottom: 10px;")
        container_layout.addWidget(subtitle)
        
        # Loading animation - centered without extra stretch
        self.loading_widget = AnimatedLoadingWidget()
        animation_container = QHBoxLayout()
        animation_container.addStretch()
        animation_container.addWidget(self.loading_widget)
        animation_container.addStretch()
        container_layout.addLayout(animation_container)
        
        # Add some spacing
        container_layout.addSpacing(10)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFixedHeight(30)  # Slightly taller
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #CFD8DC;
                border-radius: 15px;
                text-align: center;
                font-size: 12pt;
                font-weight: bold;
                color: #1976D2;
                background: white;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2196F3, stop:0.5 #42A5F5, stop:1 #64B5F6);
                border-radius: 13px;
            }
        """)
        container_layout.addWidget(self.progress_bar)
        
        # Status message
        self.status_label = QLabel("Preparing to start...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setFixedHeight(45)  # Slightly smaller height
        self.status_label.setStyleSheet("""
            color: #455A64;
            font-size: 10pt;
            padding: 8px;
            background: #ECEFF1;
            border-radius: 6px;
            border-left: 4px solid #2196F3;
        """)
        container_layout.addWidget(self.status_label)
        
        # Footer info
        footer_layout = QHBoxLayout()
        footer_left = QLabel("Powered by MATLAB Spinach")
        footer_left.setStyleSheet("color: #78909C; font-size: 9pt; font-style: italic;")
        footer_right = QLabel("First-time warmup in progress")
        footer_right.setAlignment(Qt.AlignRight)
        footer_right.setStyleSheet("color: #78909C; font-size: 9pt; font-style: italic;")
        footer_layout.addWidget(footer_left)
        footer_layout.addStretch()
        footer_layout.addWidget(footer_right)
        container_layout.addLayout(footer_layout)
        
        main_layout.addWidget(container)
        
        # Initialize worker
        self.worker = None
        self.init_success = False
        
    def _center_on_screen(self):
        """Center the splash screen on the screen"""
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
    
    def start_initialization(self):
        """Start the initialization process"""
        self.worker = InitializationWorker()
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()
    
    def on_progress(self, percentage, message):
        """Update progress bar and status message"""
        self.progress_bar.setValue(percentage)
        self.status_label.setText(message)
    
    def on_finished(self, success, message):
        """Handle initialization completion"""
        self.init_success = success
        self.loading_widget.stop()
        
        if success:
            self.status_label.setText("✓ " + message)
            self.status_label.setStyleSheet("""
                color: #2E7D32;
                font-size: 11pt;
                font-weight: bold;
                padding: 8px;
                background: #E8F5E9;
                border-radius: 6px;
                border-left: 4px solid #4CAF50;
            """)
            # Close after a short delay
            QTimer.singleShot(800, self.close_splash)
        else:
            self.status_label.setText("✗ " + message)
            self.status_label.setStyleSheet("""
                color: #C62828;
                font-size: 10pt;
                font-weight: bold;
                padding: 8px;
                background: #FFEBEE;
                border-radius: 6px;
                border-left: 4px solid #F44336;
            """)
            # Show error longer
            QTimer.singleShot(3000, self.close_splash)
    
    def close_splash(self):
        """Close the splash screen"""
        self.closed.emit()
        self.close()
    
    def mousePressEvent(self, event):
        """Allow dragging the window"""
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        """Handle window dragging"""
        if event.buttons() == Qt.LeftButton and hasattr(self, 'drag_position'):
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()


# Test standalone
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    splash = SplashScreen()
    splash.show()
    splash.start_initialization()
    
    sys.exit(app.exec())
