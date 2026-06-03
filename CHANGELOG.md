# Changelog

All notable changes to NMRsim are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow SemVer once we tag a first release.

## [Unreleased] — 0.1.0-dev

### Added (2026-06-03 — manual driver entry point)
- `main.py` — a no-UI, code-editable driver for running the simulator
  directly from Python. The file exposes a small `CONFIG` block and a
  set of example presets wiring together `SpinSystem`, `Regime`,
  `Acquisition` / `Acquisition2D`, and the public sequence functions.
  It prints a text summary of the selected experiment, lists the top
  1D / 2D peaks, and optionally plots the spectrum with matplotlib.
- `main.py` also now supports split save/load of experiments:
  `SpinSystem` is written to one JSON file, while sequence/regime/
  acquisition/kwargs live in a second JSON file. `CONFIG['mode']`
  switches between `preset` and `files`, and `tests/test_main_io.py`
  covers 1D HF and 2D HSQC round-trip reconstruction.

### Changed (2026-06-03 — unified ZULF axis convention)
- `src/core/regime.py` — `ZULF()` and `LF(B0_T=...)` now use the shared
  z-axis convention by default: `prepolarized_z(sys)` as the prepared
  state and `detect_Mz(...)` as the detector. This removes the previous
  mixed convention where ZULF implicitly started from x-polarized,
  x-detected experiments.
- `src/sequences/zulf.py` — `zulf_pulse_acquire`, `zulf_j_spectrum`, and
  `zulf_dc_pulse_acquire` now default to `initial='regime'` and
  `detect='regime'`, so sequence behavior follows the regime definition
  instead of silently assuming transverse preparation / readout.
- `src/sequences/README.md`, `AGENT_GUIDE.md`, and Layer 5 test comments
  were updated to describe the shared-axis model and to make explicit
  that transverse experiments remain available via `initial='x'` /
  `detect='Mx'` overrides.
- Full regression after the convention change: 24/24 tests passing across
  Layer 1-5 (`test_layer1_1d.py`, `test_layer2_echo.py`,
  `test_layer3_hsqc.py`, `test_layer4_cosy.py`, `test_layer5_zulf.py`).

### Added (2026-06-02 — Layer 5 sequences: ZULF)
- `src/sequences/zulf.py` — three new ZULF / low-field 1D sequences:
  - `zulf_pulse_acquire(sys, regime, acq, *, initial='regime',
    detect='regime')` — default pulse-acquire now follows the shared
    z-axis convention (prepolarize-z → free evolution → M_z detect).
    Explicit transverse experiments remain available via
    `initial='x'` / `detect='Mx'`. Works for `ZULF()` (true zero field)
    and `LF(B0_T=...)`.
  - `zulf_j_spectrum(sys, regime=None, acq=None, *, BW_Hz=200, T_s=10,
    t2_star=2.0, lb_Hz=0.5, ...)` — convenience wrapper preset for
    narrow-bandwidth J-spectroscopy.
  - `zulf_dc_pulse_acquire(sys, regime, acq, *, channel, B_T=None,
    duration_s=None, flip_angle=None, phase=0.0, initial='regime',
    detect='regime', ideal=False)` — applies a DC pulse on one channel
    and acquires. Either physical knobs (`B_T`, `duration_s`) or
    `flip_angle` may be given; `flip_angle` wins as a hard-pulse
    shortcut.
- `src/core/pulses.pulse_with_evolution(sys, channel, B_T, duration_s,
  H_static, phase)` — DC / RF pulse propagator that retains the static
  Hamiltonian during the pulse: `U = exp(-i(H_static + H_RF)·τ)`. In
  ZULF, `γB ≈ J`, so the ideal-hard-pulse limit used elsewhere is
  unreliable; `zulf_dc_pulse_acquire` defaults to this primitive.
- `src/core/states.prepolarized_z(sys)` — `Σ γ_i I_zi`; default initial
  state for `zulf_dc_pulse_acquire`.
- `tests/test_layer5_zulf.py` — 4 regression tests:
  heteronuclear ¹H-¹³C J=140 Hz peak position, homonuclear ¹H₂ DC-only
  (F_x commutes with H_J), DC-pulse ideal round-trip
  (explicit `prepolarized_z + π/2 on +y ≡ prepolarized_x/M_x` override), and physical
  (B_T, duration_s) DC pulse converging to the ideal hard pulse in
  the γB ≫ J limit.
- `src/sequences/README.md` — catalogue extended with the three ZULF
  rows + full sections.

### Added (2026-06-02 — Layer 4 sequences: COSY + TOCSY)
- `src/sequences/homcor.py` — two homonuclear 2D sequences sharing one
  pre-built propagator runner:
  - `cosy(sys, regime, acq2d)` — COSY-90 (`cosygpqf` / `cosy90`).
    Skeleton `90°φ₁ — t1 — 90°x — acq`; States cycles φ₁ between
    +y (cos) and +x (sin) so the hypercomplex FT gives the correct
    F1 sign (peaks land on the (δ, δ) diagonal, not the anti-diagonal).
  - `tocsy(sys, regime, acq2d, *, mixing_time)` — TOCSY
    (`dipsi2etgpsi` / `mlevphpr`). Replaces the read pulse with an
    *idealised isotropic mixing propagator* `exp(-i τ_m H_iso)`,
    where `H_iso = 2π Σ_{ij ∈ obs} J_ij (Ix·Ix + Iy·Iy + Iz·Iz)`
    (homonuclear pairs on the observed channel only; chemical shifts
    and heteronuclear J are dropped during mixing — the
    perfect-spin-lock limit of DIPSI / MLEV).
- `tests/test_layer4_cosy.py` — 4 regression tests:
  AX COSY shows both diagonals and both cross peaks, uncoupled COSY
  shows only diagonals, TOCSY on an A-M-X chain produces a relayed
  A↔X cross peak (COSY does not), mixing-time validation.
- `src/sequences/README.md` — catalogue extended with COSY and TOCSY
  entries.

### Added (2026-06-02 — Layer 3 sequences: HSQC + HMBC + 2D framework)
- `src/core/acquisition.Acquisition2D` — frozen dataclass bundling a
  `t1` (indirect) and `t2` (direct) `Acquisition`. Exposed via
  `src.core` and consumed by every 2D sequence.
- `src/core/processing.fft2_hypercomplex(S_cos, S_sin, *, dt_t1, dt_t2,
  ...)` — States hypercomplex 2D FFT. FT along t2 of each modulation
  set, form `Ã + i·B̃` along t1, complex FT along t1. Returns one-sided
  F1 axis (no axial mirror) — i.e. pure 2D absorption shape.
- `src/core/simulate.SimulationResult2D` + `finalize_2d(fid_cos,
  fid_sin, acq2d, regime, *, indirect)` — shared 2D finishing path
  (apodize → hypercomplex FT → Hz / ppm axes for both dimensions).
  Mirrors the `finalize_fid` pattern from Layer 2.
- `src/sequences/twoD.py` — `acquire2d_hypercomplex(one_point, acq2d)`
  generic loop that calls a user-supplied `one_point(t1, quadrature)`
  for every t1 × {cos, sin} and stacks the FIDs.
- `src/sequences/hetcor.py` — Layer 3 heteronuclear correlation
  sequences:
  - `hsqc(sys, regime, acq2d, *, indirect='13C', J_CH,
    decouple_during_acq=True)` — HSQC (`hsqcetgp`). Skeleton:
    `INEPT — t1 (with central 180°(observed) refocus) — reverse INEPT —
    acq`. Cosine / sine sets via ±x / −y phase on the first
    `90°(indirect)` pulse. Optional ideal CW decoupling during t2
    re-uses `_zero_heteronuclear_J` from Layer 1.
  - `hmbc(sys, regime, acq2d, *, indirect='13C', J_long=8.0,
    decouple_during_acq=False)` — HMBC (`hmbcgplpndqf`). Same skeleton
    with τ tuned to long-range J. Low-pass J filter not modelled.
- `tests/test_layer3_hsqc.py` — three regression tests:
  single CH pair → one cross peak at (δ_H, δ_C);
  two non-coupled CH pairs → two cross peaks at the right positions;
  HMBC with τ = 1/(4·8 Hz) on a 1J + 2J system picks up the long-range
  cross peak as the dominant signal.
- `src/sequences/README.md` — catalogue extended with the two new 2D
  sequences (signature, parameters, example).

### Not modelled (intentional, per `docs/SEQUENCES_PLAN.md`)
- Phase cycling — the density-matrix simulation already gives the
  desired coherence pathway.
- Gradient coherence selection.
- Realistic composite-pulse decoupling (WALTZ-16, GARP) — only the
  J = 0 limit is implemented.
- Echo-antiecho quadrature — only States is supported.

### Added (2026-06-02 — Layer 2 sequences: spin echo / IR / CPMG)
- `src/sequences/oneD.py` extended with three single-channel multi-pulse
  sequences:
  - `spin_echo(sys, regime, acq, *, tau, pulse_phase_180=0.0)` —
    Hahn echo (`hahnecho`). Refocuses chemical shift; J evolves over
    the full 2τ.
  - `inversion_recovery(sys, regime, acq, *, tau)` — T1 measurement
    (`t1ir`). Uses the new `relax_T1` during the τ delay.
  - `cpmg(sys, regime, acq, *, tau, n_echoes, pulse_phase_180=π/2)` —
    CPMG echo train. Default y-phase 180° matches standard CPMG.
- `src/core/relaxation.py` — new module. `relax_T1(rho, sys, t,
  observed=None)` applies a per-spin Bloch-style longitudinal recovery
  along each `Iz_i` axis. Projection-based (no Liouville-space
  propagator) — only the linear-in-Iz part of ρ is touched; bilinear
  terms and transverse coherences are left alone. Adequate for IR
  during a pure-longitudinal delay; a full relaxation matrix is
  deferred to v1.0.
- `SpinSystem.T1: np.ndarray | None` — optional per-spin longitudinal
  relaxation times (s). `None` (default) disables T1 entirely; entries
  that are `NaN`/non-positive disable that spin only. Backward-
  compatible with all existing call sites.
- `src/core/simulate.finalize_fid(fid, acq, regime) -> SimulationResult`
  — extracted from `simulate()` so sequence functions that build their
  own FID (echo, IR, CPMG, future 2D loops) share one apodize → FFT →
  axis pipeline.
- `tests/test_layer2_echo.py` — 7 regression tests:
  spin-echo identity on a single ¹H, AX anti-phase at 2τ = 1/(2J),
  IR T1 fit (recovers input within 1%), IR-without-T1 stays inverted,
  CPMG n=0 ≡ pulse-acquire, CPMG n=1 ≡ spin_echo with y-phase 180°,
  CPMG validation.
- `src/sequences/README.md` — catalogue extended with the three new
  sequences (signatures, parameters, examples).

### Changed
- `src/sequences/oneD._zero_heteronuclear_J` now propagates the
  `T1` field when copying the system.

### Added (2026-06-02 — Layer 1 sequences: pulse_acquire / zgpg)
- `src/sequences/` — new package holding named pulse-sequence wrappers
  built on top of `src.core`. Layer 1 (`oneD.py`) ships two sequences:
  - `pulse_acquire(sys, regime, acq)` — Bruker `zg`, thin alias for
    `simulate()` kept as a stable entry point.
  - `pulse_acquire_decoupled(sys, regime, acq, decouple=None)` — Bruker
    `zgpg` / `zgig`. Models ideal CW heteronuclear decoupling by
    zeroing scalar couplings between `regime.observed` and every
    nucleus in `decouple` (default: all non-observed isotopes).
    Homonuclear couplings on the observed channel are preserved.
- `tests/test_layer1_1d.py` — Layer-1 regression suite (peak counting):
  single-¹H singlet, AX ¹H→4 lines, ¹³C-CH₃ quartet (1:3:3:1) without
  decoupling, singlet under ideal ¹H decoupling, decouple-spec
  equivalence and validation.

### Fixed (high-field rotating-frame Hamiltonian)
- `H_rotating` previously kept the full `2πJ (Ix·Ix + Iy·Iy + Iz·Iz)`
  bilinear for heteronuclear pairs. In a (doubly) rotating frame the
  flip-flop part oscillates at the Larmor difference (~MHz) and must
  be dropped (standard secular truncation). Keeping it produced a
  ~3.5 Hz second-order splitting of the inner ¹³C quartet lines (a
  ¹H/¹³C system showed 6 peaks instead of 4). `_J_term` now takes
  `secular_heteronuclear` flag; `H_rotating` uses it, `H_J_only` and
  `H_lab` keep the full bilinear (correct for true zero/low field).

### Added (2026-06-02 — regime / acquisition / pulse layer)
- `docs/SEQUENCES_PLAN.md` — roadmap for pulse-sequence coverage
  (4 layers from 1D basics to 2D, plus a parallel ZULF track and
  deferred items), per-layer acceptance tests, and milestone gates
  v0.2 → v1.0.
- `src/core/regime.py` — `Regime` data class + `HF(B0_T, observed,
  carrier_ppm)` / `ZULF()` / `LF(B0_T)` factories. Bundles
  (Hamiltonian, ρ₀, detector, display unit) so HF↔ZULF is one line
  in user code and a future LF / Earth-field regime is just another
  factory.
- `src/core/acquisition.py` — frozen `Acquisition` data class
  (n_points, dt, t2_star, zero_fill, apodization, lb_Hz, gb_Hz,
  half_first) with derived `sw_Hz` / `aq_s` and factories
  `from_sw_aq` (HF) / `from_bw_duration` (ZULF) / `with_(...)`.
  Three starter presets: `default_acq_HF_1H(B0)`,
  `default_acq_HF_13C(B0)`, `default_acq_ZULF()`.
- `src/core/simulate.py` — high-level `simulate(sys, regime, acq)
  -> SimulationResult` collapsing the (build H → ρ₀ → detect → FID
  → apodize → FFT → axis) boilerplate; result carries fid, freq_Hz,
  spectrum, ppm (HF only), and the input regime/acquisition for
  reproducibility.
- `src/core/pulses.py` — coherent-manipulation primitives:
  `pulse(sys, channel, angle, phase)` (ideal hard pulse, channel
  by isotope name / index / index list), shortcuts `pulse_x` /
  `pulse_y`, `propagator(H, t)`, `evolve(rho, H, t)`,
  `apply_unitary(rho, U)`. Reserved extension points (stubs,
  raise `NotImplementedError`): `ShapedPulse` protocol (v0.6+),
  `Event` protocol and `run_sequence()` (v0.5+).
- `src/core/engine.py` — `acquire(H, rho, detect, acq)` thin wrapper
  over `fid` that takes an `Acquisition`; used by `simulate()` and
  by future sequence functions.

### Changed
- Top-level `src/core/__init__.py` API surface now leads with the
  parameter-object workflow:
  `sys = SpinSystem(...)` → `regime = HF(...)` / `ZULF()` →
  `acq = Acquisition.from_sw_aq(...)` → `simulate(sys, regime, acq)`.
  Loose numbers like `dt=1/4000, n_points=8192` no longer appear in
  the recommended path. Low-level functions (`H_rotating`,
  `thermal_high_temp`, `fid`, …) stay exported for advanced use.
- `Regime.HF(...)` initial state is now the *post-90°x* state on
  the observed channel (true pulse-acquire equivalent), so
  `simulate(sys, HF(...), acq)` returns a non-zero spectrum
  directly. Previously it returned thermal Iz, which is orthogonal
  to `I+` and produced an all-zero FID.

### Fixed
- HF `simulate()` returning empty spectrum: documented under
  "Changed" above. Verified that `simulate(sys, HF(...), acq)` and
  the manual `thermal → 90°x → acquire(H, ρ, det, acq)` chain
  produce numerically identical FIDs (`np.allclose`).

### Added (2026-06-01 — initial engine scaffold)
- `AGENT_GUIDE.md` — project-wide engineering conventions distilled from
  prior ZULF / Multi-system Spinach UI work, plus a project-specific
  architecture section (units, module layout, HF↔ZULF knob table,
  roadmap). See §16 for the structural decisions.
- `src/core/` — first cut of the shared Hilbert-space NMR engine, 9 files:
  - `isotopes.py` — signed γ table in MHz/T (¹H, ²H, ¹³C, ¹⁴N, ¹⁵N, ¹⁹F,
    ²⁹Si, ³¹P) with `gamma_rad_per_s_per_T()` and `larmor_Hz()` helpers.
  - `ops.py` — spin-1/2 operators (`Ix`, `Iy`, `Iz`, `I±`) built by
    Kronecker product, cached per spin count via `lru_cache`.
  - `system.py` — `SpinSystem(isotopes, shifts_ppm, J_Hz)` with
    validation (shape, symmetry, zero diagonal, I=1/2-only).
  - `hamiltonian.py` — three builders: `H_J_only` (true zero field),
    `H_lab` (Zeeman + J in lab frame), `H_rotating` (high-field rotating
    frame using chemical-shift offsets).
  - `states.py` — `thermal_high_temp` (∝ Σγᵢ Iᵢz) and `prepolarized_x`
    (∝ Σγᵢ Iᵢx) initial density matrices.
  - `detection.py` — `detect_Iplus(obs)` (high-field quadrature),
    `detect_Mx`, `detect_Mz` (ZULF magnetometer).
  - `engine.py` — `EigenSystem` cache, `fid()` and `stick_spectrum()`
    sharing one eigendecomposition; FID computed by `einsum` instead of
    per-step `ρ ← UρU†`.
  - `processing.py` — exponential / Gaussian apodization, FFT with
    zero-fill, Hz↔ppm axis conversion.
  - `__init__.py` — public API re-export with a quick-start example.

### Decided (architecture)
- Physics depth = **Level C** (strict Hilbert-space diagonalization). No
  first-order weak-coupling shortcuts in the core; second-order effects
  emerge naturally.
- **One engine for high field and ZULF.** The two modes differ only in
  three swap-in objects: Hamiltonian builder, ρ₀, detection operator.
- Internal unit convention = **rad/s** for Hamiltonians/propagators;
  public inputs are ppm/Hz/T/s. Conversions live in `isotopes.py`.

### Fixed (vs. reference `refs/MUI_backup_continue/src/core/TwoD_simulation.py`)
- ¹⁵N gyromagnetic ratio: was `60.86` (incorrect), now `-4.31726882`
  MHz/T (IUPAC, signed).
- γ-unit inconsistency: reference treated MHz/T as if rad/(s·T) inside H;
  new engine keeps the boundary explicit.
- `Ix/Iy/Iz` were rebuilt in every layer (`calculation`, `operation`,
  `simulation`) — now built once, cached by spin count.
- Chemical shift δ had no input path — now first-class on `SpinSystem`.
- High-field detection used `Σγᵢ Ixᵢ` (ZULF convention); new
  `detect_Iplus` is correct quadrature on a single channel.

### Not yet ported / out of scope for v0.1
- 2D pulse sequences (COSY / MQ-ZULF FID and stick generators).
- Hard / shaped pulse operators as first-class objects.
- Multi-component (mixture) weighting.
- Relaxation beyond a scalar T2*, Liouville-space propagation.
- Higher-spin nuclei (I > 1/2), quadrupolar terms.
- UI layer.

### Notes
- `refs/` is read-only reference material; no files in `refs/` have been
  modified.
