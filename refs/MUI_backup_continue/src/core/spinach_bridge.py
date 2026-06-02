from __future__ import annotations
import numpy as np
import matlab.engine, matlab
from contextlib import contextmanager
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

# Global MATLAB engine instance (kept alive after initialization)
_global_matlab_engine = None

def get_global_engine():
    """Get the global MATLAB engine instance"""
    return _global_matlab_engine

def set_global_engine(engine):
    """Set the global MATLAB engine instance"""
    global _global_matlab_engine
    _global_matlab_engine = engine

def np_to_mat(value: Any):
    """Convert common Python/NumPy types to MATLAB Engine types.
    NOTE: MATLAB Engine has no `matlab.cell`. String-list -> cell is handled in `push()`."""
    if isinstance(value, np.ndarray):
        # NumPy array -> matlab.double; complex arrays are handled as (re, im, True)
        if np.iscomplexobj(value):
            re = matlab.double(np.asarray(value.real, order="C").tolist())
            im = matlab.double(np.asarray(value.imag, order="C").tolist())
            # Caller (push) will recombine in MATLAB: name = complex(name_re, name_im)
            return re, im, True
        else:
            return matlab.double(np.asarray(value, order="C").tolist())

    elif isinstance(value, (list, tuple)):
        # Numeric list -> double row vector
        if all(isinstance(x, (int, float, np.floating)) for x in value):
            return matlab.double([list(map(float, value))])
        else:
            # Try best-effort numeric conversion; otherwise return original for caller handling
            try:
                return matlab.double(np.asarray(value, dtype=float).tolist())
            except Exception:
                return value

    elif isinstance(value, (int, float, np.floating)):
        # Python scalar -> MATLAB double
        return float(value)

    elif isinstance(value, str):
        # Python str -> MATLAB char vector
        return value

    else:
        # Unknown type -> let caller decide (e.g., push_struct will recurse or raise)
        return value
    

def start_spinach_eng(clean: bool = True):
    eng = matlab.engine.start_matlab()
    if clean:
        eng.eval("clear all", nargout=0)
    return eng

@contextmanager
def spinach_eng(clean: bool = True):
    eng = start_spinach_eng(clean=clean)
    try:
        yield eng
    finally:
        eng.quit()

class call_spinach:
    """
    Generic Python wrapper around common Spinach functions.
    You can call Spinach functions either via helpers here or via .call()/.feval().
    """

    default_eng = None

    def __init__(self, eng=None, var_prefix=''):
        if eng is None:
            self.eng = call_spinach.default_eng
        else:
            self.eng = eng
        self.var_prefix = var_prefix

    # --- GPU activation ---
    def use_gpu(self, activate: bool = True):
        """
        Try to select and activate a GPU device in MATLAB if activate is True.
        If no GPU is available, show a warning.
        """
        if activate:
            self.eng.eval("""
            try
                gpuDevice;
                disp('GPU detected and set as default device.');
            catch
                warning('No compatible GPU found.');
            end
            """, nargout=0)


    # --- Low-level generic callers ---
    def call(self, code: str, nargout: int = 0):
        """
        Execute arbitrary MATLAB code string in base workspace.
        Use nargout=0 for statements; >0 only for expressions returning values.
        """
        return self.eng.eval(code, nargout=nargout)

    def feval(self, func: str, *args, nargout: int = 1):
        """
        Call a MATLAB function by name with given arguments (already converted).
        Prefer this over .call() when possible.
        """
        return self.eng.feval(func, *args, nargout=nargout)

    # --- Push helpers ---
    def push(self, name: str, value: Any):
        """
        Push a Python value to MATLAB base workspace under variable `name`.
        Special cases:
          - list/tuple of strings -> MATLAB cell array literal {'a','b',...}
          - complex arrays come as (re, im, True) from np_to_mat(...) and are recombined here
        """
        # Special-case: list/tuple of strings -> build a MATLAB cell literal
        if isinstance(value, (list, tuple)) and all(isinstance(x, str) for x in value):
            # Escape single quotes inside each string
            cell_lit = "{" + ",".join("'" + s.replace("'", "''") + "'" for s in value) + "}"
            self.eng.eval(f"{name} = {cell_lit};", nargout=0)
            return

        conv = np_to_mat(value)

        # Complex array branch: conv == (re, im, True)
        if isinstance(conv, tuple) and len(conv) == 3 and conv[2] is True:
            re, im, _ = conv
            self.eng.workspace[name + "_re"] = re
            self.eng.workspace[name + "_im"] = im
            self.eng.eval(f"{name} = complex({name}_re, {name}_im);", nargout=0)
            # Optional cleanup:
            self.eng.eval(f"clear {name}_re {name}_im;", nargout=0)
            return

        # Default branch: direct assignment (matlab.double, float, str, etc.)
        self.eng.workspace[name] = conv

    def push_cellstr(self, name: str, strings: Sequence[str]):
        """Create a MATLAB cell array of char vectors named `name`."""
        # Escape single quotes and build MATLAB literal: {'a','b','c'}
        cell_lit = "{" + ",".join("'" + s.replace("'", "''") + "'" for s in strings) + "}"
        matlab_code = f"{name} = {cell_lit};"
        print(f"DEBUG spinach_bridge.push_cellstr() generating MATLAB code: {matlab_code}")
        self.eng.eval(matlab_code, nargout=0)

    def push_struct(self, name: str, mapping: Dict[str, Any]):
        """
        Create/update a MATLAB struct with scalar/array/cell fields from a Python dict.
        Nested dicts are supported recursively.
        """
        self.eng.eval(f"{name} = struct();", nargout=0)
        for k, v in mapping.items():
            if isinstance(v, dict):
                sub = f"{name}.{k}"
                self.push_struct(sub, v)
            else:
                self.push(k, v)
                self.eng.eval(f"{name}.{k} = {k};", nargout=0)
                self.eng.eval(f"clear {k};", nargout=0)

class sys(call_spinach):

    def __init__(self, eng=None, var_prefix=''):
        super().__init__(eng, var_prefix)
        self.var_name = f"{var_prefix}sys" if var_prefix else "sys"

    def isotopes(self, isotopes: Sequence[str]):
        iso_cell = "{" + ",".join([f"'{s}'" for s in isotopes]) + "}"
        self.eng.eval(f"{self.var_name}.isotopes = {iso_cell};", nargout=0)

    def magnet(self, value: float):
        self.eng.eval(f"{self.var_name}.magnet = {value};", nargout=0)

class bas(call_spinach):

    def __init__(self, eng=None, var_prefix=''):
        super().__init__(eng, var_prefix)
        self.var_name = f"{var_prefix}bas" if var_prefix else "bas"

    def formalism(self, formalism: str):
        self.eng.eval(f"{self.var_name}.formalism = '{formalism}';", nargout=0)
    
    def approximation(self, approximation):
        self.eng.eval(f"{self.var_name}.approximation = '{approximation}';", nargout=0)

    def sym_group(self, sym_group):
        print(f"DEBUG spinach_bridge.sym_group() called with: {sym_group} (type: {type(sym_group)})")
        if isinstance(sym_group, (list, tuple)):
            self.push_cellstr(f'{self.var_name}.sym_group', sym_group)
        else:
            self.push_cellstr(f'{self.var_name}.sym_group', [str(sym_group)])

    def sym_spins(self, groups: Sequence[Sequence[int]]):
        """
        Python list
        """
        print(f"DEBUG spinach_bridge.sym_spins() called with: {groups} (type: {type(groups)})")
        def group_to_matlab_vec(g):
            return "[" + " ".join(str(i) for i in g) + "]"
        cell_str = "{" + ",".join(group_to_matlab_vec(g) for g in groups) + "}"
        print(f"DEBUG spinach_bridge.sym_spins() generating MATLAB code: {self.var_name}.sym_spins = {cell_str};")
        self.eng.eval(f"{self.var_name}.sym_spins = {cell_str};", nargout=0)

class parameters(call_spinach):

    def __init__(self, eng=None, var_prefix=''):
        super().__init__(eng, var_prefix)
        self.var_name = f"{var_prefix}parameters" if var_prefix else "parameters"

    def params(
        self,
        sweep: float,
        npoints: int,
        zerofill: int,
        offset: float,
        spins: Sequence[str],
        axis_units: str,
        invert_axis: int,
        flip_angle: float,
        detection: str,
        extra: Optional[Dict[str, Any]],
    ):
        param = dict(
            sweep=float(sweep),
            npoints=int(npoints),
            zerofill=int(zerofill),
            offset=float(offset),
            spins=list(spins),
            axis_units=str(axis_units),
            invert_axis=int(invert_axis),
            flip_angle=float(flip_angle),
            detection=str(detection),
        )
        if extra:
            param.update(extra)
        self.push_struct(self.var_name, param)

    #tools
    def _ensure(self):
        self.eng.eval(
            f"if ~exist('{self.var_name}','var') || ~isstruct({self.var_name}), {self.var_name} = struct(); end",
            nargout=0
        )

    @staticmethod
    def _q(s: str) -> str:
        return "'" + str(s).replace("'", "''") + "'"
    
    def _field(self, key: str) -> str:
        k = str(key).replace("'", "''")   
        return f"{self.var_name}.('{k}')"      

    @classmethod
    def _encode(cls, v: Any) -> str:
        import numbers
        from collections.abc import Sequence as Seq
        if isinstance(v, bool): return "true" if v else "false"
        if isinstance(v, numbers.Integral): return str(int(v))
        if isinstance(v, numbers.Real): return repr(float(v))
        if isinstance(v, str): return cls._q(v)
        if isinstance(v, Seq) and not isinstance(v, (str, bytes, bytearray)):
            try:
                if all(isinstance(x, numbers.Real) and not isinstance(x, bool) for x in v):
                    return "[" + " ".join(repr(float(x)) for x in v) + "]"
                if all(isinstance(x, str) for x in v):
                    return "{" + ",".join(cls._q(x) for x in v) + "}"
            except TypeError:
                pass
        raise TypeError(f"Unsupported value for MATLAB encoding: {type(v).__name__}")

    def sweep(self, value: float):
        self._ensure()
        self.eng.eval(f"{self.var_name}.sweep = {float(value)};", nargout=0)

    def npoints(self, value: int):
        self._ensure()
        self.eng.eval(f"{self.var_name}.npoints = {int(value)};", nargout=0)

    def zerofill(self, value: int):
        self._ensure()
        self.eng.eval(f"{self.var_name}.zerofill = {int(value)};", nargout=0)

    def offset(self, value: float):
        self._ensure()
        self.eng.eval(f"{self.var_name}.offset = {float(value)};", nargout=0)

    def spins(self, spins: Sequence[str]):
        self._ensure()
        cell_lit = "{" + ",".join(self._q(s) for s in spins) + "}"
        self.eng.eval(f"{self.var_name}.spins = {cell_lit};", nargout=0)

    def axis_units(self, units: str):
        self._ensure()
        self.eng.eval(f"{self.var_name}.axis_units = {self._q(units)};", nargout=0)

    def invert_axis(self, value: int | bool):
        self._ensure()
        iv = 1 if bool(value) else 0
        self.eng.eval(f"{self.var_name}.invert_axis = {iv};", nargout=0)

    def flip_angle(self, value: float):
        self._ensure()
        self.eng.eval(f"{self.var_name}.flip_angle = {float(value)};", nargout=0)

    def detection(self, mode: str):
        self._ensure()
        self.eng.eval(f"{self.var_name}.detection = {self._q(mode)};", nargout=0)

    def extra(self, kv: Dict[str, Any]):
        self._ensure()
        for k, v in kv.items():
            rhs = self._encode(v)
            self.eng.eval(f"{self._field(k)} = {rhs};", nargout=0)

    def set(self, key: str, value: Any):
        self._ensure()
        rhs = self._encode(value)
        self.eng.eval(f"{self._field(key)} = {rhs};", nargout=0)

class inter(call_spinach):

    def __init__(self, eng=None, var_prefix=''):
        super().__init__(eng, var_prefix)
        self.var_name = f"{var_prefix}inter" if var_prefix else "inter"

    def zeeman(self, values: Sequence[Optional[float]]):
        items = []
        for v in values:
            if v is None:
                items.append("0.0")
            else:
                items.append(repr(float(v)))
        cell_lit = "{" + " ".join(items) + "}"
        self.eng.eval(f"{self.var_name}.zeeman.scalar = {cell_lit};", nargout=0)

    def temperature(self, value: float):
        self.eng.eval(f"{self.var_name}.temperature = {float(value)};", nargout=0)

    def coupling(self, kind: str, value):
        self.push('C_tmp', value)
        self.eng.eval(f"{self.var_name}.coupling.{kind} = C_tmp;", nargout=0)
        self.eng.eval("clear C_tmp;", nargout=0)
    
    def coupling_array(self, J, validate: bool = True, empty_diagonal: bool = True, use_gpu: bool = False):
        """
        Push a coupling matrix to MATLAB and configure inter.coupling.scalar.
        If use_gpu is True, use GPU for matrix operations.
        """
        import numpy as _np
        arr = _np.asarray(J, dtype=float)
        if arr.ndim != 2 or arr.shape[0] != arr.shape[1]:
            raise ValueError(f"J must be a square 2D array; got shape {arr.shape}")

        if validate:
            try:
                nspins = int(self.eng.eval(f"numel({self.var_name.replace('inter', 'sys')}.isotopes);", nargout=1))
                if arr.shape[0] != nspins:
                    raise ValueError(
                        f"J size {arr.shape[0]}×{arr.shape[1]} does not match numel(sys.isotopes)={nspins}"
                    )
            except Exception:
                pass

        tmp_var = f"{self.var_prefix}J_tmp" if self.var_prefix else "J_tmp"
        self.push(tmp_var, arr)
        if use_gpu:
            self.use_gpu(True)
            self.eng.eval(f"{tmp_var} = gpuArray({tmp_var});", nargout=0)
        self.eng.eval(f"""
            {self.var_name}.coupling.scalar = num2cell({tmp_var});
        """, nargout=0)
        if empty_diagonal:
            self.eng.eval(f"""
                for k = 1:size({tmp_var},1)
                    {self.var_name}.coupling.scalar{{k,k}} = [];
                end
            """, nargout=0)

        self.eng.eval(f"clear {tmp_var};", nargout=0)

class sim(call_spinach):

    def __init__(self, eng=None, var_prefix=''):
        super().__init__(eng, var_prefix)
        self.var_name = f"{var_prefix}spin_system" if var_prefix else "spin_system"

    def create(self):
        sys_name = f"{self.var_prefix}sys" if self.var_prefix else "sys"
        inter_name = f"{self.var_prefix}inter" if self.var_prefix else "inter"
        bas_name = f"{self.var_prefix}bas" if self.var_prefix else "bas"
        build_name = f"{self.var_prefix}py_build" if self.var_prefix else "py_build"
        
        self.eng.eval(f"{build_name} = @(sys,inter,bas) basis(create(sys,inter), bas);", nargout=0)
        self.eng.eval(f"{self.var_name} = {build_name}({sys_name}, {inter_name}, {bas_name});", nargout=0)

    def liquid(self, pulse_sequence: str, assumptions: str):
        ps = pulse_sequence.strip()
        if not ps.startswith('@'):
            ps = '@' + ps
        esc = assumptions.replace("'", "''")
        par_name = f"{self.var_prefix}parameters" if self.var_prefix else "parameters"
        liquid_name = f"{self.var_prefix}py_liquid" if self.var_prefix else "py_liquid"
        fid_name = f"{self.var_prefix}fid" if self.var_prefix else "fid"
        
        self.eng.eval(f"{liquid_name} = @(ss,par) liquid(ss, {ps}, par, '{esc}');", nargout=0)
        self.eng.eval(f"{fid_name} = {liquid_name}({self.var_name}, {par_name});", nargout=0)

class data(call_spinach):

    def __init__(self, eng=None, var_prefix=''):
        super().__init__(eng, var_prefix)
        self.var_name = f"{var_prefix}fid" if var_prefix else "fid"

    def apodisation(self, winfuns, use_gpu: bool = False):
        """
        Apply apodisation window function to FID. If use_gpu is True, use GPU for calculation.
        """
        if isinstance(winfuns, (str, tuple)):
            winfuns = [winfuns]

        parts = []
        for item in winfuns:
            if isinstance(item, str):
                wname = item.replace("'", "''")
                parts.append("{'" + wname + "'}")
            elif isinstance(item, (list, tuple)):
                if len(item) == 1:
                    wname = str(item[0]).replace("'", "''")
                    parts.append("{'" + wname + "'}")
                elif len(item) == 2 and item[1] is not None:
                    wname = str(item[0]).replace("'", "''")
                    parts.append("{'" + wname + "', " + repr(float(item[1])) + "}")
                else:
                    raise ValueError(f"Invalid window spec: {item}")
            else:
                raise TypeError(f"Invalid window type: {type(item).__name__}")

        win_literal = "{" + ",".join(parts) + "}"
        spin_sys_name = f"{self.var_prefix}spin_system" if self.var_prefix else "spin_system"
        fid_apod_name = f"{self.var_prefix}fid_apod" if self.var_prefix else "fid_apod"
        
        if use_gpu:
            self.use_gpu(True)
            self.eng.eval(f"{fid_apod_name} = apodisation({spin_sys_name}, gpuArray({self.var_name}-mean({self.var_name})), {win_literal});", nargout=0)
            self.eng.eval(f"{fid_apod_name} = gather({fid_apod_name});", nargout=0)
        else:
            self.eng.eval(f"{fid_apod_name} = apodisation({spin_sys_name}, {self.var_name}-mean({self.var_name}), {win_literal});", nargout=0)

    def p_complex(self, varname: str):
        """
        Convert MATLAB complex variable to numpy complex array.
        """
        self.eng.eval(f"{varname}_re = real({varname}); {varname}_im = imag({varname});", nargout=0)
        re = np.asarray(self.eng.workspace[f"{varname}_re"]).squeeze()
        im = np.asarray(self.eng.workspace[f"{varname}_im"]).squeeze()
        self.eng.eval(f"clear {varname}_re {varname}_im;", nargout=0)
        return re + 1j * im

    def FID(self):
        """
        Get FID as numpy complex array.
        """
        fid_np = self.p_complex(self.var_name)
        return fid_np

    def spectrum(self, use_gpu: bool = False):
        """
        Calculate spectrum using FFT. If use_gpu is True, use GPU for calculation.
        Uses fid_apod if available (from apodisation), otherwise uses original fid.
        """
        spec_name = f"{self.var_prefix}spec" if self.var_prefix else "spec"
        self.eng.eval(f"clear {spec_name};", nargout=0)
        
        # Check if fid_apod exists (from apodisation), otherwise use fid
        fid_apod_name = f"{self.var_prefix}fid_apod" if self.var_prefix else "fid_apod"
        has_apod = bool(self.eng.eval(f"exist('{fid_apod_name}', 'var');", nargout=1))
        fid_var = fid_apod_name if has_apod else self.var_name
        
        par_name = f"{self.var_prefix}parameters" if self.var_prefix else "parameters"
        
        if use_gpu:
            self.use_gpu(True)
            self.eng.eval(f"{spec_name} = fftshift(fft(gpuArray({fid_var}), {par_name}.zerofill));", nargout=0)
            self.eng.eval(f"{spec_name} = gather({spec_name});", nargout=0)
        else:
            self.eng.eval(f"{spec_name} = fftshift(fft({fid_var}, {par_name}.zerofill));", nargout=0)
        spectrum_np = self.p_complex(spec_name)
        return spectrum_np
        
    def freq(self, spectrum):
        """
        Calculate frequency axis for the spectrum.
        """
        N = spectrum.size
        par_name = f"{self.var_prefix}parameters" if self.var_prefix else "parameters"
        sweep = float(self.eng.eval(f"{par_name}.sweep;", nargout=1))
        offset = float(self.eng.eval(f"{par_name}.offset;", nargout=1))
        df = sweep / N
        frequency = np.linspace(-sweep/2, sweep/2 - df, N) + offset 
        return frequency
    









