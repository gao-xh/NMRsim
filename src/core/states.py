"""Density-matrix initial states."""
from __future__ import annotations

import numpy as np

from . import isotopes as iso_table
from .ops import operators
from .system import SpinSystem


def thermal_high_temp(sys: SpinSystem, observed: str | None = None) -> np.ndarray:
    """High-temperature thermal state ρ ∝ Σ γ_i I_zi.

    The identity part is dropped (it doesn't evolve and doesn't contribute
    to coherences). γ is signed so heteronuclei get correct relative weight.

    If `observed` is given, only that nucleus is populated (common
    simplification when you only detect one channel and want to suppress
    contributions from unobserved isotopes in the FID).
    """
    _, _, Iz = operators(sys.n)
    dim = 2 ** sys.n
    rho = np.zeros((dim, dim), dtype=complex)
    for i in range(sys.n):
        if observed is not None and sys.isotopes[i] != observed:
            continue
        rho = rho + iso_table.get(sys.isotopes[i]).gamma_MHz_per_T * Iz[i]
    return rho


def prepolarized_x(sys: SpinSystem) -> np.ndarray:
    """Σ γ_i I_xi — typical ZULF initial state after pre-polarization
    in a guiding field and sudden transfer to zero field along x."""
    Ix, _, _ = operators(sys.n)
    dim = 2 ** sys.n
    rho = np.zeros((dim, dim), dtype=complex)
    for i in range(sys.n):
        rho = rho + iso_table.get(sys.isotopes[i]).gamma_MHz_per_T * Ix[i]
    return rho
