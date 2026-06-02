"""Spin-1/2 operator factory.

Internal convention:
- All operators returned in the full 2**n Hilbert space (Kronecker-expanded).
- Cached per n so repeated simulations on the same system don't rebuild.

Restriction: currently I=1/2 only. Extending to higher spin requires
replacing `_PAULI` with a general spin-operator builder.
"""
from __future__ import annotations

from functools import lru_cache
from typing import List, Tuple

import numpy as np

# Spin-1/2 operators (with the 1/2 factor — i.e. actual angular momentum, not Pauli).
_SX = np.array([[0,    0.5 ], [0.5,  0  ]], dtype=complex)
_SY = np.array([[0,   -0.5j], [0.5j, 0  ]], dtype=complex)
_SZ = np.array([[0.5,  0  ], [0,   -0.5]], dtype=complex)
_E  = np.eye(2, dtype=complex)


def _kron_chain(mats: List[np.ndarray]) -> np.ndarray:
    out = mats[0]
    for m in mats[1:]:
        out = np.kron(out, m)
    return out


@lru_cache(maxsize=16)
def operators(n: int) -> Tuple[Tuple[np.ndarray, ...],
                                Tuple[np.ndarray, ...],
                                Tuple[np.ndarray, ...]]:
    """Return (Ix, Iy, Iz) — each a length-n tuple of (2**n, 2**n) arrays.

    Cached: the same n yields the same arrays (do not mutate them).
    """
    if n < 1:
        raise ValueError("n must be >= 1")
    Ix, Iy, Iz = [], [], []
    for i in range(n):
        chain_x = [(_SX if j == i else _E) for j in range(n)]
        chain_y = [(_SY if j == i else _E) for j in range(n)]
        chain_z = [(_SZ if j == i else _E) for j in range(n)]
        Ix.append(_kron_chain(chain_x))
        Iy.append(_kron_chain(chain_y))
        Iz.append(_kron_chain(chain_z))
    return tuple(Ix), tuple(Iy), tuple(Iz)


def Iplus(n: int, i: int) -> np.ndarray:
    """I+ = Ix + i Iy for spin i in an n-spin system."""
    _, Iy, _ = operators(n)
    Ix, _, _ = operators(n)
    return Ix[i] + 1j * Iy[i]


def Iminus(n: int, i: int) -> np.ndarray:
    Ix, Iy, _ = operators(n)
    return Ix[i] - 1j * Iy[i]


@lru_cache(maxsize=16)
def identity(n: int) -> np.ndarray:
    return np.eye(2 ** n, dtype=complex)
