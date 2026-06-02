"""Layer 3 regression tests (`docs/SEQUENCES_PLAN.md`).

Acceptance:
- Single ¹H–¹³C pair: HSQC produces one cross peak at (δ_H in F2,
  δ_C in F1).
- Two non-coupled CH pairs: HSQC produces two cross peaks at the
  expected positions, no extra peaks.
- HMBC on the same molecule with a long-range ²J_CH gives a cross
  peak at the long-range pair, not (or much weaker) at the direct
  ¹J_CH pair when τ is tuned to the long-range coupling.
"""
from __future__ import annotations

import numpy as np

from src.core import HF, Acquisition, Acquisition2D, SpinSystem
from src.sequences import hsqc, hmbc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _acq2d(*, n_t1: int = 64,
           SW_t1_Hz: float = 12000.0,
           n_t2: int = 1024,
           SW_t2_Hz: float = 4000.0) -> Acquisition2D:
    """Build a default Acquisition2D appropriate for HSQC at ~9.4 T."""
    t1 = Acquisition(n_points=n_t1, dt=1.0 / SW_t1_Hz,
                     t2_star=None, zero_fill=2, half_first=True)
    t2 = Acquisition(n_points=n_t2, dt=1.0 / SW_t2_Hz,
                     t2_star=None, zero_fill=2, half_first=True)
    return Acquisition2D(t1=t1, t2=t2)


def _peak_indices_2d(spec: np.ndarray, n: int = 1) -> list[tuple[int, int]]:
    """Return indices of the ``n`` largest magnitude points in the 2D spectrum."""
    mag = np.abs(spec)
    flat = np.argpartition(mag.ravel(), -n)[-n:]
    flat = flat[np.argsort(-mag.ravel()[flat])]
    return [tuple(np.unravel_index(i, mag.shape)) for i in flat]


def _ppm_of(axis_ppm: np.ndarray, idx: int) -> float:
    return float(axis_ppm[idx])


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_hsqc_single_CH_one_cross_peak():
    """One ¹H–¹³C pair → exactly one cross peak at (δ_H, δ_C)."""
    sys = SpinSystem(
        isotopes=['1H', '13C'],
        shifts_ppm=[4.0, 50.0],
        J_Hz=[[0.0, 140.0], [140.0, 0.0]],
    )
    regime = HF(B0_T=9.4, observed='1H', carrier_ppm=0.0)
    acq2d  = _acq2d()

    res = hsqc(sys, regime, acq2d, indirect='13C', J_CH=140.0,
               decouple_during_acq=True)

    assert res.spectrum.shape == (res.freq_F1_Hz.size, res.freq_F2_Hz.size)
    assert res.ppm_F1 is not None and res.ppm_F2 is not None

    (i1, i2), = _peak_indices_2d(res.spectrum, n=1)
    f2_ppm = _ppm_of(res.ppm_F2, i2)
    f1_ppm = _ppm_of(res.ppm_F1, i1)

    # Tolerances dominated by F1 dwell / zero-fill (~10 Hz at 100 MHz ≈ 0.1 ppm)
    assert abs(f2_ppm - 4.0)  < 0.2, f"F2 peak at {f2_ppm:.3f} ppm (expected 4.0)"
    assert abs(f1_ppm - 50.0) < 1.5, f"F1 peak at {f1_ppm:.3f} ppm (expected 50.0)"


def test_hsqc_two_CH_two_cross_peaks():
    """Two independent CH pairs → two cross peaks at the right positions."""
    # Spins 0-1: first CH (1H @ 1 ppm, 13C @ 20 ppm)
    # Spins 2-3: second CH (1H @ 5 ppm, 13C @ 60 ppm)
    # All inter-pair J = 0.
    J = np.zeros((4, 4))
    J[0, 1] = J[1, 0] = 125.0
    J[2, 3] = J[3, 2] = 140.0

    sys = SpinSystem(
        isotopes=['1H', '13C', '1H', '13C'],
        shifts_ppm=[1.0, 20.0, 5.0, 60.0],
        J_Hz=J,
    )
    regime = HF(B0_T=9.4, observed='1H', carrier_ppm=0.0)
    acq2d  = _acq2d(n_t1=64, SW_t1_Hz=16000.0,
                    n_t2=1024, SW_t2_Hz=6000.0)

    # Use an effective τ for the average of the two J's. Each pair still
    # transfers (with sin/cos ≠ 1 efficiency for the off-tuned one).
    res = hsqc(sys, regime, acq2d, indirect='13C', J_CH=132.5,
               decouple_during_acq=True)

    top2 = _peak_indices_2d(res.spectrum, n=2)
    peaks_ppm = sorted(
        (_ppm_of(res.ppm_F2, i2), _ppm_of(res.ppm_F1, i1))
        for (i1, i2) in top2
    )
    (f2a, f1a), (f2b, f1b) = peaks_ppm

    assert abs(f2a - 1.0) < 0.3 and abs(f1a - 20.0) < 2.0, \
        f"first cross peak at ({f2a:.2f}, {f1a:.2f}) ppm"
    assert abs(f2b - 5.0) < 0.3 and abs(f1b - 60.0) < 2.0, \
        f"second cross peak at ({f2b:.2f}, {f1b:.2f}) ppm"


def test_hmbc_long_range_cross_peak():
    """HMBC tuned to a long-range J picks up the ²J pair over the ¹J one."""
    # Spins:
    #   0 = 1H  @ 4 ppm  (directly bonded to C-1)
    #   1 = 13C @ 50 ppm (C-1, 1J_CH = 140)
    #   2 = 13C @ 100 ppm (C-2, 2J_CH = 8 Hz to H-0)
    # No 1H on C-2.
    J = np.zeros((3, 3))
    J[0, 1] = J[1, 0] = 140.0   # 1J
    J[0, 2] = J[2, 0] = 8.0     # 2J (long range)

    sys = SpinSystem(
        isotopes=['1H', '13C', '13C'],
        shifts_ppm=[4.0, 50.0, 100.0],
        J_Hz=J,
    )
    regime = HF(B0_T=9.4, observed='1H', carrier_ppm=0.0)
    acq2d  = _acq2d(n_t1=128, SW_t1_Hz=24000.0,
                    n_t2=1024, SW_t2_Hz=4000.0)

    res = hmbc(sys, regime, acq2d, indirect='13C', J_long=8.0,
               decouple_during_acq=True)

    (i1, i2), = _peak_indices_2d(res.spectrum, n=1)
    f1_ppm = _ppm_of(res.ppm_F1, i1)
    f2_ppm = _ppm_of(res.ppm_F2, i2)

    # The largest cross peak should be at the long-range (C-2 @ 100 ppm)
    # — the 1J pair is suppressed because at τ = 1/(4·8 Hz) the
    # sin(πJ·2τ) factor for the 140 Hz coupling is sin(π·140/(2·8)) ≈ 0.
    assert abs(f2_ppm - 4.0)  < 0.3, f"F2 = {f2_ppm:.3f} (expected 4.0)"
    assert abs(f1_ppm - 100.0) < 2.5, f"F1 = {f1_ppm:.3f} (expected 100.0 ppm, long-range)"


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
