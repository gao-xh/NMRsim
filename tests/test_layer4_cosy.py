"""Layer 4 regression tests (`docs/SEQUENCES_PLAN.md`).

Acceptance:
- COSY on an AX ¹H system: peaks appear at (δ_A, δ_A), (δ_X, δ_X)
  (diagonal) and at (δ_A, δ_X), (δ_X, δ_A) (cross). Off-grid noise is
  well below the smallest of those four.
- COSY on an uncoupled two-spin system: only diagonal peaks, no cross.
- TOCSY on a linear AMX chain (J_AM, J_MX nonzero, J_AX = 0) at long
  enough mixing produces a cross peak between A and X (relayed via M),
  even though A and X are NOT directly coupled.
"""
from __future__ import annotations

import numpy as np

from src.core import HF, Acquisition, Acquisition2D, SpinSystem
from src.sequences import cosy, tocsy


def _acq2d(*, n_t1: int = 64, SW_t1_Hz: float = 6000.0,
           n_t2: int = 1024, SW_t2_Hz: float = 6000.0) -> Acquisition2D:
    t1 = Acquisition(n_points=n_t1, dt=1.0 / SW_t1_Hz,
                     t2_star=0.4, zero_fill=2, half_first=True,
                     apodization="exponential", lb_Hz=2.0)
    t2 = Acquisition(n_points=n_t2, dt=1.0 / SW_t2_Hz,
                     t2_star=0.4, zero_fill=2, half_first=True,
                     apodization="exponential", lb_Hz=2.0)
    return Acquisition2D(t1=t1, t2=t2)


def _peak_amp_at(res, *, f2_ppm: float, f1_ppm: float,
                 win_ppm: float = 0.25) -> float:
    """Return max |spectrum| within ±win_ppm of (f2, f1)."""
    f2_axis = res.ppm_F2
    f1_axis = res.ppm_F1
    j2 = np.where(np.abs(f2_axis - f2_ppm) <= win_ppm)[0]
    j1 = np.where(np.abs(f1_axis - f1_ppm) <= win_ppm)[0]
    if j1.size == 0 or j2.size == 0:
        return 0.0
    block = np.abs(res.spectrum[np.ix_(j1, j2)])
    return float(block.max())


# ---------------------------------------------------------------------------
# COSY tests
# ---------------------------------------------------------------------------

def test_cosy_AX_has_diagonal_and_cross_peaks():
    sys = SpinSystem(
        isotopes=['1H', '1H'],
        shifts_ppm=[2.0, 4.0],
        J_Hz=[[0.0, 7.0], [7.0, 0.0]],
    )
    regime = HF(B0_T=9.4, observed='1H', carrier_ppm=0.0)
    acq2d  = _acq2d()

    res = cosy(sys, regime, acq2d)

    a_diag = _peak_amp_at(res, f2_ppm=2.0, f1_ppm=2.0)
    x_diag = _peak_amp_at(res, f2_ppm=4.0, f1_ppm=4.0)
    ax_cross = _peak_amp_at(res, f2_ppm=2.0, f1_ppm=4.0)
    xa_cross = _peak_amp_at(res, f2_ppm=4.0, f1_ppm=2.0)
    # Noise floor at a chemical-shift position well away from any peak.
    noise = _peak_amp_at(res, f2_ppm=-4.0, f1_ppm=-4.0)

    for label, val in (("A diag", a_diag), ("X diag", x_diag),
                       ("AX cross", ax_cross), ("XA cross", xa_cross)):
        assert val > 10.0 * noise, f"{label} ({val:.3g}) not >> noise ({noise:.3g})"


def test_cosy_uncoupled_has_no_cross_peak():
    sys = SpinSystem(
        isotopes=['1H', '1H'],
        shifts_ppm=[2.0, 4.0],
        J_Hz=[[0.0, 0.0], [0.0, 0.0]],
    )
    regime = HF(B0_T=9.4, observed='1H', carrier_ppm=0.0)
    acq2d  = _acq2d()

    res = cosy(sys, regime, acq2d)

    a_diag = _peak_amp_at(res, f2_ppm=2.0, f1_ppm=2.0)
    x_diag = _peak_amp_at(res, f2_ppm=4.0, f1_ppm=4.0)
    ax_cross = _peak_amp_at(res, f2_ppm=2.0, f1_ppm=4.0)
    xa_cross = _peak_amp_at(res, f2_ppm=4.0, f1_ppm=2.0)

    min_diag = min(a_diag, x_diag)
    assert ax_cross < 0.05 * min_diag, \
        f"AX cross {ax_cross:.3g} should be << diagonal {min_diag:.3g}"
    assert xa_cross < 0.05 * min_diag, \
        f"XA cross {xa_cross:.3g} should be << diagonal {min_diag:.3g}"


# ---------------------------------------------------------------------------
# TOCSY test
# ---------------------------------------------------------------------------

def test_tocsy_relays_through_chain():
    """A-M-X chain (J_AM ≠ 0, J_MX ≠ 0, J_AX = 0). TOCSY should produce
    a relayed A↔X cross peak, which COSY does not."""
    J = np.array([
        [0.0, 7.0, 0.0],   # A-M = 7 Hz, A-X = 0
        [7.0, 0.0, 7.0],   # M-X = 7 Hz
        [0.0, 7.0, 0.0],
    ])
    sys = SpinSystem(
        isotopes=['1H', '1H', '1H'],
        shifts_ppm=[1.0, 3.0, 5.0],
        J_Hz=J,
    )
    regime = HF(B0_T=9.4, observed='1H', carrier_ppm=0.0)
    acq2d  = _acq2d(n_t1=96, SW_t1_Hz=6000.0,
                    n_t2=1024, SW_t2_Hz=6000.0)

    # 1) COSY: direct A↔X is essentially absent.
    res_c = cosy(sys, regime, acq2d)
    ax_cosy = _peak_amp_at(res_c, f2_ppm=1.0, f1_ppm=5.0)
    am_cosy = _peak_amp_at(res_c, f2_ppm=1.0, f1_ppm=3.0)
    assert ax_cosy < 0.1 * am_cosy, \
        f"COSY A-X cross ({ax_cosy:.3g}) should be << A-M ({am_cosy:.3g})"

    # 2) TOCSY with long mixing: A-X cross peak comparable to direct ones.
    res_t = tocsy(sys, regime, acq2d, mixing_time=0.080)  # 80 ms
    ax_tocsy = _peak_amp_at(res_t, f2_ppm=1.0, f1_ppm=5.0)
    am_tocsy = _peak_amp_at(res_t, f2_ppm=1.0, f1_ppm=3.0)
    aa_tocsy = _peak_amp_at(res_t, f2_ppm=1.0, f1_ppm=1.0)
    noise = _peak_amp_at(res_t, f2_ppm=-4.0, f1_ppm=-4.0)

    assert ax_tocsy > 10.0 * noise, \
        f"TOCSY A-X cross ({ax_tocsy:.3g}) not >> noise ({noise:.3g})"
    assert ax_tocsy > 0.2 * aa_tocsy, \
        f"TOCSY A-X relayed peak ({ax_tocsy:.3g}) should be sizeable " \
        f"vs A diagonal ({aa_tocsy:.3g})"


def test_tocsy_rejects_negative_mixing_time():
    sys = SpinSystem(['1H'], [0.0], [[0.0]])
    regime = HF(B0_T=9.4, observed='1H', carrier_ppm=0.0)
    acq2d  = _acq2d(n_t1=8, n_t2=64)
    try:
        tocsy(sys, regime, acq2d, mixing_time=-0.001)
    except ValueError:
        return
    raise AssertionError("expected ValueError for negative mixing_time")


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
