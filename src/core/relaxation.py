"""Relaxation operators applied between sequence events.

Currently implements a scalar, per-spin **T1** model only:

    rho(t) = rho_eq + (rho(0) - rho_eq) * exp(-t/T1)

applied along each spin's Iz axis. Mathematically, this projects rho
onto its `Iz_i` component, drags that component toward the thermal
equilibrium value, and adds the unchanged remainder back. Transverse
(Ix, Iy) and bilinear (2 Iz_i Iz_j, ...) components are left alone —
those decay through `Acquisition.t2_star` during acquisition.

Why projection rather than a full Redfield / Lindblad propagator?
- Sequences in Layer 2 (`spin_echo`, `inversion_recovery`, `cpmg`) only
  need a longitudinal-recovery term during free-evolution delays where
  the relevant coherences are populations on Iz_i.
- The projection approach has no eigendecomposition of a superoperator,
  is O(D^2) per call, and stays inside the Hilbert-space representation
  the rest of the engine uses.

A full relaxation matrix (Solomon equations, NOE buildup, ...) is
planned for v1.0 in a new `liouville.py`.
"""
from __future__ import annotations

from typing import Optional

import numpy as np

from . import isotopes as iso_table
from .ops import operators
from .system import SpinSystem


def relax_T1(rho: np.ndarray,
             sys: SpinSystem,
             t: float,
             observed: Optional[str] = None) -> np.ndarray:
    """Apply per-spin longitudinal relaxation toward thermal equilibrium.

    Parameters
    ----------
    rho : current density matrix.
    sys : spin system. If `sys.T1` is None, `rho` is returned unchanged.
    t   : delay duration in seconds (>= 0).
    observed : if given, only spins of that isotope have a non-zero
        equilibrium polarization (matches the `thermal_high_temp(..., observed)`
        convention). Other spins relax toward 0 along Iz.

    Returns
    -------
    rho_new : density matrix after the delay.
    """
    if sys.T1 is None or t <= 0.0:
        return rho

    _, _, Iz = operators(sys.n)
    rho_new = rho.copy()
    for i in range(sys.n):
        T1_i = sys.T1[i]
        if not np.isfinite(T1_i) or T1_i <= 0.0:
            continue

        gamma_i = iso_table.get(sys.isotopes[i]).gamma_MHz_per_T
        a_eq = gamma_i if (observed is None or sys.isotopes[i] == observed) else 0.0

        norm = np.trace(Iz[i] @ Iz[i]).real          # = 2**(n-2) for I=1/2
        a_now = (np.trace(rho_new @ Iz[i]).real) / norm
        a_next = a_eq + (a_now - a_eq) * np.exp(-t / T1_i)

        rho_new = rho_new + (a_next - a_now) * Iz[i]

    return rho_new
