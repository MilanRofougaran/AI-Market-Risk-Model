# Patch notes — ARKK archetype fix + crash-growth into the MC recovery
(drop these 2 files into the project; both verified, 63/63 tests pass)

## 1. crash_growth.py  — ARKK consistency fix
- Added `"ARKK (ARK Innovation)": "broken"` to `ARCHETYPE`.
- Why: ARKK was fragile in solvency (ETF_SOLV_OVERRIDE 0.13 hazard) but the
  durability heuristic (no per-name SOLVENCY entry -> default rd 0.70) classed it
  `secular` -> 1.05 fast-recovery. The two channels now agree. Comment notes it's
  a judgment (switch to `cyclical` if you view ARKK as deeper-but-recovering).

## 2. engine.py  — thread crash-growth into the Monte-Carlo recovery channel
- In `company_to_spec`, `recov_shift` now adds `(crash_growth.recovery_g_mult(name) - 1.0)`:
  secular +0.05 (faster), cyclical -0.22 (slower but recovers), broken -0.50
  (slowest; clipped to -0.4 downstream).
- Lever choice: `recov_shift` scales recovery TIME only, never drawdown depth, so
  this keeps the model's "beta sets depth, growth/TAM sets recovery" rule intact.
- Consistency: shift = (cg_mult - 1) makes the MC recovery-time factor
  1/(1+shift) ~ 1/cg_mult equal the earn-back clock's 1/cg_mult scaling, so the
  clock view and the MC tail now tell the same story.
- Lazy import inside the function (matches the existing solvency pattern); no
  circular import (crash_growth doesn't import engine).

## Validated
- A/B on identical paths: P(>25% fall) IDENTICAL across all archetypes (depth
  untouched); median recovery 13.2m secular / 17.5m cyclical / 24.2m broken
  (cyclical 17.5/13.8 = 1.27x = 1/0.78, matching the clock).
- Live ETF tier table: DRAM (cyclical) >3y tail 0.286 vs SMH (secular) 0.239 at
  similar depth; ARKK (broken) now worst at 0.452 (was inheriting secular speed).
- `python3 test_model.py` -> ALL PASS (63 invariants). `run_all.py --light` clean.

## Still open (optional, noted earlier)
- Depth-scaling of the solvency hazard and toxic-dilution (both still step
  functions at their thresholds, not depth-ramped like the buyback slingshot).
