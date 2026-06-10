# Systemic + TAM Risk Model

A reusable, regime-switching Monte Carlo model for short-horizon (6/12/18-month)
drawdown and recovery risk in US equities, high-tech, and semiconductors —
with a bottom-up TAM-penetration layer that decomposes each company's P/E
multiple into the part its growth runway can justify and the part that floats
free of it.

**This is a research model. It is not investment advice, and its author is not
a licensed financial advisor.** Every probability is a transparent function of
stated assumptions, not a forecast with hidden precision.

---

## Why this model is built the way it is

The single most important design decision is the **separation of calibration
from engine**:

- **`calibration.py`** holds every number that describes the real world (today's
  valuations, rates, credit, the regime probabilities, each company's revenue
  and TAM and judgment scores). *This is the file you edit when the world
  changes.*
- **`engine.py`** holds the mathematics that turns those numbers into results.
  *You should rarely need to touch this.*

That seam is what makes the model **improvable rather than disposable**. To
bring it up to date next month, you edit one clearly-labeled file of assumptions
and re-run — you never have to reverse-engineer the math.

The second key idea is **where TAM enters the mathematics**. TAM penetration is
*not* put on beta. The reasoning:

> **Beta sets how deep a name falls in a panic. TAM-penetration sets whether it
> recovers.**

In a liquidity-driven selloff, a stock falls roughly with its beta regardless of
how much runway it has — price is dominated by flows and fear, not by distance
to a TAM ceiling. So penetration does not change the *depth* of a drawdown; it
changes whether the company *climbs back out* within your mandate. TAM is
therefore routed into three channels — a small **drift** effect, a large
**recovery-probability** effect, and a **bounded crisis-only tail** widening —
never into beta. Letting TAM swing the drawdown depth would double-count the
bull case the market has already priced.

---

## File structure

```
systemic_model/
  calibration.py   ← ALL real-world numbers. Edit this. Heavily commented.
  engine.py        ← The mathematics (3 parts: paths, premium decomp, recovery).
  run.py           ← The driver. Run this: `python3 run.py`
  results.json     ← Output (created by run.py). Feed to a report generator.
  README.md        ← This file.
```

## Running it

```bash
cd systemic_model
python3 run.py
```

This prints five tables, a sensitivity sweep, and a systemic-tail
reconciliation, then saves `results.json`. A run at 150,000 paths takes a few
minutes; raise `SIM["n_paths"]` to 300,000 in `calibration.py` for final,
smoother-tailed runs.

You can also run pieces:
```bash
python3 calibration.py     # self-check: prints the hazard-derived regime tail
python3 -c "import engine; print(engine.decompose_premium())"   # just the TAM decomposition (fast, no sim)
```

---

## How to update the model (the monthly / quarterly ritual)

Open **`calibration.py`** and work top to bottom:

1. **`AS_OF_DATE`** — set the date.
2. **`MACRO`** — refresh the dashboard from primary sources (forward P/E,
   CAPE, real 10y, Fed funds, VIX, oil, margin debt, hyperscaler capex). These
   document the world the model is calibrated to.
3. **`REGIME_PROBS`** — if your read of the cycle has shifted, re-derive. The
   helper `derive_regime_probs()` shows how the hazard transform turns the
   5-year base rates in `BASE_RATES_5YR` and the `CATALYST_PREMIUM` into the
   systemic/bear rows. Edit those two inputs and the derivation updates.
4. **`COMPANIES`** — as earnings and TAM estimates arrive, update each name's
   `rev_bn`, `tam_bn`, `tam_cagr`, `fwd_pe`, and the four judgment scores.
5. Re-run `run.py`. Everything downstream updates automatically.

Every number in `calibration.py` is tagged `[MEASURED]`, `[DERIVED]`, or
`[JUDGMENT]` so you know which kind of update you are making.

---

## The judgment scores (and why they are swept)

Four per-company inputs are honest opinions, not measurements:

| Score | Meaning | High value | Low value |
|---|---|---|---|
| `quality` | TAM credibility | customer-anchored, contracted | soft aggregate / cyclical |
| `earn_quality` | earnings durability | secular | price-spike / cyclical |
| `dominance` | market-share capture / moat | monopoly | fragmented |
| `capex_elastic` | does demand survive a credit crash | physical/inelastic | discretionary |

Because the ranking depends on these, `run.py` **sweeps each of them ±0.15** and
reports which conclusions survive (the *tiers*) and which shift (the *fine
ordering within a tier*). Read the output by tier, not by exact rank. This is
the model's built-in defense against dressing up judgment as precision.

`dominance` and `capex_elastic` were adopted from an external "TDVM" model
(Gemini). Its two ideas — that a large TAM is worth less if you cannot defend
your share, and that physical/inelastic demand survives a credit crash while
discretionary demand freezes — are sound and improve the model. Its *specific
output probabilities* and its five-year framing were **not** adopted, because
they assert a precision a path-simulation cannot support and because this model
is built for a short-horizon mandate where growth is deliberately the weaker
channel.

## The governing purpose: catastrophe avoidance

This model exists to prevent the permanent, mandate-breaking loss — not to
optimize returns. Recovery is treated as the *evidence* that a drawdown was
survivable rather than fatal. The stated tolerance: a drawdown that recovers
within roughly **4–18 months is acceptable**; one that drags past ~18 months is
the systemic threat to defend against.

Two consequences follow, and both are deliberate:

1. **Recovery is reported as a curve, not a hard pass/fail.** The engine gives
   the cumulative probability of recovery at a schedule of horizons (6 → 36
   months). Horizons past the suggested 18-month edge are *flagged* for the user
   to weigh, not silently discarded — **the threshold is a movable suggestion
   you set, not a wall baked into the code.**
2. **`P(never)` — still underwater at the end of the (long) simulation — is a
   first-class output.** It is the truly permanent / systemic-failure class, and
   it is the single most important number here. A hard threshold would hide it
   by lumping "slow but eventually heals" together with "never heals"; the curve
   pulls those apart.

The simulation runs to **882 days on purpose** (not truncated to the 18-month
mandate): a long sim is *required* to distinguish a month-26 recovery from a
never-recovery. Truncating would censor exactly the distinction the model
exists to make.

---

## What each engine part does

- **Part A — paths.** `_simulate_factor` walks the three-state volatility regime
  forward with a transition matrix and Student-t innovations, producing the
  daily macro factor Φ. `_price_path` loads each exposure onto Φ via beta, adds
  idiosyncratic noise, and compounds (leveraged products use a daily reset plus
  fee/borrow drag).
- **Part B — premium decomposition.** `decompose_premium` splits each multiple
  into justified vs. floating premium using runway = `(1−penetration) ×
  tam_cagr × quality × dominance`, normalized against a **fixed ideal anchor**
  (so an expanding discovery universe never rebases the scores), then builds a
  `fragility` score and a `recovery_quality` score (the latter scaled by
  `capex_elastic`). `company_to_spec` maps those scores onto the drift / tail /
  recovery channels.
- **Part C — measurement.** `_drawdown_and_recovery` finds each path's maximum
  drawdown within the horizon and its time-to-recovery (searched across the full
  long simulation so late and never- recoveries are distinguished, not
  censored). `recovery_curve` reports the dynamic recovery schedule and
  `P(never)`; `exceedance` and `recovery_stats` aggregate across paths.


---

## Ideas for future improvement

The architecture is designed to absorb these without disruption:

1. **Correlated idiosyncratic shocks.** Right now each name's private noise is
   independent. A factor structure on the idiosyncratic term (e.g. a shared
   "AI-capex" sub-factor) would make sector-specific cascades more realistic.
2. **A second macro factor.** Φ is single-factor. Adding a rates/duration factor
   would let names load differently on a rate shock vs. an equity shock.
3. **Endogenous catalyst premium.** The catalyst premium is currently a stated
   multiplier. It could be driven by the `MACRO` dashboard directly (e.g. a
   function of the oil price and the ERP) so it updates mechanically.
4. **Time-varying TAM.** `tam_cagr` is a single number; a declining-CAGR S-curve
   (fast now, saturating later) would sharpen the long-horizon penetration math.
5. **Portfolio layer.** The model scores names individually. A portfolio module
   that combines them (with the correlation structure from idea 1) would let you
   stress-test specific sleeves against the mandate directly.
6. **Backtesting harness.** Feed historical calibrations and check the model's
   drawdown/recovery probabilities against what actually happened — the natural
   next step for validating, not just specifying, the engine.

Each is a localized change: ideas 1–3 touch `engine.py` Part A, idea 4 touches
Part B, ideas 5–6 are new files that consume `results.json`.

---

*Companion to the Short-Horizon Systemic-Risk & Drawdown Model. Engines:
`engine.py` (regime-switching MC + TAM channels). Calibrated June 2026.*
