"""FID processing: apodization, zero-fill, FFT, axes."""
from __future__ import annotations

import numpy as np


def apodize_exponential(fid: np.ndarray, lb_Hz: float, dt: float) -> np.ndarray:
    """Multiply FID by exp(-π·LB·t) → Lorentz line of FWHM = LB."""
    if lb_Hz == 0.0:
        return fid.copy()
    t = np.arange(len(fid)) * dt
    return fid * np.exp(-np.pi * lb_Hz * t)


def apodize_gaussian(fid: np.ndarray, gb_Hz: float, dt: float) -> np.ndarray:
    """Multiply FID by Gaussian; gb_Hz ≈ FWHM (Hz)."""
    if gb_Hz == 0.0:
        return fid.copy()
    t = np.arange(len(fid)) * dt
    # exp(-(πt·GB)^2 / (4·ln2))  -> FWHM = GB
    a = (np.pi * gb_Hz) ** 2 / (4.0 * np.log(2.0))
    return fid * np.exp(-a * t * t)


def first_point_half(fid: np.ndarray) -> np.ndarray:
    out = fid.copy()
    out[0] *= 0.5
    return out


def fft_spectrum(
    fid: np.ndarray,
    dt: float,
    *,
    zero_fill: int = 1,
    half_first: bool = True,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (freq_Hz, spectrum). freq is centred (fftshift'ed)."""
    x = first_point_half(fid) if half_first else fid
    n = len(x) * max(1, int(zero_fill))
    spec = np.fft.fftshift(np.fft.fft(x, n=n)) / n
    freq = np.fft.fftshift(np.fft.fftfreq(n, d=dt))
    return freq, spec


def freq_to_ppm(freq_Hz: np.ndarray, larmor_Hz: float, carrier_ppm: float = 0.0) -> np.ndarray:
    """Convert offset-Hz axis to ppm using |ν0|.

    larmor_Hz is the Larmor frequency of the observed nucleus at B0
    (use absolute value; sign handled by data).
    """
    return carrier_ppm + freq_Hz / (abs(larmor_Hz) * 1e-6)
