"""Pulse-sequence wrappers built on top of `src.core`.

Each sequence is a small function `(SpinSystem, Regime, Acquisition, **kw) ->
SimulationResult`. The wrappers compose primitives from `src.core.pulses`,
`src.core.engine`, and `src.core.simulate`; they do not own any physics.

Layer 1 (v0.2) — 1D basics:
    pulse_acquire              (Bruker `zg`)
    pulse_acquire_decoupled    (Bruker `zgpg` / `zgig`, ideal CW decoupling)

Higher layers (echo, IR, CPMG, 2D HSQC/COSY/TOCSY, ZULF) are added in
later milestones per `docs/SEQUENCES_PLAN.md`.
"""
from .oneD import pulse_acquire, pulse_acquire_decoupled

__all__ = ["pulse_acquire", "pulse_acquire_decoupled"]
