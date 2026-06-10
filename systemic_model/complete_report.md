# Systemic + TAM Risk — complete report

*Full universe (45 names: stocks + ETFs + leveraged) · model as of 2026-06-05 · generated 2026-06-10 · 21.9 S&P fwd P/E*

**Research model — not investment advice. Read tiers and ranges, not decimals.**

## Macro & systemic stress
Index **48/100** (moderate (watch-zone)) — structural fragility 58, acute trigger 25; scales the crisis odds ×0.99. Inputs: CAPE 39.4, real 10y 2.25%, VIX 24.0, Brent $96.0, HY spread 312bps, margin-debt YoY 45%.

## How the ranking works
Two axes, two sort keys — so different views order names differently on the same data:
- **Growth** (expected 18-month revenue growth) sets the **tier** (>40% / 15–40% / <15%). The tiered tables below and the dashboard's recovery bars are **sorted by growth** within each tier.
- **Risk is simulated**, not assigned: a regime-switching Monte Carlo where **beta sets how deep a name falls** and **TAM-penetration sets whether it recovers**. Headline = the **>3y tail** (P of a >25% fall still underwater at ~3.5y); macro-stress scales the crisis odds.
- **vs S&P / vs SCHD** combine both: (growth ÷ benchmark growth) × (benchmark tail ÷ name tail), benchmark = 1.00. **Sorting by this gives a different order than sorting by growth** — it can rank a lower-tail name above a faster grower. (This is why a growth-sorted plot and the vs-S&P ranking look different.)
- Not an expected-return forecast or a buy list. Growth and the judgment scores are opinions the model sweeps.

## Master ranking — by reward-to-risk (vs S&P, high to low)

*The **Recovery** column is the crash-growth-aware verdict: vs-S&P sorts by reward-to-risk and can float a broken or cyclical name up the list, so read it alongside Recovery — a '⚠ broken — avoid' or 'cyclical — rebound-dependent' tag overrides a flattering vs-S&P number.*

| # | Name | Type | Tier | Recovery | Growth | >3y tail | vs S&P | vs SCHD |
|--:|---|---|---|---|--:|--:|--:|--:|
| 1 | Astera Labs | stock | High | PEG-fast / MC-uncertain | 70% | 21% | 4.91 | 5.12 |
| 2 | NVIDIA | stock | High | PEG-fast / MC-uncertain | 45% | 15% | 4.46 | 4.65 |
| 3 | Palantir | stock | High | watch | 55% | 19% | 4.4 | 4.58 |
| 4 | Micron | stock | High | cyclical — rebound-dep | 50% | 20% | 3.75 | 3.91 |
| 5 | DRAM (Roundhill Memory) | ETF | High | cyclical — rebound-dep | 45% | 19% | 3.62 | 3.78 |
| 6 | Broadcom | stock | Moderate | diversified / safe | 38% | 16% | 3.59 | 3.74 |
| 7 | AMD | stock | High | cyclical — rebound-dep | 45% | 19% | 3.53 | 3.68 |
| 8 | CHAT (Roundhill GenAI) | ETF | Moderate | diversified / safe | 32% | 14% | 3.43 | 3.57 |
| 9 | Lumentum | stock | High | cyclical — rebound-dep | 55% | 24% | 3.38 | 3.53 |
| 10 | IonQ | stock | High | ⚠ broken — avoid | 80% | 38% | 3.16 | 3.29 |
| 11 | SMH (VanEck Semis) | ETF | Moderate | diversified / safe | 30% | 15% | 3.03 | 3.15 |
| 12 | SOXX (iShares Semis) | ETF | Moderate | diversified / safe | 28% | 14% | 2.9 | 3.02 |
| 13 | Applied Optoelectronics | stock | High | cyclical — rebound-dep | 55% | 30% | 2.78 | 2.9 |
| 14 | Marvell | stock | Moderate | cyclical — rebound-dep | 35% | 19% | 2.73 | 2.84 |
| 15 | AIQ (Global X AI) | ETF | Moderate | diversified / safe | 25% | 14% | 2.61 | 2.72 |
| 16 | CoreWeave | stock | High | cyclical — rebound-dep | 60% | 43% | 2.1 | 2.19 |
| 17 | Vertiv | stock | Moderate | cyclical — rebound-dep | 28% | 22% | 1.92 | 2.0 |
| 18 | AppLovin | stock | Moderate | cyclical — rebound-dep | 30% | 24% | 1.87 | 1.94 |
| 19 | ARKK (ARK Innovation) | ETF | High | ⚠ broken — avoid | 42% | 34% | 1.86 | 1.94 |
| 20 | Meta | stock | Moderate | diversified / safe | 18% | 15% | 1.85 | 1.92 |
| 21 | ARM | stock | Moderate | diversified / safe | 25% | 21% | 1.82 | 1.89 |
| 22 | QTUM (Defiance Quantum) | ETF | Moderate | ⚠ broken — avoid | 22% | 19% | 1.73 | 1.8 |
| 23 | NUKE (Nuclear/Uranium) | ETF | Moderate | diversified / safe | 22% | 19% | 1.7 | 1.77 |
| 24 | GRID (Smart Grid) | ETF | Moderate | diversified / safe | 18% | 17% | 1.55 | 1.62 |
| 25 | Microsoft | stock | Safe | diversified / safe | 14% | 14% | 1.5 | 1.56 |
| 26 | Coherent | stock | Moderate | cyclical — rebound-dep | 25% | 26% | 1.46 | 1.52 |
| 27 | IGV (Software) | ETF | Moderate | diversified / safe | 20% | 21% | 1.45 | 1.51 |
| 28 | Oracle | stock | Moderate | diversified / safe | 16% | 17% | 1.39 | 1.45 |
| 29 | QQQ (Nasdaq-100) | ETF | Moderate | diversified / safe | 16% | 17% | 1.39 | 1.45 |
| 30 | VGT (Info Tech) | ETF | Moderate | diversified / safe | 15% | 17% | 1.32 | 1.38 |
| 31 | DTCR (Data Ctr Infra) | ETF | Safe | diversified / safe | 14% | 18% | 1.18 | 1.23 |
| 32 | VOO (S&P 500) | ETF | Safe | diversified / safe | 9% | 14% | 1.0 | 1.04 |
| 33 | Amazon | stock | Safe | diversified / safe | 13% | 20% | 0.98 | 1.02 |
| 34 | Alphabet | stock | Safe | diversified / safe | 12% | 18% | 0.97 | 1.01 |
| 35 | SCHD (Dividend) | ETF | Safe | diversified / safe | 6% | 9% | 0.96 | 1.0 |
| 36 | Texas Instruments | stock | Safe | cyclical — rebound-dep | 14% | 22% | 0.94 | 0.98 |
| 37 | Tesla | stock | Moderate | cyclical — rebound-dep | 17% | 33% | 0.78 | 0.81 |
| 38 | Qualcomm | stock | Safe | cyclical — rebound-dep | 8% | 17% | 0.69 | 0.72 |
| 39 | Cisco | stock | Safe | diversified / safe | 6% | 13% | 0.68 | 0.71 |
| 40 | IBM | stock | Safe | diversified / safe | 5% | 15% | 0.51 | 0.53 |
| 41 | Apple | stock | Safe | diversified / safe | 7% | 21% | 0.5 | 0.52 |
| 42 | Kioxia | stock | Safe | cyclical — rebound-dep | 5% | 23% | 0.33 | 0.34 |

### Trading vehicles — excluded from the ranking (path-dependent decay)

| Name | P(>25% fall) | >3y tail | note |
|---|--:|--:|---|
| SOXL (3x Semis) | 100% | 28% | 3x daily reset; volatility decay; not a growth holding |
| TECL (3x Tech) | 98% | 28% | 3x daily reset; volatility decay; not a growth holding |
| TQQQ (3x NDX) | 98% | 28% | 3x daily reset; volatility decay; not a growth holding |

*(The tiered tables below are the same names sorted by growth within tier — a different sort, same data.)*

## TIER 1  ·  HIGH growth (>40% expected, 18m)

| Name | Type | Recovery | Growth | P(>25% fall) | recover 2y | >3y tail | ×S&P | vs S&P | vs SCHD |
|---|---|---|--:|--:|--:|--:|--:|--:|--:|
| IonQ | stock | ⚠ broken — avoid | 80% | 73% | 30% | 38% | 2.81× | 3.16 | 3.29 |
| Astera Labs | stock | PEG-fast / MC-uncertain | 70% | 73% | 51% | 21% | 1.58× | 4.91 | 5.12 |
| CoreWeave | stock | cyclical — rebound-dep | 60% | 84% | 34% | 43% | 3.18× | 2.1 | 2.19 |
| Palantir | stock | watch | 55% | 59% | 45% | 19% | 1.39× | 4.4 | 4.58 |
| Lumentum | stock | cyclical — rebound-dep | 55% | 64% | 41% | 24% | 1.81× | 3.38 | 3.53 |
| Applied Optoelectronics | stock | cyclical — rebound-dep | 55% | 73% | 39% | 30% | 2.19× | 2.78 | 2.9 |
| Micron | stock | cyclical — rebound-dep | 50% | 61% | 47% | 20% | 1.48× | 3.75 | 3.91 |
| AMD | stock | cyclical — rebound-dep | 45% | 51% | 36% | 19% | 1.42× | 3.53 | 3.68 |
| NVIDIA | stock | PEG-fast / MC-uncertain | 45% | 53% | 51% | 15% | 1.12× | 4.46 | 4.65 |
| DRAM (Roundhill Memory) | ETF | cyclical — rebound-dep | 45% | 55% | 46% | 19% | 1.38× | 3.62 | 3.78 |
| ARKK (ARK Innovation) | ETF | ⚠ broken — avoid | 42% | 73% | 34% | 34% | 2.51× | 1.86 | 1.94 |

## TIER 2  ·  MODERATE growth (15-40%)

| Name | Type | Recovery | Growth | P(>25% fall) | recover 2y | >3y tail | ×S&P | vs S&P | vs SCHD |
|---|---|---|--:|--:|--:|--:|--:|--:|--:|
| Broadcom | stock | diversified / safe | 38% | 47% | 46% | 16% | 1.18× | 3.59 | 3.74 |
| Marvell | stock | cyclical — rebound-dep | 35% | 58% | 46% | 19% | 1.43× | 2.73 | 2.84 |
| CHAT (Roundhill GenAI) | ETF | diversified / safe | 32% | 43% | 43% | 14% | 1.04× | 3.43 | 3.57 |
| AppLovin | stock | cyclical — rebound-dep | 30% | 81% | 49% | 24% | 1.79× | 1.87 | 1.94 |
| SMH (VanEck Semis) | ETF | diversified / safe | 30% | 43% | 43% | 15% | 1.1× | 3.03 | 3.15 |
| Vertiv | stock | cyclical — rebound-dep | 28% | 57% | 38% | 22% | 1.62× | 1.92 | 2.0 |
| SOXX (iShares Semis) | ETF | diversified / safe | 28% | 44% | 43% | 14% | 1.07× | 2.9 | 3.02 |
| Coherent | stock | cyclical — rebound-dep | 25% | 66% | 41% | 26% | 1.9× | 1.46 | 1.52 |
| ARM | stock | diversified / safe | 25% | 52% | 42% | 21% | 1.53× | 1.82 | 1.89 |
| AIQ (Global X AI) | ETF | diversified / safe | 25% | 42% | 43% | 14% | 1.06× | 2.61 | 2.72 |
| QTUM (Defiance Quantum) | ETF | ⚠ broken — avoid | 22% | 48% | 32% | 19% | 1.42× | 1.73 | 1.8 |
| NUKE (Nuclear/Uranium) | ETF | diversified / safe | 22% | 50% | 38% | 19% | 1.44× | 1.7 | 1.77 |
| IGV (Software) | ETF | diversified / safe | 20% | 45% | 33% | 21% | 1.54× | 1.45 | 1.51 |
| Meta | stock | diversified / safe | 18% | 46% | 45% | 15% | 1.08× | 1.85 | 1.92 |
| GRID (Smart Grid) | ETF | diversified / safe | 18% | 36% | 29% | 17% | 1.29× | 1.55 | 1.62 |
| Tesla | stock | cyclical — rebound-dep | 17% | 80% | 38% | 33% | 2.44× | 0.78 | 0.81 |
| Oracle | stock | diversified / safe | 16% | 40% | 35% | 17% | 1.28× | 1.39 | 1.45 |
| QQQ (Nasdaq-100) | ETF | diversified / safe | 16% | 38% | 29% | 17% | 1.28× | 1.39 | 1.45 |

## TIER 3  ·  SAFE / smaller growth (<15%)

| Name | Type | Recovery | Growth | P(>25% fall) | recover 2y | >3y tail | ×S&P | vs S&P | vs SCHD |
|---|---|---|--:|--:|--:|--:|--:|--:|--:|
| VGT (Info Tech) | ETF | diversified / safe | 15% | 38% | 30% | 17% | 1.26× | 1.32 | 1.38 |
| Microsoft | stock | diversified / safe | 14% | 40% | 41% | 14% | 1.04× | 1.5 | 1.56 |
| Texas Instruments | stock | cyclical — rebound-dep | 14% | 47% | 28% | 22% | 1.65× | 0.94 | 0.98 |
| DTCR (Data Ctr Infra) | ETF | diversified / safe | 14% | 30% | 21% | 18% | 1.31× | 1.18 | 1.23 |
| Amazon | stock | diversified / safe | 13% | 57% | 44% | 20% | 1.47× | 0.98 | 1.02 |
| Alphabet | stock | diversified / safe | 12% | 41% | 31% | 18% | 1.37× | 0.97 | 1.01 |
| VOO (S&P 500) | ETF | diversified / safe | 9% | 28% | 27% | 14% | 1.0× | 1.0 | 1.04 |
| Qualcomm | stock | cyclical — rebound-dep | 8% | 45% | 42% | 17% | 1.29× | 0.69 | 0.72 |
| Apple | stock | diversified / safe | 7% | 45% | 34% | 21% | 1.56× | 0.5 | 0.52 |
| Cisco | stock | diversified / safe | 6% | 32% | 35% | 13% | 0.98× | 0.68 | 0.71 |
| SCHD (Dividend) | ETF | diversified / safe | 6% | 19% | 22% | 9% | 0.69× | 0.96 | 1.0 |
| IBM | stock | diversified / safe | 5% | 26% | 23% | 15% | 1.08× | 0.51 | 0.53 |
| Kioxia | stock | cyclical — rebound-dep | 5% | 61% | 44% | 23% | 1.69× | 0.33 | 0.34 |

## Trading vehicles — 3x leveraged (volatility decay; excluded from tiers & rankings)

| Name | Type | Recovery | Growth | P(>25% fall) | recover 2y | >3y tail | ×S&P | vs S&P | vs SCHD |
|---|---|---|--:|--:|--:|--:|--:|--:|--:|
| SOXL (3x Semis) | ETF | — | 60% | 100% | 59% | 28% | 2.11× | 3.16 | 3.29 |
| TECL (3x Tech) | ETF | — | 50% | 98% | 58% | 28% | 2.06× | 2.7 | 2.82 |
| TQQQ (3x NDX) | ETF | — | 45% | 98% | 58% | 28% | 2.06× | 2.43 | 2.53 |

## How to read it
- **Growth** sets the tier (>40% / 15–40% / <15%, expected 18m).
- **>3y tail** = chance a >25% fall is still underwater at ~3.5y.
- **×S&P** = that tail as a multiple of the S&P's.
- **vs S&P / vs SCHD** = (growth ÷ benchmark growth) × (benchmark tail ÷ name tail); benchmark = 1.00; above 1 = more growth per unit of long-drawdown risk than the benchmark.

## Caveats
The scaling is growth-tilted, so it under-penalizes the fat tails of leveraged ETFs (read their ~100% P(>25% fall) directly). Correlation is high (~0.9) and surfaced as a warning, not in per-name cells. Company-specific blow-ups, total return (dividends/fees/taxes), and the judgment inputs (TAM, permanence, scores) are limitations. Permanence-weighted 'true permanent loss' is in tier_table.csv as the risk-tilted alternative.

## ETF recovery lens (basket > single-name)
A single stock's crash is an idiosyncratic lottery; an ETF averages it away, so the question becomes theme TAM/SAM durability + basket financial resilience, not one CEO. theme/resilience/top-3-cov are over the model-COVERED subset; **top-3 fund** is whole-fund; LOW coverage = decimals default-driven, trust the class only.

| ETF | class | coverage | conf | theme dur | fin resil | fragile wt | top-3 fund | top-3 cov | eff N | fast/slow/perm |
|---|---|--:|:--:|--:|--:|--:|--:|--:|--:|---|
| CHAT (Roundhill GenAI) | thematic-diversified | 46% | medi | 0.69 | 0.76 | 0% | 18% | 39% | 9.3 | 67/29/4% |
| SMH (VanEck Semis) | thematic-diversified | 45% | medi | 0.66 | 0.74 | 0% | 32% | 68% | 5.0 | 66/31/4% |
| AIQ (Global X AI) | thematic-diversified | 43% | medi | 0.62 | 0.73 | 0% | 18% | 42% | 9.0 | 63/33/4% |
| SOXX (iShares Semis) | thematic-diversified | 46% | medi | 0.60 | 0.65 | 0% | 27% | 59% | 6.0 | 48/47/5% |
| QTUM (Defiance Quantum) | thematic-diversified | 16% | LOW  | 0.59 | 0.65 | 9% | 8% | 44% | 7.6 | 46/48/6% |
| DRAM (Roundhill Memory) | narrow/concentrated | 73% | high | 0.38 | 0.67 | 0% | 73% | 100% | 3.0 | 34/58/8% |

*Class-only (no holdings map): ARKK = narrow/concentrated, DTCR = thematic-diversified, GRID = thematic-diversified, IGV = sector-diversified, NUKE = thematic-diversified, QQQ = broad index, SCHD = broad index, SOXL = leveraged, TECL = leveraged, TQQQ = leveraged, VGT = sector-diversified, VOO = broad index.*

## Growth-regime recovery ranking
High-growth names grow INTO the multiple (PEG-anchored), so recovery time is the PEG earn-back; they rank HIGH when likely to reclaim within 18m. Safe/diversified names recover via buyback + adjusted-PE, ranked by vs-S&P.

**High-growth (>40%) — by PEG earn-back:**

| Name | type | growth | crash-growth | PEG earn-back | P(rec≤18m) | rank |
|---|---|--:|:--:|--:|--:|:--:|
| NVIDIA | stock | 45% | secular | 0.0y | 45% | PEG-fast / MC-uncertain |
| Micron | stock | 50% | cyclical | 0.4y | 42% | cyclical high-growth / rebound-dependent |
| Astera Labs | stock | 70% | secular | 1.3y | 45% | PEG-fast / MC-uncertain |
| DRAM (Roundhill Memory) | ETF | 45% | cyclical | 1.5y | 40% | cyclical — needs TAM rebound |
| AMD | stock | 45% | cyclical | 1.6y | 29% | cyclical — needs TAM rebound |
| Palantir | stock | 55% | secular | 2.1y | 40% | watch |
| Lumentum | stock | 55% | cyclical | 3.3y | 37% | cyclical — needs TAM rebound |
| Applied Optoelectronics | stock | 55% | cyclical | 5.1y | 35% | cyclical — needs TAM rebound |
| ARKK (ARK Innovation) | ETF | 42% | broken | 7.9y | 28% | broken thesis — avoid unless evidence changes |
| CoreWeave | stock | 60% | cyclical | ∞ | 30% | cyclical — needs TAM rebound |
| IonQ | stock | 80% | broken | ∞ | 25% | broken thesis — avoid unless evidence changes |

## Drawdown × recovery probability matrix

*The model's central question, as probabilities — never exact timing. For each drawdown horizon: the chance of a >25% fall by then, and IF it falls, the chance it's back to its prior peak within 6 / 12 / 18 / 24 months (the rest is still underwater past 36m — slow, cyclical-wait, or impaired). Cyclical names are back-loaded by an explicit demand-trough: near-zero early recovery, catching up only after the demand cycle clears.*

**NVIDIA** — secular

| If >25% fall within | P(that fall) | recover ≤6m | ≤12m | ≤18m | ≤24m | ≤36m | still down >36m |
|---|--:|--:|--:|--:|--:|--:|--:|
| 6m | 13% | 20% | 35% | 48% | 55% | 64% | 36% |
| 12m | 34% | 18% | 35% | 45% | 51% | 61% | 39% |
| 18m | 53% | 17% | 34% | 45% | 51% | 61% | 39% |

**Microsoft** — secular

| If >25% fall within | P(that fall) | recover ≤6m | ≤12m | ≤18m | ≤24m | ≤36m | still down >36m |
|---|--:|--:|--:|--:|--:|--:|--:|
| 6m | 7% | 16% | 27% | 38% | 47% | 55% | 45% |
| 12m | 22% | 9% | 22% | 30% | 41% | 50% | 50% |
| 18m | 40% | 7% | 23% | 33% | 41% | 52% | 48% |

**Micron** — cyclical

| If >25% fall within | P(that fall) | recover ≤6m | ≤12m | ≤18m | ≤24m | ≤36m | still down >36m |
|---|--:|--:|--:|--:|--:|--:|--:|
| 6m | 17% | 0% | 0% | 44% | 56% | 63% | 37% |
| 12m | 41% | 0% | 0% | 44% | 49% | 56% | 44% |
| 18m | 61% | 0% | 0% | 42% | 47% | 56% | 44% |

**AMD** — cyclical

| If >25% fall within | P(that fall) | recover ≤6m | ≤12m | ≤18m | ≤24m | ≤36m | still down >36m |
|---|--:|--:|--:|--:|--:|--:|--:|
| 6m | 13% | 12% | 26% | 32% | 42% | 48% | 52% |
| 12m | 34% | 9% | 21% | 31% | 37% | 45% | 55% |
| 18m | 51% | 7% | 19% | 29% | 36% | 45% | 55% |

**IonQ** — broken

| If >25% fall within | P(that fall) | recover ≤6m | ≤12m | ≤18m | ≤24m | ≤36m | still down >36m |
|---|--:|--:|--:|--:|--:|--:|--:|
| 6m | 24% | 12% | 22% | 30% | 35% | 45% | 55% |
| 12m | 55% | 10% | 21% | 29% | 33% | 39% | 61% |
| 18m | 73% | 8% | 19% | 25% | 30% | 37% | 63% |

**SMH (VanEck Semis)** — secular

| If >25% fall within | P(that fall) | recover ≤6m | ≤12m | ≤18m | ≤24m | ≤36m | still down >36m |
|---|--:|--:|--:|--:|--:|--:|--:|
| 6m | 9% | 15% | 25% | 33% | 41% | 52% | 48% |
| 12m | 27% | 10% | 26% | 34% | 41% | 52% | 48% |
| 18m | 43% | 10% | 25% | 38% | 43% | 53% | 47% |

**DRAM (Roundhill Memory)** — cyclical

| If >25% fall within | P(that fall) | recover ≤6m | ≤12m | ≤18m | ≤24m | ≤36m | still down >36m |
|---|--:|--:|--:|--:|--:|--:|--:|
| 6m | 13% | 0% | 0% | 40% | 50% | 58% | 42% |
| 12m | 36% | 0% | 0% | 38% | 46% | 53% | 47% |
| 18m | 55% | 0% | 0% | 40% | 46% | 53% | 47% |

**QQQ (Nasdaq-100)** — secular

| If >25% fall within | P(that fall) | recover ≤6m | ≤12m | ≤18m | ≤24m | ≤36m | still down >36m |
|---|--:|--:|--:|--:|--:|--:|--:|
| 6m | 6% | 14% | 29% | 37% | 45% | 47% | 53% |
| 12m | 22% | 7% | 17% | 23% | 27% | 35% | 65% |
| 18m | 38% | 5% | 15% | 23% | 29% | 37% | 63% |

**VOO (S&P 500)** — secular

| If >25% fall within | P(that fall) | recover ≤6m | ≤12m | ≤18m | ≤24m | ≤36m | still down >36m |
|---|--:|--:|--:|--:|--:|--:|--:|
| 6m | 4% | 12% | 22% | 31% | 31% | 38% | 62% |
| 12m | 14% | 6% | 16% | 19% | 22% | 32% | 68% |
| 18m | 28% | 5% | 13% | 22% | 27% | 35% | 65% |

**ARKK (ARK Innovation)** — broken

| If >25% fall within | P(that fall) | recover ≤6m | ≤12m | ≤18m | ≤24m | ≤36m | still down >36m |
|---|--:|--:|--:|--:|--:|--:|--:|
| 6m | 25% | 8% | 21% | 31% | 39% | 49% | 51% |
| 12m | 53% | 10% | 23% | 32% | 38% | 45% | 55% |
| 18m | 73% | 9% | 20% | 28% | 34% | 41% | 59% |