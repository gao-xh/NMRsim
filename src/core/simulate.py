"""High-level convenience: one call that goes from (system, regime, acquisition)
to a ready-to-plot spectrum.

This is the recommended entry point for scripts and the UI. It exists so
no caller has to repeat the (build H → build ρ₀ → build det → fid →
apodize → fft → axis) boilerplate, and so future changes to the pipeline
(relaxation, sequence support, etc.) only need to be wired here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from .acquisition import Acquisition
from .engine import acquire as _acquire
from .processing import (
    apodize_exponential,
    apodize_gaussian,
    fft_spectrum,
    freq_to_ppm,
)
from .regime import Regime
from .system import SpinSystem


@dataclass(frozen=True)
class SimulationResult:
    """Output of a simulate(...) call."""
    fid: np.ndarray              # complex (n_points,)
    freq_Hz: np.ndarray          # real (n_zero_filled,)
    spectrum: np.ndarray         # complex (n_zero_filled,)
    ppm: Optional[np.ndarray]    # only set for HF regimes; else None
    regime: Regime
    acquisition: Acquisition


def simulate(sys: SpinSystem,
             regime: Regime,
             acq: Acquisition) -> SimulationResult:
    """Run a 1D pulse-acquire simulation.

    Equivalent to `regime.hamiltonian / initial_state / detector` →
    `fid` → apodize → fft → convert axis.
    """
    H    = regime.hamiltonian(sys)
    rho0 = regime.initial_state(sys)
    det  = regime.detector(sys)

    f = _acquire(H, rho0, det, acq)

    if acq.apodization == "exponential":
        f = apodize_exponential(f, acq.lb_Hz, acq.dt)
    elif acq.apodization == "gaussian":
        f = apodize_gaussian(f, acq.gb_Hz, acq.dt)
    elif acq.apodization != "none":
        raise ValueError(f"Unknown apodization: {acq.apodization!r}")

    freq, spec = fft_spectrum(f, dt=acq.dt,
                              zero_fill=acq.zero_fill,
                              half_first=acq.half_first)

    ppm = None
    if regime.display_unit == "ppm":
        nu0 = regime.larmor_Hz()
        if nu0 != 0.0:
            carrier_ppm = 0.0  # offset axis is already relative to carrier in HF rotating frame
            ppm = freq_to_ppm(freq, nu0, carrier_ppm=carrier_ppm)

    return SimulationResult(
        fid=f, freq_Hz=freq, spectrum=spec, ppm=ppm,
        regime=regime, acquisition=acq,
    )
