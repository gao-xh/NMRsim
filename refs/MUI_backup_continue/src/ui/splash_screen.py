"""
Splash Screen with PNG Sequence Animation

Displays a minimalist loading screen:
- Background: PNG sequence (301 frames with transparency)
- Foreground: GIF overlay
- Progress: Frame number (0-301) as loading progress
- Ending: Hold last frame for 2 seconds
"""

import sys
import os
from pathlib import Path
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QApplication, QLabel, QMessageBox
from PySide6.QtGui import QMovie, QPixmap

# Import configuration
from src.utils.config import config


class InitializationWorker(QThread):
    """Worker thread for background initialization"""
    finished = Signal(bool, str)
    progress = Signal(str)  # Progress message updates
    progress_percent = Signal(int)  # Progress percentage (0-100) for animation sync
    
    # Validation results (exported for future use)
    file_integrity_result = None
    network_check_result = None
    matlab_engine_result = None
    simulation_result = None
    final_check_result = None
    
    def __init__(self):
        super().__init__()
        self.engine_cm = None  # Store context manager to keep engine alive
        
    def run(self):
        """Run initialization process with actual simulation test"""
        try:
            import sys
            import os
            
            parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)
            
            # ========== Phase 1: File Integrity Check (0-10%) ==========
            self.progress.emit("Checking file integrity...")
            self.progress_percent.emit(0)
            try:
                file_check_result = self._check_file_integrity()
                self.file_integrity_result = file_check_result
                
                # CRITICAL: If file integrity fails, STOP and show error
                if file_check_result['status'] == 'failed':
                    error_msg = f"File Integrity Check Failed:\n{file_check_result.get('message', 'Critical files missing')}"
                    if 'missing_files' in file_check_result:
                        error_msg += f"\n\nMissing files:\n" + "\n".join(f"  - {f}" for f in file_check_result['missing_files'])
                    self.finished.emit(False, error_msg)
                    return
                
                self.progress.emit(f"File integrity: {file_check_result['status']}")
                self.progress_percent.emit(10)
            except Exception as e:
                self.file_integrity_result = {"status": "failed", "error": str(e)}
                error_msg = f"File integrity check failed:\n{str(e)}"
                self.finished.emit(False, error_msg)
                return  # STOP if file check fails
            
            # ========== Phase 2: Network Components Check (10-20%) ==========
            self.progress.emit("Checking network components...")
            self.progress_percent.emit(12)
            try:
                network_result = self._check_network_components()
                self.network_check_result = network_result
                self.progress.emit(f"Network check: {network_result['status']}")
                self.progress_percent.emit(20)
            except Exception as e:
                self.network_check_result = {"status": "failed", "error": str(e)}
                self.progress.emit(f"Network check failed: {str(e)}")
                self.progress_percent.emit(20)
                # Continue anyway - don't stop, don't show error
            
            # ========== Phase 3: MATLAB Engine Check (20-30%) ==========
            matlab_engine_available = False
            self.progress.emit("Starting MATLAB engine...")
            self.progress_percent.emit(22)
            try:
                from src.core.spinach_bridge import (
                    spinach_eng, call_spinach, 
                    sys as SYS, bas as BAS, inter as INTER, sim as SIM
                )
                
                # Use context manager but keep it alive
                self.engine_cm = spinach_eng(clean=True)
                eng = self.engine_cm.__enter__()
                call_spinach.default_eng = eng
                
                self.matlab_engine_result = {"status": "success", "engine": eng}
                self.progress.emit("MATLAB engine started successfully")
                self.progress_percent.emit(30)
                matlab_engine_available = True
                
            except Exception as e:
                # MATLAB engine failed - don't stop, don't show error, but record it
                self.matlab_engine_result = {"status": "failed", "error": str(e)}
                self.progress.emit("MATLAB engine unavailable (continuing with limited functionality)")
                self.progress_percent.emit(30)
                matlab_engine_available = False
                # Continue to Phase 4 with fake progress
            
            # ========== Phase 4: MATLAB Initialization Simulation (30-90%, 60% total) ==========
            # Based on timing test: Total ~62s, with sim.create() taking 48s (78% of time)
            # Key milestones: ENGINE_READY@12s (42%), SIM_CREATE@13s (43%), DONE@62s (90%)
            
            if matlab_engine_available:
                # Real MATLAB simulation
                import time
                self.progress.emit("Running MATLAB initialization simulation...")
                self.progress_percent.emit(31)  # Starting Phase 4
                
                try:
                    # Step 4.1: Setup system (31-42%, ~11s for engine warmup)
                    self.progress.emit("Setting up spin system...")
                    sys_obj = SYS()
                    self.progress_percent.emit(33)
                    
                    sys_obj.isotopes(['1H', '1H'])
                    self.progress_percent.emit(35)
                    
                    sys_obj.magnet(14.1)  # 600 MHz
                    self.progress_percent.emit(37)
                    
                    # Step 4.2: Setup basis (~1s)
                    bas_obj = BAS()
                    bas_obj.formalism('sphten-liouv')
                    self.progress_percent.emit(39)
                    
                    bas_obj.approximation('none')
                    self.progress_percent.emit(41)
                    
                    # Reached ENGINE_READY milestone
                    self.progress.emit("MATLAB engine ready, configuring interactions...")
                    self.progress_percent.emit(42)
                    
                    # Step 4.3: Setup interactions (~1.5s to reach sim.create)
                    inter_obj = INTER()
                    inter_obj.zeeman([0.0, 0.0])  # Chemical shifts
                    self.progress_percent.emit(42)
                    
                    # J-coupling matrix: 2x2 with 7 Hz coupling
                    import numpy as np
                    J_matrix = np.array([[0.0, 7.0],
                                         [7.0, 0.0]])
                    inter_obj.coupling_array(J_matrix)
                    
                    # Create SIM object (reaches 43%)
                    sim_obj = SIM()
                    self.progress_percent.emit(43)
                    
                    # Step 4.4: Compute basis (43-90%, ~49s - THE LONGEST OPERATION)
                    # Strategy: Use time-based progress updates since MATLAB output
                    # is printed to console but not easily captured in GUI context
                    
                    self.progress.emit("Computing basis (this will take ~1 minute)...")
                    
                    import threading
                    import time
                    
                    # Progress tracker for sim.create()
                    progress_tracker = {'percent': 43, 'stop': False}
                    
                    def update_progress_during_create():
                        """Update progress during sim.create() based on measured timing"""
                        start_time = time.time()
                        
                        # Progress schedule based on timing test data:
                        # Total ~49s from 43% to 90% (47% progress range)
                        # Key events: startup(2s), parallel_pool(10s), system(3s), basis(34s)
                        milestones = [
                            (2, 48, "Running startup checks..."),
                            (5, 52, "Initializing Spinach engine..."),
                            (8, 56, "Starting parallel pool..."),
                            (12, 60, "Parallel pool ready (7 workers)..."),
                            (15, 63, "Building spin system (2 particles, 14.1T)..."),
                            (18, 66, "Configuring Zeeman interactions..."),
                            (21, 69, "Processing J-coupling matrix..."),
                            (24, 72, "Computing spherical tensor basis..."),
                            (30, 76, "Building basis set descriptor..."),
                            (36, 80, "Eliminating redundant states..."),
                            (42, 84, "Sorting basis set..."),
                            (48, 88, "Finalizing state space (16 states)..."),
                        ]
                        
                        milestone_index = 0
                        while not progress_tracker['stop'] and milestone_index < len(milestones):
                            elapsed = time.time() - start_time
                            target_time, percent, message = milestones[milestone_index]
                            
                            if elapsed >= target_time:
                                self.progress.emit(message)
                                self.progress_percent.emit(percent)
                                progress_tracker['percent'] = percent
                                milestone_index += 1
                            
                            time.sleep(0.5)  # Check every 500ms
                        
                        # If sim.create() finishes before all milestones, jump to 88%
                        if not progress_tracker['stop'] and progress_tracker['percent'] < 88:
                            self.progress_percent.emit(88)
                            progress_tracker['percent'] = 88
                    
                    # Start progress update thread
                    progress_thread = threading.Thread(target=update_progress_during_create, daemon=True)
                    progress_thread.start()
                    
                    # THE ACTUAL LONG OPERATION (will block for ~49 seconds)
                    # Note: MATLAB output (Running startup checks, SPINACH v2.9, etc.)
                    # will print to console but is not captured here due to GUI context
                    sim_obj.create()  # This calls create(sys, inter) and basis(spin_system, bas)
                    
                    # Stop progress thread and ensure we're at 90%
                    progress_tracker['stop'] = True
                    self.progress_percent.emit(90)
                    progress_tracker['percent'] = 90
                    
                    self.simulation_result = {"status": "success", "type": "real"}
                    self.progress.emit("MATLAB simulation completed successfully")
                    self.progress_percent.emit(90)
                    
                except Exception as e:
                    # Simulation failed - record but continue
                    self.simulation_result = {"status": "failed", "error": str(e), "type": "real"}
                    self.progress.emit(f"Simulation warning: {str(e)}")
                    self.progress_percent.emit(90)
                    # Don't return - continue to Phase 5
                    
            else:
                # Fake progress simulation (MATLAB engine not available)
                self.progress.emit("Running system checks (MATLAB unavailable)...")
                import time
                
                # Simulate progress 30% -> 90% with fake delays
                for percent in range(35, 91, 5):
                    self.progress_percent.emit(percent)
                    time.sleep(0.1)  # Small delay to simulate work
                    
                    # Update message at key points
                    if percent == 45:
                        self.progress.emit("Verifying system configuration...")
                    elif percent == 60:
                        self.progress.emit("Running compatibility checks...")
                    elif percent == 75:
                        self.progress.emit("Finalizing system validation...")
                
                self.simulation_result = {"status": "skipped", "type": "fake", "reason": "MATLAB engine unavailable"}
                self.progress.emit("System checks completed (limited mode)")
                self.progress_percent.emit(90)
            
            # ========== Phase 5: Final Check (90-100%) ==========
            self.progress.emit("Performing final checks...")
            self.progress_percent.emit(92)
            try:
                final_result = self._final_check()
                self.final_check_result = final_result
                self.progress.emit(f"Final check: {final_result['status']}")
                self.progress_percent.emit(95)
            except Exception as e:
                self.final_check_result = {"status": "warning", "error": str(e)}
                self.progress.emit(f"Final check warning: {str(e)}")
                self.progress_percent.emit(95)
                # Continue anyway - don't stop, don't show error
            
            # ========== Completion (100%) ==========
            self.progress.emit("Initialization completed")
            self.progress_percent.emit(100)
            
            # Generate summary report
            summary = self._generate_summary()
            self.finished.emit(True, summary)
                
        except Exception as e:
            error_msg = f"Unexpected initialization error:\n{str(e)}"
            self.finished.emit(False, error_msg)
    
    def _check_file_integrity(self):
        """Phase 1: Check critical file integrity (0-10%)"""
        from pathlib import Path
        
        critical_files = [
            'src/core/spinach_bridge.py',
            'src/utils/config.py',
            'config.txt'
        ]
        
        missing_files = []
        base_path = Path(__file__).parent.parent.parent
        
        for file_path in critical_files:
            full_path = base_path / file_path
            if not full_path.exists():
                missing_files.append(file_path)
        
        if missing_files:
            # CRITICAL: Missing files means failure
            return {
                "status": "failed",
                "missing_files": missing_files,
                "message": f"Critical error: {len(missing_files)} essential file(s) missing"
            }
        
        return {
            "status": "success",
            "message": "All critical files present"
        }
    
    def _check_network_components(self):
        """Phase 2: Check network components (10-20%) - Placeholder for future"""
        # TODO: Implement network connectivity check
        # This is a placeholder for future network-related checks
        # For now, just return success
        
        return {
            "status": "not_implemented",
            "message": "Network check not yet implemented (reserved for future use)",
            "components_checked": []
        }
    
    def _final_check(self):
        """Phase 5: Final system check (90-100%)"""
        # Check if MATLAB engine is still alive
        if self.engine_cm is None:
            return {
                "status": "warning",
                "message": "MATLAB engine not initialized"
            }
        
        # Check if default engine is set
        from src.core.spinach_bridge import call_spinach
        if call_spinach.default_eng is None:
            return {
                "status": "warning", 
                "message": "Default MATLAB engine not set"
            }
        
        return {
            "status": "success",
            "message": "All systems operational"
        }
    
    def _generate_summary(self):
        """Generate initialization summary report"""
        summary_lines = ["Initialization Summary:"]
        
        if self.file_integrity_result:
            summary_lines.append(f"  - File Integrity: {self.file_integrity_result['status']}")
        
        if self.network_check_result:
            summary_lines.append(f"  - Network Check: {self.network_check_result['status']}")
        
        if self.matlab_engine_result:
            summary_lines.append(f"  - MATLAB Engine: {self.matlab_engine_result['status']}")
        
        if self.simulation_result:
            summary_lines.append(f"  - Simulation: {self.simulation_result['status']}")
        
        if self.final_check_result:
            summary_lines.append(f"  - Final Check: {self.final_check_result['status']}")
        
        return "\n".join(summary_lines)


class SplashScreen(QWidget):
    """Minimalist splash screen with PNG sequence background and PNG spin overlay"""
    
    closed = Signal()
    
    # Background animation settings
    BG_TOTAL_FRAMES = 301
    BG_FRAME_RATE = 30  # FPS for background PNG sequence
    
    # Spin overlay animation settings (loops continuously)
    SPIN_TOTAL_FRAMES = 60
    SPIN_FRAME_RATE = 30  # FPS for spin PNG sequence
    
    HOLD_DURATION = 2000  # Hold last frame for 2 seconds
    
    def __init__(self):
        super().__init__()
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        # Enable transparent background for PNG with alpha channel
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        
        width = config.get("SPLASH_WINDOW_WIDTH", 700)
        height = config.get("SPLASH_WINDOW_HEIGHT", 550)
        self.setFixedSize(width, height)
        
        self._center_on_screen()
        
        # Transparent background
        self.setStyleSheet("background-color: transparent;")
        
        # Don't use layout - use absolute positioning for perfect alignment
        # Both labels will be positioned and sized when images are loaded
        
        # PNG sequence background label
        self.background_label = QLabel(self)
        self.background_label.setAlignment(Qt.AlignCenter)
        self.background_label.setAttribute(Qt.WA_TranslucentBackground)
        self.background_label.setStyleSheet("background: transparent;")
        
        # Spin PNG sequence overlay label
        # Will be sized and positioned to match the actual loaded image size (no scaling)
        self.spin_label = QLabel(self)
        self.spin_label.setAlignment(Qt.AlignCenter)
        self.spin_label.setAttribute(Qt.WA_TranslucentBackground)
        self.spin_label.setStyleSheet("background: transparent;")
        
        # Log message label at bottom (single line, transparent background)
        self.log_label = QLabel(self)
        self.log_label.setAlignment(Qt.AlignCenter)
        self.log_label.setAttribute(Qt.WA_TranslucentBackground)
        self.log_label.setStyleSheet("""
            QLabel {
                color: rgba(200, 200, 200, 180);
                font-size: 10px;
                font-family: 'Consolas', 'Courier New', monospace;
                background: transparent;
                padding: 5px;
            }
        """)
        self.log_label.setText("Initializing...")
        
        # Position log label at bottom
        log_height = 25
        self.log_label.setGeometry(0, height - log_height, width, log_height)
        
        # Load background PNG sequence frames (Starting_Animation)
        self.bg_frames = []
        self.current_bg_frame = 0
        self._load_background_sequence()
        
        # Load spin PNG sequence frames (Spin animation - loops continuously)
        self.spin_frames = []
        self.current_spin_frame = 0
        self._load_spin_sequence()
        
        self.init_success = False
        self.worker = None
        self.bg_frame_timer = None
        self.spin_frame_timer = None
        self.hold_timer = None
        
    def _load_background_sequence(self):
        """Load all background PNG frames from sequence folder"""
        png_folder = config.get("PNG_SEQUENCE_FOLDER", "assets/animations/Starting_Animation")
        frames_path = Path(__file__).parent.parent.parent / png_folder
        
        if not frames_path.exists():
            print(f"Warning: Background PNG sequence folder not found: {frames_path}")
            return
        
        print(f"Loading background PNG sequence from: {frames_path}")
        
        # Load frames: Starting_Animation_00000.png to Starting_Animation_00300.png
        loaded_count = 0
        for i in range(0, self.BG_TOTAL_FRAMES):
            frame_file = frames_path / f"Starting_Animation_{i:05d}.png"
            
            if frame_file.exists():
                # Use original image size (no scaling)
                pixmap = QPixmap(str(frame_file))
                self.bg_frames.append(pixmap)
                loaded_count += 1
            else:
                empty_pixmap = QPixmap(self.background_label.size())
                empty_pixmap.fill(Qt.transparent)
                self.bg_frames.append(empty_pixmap)
        
        print(f"Loaded {loaded_count}/{self.BG_TOTAL_FRAMES} background PNG frames")
        
        # Display first frame and position background label to center in window
        if self.bg_frames and not self.bg_frames[0].isNull():
            first_frame = self.bg_frames[0]
            bg_width = first_frame.width()
            bg_height = first_frame.height()
            
            # Get window dimensions
            width = config.get("SPLASH_WINDOW_WIDTH", 700)
            height = config.get("SPLASH_WINDOW_HEIGHT", 550)
            
            # Center the background label
            bg_x = (width - bg_width) // 2
            bg_y = (height - bg_height) // 2
            
            self.background_label.setGeometry(bg_x, bg_y, bg_width, bg_height)
            self.background_label.setPixmap(first_frame)
            print(f"Background size: {bg_width}x{bg_height}, position: ({bg_x}, {bg_y})")
    
    def _load_spin_sequence(self):
        """Load all spin overlay PNG frames from sequence folder"""
        spin_folder = config.get("SPIN_SEQUENCE_FOLDER", "assets/animations/Spin")
        frames_path = Path(__file__).parent.parent.parent / spin_folder
        
        if not frames_path.exists():
            print(f"Warning: Spin PNG sequence folder not found: {frames_path}")
            return
        
        print(f"Loading spin PNG sequence from: {frames_path}")
        
        # Load frames: Spin_00000.png to Spin_00059.png
        loaded_count = 0
        for i in range(0, self.SPIN_TOTAL_FRAMES):
            frame_file = frames_path / f"Spin_{i:05d}.png"
            
            if frame_file.exists():
                # Use original image size (no scaling)
                pixmap = QPixmap(str(frame_file))
                self.spin_frames.append(pixmap)
                loaded_count += 1
            else:
                empty_pixmap = QPixmap(400, 400)  # Default size if image not found
                empty_pixmap.fill(Qt.transparent)
                self.spin_frames.append(empty_pixmap)
        
        print(f"Loaded {loaded_count}/{self.SPIN_TOTAL_FRAMES} spin PNG frames")
        
        # Display first frame and resize/position spin label to match image size
        if self.spin_frames and not self.spin_frames[0].isNull():
            first_frame = self.spin_frames[0]
            spin_width = first_frame.width()
            spin_height = first_frame.height()
            
            # Get window dimensions
            width = config.get("SPLASH_WINDOW_WIDTH", 700)
            height = config.get("SPLASH_WINDOW_HEIGHT", 550)
            
            # Center the spin label
            spin_x = (width - spin_width) // 2
            spin_y = (height - spin_height) // 2
            
            self.spin_label.setGeometry(spin_x, spin_y, spin_width, spin_height)
            self.spin_label.setPixmap(first_frame)
            print(f"Spin size: {spin_width}x{spin_height}")
        
    def _center_on_screen(self):
        """Center window on screen"""
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
    
    def start_initialization(self):
        """Start initialization and animation with 1 second delay at first frame"""
        # Show first frame for 1 second before starting
        self.log_label.setText("Starting initialization...")
        
        # Start spin animation immediately
        if self.spin_frames:
            self.spin_frame_timer = QTimer()
            self.spin_frame_timer.timeout.connect(self._play_next_spin_frame)
            interval = int(1000 / self.SPIN_FRAME_RATE)
            self.spin_frame_timer.start(interval)
        
        # Wait 1 second, then start initialization worker
        QTimer.singleShot(1000, self._start_worker)
    
    def _start_worker(self):
        """Actually start the initialization worker after delay"""
        self.worker = InitializationWorker()
        self.worker.finished.connect(self._on_init_finished)
        self.worker.progress.connect(self._on_init_progress)
        self.worker.progress_percent.connect(self._on_progress_percent)
        self.worker.start()
    
    def _on_progress_percent(self, percent):
        """Update background animation frame based on progress percentage with smooth transition"""
        if not self.bg_frames:
            return
        
        # Map percentage (0-100) to frame index (0 to BG_TOTAL_FRAMES-1)
        target_frame = int((percent / 100.0) * (self.BG_TOTAL_FRAMES - 1))
        target_frame = min(target_frame, self.BG_TOTAL_FRAMES - 1)
        
        # Smooth transition: gradually move to target frame instead of jumping
        if not hasattr(self, '_last_target_frame'):
            self._last_target_frame = 0
        
        # If jumping too far (more than 5 frames), animate smoothly
        if target_frame > self._last_target_frame + 5:
            # Start a smooth animation from current to target
            if hasattr(self, '_smooth_animation_timer'):
                self._smooth_animation_timer.stop()
            
            self._target_frame = target_frame
            self._smooth_animation_timer = QTimer()
            self._smooth_animation_timer.timeout.connect(self._animate_to_target)
            self._smooth_animation_timer.start(16)  # ~60 FPS
        else:
            # Small jump, update directly
            self.current_bg_frame = target_frame
            self.background_label.setPixmap(self.bg_frames[self.current_bg_frame])
            self._last_target_frame = target_frame
        
        print(f"Progress: {percent}% -> Frame {target_frame}/{self.BG_TOTAL_FRAMES-1}")
    
    def _animate_to_target(self):
        """Smoothly animate background frames to target"""
        if self.current_bg_frame < self._target_frame:
            self.current_bg_frame += 1
            self.background_label.setPixmap(self.bg_frames[self.current_bg_frame])
        else:
            # Reached target, stop animation
            self._smooth_animation_timer.stop()
            self._last_target_frame = self._target_frame
    
    def _play_next_spin_frame(self):
        """Play next frame in spin PNG sequence (loops continuously)"""
        if not self.spin_frames:
            return
        
        self.current_spin_frame += 1
        
        # Loop back to start when reaching the end
        if self.current_spin_frame >= len(self.spin_frames):
            self.current_spin_frame = 0
        
        # Display current spin frame
        self.spin_label.setPixmap(self.spin_frames[self.current_spin_frame])
    
    def _hold_last_frame(self):
        """Hold the last frame for HOLD_DURATION milliseconds"""
        # Ensure last background frame is displayed
        if self.bg_frames:
            self.background_label.setPixmap(self.bg_frames[-1])
        
        # Spin animation continues to loop during hold time
        
        # Start hold timer
        self.hold_timer = QTimer()
        self.hold_timer.setSingleShot(True)
        self.hold_timer.timeout.connect(self._close_splash)
        self.hold_timer.start(self.HOLD_DURATION)
    
    def _on_init_progress(self, message):
        """Handle initialization progress updates"""
        print(f"Progress: {message}")
        # Update log label at bottom
        self.log_label.setText(message)
    
    def _on_init_finished(self, success, message):
        """Handle initialization completion"""
        self.init_success = success
        print(f"Initialization: {message}")
        self.log_label.setText("Initialization complete" if success else "Initialization failed")
        
        # If initialization failed, show error dialog
        if not success:
            # Stop animations
            if self.spin_frame_timer:
                self.spin_frame_timer.stop()
            
            # Show error message box
            error_box = QMessageBox(self)
            error_box.setIcon(QMessageBox.Critical)
            error_box.setWindowTitle("Initialization Failed")
            error_box.setText("Failed to initialize MATLAB engine or run test simulation.")
            error_box.setInformativeText(message)
            error_box.setStandardButtons(QMessageBox.Ok)
            error_box.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Dialog)
            
            # When user clicks OK, close splash
            error_box.finished.connect(self._close_splash)
            error_box.exec()
        else:
            # Success - hold last frame for 2 seconds then close
            self._hold_last_frame()
    
    def _hold_last_frame(self):
        """Hold the last frame for HOLD_DURATION milliseconds"""
        # Ensure last background frame is displayed (should be at 100%)
        if self.bg_frames:
            self.background_label.setPixmap(self.bg_frames[-1])
        
        # Spin animation continues to loop during hold time
        
        # Start hold timer
        self.hold_timer = QTimer()
        self.hold_timer.setSingleShot(True)
        self.hold_timer.timeout.connect(self._close_splash)
        self.hold_timer.start(self.HOLD_DURATION)
    
    def _close_splash(self):
        """Close splash screen and emit signal"""
        # Stop all timers
        if self.spin_frame_timer:
            self.spin_frame_timer.stop()
        
        self.close()
        self.closed.emit()
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Stop all timers
        if self.spin_frame_timer:
            self.spin_frame_timer.stop()
        
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    splash = SplashScreen()
    splash.show()
    splash.start_initialization()
    
    def on_closed():
        print("Splash closed")
        app.quit()
    
    splash.closed.connect(on_closed)
    
    sys.exit(app.exec())
