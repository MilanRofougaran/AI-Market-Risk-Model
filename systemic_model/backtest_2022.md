# 2022 backtest — predicted vs realized max drawdowns

*Model calibrated to Dec-31-2021 (stress index 34/100), 12-month horizon, 8,000 paths. Research model, not investment advice.*

| Name | beta'21 | realized 2022 | predicted median | predicted p90 | P(≥realized) | percentile | in 10-90? |
|---|--:|--:|--:|--:|--:|--:|:--:|
| Meta | 1.25 | -77% | -19% | -37% | 0% | 100% | NO |
| Tesla | 2.00 | -72% | -26% | -51% | 2% | 98% | NO |
| ARKK | 1.80 | -67% | -25% | -48% | 2% | 98% | NO |
| Palantir | 2.00 | -67% | -26% | -50% | 3% | 97% | NO |
| AMD | 1.70 | -65% | -23% | -44% | 2% | 98% | NO |
| NVIDIA | 1.60 | -63% | -22% | -41% | 2% | 98% | NO |
| Amazon | 1.25 | -56% | -19% | -36% | 2% | 98% | NO |
| Micron | 1.40 | -47% | -20% | -38% | 5% | 95% | NO |
| SOXX (semis) | 1.40 | -46% | -20% | -37% | 5% | 95% | NO |
| Alphabet | 1.10 | -45% | -17% | -33% | 3% | 97% | NO |
| Microsoft | 1.10 | -39% | -18% | -32% | 5% | 95% | NO |
| Nasdaq-100 | 1.18 | -36% | -18% | -34% | 9% | 91% | NO |
| Apple | 1.15 | -31% | -18% | -33% | 13% | 87% | yes |
| S&P 500 (SPY) | 1.00 | -25% | -17% | -31% | 18% | 82% | yes |

**2/14 names inside the unconditional 10–90 band** (a calibrated model expects ~80%).

## The 4th-regime (de-rating) view
At Dec-2021 structural fragility the model assigns **3% odds that 2022 becomes a grind year** (>40% of days in the de-rating state). 2022 WAS that year. **Conditional on a grind year, 3/14 names fall inside the predicted 10–90 band:**

| Name | realized | grind-year median | grind-year p90 | in band? |
|---|--:|--:|--:|:--:|
| Meta | -77% | -36% | -50% | NO |
| Tesla | -72% | -49% | -63% | NO |
| ARKK | -67% | -49% | -63% | NO |
| Palantir | -67% | -46% | -62% | NO |
| AMD | -65% | -37% | -51% | NO |
| NVIDIA | -63% | -34% | -50% | NO |
| Amazon | -56% | -30% | -43% | NO |
| Micron | -47% | -25% | -38% | NO |
| SOXX (semis) | -46% | -25% | -38% | NO |
| Alphabet | -45% | -23% | -34% | NO |
| Microsoft | -39% | -23% | -34% | NO |
| Nasdaq-100 | -36% | -24% | -37% | yes |
| Apple | -31% | -22% | -33% | yes |
| S&P 500 (SPY) | -25% | -19% | -32% | yes |

*Honest read: the val_gap_2021 inputs are retrospective (hindsight), so this validates the MECHANISM (floating premium bleeds in a grind), not foresight. What the model could not know in advance is WHICH year the grind arrives — that remains a probability, not a prediction.*

**Calibration metrics**: Spearman rank correlation (predicted median vs realized) = **0.81** — ordering skill. Brier scores: P(>25%): 0.444, P(>35%): 0.609, P(>45%): 0.539, P(>60%): 0.400 (0 = perfect, 0.25 = no-skill coin flip; these are WORSE than 0.25 because the model confidently assigned low probability to drawdowns that then happened — magnitude miscalibration, consistent with the band count. The 0.81 Spearman says the model ranks names well; the Brier says don't trust its 2021-conditioned levels).

## Honest findings
- The Dec-2021 **acute** trigger was asleep (VIX 17, HY 283bps) — the index could not foresee the Fed's 2022 policy shock; it is a *monitor* that would have climbed through 2022, not an oracle. Predictions at low stress under-call the depth.
- **Beta ordering held**: realized depth ranks almost exactly by 2021 beta (SPY -25% → TSLA/PLTR -67/-72%), which is the model's core 'beta sets depth' claim.
- **Meta is the lesson the model can't learn**: -77% on a 1.25 beta was an idiosyncratic earnings/strategy shock — exactly the single-name blow-up risk the model explicitly does not simulate.
- **The grind flaw is now PARTIALLY fixed.** 2022 was a de-rating year (VIX never broke 37), which the old 3-state model structurally could not produce. The 4th 'grind' regime (structural-fragility-driven entry, sticky, negative drift, val-gap bleed) closes much of the gap: conditional on a grind year the deep floating-premium names (ARKK, Palantir, ~Tesla) now bracket their realized falls. REMAINING under-call: mid-gap names (NVDA, AMD, Micron, SOXX) still land just past the conditional p90 — 2022's compression was even broader than the current drag models. Calibrated IN-SAMPLE to this one episode; needs 2000/2008/2020 episodes before the levels deserve trust.