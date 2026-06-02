# Changelog

All notable changes to NMRsim are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow SemVer once we tag a first release.

## [Unreleased] — 0.1.0-dev

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
