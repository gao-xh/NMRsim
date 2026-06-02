"""ZULF / low-field 1D sequences.

Layer 5 (v0.6) — three named sequences:

- ``zulf_pulse_acquire`` — prepolarized → free evolution → Mx detection.
- ``zulf_j_spectrum``    — convenience wrapper with a long, narrow-bandwidth
                           acquisition pre-set for J-spectrum work.
- ``zulf_dc_pulse_acquire`` — apply a finite DC pulse on one channel,
                              then acquire. The static Hamiltonian is
                              kept during the pulse (γB ≈ J in ZULF, so
                              the ideal hard-pulse limit is unreliable).

All three return a standard `SimulationResult`. The regime is typically
`ZULF()` (true zero field) or `LF(B0_T=...)` (small bias field, lab
frame); both share the project-wide default convention of z-polarized
preparation and z-axis detection. Callers may override `initial` and
`detect` to study other preparation / detection schemes.
"""
from __future__ import annotations

from typing import Optional, Union

import numpy as np

from src.core import isotopes as iso_table
from src.core.acquisition import Acquisition, default_acq_ZULF
from src.core.detection import detect_Mx, detect_Mz
from src.core.engine import acquire as _acquire
from src.core.pulses import apply_unitary, pulse, pulse_with_evolution
from src.core.regime import Regime, ZULF
from src.core.simulate import SimulationResult, finalize_fid
from src.core.states import prepolarized_x, prepolarized_z
from src.core.system import SpinSystem


InitialSpec = Union[str, np.ndarray]
DetectSpec = Union[str, np.ndarray]


def _resolve_initial(sys: SpinSystem, regime: Regime, initial: InitialSpec) -> np.ndarray:
    if isinstance(initial, np.ndarray):
        return initial
    if initial == 'x':
        return prepolarized_x(sys)
    if initial == 'z':
        return prepolarized_z(sys)
    if initial == 'regime':
        return regime.initial_state(sys)
    raise ValueError(f"Unknown initial spec: {initial!r} (use 'x', 'z', 'regime', or ndarray)")


def _resolve_detect(sys: SpinSystem, regime: Regime, detect: DetectSpec) -> np.ndarray:
    if isinstance(detect, np.ndarray):
        return detect
    if detect == 'Mx':
        return detect_Mx(sys, weighted=True)
    if detect == 'Mz':
        return detect_Mz(sys, weighted=True)
    if detect == 'regime':
        return regime.detector(sys)
    raise ValueError(f"Unknown detect spec: {detect!r} (use 'Mx', 'Mz', 'regime', or ndarray)")


# ---------------------------------------------------------------------------
# zulf_pulse_acquire
# ---------------------------------------------------------------------------

def zulf_pulse_acquire(sys: SpinSystem,
                       regime: Regime,
                       acq: Acquisition,
                       *,
                       initial: InitialSpec = 'regime',
                       detect: DetectSpec = 'regime') -> SimulationResult:
    """Prepolarized ZULF pulse-acquire (no RF pulse).

    Pipeline: ρ₀ → free evolution under ``regime.hamiltonian(sys)`` for
    the acquisition window → detector trace gives FID.

    Defaults follow the regime's axis convention. For `ZULF()` / `LF()`
    that means z-polarized preparation and z-axis detection; use
    ``initial='x'`` and/or ``detect='Mx'`` explicitly when you want a
    transverse-prepared experiment.
    """
    H    = regime.hamiltonian(sys)
    rho0 = _resolve_initial(sys, regime, initial)
    det  = _resolve_detect(sys, regime, detect)

    f = _acquire(H, rho0, det, acq)
    return finalize_fid(f, acq, regime)


# ---------------------------------------------------------------------------
# zulf_j_spectrum
# ---------------------------------------------------------------------------

def zulf_j_spectrum(sys: SpinSystem,
                    regime: Optional[Regime] = None,
                    acq: Optional[Acquisition] = None,
                    *,
                    BW_Hz: float = 200.0,
                    T_s: float = 10.0,
                    t2_star: float = 2.0,
                    lb_Hz: float = 0.5,
                    initial: InitialSpec = 'regime',
                    detect: DetectSpec = 'regime') -> SimulationResult:
    """ZULF J-spectroscopy — long-AQ pulse-acquire with narrow bandwidth.

    Convenience wrapper around :func:`zulf_pulse_acquire`. Defaults match
    typical pyridine / acetonitrile J-spectra (200 Hz BW, 10 s AQ,
    0.5 Hz exponential broadening). Pass explicit ``regime``/``acq`` to
    override.
    """
    if regime is None:
        regime = ZULF()
    if acq is None:
        acq = default_acq_ZULF(BW_Hz=BW_Hz, T_s=T_s, t2_star=t2_star).with_(
            apodization='exponential', lb_Hz=lb_Hz,
        )
    return zulf_pulse_acquire(sys, regime, acq, initial=initial, detect=detect)


# ---------------------------------------------------------------------------
# zulf_dc_pulse_acquire
# ---------------------------------------------------------------------------

def zulf_dc_pulse_acquire(sys: SpinSystem,
                          regime: Regime,
                          acq: Acquisition,
                          *,
                          channel: str,
                          B_T: Optional[float] = None,
                          duration_s: Optional[float] = None,
                          flip_angle: Optional[float] = None,
                          phase: float = 0.0,
                          initial: InitialSpec = 'regime',
                          detect: DetectSpec = 'regime',
                          ideal: bool = False) -> SimulationResult:
    """ZULF DC-pulse acquire: prepolarize → DC pulse on `channel` → acquire.

    The pulse is specified in one of two ways:

    * Physical knobs ``B_T`` (field amplitude, Tesla) and ``duration_s``
      (pulse length, seconds). The flip angle is then
      ``|γ(channel)| · B_T · duration_s`` rad.
    * Flip angle ``flip_angle`` (rad). The pulse field is treated as a
      hard pulse (zero duration, infinitely large B) — i.e. ``ideal=True``
      is implied.

    If both are provided, ``flip_angle`` wins (back-compatible shortcut).

    ``ideal`` (default False): when True, even the physical-knob path
    uses the hard-pulse limit (no static-H evolution during the pulse).
    Set True for sanity checks; the default keeps the static Hamiltonian,
    which is what reality does in ZULF.

    Parameters
    ----------
    channel : isotope label, e.g. '1H' or '13C'.
    phase   : pulse phase in radians (0 = +x, π/2 = +y).
    initial : default 'regime' (z for `ZULF()` / `LF()`).
    detect  : default 'regime' (Mz for `ZULF()` / `LF()`).
    """
    if flip_angle is None and (B_T is None or duration_s is None):
        raise ValueError(
            "zulf_dc_pulse_acquire requires either `flip_angle` or both "
            "`B_T` and `duration_s`."
        )

    H    = regime.hamiltonian(sys)
    rho0 = _resolve_initial(sys, regime, initial)
    det  = _resolve_detect(sys, regime, detect)

    if flip_angle is not None:
        # Ideal hard-pulse shortcut.
        U = pulse(sys, channel, flip_angle, phase)
    elif ideal:
        gamma_abs = abs(iso_table.gamma_rad_per_s_per_T(channel))
        angle = gamma_abs * B_T * duration_s
        U = pulse(sys, channel, angle, phase)
    else:
        U = pulse_with_evolution(sys, channel, B_T, duration_s, H, phase=phase)

    rho = apply_unitary(rho0, U)
    f = _acquire(H, rho, det, acq)
    return finalize_fid(f, acq, regime)
