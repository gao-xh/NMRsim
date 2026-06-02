"""Acquisition parameters: dwell time, number of points, broadening, zero-fill.

`Acquisition` bundles every experimentally tunable knob that is *not* a
property of the spin system or the regime. Sequence and plotting code
takes an `Acquisition` instead of loose keyword arguments, so callers
can store, share, and round-trip parameter sets.

Construction
------------
The natural inputs depend on the regime:

- HF spectroscopists think in (spectral width SW [Hz], acquisition time AQ [s]).
- ZULF / low-field thinks in (bandwidth BW [Hz], total duration T [s]).

Both reduce to (dt, n_points). Three factories cover the common entry
points; pick whichever matches your mental model.

Usage
-----
    from src.core import Acquisition

    # explicit (most precise)
    acq = Acquisition(n_points=8192, dt=1/4000, t2_star=0.5, zero_fill=2)

    # from spectral width and acquisition time
    acq = Acquisition.from_sw_aq(SW_Hz=4000, AQ_s=2.0, t2_star=0.5)

    # from bandwidth and total duration (ZULF style)
    acq = Acquisition.from_bw_duration(BW_Hz=200, T_s=10.0)
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional


@dataclass(frozen=True)
class Acquisition:
    """Acquisition / processing parameters.

    Attributes
    ----------
    n_points : number of complex FID samples.
    dt : dwell time (s). 1/dt is the spectral width (Hz).
    t2_star : optional Lorentz broadening time constant (s). None = no broadening.
    zero_fill : zero-fill factor for FFT (1 = no zero-fill).
    apodization : "none" | "exponential" | "gaussian".
    lb_Hz : line-broadening parameter for exponential window (Hz).
    gb_Hz : line-broadening parameter for Gaussian window (Hz, FWHM).
    half_first : multiply FID[0] by 0.5 before FFT (removes DC offset bias).
    """
    n_points: int
    dt: float
    t2_star: Optional[float] = None
    zero_fill: int = 1
    apodization: str = "none"
    lb_Hz: float = 0.0
    gb_Hz: float = 0.0
    half_first: bool = True

    # ------------------------------------------------------------------ derived

    @property
    def sw_Hz(self) -> float:
        """Spectral width (Hz)."""
        return 1.0 / self.dt

    @property
    def aq_s(self) -> float:
        """Total acquisition time (s)."""
        return self.n_points * self.dt

    # ------------------------------------------------------------------ factories

    @classmethod
    def from_sw_aq(cls,
                   SW_Hz: float,
                   AQ_s: float,
                   *,
                   t2_star: Optional[float] = None,
                   zero_fill: int = 1,
                   **kwargs) -> "Acquisition":
        """Build from spectral width and acquisition time (HF convention)."""
        dt = 1.0 / SW_Hz
        n = int(round(AQ_s / dt))
        return cls(n_points=n, dt=dt, t2_star=t2_star, zero_fill=zero_fill, **kwargs)

    @classmethod
    def from_bw_duration(cls,
                         BW_Hz: float,
                         T_s: float,
                         *,
                         t2_star: Optional[float] = None,
                         zero_fill: int = 1,
                         **kwargs) -> "Acquisition":
        """Build from bandwidth and total duration (ZULF / LF convention).

        Bandwidth = 1/dt; same numerically as SW. Provided as a separate
        factory because the mental model differs.
        """
        return cls.from_sw_aq(SW_Hz=BW_Hz, AQ_s=T_s,
                              t2_star=t2_star, zero_fill=zero_fill, **kwargs)

    # ------------------------------------------------------------------ helpers

    def with_(self, **changes) -> "Acquisition":
        """Return a copy with selected fields overridden."""
        return replace(self, **changes)


# ---------------------------------------------------------------------------
# Sensible regime-aware presets (use as starting points, not as constants).
# ---------------------------------------------------------------------------

def default_acq_HF_1H(B0_T: float, *, t2_star: float = 0.5) -> Acquisition:
    """Default 1D ¹H acquisition: SW = 12 ppm × ν0, AQ ≈ 2 s."""
    from .isotopes import larmor_Hz
    sw = 12.0 * 1e-6 * abs(larmor_Hz("1H", B0_T))
    return Acquisition.from_sw_aq(SW_Hz=sw, AQ_s=2.0, t2_star=t2_star)


def default_acq_HF_13C(B0_T: float, *, t2_star: float = 0.5) -> Acquisition:
    """Default 1D ¹³C acquisition: SW = 240 ppm × ν0, AQ ≈ 1 s."""
    from .isotopes import larmor_Hz
    sw = 240.0 * 1e-6 * abs(larmor_Hz("13C", B0_T))
    return Acquisition.from_sw_aq(SW_Hz=sw, AQ_s=1.0, t2_star=t2_star)


def default_acq_ZULF(*, BW_Hz: float = 200.0, T_s: float = 10.0,
                     t2_star: float = 2.0) -> Acquisition:
    """Default ZULF acquisition: BW = 200 Hz, T = 10 s."""
    return Acquisition.from_bw_duration(BW_Hz=BW_Hz, T_s=T_s, t2_star=t2_star)
