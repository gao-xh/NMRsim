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


# ---------------------------------------------------------------------------
# 2D processing (States hypercomplex)
# ---------------------------------------------------------------------------

def _fft_axis(arr: np.ndarray,
              dt: float,
              *,
              axis: int,
              zero_fill: int,
              half_first: bool) -> tuple[np.ndarray, np.ndarray]:
    """1D FFT along one axis of an N-D array (fftshift'ed)."""
    x = arr
    if half_first:
        # Multiply slice 0 along this axis by 0.5.
        sl = [slice(None)] * arr.ndim
        sl[axis] = 0
        x = arr.copy()
        x[tuple(sl)] *= 0.5
    n_pad = x.shape[axis] * max(1, int(zero_fill))
    spec = np.fft.fftshift(np.fft.fft(x, n=n_pad, axis=axis), axes=axis) / n_pad
    freq = np.fft.fftshift(np.fft.fftfreq(n_pad, d=dt))
    return freq, spec


def fft2_hypercomplex(S_cos: np.ndarray,
                      S_sin: np.ndarray,
                      *,
                      dt_t1: float,
                      dt_t2: float,
                      zero_fill_t1: int = 1,
                      zero_fill_t2: int = 1,
                      half_first: bool = True
                      ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """States hypercomplex 2D FT.

    Inputs ``S_cos[k, j]`` and ``S_sin[k, j]`` are the two t1-modulated
    datasets (shape ``(n_t1, n_t2)``, complex in t2). The returned
    spectrum has pure (one-sided) F1 frequencies, no axial mirror.

    Recipe:
        1. FT along t2 of each set.
        2. Form hypercomplex c(t1, F2) = Ã(t1, F2) + i · B̃(t1, F2).
        3. Complex FT along t1.

    Returns
    -------
    freq_F1_Hz, freq_F2_Hz, spectrum (shape ``(n_F1, n_F2)``).
    """
    if S_cos.shape != S_sin.shape:
        raise ValueError(f"shape mismatch: {S_cos.shape} vs {S_sin.shape}")

    freq_F2, A = _fft_axis(S_cos, dt_t2, axis=1,
                           zero_fill=zero_fill_t2, half_first=half_first)
    _,       B = _fft_axis(S_sin, dt_t2, axis=1,
                           zero_fill=zero_fill_t2, half_first=half_first)

    C = A + 1j * B
    freq_F1, spec = _fft_axis(C, dt_t1, axis=0,
                              zero_fill=zero_fill_t1, half_first=half_first)
    return freq_F1, freq_F2, spec
