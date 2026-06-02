"""Experimental regime abstraction.

A `Regime` bundles the three knobs that distinguish high-field from
zero/ultra-low-field experiments:

- how the Hamiltonian is built,
- which density-matrix initial state is used,
- which observable is detected.

Sequence code and high-level scripts should take a `Regime` and never
hard-code `H_rotating` / `H_J_only` etc. directly. Adding a new regime
(low field, Earth field, lab-frame ZULF with bias, ...) means writing a
new factory; existing sequences keep working unchanged.

Usage
-----
    from src.core import SpinSystem
    from src.core.regime import HF, ZULF

    sys = SpinSystem(['1H','1H'], [1.0, 3.0], [[0,7],[7,0]])

    reg = HF(B0_T=9.4, observed='1H', carrier_ppm=2.0)
    # or
    reg = ZULF()

    H    = reg.hamiltonian(sys)
    rho0 = reg.initial_state(sys)
    det  = reg.detector(sys)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np

from . import isotopes as iso_table
from .detection import detect_Iplus, detect_Mx
from .hamiltonian import H_J_only, H_lab, H_rotating
from .states import prepolarized_x, thermal_high_temp
from .system import SpinSystem


Builder = Callable[[SpinSystem], np.ndarray]


@dataclass(frozen=True)
class Regime:
    """Experimental regime: how to build H, ρ₀, and the detector.

    Attributes
    ----------
    name : short identifier ("HF", "ZULF", ...).
    hamiltonian : SpinSystem -> H (rad/s, Hermitian).
    initial_state : SpinSystem -> ρ₀.
    detector : SpinSystem -> detection operator.
    observed : nucleus label being detected, or None if regime-wide
        (e.g. ZULF magnetometer reads total magnetization).
    B0_T : static field magnitude, 0 for true zero field.
    requires_observed : True if sequences need a specific channel
        (used to validate heteronuclear sequences like HSQC).
    display_unit : "ppm" for HF (frequency → ppm via Larmor), "Hz" for ZULF.
    """
    name: str
    hamiltonian: Builder
    initial_state: Builder
    detector: Builder
    observed: Optional[str] = None
    B0_T: float = 0.0
    requires_observed: bool = False
    display_unit: str = "Hz"

    def larmor_Hz(self, nucleus: Optional[str] = None) -> float:
        """Larmor frequency for ppm conversion. None means use `observed`."""
        nuc = nucleus or self.observed
        if nuc is None or self.B0_T == 0.0:
            return 0.0
        return iso_table.larmor_Hz(nuc, self.B0_T)


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

def HF(B0_T: float,
       observed: str,
       carrier_ppm: float = 0.0) -> Regime:
    """High-field liquid NMR in the rotating frame of `observed`.

    Initial state for `simulate()` is the *post-90°x* state on the observed
    channel (i.e. the standard pulse-acquire result), so calling
    `simulate(sys, HF(...), acq)` gives a non-zero FID directly.

    If you need access to the pre-pulse thermal state, build it explicitly
    via `thermal_high_temp(sys, observed=...)` and apply your own pulses.
    """
    from .pulses import pulse, apply_unitary

    def _prepared(s):
        rho = thermal_high_temp(s, observed=observed)
        U90 = pulse(s, observed, np.pi / 2, 0.0)
        return apply_unitary(rho, U90)

    return Regime(
        name="HF",
        hamiltonian=lambda s: H_rotating(s, B0_T, observed, carrier_ppm),
        initial_state=_prepared,
        detector=lambda s: detect_Iplus(s, observed),
        observed=observed,
        B0_T=B0_T,
        requires_observed=True,
        display_unit="ppm",
    )


def ZULF() -> Regime:
    """True zero-field: pure J Hamiltonian, prepolarized state, M_x detection."""
    return Regime(
        name="ZULF",
        hamiltonian=H_J_only,
        initial_state=prepolarized_x,
        detector=lambda s: detect_Mx(s, weighted=True),
        observed=None,
        B0_T=0.0,
        requires_observed=False,
        display_unit="Hz",
    )


def LF(B0_T: float) -> Regime:
    """Low-field / ULF lab-frame: Zeeman + J in the lab frame, ZULF-style
    prepolarized initial state and magnetometer detection.

    Use when there is a small bias field and you do not want to enter a
    rotating frame.
    """
    return Regime(
        name="LF",
        hamiltonian=lambda s: H_lab(s, B0_T),
        initial_state=prepolarized_x,
        detector=lambda s: detect_Mx(s, weighted=True),
        observed=None,
        B0_T=B0_T,
        requires_observed=False,
        display_unit="Hz",
    )
