"""1D pulse sequences.

Layer 1 — single-event experiments (`pulse_acquire`, `pulse_acquire_decoupled`).
Layer 2 — multi-pulse single-channel experiments (`spin_echo`,
`inversion_recovery`, `cpmg`).

These are thin, named wrappers built on `src.core` primitives. They
exist so callers have a stable API ("run a hahnecho") and so later
layers can compose them.
"""
from __future__ import annotations

from typing import Iterable, Optional, Union

import numpy as np

from src.core.acquisition import Acquisition
from src.core.engine import acquire as _acquire
from src.core.pulses import apply_unitary, evolve, propagator, pulse
from src.core.regime import Regime
from src.core.relaxation import relax_T1
from src.core.simulate import SimulationResult, finalize_fid, simulate
from src.core.states import thermal_high_temp
from src.core.system import SpinSystem


DecoupleSpec = Union[str, Iterable[str], None]


def pulse_acquire(sys: SpinSystem,
                  regime: Regime,
                  acq: Acquisition) -> SimulationResult:
    """Standard 1D pulse-acquire (Bruker `zg`).

    Equivalent to `simulate(sys, regime, acq)` today because the HF
    regime already prepares the post-90°x state and the ZULF/LF regimes
    prepare a prepolarized state — both are what `zg`-style experiments
    measure. Kept as a named sequence so future variants (explicit pulse
    phase, presaturation, etc.) plug in without breaking callers.
    """
    return simulate(sys, regime, acq)


def pulse_acquire_decoupled(sys: SpinSystem,
                            regime: Regime,
                            acq: Acquisition,
                            *,
                            decouple: DecoupleSpec = None) -> SimulationResult:
    """Pulse-acquire with ideal heteronuclear decoupling (`zgpg` / `zgig`).

    Models perfect CW decoupling: scalar couplings between the observed
    channel and every nucleus in `decouple` are zeroed for the whole
    experiment. Homonuclear couplings on the observed channel are kept.

    Parameters
    ----------
    decouple : isotope label, iterable of labels, or None.
        None → decouple every nucleus that differs from `regime.observed`
        (the common case: ``zgpg`` on ¹³C decouples all ¹H).

    Notes
    -----
    Real CPD schemes (WALTZ-16, GARP, ...) are not modeled — the result
    is the limit of infinitely good on-resonance decoupling with zero
    residual splitting. Sub-pulse time-stepping for shaped CPD is
    deferred (see `SEQUENCES_PLAN.md` §Deferred).
    """
    if regime.observed is None:
        raise ValueError(
            "pulse_acquire_decoupled requires a regime with an observed "
            "channel (e.g. HF(...))."
        )
    sys_dec = _zero_heteronuclear_J(sys, regime.observed, decouple)
    return simulate(sys_dec, regime, acq)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _zero_heteronuclear_J(sys: SpinSystem,
                          observed: str,
                          decouple: DecoupleSpec) -> SpinSystem:
    """Return a copy of `sys` with J(observed, decoupled) set to 0."""
    if decouple is None:
        decouple_set = {n for n in sys.isotopes if n != observed}
    elif isinstance(decouple, str):
        decouple_set = {decouple}
    else:
        decouple_set = set(decouple)

    if observed in decouple_set:
        raise ValueError(
            f"Cannot decouple the observed channel ({observed!r}) from itself"
        )

    J = sys.J_Hz.copy()
    for i, ni in enumerate(sys.isotopes):
        for j, nj in enumerate(sys.isotopes):
            if i == j:
                continue
            if (ni == observed and nj in decouple_set) or \
               (nj == observed and ni in decouple_set):
                J[i, j] = 0.0

    return SpinSystem(
        isotopes=list(sys.isotopes),
        shifts_ppm=sys.shifts_ppm.copy(),
        J_Hz=J,
        T1=(None if sys.T1 is None else sys.T1.copy()),
        label=(sys.label + " [decoupled]").strip(),
    )


# ---------------------------------------------------------------------------
# Layer 2 — single-channel multi-pulse sequences
# ---------------------------------------------------------------------------

def _require_observed(regime: Regime, name: str) -> str:
    if regime.observed is None:
        raise ValueError(
            f"{name} requires a regime with an observed channel (e.g. HF(...))."
        )
    return regime.observed


def _thermal_observed(sys: SpinSystem, observed: str) -> np.ndarray:
    """Pre-pulse thermal state on the observed channel only."""
    return thermal_high_temp(sys, observed=observed)


def spin_echo(sys: SpinSystem,
              regime: Regime,
              acq: Acquisition,
              *,
              tau: float,
              pulse_phase_180: float = 0.0) -> SimulationResult:
    """Hahn spin-echo: 90°x — τ — 180°φ — τ — acq (Bruker ``hahnecho``).

    The 180° pulse refocuses chemical-shift evolution at the start of
    acquisition; scalar-coupling evolution accumulates over the full
    2τ (J-modulation). At ``τ = 1/(2J)`` an AX doublet appears in
    anti-phase, which is the standard correctness check.

    Parameters
    ----------
    tau : half-echo delay (s). The total echo time is 2·tau.
    pulse_phase_180 : phase of the refocusing pulse, radians. 0 = x.

    Notes
    -----
    No T1/T2 relaxation is applied during the τ delays — keep
    ``acq.t2_star`` for line broadening during acquisition.
    """
    obs = _require_observed(regime, "spin_echo")
    H   = regime.hamiltonian(sys)
    det = regime.detector(sys)

    rho = _thermal_observed(sys, obs)
    rho = apply_unitary(rho, pulse(sys, obs, np.pi / 2, 0.0))    # 90°x
    rho = evolve(rho, H, tau)
    rho = apply_unitary(rho, pulse(sys, obs, np.pi, pulse_phase_180))  # 180°
    rho = evolve(rho, H, tau)

    f = _acquire(H, rho, det, acq)
    return finalize_fid(f, acq, regime)


def inversion_recovery(sys: SpinSystem,
                       regime: Regime,
                       acq: Acquisition,
                       *,
                       tau: float) -> SimulationResult:
    """Inversion recovery: 180°x — τ — 90°x — acq (Bruker ``t1ir``).

    Signal versus τ recovers as ``1 - 2·exp(-τ/T1)`` for an isolated
    spin. Requires `sys.T1` to be set; otherwise the τ delay does
    nothing and every τ gives an inverted spectrum.

    Parameters
    ----------
    tau : recovery delay (s).
    """
    obs = _require_observed(regime, "inversion_recovery")
    H   = regime.hamiltonian(sys)
    det = regime.detector(sys)

    rho = _thermal_observed(sys, obs)
    rho = apply_unitary(rho, pulse(sys, obs, np.pi, 0.0))        # 180°x
    rho = relax_T1(rho, sys, tau, observed=obs)                  # T1 recovery
    rho = apply_unitary(rho, pulse(sys, obs, np.pi / 2, 0.0))    # 90°x readout

    f = _acquire(H, rho, det, acq)
    return finalize_fid(f, acq, regime)


def cpmg(sys: SpinSystem,
         regime: Regime,
         acq: Acquisition,
         *,
         tau: float,
         n_echoes: int,
         pulse_phase_180: float = np.pi / 2) -> SimulationResult:
    """CPMG echo train: 90°x — [τ — 180°y — τ] × n — acq (Bruker ``cpmg``).

    Train of `n_echoes` refocusing pulses before acquisition. Standard
    CPMG uses a y-phase 180° (``π/2`` radians) to make the sequence
    self-correcting against flip-angle imperfections; the default
    matches that convention.

    Parameters
    ----------
    tau : half-echo spacing (s). Total pre-acquisition time = 2·n·τ.
    n_echoes : number of refocusing 180° pulses (n >= 0).
    pulse_phase_180 : phase of every refocusing pulse, radians.
    """
    if n_echoes < 0:
        raise ValueError(f"n_echoes must be >= 0, got {n_echoes}")
    obs = _require_observed(regime, "cpmg")
    H   = regime.hamiltonian(sys)
    det = regime.detector(sys)

    rho = _thermal_observed(sys, obs)
    rho = apply_unitary(rho, pulse(sys, obs, np.pi / 2, 0.0))    # 90°x

    if n_echoes > 0:
        U_tau = propagator(H, tau)
        U_180 = pulse(sys, obs, np.pi, pulse_phase_180)
        for _ in range(n_echoes):
            rho = apply_unitary(rho, U_tau)
            rho = apply_unitary(rho, U_180)
            rho = apply_unitary(rho, U_tau)

    f = _acquire(H, rho, det, acq)
    return finalize_fid(f, acq, regime)
