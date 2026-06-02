"""1D pulse sequences (Layer 1 of `docs/SEQUENCES_PLAN.md`).

These are thin, named wrappers around `simulate()`. They exist so callers
have a stable API ("run a zg") instead of having to remember which
combination of regime / state / detector reproduces a given experiment,
and so later layers (spin echo, INEPT, ...) can compose them.
"""
from __future__ import annotations

from typing import Iterable, Optional, Union

from src.core.acquisition import Acquisition
from src.core.regime import Regime
from src.core.simulate import SimulationResult, simulate
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
        label=(sys.label + " [decoupled]").strip(),
    )
