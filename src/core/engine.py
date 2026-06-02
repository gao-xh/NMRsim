"""Simulation engine: diagonalize H, produce FID or stick spectrum.

Two equivalent pathways, both implemented:

  (1) fid(...)       : time-domain. Useful when you need to apply windowing,
                       zero-filling, or non-trivial processing later.
  (2) stick(...)     : frequency-domain. Returns a list of (frequency, complex
                       amplitude) lines; convolve with a line-shape to plot.

Both compute via eigendecomposition once and reuse.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import pi
from typing import Tuple

import numpy as np


@dataclass
class EigenSystem:
    """Cached eigendecomposition of a Hamiltonian."""
    evals_rad_s: np.ndarray              # shape (D,)
    evecs: np.ndarray                    # shape (D, D), columns = eigenvectors

    @classmethod
    def of(cls, H: np.ndarray) -> "EigenSystem":
        w, V = np.linalg.eigh(H)
        return cls(evals_rad_s=w, evecs=V)


def stick_spectrum(
    H: np.ndarray,
    rho0: np.ndarray,
    detect: np.ndarray,
    *,
    min_weight: float = 1e-10,
) -> Tuple[np.ndarray, np.ndarray]:
    """Frequency-domain stick spectrum.

    Returns
    -------
    freqs_Hz : (M,) real array, transition frequencies (signed)
    weights  : (M,) complex array, transition amplitudes

    The signal model is
        FID(t) = Tr[ U(t) ρ0 U(t)† · O ]
               = Σ_{m,n}  (ρ0)_{nm} (O)_{mn} · exp(i(E_m - E_n) t)
    with everything in the eigenbasis of H.
    """
    es = EigenSystem.of(H)
    V = es.evecs
    Vd = V.conj().T

    rho_e = Vd @ rho0   @ V
    O_e   = Vd @ detect @ V

    # ω_mn = (E_m - E_n) / (2π)  → Hz
    omega = es.evals_rad_s
    f_mn = (omega[:, None] - omega[None, :]) / (2.0 * pi)
    w_mn = rho_e.T * O_e          # (ρ0)_{nm} * (O)_{mn} via element-wise on transposed rho
    # ^ rho_e.T[m,n] = rho_e[n,m] = (ρ0)_{nm}; O_e[m,n] = (O)_{mn}

    mask = np.abs(w_mn) > min_weight
    return f_mn[mask], w_mn[mask]


def fid(
    H: np.ndarray,
    rho0: np.ndarray,
    detect: np.ndarray,
    *,
    n_points: int,
    dt: float,
    t2_star: float | None = None,
) -> np.ndarray:
    """Time-domain FID via eigenbasis evolution.

    Parameters
    ----------
    n_points : number of complex samples
    dt       : dwell time (s)
    t2_star  : if given, multiply by exp(-t/T2*) (Lorentz broadening)

    Returns
    -------
    fid : (n_points,) complex array; fid[k] = Tr[ρ(k·dt) · O]
    """
    es = EigenSystem.of(H)
    V = es.evecs
    Vd = V.conj().T
    rho_e = Vd @ rho0   @ V
    O_e   = Vd @ detect @ V

    omega = es.evals_rad_s
    # G_{mn} = (ρ0)_{nm} (O)_{mn}, summed with phase exp(i(E_m - E_n) t)
    G = rho_e.T * O_e                                       # (D, D)
    domega = omega[:, None] - omega[None, :]                # (D, D)

    t = np.arange(n_points) * dt                            # (T,)
    # FID[k] = Σ_{m,n} G_{mn} exp(i ω_{mn} t_k)
    phases = np.exp(1j * domega[None, :, :] * t[:, None, None])  # (T,D,D)
    fid = np.einsum("mn,kmn->k", G, phases)

    if t2_star is not None and t2_star > 0:
        fid = fid * np.exp(-t / t2_star)
    return fid
