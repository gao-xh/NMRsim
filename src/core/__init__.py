"""NMRsim core: Hilbert-space NMR engine shared by high-field and ZULF.

Quick start (recommended: parameter objects, no loose numbers)
--------------------------------------------------------------
    from src.core import SpinSystem, HF, ZULF, Acquisition, simulate

    sys = SpinSystem(
        isotopes=['1H', '1H'],
        shifts_ppm=[1.0, 3.0],
        J_Hz=[[0, 7.0], [7.0, 0]],
    )

    # All experimental knobs live in two objects:
    regime = HF(B0_T=9.4, observed='1H', carrier_ppm=2.0)   # or ZULF(), LF(B0_T=...)
    acq    = Acquisition.from_sw_aq(SW_Hz=4000, AQ_s=2.0, t2_star=0.5, zero_fill=2)

    result = simulate(sys, regime, acq)
    # result.fid, result.freq_Hz, result.spectrum, result.ppm

Low-level API (kept for advanced use)
-------------------------------------
    from src.core import H_rotating, thermal_high_temp, detect_Iplus, fid
"""
from .system import SpinSystem
from .hamiltonian import H_J_only, H_lab, H_rotating
from .states import thermal_high_temp, prepolarized_x
from .detection import detect_Iplus, detect_Mx, detect_Mz
from .engine import fid, stick_spectrum, EigenSystem, acquire
from .processing import (
    apodize_exponential,
    apodize_gaussian,
    fft_spectrum,
    freq_to_ppm,
)
from .regime import Regime, HF, ZULF, LF
from .acquisition import (
    Acquisition,
    default_acq_HF_1H,
    default_acq_HF_13C,
    default_acq_ZULF,
)
from .pulses import (
    pulse, pulse_x, pulse_y,
    propagator, evolve, apply_unitary,
)
from .simulate import simulate, SimulationResult

__all__ = [
    "SpinSystem",
    "H_J_only", "H_lab", "H_rotating",
    "thermal_high_temp", "prepolarized_x",
    "detect_Iplus", "detect_Mx", "detect_Mz",
    "fid", "stick_spectrum", "EigenSystem", "acquire",
    "apodize_exponential", "apodize_gaussian",
    "fft_spectrum", "freq_to_ppm",
    "Regime", "HF", "ZULF", "LF",
    "Acquisition",
    "default_acq_HF_1H", "default_acq_HF_13C", "default_acq_ZULF",
    "pulse", "pulse_x", "pulse_y",
    "propagator", "evolve", "apply_unitary",
    "simulate", "SimulationResult",
]
