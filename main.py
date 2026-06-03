"""Manual entry point for running NMRsim without a UI.

Edit the CONFIG block below, then run:

    python main.py

This file is intentionally plain Python rather than a CLI parser so you
can tweak systems, regimes, acquisitions, and sequence kwargs directly
in code while developing / validating the engine.
"""
from __future__ import annotations

from dataclasses import dataclass
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


# ---------------------------------------------------------------------------
# Editable config: pick one preset and optional plot behavior.
# ---------------------------------------------------------------------------

CONFIG = {
    "preset": "hf_zg_1h",
    "show_plot": True,
    "save_plot": None,   # e.g. "outputs/zulf_j_ax.png"
    "print_top_peaks": 8,
}


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


def main() -> None:
    preset_name = CONFIG["preset"]
    if preset_name not in PRESETS:
        known = ", ".join(sorted(PRESETS))
        raise ValueError(f"Unknown preset {preset_name!r}. Known presets: {known}")

    case = PRESETS[preset_name]()
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