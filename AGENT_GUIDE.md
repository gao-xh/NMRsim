# Agent Guide — General Engineering Conventions

> Project-agnostic conventions distilled from prior NMR/ZULF projects in `refs/`.
> Project-specific content (physics, algorithms, data formats, module boundaries)
> will be appended once the architecture is decided.

---

## 1. Language & Encoding

- **Source code is English-only.** No Chinese characters, no emoji in `.py`,
  `.bat`, `.ps1`, `.json`, or other code/config files. Avoids encoding issues
  on Windows (cp936/utf-8 mismatches) and keeps tooling portable.
- Chinese is allowed in user-facing documentation under `docs/`, in commit
  messages, and in conversation — but never inside code or log strings.
- All files saved as **UTF-8 without BOM**, LF or CRLF consistent per platform.

## 2. Project Layout

Keep the repository root small (≤ ~8 files). Everything else goes into a
purpose-named subdirectory.

```
<project>/
├── README.md           # entry point for humans
├── CHANGELOG.md        # version history (Keep-a-Changelog style)
├── LICENSE
├── .gitignore
├── requirements.txt    # or pyproject.toml
├── config.txt          # user-editable settings (see §5)
├── run.py              # launcher / entry point
├── src/                # all importable code
│   ├── core/           # business logic, math kernels, backend bridges
│   ├── ui/             # widgets, windows, plotting, user interaction
│   └── utils/          # config loader, IO helpers, small reusable pieces
├── tests/              # unit + integration tests
├── docs/
│   ├── setup/          # install / environment guides
│   ├── features/       # one file per user-visible feature
│   ├── development/    # design notes, refactor logs, code reviews
│   └── troubleshooting/
├── assets/             # icons, animations, images
├── presets/            # shipped read-only example data
├── user_save/          # user-generated data (gitignored)
└── scripts/            # one-off maintenance / install helpers
```

Rules:
- Tests, examples, dev notes, temp files **never** live in the root.
- Every package directory has an `__init__.py`.
- Large data and exported results go to `user_save/` and are gitignored.

## 3. Separation of Concerns

- `src/core/` — pure computation. No Qt imports, no GUI side effects. Pure
  functions / classes that take data in and return data out.
- `src/ui/` — only Qt widgets, layouts, signal wiring, plotting. Calls into
  `core/` for any math.
- `src/utils/` — small, cross-cutting helpers (config, file IO, parsing).
- Never inline math/algorithm changes into a UI file "just because it's
  convenient." If it grows past a few lines, move it to `core/`.
- Visualization-specific math (e.g. grid generation for a heatmap) may live
  next to the widget temporarily, but migrate to `core/` once it stabilizes.

## 4. Reference / Vendored Code

- Code under `refs/` (or `references/`) is **read-only**. Do not edit it.
- To reuse logic, either:
  1. **Copy** the function into `src/` (preferred — decouples versions), or
  2. Import via `sys.path` injection only if the dependency is heavy and
     stable.
- When copying, retain a short comment with the source path so future readers
  can trace it back.

## 5. Configuration

- One **single source of truth** for tunable values: `config.txt` (plain
  `KEY = VALUE`, `#` comments) loaded by a singleton in `src/utils/config.py`.
- No hardcoded:
  - file paths (use `pathlib.Path` + relative paths)
  - window sizes, colors, asset paths
  - environment names, Python interpreter paths
  - version strings, app titles
  - algorithm thresholds that a user might want to tune
- Every `config.get(KEY, default)` call **must pass a default** so the app
  still runs with a missing/older config file.
- Save-file formats carry a `"version"` field; bump it on incompatible
  changes and handle migration explicitly.

## 6. Paths & Environments

- Use `pathlib.Path` everywhere; never raw `"C:\\..."` literals.
- Launcher scripts must support arbitrary Python environments. Detect type
  from the configured interpreter path:
  - path contains `conda|anaconda|miniconda` → `conda activate <env>` then
    `python run.py`
  - otherwise → invoke the interpreter directly: `& "<path>\python.exe" run.py`
- Provide both `start.bat` and `start.ps1` on Windows; both must verify
  dependencies before launching and print a helpful error if missing.

## 7. Qt / PySide6 Specifics

- **Do not mix conda-installed Qt with pip-installed PySide6.** Remove
  `qtbase`, `pyqt`, `qt-main`, etc. from conda; install PySide6 only via pip.
- **Do not call `setFixedSize()` on a widget that is added to a parent
  layout.** Let the layout manage size; set fixed size only on the top-level
  window or on a non-layout-managed inner container.
- Use signal/slot for cross-thread communication; never touch UI widgets from
  a worker thread directly.

### 7a. Worker Thread Lifecycle ("Zombie Worker" Pattern)

Heavy work (FFT, fitting, MATLAB calls) runs in a `QThread`. Rapid UI events
(slider drags) can spawn workers faster than they finish. Naively overwriting
`self.worker` lets Python GC the old QThread while its C++ side is still
running → segfault.

Pattern:
1. Before starting a new worker, **disconnect signals** from the old one so
   stale results never reach the UI.
2. Call `old_worker.quit()` (do not `wait()` on the UI thread).
3. Move the old instance into `self._zombie_workers: list` so the Python
   reference outlives the native execution.
4. Periodically prune finished entries from that list.

## 8. Multi-Instance Backend Calls (Variable Prefixing)

When the same backend (MATLAB engine, shared interpreter, global namespace)
hosts multiple logical systems concurrently:

- Give every wrapper class a `var_prefix=""` constructor argument.
- All variables it creates in the backend are named `f"{var_prefix}{base}"`.
- A given logical instance uses **one consistent prefix** across all its
  helper objects.
- Cleanup: `eng.eval(f"clear {var_prefix}*", nargout=0)` removes everything
  belonging to that instance.
- Convention: prefix ends with `_` and is a meaningful name (`ethanol_`,
  `system_1_`), never a single letter.

## 9. UI Interaction Patterns

- **Slider + SpinBox pair** for every numeric parameter — slider for intuitive
  exploration, spinbox for precise entry. The two stay bidirectionally
  synced; one source of truth in the model.
- Long operations show a `QProgressDialog` or status-bar progress, and are
  cancellable when possible.
- Status bar shows contextual info (active counts, current mode), not just
  the last message.
- Provide keyboard shortcuts for the top ~5 actions (Run, Export, Save,
  Load, Stop).

## 10. Logging

- Single `log(message, level="INFO")` method on the main window with levels
  `INFO | WARNING | ERROR`. Prefix/color is applied centrally.
- Worker threads never write to the log widget directly — they emit a
  signal that the UI thread renders.
- A "Detailed log" window is optional but useful for long runs; it must be
  scrollable, copy-able, and clearable.

## 11. Security & Safety

- `eval` / `exec` are last resorts. If unavoidable (e.g. user-entered
  matrices with variables), restrict the namespace to an explicit allow-list
  (`{"np": numpy, **allowed_vars}`) and never pass `__builtins__`.
- File dialogs (`QFileDialog`) for all user-chosen paths; never accept raw
  string paths from arbitrary input without validation.
- Validate user input at the boundary (parse → validate → use). Trust
  internal data once validated; don't re-validate at every layer.

## 12. Documentation Discipline

- Do **not** create a new markdown file to document every change. Update the
  existing `CHANGELOG.md`, the relevant `docs/features/*.md`, or commit
  message instead.
- `docs/INDEX.md` is the single entry that links to everything else.
- `docs/troubleshooting/` gets one file per recurring problem, with:
  symptoms → root cause → fix → prevention.
- Don't add docstrings, type hints, or comments to code you didn't touch.
- For code you do write: comment **why**, not what. One short line for any
  non-obvious constraint, workaround, or invariant. No multi-paragraph
  docstrings on private helpers.

### 12a. Log & remote cadence (always-on rule)

Keep the written record and the remote in sync with the working tree at
all times. Concretely:

- **After every meaningful change** (a new module, an API change, a bug
  fix, a doc reshuffle — anything you would mention in a stand-up):
  1. update `CHANGELOG.md` with a one-bullet entry under
     `[Unreleased]` describing what changed and why;
  2. if the change is architectural (new layer, renamed contract,
     deprecated module, new public entry point), also add a one-line
     entry to `AGENT_GUIDE.md` §16.9 (Log of structural updates);
  3. `git add -A && git commit -m "<imperative summary>"` with a body
     listing the affected files / decisions;
  4. `git push` to `origin/main` (or the working branch) immediately —
     do not accumulate local-only commits across a session.
- A change is "meaningful" if a teammate joining tomorrow would want to
  know about it. Trivial reformatting and in-progress scratch edits
  don't qualify.
- The repository's `main` branch and the documentation files together
  should always describe the same project. If they drift, the
  documentation is wrong — fix it in the same commit, not later.
- When in doubt, commit and push. Small, frequent commits are cheaper
  than reconstructing intent later.

## 13. Code Style

- PEP 8, 4-space indent, ~100 char soft line limit.
- Type hints on public functions in `src/`.
- Google or NumPy docstring style, used consistently within a module.
- Magic numbers → named constants at the top of the module (or in `config`
  if user-facing).
- Imports grouped: stdlib / third-party / local; no unused imports.

## 14. Testing & Reproducibility

- `tests/` holds runnable scripts/pytest modules. Diagnostic helpers
  (`diagnose_qt.py`, `test_config.py`) also live here.
- Notebooks (if any) under `notebooks/` are exploratory. Once logic is
  stable, move it into `src/` and reduce the notebook to a thin demo.
- Provide a top-level smoke test that loads config, imports core modules,
  and exits 0 — runnable in CI without a display.

## 15. Performance Defaults

- **Cumulative / incremental computation** beats reloading. When iterating
  over growing data (averages, sums), keep a running accumulator instead of
  re-reading from disk each step.
- Apply expensive corrections (e.g. global phase, baseline) **once** with
  parameters derived from the full dataset, then reuse — don't re-fit per
  subset.
- Cache results keyed by input hash only when profiling shows it matters;
  premature caching adds bugs.

---

## 16. Project-Specific Architecture (NMRsim)

This section captures decisions that shape the codebase. Update it whenever
a structural choice is made or revised; transient progress notes go in
`CHANGELOG.md`, not here.

### 16.1 Scope and goals

Two user-facing capabilities, **one shared physics engine**:

1. **Conventional high-field NMR simulator** — 1D liquid spectra of small
   molecules from a spin-system description (isotopes, chemical shifts in
   ppm, scalar J couplings in Hz, field B0). 2D and multi-component mixing
   are planned but not in v0.
2. **High-field → ZULF "translation"** — given a spin system, simulate both
   the high-field spectrum (for comparison with experiment) and the
   zero-field / low-field spectrum from the same parameters. Fitting
   experimental high-field data to recover {δ, J} is a later phase.

Out of scope for now: solid-state, quadrupolar nuclei (I > 1/2), explicit
relaxation beyond a scalar T2*, multi-pulse 2D, DNP, gradients.

### 16.2 Physics depth: Level C (strict Hilbert-space QM)

We diagonalize the full Hamiltonian on each call; no weak-coupling /
first-order shortcuts. Second-order effects (AB roof, ABX, AA'BB',
heteronuclear strong coupling) come out automatically. The same engine
handles ZULF by simply changing the Hamiltonian and detection operator —
no separate code path.

Reference Hamiltonians:

- `H_J_only`     — true zero field, pure scalar coupling.
- `H_lab`        — Zeeman + J in the lab frame (for ZULF with a bias field
                   or sanity checks).
- `H_rotating`   — rotating-frame Hamiltonian for high field. Each spin's
                   Zeeman term is reduced to its chemical-shift offset
                   relative to its own Larmor frequency (heteronuclei) or
                   the carrier (observed nucleus). Matrix elements stay in
                   kHz instead of hundreds of MHz, so time steps and
                   numerical conditioning are sane.

### 16.3 Units convention (single source of truth)

- **Internal Hamiltonians and propagators**: angular frequency, rad/s.
  Propagator = `exp(-i H t)` with t in seconds.
- **Public inputs**: ppm (chemical shift), Hz (J, line widths, sweep), T
  (B0), seconds (dwell, T2*).
- **Gyromagnetic ratios**: stored as **signed** γ/(2π) in MHz/T (IUPAC).
  Conversion to rad/(s·T) happens only in `isotopes.gamma_rad_per_s_per_T`.
- Never mix conventions inside `core/`. UI / IO layers convert at the
  boundary, not deeper.

### 16.4 Module layout (`src/core/`)

| Module           | Responsibility                                                |
|------------------|---------------------------------------------------------------|
| `isotopes.py`    | γ and spin-quantum-number table, with conversion helpers.     |
| `ops.py`         | Spin-1/2 Pauli operators, Kron expansion, Ix/Iy/Iz/I±.        |
|                  | Cached per spin count via `lru_cache`.                        |
| `system.py`      | `SpinSystem` dataclass: isotopes + shifts_ppm + J_Hz.         |
|                  | Validates shape, symmetry, diagonal-zero, I=1/2-only.         |
| `hamiltonian.py` | Three H builders (see 16.2). All return Hermitian, rad/s.     |
| `states.py`      | Initial density matrices (thermal high-T, prepolarized x).    |
| `detection.py`   | Detection operators (I+, Mx, Mz).                             |
| `pulses.py`      | Hard pulses (`pulse`), propagators, `evolve`, `apply_unitary`.|
|                  | Reserved stubs: `ShapedPulse`, `Event`, `run_sequence` (NYI). |
| `engine.py`      | `EigenSystem`, `fid()`, `stick_spectrum()`, `acquire(...,acq)`. |
| `processing.py`  | Apodization, FFT with zero-fill, Hz↔ppm axis conversion.      |
| `regime.py`      | `Regime` dataclass + `HF` / `ZULF` / `LF` factories.          |
| `acquisition.py` | `Acquisition` dataclass + HF/ZULF presets and constructors.   |
| `simulate.py`    | High-level `simulate(sys, regime, acq) -> SimulationResult`.  |

Layering rule: each module imports only from modules above it in this
table; no cycles. `simulate.py` is the only module that touches all
three of (regime, acquisition, engine). Anything Qt-related lives in
`src/ui/`, not here.

### 16.4a Public API contract

All new user code (scripts, sequences, UI) MUST go through the three
parameter objects below. Hard-coded numbers like `dt=1/4000` or
`B0_T=9.4` outside of test fixtures are a code smell.

```python
from src.core import SpinSystem, HF, ZULF, Acquisition, simulate

sys    = SpinSystem(isotopes=[...], shifts_ppm=[...], J_Hz=[[...]])
regime = HF(B0_T=9.4, observed='1H', carrier_ppm=2.0)   # or ZULF() / LF(B0_T=...)
acq    = Acquisition.from_sw_aq(SW_Hz=4000, AQ_s=2.0, t2_star=0.5, zero_fill=2)
result = simulate(sys, regime, acq)
```

Low-level functions (`H_rotating`, `thermal_high_temp`, `fid`, `pulse`,
`acquire`, ...) remain exported for sequence implementations and
advanced use, but are not the recommended entry point.

### 16.5 High-field ↔ ZULF as engine configurations

The same FID pipeline serves both modes; only three knobs change, and
they are bundled by the `Regime` abstraction (`src/core/regime.py`):

| Knob               | High field (`HF`)                      | ZULF (`ZULF`)            |
|--------------------|----------------------------------------|--------------------------|
| Hamiltonian        | `H_rotating(sys, B0, observed)`        | `H_J_only(sys)`          |
| Initial state ρ₀   | thermal → 90°x on `observed` (auto)    | `prepolarized_x(sys)`    |
| Detection operator | `detect_Iplus(observed)`               | `detect_Mx()`            |
| Display unit       | ppm (via `regime.larmor_Hz()`)         | Hz                       |

Adding another regime (low field with bias, Earth field, ...) means
writing a new factory in `regime.py`; sequences and `simulate()` do not
change. `HF`'s initial state is the *post-90°x* density matrix, so
`simulate(sys, HF(...), acq)` directly returns a pulse-acquire FID.

The "translation" workflow is therefore: build one `SpinSystem` →
swap `regime` between `HF(...)` and `ZULF()` → render two spectra.

### 16.6 Caching and reuse

- `ops.operators(n)` is `lru_cache`'d. Repeated `H_*` calls on the same
  spin count cost nothing for the Kronecker products.
- `engine.EigenSystem` caches the eigendecomposition of a given H. Both
  `fid()` and `stick_spectrum()` reuse it; long parameter sweeps should
  call `EigenSystem.of(H)` once if H is fixed.
- Never mutate the cached arrays returned by `operators(n)`.

### 16.7 What the old reference (`refs/MUI_backup_continue`) gives us

- The PySide6 UI, MATLAB-engine bridge, splash screen, save/load, network
  interface, and presets are reference material only. We may port specific
  patterns (multi-system tabs, slider+spinbox, zombie-worker pattern) into
  the new UI; we do not import or edit those files.
- The `TwoD_simulation.py` core was the seed for `src/core/`: kept the
  algorithmic structure (Hilbert-space diagonalization, generator-based 2D
  sticks, cumulative t1 propagator), discarded the unit mistakes
  (γ-as-rad-vs-MHz confusion, wrong ¹⁵N γ, missing shifts, repeated
  operator construction).

### 16.8 Roadmap (engineering, not deadlines)

See `docs/SEQUENCES_PLAN.md` for the authoritative pulse-sequence
roadmap (4 layers, per-layer acceptance tests, ZULF parallel track).
High-level milestones below mirror that plan:

- v0.1 — `src/core` 1D engine (done). Smoke tests against analytic AX/AB.
- v0.1-dev (current) — added `regime` / `acquisition` / `pulse` layers and
  the `simulate()` entry point so HF↔ZULF and parameter changes are
  one-liners. See §16.9 for the structural log.
- v0.2 — `src/sequences/oneD.py`: `pulse_acquire`, `pulse_acquire_decoupled`,
  `spin_echo`, `inversion_recovery`, `cpmg`. T1 field on `SpinSystem`.
- v0.3 — Multi-component mixing (weighted sum of `SpinSystem`s), basic
  matplotlib viewer.
- v0.4 — 2D module: `hsqc`, `hmbc`; generic 2D wrapper + `fft2_spectrum`.
- v0.5 — `cosy`, `tocsy`. Optional sequence-DSL (`Event` / `run_sequence`).
- v0.6 — Minimal Qt UI: edit `SpinSystem` + pick `Regime` + pick `Acquisition`
  + run any sequence + compare.
- v0.7 — High-field spectrum → {δ, J} fitting (scipy.optimize on the same
  forward engine).
- v1.0 — Relaxation (T1/T2 per spin or per coherence), Liouville path,
  NOESY/ROESY.

### 16.8a Sequence catalogue maintenance

`src/sequences/README.md` is the user-facing catalogue of every
implemented pulse sequence (name, file, Bruker equivalent, signature,
parameters, call example). It is the entry point a caller reads before
writing experiment code.

Rule: **any change to the public set of sequences requires a same-commit
update to that README.** This includes:

- adding a new sequence function (new row in the top table + a dedicated
  section with signature, parameter notes, and a runnable example);
- removing or renaming a sequence;
- changing a sequence's public signature, default arguments, or
  validation behaviour;
- adding/removing a sequence file under `src/sequences/`.

What does *not* belong there:

- physics derivations, design rationale, roadmap (those live in
  `docs/SEQUENCES_PLAN.md` and §16.4 / §16.5 of this guide);
- per-change history (that goes in `CHANGELOG.md`);
- planned-but-unimplemented sequences (keep the README a catalogue of
  what works *now*).

If a PR adds a sequence without updating the README, treat it as
incomplete.

### 16.9 Log of structural updates

This section records architecture-level changes only. Per-change deltas
(file lists, bug fixes, …) live in `CHANGELOG.md`.

- **2026-06-01 — initial engine scaffold.** Created `src/core/` with the
  9-module Hilbert-space engine described in §16.4 (pre-regime version).
  Locked in Level-C physics (§16.2), rad/s internal unit (§16.3), and
  the three-knob HF/ZULF table (§16.5, original form). Identified the
  reference repo as read-only (§16.7).
- **2026-06-02 — regime / acquisition / pulse layers + `simulate()`.**
  Added three parameter-object abstractions so user code no longer
  threads loose numbers through the call stack:
  - `Regime` (`HF` / `ZULF` / `LF`) bundles Hamiltonian + ρ₀ +
    detector + display unit. `HF` now bakes in the 90°x pulse so
    `simulate(...)` is a true pulse-acquire (fixes the previously
    empty HF spectrum).
  - `Acquisition` collects dwell, n_points, T2*, zero-fill, apodization,
    with `from_sw_aq` / `from_bw_duration` / `with_` constructors and
    HF-1H / HF-13C / ZULF presets.
  - `simulate(sys, regime, acq) -> SimulationResult` is the new
    top-level entry point; collapses H → ρ₀ → detect → FID → apodize
    → FFT → axis. Result carries inputs back for reproducibility.
  - `pulses.py` introduces the first multi-pulse primitives
    (`pulse`, `propagator`, `evolve`, `apply_unitary`) plus reserved
    extension stubs (`ShapedPulse`, `Event`, `run_sequence`) that
    raise `NotImplementedError` until v0.5+ / v0.6+.
  - `engine.acquire(H, rho, det, acq)` is added so future sequence
    functions and `simulate()` share one boilerplate-free path.
  - Authored `docs/SEQUENCES_PLAN.md` (4-layer pulse-sequence roadmap,
    parallel ZULF track, deferred items, milestone gates v0.2–v1.0).
