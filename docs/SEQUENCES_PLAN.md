# Pulse Sequence Roadmap

Status: draft (2026-06-02)
Owner: NMRsim core
Scope: which pulse sequences to implement, in what order, and what
infrastructure each one requires.

This plan is read together with `AGENT_GUIDE.md` §16 (architecture) and
`CHANGELOG.md` (per-change deltas). All physics constraints from §16.2
(Level-C, strict diagonalization, no first-order shortcuts) apply.

---

## 0. Guiding principles

1. **Each sequence layer unlocks the next.** Add the minimum primitives,
   then build several sequences on top before moving on.
2. **Coverage over cleverness.** Prefer sequences that cover the most
   day-to-day experiments first (1D zg, 1D zgpg, HSQC).
3. **Ideal first, realistic later.** Use ideal hard pulses and ideal
   heteronuclear decoupling first; CPD/shaped/adiabatic come later only
   if needed.
4. **No relaxation in early layers.** T1/T2 enter the model only when a
   sequence's *physics* requires it (inversion recovery → T1; NOESY →
   cross-relaxation). Other sequences keep using `t2_star` line-broadening.
5. **Same engine for HF and ZULF.** Pulse + evolve primitives are
   field-agnostic; the Hamiltonian builder decides the regime.

---

## 1. Required new primitives (added once, used by all sequences)

These belong in `src/core/` and are prerequisites for everything in
layer 2 and beyond.

| Primitive | Module | Signature (sketch) | Notes |
|---|---|---|---|
| `propagator(H, t)` | `engine.py` | `U = expm(-i H t)` via eigendecomp | reuse `EigenSystem.of(H)` cache |
| `apply(U, rho)` | `engine.py` | `U @ rho @ U.conj().T` | trivial wrapper, keep style consistent |
| `pulse(sys, channel, angle, phase)` | `pulses.py` (new) | returns unitary `U_p` | hard pulse, ideal, on one nucleus type |
| `evolve(rho, H, t)` | `engine.py` | `apply(propagator(H,t), rho)` | |
| `acquire(H, rho, detect, n, dt, t2_star)` | `engine.py` | thin wrapper over current `fid` | accepts pre-prepared `rho` |

**Cost estimate:** ~1 file (`pulses.py`, ~80 lines) + ~30 lines added to
`engine.py`. Unblocks all multi-pulse sequences.

---

## 2. Sequence layers

### Layer 1 — 1D basics (target: v0.2)

These finish "every standard 1D experiment".

| ID | Bruker name | Description | Status | New primitives needed |
|---|---|---|---|---|
| `pulse_acquire` | `zg` | 90° — acq | partially done (current `thermal → fid` path) | none, just wrap as `sequences.pulse_acquire(...)` |
| `pulse_acquire_decoupled` | `zgpg` / `zgig` | 90°(X) — acq with ideal heteronuclear decoupling on ¹H | new | ideal-decoupling switch (drop ¹H spins or zero heteronuclear J) |

Acceptance:
- AX ¹H system (e.g. ethanol CH₃/CH₂) reproduces textbook triplet/quartet.
- ¹³C{¹H} of acetone gives one line at 206 ppm and one at 30 ppm with
  no multiplets.

---

### Layer 2 — Single-channel multi-pulse (target: v0.3)

These exercise `pulse + evolve` for the first time, still 1D in
detection.

| ID | Bruker name | Description | New physics |
|---|---|---|---|
| `spin_echo` | `hahnecho` | 90 — τ — 180 — τ — acq | refocuses chemical shift; J evolution survives → can use to *measure* J |
| `inversion_recovery` | `t1ir` | 180 — τ — 90 — acq, τ swept | first sequence that *needs* T1; add manual T1 input per spin (no full relaxation matrix yet) |
| `cpmg` | `cpmg` | 90 — (τ — 180 — τ)ⁿ — acq | T2 / J modulation; same machinery as spin echo |

Acceptance:
- AX spin echo at τ = 1/(2J) shows phase inversion of the doublet
  (in-phase ↔ anti-phase) — confirms J evolution is correct.
- Inversion recovery on a single spin recovers the input T1 from a 3-parameter fit.

**New core change for T1:** add `T1: np.ndarray | None` field to
`SpinSystem`, applied as exponential decay on `Iz` components between
events. Stays optional; defaults to `None` (no relaxation).

---

### Layer 3 — 2D heteronuclear correlation (target: v0.4)

This is the practical 2D milestone. HSQC alone is the most-used 2D in
chemistry.

| ID | Bruker name | Description | New primitives |
|---|---|---|---|
| `hsqc` | `hsqcetgp` (simplified) | INEPT(¹H→¹³C) — t₁(¹³C) — reverse-INEPT — acq(¹H) with ¹³C decoupling | 2D acquisition loop (`t1` array → matrix `S(t1, t2)`) |
| `hmbc` | `hmbcgplpndqf` (simplified) | like HSQC but τ = 1/(2·J_long) ≈ 60 ms, low-pass J filter optional | shares 90% with HSQC |

Acceptance:
- HSQC of ethanol shows two cross peaks at (1.2/17.9) and (3.7/57.3) ppm.
- HMBC of acetone shows the (2.1/206) cross peak (3-bond).

**New core change:** `sequences/twoD.py` introduces a generic 2D wrapper
that takes a sequence function, sweeps `t1`, calls `fid` for `t2`,
returns a 2D `np.ndarray`. Processing module gets `fft2_spectrum`.

---

### Layer 4 — 2D homonuclear correlation (target: v0.5)

| ID | Bruker name | Description | Notes |
|---|---|---|---|
| `cosy` | `cosygp` | 90 — t₁ — 90 — t₂ | trivial extension once 2D framework exists |
| `tocsy` | `mlevphpr` | 90 — t₁ — spinlock(τₘ) — t₂ | use "ideal isotropic mixing" approximation first: average Hamiltonian = 0, propagator = full J-driven mixing matrix |

Acceptance:
- COSY of ethanol shows the expected (1.2,3.7) cross peak.
- TOCSY with long τₘ on an AMX system propagates magnetization to all 3 spins.

---

### Deferred (target: v0.6+ or v1.0)

Need infrastructure we don't have yet.

| ID | Reason it's deferred |
|---|---|
| `noesy`, `roesy`, `exsy` | require dipolar / chemical-exchange relaxation matrix (Solomon eqs.) — full relaxation module |
| `dept`, `apt` | implementable in Layer 3 if user demand exists; skipped only because HSQC covers most use cases |
| Solid-state (CP-MAS, REDOR, DNP) | requires anisotropic interactions (CSA, dipolar) and MAS; out of scope for v1.0 |
| Realistic CPD decoupling (WALTZ-16, GARP) | requires sub-pulse time-stepping; current "ideal decoupling" suffices for line-shape simulation |
| Shaped / adiabatic / selective pulses | needs time-dependent Hamiltonian integrator |
| Gradient pulses & coherence selection by gradients | dense-matrix sim can replace this with explicit coherence-order projection; defer |

---

### ZULF-specific track (parallel, owner decides priority)

The current engine was originally ZULF-capable. If ZULF is the primary
research direction, these come *before* HSQC.

| ID | Description |
|---|---|
| `zulf_pulse_acquire` | prepolarized → sudden field drop → free evolution in `H_J_only` → `Mx` detection (already supported via current primitives, just needs sequence wrapper) |
| `zulf_j_spectroscopy` | same as above, longer acquisition, narrower features |
| `zulf_pulsed` | DC pulse trains in zero field (heteronuclear excitation) — needs `evolve` under a different `H` for short windows |
| `sabre` / parahydrogen prep | requires non-thermal initial states and possibly time-dependent J/dipolar — defer until requested |

---

## 3. File layout once Layer 2 lands

```
src/core/
  __init__.py            # extend with re-exports of pulses/sequences
  isotopes.py
  ops.py
  system.py
  hamiltonian.py
  states.py
  detection.py
  pulses.py              # NEW: pulse(sys, channel, angle, phase) → U
  engine.py              # +propagator, +apply, +evolve, +acquire
  processing.py          # +fft2_spectrum (Layer 3)
src/sequences/           # NEW package, one file per family
  __init__.py
  oneD.py                # pulse_acquire, pulse_acquire_decoupled, spin_echo, ir, cpmg
  twoD.py                # 2D loop helper
  hetcor.py              # hsqc, hmbc
  homcor.py              # cosy, tocsy
  zulf.py                # zulf_*
tests/
  test_layer1_1d.py
  test_layer2_echo.py
  test_layer3_hsqc.py
  ...
```

---

## 4. Open questions (need answers before coding Layer 2)

1. **T1 / T2 model** — start with per-spin scalar T1/T2 (Bloch-style), or
   jump straight to a relaxation matrix? Recommendation: scalar first,
   matrix in v1.0.
2. **Phase cycling** — implement explicitly (loop and sum), or rely on
   density-matrix simulation already giving the "correct" coherence
   pathway? Recommendation: skip phase cycling; document that the
   simulator returns the pure desired pathway.
3. **Acquisition during decoupling** — keep ideal (no Hamiltonian on
   decoupled channel during acq) or honor a user-supplied CPD scheme?
   Recommendation: ideal only, with a comment in the docstring.
4. **2D states-TPPI / echo-antiecho** — pick one convention for v0.4 and
   document it. Recommendation: States-TPPI (simpler, real FT).

---

## 5. Acceptance / regression tests per layer

Each layer ships with at least one numerical regression test that
*does not* depend on the engine internals (so refactors don't break
them). Suggested fixtures:

- **AX** (¹H₂, J=7 Hz, Δδ=1 ppm at 500 MHz) — first-order doublet/doublet
- **AB** (¹H₂, J=7 Hz, Δδ such that 2πΔν ≈ πJ) — roof effect, intensities asymmetric
- **AMX** (¹H₃, e.g. styrene vinyl) — three-spin test for COSY/TOCSY
- **Ethanol** — heteronuclear test for HSQC

Numerical tolerance: peak position ±0.5 Hz, integrated intensity ±1%.

---

## 6. Milestones

| Version | Contents | Gate |
|---|---|---|
| v0.2 | Layer 1 (1D basics) + Layer 1 tests | AX/AB/ethanol-1D pass |
| v0.3 | Layer 2 (echo / IR / CPMG) + T1 field | spin-echo phase inversion at τ=1/(2J) |
| v0.4 | Layer 3 (HSQC, HMBC) + 2D processing | ethanol HSQC reproduces 2 cross peaks |
| v0.5 | Layer 4 (COSY, TOCSY) | ethanol COSY cross peak |
| v0.6 | ZULF sequence wrappers (if not already in v0.2) | pyridine ZULF J-spectrum |
| v1.0 | Relaxation matrix + NOESY + small UI | NOE buildup curve |
