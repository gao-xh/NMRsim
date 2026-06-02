"""Spin system definition: what the molecule is."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from . import isotopes as iso_table


@dataclass
class SpinSystem:
    """A liquid-state spin system.

    Parameters
    ----------
    isotopes : list[str]
        Per-spin isotope label, e.g. ['1H','1H','13C'].
    shifts_ppm : np.ndarray, shape (N,)
        Isotropic chemical shifts in ppm of each spin's own nucleus.
        For ZULF-only simulations the values are ignored (shifts collapse).
    J_Hz : np.ndarray, shape (N, N)
        Symmetric scalar coupling matrix in Hz. Diagonal must be zero.
    label : str
        Optional human-readable name.
    """
    isotopes: List[str]
    shifts_ppm: np.ndarray
    J_Hz: np.ndarray
    label: str = ""

    # Derived
    n: int = field(init=False)

    def __post_init__(self):
        self.n = len(self.isotopes)
        self.shifts_ppm = np.asarray(self.shifts_ppm, dtype=float)
        self.J_Hz = np.asarray(self.J_Hz, dtype=float)
        self._validate()

    def _validate(self):
        if self.shifts_ppm.shape != (self.n,):
            raise ValueError(
                f"shifts_ppm shape {self.shifts_ppm.shape} != ({self.n},)"
            )
        if self.J_Hz.shape != (self.n, self.n):
            raise ValueError(
                f"J_Hz shape {self.J_Hz.shape} != ({self.n}, {self.n})"
            )
        if not np.allclose(self.J_Hz, self.J_Hz.T):
            raise ValueError("J_Hz must be symmetric")
        if not np.allclose(np.diag(self.J_Hz), 0.0):
            raise ValueError("J_Hz diagonal must be zero")
        for name in self.isotopes:
            iso = iso_table.get(name)
            if iso.spin != 0.5:
                raise NotImplementedError(
                    f"Only I=1/2 supported, got {name} (I={iso.spin})"
                )

    def indices_of(self, isotope: str) -> List[int]:
        return [i for i, n in enumerate(self.isotopes) if n == isotope]

    def gammas_MHz_per_T(self) -> np.ndarray:
        return np.array(
            [iso_table.get(n).gamma_MHz_per_T for n in self.isotopes]
        )
