import sys
import re
import numpy as np
from datetime import datetime
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QDoubleSpinBox, QLineEdit, QPushButton, QMessageBox, QTextEdit, 
    QLabel, QTabWidget, QFormLayout, QGroupBox, QSplitter, QCheckBox,
    QComboBox, QSlider, QScrollArea, QFileDialog, QInputDialog, QFrame,
    QStackedWidget, QGridLayout, QDialog
)
from PySide6.QtGui import QAction
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavToolbar
from matplotlib.figure import Figure

from src.core.spinach_bridge import (
    call_spinach, sys as SYS, bas as BAS, inter as INTER, 
    parameters as PAR, sim as SIM, data as DATA, spinach_eng
)

# Import configuration
from src.utils.config import config

# Import icon manager
from src.utils.icon_manager import icon_manager

# Import Save_Load module
try:
    from src.utils.Save_Load import SaveLoad, MoleculeData, ParameterData, SpectrumData
except ImportError:
    SaveLoad = None
    MoleculeData = None
    ParameterData = None
    SpectrumData = None


# ---------- Configuration Constants ----------
# UI Configuration
MAX_SYSTEMS = 10  # Maximum number of systems allowed
DEFAULT_WINDOW_WIDTH = 1400
DEFAULT_WINDOW_HEIGHT = 900

# J-Coupling Grid Configuration
GRID_INPUT_WIDTH = 60
GRID_INPUT_HEIGHT_MIN = 35
POPUP_EDITOR_WIDTH = 800
POPUP_EDITOR_HEIGHT = 600
POPUP_GRID_INPUT_WIDTH = 80
POPUP_GRID_INPUT_HEIGHT = 35

# Default Simulation Parameters
DEFAULT_MAGNET = 0.0
DEFAULT_SWEEP = 400.0
DEFAULT_NPOINTS = 2048
DEFAULT_ZEROFILL = 8192


# ---------- MATLAB Engine manager ----------
class EngineManager:
    def __init__(self):
        self._cm = None
        self._eng = None

    def start(self, clean: bool = True):
        self.stop()
        cm = spinach_eng(clean=clean)
        eng = cm.__enter__()
        call_spinach.default_eng = eng
        self._cm = cm
        self._eng = eng

    def stop(self):
        if self._cm is not None:
            try:
                self._cm.__exit__(None, None, None)
            except:
                pass
        self._cm = None
        self._eng = None
        call_spinach.default_eng = None

    @property
    def running(self) -> bool:
        return self._eng is not None


ENGINE = EngineManager()


# ---------- Helper functions ----------
def parse_isotopes(text):
    """Parse isotopes from comma-separated text"""
    return [s.strip() for s in text.replace('\n', ',').split(',') if s.strip()]


def parse_symmetry(text):
    """
    Parse symmetry spins from text. Supports multiple groups.
    Examples:
      - Single group: '1 2 3' or '1,2,3' -> [[1,2,3]]
      - Multiple groups: '1 2 3; 4 5' or '[1,2,3], [4,5]' -> [[1,2,3], [4,5]]
      - Line-separated: '1 2 3\n4 5' -> [[1,2,3], [4,5]]
    """
    if not text.strip():
        return None
    
    # Normalize input: remove brackets and split by semicolon or newline
    normalized = text.replace('[', '').replace(']', '').replace(';', '\n')
    lines = [line.strip() for line in normalized.split('\n') if line.strip()]
    
    groups = []
    for line in lines:
        # Split by comma or space
        parts = line.replace(',', ' ').split()
        if parts:
            try:
                group = [int(x) for x in parts]
                if group:
                    groups.append(group)
            except ValueError:
                continue
    
    return groups if groups else None


def extract_variables_from_matrix(matrix_text):
    """Extract all variable names (letters) from J matrix text"""
    # Find all sequences of letters (variable names)
    variables = set()
    for match in re.finditer(r'[a-zA-Z_][a-zA-Z0-9_]*', matrix_text):
        var = match.group()
        # Exclude common numpy functions
        if var not in ['np', 'array', 'zeros', 'ones', 'pi', 'e']:
            variables.add(var)
    return sorted(variables)


def evaluate_matrix(matrix_text, var_values):
    """Evaluate J matrix with variable substitutions"""
    # Create namespace with numpy and variables
    namespace = {'np': np, 'array': np.array, 'zeros': np.zeros, 'ones': np.ones}
    namespace.update(var_values)
    
    try:
        # Evaluate the expression
        result = eval(matrix_text, namespace)
        return np.array(result, dtype=float)
    except Exception as e:
        raise ValueError(f"Failed to evaluate matrix: {e}")


# ---------- Worker thread for simulation ----------
class SimWorker(QThread):
    log = Signal(str)
    detailed_log = Signal(str)  # For detailed MATLAB output
    progress = Signal(int)
    done = Signal(np.ndarray, np.ndarray, str)  # freq, spec, system_name
    failed = Signal(str)

    def __init__(self, isotopes, J_matrix, magnet, sweep, npoints, zerofill, 
                 offset, sym_spins, sym_group_name, system_name, use_gpu=False,
                 approximation='none', formalism='zeeman-hilb', window_type='exp', window_k=10):
        super().__init__()
        self.isotopes = isotopes
        self.J_matrix = J_matrix
        self.magnet = magnet
        self.sweep = sweep
        self.npoints = npoints
        self.zerofill = zerofill
        self.offset = offset
        self.sym_spins = sym_spins
        self.sym_group_name = sym_group_name
        self.system_name = system_name
        self.use_gpu = use_gpu
        self.approximation = approximation
        self.formalism = formalism
        self.window_type = window_type
        self.window_k = window_k

    def run(self):
        try:
            self.log.emit(f"[{self.system_name}] Starting simulation...")
            self.detailed_log.emit(f"\n{'='*60}")
            self.detailed_log.emit(f"[{self.system_name}] DETAILED SIMULATION LOG")
            self.detailed_log.emit(f"{'='*60}")
            self.detailed_log.emit(f"Isotopes: {self.isotopes}")
            self.detailed_log.emit(f"Magnet field: {self.magnet} T")
            self.detailed_log.emit(f"Sweep: {self.sweep} Hz, Points: {self.npoints}, Zerofill: {self.zerofill}")
            self.detailed_log.emit(f"J-matrix shape: {self.J_matrix.shape}")
            self.progress.emit(10)
            
            if not ENGINE.running:
                self.log.emit("Starting MATLAB engine...")
                self.detailed_log.emit("Initializing MATLAB engine...")
                ENGINE.start(clean=True)
                self.detailed_log.emit("MATLAB engine started successfully")
            
            self.progress.emit(30)
            
            # Use system_name as variable prefix to avoid conflicts in multi-system simulations
            var_prefix = self.system_name.replace(' ', '_').replace('-', '_') + '_'
            self.detailed_log.emit(f"Variable prefix: {var_prefix}")
            
            # Setup Spinach system
            self.detailed_log.emit("Creating Spinach system object...")
            sys_obj = SYS(ENGINE._eng, var_prefix=var_prefix)
            sys_obj.isotopes(self.isotopes)
            sys_obj.magnet(self.magnet)
            self.detailed_log.emit(f"  → isotopes: {self.isotopes}")
            self.detailed_log.emit(f"  → magnet: {self.magnet} T")
            
            # Setup basis with symmetry
            self.detailed_log.emit("Creating basis object...")
            bas_obj = BAS(ENGINE._eng, var_prefix=var_prefix)
            bas_obj.formalism(self.formalism)
            bas_obj.approximation(self.approximation)
            self.detailed_log.emit(f"  → formalism: {self.formalism}")
            self.detailed_log.emit(f"  → approximation: {self.approximation}")
            
            self.log.emit(f"[{self.system_name}] Using formalism: {self.formalism}, approximation: {self.approximation}")
            
            # Handle symmetry groups - only if explicitly provided
            if self.sym_group_name and self.sym_spins:
                if isinstance(self.sym_group_name, list) and len(self.sym_group_name) > 0:
                    # Multiple symmetry groups
                    valid_groups = [g for g in self.sym_group_name if g and g.lower() != 'none' and not g.startswith('---')]
                    if valid_groups and len(self.sym_spins) == len(valid_groups):
                        self.log.emit(f"[{self.system_name}] Symmetry: {len(valid_groups)} group(s), {sum(len(s) for s in self.sym_spins)} spin(s)")
                        self.detailed_log.emit(f"Symmetry groups: {valid_groups}")
                        self.detailed_log.emit(f"Symmetry spins: {self.sym_spins}")
                        bas_obj.sym_group(valid_groups)
                        bas_obj.sym_spins(self.sym_spins)
                    else:
                        self.log.emit(f"[{self.system_name}] Symmetry: disabled (invalid configuration)")
                        self.detailed_log.emit("Symmetry: Invalid configuration, disabled")
                elif isinstance(self.sym_group_name, str) and self.sym_group_name and self.sym_group_name.lower() != 'none' and not self.sym_group_name.startswith('---'):
                    # Single symmetry group (backward compatibility)
                    sym_spins_list = self.sym_spins if isinstance(self.sym_spins[0], list) else [self.sym_spins]
                    self.log.emit(f"[{self.system_name}] Symmetry: 1 group, {sum(len(s) for s in sym_spins_list)} spin(s)")
                    self.detailed_log.emit(f"Symmetry group: {self.sym_group_name}")
                    self.detailed_log.emit(f"Symmetry spins: {sym_spins_list}")
                    bas_obj.sym_group([self.sym_group_name])
                    bas_obj.sym_spins(sym_spins_list)
                else:
                    self.log.emit(f"[{self.system_name}] Symmetry: disabled")
                    self.detailed_log.emit("Symmetry: disabled")
            else:
                self.log.emit(f"[{self.system_name}] Symmetry: disabled")
                self.detailed_log.emit("Symmetry: not specified")

            
            self.progress.emit(50)
            
            # Setup interactions (don't use GPU here to avoid type mismatch in basis creation)
            self.detailed_log.emit("Setting up interactions...")
            inter_obj = INTER(ENGINE._eng, var_prefix=var_prefix)
            inter_obj.coupling_array(self.J_matrix, validate=False, use_gpu=False)
            self.detailed_log.emit(f"  → J-coupling matrix loaded: {self.J_matrix.shape}")
            
            # Setup parameters
            self.detailed_log.emit("Setting acquisition parameters...")
            par_obj = PAR(ENGINE._eng, var_prefix=var_prefix)
            par_obj.sweep(self.sweep)
            par_obj.npoints(self.npoints)
            par_obj.zerofill(self.zerofill)
            par_obj.offset(self.offset)
            par_obj.spins([self.isotopes[0]])
            par_obj.axis_units('Hz')
            par_obj.invert_axis(0)
            par_obj.flip_angle(np.pi/2)
            par_obj.detection('uniaxial')
            self.detailed_log.emit(f"  → sweep={self.sweep} Hz, npoints={self.npoints}, zerofill={self.zerofill}")
            
            self.progress.emit(70)
            
            # Create and run simulation
            self.detailed_log.emit("Creating Spinach system and running simulation...")
            sim_obj = SIM(ENGINE._eng, var_prefix=var_prefix)
            sim_obj.create()
            self.detailed_log.emit("  → Spinach system created")
            sim_obj.liquid('zerofield', 'labframe')
            self.detailed_log.emit("  → Liquid-state simulation completed")
            
            self.progress.emit(80)
            
            # Process data
            self.detailed_log.emit("Processing FID data...")
            data_obj = DATA(ENGINE._eng, var_prefix=var_prefix)
            
            # Apply window function
            if self.window_type != 'none':
                window_params = [(self.window_type, self.window_k)]
                self.log.emit(f"[{self.system_name}] Applying window: {self.window_type} (k={self.window_k})")
                self.detailed_log.emit(f"  → Applying {self.window_type} window (k={self.window_k})")
                data_obj.apodisation(window_params, use_gpu=self.use_gpu)
            else:
                self.log.emit(f"[{self.system_name}] No window function applied")
                self.detailed_log.emit("  → No window function applied (crisp)")
                data_obj.apodisation([('crisp', 1)], use_gpu=self.use_gpu)
            
            self.detailed_log.emit("Computing spectrum via FFT...")
            spectrum = data_obj.spectrum(use_gpu=self.use_gpu)
            freq_axis = data_obj.freq(spectrum)
            self.detailed_log.emit(f"  → Spectrum computed: {len(freq_axis)} points")
            self.detailed_log.emit(f"  → Frequency range: {freq_axis.min():.2f} to {freq_axis.max():.2f} Hz")
            
            self.progress.emit(100)
            self.log.emit(f"[{self.system_name}] Simulation completed!")
            self.detailed_log.emit(f"{'='*60}\n")
            
            self.done.emit(freq_axis, spectrum, self.system_name)
            
        except Exception as e:
            error_msg = f"[{self.system_name}] Error: {str(e)}"
            self.log.emit(error_msg)
            self.detailed_log.emit(f"\n!!! ERROR !!!\n{error_msg}\n{'='*60}\n")
            self.failed.emit(f"[{self.system_name}] {str(e)}")


# ---------- Worker thread for post-processing only ----------
class PostProcessWorker(QThread):
    """Worker to reprocess existing FID data with new window/zerofill settings"""
    log = Signal(str)
    detailed_log = Signal(str)  # For detailed MATLAB output
    progress = Signal(int)
    done = Signal(np.ndarray, np.ndarray, str)  # freq, spec, system_name
    failed = Signal(str)

    def __init__(self, system_name, window_type, window_k, zerofill, use_gpu=False):
        super().__init__()
        self.system_name = system_name
        self.window_type = window_type
        self.window_k = window_k
        self.zerofill = zerofill
        self.use_gpu = use_gpu

    def run(self):
        try:
            self.log.emit(f"[{self.system_name}] Reprocessing with new settings...")
            self.progress.emit(20)
            
            if not ENGINE.running:
                self.log.emit("MATLAB engine not running. Please run full simulation first.")
                self.failed.emit(f"[{self.system_name}] MATLAB engine not running")
                return
            
            self.progress.emit(40)
            
            # Use same variable prefix as in SimWorker
            var_prefix = self.system_name.replace(' ', '_').replace('-', '_') + '_'
            
            # Update zerofill in parameters first
            par_obj = PAR(ENGINE._eng, var_prefix=var_prefix)
            par_obj.zerofill(self.zerofill)
            
            # Get the DATA object (should contain FID from previous simulation)
            data_obj = DATA(ENGINE._eng, var_prefix=var_prefix)
            
            # Apply window function
            if self.window_type != 'none':
                window_params = [(self.window_type, self.window_k)]
                self.log.emit(f"[{self.system_name}] Applying window: {self.window_type} (k={self.window_k})")
                data_obj.apodisation(window_params, use_gpu=self.use_gpu)
            else:
                self.log.emit(f"[{self.system_name}] No window function applied")
                data_obj.apodisation([('crisp', 1)], use_gpu=self.use_gpu)
            
            self.progress.emit(60)
            
            # Apply zerofill and get spectrum
            self.log.emit(f"[{self.system_name}] Applying zerofill: {self.zerofill}")
            spectrum = data_obj.spectrum(use_gpu=self.use_gpu)
            freq_axis = data_obj.freq(spectrum)
            
            self.progress.emit(100)
            self.log.emit(f"[{self.system_name}] Reprocessing completed!")
            
            self.done.emit(freq_axis, spectrum, self.system_name)
            
        except Exception as e:
            self.log.emit(f"[{self.system_name}] Reprocessing error: {str(e)}")
            self.failed.emit(f"[{self.system_name}] {str(e)}")


# ---------- Plot widget ----------
class PlotWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.fig = Figure(figsize=(8, 6), dpi=100)
        self.canvas = FigureCanvas(self.fig)
        self.toolbar = NavToolbar(self.canvas, self)
        
        # Data storage for re-plotting (store complex spectrum for display mode switching)
        self.current_x = None
        self.current_y = None  # Display y data (magnitude/re/im)
        self.current_spec = None  # Complex spectrum data
        self.xlabel_text = "Frequency (Hz)"
        self.ylabel_text = "|Spectrum|"
        self.title_text = ""
        self.invert_axis = True
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        
        # Coordinate display
        self.coord_label = QLabel("")
        self.coord_label.setStyleSheet("color: #546E7A; font-size: 10px;")
        layout.addWidget(self.coord_label)
        
        # Mouse events
        self.canvas.mpl_connect('motion_notify_event', self._on_mouse_move)
        self.canvas.mpl_connect('scroll_event', self._on_scroll)
    
    def draw(self, x: np.ndarray, y: np.ndarray, xlabel: str = "Frequency (Hz)", 
             invert: bool = True, title: str = "", ylabel: str = "|Spectrum|",
             x_range=None, y_range=None):
        """Draw spectrum and store data for later updates"""
        self.current_x = x
        self.current_y = y
        self.xlabel_text = xlabel
        self.ylabel_text = ylabel
        self.title_text = title
        self.invert_axis = invert
        
        # Filter out negative frequencies
        positive_mask = x >= 0
        x_positive = x[positive_mask]
        y_positive = y[positive_mask]
        
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.plot(x_positive, y_positive, linewidth=1.0, color='#607D8B')
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        
        if title:
            ax.set_title(title, fontsize=10, color='#546E7A')
        
        ax.grid(True, alpha=0.3, linestyle='--')
        
        # Apply custom ranges
        if x_range:
            x_min, x_max = x_range
            if x_min is not None and x_max is not None:
                # Ensure x_min is not negative
                x_min = max(0, x_min)
                ax.set_xlim(x_min, x_max)
        else:
            # Default: show only positive frequencies
            if len(x_positive) > 0:
                ax.set_xlim(0, x_positive.max())
        
        if y_range:
            y_min, y_max = y_range
            if y_min is not None and y_max is not None:
                ax.set_ylim(y_min, y_max)
        
        if invert:
            ax.invert_xaxis()
        
        self.fig.tight_layout()
        self.canvas.draw()

    def draw_multi(self, data_list, xlabel: str = "Frequency (Hz)", 
             invert: bool = True, title: str = "", ylabel: str = "|Spectrum|",
             x_range=None, y_range=None):
        """
        Draw multiple spectra overlay
        data_list: List of tuples (x, y, label, color)
        """
        self.current_x = None  # Invalidate single plot data
        
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        
        # Default colors
        default_colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
                         '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
        
        max_x = 0
        
        for i, (x, y, label, color) in enumerate(data_list):
            if color is None:
                color = default_colors[i % len(default_colors)]
            
            # Filter positive
            positive_mask = x >= 0
            x_pos = x[positive_mask]
            y_pos = y[positive_mask]
            
            if len(x_pos) > 0:
                max_x = max(max_x, x_pos.max())
                ax.plot(x_pos, y_pos, linewidth=1.0, color=color, label=label, alpha=0.8)

        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        
        if title:
            ax.set_title(title, fontsize=10, color='#546E7A')
            
        ax.legend()
        ax.grid(True, alpha=0.3, linestyle='--')
        
        # Ranges
        if x_range:
             x_min, x_max = x_range
             if x_min is not None and x_max is not None: 
                x_min = max(0, x_min)
                ax.set_xlim(x_min, x_max)
        else:
            if max_x > 0:
                ax.set_xlim(0, max_x)
                
        if invert:
            ax.invert_xaxis()
            
        self.fig.tight_layout()
        self.canvas.draw()
    
    def update_plot(self):
        """Re-draw using stored data"""
        if self.current_x is not None and self.current_y is not None:
            self.draw(self.current_x, self.current_y, self.xlabel_text, 
                     self.invert_axis, self.title_text, self.ylabel_text)
    
    def _on_mouse_move(self, event):
        if event.inaxes and event.xdata is not None:
            self.coord_label.setText(f'X: {event.xdata:.2f} Hz, Y: {event.ydata:.6f}')
        else:
            self.coord_label.setText("")
    
    def _on_scroll(self, event):
        if event.inaxes is None or event.xdata is None:
            return
        scale = 1.2 if event.button == "up" else (1/1.2)
        ax = event.inaxes
        xl, xr = ax.get_xlim()
        yl, yr = ax.get_ylim()
        xcenter, ycenter = event.xdata, event.ydata
        
        ax.set_xlim(xcenter + (xl - xcenter) * scale, xcenter + (xr - xcenter) * scale)
        ax.set_ylim(ycenter + (yl - ycenter) * scale, ycenter + (yr - ycenter) * scale)
        self.canvas.draw_idle()
        ax.set_xlim(xcenter + (xl - xcenter) * scale, xcenter + (xr - xcenter) * scale)
        ax.set_ylim(ycenter + (yl - ycenter) * scale, ycenter + (yr - ycenter) * scale)
        self.canvas.draw_idle()


# ---------- Detailed Log Window ----------
class DetailedLogWindow(QWidget):
    """Separate window to display detailed MATLAB/terminal output"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Detailed Logs")
        self.resize(900, 600)
        
        layout = QVBoxLayout(self)
        
        # Toolbar with controls
        toolbar = QHBoxLayout()
        
        self.auto_scroll_check = QCheckBox("Auto-scroll")
        self.auto_scroll_check.setChecked(True)
        toolbar.addWidget(self.auto_scroll_check)
        
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_logs)
        clear_btn.setMaximumWidth(80)
        toolbar.addWidget(clear_btn)
        
        toolbar.addStretch()
        
        layout.addLayout(toolbar)
        
        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QTextEdit.NoWrap)
        self.log_text.setStyleSheet("""
            QTextEdit {
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 9pt;
                background-color: #1E1E1E;
                color: #D4D4D4;
                border: 1px solid #3E3E3E;
            }
        """)
        layout.addWidget(self.log_text)
        
    def append_log(self, message):
        """Append a log message"""
        self.log_text.append(message)
        if self.auto_scroll_check.isChecked():
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
    
    def clear_logs(self):
        """Clear all logs"""
        self.log_text.clear()


# ---------- J-Coupling Popup Editor Window ----------
class JCouplingEditorDialog(QDialog):
    """Large popup window for easier J-coupling upper triangle input"""
    def __init__(self, parent, sys_name, isotopes, current_values, parent_window):
        super().__init__(parent)
        self.sys_name = sys_name
        self.isotopes = isotopes
        self.current_values = current_values  # Dict {(i, j): value_str}
        self.parent_window = parent_window
        self.grid_inputs = {}  # Store input widgets
        
        self.setWindowTitle(f"J-Coupling Editor - {sys_name}")
        
        # Calculate optimal window size based on number of spins
        n_spins = len(isotopes)
        if n_spins <= 4:
            width, height = 900, 650
        elif n_spins <= 6:
            width, height = 1000, 700
        else:
            width, height = 1100, 750
        
        self.resize(width, height)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # Header with better styling
        header = QLabel(f"<h2 style='margin: 0; color: #1976D2;'>J-Coupling Matrix Editor - {sys_name}</h2>")
        header.setStyleSheet("padding: 8px; background: #E3F2FD; border-radius: 6px;")
        layout.addWidget(header)
        
        # Info panel
        info_label = QLabel(
            f"<b>Editing upper triangle</b> for <b>{len(isotopes)} spins</b>: "
            f"<span style='color: #1976D2;'>{', '.join(isotopes)}</span><br>"
            f"<span style='color: #666; font-size: 9pt;'>Tip: Use Tab/Shift+Tab to navigate between fields</span>"
        )
        info_label.setStyleSheet(
            "color: #546E7A; padding: 8px 12px; "
            "background: #F5F5F5; border-left: 4px solid #4CAF50; "
            "border-radius: 4px;"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Scroll area for grid with both scrollbars
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet("""
            QScrollArea {
                border: 2px solid #CFD8DC;
                background: white;
                border-radius: 4px;
            }
            QScrollBar:vertical {
                border: none;
                background: #F5F5F5;
                width: 12px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #B0BEC5;
                min-height: 20px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical:hover {
                background: #90A4AE;
            }
            QScrollBar:horizontal {
                border: none;
                background: #F5F5F5;
                height: 12px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background: #B0BEC5;
                min-width: 20px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #90A4AE;
            }
        """)
        
        # Grid container
        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(6)
        grid_layout.setContentsMargins(15, 15, 15, 15)
        
        n = len(isotopes)
        
        # Calculate cell size based on number of spins
        if n <= 4:
            cell_width, cell_height = 100, 45
            label_width, label_height = 85, 35  # Reduced height for single line
            font_size = 11
        elif n <= 6:
            cell_width, cell_height = 90, 42
            label_width, label_height = 75, 32  # Reduced height for single line
            font_size = 10
        else:
            cell_width, cell_height = 80, 40
            label_width, label_height = 70, 30  # Reduced height for single line
            font_size = 9
        
        # Header row (column labels)
        for j in range(n):
            header_label = QLabel(f"<b>{isotopes[j]}({j+1})</b>")
            header_label.setAlignment(Qt.AlignCenter)
            header_label.setStyleSheet(
                f"color: #1976D2; font-size: {font_size}pt; "
                f"padding: 5px; background: #E3F2FD; "
                f"border: 1px solid #90CAF9; border-radius: 4px;"
            )
            header_label.setMinimumWidth(cell_width)
            header_label.setFixedHeight(label_height)
            grid_layout.addWidget(header_label, 0, j + 1)
        
        # Data rows
        for i in range(n):
            # Row label
            row_label = QLabel(f"<b>{isotopes[i]}({i+1})</b>")
            row_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            row_label.setStyleSheet(
                f"color: #1976D2; font-size: {font_size}pt; "
                f"padding: 5px; background: #E3F2FD; "
                f"border: 1px solid #90CAF9; border-radius: 4px;"
            )
            row_label.setMinimumWidth(label_width)
            row_label.setFixedHeight(cell_height)
            grid_layout.addWidget(row_label, i + 1, 0)
            
            for j in range(n):
                if j > i:  # Upper triangle
                    input_box = QLineEdit()
                    current_val = current_values.get((i, j), "0")
                    input_box.setText(current_val)
                    input_box.setAlignment(Qt.AlignCenter)
                    input_box.setMinimumWidth(cell_width)
                    input_box.setFixedHeight(cell_height)
                    input_box.setStyleSheet(f"""
                        QLineEdit {{
                            font-size: {font_size}pt;
                            font-weight: bold;
                            padding: 5px;
                            border: 2px solid #CFD8DC;
                            border-radius: 4px;
                            background: white;
                        }}
                        QLineEdit:focus {{
                            border: 2px solid #1976D2;
                            background: #E8EAF6;
                        }}
                        QLineEdit:hover {{
                            border: 2px solid #90CAF9;
                            background: #F5F5F5;
                        }}
                    """)
                    input_box.setToolTip(f"J-coupling between spin {i+1} ({isotopes[i]}) and spin {j+1} ({isotopes[j]})")
                    
                    grid_layout.addWidget(input_box, i + 1, j + 1)
                    self.grid_inputs[(i, j)] = input_box
                    
                elif i == j:  # Diagonal
                    dash_label = QLabel("—")
                    dash_label.setAlignment(Qt.AlignCenter)
                    dash_label.setMinimumWidth(cell_width)
                    dash_label.setFixedHeight(cell_height)
                    dash_label.setStyleSheet(
                        "color: #BDBDBD; font-size: 18pt; "
                        "background: #FAFAFA; "
                        "border: 1px solid #E0E0E0; border-radius: 4px;"
                    )
                    grid_layout.addWidget(dash_label, i + 1, j + 1)
                # Lower triangle: leave empty (shows as gray background)
                else:
                    empty_label = QLabel("")
                    empty_label.setMinimumWidth(cell_width)
                    empty_label.setFixedHeight(cell_height)
                    empty_label.setStyleSheet(
                        "background: #F0F0F0; "
                        "border: 1px solid #E0E0E0; border-radius: 4px;"
                    )
                    grid_layout.addWidget(empty_label, i + 1, j + 1)
        
        scroll.setWidget(grid_widget)
        layout.addWidget(scroll)
        
        # Bottom buttons with better styling
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        # Helper text
        helper_text = QLabel(
            "<span style='color: #666; font-size: 9pt;'>"
            "Values are in Hz. Changes apply when you click 'Apply'."
            "</span>"
        )
        btn_layout.addWidget(helper_text)
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumSize(100, 36)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #757575;
                color: white;
                font-size: 11pt;
                font-weight: bold;
                padding: 8px 20px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #616161;
            }
            QPushButton:pressed {
                background-color: #424242;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        apply_btn = QPushButton("Apply")
        apply_btn.setMinimumSize(100, 36)
        apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 11pt;
                font-weight: bold;
                padding: 8px 20px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        apply_btn.clicked.connect(self.apply_changes)
        apply_btn.setDefault(True)  # Make it the default button (Enter key)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(apply_btn)
        
        layout.addLayout(btn_layout)
        
        # Set dialog to be modal
        self.setModal(True)
    
    def apply_changes(self):
        """Apply changes back to the main grid"""
        try:
            # Update parent window's grid
            tab_widget = self.parent_window.systems[self.sys_name]['tab_widget']
            
            for (i, j), input_box in self.grid_inputs.items():
                value = input_box.text().strip()
                if (i, j) in tab_widget.j_grid_inputs:
                    tab_widget.j_grid_inputs[(i, j)].setText(value)
            
            # Sync to text mode
            self.parent_window.sync_grid_to_text(self.sys_name)
            
            self.parent_window.log(f"[{self.sys_name}] J-coupling values updated from popup editor")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to apply changes:\n{str(e)}")


# ---------- Main window ----------
class MultiSystemSpinachUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(config.app_name)
        self.resize(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)
        
        # Set application icon
        app_icon = icon_manager.get_app_icon()
        if not app_icon.isNull():
            self.setWindowIcon(app_icon)
        
        # Multi-system data storage (dynamic)
        self.systems = {}  # Dictionary: {system_name: {'freq': array, 'spec': array, 'worker': worker, 'weight': float}}
        self.system_counter = 0  # Counter for auto-naming new systems
        self.max_systems = MAX_SYSTEMS  # Maximum number of systems allowed
        
        # Initialize detailed log window (hidden by default, no parent to avoid embedding)
        self.detailed_log_window = DetailedLogWindow()
        
        # Create default two systems
        self._add_default_systems()
        
        self.setup_menu()
        self.setup_ui()
    
    def _add_default_systems(self):
        """Initialize with two default systems"""
        self.systems['System 1'] = {
            'freq': None,
            'spec': None,
            'spec_raw': None,  # Store unbroadened spectrum
            'worker': None,
            'weight': 0.5,
            'tab_widget': None,
            'plot_widget': None,
            'broadening_fwhm': 0.0,  # Gaussian broadening FWHM in Hz
            'broadening_enabled': False,
            'pending_update': False  # Flag for pending auto-rerun
        }
        self.systems['System 2'] = {
            'freq': None,
            'spec': None,
            'spec_raw': None,  # Store unbroadened spectrum
            'worker': None,
            'weight': 0.5,
            'tab_widget': None,
            'plot_widget': None,
            'broadening_fwhm': 0.0,  # Gaussian broadening FWHM in Hz
            'broadening_enabled': False,
            'pending_update': False  # Flag for pending auto-rerun
        }
        self.system_counter = 2
    
    def setup_menu(self):
        """Setup menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        # Save/Load Parameters
        save_param_action = QAction("Save Parameters", self)
        save_param_action.triggered.connect(self.save_parameters)
        file_menu.addAction(save_param_action)
        
        load_param_action = QAction("Load Parameters", self)
        load_param_action.triggered.connect(self.load_parameters)
        file_menu.addAction(load_param_action)
        
        file_menu.addSeparator()
        
        # Export/Load Spectrum
        export_spec_action = QAction("Export Spectrum", self)
        export_spec_action.triggered.connect(self.export_spectrum)
        file_menu.addAction(export_spec_action)
        
        load_spec_action = QAction("Load Spectrum", self)
        load_spec_action.triggered.connect(self.load_spectrum)
        file_menu.addAction(load_spec_action)
        
        file_menu.addSeparator()
        
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        reset_plot_action = QAction("Reset Plot View", self)
        reset_plot_action.triggered.connect(self.reset_all_plots)
        view_menu.addAction(reset_plot_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(lambda: QMessageBox.information(
            self, f"About {config.app_name}", 
            f"{config.app_name}\n"
            f"{config.app_full_version}\n\n"
            f"{config.get('APP_DESCRIPTION', 'Advanced ZULF-NMR simulation tool')}\n\n"
            "Features:\n"
            "• Multi-system parallel simulation and analysis\n"
            "• Zero to ultralow field (ZULF) NMR support\n"
            "• Symmetry optimization for large spin systems\n"
            "• Real-time parameter adjustment and visualization\n"
            "• Gaussian line broadening with per-system control\n"
            "• Advanced plotting with system weighting\n\n"
            "Powered by MATLAB Spinach Framework\n"
            "For documentation and support, see README.md"
        ))
        help_menu.addAction(about_action)
        
    def setup_ui(self):
        # Central widget with horizontal splitter (left: controls, right: plots)
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        
        # Main horizontal splitter
        main_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(main_splitter)
        
        # LEFT PANEL: Top-level tabs (System / Parameters / Plot Settings)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)
        
        # Create top-level tab widget
        self.main_tabs = QTabWidget()
        self.main_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 2px solid #607D8B;
                border-radius: 6px;
                background: #FAFAFA;
            }
            QTabBar::tab {
                background: #CFD8DC;
                color: #37474F;
                padding: 8px 20px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: #607D8B;
                color: white;
            }
            QTabBar::tab:hover:!selected {
                background: #B0BEC5;
            }
        """)
        
        # ========== TAB 1: System ==========
        system_tab = QWidget()
        system_layout = QVBoxLayout(system_tab)
        system_layout.setContentsMargins(5, 5, 5, 5)
        
        # System management buttons
        system_mgmt_layout = QHBoxLayout()
        self.btn_add_system = QPushButton("+ Add System")
        self.btn_remove_system = QPushButton("- Remove System")
        self.btn_add_system.setStyleSheet("""
            QPushButton {
                background: #4CAF50;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #45A049;
            }
        """)
        self.btn_remove_system.setStyleSheet("""
            QPushButton {
                background: #F44336;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #DA190B;
            }
        """)
        self.btn_add_system.clicked.connect(self.add_new_system)
        self.btn_remove_system.clicked.connect(self.remove_current_system)
        
        system_mgmt_layout.addWidget(self.btn_add_system)
        system_mgmt_layout.addWidget(self.btn_remove_system)
        system_mgmt_layout.addStretch()
        system_layout.addLayout(system_mgmt_layout)
        
        # System tabs (dynamic)
        self.system_tabs = QTabWidget()
        self.system_tabs.setStyleSheet("""
            QTabBar::tab {
                background: #F5F5F5;
                color: #546E7A;
                padding: 6px 16px;
                font-weight: normal;
                border: 1px solid #E0E0E0;
                border-bottom: none;
            }
            QTabBar::tab:selected {
                background: #E8EAF6;
                color: #3F51B5;
                font-weight: bold;
            }
            QTabBar::tab:hover {
                background: #ECEFF1;
            }
        """)
        
        # Create tabs for initial systems
        for sys_name in ['System 1', 'System 2']:
            self._create_system_tab(sys_name)
        
        system_layout.addWidget(self.system_tabs)
        
        # ========== TAB 2: Parameters ==========
        param_scroll = QScrollArea()
        param_scroll.setWidgetResizable(True)
        param_scroll.setFrameShape(QScrollArea.NoFrame)
        
        parameters_tab = QWidget()
        param_scroll.setWidget(parameters_tab)
        
        parameters_layout = QVBoxLayout(parameters_tab)
        parameters_layout.setContentsMargins(10, 10, 10, 10)
        parameters_layout.setSpacing(10)
        
        # Note about parameters being system-specific
        param_note = QLabel("Note: Parameters below apply to both systems. System-specific acquisition parameters are in their respective System tabs.")
        param_note.setStyleSheet("color: #546E7A; font-style: italic; padding: 8px; background: #E8F5E9; border-radius: 4px; border-left: 3px solid #4CAF50;")
        param_note.setWordWrap(True)
        parameters_layout.addWidget(param_note)
        
        # Window Function group
        window_group = QGroupBox("Apodization Window")
        window_layout = QFormLayout(window_group)
        window_layout.setSpacing(8)
        
        # Window type selector
        self.window_choices = {
            "none (no window; first point /2)": "none",
            "crisp (cos^8 half-bell)": "crisp",
            "exp (exp(-k*x))": "exp",
            "gauss (exp(-k*(x^2)))": "gauss",
            "cos (half-bell)": "cos",
            "sin (full-bell)": "sin",
            "sqcos (cos^2 half-bell)": "sqcos",
            "sqsine (sin^2 full-bell)": "sqsine",
            "kaiser (k controls side-lobe)": "kaiser",
        }
        
        self.window_type_combo = QComboBox()
        self.window_type_combo.addItems(list(self.window_choices.keys()))
        self.window_type_combo.setCurrentIndex(0)  # Default to "none"
        self.window_type_combo.currentIndexChanged.connect(self.on_window_type_changed)
        
        # Window k parameter (for exp, gauss, kaiser)
        self.window_k_spin = QDoubleSpinBox()
        self.window_k_spin.setRange(0.0, 1000.0)
        self.window_k_spin.setDecimals(3)
        self.window_k_spin.setValue(5.0)
        self.window_k_spin.setEnabled(False)
        
        window_layout.addRow("Window Type:", self.window_type_combo)
        window_layout.addRow("k parameter:", self.window_k_spin)
        
        # Enhanced help text with linewidth effects
        window_help = QLabel(
            "<b>Effect on linewidth:</b><br>"
            "• <b>none/crisp</b>: Narrowest lines, may have artifacts<br>"
            "• <b>exp</b>: Increases linewidth (↑k = broader lines, less noise)<br>"
            "• <b>gauss</b>: Can narrow then broaden lines depending on k<br>"
            "• <b>cos/sin/kaiser</b>: Moderate broadening, smoother baseline<br>"
            "⚠️ Window functions trade resolution for sensitivity"
        )
        window_help.setStyleSheet("color: #555; font-size: 9px; background: #FFF9E6; padding: 6px; border-radius: 3px;")
        window_help.setWordWrap(True)
        window_layout.addRow(window_help)
        
        parameters_layout.addWidget(window_group)
        
        # Acquisition Parameters group
        acq_group = QGroupBox("Acquisition Parameters")
        acq_layout = QFormLayout(acq_group)
        acq_layout.setSpacing(6)
        
        self.sweep_spin = QDoubleSpinBox()
        self.sweep_spin.setRange(10, 10000)
        self.sweep_spin.setValue(600.0)
        self.sweep_spin.setToolTip("Spectral width in Hz")
        
        # Create container for sweep with unit label
        sweep_container = QWidget()
        sweep_layout = QHBoxLayout(sweep_container)
        sweep_layout.setContentsMargins(0, 0, 0, 0)
        sweep_layout.setSpacing(5)
        sweep_layout.addWidget(self.sweep_spin)
        sweep_unit_label = QLabel("Hz")
        sweep_unit_label.setStyleSheet("font-size: 10pt; color: #546E7A;")
        sweep_layout.addWidget(sweep_unit_label)
        sweep_layout.addStretch()
        
        self.npoints_spin = QDoubleSpinBox()
        self.npoints_spin.setRange(256, 100000)
        self.npoints_spin.setDecimals(0)
        self.npoints_spin.setValue(5000)
        self.npoints_spin.setToolTip("Number of data points in acquisition")
        
        self.zerofill_spin = QDoubleSpinBox()
        self.zerofill_spin.setRange(256, 100000)
        self.zerofill_spin.setDecimals(0)
        self.zerofill_spin.setValue(10000)
        self.zerofill_spin.setToolTip("Zero-fill size for FFT")
        
        # Magnet with unit selection
        self.magnet_container = QWidget()
        magnet_layout = QHBoxLayout(self.magnet_container)
        magnet_layout.setContentsMargins(0, 0, 0, 0)
        magnet_layout.setSpacing(5)

        self.magnet_spin = QDoubleSpinBox()
        self.magnet_spin.setRange(0, 1e12)  # Large range for pT/nT
        self.magnet_spin.setValue(0)
        self.magnet_spin.setDecimals(4)  # 4 decimals for high precision in chosen unit
        self.magnet_spin.setSingleStep(0.1)
        self.magnet_spin.setToolTip("Magnetic field strength")
        
        self.magnet_unit_combo = QComboBox()
        self.magnet_units = {
            "T": 1.0, "mT": 1e-3, "µT": 1e-6, "nT": 1e-9, "pT": 1e-12
        }
        self.magnet_unit_combo.addItems(list(self.magnet_units.keys()))
        self.magnet_unit_combo.setCurrentText("T")
        # Store last unit for conversion logic
        self.last_magnet_unit = "T"
        
        # Connect unit change for conversion
        self.magnet_unit_combo.currentTextChanged.connect(self._on_magnet_unit_changed)
        
        magnet_layout.addWidget(self.magnet_spin, 2)
        magnet_layout.addWidget(self.magnet_unit_combo, 1)
        
        self.gpu_check = QCheckBox("Use GPU (if available)")
        self.gpu_check.setChecked(False)
        self.gpu_check.setToolTip("Enable GPU acceleration for simulation")
        
        acq_layout.addRow("Sweep:", sweep_container)
        acq_layout.addRow("N Points:", self.npoints_spin)
        acq_layout.addRow("Zero Fill:", self.zerofill_spin)
        acq_layout.addRow("Magnet:", self.magnet_container)
        acq_layout.addRow(self.gpu_check)
        
        parameters_layout.addWidget(acq_group)
        
        # Parameter Management group
        param_btn_group = QGroupBox("Parameter Management")
        param_btn_layout = QVBoxLayout(param_btn_group)
        
        save_load_layout = QHBoxLayout()
        btn_save_all = QPushButton("Save All Parameters")
        btn_save_all.clicked.connect(self.save_parameters)
        btn_load_all = QPushButton("Load Parameters")
        btn_load_all.clicked.connect(self.load_parameters)
        save_load_layout.addWidget(btn_save_all)
        save_load_layout.addWidget(btn_load_all)
        param_btn_layout.addLayout(save_load_layout)
        
        parameters_layout.addWidget(param_btn_group)
        parameters_layout.addStretch()
        
        # ========== TAB 3: Plot Settings ==========
        plot_settings_tab = QScrollArea()
        plot_settings_tab.setWidgetResizable(True)
        plot_settings_tab.setFrameShape(QScrollArea.NoFrame)
        
        # Create content widget
        plot_settings_content = QWidget()
        plot_settings_layout = QVBoxLayout(plot_settings_content)
        plot_settings_layout.setContentsMargins(10, 10, 10, 10)
        plot_settings_layout.setSpacing(12)
        
        # Create display mode combo (will be used in toolbar and here)
        self.display_mode_combo = QComboBox()
        self.display_mode_combo.addItems(["|spec| (magnitude)", "Re(spec)", "Im(spec)"])
        self.display_mode_combo.setCurrentIndex(0)
        self.display_mode_combo.setToolTip("Choose how to display the spectrum")
        self.display_mode_combo.currentIndexChanged.connect(self.on_display_mode_changed)
        
        # Display mode section
        display_group = QGroupBox("Spectrum Display")
        display_group_layout = QFormLayout(display_group)
        display_group_layout.addRow("Display Mode:", self.display_mode_combo)
        
        display_help = QLabel("• |spec|: Magnitude\n• Re(spec): Real part\n• Im(spec): Imaginary part")
        display_help.setStyleSheet("color: #666; font-size: 9px; font-style: italic; padding: 5px;")
        display_group_layout.addRow(display_help)
        
        plot_settings_layout.addWidget(display_group)
        
        # Weight control section (Multi-system support)
        weight_group = QGroupBox("System Weights")
        weight_group_layout = QVBoxLayout(weight_group)
        weight_group_layout.setSpacing(6)
        
        # Container for weight controls (will be dynamically populated)
        self.weight_controls_container = QWidget()
        self.weight_controls_layout = QVBoxLayout(self.weight_controls_container)
        self.weight_controls_layout.setContentsMargins(0, 0, 0, 0)
        self.weight_controls_layout.setSpacing(4)
        
        # Dictionary to store weight spinboxes
        self.weight_spinboxes = {}
        
        # Auto-normalize checkbox
        self.auto_normalize_checkbox = QCheckBox("Auto-normalize weights")
        self.auto_normalize_checkbox.setChecked(False)
        self.auto_normalize_checkbox.stateChanged.connect(self.on_auto_normalize_changed)
        
        weight_group_layout.addWidget(self.weight_controls_container)
        weight_group_layout.addWidget(self.auto_normalize_checkbox)
        
        # Initialize weight controls for existing systems
        self._update_weight_controls()
        
        plot_settings_layout.addWidget(weight_group)
        
        # Line Broadening control section (Multi-system support, similar to weights)
        broadening_group = QGroupBox("Gaussian Line Broadening")
        broadening_group_layout = QVBoxLayout(broadening_group)
        broadening_group_layout.setSpacing(6)
        
        # Container for broadening controls (will be dynamically populated)
        self.broadening_controls_container = QWidget()
        self.broadening_controls_layout = QVBoxLayout(self.broadening_controls_container)
        self.broadening_controls_layout.setContentsMargins(0, 0, 0, 0)
        self.broadening_controls_layout.setSpacing(4)
        
        # Dictionary to store broadening controls
        self.broadening_controls = {}  # {sys_name: (enable_check, slider, spinbox, label)}
        
        # Help text
        broadening_help = QLabel(
            "<b>Post-processing Gaussian broadening</b> (does not require re-simulation)<br>"
            "• Smooths spectral lines in real-time<br>"
            "• FWHM: Full Width at Half Maximum in Hz"
        )
        broadening_help.setStyleSheet(
            "color: #555; font-size: 9px; background: #E3F2FD; "
            "padding: 6px; border-radius: 3px; border-left: 3px solid #2196F3;"
        )
        broadening_help.setWordWrap(True)
        
        broadening_group_layout.addWidget(self.broadening_controls_container)
        broadening_group_layout.addWidget(broadening_help)
        
        # Initialize broadening controls for existing systems
        self._update_broadening_controls()
        
        plot_settings_layout.addWidget(broadening_group)
        
        
        # Plot range section
        range_group = QGroupBox("Axis Range")
        range_group.setCheckable(True)
        range_group.setChecked(False)
        range_group.setStyleSheet("""
            QGroupBox {
                margin-top: 8px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                margin-top: 0px;
            }
        """)
        range_layout = QFormLayout(range_group)
        range_layout.setSpacing(6)
        range_layout.setContentsMargins(10, 15, 10, 10)
        
        self.x_min_edit = QLineEdit()
        self.x_min_edit.setPlaceholderText("Auto")
        self.x_max_edit = QLineEdit()
        self.x_max_edit.setPlaceholderText("Auto")
        self.y_min_edit = QLineEdit()
        self.y_min_edit.setPlaceholderText("Auto")
        self.y_max_edit = QLineEdit()
        self.y_max_edit.setPlaceholderText("Auto")
        
        range_layout.addRow("X min (Hz):", self.x_min_edit)
        range_layout.addRow("X max (Hz):", self.x_max_edit)
        range_layout.addRow("Y min:", self.y_min_edit)
        range_layout.addRow("Y max:", self.y_max_edit)
        
        # Range buttons
        range_btn_layout = QHBoxLayout()
        self.btn_reset_range = QPushButton("Reset")
        self.btn_reset_range.setToolTip("Reset all ranges to auto")
        self.btn_reset_range.clicked.connect(self.reset_plot_ranges)
        self.btn_auto_y = QPushButton("Auto Y from X")
        self.btn_auto_y.setToolTip("Automatically calculate Y range based on X range")
        self.btn_auto_y.clicked.connect(self.auto_y_from_x)
        
        range_btn_layout.addWidget(self.btn_reset_range)
        range_btn_layout.addWidget(self.btn_auto_y)
        range_layout.addRow(range_btn_layout)
        
        self.range_group = range_group
        plot_settings_layout.addWidget(range_group)
        
        # Update plot button
        self.btn_update_plot_big = QPushButton("Update Current Plot")
        self.btn_update_plot_big.setToolTip("Refresh plot with new settings")
        self.btn_update_plot_big.clicked.connect(self.update_current_plot)
        self.btn_update_plot_big.setStyleSheet("""
            QPushButton {
                background-color: #5C6BC0;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #3F51B5; }
        """)
        plot_settings_layout.addWidget(self.btn_update_plot_big)
        plot_settings_layout.addStretch()
        
        # Set scroll area content
        plot_settings_tab.setWidget(plot_settings_content)
        
        # Add all tabs to main tab widget
        self.main_tabs.addTab(system_tab, "System")
        self.main_tabs.addTab(param_scroll, "Parameters")
        self.main_tabs.addTab(plot_settings_tab, "Plot Settings")
        
        left_layout.addWidget(self.main_tabs)
        
        # Action buttons (below tabs)
        btn_group = QGroupBox("Actions")
        btn_layout = QVBoxLayout(btn_group)
        btn_layout.setSpacing(6)
        
        # Action buttons (updated for multi-system)
        btn_group = QGroupBox("Actions")
        btn_layout = QVBoxLayout(btn_group)
        btn_layout.setSpacing(6)
        
        self.btn_run_current = QPushButton("Run Current System")
        self.btn_run_all = QPushButton("Run All Systems")
        self.btn_reprocess_current = QPushButton("Reprocess Current")
        self.btn_restart = QPushButton("Restart MATLAB Engine")
        
        # Set styles
        self.btn_run_current.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        
        self.btn_run_all.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45A049;
            }
        """)
        
        self.btn_reprocess_current.setStyleSheet("""
            QPushButton {
                background-color: #81C784;
                color: white;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #66BB6A;
            }
        """)
        
        # Set tooltips
        self.btn_run_current.setToolTip("Run simulation for the currently selected system")
        self.btn_run_all.setToolTip("Run simulations for all systems sequentially")
        self.btn_reprocess_current.setToolTip("Reapply window/zerofill without full simulation (fast)")
        
        # Connect signals
        self.btn_run_current.clicked.connect(self.run_current_system)
        self.btn_run_all.clicked.connect(self.run_all_systems)
        self.btn_reprocess_current.clicked.connect(self.reprocess_current_system)
        self.btn_restart.clicked.connect(self.restart_matlab)
        
        btn_layout.addWidget(self.btn_run_current)
        btn_layout.addWidget(self.btn_run_all)
        btn_layout.addWidget(self.btn_reprocess_current)
        btn_layout.addWidget(self.btn_restart)
        
        left_layout.addWidget(btn_group)
        
        main_splitter.addWidget(left_panel)
        
        # RIGHT PANEL: Plots and Logs
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(5, 5, 5, 5)
        
        # Toolbar for plot operations
        plot_toolbar = QWidget()
        plot_toolbar_layout = QHBoxLayout(plot_toolbar)
        plot_toolbar_layout.setContentsMargins(0, 0, 0, 5)
        plot_toolbar_layout.setSpacing(8)
        
        self.btn_update_plot = QPushButton("Update Current Plot")
        self.btn_update_plot.setToolTip("Refresh the current plot view without re-running simulation")
        self.btn_update_plot.clicked.connect(self.update_current_plot)
        
        # Add spectrum export/load buttons
        self.btn_export_spec = QPushButton("Export Spectrum")
        self.btn_export_spec.clicked.connect(self.export_spectrum)
        self.btn_export_spec.setToolTip("Export current spectrum data and settings")
        
        self.btn_load_spec = QPushButton("Load Spectrum")
        self.btn_load_spec.clicked.connect(self.load_spectrum)
        self.btn_load_spec.setToolTip("Load spectrum data from file")
        
        plot_toolbar_layout.addWidget(self.btn_update_plot)
        plot_toolbar_layout.addStretch()
        plot_toolbar_layout.addWidget(self.btn_export_spec)
        plot_toolbar_layout.addWidget(self.btn_load_spec)
        
        right_layout.addWidget(plot_toolbar)
        
        # Tabs for different plots (dynamically populated)
        self.plot_tabs = QTabWidget()
        
        # Create plot tabs for initial systems
        for sys_name in ['System 1', 'System 2']:
            plot_widget = PlotWidget()
            self.systems[sys_name]['plot_widget'] = plot_widget
            self.plot_tabs.addTab(plot_widget, sys_name)
        
        # Weighted sum tab (always last)
        self.sum_tab_widget = QWidget()
        sum_tab_layout = QVBoxLayout(self.sum_tab_widget)
        sum_tab_layout.setContentsMargins(0, 5, 0, 0)
        
        # Controls (Overlay toggle)
        sum_controls = QHBoxLayout()
        sum_controls.setContentsMargins(5, 0, 5, 0)
        self.overlay_check = QCheckBox("Overlay Spectra")
        self.overlay_check.setToolTip("Overlay individual system spectra instead of summation")
        self.overlay_check.toggled.connect(self.update_weighted_sum)
        sum_controls.addStretch()
        sum_controls.addWidget(self.overlay_check)
        sum_tab_layout.addLayout(sum_controls)
        
        self.plot_sum = PlotWidget()
        sum_tab_layout.addWidget(self.plot_sum)
        
        self.plot_tabs.addTab(self.sum_tab_widget, "Weighted Sum")
        
        right_layout.addWidget(self.plot_tabs, stretch=4)
        
        # Log area
        log_group = QGroupBox("Log Output")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(5, 10, 5, 5)
        
        # Add toolbar with detailed log button
        log_toolbar = QHBoxLayout()
        log_toolbar.addStretch()
        
        self.detailed_log_btn = QPushButton("Detailed Logs")
        self.detailed_log_btn.setMaximumWidth(130)
        self.detailed_log_btn.setToolTip("Show detailed MATLAB/terminal output")
        self.detailed_log_btn.clicked.connect(self.show_detailed_logs)
        log_toolbar.addWidget(self.detailed_log_btn)
        
        log_layout.addLayout(log_toolbar)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(120)
        # Enable horizontal scrollbar and disable word wrap
        self.log_text.setLineWrapMode(QTextEdit.NoWrap)
        self.log_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        log_layout.addWidget(self.log_text)
        
        right_layout.addWidget(log_group, stretch=1)
        
        main_splitter.addWidget(right_panel)
        
        # Set splitter proportions (left:right = 2:3)
        main_splitter.setStretchFactor(0, 2)
        main_splitter.setStretchFactor(1, 3)
        
        # Apply stylesheet
        self.setStyleSheet("""
            QPushButton {
                background-color: #607D8B;
                color: white;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: normal;
                border: none;
            }
            QPushButton:hover {
                background-color: #546E7A;
            }
            QPushButton#ParseButton {
                background-color: #5C6BC0;
            }
            QPushButton#ParseButton:hover {
                background-color: #3F51B5;
            }
            QPushButton#AddSymButton {
                background-color: #78909C;
            }
            QPushButton#AddSymButton:hover {
                background-color: #607D8B;
            }
            QPushButton#DeleteSymButton {
                background-color: #90A4AE;
                padding: 4px 8px;
            }
            QPushButton#DeleteSymButton:hover {
                background-color: #78909C;
            }
            QGroupBox {
                border: 1px solid #CFD8DC;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: normal;
                background-color: #FAFAFA;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #546E7A;
            }
            QTextEdit {
                border: 1px solid #CFD8DC;
                border-radius: 3px;
                padding: 4px;
                background-color: white;
            }
            QLineEdit {
                border: 1px solid #CFD8DC;
                border-radius: 3px;
                padding: 4px;
                background-color: white;
            }
            QSlider::groove:horizontal {
                border: 1px solid #B0BEC5;
                height: 6px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #CFD8DC, stop:1 #ECEFF1);
                margin: 2px 0;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #607D8B, stop:1 #546E7A);
                border: 1px solid #455A64;
                width: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
            QSlider::handle:horizontal:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #78909C, stop:1 #607D8B);
            }
        """)
    
    def _on_magnet_unit_changed(self, new_unit):
        """Handle magnet unit change with value conversion"""
        # Get conversion factors
        old_factor = self.magnet_units.get(self.last_magnet_unit, 1.0)
        new_factor = self.magnet_units.get(new_unit, 1.0)
        
        # Calculate current value in Tesla
        current_val_tesla = self.magnet_spin.value() * old_factor
        
        # Calculate new value in new unit
        new_val = current_val_tesla / new_factor
        
        # Update spinbox without triggering signls if needed (but valueChanged is fine usually)
        self.magnet_spin.blockSignals(True)
        self.magnet_spin.setValue(new_val)
        self.magnet_spin.blockSignals(False)
        
        # Update last unit
        self.last_magnet_unit = new_unit

    def get_magnet_tesla(self):
        """Get current magnet value in Tesla"""
        unit = self.magnet_unit_combo.currentText()
        factor = self.magnet_units.get(unit, 1.0)
        return self.magnet_spin.value() * factor

    def set_magnet_tesla(self, value_tesla):
        """Set magnet value in Tesla (auto-selects best unit)"""
        if value_tesla == 0:
            unit = "T"
            val = 0
        elif abs(value_tesla) < 1e-7: # < 0.1 uT -> use nT or pT
            if abs(value_tesla) < 1e-10: # < 0.1 nT -> use pT
                unit = "pT"
            else:
                unit = "nT"
        elif abs(value_tesla) < 1e-4: # < 0.1 mT -> use uT
             unit = "µT"
        elif abs(value_tesla) < 0.1: # < 0.1 T -> use mT
            unit = "mT"
        else:
            unit = "T"
            
        # Update combo and spinbox
        self.magnet_unit_combo.blockSignals(True)
        self.magnet_unit_combo.setCurrentText(unit)
        self.last_magnet_unit = unit
        self.magnet_unit_combo.blockSignals(False)
        
        factor = self.magnet_units.get(unit, 1.0)
        self.magnet_spin.setValue(value_tesla / factor)

    def _create_system_tab(self, sys_name):
        """Create a system tab with controls"""
        if sys_name == 'System 1':
            default_isotopes = "1H, 1H, 1H, 15N"
            default_j_matrix = "[[0, 0, c1, a1],\n [0, 0, c1, a1],\n [0, 0, 0, b1],\n [0, 0, 0, 0]]"
        elif sys_name == 'System 2':
            default_isotopes = "1H, 1H, 1H, 1H, 13C"
            default_j_matrix = "[[0, 0, 0, c2, a2],\n [0, 0, 0, c2, a2],\n [0, 0, 0, c2, a2],\n [0, 0, 0, 0, b2],\n [0, 0, 0, 0, 0]]"
        else:
            # Default for new systems
            default_isotopes = "1H, 1H, 13C"
            default_j_matrix = "[[0, 7.5, 125],\n [0, 0, 7.5],\n [0, 0, 0]]"
        
        sys_widget = self.create_system_controls(
            sys_name,
            default_isotopes=default_isotopes,
            default_j_matrix=default_j_matrix,
            default_sym=""
        )
        
        # Store reference
        self.systems[sys_name]['tab_widget'] = sys_widget
        
        # Add to tabs
        self.system_tabs.addTab(sys_widget, sys_name)
        
        # Connect signals (we'll update parse_system to handle system names)
        sys_widget.parse_btn.clicked.connect(lambda: self.parse_system(sys_name))
        sys_widget.save_mol_btn.clicked.connect(lambda: self.save_molecule(sys_name))
        sys_widget.load_mol_btn.clicked.connect(lambda: self.load_molecule(sys_name))
        sys_widget.j_input_mode_combo.currentIndexChanged.connect(lambda idx: self.on_j_input_mode_changed(sys_name, idx))
        sys_widget.gen_grid_btn.clicked.connect(lambda: self.generate_j_grid(sys_name))
        sys_widget.popup_editor_btn.clicked.connect(lambda: self.open_j_popup_editor(sys_name))
    
    def add_new_system(self):
        """Add a new system tab"""
        if len(self.systems) >= self.max_systems:
            QMessageBox.warning(self, "Limit Reached", 
                              f"Maximum {self.max_systems} systems allowed.")
            return
        
        # Generate new system name
        self.system_counter += 1
        new_name = f"System {self.system_counter}"
        
        # Calculate default weight (equal distribution)
        default_weight = 1.0 / (len(self.systems) + 1)
        
        # Add to data structure
        self.systems[new_name] = {
            'freq': None,
            'spec': None,
            'spec_raw': None,
            'worker': None,
            'weight': default_weight,
            'tab_widget': None,
            'plot_widget': None,
            'broadening_fwhm': 0.0,
            'broadening_enabled': False,
            'pending_update': False
        }
        
        # Create UI elements
        self._create_system_tab(new_name)
        self._create_plot_tab(new_name)
        
        # Update weight controls to show new system
        self._update_weight_controls()
        
        # Update broadening controls to show new system
        self._update_broadening_controls()
        
        # Switch to new tab
        self.system_tabs.setCurrentIndex(self.system_tabs.count() - 1)
        
        self.log(f"Added {new_name}")
    
    def remove_current_system(self):
        """Remove the currently selected system"""
        if len(self.systems) <= 1:
            QMessageBox.warning(self, "Cannot Remove", 
                              "At least one system must remain.")
            return
        
        current_idx = self.system_tabs.currentIndex()
        sys_name = self.system_tabs.tabText(current_idx)
        
        # Confirm deletion
        reply = QMessageBox.question(self, "Confirm Deletion",
                                    f"Remove {sys_name}?\n\nThis will delete all associated data.",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.No:
            return
        
        # Clean up MATLAB variables
        if ENGINE.running:
            try:
                var_prefix = sys_name.replace(' ', '_').replace('-', '_') + '_'
                ENGINE._eng.eval(f"clear {var_prefix}*", nargout=0)
                self.log(f"Cleared MATLAB variables for {sys_name}")
            except:
                pass
        
        # Remove from UI
        self.system_tabs.removeTab(current_idx)
        
        # Find and remove plot tab
        for i in range(self.plot_tabs.count()):
            if self.plot_tabs.tabText(i) == sys_name:
                self.plot_tabs.removeTab(i)
                break
        
        # Remove from data structure
        del self.systems[sys_name]
        
        # Update weight controls to reflect removal
        self._update_weight_controls()
        
        # Update broadening controls to reflect removal
        self._update_broadening_controls()
        
        self.log(f"Removed {sys_name}")
        self.update_weighted_sum()
    
    def _create_plot_tab(self, sys_name):
        """Create a plot tab for a system"""
        plot_widget = PlotWidget()
        self.systems[sys_name]['plot_widget'] = plot_widget
        
        # Insert before "Weighted Sum" tab (last tab)
        insert_idx = self.plot_tabs.count() - 1
        self.plot_tabs.insertTab(insert_idx, plot_widget, sys_name)
    
    def create_system_controls(self, title, default_isotopes, default_j_matrix, default_sym):
        """Create control panel for one system with customizable inputs"""
        # Create a scroll area wrapper
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # Disable horizontal scroll
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)  # Enable vertical scroll when needed
        
        # Content widget
        content = QWidget()
        layout = QFormLayout(content)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Isotopes input
        iso_edit = QTextEdit()
        iso_edit.setPlainText(default_isotopes)
        iso_edit.setMinimumHeight(50)
        iso_edit.setMaximumHeight(70)
        iso_edit.setPlaceholderText("e.g., 1H, 1H, 1H, 15N")
        layout.addRow("Isotopes:", iso_edit)
        
        # Molecule Save/Load buttons
        mol_btn_layout = QHBoxLayout()
        save_mol_btn = QPushButton("Save Molecule")
        load_mol_btn = QPushButton("Load Molecule")
        save_mol_btn.setMaximumWidth(120)
        load_mol_btn.setMaximumWidth(120)
        save_mol_btn.setToolTip("Save current isotopes, J-matrix and symmetry as a molecule preset")
        load_mol_btn.setToolTip("Load a saved molecule preset")
        mol_btn_layout.addWidget(save_mol_btn)
        mol_btn_layout.addWidget(load_mol_btn)
        mol_btn_layout.addStretch()
        layout.addRow(mol_btn_layout)
        
        # J matrix input with parse button
        j_container = QWidget()
        j_layout = QVBoxLayout(j_container)
        j_layout.setContentsMargins(0, 0, 0, 0)
        j_layout.setSpacing(8)
        
        # Mode selector
        mode_container = QWidget()
        mode_layout = QHBoxLayout(mode_container)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.setSpacing(8)
        
        mode_label = QLabel("Input Mode:")
        mode_label.setStyleSheet("font-weight: normal; color: #546E7A;")
        j_input_mode_combo = QComboBox()
        j_input_mode_combo.addItems(["Matrix Text", "Upper Triangle Grid"])
        j_input_mode_combo.setMaximumWidth(160)
        j_input_mode_combo.setToolTip("Choose J-coupling input method")
        
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(j_input_mode_combo)
        mode_layout.addStretch()
        
        j_layout.addWidget(mode_container)
        
        # Stacked widget to hold both input modes
        j_stack = QStackedWidget()
        
        # Mode 1: Text matrix input (original)
        text_mode_widget = QWidget()
        text_mode_layout = QVBoxLayout(text_mode_widget)
        text_mode_layout.setContentsMargins(0, 0, 0, 0)
        text_mode_layout.setSpacing(0)
        
        j_edit = QTextEdit()
        j_edit.setPlainText(default_j_matrix)
        j_edit.setMinimumHeight(100)
        j_edit.setMaximumHeight(150)
        j_edit.setPlaceholderText("Enter J matrix with variables (a, b, c, ...)\ne.g., [[0, 0, c, a], [0, 0, c, a], ...]")
        j_edit.setStyleSheet("QTextEdit { font-family: 'Consolas', 'Courier New', monospace; font-size: 9pt; }")
        
        text_mode_layout.addWidget(j_edit)
        
        # Mode 2: Upper triangle grid input
        grid_mode_widget = QWidget()
        grid_mode_layout = QVBoxLayout(grid_mode_widget)
        grid_mode_layout.setContentsMargins(0, 0, 0, 0)
        grid_mode_layout.setSpacing(5)
        
        # Scroll area for grid
        grid_scroll = QScrollArea()
        grid_scroll.setWidgetResizable(True)
        grid_scroll.setMinimumHeight(150)  # Minimum height
        grid_scroll.setMaximumHeight(350)  # Increased max height, adjustable
        grid_scroll.setStyleSheet("QScrollArea { border: 1px solid #ccc; background: white; }")
        
        grid_content = QWidget()
        grid_content_layout = QVBoxLayout(grid_content)
        grid_content_layout.setAlignment(Qt.AlignTop)
        
        grid_placeholder = QLabel("Please enter isotopes first, then click 'Generate Grid' button")
        grid_placeholder.setAlignment(Qt.AlignCenter)
        grid_placeholder.setStyleSheet("color: #888; font-style: italic; padding: 20px;")
        grid_content_layout.addWidget(grid_placeholder)
        
        grid_scroll.setWidget(grid_content)
        
        # Button container for grid mode buttons
        grid_btn_container = QWidget()
        grid_btn_layout = QHBoxLayout(grid_btn_container)
        grid_btn_layout.setContentsMargins(0, 0, 0, 0)
        grid_btn_layout.setSpacing(8)
        
        gen_grid_btn = QPushButton("Generate Grid from Isotopes")
        gen_grid_btn.setObjectName("GenGridButton")
        gen_grid_btn.setMaximumWidth(200)
        gen_grid_btn.setToolTip("Generate J-coupling input grid based on isotopes")
        
        popup_editor_btn = QPushButton("Open Large Editor")
        popup_editor_btn.setObjectName("PopupEditorButton")
        popup_editor_btn.setMaximumWidth(150)
        popup_editor_btn.setToolTip("Open a larger popup window for easier J-coupling input")
        popup_editor_btn.setEnabled(False)  # Initially disabled until grid is generated
        
        grid_btn_layout.addWidget(gen_grid_btn)
        grid_btn_layout.addWidget(popup_editor_btn)
        grid_btn_layout.addStretch()
        
        grid_mode_layout.addWidget(grid_scroll)
        grid_mode_layout.addWidget(grid_btn_container)
        
        # Add both modes to stack
        j_stack.addWidget(text_mode_widget)
        j_stack.addWidget(grid_mode_widget)
        
        j_layout.addWidget(j_stack)
        
        # Parse button with better alignment
        parse_btn_container = QWidget()
        parse_btn_layout = QHBoxLayout(parse_btn_container)
        parse_btn_layout.setContentsMargins(0, 5, 0, 0)
        parse_btn_layout.setSpacing(0)
        
        parse_btn = QPushButton("Parse Variables")
        parse_btn.setObjectName("ParseButton")
        parse_btn.setMinimumWidth(130)
        parse_btn.setMaximumWidth(150)
        
        parse_btn_layout.addWidget(parse_btn)
        parse_btn_layout.addStretch()
        
        j_layout.addWidget(parse_btn_container)
        
        layout.addRow("J Matrix:", j_container)
        
        # Symmetry configuration - Dynamic list
        sym_container = QGroupBox("Symmetry Optimization")
        sym_main_layout = QVBoxLayout(sym_container)
        sym_main_layout.setContentsMargins(8, 12, 8, 8)
        sym_main_layout.setSpacing(6)
        
        # Scroll area for symmetry entries
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(80)
        scroll_area.setMaximumHeight(180)
        scroll_content = QWidget()
        sym_entries_layout = QVBoxLayout(scroll_content)
        sym_entries_layout.setContentsMargins(0, 0, 0, 0)
        sym_entries_layout.setSpacing(4)
        scroll_area.setWidget(scroll_content)
        
        # Container to store symmetry entry widgets
        sym_entry_list = []
        
        # Add button
        add_sym_btn = QPushButton("Add Symmetry Group")
        add_sym_btn.setObjectName("AddSymButton")
        add_sym_btn.setMinimumWidth(140)
        add_sym_btn.setMaximumWidth(180)
        
        sym_main_layout.addWidget(scroll_area)
        sym_main_layout.addWidget(add_sym_btn)
        
        # Help label
        sym_help = QLabel("Add multiple symmetry groups using the button above. Each group needs a point group type and spin indices.")
        sym_help.setStyleSheet("color: #777; font-size: 9px; font-style: italic; padding: 2px 0;")
        sym_help.setWordWrap(True)
        sym_main_layout.addWidget(sym_help)
        
        layout.addRow(sym_container)
        
        # Basis settings (approximation and formalism)
        bas_group = QGroupBox("Basis Settings (Performance)")
        bas_layout = QFormLayout(bas_group)
        bas_layout.setSpacing(6)
        bas_layout.setContentsMargins(8, 12, 8, 8)
        
        # Approximation method
        approx_combo = QComboBox()
        approx_combo.addItems([
            "none (slowest, most accurate)",
            "IK-0 (fastest, weak coupling)",
            "IK-1 (fast, 1st order)",
            "IK-2 (medium, 2nd order)"
        ])
        approx_combo.setCurrentIndex(0)
        approx_combo.setToolTip("Basis approximation method - higher order = slower but more accurate")
        
        # Formalism
        formalism_combo = QComboBox()
        formalism_combo.addItems([
            "zeeman-hilb (standard)",
            "zeeman-liov (alternative)",
            "sphten-liov (compact)"
        ])
        formalism_combo.setCurrentIndex(0)
        formalism_combo.setToolTip("State space formalism - affects speed and memory usage")
        
        bas_layout.addRow("Approximation:", approx_combo)
        bas_layout.addRow("Formalism:", formalism_combo)
        
        bas_help = QLabel("Speed tips: Use IK approximations for large systems (>6 spins). "
                         "Enable symmetry optimization when possible.")
        bas_help.setStyleSheet("color: #F57C00; font-size: 9px; font-style: italic;")
        bas_help.setWordWrap(True)
        bas_layout.addRow(bas_help)
        
        layout.addRow(bas_group)
        
        # Variable sliders container (will be populated dynamically)
        var_group = QGroupBox("J Coupling Variables")
        var_layout = QFormLayout(var_group)
        var_layout.setSpacing(8)
        var_layout.setContentsMargins(8, 12, 8, 8)
        
        # Add Auto re-run checkbox in Variables group
        auto_rerun_check = QCheckBox("Auto re-run on J-coupling change")
        auto_rerun_check.setChecked(False)
        auto_rerun_check.setToolTip("Automatically re-run simulation when variable sliders change")
        auto_rerun_check.setStyleSheet("color: #546E7A; font-weight: normal;")
        var_layout.addRow(auto_rerun_check)
        
        layout.addRow(var_group)
        
        # Set scroll content
        scroll.setWidget(content)
        
        # Store controls as attributes on the scroll widget (return value)
        scroll.iso_edit = iso_edit
        scroll.save_mol_btn = save_mol_btn
        scroll.load_mol_btn = load_mol_btn
        scroll.j_edit = j_edit
        scroll.j_input_mode_combo = j_input_mode_combo
        scroll.j_stack = j_stack
        scroll.grid_scroll = grid_scroll
        scroll.grid_content = grid_content
        scroll.grid_content_layout = grid_content_layout
        scroll.grid_placeholder = grid_placeholder
        scroll.gen_grid_btn = gen_grid_btn
        scroll.popup_editor_btn = popup_editor_btn
        scroll.j_grid_inputs = {}  # Will store grid input widgets {(i, j): QLineEdit}
        scroll.sym_entries_layout = sym_entries_layout
        scroll.sym_entry_list = sym_entry_list
        scroll.add_sym_btn = add_sym_btn
        scroll.approx_combo = approx_combo  # Store approximation combo
        scroll.formalism_combo = formalism_combo  # Store formalism combo
        scroll.var_layout = var_layout
        scroll.var_group = var_group
        scroll.var_sliders = {}  # Will store {var_name: (slider, spinbox, label)}
        scroll.auto_rerun_check = auto_rerun_check  # Store reference to checkbox
        scroll.parse_btn = parse_btn
        
        # Connect add button
        add_sym_btn.clicked.connect(lambda: self.add_symmetry_entry(scroll, default_sym if not sym_entry_list else ""))
        
        # Add one default symmetry entry if default_sym is provided
        if default_sym.strip():
            self.add_symmetry_entry(scroll, default_sym)
        
        return scroll
    
    def add_symmetry_entry(self, group, default_spins=""):
        """Add a new symmetry group entry with combo box and spin input"""
        entry_widget = QWidget()
        entry_layout = QHBoxLayout(entry_widget)
        entry_layout.setContentsMargins(0, 0, 0, 0)
        entry_layout.setSpacing(8)
        
        # Point group combo box (editable for custom groups)
        group_combo = QComboBox()
        group_combo.setEditable(True)  # Allow custom input
        group_combo.addItems([
            "None",
            "--- Cyclic ---",
            "Ci", "Cs", "C2", "C3", "C4", "C5", "C6",
            "--- Dihedral ---", 
            "D2", "D3", "D4", "D5", "D6",
            "--- Improper Rotation ---",
            "S2", "S3", "S4", "S6", "S8",
            "--- Cubic ---",
            "T", "Td", "Th", "O", "Oh",
            "--- Icosahedral ---",
            "I", "Ih",
            "--- Common Subgroups ---",
            "C2v", "C3v", "C4v", "C5v", "C6v",
            "C2h", "C3h", "C4h", "C5h", "C6h",
            "D2h", "D3h", "D4h", "D5h", "D6h",
            "D2d", "D3d", "D4d", "D5d", "D6d"
        ])
        
        # Disable separator items so they can't be selected
        model = group_combo.model()
        for i in range(group_combo.count()):
            item_text = group_combo.itemText(i)
            if item_text.startswith("---"):
                item = model.item(i)
                item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
                item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
        
        group_combo.setCurrentText("None")
        group_combo.setToolTip(
            "Spinach point groups (editable - you can also type custom groups):\n"
            "C3v: NH3, CH3\n"
            "C2v: H2O\n"
            "D3h: BF3\n"
            "Td: CH4\n"
            "Oh: SF6\n"
            "Set to 'None' to disable symmetry"
        )
        group_combo.setMinimumWidth(100)
        
        # Spin indices input
        spins_edit = QLineEdit()
        spins_edit.setText(default_spins)
        spins_edit.setPlaceholderText("e.g., 1 2 3")
        spins_edit.setToolTip("Enter space-separated spin indices for this symmetry group")
        
        # Delete button
        delete_btn = QPushButton("Delete")
        delete_btn.setObjectName("DeleteSymButton")
        delete_btn.setMaximumWidth(60)
        delete_btn.setToolTip("Remove this symmetry group")
        delete_btn.clicked.connect(lambda: self.remove_symmetry_entry(group, entry_widget))
        
        entry_layout.addWidget(QLabel("Group:"), 0)
        entry_layout.addWidget(group_combo, 2)
        entry_layout.addWidget(QLabel("Spins:"), 0)
        entry_layout.addWidget(spins_edit, 3)
        entry_layout.addWidget(delete_btn, 0)
        
        # Add to layout
        group.sym_entries_layout.addWidget(entry_widget)
        
        # Store reference
        entry_data = {
            'widget': entry_widget,
            'group_combo': group_combo,
            'spins_edit': spins_edit
        }
        group.sym_entry_list.append(entry_data)
        
    def remove_symmetry_entry(self, group, entry_widget):
        """Remove a symmetry entry"""
        # Find and remove from list
        for i, entry_data in enumerate(group.sym_entry_list):
            if entry_data['widget'] == entry_widget:
                group.sym_entry_list.pop(i)
                break
        
        # Remove widget
        entry_widget.setParent(None)
        entry_widget.deleteLater()

    def on_j_input_mode_changed(self, system_identifier, mode_index):
        """Handle J-coupling input mode change
        Args:
            system_identifier: System name (str) or legacy system number (int)
            mode_index: 0 for text mode, 1 for grid mode
        """
        # Handle both string names and legacy int IDs
        if isinstance(system_identifier, int):
            sys_name = f"System {system_identifier}"
        else:
            sys_name = system_identifier
        
        if sys_name not in self.systems:
            return
        
        tab_widget = self.systems[sys_name]['tab_widget']
        tab_widget.j_stack.setCurrentIndex(mode_index)
        
        # Sync data between modes when switching
        if mode_index == 0:  # Switching to text mode
            # Convert grid to text matrix
            self.sync_grid_to_text(sys_name)
        else:  # Switching to grid mode
            # Optionally sync text to grid if grid is empty
            pass
    
    def generate_j_grid(self, system_identifier):
        """Generate J-coupling grid based on isotopes
        Args:
            system_identifier: System name (str) or legacy system number (int)
        """
        # Handle both string names and legacy int IDs
        if isinstance(system_identifier, int):
            sys_name = f"System {system_identifier}"
        else:
            sys_name = system_identifier
        
        if sys_name not in self.systems:
            return
        
        tab_widget = self.systems[sys_name]['tab_widget']
        
        # Get isotopes
        isotopes_text = tab_widget.iso_edit.toPlainText()
        isotopes = parse_isotopes(isotopes_text)
        
        if not isotopes:
            QMessageBox.warning(self, "Invalid Input",
                              f"{sys_name}: Please enter valid isotopes first")
            return
        
        n = len(isotopes)
        
        # Clear existing grid
        tab_widget.j_grid_inputs.clear()
        
        # Clear layout
        while tab_widget.grid_content_layout.count():
            item = tab_widget.grid_content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Create grid layout
        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(3)
        grid_layout.setContentsMargins(5, 5, 5, 5)
        
        # Set column stretch factors to make all columns equal width
        for col in range(n + 1):  # +1 for row label column
            if col == 0:
                grid_layout.setColumnStretch(col, 1)  # Row labels get 1 unit
            else:
                grid_layout.setColumnStretch(col, 2)  # Data columns get 2 units each
        
        # Add header row (isotope labels)
        for j in range(n):
            header_label = QLabel(f"<b>{isotopes[j]}<br/>({j+1})</b>")
            header_label.setAlignment(Qt.AlignCenter)
            header_label.setStyleSheet("color: #1976D2; font-size: 9pt; padding: 2px;")
            header_label.setMinimumWidth(GRID_INPUT_WIDTH)  # Minimum width for readability
            grid_layout.addWidget(header_label, 0, j + 1)
        
        # Add rows for upper triangle
        for i in range(n):
            # Row label
            row_label = QLabel(f"<b>{isotopes[i]} ({i+1})</b>")
            row_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            row_label.setStyleSheet("color: #1976D2; font-size: 9pt; padding: 2px;")
            row_label.setMinimumWidth(50)
            grid_layout.addWidget(row_label, i + 1, 0)
            
            for j in range(n):
                if j > i:  # Upper triangle only
                    input_box = QLineEdit()
                    input_box.setPlaceholderText("0")
                    input_box.setText("0")
                    input_box.setMinimumWidth(GRID_INPUT_WIDTH)  # Minimum width for usability
                    input_box.setAlignment(Qt.AlignCenter)
                    input_box.setStyleSheet("QLineEdit { font-size: 10pt; padding: 3px; }")
                    input_box.setToolTip(f"J-coupling between {isotopes[i]} ({i+1}) and {isotopes[j]} ({j+1})")
                    
                    # Auto-sync to text mode on edit
                    input_box.textChanged.connect(lambda text, sn=sys_name: self.on_grid_value_changed(sn))
                    
                    grid_layout.addWidget(input_box, i + 1, j + 1)
                    tab_widget.j_grid_inputs[(i, j)] = input_box
                elif i == j:  # Diagonal - show dash
                    dash_label = QLabel("—")
                    dash_label.setMinimumWidth(GRID_INPUT_WIDTH)
                    dash_label.setAlignment(Qt.AlignCenter)
                    dash_label.setStyleSheet("color: #ccc; font-size: 14pt;")
                    grid_layout.addWidget(dash_label, i + 1, j + 1)
                else:  # Lower triangle - empty
                    pass
        
        tab_widget.grid_content_layout.addWidget(grid_widget)
        tab_widget.grid_content_layout.addStretch()
        
        # Enable popup editor button now that grid is generated
        tab_widget.popup_editor_btn.setEnabled(True)
        
        # Try to populate from existing text matrix if available
        self.sync_text_to_grid(sys_name)
        
        self.log(f"{sys_name}: Generated J-coupling grid for {n} spins")
    
    def open_j_popup_editor(self, sys_name):
        """Open large popup window for J-coupling editing"""
        if sys_name not in self.systems:
            return
        
        tab_widget = self.systems[sys_name]['tab_widget']
        
        # Check if grid has been generated
        if not tab_widget.j_grid_inputs:
            QMessageBox.warning(self, "No Grid", 
                              "Please generate the J-coupling grid first by clicking 'Generate Grid from Isotopes'")
            return
        
        # Get isotopes
        isotopes_text = tab_widget.iso_edit.toPlainText()
        isotopes = parse_isotopes(isotopes_text)
        
        if not isotopes:
            QMessageBox.warning(self, "No Isotopes", "Please enter isotopes first")
            return
        
        # Get current values from grid
        current_values = {}
        for (i, j), input_box in tab_widget.j_grid_inputs.items():
            current_values[(i, j)] = input_box.text()
        
        # Create and show dialog
        dialog = JCouplingEditorDialog(self, sys_name, isotopes, current_values, self)
        dialog.exec()
    
    def on_grid_value_changed(self, system_identifier):
        """Auto-sync grid changes to text matrix
        Args:
            system_identifier: System name (str) or legacy system number (int)
        """
        # Handle both string names and legacy int IDs
        if isinstance(system_identifier, int):
            sys_name = f"System {system_identifier}"
        else:
            sys_name = system_identifier
        
        if sys_name not in self.systems:
            return
        
        tab_widget = self.systems[sys_name]['tab_widget']
        # Only sync if currently in grid mode
        if tab_widget.j_stack.currentIndex() == 1:  # Grid mode
            self.sync_grid_to_text(sys_name)
    
    def sync_grid_to_text(self, system_identifier):
        """Convert grid input to text matrix format
        Args:
            system_identifier: System name (str) or legacy system number (int)
        """
        # Handle both string names and legacy int IDs
        if isinstance(system_identifier, int):
            sys_name = f"System {system_identifier}"
        else:
            sys_name = system_identifier
        
        if sys_name not in self.systems:
            return
        
        tab_widget = self.systems[sys_name]['tab_widget']
        
        if not tab_widget.j_grid_inputs:
            return
        
        # Determine matrix size
        n = 0
        for (i, j) in tab_widget.j_grid_inputs.keys():
            n = max(n, i + 1, j + 1)
        
        # Build matrix
        matrix_lines = []
        for i in range(n):
            row = []
            for j in range(n):
                if i == j:
                    row.append("0")
                elif j > i:  # Upper triangle
                    if (i, j) in tab_widget.j_grid_inputs:
                        value = tab_widget.j_grid_inputs[(i, j)].text().strip()
                        row.append(value if value else "0")
                    else:
                        row.append("0")
                else:  # Lower triangle (symmetric)
                    row.append("0")
            matrix_lines.append("[" + ", ".join(row) + "]")
        
        matrix_text = "[" + ",\n ".join(matrix_lines) + "]"
        tab_widget.j_edit.setPlainText(matrix_text)
    
    def sync_text_to_grid(self, system_identifier):
        """Try to parse text matrix and populate grid
        Args:
            system_identifier: System name (str) or legacy system number (int)
        """
        # Handle both string names and legacy int IDs
        if isinstance(system_identifier, int):
            sys_name = f"System {system_identifier}"
        else:
            sys_name = system_identifier
        
        if sys_name not in self.systems:
            return
        
        tab_widget = self.systems[sys_name]['tab_widget']
        
        if not tab_widget.j_grid_inputs:
            return
        
        j_text = tab_widget.j_edit.toPlainText().strip()
        if not j_text:
            return
        
        try:
            # Simple parsing - extract values from matrix text
            # Remove whitespace and brackets
            j_text = j_text.replace(" ", "").replace("\n", "")
            
            # Try to parse as nested list
            import ast
            try:
                matrix = ast.literal_eval(j_text)
            except:
                # If literal_eval fails, it might contain variables
                # Just skip syncing in this case
                return
            
            # Populate grid from matrix
            for (i, j), input_box in tab_widget.j_grid_inputs.items():
                if i < len(matrix) and j < len(matrix[i]):
                    value = matrix[i][j]
                    input_box.setText(str(value))
        except Exception as e:
            # If parsing fails, just skip
            pass
    
    def parse_system(self, system_identifier):
        """Parse J matrix and create sliders for variables
        Args:
            system_identifier: System name (str) or legacy system number (int)
        """
        # Handle both string names and legacy int IDs
        if isinstance(system_identifier, int):
            sys_name = f"System {system_identifier}"
            if sys_name not in self.systems:
                QMessageBox.warning(self, "Error", f"System {system_identifier} does not exist")
                return
        else:
            sys_name = system_identifier
            if sys_name not in self.systems:
                QMessageBox.warning(self, "Error", f"{sys_name} does not exist")
                return
        
        # Get system tab widget
        tab_widget = self.systems[sys_name]['tab_widget']
        
        # Get J matrix text (always use text mode as source)
        # j_edit is stored as an attribute on tab_widget
        if not hasattr(tab_widget, 'j_edit'):
            QMessageBox.warning(self, "Error", f"Cannot find J matrix editor for {sys_name}")
            return
        
        j_text = tab_widget.j_edit.toPlainText()
        
        # Extract variables
        variables = extract_variables_from_matrix(j_text)
        
        if not variables:
            QMessageBox.information(self, "Parse Result", 
                                   f"No variables found in {sys_name} J matrix.\n"
                                   "Matrix appears to contain only numbers.")
            return
        
        # Get var_layout and var_sliders from tab_widget
        var_layout = tab_widget.var_layout
        auto_rerun_check = tab_widget.auto_rerun_check
        
        # Clear existing variable controls (but keep the auto re-run checkbox)
        for i in reversed(range(var_layout.count())):
            item = var_layout.takeAt(i)
            widget = item.widget()
            # Don't delete the auto re-run checkbox
            if widget and widget != auto_rerun_check:
                widget.deleteLater()
            elif widget == auto_rerun_check:
                # Re-add the checkbox at the top
                var_layout.insertRow(0, auto_rerun_check)
        
        tab_widget.var_sliders.clear()
        
        # Create slider for each variable
        for var in variables:
            container = QWidget()
            h_layout = QHBoxLayout(container)
            h_layout.setContentsMargins(0, 0, 0, 0)
            h_layout.setSpacing(5)
            
            # Slider
            slider = QSlider(Qt.Horizontal)
            slider.setRange(-5000, 5000)  # 10x range for 0.1 precision
            slider.setValue(1000)  # 100.0 * 10
            slider.setTickPosition(QSlider.TicksBelow)
            slider.setTickInterval(500)
            
            # Spinbox (no suffix - Hz is default unit)
            spinbox = QDoubleSpinBox()
            spinbox.setRange(-500, 500)
            spinbox.setValue(100.0)
            spinbox.setDecimals(2)  # Two decimal places
            spinbox.setSingleStep(0.1)  # Default step for click
            spinbox.setMinimumWidth(95)  # Increased to show full value
            spinbox.setMaximumWidth(110)  # Slightly wider
            spinbox.setToolTip("J-coupling value in Hz\nKeys: ←/→ ±0.1 Hz, ↑/↓ ±1 Hz")
            spinbox.setStyleSheet("QDoubleSpinBox { font-size: 11pt; padding: 2px 4px; }")
            
            # Add keyboard shortcut handler
            spinbox.keyPressEvent = lambda event, sb=spinbox: self._spinbox_key_handler(event, sb)
            
            # Value label (show Hz unit here)
            label = QLabel("100.00 Hz")
            label.setMinimumWidth(60)  # Reduced from 80 to save space
            label.setMaximumWidth(70)  # Add max width to prevent excessive spacing
            label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # Left align to reduce gap
            label.setStyleSheet("font-size: 10pt; font-weight: normal; color: #546E7A; margin-left: 3px;")
            
            # Connect signals for real-time update
            slider.valueChanged.connect(lambda val, sb=spinbox, lbl=label, sn=var: self._update_from_slider(val, sb, lbl, sn))
            spinbox.valueChanged.connect(lambda val, sl=slider, lbl=label, sn=var: self._update_from_spinbox(val, sl, lbl, sn))
            
            h_layout.addWidget(slider, stretch=3)
            h_layout.addWidget(spinbox, stretch=0)
            h_layout.addWidget(label, stretch=0)
            
            var_layout.addRow(f"{var}:", container)
            tab_widget.var_sliders[var] = (slider, spinbox, label)
        
        self.log(f"Parsed {sys_name}: Found variables {variables}")
        QMessageBox.information(self, "Parse Complete", 
                               f"{sys_name}: Found {len(variables)} variable(s):\n{', '.join(variables)}")
    
    def _spinbox_key_handler(self, event, spinbox):
        """Handle keyboard shortcuts for spinbox"""
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QKeyEvent
        
        key = event.key()
        current_val = spinbox.value()
        
        if key == Qt.Key_Left:
            spinbox.setValue(current_val - 0.1)
            event.accept()
        elif key == Qt.Key_Right:
            spinbox.setValue(current_val + 0.1)
            event.accept()
        elif key == Qt.Key_Up:
            spinbox.setValue(current_val + 1.0)
            event.accept()
        elif key == Qt.Key_Down:
            spinbox.setValue(current_val - 1.0)
            event.accept()
        else:
            # Call original key handler
            QDoubleSpinBox.keyPressEvent(spinbox, event)
    
    def _update_from_slider(self, int_val, spinbox, label, var_name):
        """Update spinbox and label when slider changes"""
        float_val = int_val / 10.0  # Convert back to float (slider is 10x)
        spinbox.blockSignals(True)
        spinbox.setValue(float_val)
        spinbox.blockSignals(False)
        label.setText(f"{float_val:.2f} Hz")
        
        # Always update J matrix and weighted sum in real-time
        sys_name = self._get_system_name_for_spinbox(spinbox)
        if sys_name:
            self._update_j_coupling_realtime(sys_name)
    
    def _update_from_spinbox(self, float_val, slider, label, var_name):
        """Update slider and label when spinbox changes"""
        int_val = int(round(float_val * 10))  # Convert to slider value (10x)
        slider.blockSignals(True)
        slider.setValue(int_val)
        slider.blockSignals(False)
        label.setText(f"{float_val:.2f} Hz")
        
        # Always update J matrix and weighted sum in real-time
        sys_name = self._get_system_name_for_slider(slider)
        if sys_name:
            self._update_j_coupling_realtime(sys_name)
    
    def _get_system_name_for_spinbox(self, spinbox):
        """Determine which system a spinbox belongs to"""
        for sys_name, sys_data in self.systems.items():
            tab_widget = sys_data['tab_widget']
            for var_name, (sl, sb, lbl) in tab_widget.var_sliders.items():
                if sb == spinbox:
                    return sys_name
        return None
    
    def _get_system_name_for_slider(self, slider):
        """Determine which system a slider belongs to"""
        for sys_name, sys_data in self.systems.items():
            tab_widget = sys_data['tab_widget']
            for var_name, (sl, sb, lbl) in tab_widget.var_sliders.items():
                if sl == slider:
                    return sys_name
        return None
    
    def _update_j_coupling_realtime(self, sys_name):
        """Real-time update: re-run simulation only if auto re-run is enabled"""
        if sys_name not in self.systems:
            return
        
        tab_widget = self.systems[sys_name]['tab_widget']
        
        if tab_widget.auto_rerun_check.isChecked():
            # Check if system is already running
            if self.systems[sys_name]['worker'] and self.systems[sys_name]['worker'].isRunning():
                # Mark pending update to run after current one finishes
                self.systems[sys_name]['pending_update'] = True
                return  # Silently skip if already running
            
            # Re-run simulation for real-time update
            self.run_system(sys_name)
        else:
            # Just update weighted sum if all systems are ready
            self.update_weighted_sum()
    
    def _update_weight_controls(self):
        """Update weight control spinboxes and sliders for all systems"""
        # Clear existing controls
        while self.weight_controls_layout.count():
            child = self.weight_controls_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        self.weight_spinboxes.clear()
        
        # Create weight control for each system
        for sys_name in sorted(self.systems.keys()):
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(8)
            
            # System name label
            label = QLabel(f"{sys_name}:")
            label.setMinimumWidth(80)
            
            # Slider (0-100 for 0.0-1.0 range, step 0.01)
            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, 100)  # 0-100 for 0.0-1.0 with 0.01 precision
            slider.setValue(int(self.systems[sys_name]['weight'] * 100))
            slider.setTickPosition(QSlider.TicksBelow)
            slider.setTickInterval(10)  # Tick every 0.1
            
            # SpinBox
            spinbox = QDoubleSpinBox()
            spinbox.setRange(0.0, 1.0)
            spinbox.setValue(self.systems[sys_name]['weight'])
            spinbox.setSingleStep(0.1)
            spinbox.setDecimals(2)
            spinbox.setMinimumWidth(80)
            spinbox.setMaximumWidth(90)
            
            # Connect signals - slider and spinbox sync
            slider.valueChanged.connect(
                lambda val, sb=spinbox, name=sys_name: self._on_weight_slider_changed(val, sb, name)
            )
            spinbox.valueChanged.connect(
                lambda val, sl=slider, name=sys_name: self._on_weight_spinbox_changed(val, sl, name)
            )
            
            self.weight_spinboxes[sys_name] = (slider, spinbox)
            
            # Layout: [Label] [Slider--------] [SpinBox]
            row_layout.addWidget(label)
            row_layout.addWidget(slider, stretch=3)
            row_layout.addWidget(spinbox, stretch=0)
            
            self.weight_controls_layout.addWidget(row_widget)
    
    def _update_broadening_controls(self):
        """Update broadening control widgets for all systems (similar to weight controls)"""
        # Clear existing controls
        while self.broadening_controls_layout.count():
            child = self.broadening_controls_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        self.broadening_controls.clear()
        
        # Create broadening control for each system
        for sys_name in sorted(self.systems.keys()):
            row_widget = QWidget()
            row_layout = QVBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 6)
            row_layout.setSpacing(4)
            
            # First row: System name + Enable checkbox
            header_widget = QWidget()
            header_layout = QHBoxLayout(header_widget)
            header_layout.setContentsMargins(0, 0, 0, 0)
            header_layout.setSpacing(8)
            
            # System name label
            sys_label = QLabel(f"{sys_name}:")
            sys_label.setMinimumWidth(80)
            sys_label.setStyleSheet("font-weight: bold; color: #546E7A;")
            
            # Enable checkbox
            enable_check = QCheckBox("Enable")
            enable_check.setChecked(self.systems[sys_name]['broadening_enabled'])
            enable_check.setToolTip(f"Enable Gaussian broadening for {sys_name}")
            
            header_layout.addWidget(sys_label)
            header_layout.addWidget(enable_check)
            header_layout.addStretch()
            
            # Second row: FWHM controls
            fwhm_widget = QWidget()
            fwhm_layout = QHBoxLayout(fwhm_widget)
            fwhm_layout.setContentsMargins(20, 0, 0, 0)  # Indent for hierarchy
            fwhm_layout.setSpacing(8)
            
            # FWHM label
            fwhm_label_text = QLabel("FWHM:")
            fwhm_label_text.setMinimumWidth(60)
            fwhm_label_text.setStyleSheet("color: #757575;")
            
            # Slider (1-100 for 0.1-10.0 Hz)
            slider = QSlider(Qt.Horizontal)
            slider.setRange(1, 100)
            slider.setValue(int(self.systems[sys_name]['broadening_fwhm'] * 10))
            slider.setEnabled(self.systems[sys_name]['broadening_enabled'])
            slider.setMinimumWidth(150)
            
            # SpinBox
            spinbox = QDoubleSpinBox()
            spinbox.setRange(0.0, 10.0)
            spinbox.setDecimals(1)
            spinbox.setSingleStep(0.1)
            spinbox.setValue(self.systems[sys_name]['broadening_fwhm'])
            spinbox.setSuffix(" Hz")
            spinbox.setEnabled(self.systems[sys_name]['broadening_enabled'])
            spinbox.setMinimumWidth(90)
            spinbox.setMaximumWidth(110)
            
            # Value display label
            value_label = QLabel(f"{self.systems[sys_name]['broadening_fwhm']:.1f} Hz")
            value_label.setStyleSheet("color: #2196F3; font-weight: bold; min-width: 60px;")
            value_label.setAlignment(Qt.AlignCenter)
            
            fwhm_layout.addWidget(fwhm_label_text)
            fwhm_layout.addWidget(slider, stretch=3)
            fwhm_layout.addWidget(spinbox, stretch=0)
            fwhm_layout.addWidget(value_label, stretch=0)
            
            # Add to main row
            row_layout.addWidget(header_widget)
            row_layout.addWidget(fwhm_widget)
            
            # Store references
            self.broadening_controls[sys_name] = (enable_check, slider, spinbox, value_label)
            
            # Connect signals
            enable_check.stateChanged.connect(
                lambda state, sn=sys_name: self._on_broadening_enabled_changed_plotsettings(sn, state)
            )
            slider.valueChanged.connect(
                lambda val, sn=sys_name: self._on_broadening_slider_changed_plotsettings(sn, val)
            )
            spinbox.valueChanged.connect(
                lambda val, sn=sys_name: self._on_broadening_spinbox_changed_plotsettings(sn, val)
            )
            
            self.broadening_controls_layout.addWidget(row_widget)
    
    def _on_weight_slider_changed(self, int_val, spinbox, sys_name):
        """Handle weight slider change"""
        float_val = int_val / 100.0  # Convert 0-100 to 0.0-1.0
        spinbox.blockSignals(True)
        spinbox.setValue(float_val)
        spinbox.blockSignals(False)
        self.on_system_weight_changed(sys_name, float_val)
    
    def _on_weight_spinbox_changed(self, float_val, slider, sys_name):
        """Handle weight spinbox change"""
        int_val = int(float_val * 100)  # Convert 0.0-1.0 to 0-100
        slider.blockSignals(True)
        slider.setValue(int_val)
        slider.blockSignals(False)
        self.on_system_weight_changed(sys_name, float_val)
    
    def on_system_weight_changed(self, sys_name, value):
        """Update weight for a specific system"""
        self.systems[sys_name]['weight'] = value
        
        # Auto-normalize if enabled
        if self.auto_normalize_checkbox.isChecked():
            self._normalize_weights()
        
        # Update weighted sum
        self.update_weighted_sum()
    
    def _on_broadening_enabled_changed_plotsettings(self, sys_name, state):
        """Handle broadening enable/disable from Plot Settings tab"""
        enabled = (state == Qt.CheckState.Checked.value or state == 2)
        self.systems[sys_name]['broadening_enabled'] = enabled
        
        # Update UI controls
        if sys_name in self.broadening_controls:
            enable_check, slider, spinbox, value_label = self.broadening_controls[sys_name]
            slider.setEnabled(enabled)
            spinbox.setEnabled(enabled)
            
            # Log the change
            if enabled:
                fwhm = self.systems[sys_name]['broadening_fwhm']
                self.log(f"{sys_name}: Gaussian broadening <b>enabled</b> (FWHM = {fwhm:.1f} Hz)")
            else:
                self.log(f"{sys_name}: Gaussian broadening <b>disabled</b> (restored original spectrum)")
        
        # Apply or remove broadening
        self._apply_broadening_to_system(sys_name)
    
    def _on_broadening_slider_changed_plotsettings(self, sys_name, slider_val):
        """Handle broadening slider change from Plot Settings tab"""
        if not self.systems[sys_name]['broadening_enabled']:
            return
        
        fwhm = slider_val / 10.0  # Convert 1-100 to 0.1-10.0
        self.systems[sys_name]['broadening_fwhm'] = fwhm
        
        # Update spinbox and label
        if sys_name in self.broadening_controls:
            enable_check, slider, spinbox, value_label = self.broadening_controls[sys_name]
            spinbox.blockSignals(True)
            spinbox.setValue(fwhm)
            spinbox.blockSignals(False)
            value_label.setText(f"{fwhm:.1f} Hz")
        
        # Apply broadening (no log for slider to avoid spam)
        self._apply_broadening_to_system(sys_name)
    
    def _on_broadening_spinbox_changed_plotsettings(self, sys_name, fwhm):
        """Handle broadening spinbox change from Plot Settings tab"""
        if not self.systems[sys_name]['broadening_enabled']:
            return
        
        self.systems[sys_name]['broadening_fwhm'] = fwhm
        
        # Update slider and label
        if sys_name in self.broadening_controls:
            enable_check, slider, spinbox, value_label = self.broadening_controls[sys_name]
            slider.blockSignals(True)
            slider.setValue(int(fwhm * 10))
            slider.blockSignals(False)
            value_label.setText(f"{fwhm:.1f} Hz")
        
        # Log precise input
        self.log(f"{sys_name}: Broadening FWHM set to <b>{fwhm:.1f} Hz</b>")
        
        # Apply broadening
        self._apply_broadening_to_system(sys_name)
    
    def on_auto_normalize_changed(self, state):
        """Handle auto-normalize checkbox state change"""
        if state == Qt.Checked:
            self._normalize_weights()
            self.update_weighted_sum()
    
    def _normalize_weights(self):
        """Normalize all weights to sum to 1.0"""
        total = sum(sys_data['weight'] for sys_data in self.systems.values())
        if total > 0:
            for sys_name, sys_data in self.systems.items():
                normalized = sys_data['weight'] / total
                sys_data['weight'] = normalized
                if sys_name in self.weight_spinboxes:
                    slider, spinbox = self.weight_spinboxes[sys_name]
                    
                    # Update both slider and spinbox
                    slider.blockSignals(True)
                    spinbox.blockSignals(True)
                    
                    slider.setValue(int(normalized * 100))
                    spinbox.setValue(normalized)
                    
                    slider.blockSignals(False)
                    spinbox.blockSignals(False)
    
    def on_weight_changed(self, value):
        """Legacy method - kept for compatibility but deprecated"""
        # This is no longer used with multi-system design
        pass
    
    # ========== Broadening Control Methods ==========
    
    def _apply_broadening_to_system(self, sys_name):
        """Apply broadening to a system's spectrum and update plot"""
        # Check if we have data
        if self.systems[sys_name]['spec_raw'] is None:
            return  # No data to broaden
        
        freq = self.systems[sys_name]['freq']
        spec_raw = self.systems[sys_name]['spec_raw']
        
        # Check if broadening is enabled
        if self.systems[sys_name]['broadening_enabled']:
            # Apply Gaussian broadening
            fwhm = self.systems[sys_name]['broadening_fwhm']
            spec_broadened = self.apply_gaussian_broadening(freq, spec_raw, fwhm)
            self.systems[sys_name]['spec'] = spec_broadened
        else:
            # Restore original spectrum (no broadening)
            self.systems[sys_name]['spec'] = spec_raw.copy()
        
        # Update plot
        self._update_system_plot(sys_name)
        
        # Update weighted sum
        self.update_weighted_sum()
    
    def _update_system_plot(self, sys_name):
        """Update the plot for a specific system"""
        plot_widget = self.systems[sys_name]['plot_widget']
        freq = self.systems[sys_name]['freq']
        spec = self.systems[sys_name]['spec']
        
        if plot_widget and freq is not None and spec is not None:
            self.plot_spectrum(plot_widget, freq, spec, sys_name)
    
    # ========== End Broadening Methods ==========
    
    def get_variable_values(self, system_identifier):
        """Get current values of all variables for a system
        Args:
            system_identifier: System name (str) or legacy system number (int)
        """
        # Handle both string names and legacy int IDs
        if isinstance(system_identifier, int):
            sys_name = f"System {system_identifier}"
        else:
            sys_name = system_identifier
        
        if sys_name not in self.systems:
            return {}
        
        tab_widget = self.systems[sys_name]['tab_widget']
        
        var_values = {}
        for var_name, (slider, spinbox, label) in tab_widget.var_sliders.items():
            var_values[var_name] = spinbox.value()
        
        return var_values
    
    def get_j_matrix(self, system_identifier):
        """Evaluate J matrix with current variable values
        Args:
            system_identifier: System name (str) or legacy system number (int)
        """
        # Handle both string names and legacy int IDs
        if isinstance(system_identifier, int):
            sys_name = f"System {system_identifier}"
        else:
            sys_name = system_identifier
        
        if sys_name not in self.systems:
            raise ValueError(f"{sys_name} does not exist")
        
        tab_widget = self.systems[sys_name]['tab_widget']
        j_text = tab_widget.j_edit.toPlainText()
        var_values = self.get_variable_values(sys_name)
        
        try:
            j_matrix = evaluate_matrix(j_text, var_values)
            return j_matrix
        except Exception as e:
            raise ValueError(f"Failed to evaluate J matrix for {sys_name}: {e}")
    
    def run_current_system(self):
        """Run simulation for the currently selected system"""
        current_idx = self.system_tabs.currentIndex()
        sys_name = self.system_tabs.tabText(current_idx)
        self.run_system(sys_name)
    
    def run_all_systems(self):
        """Run simulations for all systems sequentially"""
        system_names = sorted(self.systems.keys())
        if not system_names:
            QMessageBox.warning(self, "No Systems", "No systems to run")
            return
        
        # Store the queue of systems to run
        self._run_queue = system_names[1:]  # All except first
        
        self.log(f"Starting sequential run of {len(system_names)} systems...")
        # Start with first system
        self.run_system(system_names[0])
    
    def reprocess_current_system(self):
        """Reprocess the currently selected system with new window/zerofill settings"""
        current_idx = self.system_tabs.currentIndex()
        sys_name = self.system_tabs.tabText(current_idx)
        self.reprocess_system(sys_name)

    def check_pending_updates(self, sys_name):
        """Check if there are any pending updates for a system and run them"""
        if sys_name in self.systems and self.systems[sys_name].get('pending_update', False):
            # Clear flag implies we are handling it
            self.systems[sys_name]['pending_update'] = False
            self.log(f"{sys_name}: Running pending update...")
            
            # Use QTimer to schedule next run to ensure current thread logic is fully complete
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self.run_system(sys_name))
    
    def run_system(self, system_identifier):
        """Run simulation for one system
        
        Args:
            system_identifier: Either system name (str) like "System 1" or legacy number (int) 1, 2
        """
        # Handle legacy numeric input
        if isinstance(system_identifier, int):
            system_num = system_identifier
            sys_name = f"System {system_num}"
            if sys_name not in self.systems:
                QMessageBox.warning(self, "Error", f"System {system_num} not found")
                return
        else:
            sys_name = system_identifier
            if sys_name not in self.systems:
                QMessageBox.warning(self, "Error", f"{sys_name} not found")
                return
        
        # Check if system is already running
        if self.systems[sys_name]['worker'] and self.systems[sys_name]['worker'].isRunning():
            QMessageBox.warning(self, "Busy", f"{sys_name} simulation is already running")
            return
        
        # Get the tab widget for this system
        group = self.systems[sys_name]['tab_widget']
        if not group:
            QMessageBox.warning(self, "Error", f"{sys_name} tab not found")
            return
        
        try:
            # Get parameters
            isotopes_text = group.iso_edit.toPlainText()
            isotopes = parse_isotopes(isotopes_text)
            
            if not isotopes:
                QMessageBox.warning(self, "Invalid Input", 
                                   f"{sys_name}: Please enter valid isotopes")
                return
            
            # Check for variables in J matrix text
            j_text = group.j_edit.toPlainText()
            vars_in_text = extract_variables_from_matrix(j_text)
            
            # Check if variables are parsed (only if variables exist)
            if vars_in_text and not group.var_sliders:
                reply = QMessageBox.question(self, "Variables Not Parsed",
                                            f"{sys_name}: J matrix contains variables but they have not been parsed.\n"
                                            "Would you like to parse them now?",
                                            QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.Yes:
                    self.parse_system(sys_name)
                    if not group.var_sliders:
                        return
                else:
                    return
            
            J_matrix = self.get_j_matrix(sys_name)
            
            # Get parameters from Parameters tab (shared by both systems)
            magnet = self.get_magnet_tesla()
            sweep = self.sweep_spin.value()
            npoints = int(self.npoints_spin.value())
            zerofill = int(self.zerofill_spin.value())
            offset = 0.0
            
            # Get symmetry settings from all entries
            sym_groups = []  # List of (group_name, spins_list)
            
            for entry_data in group.sym_entry_list:
                group_name = entry_data['group_combo'].currentText().strip()
                spins_text = entry_data['spins_edit'].text().strip()
                
                # Skip separators, "None", and empty entries
                if not group_name or group_name.startswith('---') or group_name.lower() == "none":
                    continue
                
                # Parse spin indices
                if spins_text:
                    try:
                        spins = [int(x) for x in spins_text.replace(',', ' ').split()]
                        if spins:
                            sym_groups.append((group_name, spins))
                            self.log(f"{sys_name}: Added {group_name} symmetry for spins {spins}")
                    except ValueError:
                        self.log(f"{sys_name}: Warning - Invalid spin indices: {spins_text}")
            
            # Format for Spinach
            sym_spins = None
            sym_group_names = None
            if sym_groups:
                sym_spins = [spins for _, spins in sym_groups]
                sym_group_names = [name for name, _ in sym_groups]

            
            use_gpu = self.gpu_check.isChecked()
            
            # Get performance settings from the current system's controls
            approx_text = group.approx_combo.currentText()
            approx = approx_text.split(' ')[0]  # Extract 'none', 'IK-0', 'IK-1', 'IK-2'
            
            formalism_text = group.formalism_combo.currentText()
            formalism = formalism_text.split(' ')[0]  # Extract 'zeeman-hilb', 'zeeman-liov', 'sphten-liov'
            
            # Get window function settings
            window_label = self.window_type_combo.currentText()
            window_type = self.window_choices[window_label]
            window_k = self.window_k_spin.value()
            
            # Log system information before starting
            self.log(f"<b>Starting {sys_name} simulation:</b>")
            self.log(f"  - Isotopes: {isotopes} ({len(isotopes)} spins)")
            
            # Display J-coupling matrix as table with isotope labels
            self.log(f"  - J-coupling matrix (Hz):")
            # Header row with isotope labels
            header = "         " + "".join([f"{isotopes[j]:>10}" for j in range(len(isotopes))])
            self.log(header)
            # Matrix rows with isotope label on left
            for i in range(len(J_matrix)):
                row_str = f"    {isotopes[i]:>4} " + "".join([f"{J_matrix[i,j]:10.2f}" for j in range(len(J_matrix[i]))])
                self.log(row_str)
            
            self.log(f"  - Magnet: {magnet:.2f} T, Sweep: {sweep:.1f} Hz, Points: {int(npoints)}")
            self.log(f"  - Approximation: {approx}, Formalism: {formalism}")
            self.log(f"  - Window: {window_type}, GPU: {'Yes' if use_gpu else 'No'}")
            if sym_groups:
                sym_str = ", ".join([f"{name}({' '.join(map(str, spins))})" for name, spins in sym_groups])
                self.log(f"  - Symmetry: {sym_str}")
            
            # Create worker
            worker = SimWorker(isotopes, J_matrix, magnet, sweep, npoints, 
                              zerofill, offset, sym_spins, sym_group_names, 
                              sys_name, use_gpu, approx, formalism, 
                              window_type, window_k)
            worker.log.connect(self.log)
            worker.detailed_log.connect(self.detailed_log_window.append_log)
            worker.done.connect(self.on_simulation_done)
            worker.failed.connect(self.on_simulation_failed)
            # Connect finished signal to check for pending updates
            worker.finished.connect(lambda: self.check_pending_updates(sys_name))
            
            # Store worker reference
            self.systems[sys_name]['worker'] = worker
            
            worker.start()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to run {sys_name}:\n{str(e)}")
            self.log(f"<b>Error:</b> {str(e)}")
    
    def reprocess_system(self, system_identifier):
        """Reprocess existing simulation data with new window/zerofill settings (fast)
        
        Args:
            system_identifier: Either system name (str) like "System 1" or legacy number (int) 1, 2
        """
        # Handle legacy numeric input
        if isinstance(system_identifier, int):
            system_num = system_identifier
            sys_name = f"System {system_num}"
            if sys_name not in self.systems:
                QMessageBox.warning(self, "Error", f"System {system_num} not found")
                return
        else:
            sys_name = system_identifier
            if sys_name not in self.systems:
                QMessageBox.warning(self, "Error", f"{sys_name} not found")
                return
        
        try:
            # Check if system has been simulated
            if self.systems[sys_name]['freq'] is None:
                QMessageBox.warning(self, "No Data", f"{sys_name} has not been simulated yet.\nPlease run full simulation first.")
                return
            
            # Check if worker is already running for this system
            if self.systems[sys_name]['worker'] and self.systems[sys_name]['worker'].isRunning():
                QMessageBox.warning(self, "Busy", f"{sys_name} is already running")
                return
            
            # Get window function settings
            window_label = self.window_type_combo.currentText()
            window_type = self.window_choices[window_label]
            window_k = self.window_k_spin.value()
            zerofill = int(self.zerofill_spin.value())
            use_gpu = self.gpu_check.isChecked()
            
            # Create reprocess worker
            worker = PostProcessWorker(sys_name, window_type, window_k, zerofill, use_gpu)
            worker.log.connect(self.log)
            worker.detailed_log.connect(self.detailed_log_window.append_log)
            worker.done.connect(self.on_simulation_done)
            worker.failed.connect(self.on_simulation_failed)
            
            # Store worker in system dictionary
            self.systems[sys_name]['worker'] = worker
            
            worker.start()
            self.log(f"Reprocessing {sys_name} (fast mode)...")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to reprocess {sys_name}:\n{str(e)}")
            self.log(f"<b>Error:</b> {str(e)}")
    
    def run_both_systems(self):
        """Run both systems sequentially"""
        self.run_system(1)
        # System 2 will be started when System 1 completes
        self._pending_system2 = True
    
    @Slot(np.ndarray, np.ndarray, str)
    def on_simulation_done(self, freq, spec, system_name):
        """Handle completed simulation"""
        # Update system data
        if system_name in self.systems:
            self.systems[system_name]['freq'] = freq
            self.systems[system_name]['spec_raw'] = spec  # Store original unbroadened spectrum
            
            # Apply broadening if enabled
            if self.systems[system_name]['broadening_enabled']:
                fwhm = self.systems[system_name]['broadening_fwhm']
                spec_broadened = self.apply_gaussian_broadening(freq, spec, fwhm)
                self.systems[system_name]['spec'] = spec_broadened
            else:
                self.systems[system_name]['spec'] = spec
            
            # Get the plot widget for this system
            plot_widget = self.systems[system_name]['plot_widget']
            if plot_widget:
                self.plot_spectrum(plot_widget, freq, self.systems[system_name]['spec'], system_name)
            
            self.log(f"{system_name} completed!")
        else:
            self.log(f"Warning: Received data for unknown system '{system_name}'")
        
        # Check if there are more systems to run in the queue
        if hasattr(self, '_run_queue') and self._run_queue:
            next_system = self._run_queue.pop(0)
            self.log(f"Starting next system: {next_system}")
            self.run_system(next_system)
        elif hasattr(self, '_run_queue'):
            # Queue is empty, all systems completed
            del self._run_queue
            self.log("All systems completed!")
        
        # Update weighted sum if at least one system has data
        self.update_weighted_sum()
    
    def update_weighted_sum(self):
        """Calculate and plot weighted sum of all systems"""
        # Collect all systems with data
        systems_with_data = []
        for sys_name in sorted(self.systems.keys()):
            if self.systems[sys_name]['freq'] is not None and self.systems[sys_name]['spec'] is not None:
                systems_with_data.append(sys_name)
        
        if len(systems_with_data) == 0:
            # No data to plot
            return
        
        # Check for Overlay Mode
        if hasattr(self, 'overlay_check') and self.overlay_check.isChecked():
            # Overlay Mode
            data_list = []
            
            # Get display mode
            mode = self.display_mode_combo.currentIndex()
            ylabel = ["Magnitude", "Re(spec)", "Im(spec)"][mode]
            
            for sys_name in systems_with_data:
                freq = self.systems[sys_name]['freq']
                spec = self.systems[sys_name]['spec']
                weight = self.systems[sys_name]['weight']
                
                # Apply display mode logic locally since we are bypassing plot_spectrum
                if mode == 0:  # Magnitude
                    y_data = np.abs(spec)
                elif mode == 1:  # Real
                    y_data = np.real(spec)
                else:  # Imag
                    y_data = np.imag(spec)
                
                # Apply weight (showing weighted components helps understand the sum)
                y_data = y_data * weight
                
                data_list.append((freq, y_data, f"{sys_name} ({weight:.2f})", None))

            # Get ranges
            x_min, x_max, y_min, y_max = self.get_plot_ranges()
            x_range = (x_min, x_max) if x_min is not None and x_max is not None else None
            y_range = (y_min, y_max) if y_min is not None and y_max is not None else None
            
            self.plot_sum.draw_multi(data_list, ylabel=ylabel, x_range=x_range, y_range=y_range, title="Overlay Spectra", invert=False)
            return
        
        if len(systems_with_data) == 1:
            # Only one system has data, just plot it
            sys_name = systems_with_data[0]
            freq = self.systems[sys_name]['freq']
            spec = self.systems[sys_name]['spec']
            self.plot_spectrum(self.plot_sum, freq, spec, 
                              f"{sys_name}")
            return
        
        # Multiple systems - calculate weighted sum
        # Find common frequency range
        freq_min = max(self.systems[sys_name]['freq'].min() for sys_name in systems_with_data)
        freq_max = min(self.systems[sys_name]['freq'].max() for sys_name in systems_with_data)
        
        # Use the first system's frequency array length as reference
        first_sys = systems_with_data[0]
        freq = np.linspace(freq_min, freq_max, len(self.systems[first_sys]['freq']))
        
        # Initialize weighted sum
        weighted_spec = np.zeros_like(freq, dtype=complex)
        
        # Interpolate and add each system with its weight
        for sys_name in systems_with_data:
            sys_freq = self.systems[sys_name]['freq']
            sys_spec = self.systems[sys_name]['spec']
            weight = self.systems[sys_name]['weight']
            
            # Interpolate to common frequency grid
            spec_interp_real = np.interp(freq, sys_freq, sys_spec.real)
            spec_interp_imag = np.interp(freq, sys_freq, sys_spec.imag)
            spec_interp = spec_interp_real + 1j * spec_interp_imag
            
            weighted_spec += weight * spec_interp
        
        # Create title showing weights
        weight_str = ", ".join([f"{sys}: {self.systems[sys]['weight']:.2f}" 
                                for sys in systems_with_data])
        title = f"Weighted Sum ({weight_str})"
        
        self.plot_spectrum(self.plot_sum, freq, weighted_spec, title)
    
    def apply_gaussian_broadening(self, freq, spec, fwhm_hz):
        """
        Apply Gaussian line broadening in frequency domain via convolution
        
        Args:
            freq: frequency array (Hz)
            spec: complex spectrum
            fwhm_hz: Full Width at Half Maximum in Hz
        
        Returns:
            Broadened complex spectrum
        """
        if fwhm_hz <= 0:
            return spec
        
        # Convert FWHM to sigma (standard deviation)
        sigma = fwhm_hz / (2 * np.sqrt(2 * np.log(2)))
        
        # Get frequency spacing
        df = abs(freq[1] - freq[0]) if len(freq) > 1 else 1.0
        
        # Create Gaussian kernel
        # Kernel size: 6*sigma should cover >99.7% of Gaussian
        kernel_half_width = int(np.ceil(3 * sigma / df))
        kernel_size = 2 * kernel_half_width + 1
        
        # Build Gaussian
        x = np.arange(-kernel_half_width, kernel_half_width + 1) * df
        gaussian = np.exp(-x**2 / (2 * sigma**2))
        gaussian /= gaussian.sum()  # Normalize to preserve total intensity
        
        # Apply convolution separately to real and imaginary parts
        spec_real = np.convolve(spec.real, gaussian, mode='same')
        spec_imag = np.convolve(spec.imag, gaussian, mode='same')
        
        return spec_real + 1j * spec_imag

    
    def plot_spectrum(self, plot_widget, freq, spec, title):
        """Plot a spectrum using PlotWidget's draw method"""
        # Get display mode
        mode = self.display_mode_combo.currentIndex()
        
        # Process spectrum based on display mode
        if mode == 0:  # |spec| (magnitude)
            y_data = np.abs(spec)
            ylabel = "Magnitude"
        elif mode == 1:  # Re(spec)
            y_data = np.real(spec)
            ylabel = "Re(spec)"
        else:  # Im(spec)
            y_data = np.imag(spec)
            ylabel = "Im(spec)"
        
        # Get plot ranges
        x_min, x_max, y_min, y_max = self.get_plot_ranges()
        x_range = (x_min, x_max) if x_min is not None and x_max is not None else None
        y_range = (y_min, y_max) if y_min is not None and y_max is not None else None
        
        if isinstance(plot_widget, PlotWidget):
            # Store complex spectrum data in widget for display mode switching
            plot_widget.current_spec = spec
            plot_widget.draw(freq, y_data, "Frequency (Hz)", invert=False, 
                            title=title, ylabel=ylabel,
                            x_range=x_range, y_range=y_range)
        else:
            # Fallback to old method
            plot_widget.fig.clear()
            ax = plot_widget.fig.add_subplot(111)
            
            ax.plot(freq, y_data, 'b-', linewidth=1)
            ax.set_xlabel('Frequency (Hz)')
            ax.set_ylabel(ylabel)
            ax.set_title(title, fontweight='bold')
            ax.grid(True, alpha=0.3)
            
            # Apply ranges
            if x_range and x_range[0] is not None and x_range[1] is not None:
                ax.set_xlim(x_range)
            if y_range and y_range[0] is not None and y_range[1] is not None:
                ax.set_ylim(y_range)
            
            plot_widget.canvas.draw()
            plot_widget.canvas.draw()
    
    def on_display_mode_changed(self):
        """Handle display mode change - update all plots"""
        # Re-plot all available spectra
        for sys_name, sys_data in self.systems.items():
            freq = sys_data['freq']
            spec = sys_data['spec']
            plot_widget = sys_data['plot_widget']
            
            if freq is not None and spec is not None and plot_widget:
                self.plot_spectrum(plot_widget, freq, spec, sys_name)
        
        # Re-plot weighted sum if available
        self.update_weighted_sum()
        
        self.log(f"Display mode changed to: {self.display_mode_combo.currentText()}")
    
    def on_window_type_changed(self):
        """Enable/disable k parameter based on window type"""
        win_label = self.window_type_combo.currentText()
        wtoken = self.window_choices[win_label]
        needs_k = wtoken in ("exp", "gauss", "kaiser")
        self.window_k_spin.setEnabled(needs_k)
        self.log(f"Window function changed to: {win_label}")
    
    @Slot(str)
    def on_simulation_failed(self, msg):
        """Handle simulation failure"""
        self.log(f"<b>ERROR:</b> {msg}")
        QMessageBox.critical(self, "Simulation Failed", msg)
    
    def log(self, msg):
        """Add message to log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] {msg}"
        self.log_text.append(formatted_msg)
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
        # Also send to detailed log window
        self.detailed_log_window.append_log(formatted_msg)
    
    def show_detailed_logs(self):
        """Show the detailed log window"""
        self.detailed_log_window.show()
        self.detailed_log_window.raise_()
        self.detailed_log_window.activateWindow()
    
    def reset_all_plots(self):
        """Reset all plot views"""
        for sys_data in self.systems.values():
            if sys_data['plot_widget']:
                sys_data['plot_widget'].update_plot()
        if hasattr(self, 'plot_sum') and self.plot_sum:
            self.plot_sum.update_plot()
        self.log("All plots reset to default view")
    
    def reset_plot_ranges(self):
        """Reset all plot range inputs to auto"""
        if hasattr(self, 'x_min_edit'):
            self.x_min_edit.clear()
            self.x_max_edit.clear()
            self.y_min_edit.clear()
            self.y_max_edit.clear()
        if hasattr(self, 'range_group'):
            self.range_group.setChecked(False)
        self.update_current_plot()
        self.log("Plot ranges reset to auto")
    
    def auto_y_from_x(self):
        """Automatically set Y range based on current X range"""
        if not hasattr(self, 'x_min_edit'):
            return
            
        current_index = self.plot_tabs.currentIndex()
        current_widget = self.plot_tabs.currentWidget()
        tab_name = self.plot_tabs.tabText(current_index)
        
        # Get current spectrum data
        freq, spec = None, None
        
        if tab_name == "Weighted Sum":
            # For weighted sum, we'll use the combined spectrum
            # This will be calculated by update_weighted_sum logic
            # For now, just get data from first available system
            for sys_name, sys_data in self.systems.items():
                if sys_data['freq'] is not None and sys_data['spec'] is not None:
                    freq = sys_data['freq']
                    spec = sys_data['spec']
                    break
        else:
            # Find the system for this plot
            for sys_name, sys_data in self.systems.items():
                if sys_data['plot_widget'] == current_widget:
                    freq = sys_data['freq']
                    spec = sys_data['spec']
                    break
        
        if freq is None or spec is None:
            QMessageBox.information(self, "No Data", "No spectrum data available")
            return
        
        # Get X range
        try:
            x_min_str = self.x_min_edit.text().strip()
            x_max_str = self.x_max_edit.text().strip()
            
            if not x_min_str or not x_max_str:
                QMessageBox.warning(self, "Invalid Range", "Please set X min and X max first")
                return
            
            x_min = float(x_min_str)
            x_max = float(x_max_str)
            
            # Find data in X range
            mode = self.display_mode_combo.currentIndex()
            if mode == 0:  # |spec|
                y_data = np.abs(spec)
            elif mode == 1:  # Re(spec)
                y_data = np.real(spec)
            else:  # Im(spec)
                y_data = np.imag(spec)
            
            # Filter data in range
            mask = (freq >= min(x_min, x_max)) & (freq <= max(x_min, x_max))
            if np.any(mask):
                y_in_range = y_data[mask]
                y_min = float(np.min(y_in_range))
                y_max = float(np.max(y_in_range))
                
                # Add 10% margin
                margin = (y_max - y_min) * 0.1
                y_min -= margin
                y_max += margin
                
                self.y_min_edit.setText(f"{y_min:.6f}")
                self.y_max_edit.setText(f"{y_max:.6f}")
                
                self.update_current_plot()
                self.log(f"Auto Y range set: [{y_min:.6f}, {y_max:.6f}]")
            else:
                QMessageBox.warning(self, "No Data", "No data found in the specified X range")
        
        except ValueError as e:
            QMessageBox.warning(self, "Invalid Input", f"Please enter valid numbers: {e}")
    
    def get_plot_ranges(self):
        """Get current plot range settings"""
        if not hasattr(self, 'range_group') or not self.range_group.isChecked():
            return None, None, None, None
        
        def parse_opt(text):
            text = text.strip()
            if not text or text.lower() == "auto":
                return None
            try:
                return float(text)
            except:
                return None
        
        x_min = parse_opt(self.x_min_edit.text())
        x_max = parse_opt(self.x_max_edit.text())
        y_min = parse_opt(self.y_min_edit.text())
        y_max = parse_opt(self.y_max_edit.text())
        
        return x_min, x_max, y_min, y_max
    
    def update_current_plot(self):
        """Update the currently visible plot without re-running simulation"""
        current_index = self.plot_tabs.currentIndex()
        current_widget = self.plot_tabs.currentWidget()
        
        if not isinstance(current_widget, PlotWidget):
            return
        
        # Get the tab name to identify which plot to update
        tab_name = self.plot_tabs.tabText(current_index)
        
        # Check if it's a system plot or weighted sum
        if tab_name == "Weighted Sum":
            # Update weighted sum plot
            self.update_weighted_sum()
            self.log("Weighted sum plot updated")
        else:
            # It's a system plot - find the corresponding system
            system_found = False
            for sys_name, sys_data in self.systems.items():
                if sys_data['plot_widget'] == current_widget:
                    # Found the system
                    freq = sys_data['freq']
                    spec = sys_data['spec']
                    
                    if freq is not None and spec is not None:
                        self.plot_spectrum(current_widget, freq, spec, sys_name)
                        self.log(f"{sys_name} plot updated")
                        system_found = True
                    else:
                        QMessageBox.information(self, "No Data", f"{sys_name} has not been simulated yet")
                        system_found = True
                    break
            
            if not system_found:
                QMessageBox.warning(self, "Error", "Could not identify current plot")
    
    # ---------- Save & Load Methods ----------
    
    def save_parameters(self):
        """Save current parameters to file"""
        if SaveLoad is None:
            QMessageBox.warning(self, "Warning", "Save_Load module not available")
            return
        
        from PySide6.QtWidgets import QFileDialog
        import os
        
        # Get default directory
        default_dir = os.path.join(os.path.dirname(__file__), 'user_save', 'parameters')
        os.makedirs(default_dir, exist_ok=True)
        
        # Open file dialog to select save location
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Parameters",
            os.path.join(default_dir, "parameters.json"),
            "JSON Files (*.json);;All Files (*.*)"
        )
        
        if not file_path:
            return
        
        # Ensure .json extension
        if not file_path.endswith('.json'):
            file_path += '.json'
        
        try:
            # Build parameters dictionary with all systems
            file_version = config.get('FILE_FORMAT_VERSION', '2.0')
            params = {
                'version': file_version,  # Mark as multi-system version
                'systems': {}
            }
            
            # Save each system's parameters
            for sys_name in sorted(self.systems.keys()):
                tab_widget = self.systems[sys_name]['tab_widget']
                
                system_params = {
                    'isotopes': tab_widget.iso_edit.toPlainText(),
                    'j_matrix': tab_widget.j_edit.toPlainText(),
                    'weight': self.systems[sys_name]['weight'],
                    'symmetry': [
                        {
                            'group': entry['group_combo'].currentText(),
                            'spins': entry['spins_edit'].text()
                        }
                        for entry in tab_widget.sym_entry_list
                    ],
                    'variables': {
                        var: spinbox.value()
                        for var, (slider, spinbox, label) in tab_widget.var_sliders.items()
                    },
                    'approximation': tab_widget.approx_combo.currentIndex(),
                    'formalism': tab_widget.formalism_combo.currentIndex()
                }
                
                params['systems'][sys_name] = system_params
            
            # Save global settings
            params['acquisition'] = {
                'magnet': self.get_magnet_tesla(),
                'sweep': self.sweep_spin.value(),
                'npoints': self.npoints_spin.value(),
                'zerofill': self.zerofill_spin.value(),
                'use_gpu': self.gpu_check.isChecked()
            }
            
            params['window'] = {
                'type': self.window_type_combo.currentText(),
                'k': self.window_k_spin.value()
            }
            
            params['plot_settings'] = {
                'display_mode': self.display_mode_combo.currentIndex(),
                'auto_normalize': self.auto_normalize_checkbox.isChecked()
            }
            
            # Save directly to selected file path
            import json
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(params, f, ensure_ascii=False, indent=2)
            
            name = os.path.basename(file_path)
            self.log(f"Parameters saved: {name} ({len(params['systems'])} systems)")
            QMessageBox.information(self, "Success", 
                f"Parameters saved to:\n{file_path}\n\n{len(params['systems'])} systems saved")
        
        except Exception as e:
            self.log(f"<b>Error saving parameters:</b> {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to save parameters:\n{str(e)}")
    
    def load_parameters(self):
        """Load parameters from file"""
        if SaveLoad is None:
            QMessageBox.warning(self, "Warning", "Save_Load module not available")
            return
        
        from PySide6.QtWidgets import QFileDialog
        import os
        
        # Get default directory
        default_dir = os.path.join(os.path.dirname(__file__), 'user_save', 'parameters')
        if not os.path.exists(default_dir):
            default_dir = os.path.dirname(__file__)
        
        # Open file dialog to select parameter file
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Parameters",
            default_dir,
            "JSON Files (*.json);;All Files (*.*)"
        )
        
        if not file_path:
            return
        
        try:
            # Load JSON file
            with open(file_path, 'r', encoding='utf-8') as f:
                import json
                params = json.load(f)
            
            name = os.path.splitext(os.path.basename(file_path))[0]
            
            # Check version and handle accordingly
            if params.get('version') == '2.0' and 'systems' in params:
                # New multi-system format
                self._load_multi_system_params(params)
            else:
                # Legacy dual-system format
                self._load_legacy_params(params)
            
            # Load global settings
            if 'acquisition' in params:
                acq = params['acquisition']
                self.set_magnet_tesla(acq.get('magnet', 0.0))
                self.sweep_spin.setValue(acq.get('sweep', 600.0))
                self.npoints_spin.setValue(acq.get('npoints', 2000))
                self.zerofill_spin.setValue(acq.get('zerofill', 8000))
                self.gpu_check.setChecked(acq.get('use_gpu', False))
            
            # Load window function settings
            if 'window' in params:
                win = params['window']
                self.window_type_combo.setCurrentText(win.get('type', 'none (no window; first point /2)'))
                self.window_k_spin.setValue(win.get('k', 5.0))
            
            # Load plot settings
            if 'plot_settings' in params:
                plot = params['plot_settings']
                if 'display_mode' in plot:
                    self.display_mode_combo.setCurrentIndex(plot.get('display_mode', 0))
                if 'auto_normalize' in plot:
                    self.auto_normalize_checkbox.setChecked(plot.get('auto_normalize', False))
            
            self.log(f"Parameters loaded: {name}")
            QMessageBox.information(self, "Success", f"Parameters loaded from:\n{file_path}")
        
        except Exception as e:
            import traceback
            self.log(f"<b>Error loading parameters:</b> {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to load parameters:\n{str(e)}\n\n{traceback.format_exc()}")
    
    def _load_multi_system_params(self, params):
        """Load parameters in new multi-system format (v2.0)"""
        systems_data = params['systems']
        
        # Clear existing systems (except keep at least 2)
        current_systems = list(self.systems.keys())
        for sys_name in current_systems:
            if sys_name not in systems_data and len(self.systems) > 1:
                # Remove system if not in saved data
                for i in range(self.system_tabs.count()):
                    if self.system_tabs.tabText(i) == sys_name:
                        self.system_tabs.setCurrentIndex(i)
                        self.remove_current_system()
                        break
        
        # Add missing systems
        for sys_name in systems_data.keys():
            if sys_name not in self.systems:
                self.add_new_system()
                # Rename the newly added system
                new_idx = self.system_tabs.count() - 1
                self.system_tabs.setTabText(new_idx, sys_name)
                # Update dictionary key
                old_name = f"System {self.system_counter}"
                if old_name in self.systems:
                    self.systems[sys_name] = self.systems.pop(old_name)
        
        # Load each system's parameters
        for sys_name, sys_params in systems_data.items():
            if sys_name not in self.systems:
                continue
            
            tab_widget = self.systems[sys_name]['tab_widget']
            
            # Load basic inputs
            tab_widget.iso_edit.setPlainText(sys_params.get('isotopes', ''))
            tab_widget.j_edit.setPlainText(sys_params.get('j_matrix', ''))
            
            # Load weight
            if 'weight' in sys_params:
                self.systems[sys_name]['weight'] = sys_params['weight']
            
            # Clear and reload symmetry entries
            for entry_data in tab_widget.sym_entry_list[:]:
                self.remove_symmetry_entry(tab_widget, entry_data['widget'])
            
            for sym in sys_params.get('symmetry', []):
                self.add_symmetry_entry(tab_widget, sym.get('spins', ''))
                if tab_widget.sym_entry_list:
                    entry = tab_widget.sym_entry_list[-1]
                    entry['group_combo'].setCurrentText(sym.get('group', 'None'))
            
            # Parse variables to create sliders
            if sys_params.get('j_matrix'):
                self.parse_system(sys_name)
            
            # Load variable values
            if 'variables' in sys_params and tab_widget.var_sliders:
                for var_name, value in sys_params['variables'].items():
                    if var_name in tab_widget.var_sliders:
                        slider, spinbox, label = tab_widget.var_sliders[var_name]
                        spinbox.setValue(value)
                        slider.setValue(int(value * 10))
                        label.setText(f"{value:.2f} Hz")
                self.log(f"{sys_name}: Loaded {len(sys_params['variables'])} variable values")
            
            # Load basis settings
            if 'approximation' in sys_params:
                tab_widget.approx_combo.setCurrentIndex(sys_params.get('approximation', 0))
            if 'formalism' in sys_params:
                tab_widget.formalism_combo.setCurrentIndex(sys_params.get('formalism', 0))
        
        # Update weight controls after loading all systems
        self._update_weight_controls()
    
    def _load_legacy_params(self, params):
        """Load parameters in legacy dual-system format (for backward compatibility)"""
        # Map old system names to new format
        legacy_map = {'system1': 'System 1', 'system2': 'System 2'}
        
        for old_name, new_name in legacy_map.items():
            if old_name not in params:
                continue
            
            if new_name not in self.systems:
                continue
            
            sys_params = params[old_name]
            tab_widget = self.systems[new_name]['tab_widget']
            
            # Load basic inputs
            tab_widget.iso_edit.setPlainText(sys_params.get('isotopes', ''))
            tab_widget.j_edit.setPlainText(sys_params.get('j_matrix', ''))
            
            # Clear and reload symmetry entries
            for entry_data in tab_widget.sym_entry_list[:]:
                self.remove_symmetry_entry(tab_widget, entry_data['widget'])
            
            for sym in sys_params.get('symmetry', []):
                self.add_symmetry_entry(tab_widget, sym.get('spins', ''))
                if tab_widget.sym_entry_list:
                    entry = tab_widget.sym_entry_list[-1]
                    entry['group_combo'].setCurrentText(sym.get('group', 'None'))
            
            # Parse variables
            if sys_params.get('j_matrix'):
                self.parse_system(new_name)
            
            # Load variable values
            if 'variables' in sys_params and tab_widget.var_sliders:
                for var_name, value in sys_params['variables'].items():
                    if var_name in tab_widget.var_sliders:
                        slider, spinbox, label = tab_widget.var_sliders[var_name]
                        spinbox.setValue(value)
                        slider.setValue(int(value * 10))
                        label.setText(f"{value:.2f} Hz")
            
            # Load basis settings
            if 'approximation' in sys_params:
                tab_widget.approx_combo.setCurrentIndex(sys_params.get('approximation', 0))
            if 'formalism' in sys_params:
                tab_widget.formalism_combo.setCurrentIndex(sys_params.get('formalism', 0))
        
        # Update weight controls
        self._update_weight_controls()
        
        self.log("Loaded legacy dual-system parameters")
    
    def save_molecule(self, sys_name):
        """Save current molecule (isotopes, J-matrix, symmetry) for a specific system"""
        if SaveLoad is None or MoleculeData is None:
            QMessageBox.warning(self, "Warning", "Save_Load module not available")
            return
        
        if sys_name not in self.systems:
            return
        
        try:
            tab_widget = self.systems[sys_name]['tab_widget']
            
            # Get default name from isotopes
            iso_text = tab_widget.iso_edit.toPlainText().replace(',', '_').replace(' ', '_').strip()
            default_name = iso_text[:30] if iso_text else "molecule"
            
            # Custom dialog for molecule name and information
            from PySide6.QtWidgets import QDialog, QLabel, QLineEdit, QTextEdit, QPushButton, QHBoxLayout
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Save Molecule - {sys_name}")
            layout = QVBoxLayout(dialog)
            
            name_label = QLabel("Enter molecule name:")
            name_edit = QLineEdit(default_name)
            info_label = QLabel("Enter molecule information:")
            info_edit = QTextEdit()
            info_edit.setPlaceholderText("Optional: description, source, notes, etc.")
            info_edit.setMaximumHeight(80)
            
            layout.addWidget(name_label)
            layout.addWidget(name_edit)
            layout.addWidget(info_label)
            layout.addWidget(info_edit)
            
            btn_layout = QHBoxLayout()
            btn_ok = QPushButton("OK")
            btn_cancel = QPushButton("Cancel")
            btn_layout.addWidget(btn_ok)
            btn_layout.addWidget(btn_cancel)
            layout.addLayout(btn_layout)
            
            btn_ok.clicked.connect(dialog.accept)
            btn_cancel.clicked.connect(dialog.reject)
            
            if dialog.exec() != QDialog.Accepted:
                return
            
            name = name_edit.text().strip()
            info = info_edit.toPlainText()
            
            if not name:
                QMessageBox.warning(self, "Warning", "Please enter a molecule name")
                return
            
            # Parse isotopes
            isotopes_text = tab_widget.iso_edit.toPlainText()
            isotopes = [s.strip() for s in isotopes_text.replace('\n', ',').split(',') if s.strip()]
            
            if not isotopes:
                QMessageBox.warning(self, "Warning", "Please enter isotopes first")
                return
            
            n = len(isotopes)
            
            # Get J-coupling matrix
            import re
            j_matrix_text = tab_widget.j_edit.toPlainText().strip()
            
            # Parse J matrix - handle both numeric and variable-based matrices
            try:
                # Try to evaluate as literal
                import ast
                j_parsed = ast.literal_eval(j_matrix_text)
                J_coupling = np.array(j_parsed, dtype=float).tolist()
            except:
                # If it contains variables, substitute with current values
                if tab_widget.var_sliders:
                    namespace = {'np': np}
                    for var_name, (slider, spinbox, label) in tab_widget.var_sliders.items():
                        namespace[var_name] = spinbox.value()
                    
                    try:
                        J_coupling = eval(j_matrix_text, namespace)
                        J_coupling = np.array(J_coupling, dtype=float).tolist()
                    except:
                        # If still fails, create zero matrix
                        J_coupling = [[0.0] * n for _ in range(n)]
                else:
                    # Create zero matrix as fallback
                    J_coupling = [[0.0] * n for _ in range(n)]
            
            # Get symmetry groups and spins
            symmetry_group = []
            symmetry_spins = []
            
            for entry_data in tab_widget.sym_entry_list:
                group = entry_data['group_combo'].currentText()
                spins_text = entry_data['spins_edit'].text().strip()
                
                if group and group != 'None' and not group.startswith('---') and spins_text:
                    symmetry_group.append(group)
                    # Parse spins: "1,2,3" or "1 2 3"
                    spins = [int(x) for x in spins_text.replace(',', ' ').split() if x.strip().isdigit()]
                    symmetry_spins.append(spins)
            
            # Add timestamp to information
            from datetime import datetime
            save_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            info_full = f"Saved from: {sys_name}\nSaved at: {save_time}\n\n{info}"
            
            # Create MoleculeData object
            mol = MoleculeData(
                name=name,
                isotopes=isotopes,
                J_coupling=J_coupling,
                symmetry_group=symmetry_group if symmetry_group else None,
                symmetry_spins=symmetry_spins if symmetry_spins else None,
                information=info_full
            )
            
            # Save using SaveLoad
            SaveLoad.save_user_molecule(mol)
            
            self.log(f"[{sys_name}] Molecule '{name}' saved successfully")
            QMessageBox.information(self, "Success", 
                f"Molecule '{name}' saved successfully to:\nuser_save/molecules/{name}/\n\nFiles:\n- structure.csv\n- symmetry.csv\n- information.txt")
        
        except Exception as e:
            self.log(f"<b>Error saving molecule:</b> {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to save molecule:\n{str(e)}")
    
    def load_molecule(self, sys_name):
        """Load a molecule for a specific system"""
        if SaveLoad is None:
            QMessageBox.warning(self, "Warning", "Save_Load module not available")
            return
        
        if sys_name not in self.systems:
            return
        
        try:
            from PySide6.QtWidgets import QFileDialog
            import os
            
            # Get default directory
            default_dir = os.path.join(os.path.dirname(__file__), 'user_save', 'molecules')
            if not os.path.exists(default_dir):
                default_dir = os.path.join(os.path.dirname(__file__), 'presets', 'molecules')
            
            # Select molecule folder
            folder = QFileDialog.getExistingDirectory(
                self,
                f"Select Molecule Folder - {sys_name}",
                default_dir
            )
            
            if not folder:
                return
            
            # Load molecule
            structure_path = os.path.join(folder, 'structure.csv')
            symmetry_path = os.path.join(folder, 'symmetry.csv')
            
            if not os.path.exists(structure_path):
                QMessageBox.critical(self, "Error", 
                    f"structure.csv not found in:\n{folder}")
                return
            
            mol = SaveLoad.read_user_molecule(
                name=os.path.basename(folder),
                structure_path=structure_path,
                symmetry_path=symmetry_path if os.path.exists(symmetry_path) else None
            )
            
            # Fill UI fields
            tab_widget = self.systems[sys_name]['tab_widget']
            
            # Set isotopes
            tab_widget.iso_edit.setPlainText(", ".join(mol.isotopes))
            
            # Set J-matrix
            j_matrix_str = str(mol.J_coupling)
            tab_widget.j_edit.setPlainText(j_matrix_str)
            
            # Clear existing symmetry entries
            for entry_data in tab_widget.sym_entry_list[:]:
                self.remove_symmetry_entry(tab_widget, entry_data['widget'])
            
            # Add symmetry entries
            if mol.symmetry_group and mol.symmetry_spins:
                for group, spins in zip(mol.symmetry_group, mol.symmetry_spins):
                    spins_text = ', '.join(str(s) for s in spins)
                    self.add_symmetry_entry(tab_widget, spins_text)
                    
                    if tab_widget.sym_entry_list:
                        entry = tab_widget.sym_entry_list[-1]
                        # Find matching group in combo
                        idx = entry['group_combo'].findText(group)
                        if idx >= 0:
                            entry['group_combo'].setCurrentIndex(idx)
            
            # Show information if available
            if hasattr(mol, 'information') and mol.information:
                from PySide6.QtWidgets import QDialog, QLabel, QTextEdit, QPushButton
                info_dialog = QDialog(self)
                info_dialog.setWindowTitle("Molecule Information")
                info_layout = QVBoxLayout(info_dialog)
                
                info_text = QTextEdit()
                info_text.setPlainText(mol.information)
                info_text.setReadOnly(True)
                info_text.setMaximumHeight(200)
                
                close_btn = QPushButton("Close")
                close_btn.clicked.connect(info_dialog.accept)
                
                info_layout.addWidget(QLabel(f"Loaded: {os.path.basename(folder)}"))
                info_layout.addWidget(info_text)
                info_layout.addWidget(close_btn)
                
                info_dialog.exec()
            
            self.log(f"[{sys_name}] Molecule '{os.path.basename(folder)}' loaded successfully")
            QMessageBox.information(self, "Success", 
                f"Molecule loaded from:\n{folder}")
        
        except Exception as e:
            self.log(f"<b>Error loading molecule:</b> {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to load molecule:\n{str(e)}")
    
    def export_spectrum(self):
        """Export current spectrum data using file dialog"""
        if SaveLoad is None:
            QMessageBox.warning(self, "Warning", "Save_Load module not available")
            return
        
        from PySide6.QtWidgets import QDialog, QRadioButton, QDialogButtonBox, QFileDialog
        import os
        
        # Ask which system to export
        dialog = QDialog(self)
        dialog.setWindowTitle("Export Spectrum")
        layout = QVBoxLayout(dialog)
        
        layout.addWidget(QLabel("Select spectrum to export:"))
        
        # Create radio buttons for each system + weighted sum
        radio_buttons = {}
        first_radio = None
        
        for sys_name in sorted(self.systems.keys()):
            if self.systems[sys_name]['freq'] is not None:  # Only show systems with data
                radio = QRadioButton(sys_name)
                radio_buttons[sys_name] = radio
                layout.addWidget(radio)
                if first_radio is None:
                    first_radio = radio
                    radio.setChecked(True)
        
        if not radio_buttons:
            QMessageBox.warning(self, "No Data", "No systems have been simulated yet")
            return
        
        # Add weighted sum option if multiple systems
        if len(radio_buttons) > 1:
            radio_sum = QRadioButton("Weighted Sum")
            radio_buttons["Weighted Sum"] = radio_sum
            layout.addWidget(radio_sum)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec() != QDialog.Accepted:
            return
        
        # Determine which spectrum to export
        selected_sys = None
        for sys_name, radio in radio_buttons.items():
            if radio.isChecked():
                selected_sys = sys_name
                break
        
        if not selected_sys:
            return
        
        # Get spectrum data
        if selected_sys == "Weighted Sum":
            # Calculate weighted sum
            freq = None
            spec_sum = None
            total_weight = 0
            
            for sys_name in sorted(self.systems.keys()):
                if self.systems[sys_name]['freq'] is not None:
                    weight = self.systems[sys_name]['weight']
                    if freq is None:
                        freq = self.systems[sys_name]['freq']
                        spec_sum = self.systems[sys_name]['spec'] * weight
                    else:
                        spec_sum += self.systems[sys_name]['spec'] * weight
                    total_weight += weight
            
            if spec_sum is not None and total_weight > 0:
                spec = spec_sum / total_weight
            else:
                QMessageBox.warning(self, "Error", "Failed to calculate weighted sum")
                return
            
            source_sys = "Weighted Sum"
        else:
            if selected_sys not in self.systems:
                QMessageBox.warning(self, "Error", f"{selected_sys} not found")
                return
            
            freq = self.systems[selected_sys]['freq']
            spec = self.systems[selected_sys]['spec']
            source_sys = selected_sys
        
        if freq is None or spec is None:
            QMessageBox.warning(self, "Warning", f"{selected_sys} has not been computed yet")
            return
        
        # Get default directory
        default_dir = os.path.join(os.path.dirname(__file__), 'spectrum')
        os.makedirs(default_dir, exist_ok=True)
        
        # Get save directory using folder selection dialog
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Folder to Export Spectrum",
            default_dir
        )
        
        if not folder:
            return
        
        try:
            # Prepare spectrum data - include real, imag, and magnitude
            spectrum_data = [
                [float(f), float(np.real(s)), float(np.imag(s)), float(np.abs(s))]
                for f, s in zip(freq, spec)
            ]
            
            # Prepare settings
            settings = {
                'version': '2.0',
                'source': source_sys,
                'magnet': self.get_magnet_tesla(),
                'sweep': self.sweep_spin.value(),
                'npoints': int(self.npoints_spin.value()),
                'zerofill': int(self.zerofill_spin.value()),
                'window_type': self.window_type_combo.currentText(),
                'window_k': self.window_k_spin.value(),
                'use_gpu': self.gpu_check.isChecked()
            }
            
            # Add information
            from datetime import datetime
            export_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            information = f"Exported from: Multi-System Spinach UI\nSource: {source_sys}\nExported at: {export_time}"
            
            # Save to the selected folder
            spectrum_name = os.path.basename(folder)
            
            # Save setting.json
            setting_path = os.path.join(folder, 'setting.json')
            with open(setting_path, 'w', encoding='utf-8') as f:
                import json
                json.dump(settings, f, ensure_ascii=False, indent=2)
            
            # Save spectrum.csv
            spectrum_path = os.path.join(folder, 'spectrum.csv')
            with open(spectrum_path, 'w', encoding='utf-8') as f:
                f.write("Frequency,Real,Imaginary,Magnitude\n")
                for row in spectrum_data:
                    f.write(f"{row[0]},{row[1]},{row[2]},{row[3]}\n")
            
            # Save information.txt
            info_path = os.path.join(folder, 'information.txt')
            with open(info_path, 'w', encoding='utf-8') as f:
                f.write(information)
            
            self.log(f"Spectrum exported to: {folder}")
            QMessageBox.information(self, "Success", 
                f"Spectrum exported to:\n{folder}\n\nFiles:\n- setting.json\n- spectrum.csv\n- information.txt")
        
        except Exception as e:
            self.log(f"<b>Error exporting spectrum:</b> {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to export spectrum:\n{str(e)}")
    
    def load_spectrum(self):
        """Load and display spectrum from folder using file dialog"""
        if SaveLoad is None:
            QMessageBox.warning(self, "Warning", "Save_Load module not available")
            return
        
        from PySide6.QtWidgets import QFileDialog
        import os
        
        # Get default directory
        default_dir = os.path.join(os.path.dirname(__file__), 'spectrum')
        if not os.path.exists(default_dir):
            default_dir = os.path.dirname(__file__)
        
        # Select spectrum folder
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Spectrum Folder to Load",
            default_dir
        )
        
        if not folder:
            return
        
        try:
            # Load files
            setting_path = os.path.join(folder, 'setting.json')
            spectrum_path = os.path.join(folder, 'spectrum.csv')
            info_path = os.path.join(folder, 'information.txt')
            
            if not os.path.exists(setting_path) or not os.path.exists(spectrum_path):
                QMessageBox.critical(self, "Error", 
                    "Required files (setting.json or spectrum.csv) not found in:\n" + folder)
                return
            
            # Load settings
            with open(setting_path, 'r', encoding='utf-8') as f:
                import json
                settings = json.load(f)
            
            # Load spectrum data
            spectrum_data = []
            with open(spectrum_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines[1:]:  # Skip header
                    if line.strip():
                        parts = line.strip().split(',')
                        if len(parts) >= 4:
                            freq_val = float(parts[0])
                            real_val = float(parts[1])
                            imag_val = float(parts[2])
                            spectrum_data.append([freq_val, complex(real_val, imag_val)])
            
            if not spectrum_data:
                QMessageBox.warning(self, "Warning", "No spectrum data found")
                return
            
            # Parse spectrum data
            freq = np.array([row[0] for row in spectrum_data])
            spec = np.array([row[1] for row in spectrum_data])
            
            # Display in current plot tab
            current_plot = self.plot_tabs.currentWidget()
            if isinstance(current_plot, PlotWidget):
                # Store the data
                current_plot.current_x = freq
                current_plot.current_spec = spec
                
                # Determine display mode
                mode_text = self.display_mode_combo.currentText()
                if mode_text.startswith("|spec|"):
                    y_plot = np.abs(spec)
                    ylabel = "|Spectrum|"
                elif mode_text.startswith("Re"):
                    y_plot = np.real(spec)
                    ylabel = "Re{Spectrum}"
                else:
                    y_plot = np.imag(spec)
                    ylabel = "Im{Spectrum}"
                
                current_plot.current_y = y_plot
                current_plot.ylabel_text = ylabel
                current_plot.draw(freq, y_plot, "Frequency (Hz)", invert=True, title=f"Loaded: {os.path.basename(folder)}")
            
            # Load settings
            if 'magnet' in settings:
                self.set_magnet_tesla(float(settings['magnet']))
            if 'sweep' in settings:
                self.sweep_spin.setValue(float(settings['sweep']))
            if 'npoints' in settings:
                self.npoints_spin.setValue(int(settings['npoints']))
            if 'zerofill' in settings:
                self.zerofill_spin.setValue(int(settings['zerofill']))
            if 'window_type' in settings:
                self.window_type_combo.setCurrentText(settings['window_type'])
            if 'window_k' in settings:
                self.window_k_spin.setValue(float(settings['window_k']))
            if 'use_gpu' in settings:
                self.gpu_check.setChecked(bool(settings['use_gpu']))
            
            # Load and display information if available
            if os.path.exists(info_path):
                with open(info_path, 'r', encoding='utf-8') as f:
                    information = f.read()
                    
                from PySide6.QtWidgets import QDialog, QTextEdit, QPushButton
                info_dialog = QDialog(self)
                info_dialog.setWindowTitle("Spectrum Information")
                info_layout = QVBoxLayout(info_dialog)
                
                info_text = QTextEdit()
                info_text.setPlainText(information)
                info_text.setReadOnly(True)
                info_text.setMaximumHeight(150)
                
                close_btn = QPushButton("Close")
                close_btn.clicked.connect(info_dialog.accept)
                
                info_layout.addWidget(QLabel(f"Loaded: {os.path.basename(folder)}"))
                info_layout.addWidget(info_text)
                info_layout.addWidget(close_btn)
                
                info_dialog.exec()
            
            self.log(f"Spectrum loaded from: {os.path.basename(folder)}")
            QMessageBox.information(self, "Success", 
                f"Spectrum loaded from:\n{folder}")
        
        except Exception as e:
            self.log(f"<b>Error loading spectrum:</b> {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to load spectrum:\n{str(e)}")
    
    def restart_matlab(self):
        """Restart MATLAB engine"""
        try:
            self.log("Restarting MATLAB engine...")
            ENGINE.start(clean=True)
            self.log("MATLAB engine restarted successfully!")
        except Exception as e:
            self.log(f"<b>Error restarting MATLAB:</b> {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to restart MATLAB:\n{str(e)}")
    
    def closeEvent(self, event):
        """Clean up on close"""
        # Stop all running workers
        for sys_name, sys_data in self.systems.items():
            worker = sys_data.get('worker')
            if worker and worker.isRunning():
                worker.terminate()
                worker.wait()
        
        # Stop MATLAB engine
        try:
            ENGINE.stop()
        except:
            pass
        
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    
    # Start MATLAB engine
    try:
        ENGINE.start(clean=True)
        print("MATLAB engine started successfully!")
    except Exception as e:
        QMessageBox.critical(None, "Error", f"Failed to start MATLAB:\n{str(e)}")
        return
    
    window = MultiSystemSpinachUI()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
