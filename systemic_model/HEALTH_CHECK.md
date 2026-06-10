# Systemic + TAM model — end-to-end health check (2026-06-08)

Ran the full pipeline stage-by-stage and audited every output. **Result: healthy. Every stage executes, all 39 invariant checks pass, every generated JSON is strict-parseable, the leveraged-ETF separation holds, the model is deterministic, and the core findings reproduce.**

## Stage-by-stage (the 8-step pipeline)

| # | Stage | Result |
|--:|---|---|
| 1 | Discovery (screen registry) | OK — 10 registry candidates re-scored |
| 2 | TAM bridge (make priceable) | OK — 42 priceable names (stocks + sector/broad ETFs) |
| 3 | Macro + systemic stress | OK — index **48/100** (structural 58, acute 25); engine == reports (the ordering bug stays fixed); crisis ×0.99, grind ×1.55 |
| 4 | Monte Carlo (regime-switching) | OK — 42 names; beta-ordering correct (NVDA P>25 ≈71%, VOO ≈45%, IonQ ≈90% on a quick 4k-path run) |
| 5 | Leveraged ETFs (vol-decay path) | OK — SOXL/TECL/TQQQ injected, P(>25%) ≈99–100%, >3y tail ≈56–58% |
| 6 | Change ledger | OK — snapshot recorded (24 in history) |
| 7 | Analysis layers | OK — correlation (neff ≈1.1, ρ 0.88–0.94), 2022 backtest, portfolio risk, valuation link, earn-back clock all run |
| 8 | Outputs | OK — both dashboards, both ETF views, both CSVs, artifacts rebuilt |

## Audits

- **Invariants:** 39 checks, **ALL PASS** (transition rows, stress consistency, contagion variance-preservation, grind mask, recovery window, leveraged-leak in CSV+HTML, ETF-cap survival, and the 5 buyback tests).
- **Strict JSON:** all 14 generated JSON files parse with no NaN/Infinity (cleaned the one stale baseline file).
- **Leveraged separation:** SOXL / TECL / TQQQ are `Trading`, never a growth tier. Tier counts: High 11, Moderate 19, Safe 12, Trading 3 = 45.
- **Determinism:** two identical runs match exactly; per-name results are now order-invariant (name-seeded idiosyncratic RNG).
- **Buyback slingshot:** dormant in the closed-form clock under mild compression (correct), fires in the MC only on deep accretive panics (validated: P(recover<18m) up, depth unchanged).
- **2022 backtest:** Spearman ≈0.89 (strong ordering), Brier worse than coin-flip (honest magnitude miscalibration), grind regime improves the conditional band — all reported transparently.

## Known limits (carried in the docs, not bugs)

Magnitude is softer than ranking (read tiers, not decimals); judgment inputs (TAM, growth, scores) are opinions swept ±0.15; single-name blow-ups, total return, and cyclical earnings-denominator collapse are not modeled; the grind regime is calibrated in-sample to 2022.

## Open v3 roadmap (optional, not blocking)

Multi-episode out-of-sample backtests (2000/2008/2020), a dynamic rate-driven BASE_PE, capex-intensity penalty, Numba speedups, and moving the universe data to JSON/YAML.

**RESEARCH MODEL — NOT INVESTMENT ADVICE.**
