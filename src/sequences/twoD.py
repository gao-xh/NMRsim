"""Generic 2D acquisition helpers shared by hetcor / homcor sequences.

For now this module exists to host the small loop pattern that all 2D
sequences use:

    for k in range(n_t1):
        t1 = k * dt_t1
        S_cos[k, :] = run_one(t1, quadrature='cos')
        S_sin[k, :] = run_one(t1, quadrature='sin')

Sequence-specific physics (HSQC, COSY, ...) lives in `hetcor.py` /
`homcor.py`; this file only owns the orchestration.
"""
from __future__ import annotations

from typing import Callable

import numpy as np

from src.core.acquisition import Acquisition2D


SinglePoint = Callable[[float, str], np.ndarray]
"""``one_point(t1, quadrature) -> t2_fid (complex array of length n_t2)``."""


def acquire2d_hypercomplex(one_point: SinglePoint,
                           acq2d: Acquisition2D) -> tuple[np.ndarray, np.ndarray]:
    """Build (S_cos, S_sin) arrays of shape (n_t1, n_t2) for States quadrature."""
    n_t1 = acq2d.n_t1
    n_t2 = acq2d.n_t2
    dt_t1 = acq2d.t1.dt

    S_cos = np.zeros((n_t1, n_t2), dtype=complex)
    S_sin = np.zeros((n_t1, n_t2), dtype=complex)

    for k in range(n_t1):
        t1 = k * dt_t1
        S_cos[k, :] = one_point(t1, 'cos')
        S_sin[k, :] = one_point(t1, 'sin')

    return S_cos, S_sin
