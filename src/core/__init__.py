"""NMRsim core: Hilbert-space NMR engine shared by high-field and ZULF.

Quick start
-----------
    from src.core import SpinSystem, H_rotating, thermal_high_temp, detect_Iplus
    from src.core import fid, fft_spectrum, freq_to_ppm
    from src.core.isotopes import larmor_Hz

    sys = SpinSystem(
        isotopes=['1H', '1H'],
        shifts_ppm=[1.0, 3.0],
        J_Hz=[[0, 7.0], [7.0, 0]],
    )
    B0 = 9.4
    H = H_rotating(sys, B0_T=B0, observed='1H', carrier_ppm=2.0)
    rho0 = thermal_high_temp(sys, observed='1H')
    O = detect_Iplus(sys, observed='1H')
    f = fid(H, rho0, O, n_points=8192, dt=1/4000, t2_star=0.5)
    freq, spec = fft_spectrum(f, dt=1/4000, zero_fill=2)
    ppm = freq_to_ppm(freq, larmor_Hz('1H', B0), carrier_ppm=2.0)
"""
from .system import SpinSystem
from .hamiltonian import H_J_only, H_lab, H_rotating
from .states import thermal_high_temp, prepolarized_x
from .detection import detect_Iplus, detect_Mx, detect_Mz
from .engine import fid, stick_spectrum, EigenSystem
from .processing import (
    apodize_exponential,
    apodize_gaussian,
    fft_spectrum,
    freq_to_ppm,
)

__all__ = [
    "SpinSystem",
    "H_J_only", "H_lab", "H_rotating",
    "thermal_high_temp", "prepolarized_x",
    "detect_Iplus", "detect_Mx", "detect_Mz",
    "fid", "stick_spectrum", "EigenSystem",
    "apodize_exponential", "apodize_gaussian",
    "fft_spectrum", "freq_to_ppm",
]
