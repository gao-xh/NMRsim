"""Regression tests for the manual main.py save/load helpers.

These cover the split-file workflow introduced for development-time use:
spin systems are saved in one JSON file, experiment parameters in a
second JSON file, and the pair must reconstruct the original case.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from src.core import Acquisition, Acquisition2D, HF, SpinSystem
from src.sequences import hsqc, pulse_acquire

import main


def _temp_paths() -> tuple[Path, Path]:
    root = Path(tempfile.mkdtemp())
    return root / "system.json", root / "parameters.json"


def _hf_1d_case() -> main.ExperimentCase:
    return main.ExperimentCase(
        name="hf_zg_1h",
        note="1D high-field pulse-acquire on a simple AX 1H system.",
        sequence=pulse_acquire,
        system=SpinSystem(
            isotopes=["1H", "1H"],
            shifts_ppm=[1.0, 3.0],
            J_Hz=[[0.0, 7.0], [7.0, 0.0]],
            label="AX 1H pair",
        ),
        regime=HF(B0_T=9.4, observed="1H", carrier_ppm=2.0),
        acquisition=Acquisition.from_sw_aq(
            SW_Hz=4800.0,
            AQ_s=2.0,
            t2_star=0.5,
            zero_fill=2,
            apodization="exponential",
            lb_Hz=1.0,
        ),
        kwargs={},
    )


def _hsqc_case() -> main.ExperimentCase:
    return main.ExperimentCase(
        name="hsqc_ch",
        note="2D HSQC on a single directly bonded 1H-13C pair.",
        sequence=hsqc,
        system=SpinSystem(
            isotopes=["1H", "13C"],
            shifts_ppm=[4.0, 50.0],
            J_Hz=[[0.0, 140.0], [140.0, 0.0]],
            label="1H-13C CH pair",
        ),
        regime=HF(B0_T=9.4, observed="1H", carrier_ppm=0.0),
        acquisition=Acquisition2D(
            t1=Acquisition(
                n_points=64,
                dt=1.0 / 16000.0,
                zero_fill=2,
                half_first=True,
            ),
            t2=Acquisition(
                n_points=1024,
                dt=1.0 / 6000.0,
                zero_fill=2,
                half_first=True,
            ),
        ),
        kwargs={"indirect": "13C", "J_CH": 140.0},
    )


def test_main_io_round_trip_hf_1d():
    case = _hf_1d_case()
    system_path, parameter_path = _temp_paths()

    main.save_system_file(case.system, system_path)
    main.save_parameters_file(case, parameter_path)
    loaded = main.load_case_from_files(system_path, parameter_path)

    assert loaded.name == case.name
    assert loaded.sequence.__name__ == case.sequence.__name__
    assert loaded.regime.name == case.regime.name
    assert loaded.regime.observed == case.regime.observed
    assert loaded.regime.B0_T == case.regime.B0_T
    assert loaded.regime.carrier_ppm == case.regime.carrier_ppm
    assert loaded.system.label == case.system.label
    assert loaded.system.isotopes == case.system.isotopes
    assert loaded.kwargs == case.kwargs

    res = main.run_case(loaded)
    assert res.ppm is not None
    assert res.spectrum.ndim == 1


def test_main_io_round_trip_hsqc_2d():
    case = _hsqc_case()
    system_path, parameter_path = _temp_paths()

    main.save_system_file(case.system, system_path)
    main.save_parameters_file(case, parameter_path)
    loaded = main.load_case_from_files(system_path, parameter_path)

    assert loaded.sequence.__name__ == case.sequence.__name__
    assert isinstance(loaded.acquisition, Acquisition2D)
    assert loaded.kwargs == case.kwargs
    assert loaded.acquisition.n_t1 == case.acquisition.n_t1
    assert loaded.acquisition.n_t2 == case.acquisition.n_t2

    res = main.run_case(loaded)
    assert res.spectrum.ndim == 2
    assert res.ppm_F1 is not None
    assert res.ppm_F2 is not None


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