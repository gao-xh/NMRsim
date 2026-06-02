"""Isotope table: gyromagnetic ratio and spin quantum number.

Gyromagnetic ratios are in MHz/T, signed (sign matters for relative phase
of heteronuclear coherences and for thermal polarization sign).

Reference: IUPAC recommendations, Harris et al. 2001.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Isotope:
    name: str
    spin: float          # I (1/2, 1, 3/2, ...)
    gamma_MHz_per_T: float   # signed; γ/(2π) in MHz/T


# Built-in table. Extend as needed.
_TABLE: dict[str, Isotope] = {
    iso.name: iso for iso in [
        Isotope("1H",   0.5,  42.577478518),
        Isotope("2H",   1.0,   6.53590),       # deuterium (I=1, quadrupolar)
        Isotope("13C",  0.5,  10.7083965),
        Isotope("14N",  1.0,   3.077706),
        Isotope("15N",  0.5,  -4.31726882),    # negative gamma
        Isotope("19F",  0.5,  40.0775701),
        Isotope("29Si", 0.5,  -8.4654995),
        Isotope("31P",  0.5,  17.2514293),
    ]
}


def get(name: str) -> Isotope:
    if name not in _TABLE:
        raise KeyError(
            f"Unknown isotope '{name}'. Known: {sorted(_TABLE.keys())}"
        )
    return _TABLE[name]


def gamma_rad_per_s_per_T(name: str) -> float:
    """Angular gyromagnetic ratio in rad/(s*T)."""
    from math import pi
    return 2.0 * pi * 1e6 * get(name).gamma_MHz_per_T


def larmor_Hz(name: str, B0_T: float) -> float:
    """Larmor frequency in Hz at field B0 (T). Signed."""
    return get(name).gamma_MHz_per_T * 1e6 * B0_T
