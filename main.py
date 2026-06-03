"""Manual entry point for running NMRsim without a UI.

Edit the CONFIG block below, then run:

    python main.py

This file is intentionally plain Python rather than a CLI parser so you
can tweak systems, regimes, acquisitions, and sequence kwargs directly
in code while developing / validating the engine.

Two usage modes are supported:

- ``mode='preset'``: build an experiment from one of the Python presets
    below. Optional save hooks can write the spin system and experiment
    parameters as separate JSON files.
- ``mode='files'``: load a spin system JSON and an experiment-parameter
    JSON, then run the experiment without editing the preset functions.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Callable, Dict, Union

import numpy as np

from src.core import Acquisition, Acquisition2D, HF, LF, SpinSystem, ZULF
from src.sequences import (
    cosy,
    cpmg,
    hmbc,
    hsqc,
    inversion_recovery,
    pulse_acquire,
    pulse_acquire_decoupled,
    spin_echo,
    tocsy,
    zulf_dc_pulse_acquire,
    zulf_j_spectrum,
    zulf_pulse_acquire,
)


Result1D = Any
Result2D = Any
SequenceFn = Callable[..., Union[Result1D, Result2D]]


@dataclass(frozen=True)
class ExperimentCase:
    name: str
    note: str
    sequence: SequenceFn
    system: SpinSystem
    regime: Any
    acquisition: Union[Acquisition, Acquisition2D]
    kwargs: Dict[str, Any]


SAVE_FORMAT_VERSION = 1
USER_SAVE_DIR = Path("user_save")
MOLECULE_SAVE_DIR = USER_SAVE_DIR / "molecules"
PARAMETER_SAVE_DIR = USER_SAVE_DIR / "parameters"


# ---------------------------------------------------------------------------
# Editable config: pick one preset and optional plot behavior.
# ---------------------------------------------------------------------------

CONFIG = {
    "mode": "preset",   # 'preset' | 'files'
    "preset": "hf_zg_1h",
    "system_file": None,
    "parameters_file": None,
    "save_system_as": None,       # e.g. 'user_save/molecules/my_ax.json'
    "save_parameters_as": None,   # e.g. 'user_save/parameters/my_hsqc.json'
    "show_plot": True,
    "save_plot": None,   # e.g. "outputs/zulf_j_ax.png"
    "print_top_peaks": 8,
}


# ---------------------------------------------------------------------------
# Save / load helpers.
# ---------------------------------------------------------------------------

def _jsonify(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _jsonify(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonify(v) for v in value]
    return value


def _write_json(path: str | Path, payload: dict[str, Any]) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def system_to_dict(sys: SpinSystem) -> dict[str, Any]:
    return {
        "version": SAVE_FORMAT_VERSION,
        "kind": "spin_system",
        "label": sys.label,
        "isotopes": list(sys.isotopes),
        "shifts_ppm": _jsonify(sys.shifts_ppm),
        "J_Hz": _jsonify(sys.J_Hz),
        "T1": None if sys.T1 is None else _jsonify(sys.T1),
    }


def system_from_dict(data: dict[str, Any]) -> SpinSystem:
    if data.get("kind") != "spin_system":
        raise ValueError(f"expected kind='spin_system', got {data.get('kind')!r}")
    return SpinSystem(
        isotopes=list(data["isotopes"]),
        shifts_ppm=np.asarray(data["shifts_ppm"], dtype=float),
        J_Hz=np.asarray(data["J_Hz"], dtype=float),
        T1=(None if data.get("T1") is None else np.asarray(data["T1"], dtype=float)),
        label=str(data.get("label", "")),
    )


def regime_to_dict(regime: Any) -> dict[str, Any]:
    if regime.name == "HF":
        return {
            "kind": "HF",
            "B0_T": regime.B0_T,
            "observed": regime.observed,
            "carrier_ppm": regime.carrier_ppm,
        }
    if regime.name == "ZULF":
        return {"kind": "ZULF"}
    if regime.name == "LF":
        return {
            "kind": "LF",
            "B0_T": regime.B0_T,
        }
    raise ValueError(f"unsupported regime for save/load: {regime.name!r}")


def regime_from_dict(data: dict[str, Any]) -> Any:
    kind = data.get("kind")
    if kind == "HF":
        return HF(
            B0_T=float(data["B0_T"]),
            observed=str(data["observed"]),
            carrier_ppm=float(data.get("carrier_ppm", 0.0)),
        )
    if kind == "ZULF":
        return ZULF()
    if kind == "LF":
        return LF(B0_T=float(data["B0_T"]))
    raise ValueError(f"unsupported regime kind: {kind!r}")


def acquisition1d_to_dict(acq: Acquisition) -> dict[str, Any]:
    return {
        "kind": "Acquisition1D",
        "n_points": acq.n_points,
        "dt": acq.dt,
        "t2_star": acq.t2_star,
        "zero_fill": acq.zero_fill,
        "apodization": acq.apodization,
        "lb_Hz": acq.lb_Hz,
        "gb_Hz": acq.gb_Hz,
        "half_first": acq.half_first,
    }


def acquisition_to_dict(acq: Union[Acquisition, Acquisition2D]) -> dict[str, Any]:
    if isinstance(acq, Acquisition2D):
        return {
            "kind": "Acquisition2D",
            "t1": acquisition1d_to_dict(acq.t1),
            "t2": acquisition1d_to_dict(acq.t2),
        }
    return acquisition1d_to_dict(acq)


def acquisition1d_from_dict(data: dict[str, Any]) -> Acquisition:
    return Acquisition(
        n_points=int(data["n_points"]),
        dt=float(data["dt"]),
        t2_star=(None if data.get("t2_star") is None else float(data["t2_star"])),
        zero_fill=int(data.get("zero_fill", 1)),
        apodization=str(data.get("apodization", "none")),
        lb_Hz=float(data.get("lb_Hz", 0.0)),
        gb_Hz=float(data.get("gb_Hz", 0.0)),
        half_first=bool(data.get("half_first", True)),
    )


def acquisition_from_dict(data: dict[str, Any]) -> Union[Acquisition, Acquisition2D]:
    kind = data.get("kind")
    if kind == "Acquisition1D":
        return acquisition1d_from_dict(data)
    if kind == "Acquisition2D":
        return Acquisition2D(
            t1=acquisition1d_from_dict(data["t1"]),
            t2=acquisition1d_from_dict(data["t2"]),
        )
    raise ValueError(f"unsupported acquisition kind: {kind!r}")


def save_system_file(sys: SpinSystem, path: str | Path) -> None:
    _write_json(path, system_to_dict(sys))


def load_system_file(path: str | Path) -> SpinSystem:
    return system_from_dict(_read_json(path))


def parameters_to_dict(case: ExperimentCase) -> dict[str, Any]:
    return {
        "version": SAVE_FORMAT_VERSION,
        "kind": "experiment_parameters",
        "name": case.name,
        "note": case.note,
        "sequence": case.sequence.__name__,
        "regime": regime_to_dict(case.regime),
        "acquisition": acquisition_to_dict(case.acquisition),
        "kwargs": _jsonify(case.kwargs),
    }


def save_parameters_file(case: ExperimentCase, path: str | Path) -> None:
    _write_json(path, parameters_to_dict(case))


def _sequence_registry() -> dict[str, SequenceFn]:
    return {
        fn.__name__: fn
        for fn in (
            pulse_acquire,
            pulse_acquire_decoupled,
            spin_echo,
            inversion_recovery,
            cpmg,
            hsqc,
            hmbc,
            cosy,
            tocsy,
            zulf_pulse_acquire,
            zulf_j_spectrum,
            zulf_dc_pulse_acquire,
        )
    }


def load_case_from_files(system_path: str | Path,
                         parameter_path: str | Path) -> ExperimentCase:
    system = load_system_file(system_path)
    data = _read_json(parameter_path)
    if data.get("kind") != "experiment_parameters":
        raise ValueError(
            f"expected kind='experiment_parameters', got {data.get('kind')!r}"
        )

    sequence_name = str(data["sequence"])
    registry = _sequence_registry()
    if sequence_name not in registry:
        known = ", ".join(sorted(registry))
        raise ValueError(f"unknown sequence {sequence_name!r}; known: {known}")

    return ExperimentCase(
        name=str(data.get("name", sequence_name)),
        note=str(data.get("note", "")),
        sequence=registry[sequence_name],
        system=system,
        regime=regime_from_dict(data["regime"]),
        acquisition=acquisition_from_dict(data["acquisition"]),
        kwargs=dict(data.get("kwargs", {})),
    )


def maybe_save_case_files(case: ExperimentCase) -> None:
    system_path = CONFIG.get("save_system_as")
    parameter_path = CONFIG.get("save_parameters_as")

    if system_path:
        save_system_file(case.system, system_path)
        print(f"Saved system file      : {Path(system_path)}")
    if parameter_path:
        save_parameters_file(case, parameter_path)
        print(f"Saved parameter file   : {Path(parameter_path)}")


# ---------------------------------------------------------------------------
# Example experiment presets.
# ---------------------------------------------------------------------------

def preset_hf_zg_1h() -> ExperimentCase:
    sys = SpinSystem(
        isotopes=["1H", "1H"],
        shifts_ppm=[1.0, 3.0],
        J_Hz=[[0.0, 7.0], [7.0, 0.0]],
        label="AX 1H pair",
    )
    regime = HF(B0_T=9.4, observed="1H", carrier_ppm=2.0)
    acq = Acquisition.from_sw_aq(
        SW_Hz=4800.0,
        AQ_s=2.0,
        t2_star=0.5,
        zero_fill=2,
        apodization="exponential",
        lb_Hz=1.0,
    )
    return ExperimentCase(
        name="hf_zg_1h",
        note="1D high-field pulse-acquire on a simple AX 1H system.",
        sequence=pulse_acquire,
        system=sys,
        regime=regime,
        acquisition=acq,
        kwargs={},
    )


def preset_hf_spin_echo() -> ExperimentCase:
    sys = SpinSystem(
        isotopes=["1H", "1H"],
        shifts_ppm=[1.0, 3.0],
        J_Hz=[[0.0, 7.0], [7.0, 0.0]],
        label="AX 1H pair",
    )
    regime = HF(B0_T=9.4, observed="1H", carrier_ppm=2.0)
    acq = Acquisition.from_sw_aq(
        SW_Hz=4800.0,
        AQ_s=2.0,
        t2_star=0.5,
        zero_fill=2,
        apodization="exponential",
        lb_Hz=1.0,
    )
    return ExperimentCase(
        name="hf_spin_echo",
        note="1D Hahn echo; tau = 1/(4J) gives the standard AX antiphase check.",
        sequence=spin_echo,
        system=sys,
        regime=regime,
        acquisition=acq,
        kwargs={"tau": 1.0 / (4.0 * 7.0)},
    )


def preset_hf_ir_single() -> ExperimentCase:
    sys = SpinSystem(
        isotopes=["1H"],
        shifts_ppm=[0.0],
        J_Hz=[[0.0]],
        T1=[0.7],
        label="Single proton with T1",
    )
    regime = HF(B0_T=9.4, observed="1H", carrier_ppm=0.0)
    acq = Acquisition.from_sw_aq(
        SW_Hz=4800.0,
        AQ_s=0.5,
        t2_star=0.3,
        zero_fill=2,
        apodization="exponential",
        lb_Hz=1.0,
    )
    return ExperimentCase(
        name="hf_ir_single",
        note="1D inversion-recovery snapshot at one tau value.",
        sequence=inversion_recovery,
        system=sys,
        regime=regime,
        acquisition=acq,
        kwargs={"tau": 0.5},
    )


def preset_hsqc_ch() -> ExperimentCase:
    sys = SpinSystem(
        isotopes=["1H", "13C"],
        shifts_ppm=[4.0, 50.0],
        J_Hz=[[0.0, 140.0], [140.0, 0.0]],
        label="1H-13C CH pair",
    )
    regime = HF(B0_T=9.4, observed="1H", carrier_ppm=0.0)
    acq2d = Acquisition2D(
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
    )
    return ExperimentCase(
        name="hsqc_ch",
        note="2D HSQC on a single directly bonded 1H-13C pair.",
        sequence=hsqc,
        system=sys,
        regime=regime,
        acquisition=acq2d,
        kwargs={"indirect": "13C", "J_CH": 140.0},
    )


def preset_cosy_ax() -> ExperimentCase:
    sys = SpinSystem(
        isotopes=["1H", "1H"],
        shifts_ppm=[2.0, 4.0],
        J_Hz=[[0.0, 7.0], [7.0, 0.0]],
        label="AX homonuclear pair",
    )
    regime = HF(B0_T=9.4, observed="1H", carrier_ppm=0.0)
    acq2d = Acquisition2D(
        t1=Acquisition(
            n_points=64,
            dt=1.0 / 6000.0,
            t2_star=0.4,
            zero_fill=2,
            half_first=True,
            apodization="exponential",
            lb_Hz=2.0,
        ),
        t2=Acquisition(
            n_points=1024,
            dt=1.0 / 6000.0,
            t2_star=0.4,
            zero_fill=2,
            half_first=True,
            apodization="exponential",
            lb_Hz=2.0,
        ),
    )
    return ExperimentCase(
        name="cosy_ax",
        note="2D COSY-90 with diagonal and cross peaks.",
        sequence=cosy,
        system=sys,
        regime=regime,
        acquisition=acq2d,
        kwargs={},
    )


def preset_tocsy_amx() -> ExperimentCase:
    sys = SpinSystem(
        isotopes=["1H", "1H", "1H"],
        shifts_ppm=[1.0, 3.0, 5.0],
        J_Hz=[[0.0, 7.0, 0.0], [7.0, 0.0, 7.0], [0.0, 7.0, 0.0]],
        label="A-M-X proton chain",
    )
    regime = HF(B0_T=9.4, observed="1H", carrier_ppm=0.0)
    acq2d = Acquisition2D(
        t1=Acquisition(
            n_points=96,
            dt=1.0 / 6000.0,
            t2_star=0.4,
            zero_fill=2,
            half_first=True,
            apodization="exponential",
            lb_Hz=2.0,
        ),
        t2=Acquisition(
            n_points=1024,
            dt=1.0 / 6000.0,
            t2_star=0.4,
            zero_fill=2,
            half_first=True,
            apodization="exponential",
            lb_Hz=2.0,
        ),
    )
    return ExperimentCase(
        name="tocsy_amx",
        note="2D TOCSY on an A-M-X chain; relayed A-X correlations appear.",
        sequence=tocsy,
        system=sys,
        regime=regime,
        acquisition=acq2d,
        kwargs={"mixing_time": 0.080},
    )


def preset_zulf_j_ax() -> ExperimentCase:
    sys = SpinSystem(
        isotopes=["1H", "13C"],
        shifts_ppm=[0.0, 0.0],
        J_Hz=[[0.0, 140.0], [140.0, 0.0]],
        label="ZULF 1H-13C pair",
    )
    regime = ZULF()
    acq = Acquisition.from_bw_duration(
        BW_Hz=400.0,
        T_s=2.0,
        t2_star=1.0,
        zero_fill=4,
        apodization="exponential",
        lb_Hz=0.5,
    )
    return ExperimentCase(
        name="zulf_j_ax",
        note="1D ZULF pulse-acquire under the current shared z-axis convention.",
        sequence=zulf_pulse_acquire,
        system=sys,
        regime=regime,
        acquisition=acq,
        kwargs={},
    )


def preset_zulf_dc_pulse() -> ExperimentCase:
    sys = SpinSystem(
        isotopes=["1H", "1H"],
        shifts_ppm=[0.0, 0.0],
        J_Hz=[[0.0, 7.0], [7.0, 0.0]],
        label="ZULF 1H homonuclear pair",
    )
    regime = ZULF()
    acq = Acquisition.from_bw_duration(
        BW_Hz=50.0,
        T_s=2.0,
        t2_star=1.0,
        zero_fill=4,
        apodization="exponential",
        lb_Hz=0.5,
    )
    return ExperimentCase(
        name="zulf_dc_pulse",
        note="1D ZULF DC-pulse experiment with explicit transverse readout.",
        sequence=zulf_dc_pulse_acquire,
        system=sys,
        regime=regime,
        acquisition=acq,
        kwargs={
            "channel": "1H",
            "flip_angle": np.pi / 2,
            "phase": np.pi / 2,
            "detect": "Mx",
        },
    )


PRESETS: dict[str, Callable[[], ExperimentCase]] = {
    "hf_zg_1h": preset_hf_zg_1h,
    "hf_spin_echo": preset_hf_spin_echo,
    "hf_ir_single": preset_hf_ir_single,
    "hsqc_ch": preset_hsqc_ch,
    "cosy_ax": preset_cosy_ax,
    "tocsy_amx": preset_tocsy_amx,
    "zulf_j_ax": preset_zulf_j_ax,
    "zulf_dc_pulse": preset_zulf_dc_pulse,
}


def summarize_1d(result: Result1D, *, top_n: int) -> None:
    axis = result.ppm if result.ppm is not None else result.freq_Hz
    unit = "ppm" if result.ppm is not None else "Hz"
    magnitude = np.abs(result.spectrum)
    idx = np.argsort(magnitude)[-top_n:][::-1]

    print("Top peaks:")
    for rank, i in enumerate(idx, start=1):
        print(
            f"  {rank:>2}. axis={axis[i]:>10.4f} {unit:<3}  "
            f"|S|={magnitude[i]:.6g}"
        )


def summarize_2d(result: Result2D, *, top_n: int) -> None:
    mag = np.abs(result.spectrum)
    flat = np.argsort(mag.ravel())[-top_n:][::-1]

    f1_axis = result.ppm_F1 if result.ppm_F1 is not None else result.freq_F1_Hz
    f2_axis = result.ppm_F2 if result.ppm_F2 is not None else result.freq_F2_Hz
    unit_f1 = "ppm" if result.ppm_F1 is not None else "Hz"
    unit_f2 = "ppm" if result.ppm_F2 is not None else "Hz"

    print("Top 2D peaks:")
    for rank, flat_i in enumerate(flat, start=1):
        i1, i2 = np.unravel_index(flat_i, mag.shape)
        print(
            f"  {rank:>2}. F1={f1_axis[i1]:>10.4f} {unit_f1:<3}  "
            f"F2={f2_axis[i2]:>10.4f} {unit_f2:<3}  |S|={mag[i1, i2]:.6g}"
        )


def maybe_plot(case: ExperimentCase,
               result: Union[Result1D, Result2D],
               *,
               show_plot: bool,
               save_plot: str | None) -> None:
    if not show_plot and not save_plot:
        return

    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed; skipping plot")
        return

    fig = plt.figure(figsize=(8, 5))

    if hasattr(result, "fid_cos"):
        ax = fig.add_subplot(111)
        image = np.abs(result.spectrum)
        f1 = result.ppm_F1 if result.ppm_F1 is not None else result.freq_F1_Hz
        f2 = result.ppm_F2 if result.ppm_F2 is not None else result.freq_F2_Hz
        unit_f1 = "ppm" if result.ppm_F1 is not None else "Hz"
        unit_f2 = "ppm" if result.ppm_F2 is not None else "Hz"
        im = ax.imshow(
            image,
            aspect="auto",
            origin="lower",
            extent=[float(f2[0]), float(f2[-1]), float(f1[0]), float(f1[-1])],
            cmap="magma",
        )
        ax.set_xlabel(f"F2 ({unit_f2})")
        ax.set_ylabel(f"F1 ({unit_f1})")
        ax.set_title(case.name)
        fig.colorbar(im, ax=ax, label="|S|")
    else:
        ax = fig.add_subplot(111)
        x = result.ppm if result.ppm is not None else result.freq_Hz
        unit = "ppm" if result.ppm is not None else "Hz"
        ax.plot(x, np.abs(result.spectrum), linewidth=1.2)
        ax.set_xlabel(unit)
        ax.set_ylabel("|S|")
        ax.set_title(case.name)

    fig.tight_layout()

    if save_plot:
        out = Path(save_plot)
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=150)
        print(f"Saved plot to {out}")

    if show_plot:
        plt.show()
    else:
        plt.close(fig)


def run_case(case: ExperimentCase):
    print(f"Preset   : {case.name}")
    print(f"System   : {case.system.label or '<unnamed>'}")
    print(f"Regime   : {case.regime.name}")
    print(f"Sequence : {case.sequence.__name__}")
    print(f"Note     : {case.note}")
    print(f"Kwargs   : {case.kwargs}")
    print()

    result = case.sequence(
        case.system,
        case.regime,
        case.acquisition,
        **case.kwargs,
    )
    return result


def build_case_from_config() -> ExperimentCase:
    mode = str(CONFIG.get("mode", "preset"))
    if mode == "preset":
        preset_name = CONFIG["preset"]
        if preset_name not in PRESETS:
            known = ", ".join(sorted(PRESETS))
            raise ValueError(f"Unknown preset {preset_name!r}. Known presets: {known}")
        case = PRESETS[preset_name]()
        maybe_save_case_files(case)
        return case

    if mode == "files":
        system_path = CONFIG.get("system_file")
        parameter_path = CONFIG.get("parameters_file")
        if not system_path or not parameter_path:
            raise ValueError(
                "files mode requires CONFIG['system_file'] and CONFIG['parameters_file']"
            )
        return load_case_from_files(system_path, parameter_path)

    raise ValueError("CONFIG['mode'] must be 'preset' or 'files'")


def main() -> None:
    case = build_case_from_config()
    result = run_case(case)

    if hasattr(result, "fid_cos"):
        summarize_2d(result, top_n=int(CONFIG["print_top_peaks"]))
    else:
        summarize_1d(result, top_n=int(CONFIG["print_top_peaks"]))

    maybe_plot(
        case,
        result,
        show_plot=bool(CONFIG["show_plot"]),
        save_plot=CONFIG["save_plot"],
    )


if __name__ == "__main__":
    main()