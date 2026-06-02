"""Pulse and propagator primitives.

This module owns *coherent manipulation* of the density matrix:
- ideal hard pulses on a chosen channel (`pulse`),
- free-evolution propagators (`propagator`),
- generic state evolution (`evolve`, `apply_unitary`).

It does NOT own:
- Hamiltonian construction (see `hamiltonian.py`),
- Final detection / FID assembly (see `engine.py`),
- Multi-event sequences (see `sequences/` package — to be added in v0.2).

Reserved extension points (deliberately stubbed, NOT YET IMPLEMENTED):
- shaped / frequency-selective pulses (`ShapedPulse` protocol)
- sequence event lists (`Event` protocol + `run_sequence`)

These stubs exist so future code can import them and so the module
boundary is clear; calling them today raises NotImplementedError.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import cos, sin
from typing import Iterable, List, Protocol, Sequence, Union

import numpy as np
from scipy.linalg import expm

from .ops import operators
from .system import SpinSystem


# ---------------------------------------------------------------------------
# Channel resolution
# ---------------------------------------------------------------------------

ChannelSpec = Union[str, int, Iterable[int]]
"""Channel can be:
- a nucleus label, e.g. '1H' — all spins of that isotope
- an int — single spin index
- an iterable of ints — explicit set of spin indices
"""


def _resolve_channel(sys: SpinSystem, channel: ChannelSpec) -> List[int]:
    if isinstance(channel, str):
        idx = sys.indices_of(channel)
        if not idx:
            raise ValueError(f"No spin of isotope {channel!r} in system")
        return idx
    if isinstance(channel, (int, np.integer)):
        return [int(channel)]
    return [int(i) for i in channel]


# ---------------------------------------------------------------------------
# Hard pulses
# ---------------------------------------------------------------------------

def pulse(sys: SpinSystem,
          channel: ChannelSpec,
          angle: float,
          phase: float = 0.0) -> np.ndarray:
    """Ideal hard-pulse propagator on a channel.

    U = exp(-i · angle · Σ_{i ∈ channel} (cosφ · Ix_i + sinφ · Iy_i))

    Parameters
    ----------
    angle : flip angle in radians (use np.pi/2 for 90°, np.pi for 180°)
    phase : pulse phase in radians (0 = x, π/2 = y, π = -x, 3π/2 = -y)

    Notes
    -----
    "Hard" means: instantaneous and uniform across all selected spins —
    Hamiltonian during the pulse contains only the RF term. Real spectro-
    meter pulses have finite duration and bandwidth; see `ShapedPulse`
    (not yet implemented) for that case.
    """
    idx = _resolve_channel(sys, channel)
    Ix, Iy, _ = operators(sys.n)
    R = np.zeros((2 ** sys.n, 2 ** sys.n), dtype=complex)
    cphi, sphi = cos(phase), sin(phase)
    for i in idx:
        R = R + cphi * Ix[i] + sphi * Iy[i]
    return expm(-1j * angle * R)


def pulse_x(sys: SpinSystem, channel: ChannelSpec, angle: float) -> np.ndarray:
    return pulse(sys, channel, angle, 0.0)


def pulse_y(sys: SpinSystem, channel: ChannelSpec, angle: float) -> np.ndarray:
    return pulse(sys, channel, angle, np.pi / 2)


# ---------------------------------------------------------------------------
# Propagators and evolution
# ---------------------------------------------------------------------------

def propagator(H: np.ndarray, t: float) -> np.ndarray:
    """U = exp(-i H t) via eigendecomposition.

    For Hermitian H, this is numerically stable and avoids a full matrix
    exponential. Cached eigensystem is not reused across calls because the
    caller may pass different H's; if you need repeated propagators with
    the *same* H, decompose once via `EigenSystem.of(H)` and build U
    yourself.
    """
    w, V = np.linalg.eigh(H)
    return (V * np.exp(-1j * w * t)) @ V.conj().T


def apply_unitary(rho: np.ndarray, U: np.ndarray) -> np.ndarray:
    """ρ → U ρ U†. Use for pulses and other unitary operations."""
    return U @ rho @ U.conj().T


def evolve(rho: np.ndarray, H: np.ndarray, t: float) -> np.ndarray:
    """Free evolution under H for time t."""
    U = propagator(H, t)
    return apply_unitary(rho, U)


# ---------------------------------------------------------------------------
# Reserved extension points (NOT YET IMPLEMENTED)
# ---------------------------------------------------------------------------

class ShapedPulse(Protocol):
    """Future protocol for frequency-selective / shaped pulses.

    Implementations will return a propagator built from a time-discretised
    RF waveform `B1(t)` integrated under the channel Hamiltonian.
    Reserved for v0.6+.
    """
    def propagator(self, sys: SpinSystem, H_static: np.ndarray) -> np.ndarray: ...


class Event(Protocol):
    """Future protocol for sequence-DSL events (pulse / delay / acquire / ...).

    A sequence will be a list of `Event`s; `run_sequence` will fold them
    into a final ρ (or FID for the terminal acquire). Reserved for v0.5+.
    """
    name: str
    def apply(self, sys: SpinSystem, regime, rho: np.ndarray, H: np.ndarray): ...


def run_sequence(*args, **kwargs):
    """Placeholder for the future event-list runner. Raises until implemented."""
    raise NotImplementedError(
        "run_sequence is a v0.5+ feature; use procedural sequence functions "
        "in src/sequences/ for now."
    )
