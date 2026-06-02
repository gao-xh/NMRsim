"""Detection operators."""
from __future__ import annotations

import numpy as np

from .ops import operators, Iplus
from .system import SpinSystem


def detect_Iplus(sys: SpinSystem, observed: str) -> np.ndarray:
    """Quadrature detection on a single channel.

    FID(t) = Tr[ρ(t) · I_+,obs].  Standard high-field liquid-NMR detection.
    """
    dim = 2 ** sys.n
    O = np.zeros((dim, dim), dtype=complex)
    for i in sys.indices_of(observed):
        O = O + Iplus(sys.n, i)
    return O


def detect_Mx(sys: SpinSystem, weighted: bool = True) -> np.ndarray:
    """Total transverse magnetization along x (ZULF magnetometer).

    If weighted=True, scale each spin by γ (signed) so the detected signal
    matches what a magnetometer measures.
    """
    Ix, _, _ = operators(sys.n)
    dim = 2 ** sys.n
    O = np.zeros((dim, dim), dtype=complex)
    from . import isotopes as iso_table
    for i in range(sys.n):
        w = iso_table.get(sys.isotopes[i]).gamma_MHz_per_T if weighted else 1.0
        O = O + w * Ix[i]
    return O


def detect_Mz(sys: SpinSystem, weighted: bool = True) -> np.ndarray:
    _, _, Iz = operators(sys.n)
    dim = 2 ** sys.n
    O = np.zeros((dim, dim), dtype=complex)
    from . import isotopes as iso_table
    for i in range(sys.n):
        w = iso_table.get(sys.isotopes[i]).gamma_MHz_per_T if weighted else 1.0
        O = O + w * Iz[i]
    return O
