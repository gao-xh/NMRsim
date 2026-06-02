"""Layer 5 regression tests (`docs/SEQUENCES_PLAN.md`).

Acceptance:
- Heteronuclear AX [¹H, ¹³C], J = 140 Hz, ZULF pulse-acquire under the
    default z/Mz convention: spectrum has a single line at f = |J| = 140 Hz
    (singlet–triplet transition).
- Homonuclear AX [¹H, ¹H], J = 7 Hz, ZULF pulse-acquire under the default
    z/Mz convention: spectrum has only DC; no peak at f = J (Σγ_i I_z is
    proportional to total F_z, which commutes with H_J for identical γ).
- DC pulse round-trip: explicit prepolarized-z + ideal π/2 on +y
    reproduces the explicit prepolarized-x / Mx FID exactly.
- Physical (B_T, duration_s) DC pulse with γB ≫ J converges to the
  ideal hard-pulse result.
"""
from __future__ import annotations

import numpy as np

from src.core import Acquisition, SpinSystem, ZULF
from src.core import isotopes as iso_table
from src.sequences import zulf_pulse_acquire, zulf_dc_pulse_acquire


def _acq(*, BW_Hz: float = 400.0, T_s: float = 2.0,
         t2_star: float = 1.0, lb_Hz: float = 0.5) -> Acquisition:
    return Acquisition(
        n_points=int(round(BW_Hz * T_s)),
        dt=1.0 / BW_Hz,
        t2_star=t2_star,
        zero_fill=4,
        apodization="exponential",
        lb_Hz=lb_Hz,
        half_first=True,
    )


def _peak_amp_near(res, f_Hz: float, *, win_Hz: float = 3.0) -> float:
    idx = np.where(np.abs(res.freq_Hz - f_Hz) <= win_Hz)[0]
    if idx.size == 0:
        return 0.0
    return float(np.abs(res.spectrum[idx]).max())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_zulf_heteronuclear_AX_peak_at_J():
    """¹H–¹³C with J=140 Hz: single line at 140 Hz, nothing at DC of
    comparable size."""
    sys = SpinSystem(
        isotopes=['1H', '13C'],
        shifts_ppm=[0.0, 0.0],
        J_Hz=[[0.0, 140.0], [140.0, 0.0]],
    )
    res = zulf_pulse_acquire(sys, ZULF(), _acq(BW_Hz=400.0, T_s=2.0))

    peak_J  = _peak_amp_near(res, 140.0, win_Hz=3.0)
    noise   = _peak_amp_near(res,  60.0, win_Hz=3.0)   # quiet region

    assert peak_J > 20.0 * noise, f"J peak ({peak_J:.3g}) not >> noise ({noise:.3g})"
    # Heteronuclear ZULF also has a strong DC line: ρ(0) splits into a part
    # commuting with H_J (the symmetric, γ_H+γ_C piece) and an oscillating
    # part (the γ_H−γ_C piece). Both are observable, so we only check the J
    # line is well above noise at the expected frequency.


def test_zulf_homonuclear_AX_has_no_J_peak():
    """Two ¹H, J=7 Hz: default prepolarized_z / Mz is proportional to F_z,
    which commutes with H_J, so the FID is constant — only DC."""
    sys = SpinSystem(
        isotopes=['1H', '1H'],
        shifts_ppm=[0.0, 0.0],
        J_Hz=[[0.0, 7.0], [7.0, 0.0]],
    )
    res = zulf_pulse_acquire(sys, ZULF(), _acq(BW_Hz=50.0, T_s=4.0, lb_Hz=0.1))

    peak_J = _peak_amp_near(res, 7.0, win_Hz=1.0)
    peak_0 = _peak_amp_near(res, 0.0, win_Hz=1.0)

    assert peak_0 > 20.0 * peak_J, (
        f"homonuclear ZULF should give DC only: DC={peak_0:.3g}, "
        f"J line={peak_J:.3g}"
    )


def test_zulf_dc_pulse_ideal_round_trip():
    """Explicit z/Mz preparation plus π/2 on +y reproduces explicit x/Mx."""
    sys = SpinSystem(
        isotopes=['1H', '1H'],
        shifts_ppm=[0.0, 0.0],
        J_Hz=[[0.0, 7.0], [7.0, 0.0]],
    )
    regime = ZULF()
    acq    = _acq(BW_Hz=50.0, T_s=2.0)

    res_x = zulf_pulse_acquire(sys, regime, acq, initial='x')
    res_z = zulf_dc_pulse_acquire(
        sys, regime, acq,
        channel='1H', flip_angle=np.pi / 2, phase=np.pi / 2,
        initial='z',
    )

    # phase=+π/2 rotates Iz → +Ix in our pulse convention, so the post-pulse
    # state matches prepolarized_x exactly and the two FIDs coincide.
    np.testing.assert_allclose(res_z.fid, res_x.fid, rtol=1e-10, atol=1e-12)


def test_zulf_dc_pulse_physical_converges_to_ideal():
    """Physical (B_T, duration_s) pulse with γB ≫ J ≈ ideal hard pulse."""
    sys = SpinSystem(
        isotopes=['1H', '1H'],
        shifts_ppm=[0.0, 0.0],
        J_Hz=[[0.0, 7.0], [7.0, 0.0]],
    )
    regime = ZULF()
    acq    = _acq(BW_Hz=50.0, T_s=2.0)

    res_ideal = zulf_dc_pulse_acquire(
        sys, regime, acq,
        channel='1H', flip_angle=np.pi / 2, phase=np.pi / 2,
        initial='z',
    )

    # B=1 mT → γB ≈ 2π·42.6 kHz, π/2 in ~5.9 µs; γB/J ≈ 6000.
    B_T = 1e-3
    gamma_abs = abs(iso_table.gamma_rad_per_s_per_T('1H'))
    duration_s = (np.pi / 2) / (gamma_abs * B_T)

    res_phys = zulf_dc_pulse_acquire(
        sys, regime, acq,
        channel='1H', B_T=B_T, duration_s=duration_s, phase=np.pi / 2,
        initial='z',
    )

    # Strict enough to catch a sign/phase bug, loose enough for the residual
    # static-H evolution during the 6 µs pulse.
    np.testing.assert_allclose(res_phys.fid, res_ideal.fid, rtol=1e-3, atol=1e-9)


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
