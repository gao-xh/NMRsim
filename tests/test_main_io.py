"""Regression tests for the manual main.py save/load helpers.

These cover the split-file workflow introduced for development-time use:
spin systems are saved in one JSON file, experiment parameters in a
second JSON file, and the pair must reconstruct the original case.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from src.core import Acquisition2D

import main


def _temp_paths() -> tuple[Path, Path]:
    root = Path(tempfile.mkdtemp())
    return root / "system.json", root / "parameters.json"


def test_main_io_round_trip_hf_1d():
    case = main.preset_hf_zg_1h()
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
    case = main.preset_hsqc_ch()
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