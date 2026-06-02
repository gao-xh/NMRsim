"""Hamiltonian builders.

All Hamiltonians are returned as Hermitian (2**N, 2**N) complex matrices in
**angular frequency units (rad/s)**, so propagators are simply
``exp(-i H t)`` with t in seconds.

Three flavors:

- H_J_only(sys)              : pure scalar coupling. Used for true zero-field.
- H_lab(sys, B0)             : Zeeman + J in the lab frame. Used for ZULF
                               with a small bias field, or as a sanity check.
- H_rotating(sys, B0, obs)   : Zeeman (offset only, by chemical shift) + J in
                               the rotating frame of the observed nucleus.
                               Standard high-field liquid-NMR Hamiltonian.

The rotating-frame form is **strongly preferred for high field** because the
matrix elements are in kHz, not hundreds of MHz, so numerical conditioning
and time-step requirements are sane.
"""
from __future__ import annotations

from math import pi
from typing import Optional

import numpy as np

from . import isotopes as iso_table
from .ops import operators
from .system import SpinSystem


def _J_term(sys: SpinSystem, *, secular_heteronuclear: bool = False) -> np.ndarray:
    """Sum_{i<j} 2π J_ij (Ix Ix + Iy Iy + Iz Iz).

    If `secular_heteronuclear` is True, the transverse (flip-flop) part is
    dropped for pairs of different isotopes — required in any (multiply)
    rotating frame where the Larmor difference is huge compared to J, so
    those terms oscillate fast and average to zero. Homonuclear pairs
    always keep the full bilinear.
    """
    Ix, Iy, Iz = operators(sys.n)
    dim = 2 ** sys.n
    H = np.zeros((dim, dim), dtype=complex)
    for i in range(sys.n):
        for j in range(i + 1, sys.n):
            J = sys.J_Hz[i, j]
            if J == 0.0:
                continue
            same = sys.isotopes[i] == sys.isotopes[j]
            if same or not secular_heteronuclear:
                H += 2.0 * pi * J * (Ix[i] @ Ix[j] + Iy[i] @ Iy[j] + Iz[i] @ Iz[j])
            else:
                H += 2.0 * pi * J * (Iz[i] @ Iz[j])
    return H


def H_J_only(sys: SpinSystem) -> np.ndarray:
    """Pure scalar-coupling Hamiltonian (true zero field)."""
    return _J_term(sys)


def H_lab(sys: SpinSystem, B0_T: float) -> np.ndarray:
    """Lab-frame: Zeeman + scalar J.

    H_Z = - sum_i γ_i B0 I_zi      (rad/s; sign matches standard convention)
    Note: signed γ is used so 15N picks up the correct sign.
    """
    _, _, Iz = operators(sys.n)
    dim = 2 ** sys.n
    H = np.zeros((dim, dim), dtype=complex)
    for i in range(sys.n):
        omega = -iso_table.gamma_rad_per_s_per_T(sys.isotopes[i]) * B0_T
        H += omega * Iz[i]
    H += _J_term(sys)
    return H


def H_rotating(sys: SpinSystem,
               B0_T: float,
               observed: str,
               carrier_ppm: float = 0.0) -> np.ndarray:
    """Rotating-frame Hamiltonian for high-field liquid NMR.

    In the rotating frame of the *observed* nucleus at carrier frequency
    ν_carrier = (carrier_ppm * 1e-6) * |ν0,obs|, each spin contributes a
    Zeeman offset:

        ω_i = 2π · (δ_i - carrier_ppm) · 1e-6 · ν0,nuc(i)

    where ν0,nuc(i) is the Larmor frequency of spin i's own nucleus at B0.

    Heteronuclear spins keep their full chemical-shift offset relative to
    their own Larmor frequency — this is the standard "doubly rotating
    frame" picture; couplings stay (no truncation), so AB/ABX etc. are
    treated exactly.
    """
    _, _, Iz = operators(sys.n)
    dim = 2 ** sys.n
    H = np.zeros((dim, dim), dtype=complex)
    for i in range(sys.n):
        nu0 = iso_table.larmor_Hz(sys.isotopes[i], B0_T)   # signed
        # For the observed nucleus we subtract the carrier; for heteronuclei
        # the natural rotating frame is each spin's own Larmor, so the
        # offset is just the chemical shift (carrier_ppm is irrelevant).
        if sys.isotopes[i] == observed:
            offset_Hz = (sys.shifts_ppm[i] - carrier_ppm) * 1e-6 * nu0
        else:
            offset_Hz = sys.shifts_ppm[i] * 1e-6 * nu0
        H += 2.0 * pi * offset_Hz * Iz[i]
    H += _J_term(sys, secular_heteronuclear=True)
    return H
