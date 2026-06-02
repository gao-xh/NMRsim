# Changelog

All notable changes to NMRsim are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow SemVer once we tag a first release.

## [Unreleased] — 0.1.0-dev

### Added
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
