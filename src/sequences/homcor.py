"""Homonuclear correlation 2D sequences: COSY, TOCSY.

Both detect the observed channel (`regime.observed`) on both dimensions
(F1 = F2 = observed-nucleus shift), so they are *homonuclear*. They
share the same States hypercomplex t1 quadrature trick used in
`hetcor.py`.

Sequences
---------
COSY-90:   90°(obs)φ₁ — t1 — 90°x(obs) — acq
TOCSY:     90°(obs)φ₁ — t1 — U_iso(τ_m) — acq

For States the first pulse phase φ₁ is cycled between -y (cosine set)
and +x (sine set); the second/mixing block is identical for both.

Idealisations
-------------
- COSY: no axial-peak filter, no DQ filtering, no gradient selection.
- TOCSY: the isotropic mixing block is the **exact** isotropic-J
  propagator `exp(-i·τ_m·H_iso)`, which is the τ_m → ideal-spin-lock
  limit of DIPSI / MLEV. Chemical shifts and heteronuclear couplings
  are dropped during mixing; only homonuclear J between observed-channel
  spins remains, with its full `Ix·Ix + Iy·Iy + Iz·Iz` form.
"""
from __future__ import annotations

from math import pi

import numpy as np

from src.core.acquisition import Acquisition2D
from src.core.engine import fid as _fid1d
from src.core.ops import operators
from src.core.pulses import apply_unitary, propagator, pulse
from src.core.regime import Regime
from src.core.simulate import SimulationResult2D, finalize_2d
from src.core.states import thermal_high_temp
from src.core.system import SpinSystem

from .twoD import acquire2d_hypercomplex


def _isotropic_J_obs(sys: SpinSystem, observed: str) -> np.ndarray:
    """Sum_{i<j, both `observed`} 2π J_ij (Ix·Ix + Iy·Iy + Iz·Iz) — rad/s."""
    Ix, Iy, Iz = operators(sys.n)
    dim = 2 ** sys.n
    H = np.zeros((dim, dim), dtype=complex)
    for i in range(sys.n):
        if sys.isotopes[i] != observed:
            continue
        for j in range(i + 1, sys.n):
            if sys.isotopes[j] != observed:
                continue
            Jij = sys.J_Hz[i, j]
            if Jij == 0.0:
                continue
            H += 2.0 * pi * Jij * (Ix[i] @ Ix[j] +
                                   Iy[i] @ Iy[j] +
                                   Iz[i] @ Iz[j])
    return H


def _build_homcor_runner(sys: SpinSystem,
                         regime: Regime,
                         acq2d: Acquisition2D,
                         *,
                         mixing: str,
                         mixing_time: float = 0.0):
    """Pre-build propagators; return ``one_point(t1, quadrature)``.

    ``mixing`` selects the block placed between t1 and acquisition:
      - ``'cosy90'`` → single 90°x(obs) read pulse.
      - ``'tocsy'``  → isotropic-mixing propagator of length ``mixing_time``.
    """
    observed = regime.observed
    if observed is None:
        raise ValueError("homcor sequences require regime.observed "
                         "(e.g. HF(...))")
    if not sys.indices_of(observed):
        raise ValueError(f"no spin of isotope {observed!r} in system")

    H = regime.hamiltonian(sys)
    det = regime.detector(sys)

    # Static pulse propagators.
    U_90x_obs = pulse(sys, observed, np.pi / 2, 0.0)
    U_90y_obs = pulse(sys, observed, np.pi / 2, np.pi / 2)

    if mixing == 'cosy90':
        U_mix = U_90x_obs
    elif mixing == 'tocsy':
        H_iso = _isotropic_J_obs(sys, observed)
        U_mix = propagator(H_iso, mixing_time)
    else:
        raise ValueError(f"unknown mixing block: {mixing!r}")

    rho_thermal = thermal_high_temp(sys, observed=observed)
    # States quadrature on the first pulse:
    #   cosine set: 90°y   (Iz → +Ix, t1 → +Ix cosΩt + Iy sinΩt)
    #   sine  set: 90°x    (Iz → -Iy, t1 → -Iy cosΩt + Ix sinΩt)
    # After a 90°x mixing pulse the cosine set keeps Ix·cosΩt and the
    # sine set keeps Ix·sinΩt → hypercomplex FT gives exp(+iΩt1) ⇒
    # peak at +Ω in F1, matching the conventional sign in F2.
    rho_cos = apply_unitary(rho_thermal, U_90y_obs)
    rho_sin = apply_unitary(rho_thermal, U_90x_obs)

    n_t2 = acq2d.n_t2
    dt_t2 = acq2d.t2.dt
    t2_star = acq2d.t2.t2_star

    def one_point(t1: float, quadrature: str) -> np.ndarray:
        rho_t1 = rho_cos if quadrature == 'cos' else rho_sin

        if t1 > 0.0:
            U_t1 = propagator(H, t1)
            rho = apply_unitary(rho_t1, U_t1)
        else:
            rho = rho_t1

        rho = apply_unitary(rho, U_mix)

        return _fid1d(H, rho, det,
                      n_points=n_t2, dt=dt_t2, t2_star=t2_star)

    return one_point


def cosy(sys: SpinSystem,
         regime: Regime,
         acq2d: Acquisition2D) -> SimulationResult2D:
    """Magnitude / phase-sensitive COSY-90 (90°-t1-90°-acq).

    F1 = F2 = observed-nucleus chemical shift. Diagonal and cross peaks
    appear for every J-coupled pair on the observed channel. Cross-peak
    sign / multiplet structure is the anti-phase pattern characteristic
    of COSY-90; no extra filters are applied.
    """
    runner = _build_homcor_runner(sys, regime, acq2d, mixing='cosy90')
    S_cos, S_sin = acquire2d_hypercomplex(runner, acq2d)
    return finalize_2d(S_cos, S_sin, acq2d, regime, indirect=regime.observed)


def tocsy(sys: SpinSystem,
          regime: Regime,
          acq2d: Acquisition2D,
          *,
          mixing_time: float) -> SimulationResult2D:
    """Total correlation spectroscopy (TOCSY) — idealised isotropic mixing.

    F1 = F2 = observed-nucleus shift. Diagonal + cross peaks for every
    pair of spins in the same J-coupled subnetwork (not just directly
    coupled, unlike COSY). The mixing block is the exact unitary
    ``exp(-i·τ_m·H_iso)`` (idealised spin-lock); residual chemical
    shift / off-resonance effects of real DIPSI / MLEV are not modelled.

    Parameters
    ----------
    mixing_time : isotropic-mixing duration τ_m (seconds). Typical
        values for ¹H TOCSY: 30–120 ms.
    """
    if mixing_time < 0.0:
        raise ValueError("mixing_time must be non-negative")
    runner = _build_homcor_runner(sys, regime, acq2d,
                                  mixing='tocsy', mixing_time=mixing_time)
    S_cos, S_sin = acquire2d_hypercomplex(runner, acq2d)
    return finalize_2d(S_cos, S_sin, acq2d, regime, indirect=regime.observed)
