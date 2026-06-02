"""Heteronuclear correlation 2D sequences: HSQC, HMBC.

Both are built from the same INEPT–t1–reverse-INEPT skeleton; the only
difference is the transfer delay τ = 1/(4·J) and the J used (1J_CH for
HSQC, n_J_CH long-range for HMBC).

Conventions
-----------
- The directly detected nucleus is taken from ``regime.observed`` (usually
  '1H').
- The indirect (incremented) nucleus is given by ``indirect=`` (usually
  '13C' or '15N').
- States hypercomplex t1 quadrature: the first 90° pulse on the indirect
  channel is along +x for the cosine set and along -y for the sine set.
- A 180° pulse on the observed channel is placed at t1/2 to refocus the
  ``J·Iz_obs·Iz_ind`` coupling during the indirect evolution, so the F1
  axis carries only the indirect chemical shift.
- Acquisition is performed on the observed channel; by default with
  ``decouple_during_acq=True`` the indirect–observed J is zeroed during
  t2 (ideal CW decoupling), so each cross peak is a singlet in F2.

What is NOT modelled
--------------------
- Phase cycling (the density-matrix picture already gives the desired
  pathway; see ``docs/SEQUENCES_PLAN.md`` §4).
- Gradient coherence selection.
- Realistic CPD waveforms (WALTZ-16, GARP) — the decoupling here is the
  J = 0 limit.
- Echo-antiecho quadrature — only States is implemented for v0.4.
"""
from __future__ import annotations

from typing import Optional

import numpy as np

from src.core.acquisition import Acquisition2D
from src.core.engine import fid as _fid1d
from src.core.pulses import apply_unitary, propagator, pulse
from src.core.regime import Regime
from src.core.simulate import SimulationResult2D, finalize_2d
from src.core.states import thermal_high_temp
from src.core.system import SpinSystem

from .oneD import _zero_heteronuclear_J
from .twoD import acquire2d_hypercomplex


def _check_channels(sys: SpinSystem, observed: str, indirect: str) -> None:
    if observed == indirect:
        raise ValueError("observed and indirect must be different nuclei")
    if not sys.indices_of(observed):
        raise ValueError(f"no spin of isotope {observed!r} in system")
    if not sys.indices_of(indirect):
        raise ValueError(f"no spin of isotope {indirect!r} in system")


def _build_hetcor_runner(sys: SpinSystem,
                         regime: Regime,
                         acq2d: Acquisition2D,
                         *,
                         indirect: str,
                         tau: float,
                         decouple_during_acq: bool):
    """Compose the propagators once; return ``one_point(t1, quadrature)``."""
    observed = regime.observed
    if observed is None:
        raise ValueError("hetcor sequences require regime.observed (e.g. HF(...))")
    _check_channels(sys, observed, indirect)

    H = regime.hamiltonian(sys)
    det = regime.detector(sys)

    # Acquisition Hamiltonian / detector: optionally decoupled.
    if decouple_during_acq:
        sys_acq = _zero_heteronuclear_J(sys, observed,
                                        decouple=(indirect,))
        H_acq = regime.hamiltonian(sys_acq)
        det_acq = regime.detector(sys_acq)
    else:
        H_acq = H
        det_acq = det

    # Static pulse propagators (sys topology never changes ⇒ build once).
    U_90x_obs   = pulse(sys, observed, np.pi / 2, 0.0)
    U_90y_obs   = pulse(sys, observed, np.pi / 2, np.pi / 2)
    U_180x_obs  = pulse(sys, observed, np.pi,     0.0)
    U_180x_ind  = pulse(sys, indirect, np.pi,     0.0)
    U_180_both  = U_180x_ind @ U_180x_obs        # disjoint channels ⇒ commute
    U_90x_ind   = pulse(sys, indirect, np.pi / 2, 0.0)
    U_90_neg_y_ind = pulse(sys, indirect, np.pi / 2, -np.pi / 2)

    U_tau = propagator(H, tau)

    rho_thermal = thermal_high_temp(sys, observed=observed)

    # Pre-transfer block: 90°x(obs) — τ — 180(both) — τ — 90°y(obs)
    # then a 90° on the indirect channel whose phase encodes cos / sin.
    rho_pre = apply_unitary(rho_thermal, U_90x_obs)
    rho_pre = apply_unitary(rho_pre,    U_tau)
    rho_pre = apply_unitary(rho_pre,    U_180_both)
    rho_pre = apply_unitary(rho_pre,    U_tau)
    rho_pre = apply_unitary(rho_pre,    U_90y_obs)

    rho_cos = apply_unitary(rho_pre, U_90x_ind)        # anti-phase along Iy_ind
    rho_sin = apply_unitary(rho_pre, U_90_neg_y_ind)   # anti-phase along Ix_ind

    n_t2 = acq2d.n_t2
    dt_t2 = acq2d.t2.dt
    t2_star = acq2d.t2.t2_star

    def one_point(t1: float, quadrature: str) -> np.ndarray:
        rho_t1 = rho_cos if quadrature == 'cos' else rho_sin

        if t1 > 0.0:
            U_half = propagator(H, t1 / 2.0)
            rho = apply_unitary(rho_t1, U_half)
            rho = apply_unitary(rho,    U_180x_obs)    # refocus J during t1
            rho = apply_unitary(rho,    U_half)
        else:
            rho = rho_t1

        # Reverse transfer: 90°x(ind), 90°y(obs), τ — 180(both) — τ.
        rho = apply_unitary(rho, U_90x_ind)
        rho = apply_unitary(rho, U_90y_obs)
        rho = apply_unitary(rho, U_tau)
        rho = apply_unitary(rho, U_180_both)
        rho = apply_unitary(rho, U_tau)

        return _fid1d(H_acq, rho, det_acq,
                      n_points=n_t2, dt=dt_t2, t2_star=t2_star)

    return one_point


def hsqc(sys: SpinSystem,
         regime: Regime,
         acq2d: Acquisition2D,
         *,
         indirect: str = '13C',
         J_CH: float,
         decouple_during_acq: bool = True) -> SimulationResult2D:
    """Heteronuclear single-quantum coherence (HSQC).

    Cross peaks appear at (δ_obs, δ_ind) for every directly-J-coupled
    observed–indirect pair. F1 = indirect chemical shift, F2 = observed
    chemical shift.

    Parameters
    ----------
    indirect : indirect-channel nucleus label (default '13C').
    J_CH : one-bond coupling between observed and indirect spins (Hz);
        sets τ = 1/(4·J_CH) for both transfer steps.
    decouple_during_acq : if True, the J between `observed` and
        `indirect` is zeroed during t2 (ideal CW decoupling) so every
        cross peak is a singlet in F2.
    """
    tau = 1.0 / (4.0 * J_CH)
    runner = _build_hetcor_runner(sys, regime, acq2d,
                                  indirect=indirect, tau=tau,
                                  decouple_during_acq=decouple_during_acq)
    S_cos, S_sin = acquire2d_hypercomplex(runner, acq2d)
    return finalize_2d(S_cos, S_sin, acq2d, regime, indirect=indirect)


def hmbc(sys: SpinSystem,
         regime: Regime,
         acq2d: Acquisition2D,
         *,
         indirect: str = '13C',
         J_long: float = 8.0,
         decouple_during_acq: bool = False) -> SimulationResult2D:
    """Heteronuclear multiple-bond correlation (HMBC).

    Same skeleton as `hsqc`, but τ = 1/(4·J_long) tuned for long-range
    (typically 2J / 3J ≈ 4–10 Hz) couplings instead of 1J. Long-range
    cross peaks dominate; one-bond peaks appear too and are usually
    suppressed by a low-pass J filter in real experiments (not modelled).

    Acquisition decoupling defaults to False because HMBC traditionally
    shows the residual 1J_CH splitting in F2.
    """
    tau = 1.0 / (4.0 * J_long)
    runner = _build_hetcor_runner(sys, regime, acq2d,
                                  indirect=indirect, tau=tau,
                                  decouple_during_acq=decouple_during_acq)
    S_cos, S_sin = acquire2d_hypercomplex(runner, acq2d)
    return finalize_2d(S_cos, S_sin, acq2d, regime, indirect=indirect)
