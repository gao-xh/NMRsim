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

| Module          | Responsibility                                              |
|-----------------|-------------------------------------------------------------|
| `isotopes.py`   | γ and spin-quantum-number table, with conversion helpers.   |
| `ops.py`        | Spin-1/2 Pauli operators, Kron expansion, Ix/Iy/Iz/I±.      |
|                 | Cached per spin count via `lru_cache`.                      |
| `system.py`     | `SpinSystem` dataclass: isotopes + shifts_ppm + J_Hz.       |
|                 | Validates shape, symmetry, diagonal-zero, I=1/2-only.       |
| `hamiltonian.py`| Three H builders (see 16.2). All return Hermitian, rad/s.   |
| `states.py`     | Initial density matrices (thermal high-T, prepolarized x).  |
| `detection.py`  | Detection operators (I+, Mx, Mz).                           |
| `engine.py`     | One-time eigendecomp + `fid()` + `stick_spectrum()`.        |
| `processing.py` | Apodization, FFT with zero-fill, Hz↔ppm axis conversion.    |

Layering rule: each module imports only from modules above it in this
table; no cycles. Anything Qt-related lives in `src/ui/`, not here.

### 16.5 High-field ↔ ZULF as engine configurations

The same FID pipeline serves both modes; only three knobs change:

| Knob               | High field            | ZULF (true zero)        |
|--------------------|-----------------------|-------------------------|
| Hamiltonian        | `H_rotating(...)`     | `H_J_only(...)`         |
| Initial state ρ₀   | `thermal_high_temp`   | `prepolarized_x`        |
| Detection operator | `detect_Iplus(obs)`   | `detect_Mx()`           |

The "translation" workflow is therefore: build one `SpinSystem` →
configure two engines (HF and ZULF) on it → render two spectra.

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

- v0.1 — `src/core` 1D engine (done). Smoke tests against analytic AX/AB.
- v0.2 — Multi-component mixing (weighted sum of `SpinSystem`s), basic
  matplotlib viewer.
- v0.3 — Minimal Qt UI: edit `SpinSystem` + run HF + run ZULF + compare.
- v0.4 — 2D module port (COSY, MQ-ZULF) from reference.
- v0.5 — High-field spectrum → {δ, J} fitting (scipy.optimize on the same
  forward engine).
- v1.0 — Relaxation (T1/T2 per spin or per coherence), Liouville path for
  multi-pulse sequences.
