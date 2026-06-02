"""Layer 2 regression tests (`docs/SEQUENCES_PLAN.md`).

Acceptance:
- Single isolated ¹H: spin echo at any τ gives a positive (in-phase)
  singlet, identical magnitude to pulse-acquire.
- AX ¹H system at τ = 1/(2J): the two doublet lines become anti-phase
  (opposite sign).
- Inversion recovery on a single ¹H with known T1: signal vs τ matches
  ``1 - 2·exp(-τ/T1)``.
- IR with no T1 set: every τ gives the same inverted spectrum.
- CPMG with n_echoes=0 reduces to a 90°-acquire.
- CPMG with n_echoes=1 matches the spin-echo at the same τ (within
  pulse-phase choice).
"""
from __future__ import annotations

import numpy as np

from src.core import HF, Acquisition, SpinSystem
from src.sequences import (
    cpmg,
    inversion_recovery,
    pulse_acquire,
    spin_echo,
)


def _hf_acq(SW_Hz: float = 4800.0,
            AQ_s: float = 2.0,
            t2_star: float | None = None) -> Acquisition:
    return Acquisition.from_sw_aq(
        SW_Hz=SW_Hz, AQ_s=AQ_s, t2_star=t2_star, zero_fill=2
    )


def _peak_amplitudes(freq: np.ndarray,
                     spec: np.ndarray,
                     targets_Hz,
                     half_window_Hz: float = 5.0):
    """Return the signed real-part amplitude (at FID(t=0) phase) of the
    largest |spec| in a window around each target frequency."""
    out = []
    for f0 in targets_Hz:
        mask = np.abs(freq - f0) <= half_window_Hz
        if not mask.any():
            out.append(0.0)
            continue
        local = spec[mask]
        k = int(np.argmax(np.abs(local)))
        out.append(local[k].real)
    return out


# ---------------------------------------------------------------------------
# spin_echo
# ---------------------------------------------------------------------------

def test_spin_echo_single_proton_matches_pulse_acquire():
    sys = SpinSystem(['1H'], [1.0], [[0.0]])
    regime = HF(B0_T=9.4, observed='1H', carrier_ppm=0.0)
    acq = _hf_acq()
    r_zg = pulse_acquire(sys, regime, acq)
    r_se = spin_echo(sys, regime, acq, tau=0.01)
    # Hahn echo on an isolated spin: identical magnitude spectrum.
    assert np.allclose(np.abs(r_zg.spectrum), np.abs(r_se.spectrum))


def test_spin_echo_AX_antiphase_at_total_time_1_over_2J():
    """AX at total echo time 2τ = 1/(2J) (i.e. τ = 1/(4J)): the final
    state is pure anti-phase 2 Ix_A Iz_B + 2 Ix_B Iz_A, with
    Tr(ρ · I+) = 0, so ``|FID[0]|`` collapses to ~ 0.
    """
    J = 7.0
    sys = SpinSystem(['1H', '1H'], [1.0, 3.0], [[0, J], [J, 0]])
    regime = HF(B0_T=9.4, observed='1H', carrier_ppm=2.0)
    acq = _hf_acq()

    r0 = spin_echo(sys, regime, acq, tau=0.0)
    r_anti = spin_echo(sys, regime, acq, tau=1.0 / (4.0 * J))

    s0 = abs(r0.fid[0])
    s_anti = abs(r_anti.fid[0])
    assert s_anti < 0.01 * s0, \
        f"expected |FID[0]| << in-phase at τ = 1/(4J), got {s_anti} vs {s0}"


# ---------------------------------------------------------------------------
# inversion_recovery
# ---------------------------------------------------------------------------

def _ir_signal_integral(sys, regime, acq, tau):
    """FID[0].imag tracks the pre-readout longitudinal magnetization.

    After 90°x readout, ρ ∝ -a Iy with ``a = M_z(τ)``. Then
    Tr(ρ · I+) = -i · a · Tr(Iy²), so the *imaginary* part of FID[0]
    is the relevant signal channel in our convention.
    """
    r = inversion_recovery(sys, regime, acq, tau=tau)
    return r.fid[0].imag


def test_inversion_recovery_recovers_T1():
    T1_true = 0.7  # seconds
    sys = SpinSystem(['1H'], [0.0], [[0.0]], T1=[T1_true])
    regime = HF(B0_T=9.4, observed='1H', carrier_ppm=0.0)
    acq = _hf_acq(AQ_s=0.5)

    # Reference (no inversion → equilibrium magnitude). Same imag channel.
    S_inf = pulse_acquire(sys, regime, acq).fid[0].imag

    taus = np.array([0.05, 0.2, 0.5, 1.0, 2.0])
    S = np.array([_ir_signal_integral(sys, regime, acq, t) for t in taus])

    # Bloch: S(τ) = S_inf * (1 - 2 exp(-τ/T1)). Fit T1 by least squares.
    # Equivalently: log((S_inf - S)/(2 S_inf)) = -τ/T1
    ratio = (S_inf - S) / (2.0 * S_inf)
    assert (ratio > 0).all(), f"non-positive ratios: {ratio}"
    y = np.log(ratio)
    slope, _ = np.polyfit(taus, y, 1)
    T1_fit = -1.0 / slope
    assert abs(T1_fit - T1_true) / T1_true < 0.01, \
        f"T1 fit {T1_fit:.4f} vs true {T1_true}"


def test_inversion_recovery_without_T1_stays_inverted():
    """Without T1, every τ should give the same fully-inverted signal."""
    sys = SpinSystem(['1H'], [0.0], [[0.0]])  # T1=None
    regime = HF(B0_T=9.4, observed='1H', carrier_ppm=0.0)
    acq = _hf_acq(AQ_s=0.5)
    s1 = _ir_signal_integral(sys, regime, acq, tau=0.1)
    s2 = _ir_signal_integral(sys, regime, acq, tau=2.0)
    s_zg = pulse_acquire(sys, regime, acq).fid[0].imag
    assert np.isclose(s1, s2)
    assert np.isclose(s1, -s_zg)


# ---------------------------------------------------------------------------
# cpmg
# ---------------------------------------------------------------------------

def test_cpmg_zero_echoes_equals_pulse_acquire():
    sys = SpinSystem(['1H'], [1.0], [[0.0]])
    regime = HF(B0_T=9.4, observed='1H', carrier_ppm=0.0)
    acq = _hf_acq()
    r_zg = pulse_acquire(sys, regime, acq)
    r_cp = cpmg(sys, regime, acq, tau=0.0, n_echoes=0)
    assert np.allclose(r_zg.fid, r_cp.fid)


def test_cpmg_one_echo_matches_spin_echo_with_y_pulse():
    sys = SpinSystem(['1H', '1H'], [1.0, 3.0], [[0, 7.0], [7.0, 0]])
    regime = HF(B0_T=9.4, observed='1H', carrier_ppm=2.0)
    acq = _hf_acq()
    tau = 0.005
    r_se = spin_echo(sys, regime, acq, tau=tau, pulse_phase_180=np.pi / 2)
    r_cp = cpmg(sys, regime, acq, tau=tau, n_echoes=1)
    assert np.allclose(r_se.fid, r_cp.fid)


def test_cpmg_rejects_negative_n_echoes():
    sys = SpinSystem(['1H'], [0.0], [[0.0]])
    regime = HF(B0_T=9.4, observed='1H', carrier_ppm=0.0)
    acq = _hf_acq()
    try:
        cpmg(sys, regime, acq, tau=0.001, n_echoes=-1)
    except ValueError:
        return
    raise AssertionError("expected ValueError for negative n_echoes")


if __name__ == "__main__":
    import sys as _sys
    failed = []
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS  {name}")
            except Exception as exc:  # noqa: BLE001
                failed.append((name, exc))
                print(f"FAIL  {name}: {exc!r}")
    _sys.exit(1 if failed else 0)
