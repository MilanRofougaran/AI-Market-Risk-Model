# Verification & Change Record


> **UPDATE (Jun 2026, post external review):** the simulation window discussed
> below as 882 days has been **extended to 1134 days** so the 36-month recovery
> point is fully observed even for a trough at the 18-month edge (the 882-day
> window right-censored late recoveries and inflated the >3y tail by ~3-5pts).
> The engine is now FOUR-state (calm/stress/crisis + de-rating grind), the
> leveraged-ETF exclusion bug is fixed, and `test_model.py` (20+ invariants,
> incl. generated-output leak checks) guards all of this. Sections below that
> reference 882 days or three regimes describe the PREVIOUS version.


This document is the package's own account of what it is, what changed in the
most recent revision, and what was tested. It exists so that anyone opening the
system later — including a future session — can see the verified state without
having to re-derive it. Read it alongside `README.md`, which explains how the
system works; this file explains what was *checked*.

**This is a research model. It is not investment advice, and its author is not
a licensed financial advisor.**

---

## 1. What this system is, in one paragraph

A regime-switching Monte Carlo model for short-horizon (6/12/18-month) drawdown
and recovery risk in US equities, high-tech, and semiconductors, with a
bottom-up TAM-penetration layer that decomposes each company's P/E multiple
into the part its growth runway can justify and the part that floats free of
it. Sitting on top is a discovery agent that screens the broad market for
high-growth candidates, remembers its findings across runs, and feeds survivors
into the model. The model's governing purpose is **catastrophe avoidance**: it
exists to distinguish a deep-but-survivable drawdown from a permanent, systemic
loss.

## 2. The core design principle (unchanged, and the reason the model works)

> **Beta sets how deep a name falls in a panic. TAM-penetration sets whether it
> recovers.**

These are routed into different parts of the engine on purpose. Beta drives the
drawdown *depth* (a short-timescale, flows-and-fear phenomenon). TAM-penetration
drives the *recovery* (whether the fundamental that justified the multiple is
still intact on the other side). TAM never touches beta — doing so would
double-count the bull case the market has already priced.

## 3. What changed in this revision (the catastrophe-avoidance refit)

The model was reframed around a stated tolerance: **a drawdown that recovers
within roughly 4–18 months is acceptable; one that drags past ~18 months is the
systemic threat to defend against.** Four concrete changes followed:

1. **Recovery is now a CURVE, not a hard threshold.** The engine reports the
   cumulative probability of recovery at a schedule of horizons (6, 9, 12, 15,
   18, 24, 30, 36 months). Horizons past the suggested 18-month edge are
   *flagged* (`beyond_suggested=True`), not discarded — the threshold is a
   movable suggestion the user sets, not a wall baked into the code.
   (Engine: `recovery_curve()`. Calibration: `RECOVERY_SCHEDULE_MONTHS`.)

2. **`P(never)` is now a first-class output.** The probability that a drawdown
   is *still underwater at the end of the (generous) simulation* is the truly
   permanent / systemic-failure class — the single most important number for
   catastrophe avoidance, and the one a hard threshold would hide by lumping
   "slow but heals" together with "never heals."

3. **The recovery mandate moved from 24 to 18 months**, and the simulation was
   *lengthened* to 882 days (not shortened). This is the opposite of truncating
   the sim: a long sim is required to *distinguish* a month-26 recovery from a
   never-recovery. Truncating to 18 months would have censored that distinction
   and biased late-horizon drawdowns toward false "failure."
   (Calibration: `MANDATE_MONTHS = 18`, `SIM["days"] = 882`.)

4. **Runway normalization is now ANCHORED to a fixed ideal**, not the dataset
   maximum. Previously each name's runway was scored relative to the best name
   in the set — which silently rebased every score whenever the universe
   changed. Since the discovery agent *changes the universe by design*, runway
   is now measured against a fixed theoretical ideal (≈2% penetration, 50% TAM
   CAGR, full quality+dominance), so adding or removing candidates no longer
   distorts existing scores. (Engine: `RUNWAY_ANCHOR` in `decompose_premium()`.)

Also adopted earlier, retained here: a **Dominance factor** (a large TAM is
worth less if you can't defend your share) and a **Capex-coupling elasticity**
(physical/inelastic demand survives a credit crash; discretionary demand
freezes). Both came from an external "TDVM" review; its *ideas* were adopted,
its decimal-precise output tables and 5-year framing were explicitly rejected.

### Note on comparing to older runs
Recovery numbers are **lower** than earlier versions for two deliberate
reasons, not because anything worsened: the deadline is stricter (18m vs 24m),
and the runway yardstick stopped grading on a curve. A more demanding, more
honest standard is the correct bias for a catastrophe-avoidance tool.

## 4. What was verified (integration test, this revision)

Every layer was executed from a clean state:

| Layer | Check | Result |
|---|---|---|
| `calibration.py` | self-check runs; hazard tail cross-validates regime probs | PASS |
| `run.py` | full model executes end-to-end at 882-day / 18m settings | PASS |
| labels | printed headers now read the mandate from calibration at runtime | PASS (fixed) |
| `run_dominance_sweep.py` | executes under new calibration (2-name fast check) | PASS |
| discovery `registry.py` | loads prior runs, computes trajectories | PASS |
| discovery `screen_rules.py` | ranks candidates on the demonstrated/forward blend | PASS |
| discovery `agent.py` | builds the 7-stage plan with warm start | PASS |

### Defect found and fixed during this test
Printed table headers still said `P(recover<2y)` after the mandate had moved to
18 months. The *math* was correct; only the *label* was stale. Fixed at the
cause: headers now pull `MANDATE_MONTHS` from calibration at runtime, so they
can never again drift away from the math. Change the mandate and the labels
update themselves.

### Verified at reduced scale (not full production scale)
The dominance sweep was confirmed on 2 names at lower path counts, and the
discovery agent via its self-tests rather than a fresh live web screen. These
are the heavy / research-bound components; the goal was to confirm they
*execute correctly under the new calibration*, which they do. Full-scale runs
are available on demand (they take the longer batched effort).

## 5. Robust findings (survive the sensitivity sweep)

- **Top recovery tier, robust across all score perturbations:** NVIDIA,
  Broadcom, Marvell.
- **Bottom recovery tier, robust across all score perturbations:** Kioxia,
  Micron.
- **Fine ordering of the middle (Qualcomm, ARM, AMD) is calibration-dependent**
  — the sweep flags this; do not over-read it.
- **Systemic-tail reconciliation holds:** the simulation's emergent tail and
  the independent hazard-derived tail still agree on shape (≈2–3% / 4–6% / 6–9%
  at 6/12/18m).

## 6. How to run it

```bash
cd systemic_model
python3 run.py                  # full model: tables, sensitivity, reconciliation
python3 run_dominance_sweep.py  # moat-sensitivity matrix (heavier; batches on big universes)
python3 calibration.py          # quick self-check only
cd discovery && python3 agent.py   # show the discovery pipeline's stage plan
```

To update for a new month: edit `calibration.py` (every number is tagged
`[MEASURED]`, `[DERIVED]`, or `[JUDGMENT]`), then re-run `run.py`.

---

*Verification performed June 2026, on the catastrophe-avoidance revision of the
model. Engines: `engine.py` (regime-switching MC + TAM channels), discovery
layer in `discovery/`.*
