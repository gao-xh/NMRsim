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

from .acquisition import Acquisition, Acquisition2D
from .engine import acquire as _acquire
from .processing import (
    apodize_exponential,
    apodize_gaussian,
    fft2_hypercomplex,
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
    return finalize_fid(f, acq, regime)


def finalize_fid(fid: np.ndarray,
                 acq: Acquisition,
                 regime: Regime) -> SimulationResult:
    """Apodize → FFT → axis conversion → wrap into SimulationResult.

    Shared between `simulate()` and sequence functions that build their
    own FID (echo, IR, CPMG, 2D wrappers...). Centralizing this here
    means processing changes only happen in one place.
    """
    f = fid
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
            # offset axis is already relative to carrier in HF rotating frame
            ppm = freq_to_ppm(freq, nu0, carrier_ppm=0.0)

    return SimulationResult(
        fid=f, freq_Hz=freq, spectrum=spec, ppm=ppm,
        regime=regime, acquisition=acq,
    )


# ---------------------------------------------------------------------------
# 2D results
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SimulationResult2D:
    """Output of a 2D simulate / sequence call.

    Axis convention: F1 = indirect (t1), F2 = direct (t2). The
    ``spectrum`` array is shaped ``(n_F1, n_F2)``; ``freq_F1_Hz`` /
    ``freq_F2_Hz`` are the corresponding centered frequency axes.
    ``ppm_F1`` / ``ppm_F2`` are only set when the relevant nucleus
    Larmor frequency is known (HF-like regimes).
    """
    fid_cos: np.ndarray          # (n_t1, n_t2) — cosine-modulated t1
    fid_sin: np.ndarray          # (n_t1, n_t2) — sine-modulated t1
    freq_F1_Hz: np.ndarray
    freq_F2_Hz: np.ndarray
    spectrum: np.ndarray         # (n_F1, n_F2)
    ppm_F1: Optional[np.ndarray]
    ppm_F2: Optional[np.ndarray]
    regime: Regime
    acquisition: Acquisition2D
    indirect: Optional[str]      # indirect-dimension nucleus label, e.g. '13C'


def _apodize(fid: np.ndarray, acq: Acquisition, axis: int) -> np.ndarray:
    if acq.apodization == "none":
        return fid
    # Build a 1D window of length fid.shape[axis], then broadcast.
    n = fid.shape[axis]
    t = np.arange(n) * acq.dt
    if acq.apodization == "exponential":
        win = np.exp(-np.pi * acq.lb_Hz * t)
    elif acq.apodization == "gaussian":
        a = (np.pi * acq.gb_Hz) ** 2 / (4.0 * np.log(2.0))
        win = np.exp(-a * t * t)
    else:
        raise ValueError(f"Unknown apodization: {acq.apodization!r}")
    shape = [1] * fid.ndim
    shape[axis] = n
    return fid * win.reshape(shape)


def finalize_2d(fid_cos: np.ndarray,
                fid_sin: np.ndarray,
                acq2d: Acquisition2D,
                regime: Regime,
                *,
                indirect: Optional[str] = None) -> SimulationResult2D:
    """Apodize (both axes) → hypercomplex 2D FT → ppm axes.

    Shared finishing path for every 2D sequence (HSQC, HMBC, future
    COSY/TOCSY). Sequences only have to produce the two t1-modulated FID
    arrays and pass them here.
    """
    A = _apodize(_apodize(fid_cos, acq2d.t1, axis=0), acq2d.t2, axis=1)
    B = _apodize(_apodize(fid_sin, acq2d.t1, axis=0), acq2d.t2, axis=1)

    freq_F1, freq_F2, spec = fft2_hypercomplex(
        A, B,
        dt_t1=acq2d.t1.dt,
        dt_t2=acq2d.t2.dt,
        zero_fill_t1=acq2d.t1.zero_fill,
        zero_fill_t2=acq2d.t2.zero_fill,
        half_first=acq2d.t1.half_first,  # both axes share the convention
    )

    ppm_F2 = None
    if regime.display_unit == "ppm":
        nu0 = regime.larmor_Hz()
        if nu0 != 0.0:
            ppm_F2 = freq_to_ppm(freq_F2, nu0, carrier_ppm=0.0)

    ppm_F1 = None
    if indirect is not None and regime.B0_T != 0.0:
        nu0_ind = regime.larmor_Hz(indirect)
        if nu0_ind != 0.0:
            ppm_F1 = freq_to_ppm(freq_F1, nu0_ind, carrier_ppm=0.0)

    return SimulationResult2D(
        fid_cos=A, fid_sin=B,
        freq_F1_Hz=freq_F1, freq_F2_Hz=freq_F2,
        spectrum=spec,
        ppm_F1=ppm_F1, ppm_F2=ppm_F2,
        regime=regime, acquisition=acq2d, indirect=indirect,
    )
