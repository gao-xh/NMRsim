"""Layer 1 regression tests (`docs/SEQUENCES_PLAN.md`).

Acceptance gates:
- AX ¹H system reproduces textbook doublet-of-doublets (4 lines, J survives).
- ¹³C{¹H} of an acetone-CH3 fragment gives one line under ideal decoupling
  and a quartet without it.
- A single isolated ¹H gives one line.
"""
from __future__ import annotations

import numpy as np

from src.core import HF, Acquisition, SpinSystem
from src.sequences import pulse_acquire, pulse_acquire_decoupled


def _count_peaks(spec: np.ndarray, threshold: float = 0.05) -> int:
    """Count local maxima of |spec| above `threshold * max(|spec|)`."""
    a = np.abs(spec)
    m = a.max()
    if m == 0.0:
        return 0
    cutoff = threshold * m
    # strict-greater than left, >= right (handles flat tops as single peak)
    n = 0
    for i in range(1, len(a) - 1):
        if a[i] >= cutoff and a[i] > a[i - 1] and a[i] >= a[i + 1]:
            n += 1
    return n


def _hf_acq(SW_Hz: float, AQ_s: float = 2.0, t2_star: float = 0.3) -> Acquisition:
    return Acquisition.from_sw_aq(
        SW_Hz=SW_Hz, AQ_s=AQ_s, t2_star=t2_star, zero_fill=2
    )


# ---------------------------------------------------------------------------
# pulse_acquire (zg)
# ---------------------------------------------------------------------------

def test_single_proton_one_peak():
    sys = SpinSystem(isotopes=['1H'], shifts_ppm=[1.0], J_Hz=[[0.0]])
    regime = HF(B0_T=9.4, observed='1H', carrier_ppm=0.0)
    acq = _hf_acq(SW_Hz=4800.0)
    result = pulse_acquire(sys, regime, acq)
    assert _count_peaks(result.spectrum) == 1


def test_AX_proton_gives_four_lines():
    """Two coupled ¹H (Δδ = 2 ppm at 9.4 T, J = 7 Hz) → two doublets = 4 lines."""
    sys = SpinSystem(
        isotopes=['1H', '1H'],
        shifts_ppm=[1.0, 3.0],
        J_Hz=[[0.0, 7.0], [7.0, 0.0]],
    )
    regime = HF(B0_T=9.4, observed='1H', carrier_ppm=2.0)
    acq = _hf_acq(SW_Hz=4800.0)
    result = pulse_acquire(sys, regime, acq)
    assert _count_peaks(result.spectrum) == 4


# ---------------------------------------------------------------------------
# pulse_acquire_decoupled (zgpg / zgig)
# ---------------------------------------------------------------------------

def _acetone_methyl_C13() -> SpinSystem:
    """One ¹³C coupled to three equivalent ¹H (1JCH = 125 Hz)."""
    n = 4
    J = np.zeros((n, n))
    J[0, 1:] = 125.0
    J[1:, 0] = 125.0
    return SpinSystem(
        isotopes=['13C', '1H', '1H', '1H'],
        shifts_ppm=[30.0, 2.1, 2.1, 2.1],
        J_Hz=J,
    )


def test_C13_methyl_coupled_is_quartet():
    sys = _acetone_methyl_C13()
    regime = HF(B0_T=9.4, observed='13C', carrier_ppm=100.0)
    # SW = 240 ppm * 100.6 MHz ~= 24 kHz; AQ shorter to keep test fast.
    acq = _hf_acq(SW_Hz=24000.0, AQ_s=1.0, t2_star=0.2)
    result = pulse_acquire(sys, regime, acq)
    assert _count_peaks(result.spectrum) == 4


def test_C13_methyl_decoupled_is_singlet():
    sys = _acetone_methyl_C13()
    regime = HF(B0_T=9.4, observed='13C', carrier_ppm=100.0)
    acq = _hf_acq(SW_Hz=24000.0, AQ_s=1.0, t2_star=0.2)
    result = pulse_acquire_decoupled(sys, regime, acq)  # decouple=None → all non-13C
    assert _count_peaks(result.spectrum) == 1


def test_decoupled_explicit_channel_equivalent_to_default():
    sys = _acetone_methyl_C13()
    regime = HF(B0_T=9.4, observed='13C', carrier_ppm=100.0)
    acq = _hf_acq(SW_Hz=24000.0, AQ_s=1.0, t2_star=0.2)
    r_default = pulse_acquire_decoupled(sys, regime, acq)
    r_explicit = pulse_acquire_decoupled(sys, regime, acq, decouple='1H')
    assert np.allclose(r_default.spectrum, r_explicit.spectrum)


def test_decoupled_rejects_observed_channel():
    sys = _acetone_methyl_C13()
    regime = HF(B0_T=9.4, observed='13C', carrier_ppm=100.0)
    acq = _hf_acq(SW_Hz=24000.0, AQ_s=1.0)
    try:
        pulse_acquire_decoupled(sys, regime, acq, decouple='13C')
    except ValueError:
        return
    raise AssertionError("expected ValueError when decoupling the observed channel")


if __name__ == "__main__":
    # Allow `python tests/test_layer1_1d.py` without pytest installed.
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
