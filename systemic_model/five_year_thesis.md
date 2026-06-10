# The 5-year thesis, tested: drops are inevitable, recovery is the test, runway is the condition

*Model calibrated June 2026 · extended Monte Carlo at ~8 years (so recovery from late troughs isn't censored) · runway projection with growth fading to the TAM rate.*
**Research model, not investment advice.** This 18-month-calibrated engine is *extended* to longer horizons mechanically — read the long-horizon numbers as ranges and orderings, not point forecasts.

## Your thesis, restated

> Over a longer hold the chance of a drop goes up; but a drop is acceptable if recovery within ~24 months is likely — and recovery is likely as long as the TAM is still high and the company is still far from it, so there's earned upside (justified premium) to climb back to.

The model agrees, with one tightening. Three findings:

## 1. Over 5 years, a deep drawdown is near-certain

For these high-beta names, the probability of a >25% drawdown *occurring* climbs sharply with the holding period:

| Horizon | P(>25% drawdown occurs) |
|---|---|
| 18 months | ~50% |
| 36 months | ~79% |
| 60 months | ~93% |

So you are right to stop asking "will it drop?" Over a five-year hold it almost certainly will. The question becomes whether it comes back — exactly the reframing the model is built around.

## 2. Recovery keeps improving with patience — extend the line, improve the odds

Conditional on a >25% fall (trough within the first 3 years, recovery measured over 8), the probability of climbing back to the prior peak rises steadily the longer you're willing to wait:

| Recover by | NVIDIA (high runway) | Micron (cyclical) | Kioxia (near-saturated) |
|---|---|---|---|
| 18 months | 43% | 36% | 33% |
| **24 months** | **51%** | **44%** | **40%** |
| 36 months | 61% | 54% | 50% |
| 60 months | 71% | 65% | 61% |
| **Never (8y)** | **27%** | **33%** | **36%** |

This is the heart of your point: moving the acceptable-recovery line from 18 to 24 months lifts NVIDIA's odds from 43% to 51%, and out to 60 months to 71%. Patience is a lever — *if* the fundamental floor is there. And the spread between NVIDIA and Kioxia at every horizon is the runway difference doing its work.

## 3. The condition: the runway cushion must survive the hold

This is the tightening. The recovery odds above are not fixed — they rest on runway (distance from the TAM ceiling), and runway *decays as you hold* unless the TAM grows at least as fast as the company. Rolling each name's revenue (at fading growth) against its TAM forward five years:

| Name | growth vs TAM-growth | penetration 0y → 5y | cushion |
|---|---|---|---|
| NVIDIA | 45% vs 45% | 39% → 39% | holds |
| Microsoft | 14% vs 18% | 19% → 17% | holds (TAM outgrows it) |
| Broadcom | 38% vs 40% | 27% → 26% | holds |
| **Lumentum** | **55% vs 30%** | **12% → 21%** | **erodes — consuming runway** |
| **Applied Opto.** | **55% vs 30%** | rising | **erodes** |
| **IonQ** | **80% vs 42%** | rising, off ~0 base | **erodes** |

A name growing *faster* than its market (Lumentum, AAOI, IonQ) climbs toward its ceiling — its penetration rises, its runway shrinks, and the premium that recovery depends on quietly converts from justified to floating. A name whose TAM grows as fast as it does (NVIDIA) or faster (Microsoft) stays the same distance from the ceiling and keeps its cushion intact across the whole hold.

## The synthesis

Your rule is correct, sharpened to: **over a multi-year hold, accept the near-certain drawdown if (a) you'll extend recovery patience to ~24–36 months, and (b) the name's TAM keeps growing at least as fast as the name does — so it stays far from its ceiling and the premium stays earned.** Condition (b) is not a one-time check; it's why the registry re-screens every run, watching penetration creep. A name that passes today can fail in two years if it grows into its TAM faster than the TAM grows.

One caveat on reading the table in §2: those recovery and "never" figures are *conditional on a >25% fall*, so they are only directly comparable within a similar-beta cohort — a very high-beta name (AppLovin, IonQ) crosses −25% on shallow, recoverable dips, which flatters its conditional figures. For cross-name comparison, lean on the unconditional permanent-loss measure and recovery-quality from the main report.
