# Systemic + TAM Risk — complete report

*Full universe (125 names: stocks + ETFs + leveraged) · model as of 2026-06-26 · generated 2026-06-26 · 21.9 S&P fwd P/E*

**Research model — not investment advice. Read tiers and ranges, not decimals.**

*Data sources: macro inputs from **FRED**; market prices and option quotes from **Polygon**; company fundamentals refreshed by an automated **Claude + Polygon** review. Company inputs (growth, TAM/SAM, moat-permanence, quality scores) are the maintainer's **documented judgments swept by the model — not third-party consensus estimates**. Single-maintainer research model; company inputs last reviewed 2026-06-26.*

## Plain-English glossary
New to investing? Read this first — every column in the tables, one line each.
- **Tier** — growth bucket: High (>40%), Moderate (15–40%), Safe (<15%) expected revenue growth over 18 months.
- **Growth** — how fast the model expects the company's revenue to grow over the next 18 months.
- **Drawdown / >25% fall** — a drop of 25% or more from a recent high.
- **>3y tail** — the chance a >25% fall is *still* not recovered ~3.5 years later — the model's measure of *permanent* loss risk. Lower is safer.
- **Recover 2y** — if it falls, the chance it's back to its old high within 2 years. Higher is better.
- **vs S&P / vs SCHD** — reward-for-risk versus owning the S&P 500 (or the SCHD dividend fund). 1.00 = same as that benchmark; above 1 = more growth per unit of permanent-loss risk.
- **×S&P** — this name's tail risk as a multiple of the S&P's (2× = twice as risky on the tail).
- **Recovery tag** — *secular* = durable grower; *cyclical* = depends on its demand cycle turning back up; *broken* = thesis impaired, avoid; *PEG-fast* = can grow back into its price quickly.
- **PEG earn-back** — how many years of growth it would take to justify today's price; lower = recovers its valuation faster.
- **Effective N (eff N)** — how many *truly independent* bets a basket really is. Five names that move together can be ~1 bet.
- **Monte Carlo** — the model runs tens of thousands of simulated futures and reports how often each outcome happened. These are *probabilities, not predictions*.
- **League / hysteresis** — a fixed Top-125 board; a new name only joins when it clearly beats a current member, so the list doesn't churn on random noise.

## Macro & systemic stress
Index **48/100** (moderate (watch-zone)) — structural fragility 58, acute trigger 25; scales the crisis odds ×0.99. Inputs: CAPE 39.4, real 10y 2.25%, VIX 24.0, Brent $96.0, HY spread 312bps, margin-debt YoY 45%.

## Concentration
~1 effective independent bets across 122 names (avg correlation 0.91) — essentially one AI-capex bet; specialized ETFs are ~0.95 correlated with their lead holding.

## How the ranking works
Two axes, two sort keys — so different views order names differently on the same data:
- **Growth** (expected 18-month revenue growth) sets the **tier** (>40% / 15–40% / <15%). The tiered tables below and the dashboard's recovery bars are **sorted by growth** within each tier.
- **Risk is simulated**, not assigned: a regime-switching Monte Carlo where **beta sets how deep a name falls** and **TAM-penetration sets whether it recovers**. Headline = the **>3y tail** (P of a >25% fall still underwater at ~3.5y); macro-stress scales the crisis odds.
- **vs S&P / vs SCHD** combine both: (growth ÷ benchmark growth) × (benchmark tail ÷ name tail), benchmark = 1.00. **Sorting by this gives a different order than sorting by growth** — it can rank a lower-tail name above a faster grower. (This is why a growth-sorted plot and the vs-S&P ranking look different.)
- Not an expected-return forecast or a buy list. Growth and the judgment scores are opinions the model sweeps.

### The ranked league (Top-125 board · Top-50 view)
The headline ranking is **reward-vs-S&P**, and it drives a fixed-size **league**: the whole priced market competes for a slot, and the board keeps the **Top 125** (the dashboard highlights the **Top 50**). **Everything competes** (stocks + ETFs); the **S&P (VOO) and SCHD benchmarks are pinned** for comparison and **leveraged 3× vehicles are excluded** by design.
- A name only **enters** the league when it genuinely **out-ranks an incumbent** by more than a 5% margin (**hysteresis**) — so Monte-Carlo noise near the cut-off does **not** churn the standings or the graphs. If nothing breaks in, the published table is unchanged; when something does, it displaces the weakest member and the standings (and graphs) update.
- This run's league: **122 members**; entered: —; exited: —.
- On the dashboard, clicking a column header **re-orders the display** of the Top-50 by that field (ascending/descending) — it does **not** change who is in the league.

## Master ranking — by reward-to-risk (vs S&P, high to low)

*The **Recovery** column is the crash-growth-aware verdict: vs-S&P sorts by reward-to-risk and can float a broken or cyclical name up the list, so read it alongside Recovery — a '⚠ broken — avoid' or 'cyclical — rebound-dependent' tag overrides a flattering vs-S&P number.*

| # | Name | Type | Tier | Recovery | Growth | >3y tail | vs S&P | vs SCHD |
|--:|---|---|---|---|--:|--:|--:|--:|
| 1 | NVIDIA | stock | High | PEG-fast / MC-uncertain | 45% | 10% | 7.77 | 8.47 |
| 2 | Astera Labs | stock | High | PEG-fast / MC-uncertain | 55% | 15% | 6.25 | 6.81 |
| 3 | AMD | stock | Moderate | cyclical — rebound-dep | 40% | 11% | 6.2 | 6.75 |
| 4 | Palantir | stock | High | PEG-fast / MC-uncertain | 45% | 13% | 6.18 | 6.73 |
| 5 | Marvell | stock | Moderate | cyclical — rebound-dep | 35% | 12% | 5.06 | 5.51 |
| 6 | Broadcom | stock | Moderate | diversified / safe | 38% | 13% | 4.99 | 5.44 |
| 7 | DRAM (Roundhill Memory) | ETF | High | cyclical — rebound-dep | 45% | 21% | 3.85 | 4.19 |
| 8 | Credo Technology | stock | High | PEG-fast / MC-uncertain | 55% | 27% | 3.62 | 3.94 |
| 9 | CHAT (Roundhill GenAI) | ETF | Moderate | diversified / safe | 32% | 16% | 3.45 | 3.76 |
| 10 | Micron | stock | High | cyclical — rebound-dep | 45% | 23% | 3.38 | 3.68 |
| 11 | SMH (VanEck Semis) | ETF | Moderate | diversified / safe | 30% | 17% | 3.19 | 3.48 |
| 12 | SOXX (iShares Semis) | ETF | Moderate | diversified / safe | 28% | 17% | 2.97 | 3.24 |
| 13 | CoreWeave | stock | High | cyclical — rebound-dep | 60% | 37% | 2.84 | 3.1 |
| 14 | AIQ (Global X AI) | ETF | Moderate | diversified / safe | 25% | 16% | 2.69 | 2.93 |
| 15 | SoundHound AI | stock | High | watch | 45% | 30% | 2.6 | 2.83 |
| 16 | IonQ | stock | High | ⚠ broken — avoid | 60% | 41% | 2.58 | 2.81 |
| 17 | ARM | stock | Moderate | diversified / safe | 25% | 17% | 2.52 | 2.74 |
| 18 | Taiwan Semiconductor | stock | Moderate | diversified / safe | 30% | 21% | 2.52 | 2.74 |
| 19 | Lumentum | stock | Moderate | cyclical — rebound-dep | 40% | 28% | 2.51 | 2.73 |
| 20 | Applied Optoelectronics | stock | High | cyclical — rebound-dep | 45% | 33% | 2.39 | 2.6 |
| 21 | ARKK (ARK Innovation) | ETF | High | ⚠ broken — avoid | 42% | 35% | 2.13 | 2.32 |
| 22 | Super Micro Computer | stock | Moderate | diversified / safe | 25% | 21% | 2.11 | 2.3 |
| 23 | AppLovin | stock | Moderate | cyclical — rebound-dep | 30% | 26% | 2.04 | 2.22 |
| 24 | Meta | stock | Moderate | diversified / safe | 18% | 16% | 1.99 | 2.17 |
| 25 | Vertiv | stock | Moderate | cyclical — rebound-dep | 28% | 25% | 1.97 | 2.15 |
| 26 | Dell Technologies | stock | Moderate | diversified / safe | 18% | 17% | 1.85 | 2.02 |
| 27 | QTUM (Defiance Quantum) | ETF | Moderate | ⚠ broken — avoid | 22% | 21% | 1.84 | 2.01 |
| 28 | Camtek | stock | Moderate | diversified / safe | 25% | 25% | 1.79 | 1.95 |
| 29 | Samsara | stock | Moderate | diversified / safe | 30% | 30% | 1.79 | 1.95 |
| 30 | NUKE (Nuclear/Uranium) | ETF | Moderate | diversified / safe | 22% | 22% | 1.73 | 1.89 |
| 31 | NuScale Power | stock | Moderate | diversified / safe | 30% | 31% | 1.72 | 1.87 |
| 32 | Tempus AI | stock | Moderate | diversified / safe | 30% | 31% | 1.7 | 1.85 |
| 33 | GRID (Smart Grid) | ETF | Moderate | diversified / safe | 18% | 19% | 1.66 | 1.8 |
| 34 | Talen Energy | stock | Moderate | diversified / safe | 22% | 24% | 1.62 | 1.77 |
| 35 | Oracle | stock | Moderate | diversified / safe | 18% | 20% | 1.61 | 1.76 |
| 36 | IGV (Software) | ETF | Moderate | diversified / safe | 20% | 22% | 1.58 | 1.72 |
| 37 | Snowflake | stock | Moderate | diversified / safe | 26% | 30% | 1.54 | 1.68 |
| 38 | Coherent | stock | Moderate | cyclical — rebound-dep | 25% | 29% | 1.54 | 1.68 |
| 39 | Microsoft | stock | Safe | diversified / safe | 14% | 16% | 1.5 | 1.63 |
| 40 | QQQ (Nasdaq-100) | ETF | Moderate | diversified / safe | 16% | 19% | 1.46 | 1.59 |
| 41 | Arista Networks | stock | Moderate | diversified / safe | 20% | 24% | 1.44 | 1.57 |
| 42 | ServiceNow | stock | Moderate | diversified / safe | 20% | 25% | 1.39 | 1.52 |
| 43 | ServiceTitan | stock | Moderate | diversified / safe | 24% | 30% | 1.38 | 1.51 |
| 44 | CrowdStrike | stock | Moderate | diversified / safe | 22% | 28% | 1.37 | 1.49 |
| 45 | GitLab | stock | Moderate | diversified / safe | 22% | 28% | 1.36 | 1.49 |
| 46 | VGT (Info Tech) | ETF | Moderate | diversified / safe | 15% | 19% | 1.36 | 1.48 |
| 47 | Datadog | stock | Moderate | diversified / safe | 22% | 29% | 1.35 | 1.47 |
| 48 | SiTime | stock | Moderate | diversified / safe | 22% | 29% | 1.32 | 1.44 |
| 49 | DTCR (Data Ctr Infra) | ETF | Safe | diversified / safe | 14% | 19% | 1.31 | 1.42 |
| 50 | C3.ai | stock | Moderate | diversified / safe | 22% | 30% | 1.27 | 1.38 |
| 51 | Qualcomm | stock | Safe | cyclical — rebound-dep | 8% | 11% | 1.24 | 1.35 |
| 52 | Confluent | stock | Moderate | diversified / safe | 20% | 29% | 1.23 | 1.34 |
| 53 | Teradyne | stock | Moderate | diversified / safe | 17% | 25% | 1.21 | 1.31 |
| 54 | Monolithic Power Systems | stock | Moderate | diversified / safe | 18% | 27% | 1.18 | 1.29 |
| 55 | Alphabet | stock | Safe | diversified / safe | 12% | 19% | 1.1 | 1.2 |
| 56 | Amazon | stock | Safe | diversified / safe | 13% | 22% | 1.06 | 1.16 |
| 57 | ASML Holding | stock | Moderate | diversified / safe | 15% | 25% | 1.06 | 1.15 |
| 58 | Seagate Technology | stock | Safe | diversified / safe | 12% | 20% | 1.06 | 1.15 |
| 59 | Texas Instruments | stock | Safe | cyclical — rebound-dep | 14% | 23% | 1.05 | 1.15 |
| 60 | HubSpot | stock | Moderate | diversified / safe | 16% | 27% | 1.04 | 1.14 |
| 61 | nVent Electric | stock | Safe | diversified / safe | 12% | 20% | 1.04 | 1.13 |
| 62 | Hewlett Packard Enterprise | stock | Safe | diversified / safe | 11% | 19% | 1.03 | 1.13 |
| 63 | Western Digital | stock | Safe | diversified / safe | 12% | 20% | 1.03 | 1.12 |
| 64 | VOO (S&P 500) | ETF | Safe | diversified / safe | 9% | 16% | 1.0 | 1.09 |
| 65 | Pure Storage | stock | Safe | diversified / safe | 14% | 25% | 0.98 | 1.07 |
| 66 | Fabrinet | stock | Safe | diversified / safe | 12% | 22% | 0.97 | 1.06 |
| 67 | Vistra | stock | Safe | diversified / safe | 12% | 22% | 0.96 | 1.05 |
| 68 | Lam Research | stock | Safe | diversified / safe | 12% | 22% | 0.96 | 1.04 |
| 69 | Elastic | stock | Safe | diversified / safe | 14% | 26% | 0.95 | 1.04 |
| 70 | KLA Corporation | stock | Safe | diversified / safe | 12% | 23% | 0.94 | 1.02 |
| 71 | Ciena | stock | Safe | diversified / safe | 12% | 23% | 0.92 | 1.01 |
| 72 | SCHD (Dividend) | ETF | Safe | diversified / safe | 6% | 12% | 0.92 | 1.0 |
| 73 | Constellation Energy | stock | Safe | diversified / safe | 12% | 23% | 0.91 | 0.99 |
| 74 | Rambus | stock | Safe | diversified / safe | 12% | 23% | 0.9 | 0.98 |
| 75 | Onto Innovation | stock | Safe | diversified / safe | 12% | 24% | 0.87 | 0.94 |
| 76 | Semtech | stock | Safe | diversified / safe | 12% | 25% | 0.85 | 0.92 |
| 77 | Cadence Design Systems | stock | Safe | diversified / safe | 12% | 25% | 0.84 | 0.91 |
| 78 | Ichor Holdings | stock | Safe | diversified / safe | 12% | 25% | 0.83 | 0.9 |
| 79 | Analog Devices | stock | Safe | diversified / safe | 10% | 21% | 0.83 | 0.9 |
| 80 | Tesla | stock | Moderate | cyclical — rebound-dep | 15% | 33% | 0.81 | 0.88 |
| 81 | MongoDB | stock | Safe | diversified / safe | 14% | 31% | 0.81 | 0.88 |
| 82 | Impinj | stock | Safe | diversified / safe | 12% | 26% | 0.8 | 0.88 |
| 83 | MACOM Technology | stock | Safe | diversified / safe | 12% | 27% | 0.79 | 0.86 |
| 84 | Synopsys | stock | Safe | diversified / safe | 11% | 25% | 0.79 | 0.86 |
| 85 | Lattice Semiconductor | stock | Safe | diversified / safe | 12% | 27% | 0.78 | 0.85 |
| 86 | Iron Mountain | stock | Safe | diversified / safe | 10% | 24% | 0.74 | 0.8 |
| 87 | Advanced Energy Industries | stock | Safe | diversified / safe | 10% | 24% | 0.72 | 0.79 |
| 88 | Quanta Services | stock | Safe | diversified / safe | 10% | 25% | 0.72 | 0.78 |
| 89 | Cisco | stock | Safe | diversified / safe | 6% | 15% | 0.71 | 0.78 |
| 90 | Indie Semiconductor | stock | Safe | diversified / safe | 12% | 31% | 0.68 | 0.74 |
| 91 | Allegro MicroSystems | stock | Safe | diversified / safe | 10% | 27% | 0.66 | 0.71 |
| 92 | FormFactor | stock | Safe | diversified / safe | 9% | 25% | 0.64 | 0.7 |
| 93 | Eaton | stock | Safe | diversified / safe | 8% | 23% | 0.62 | 0.68 |
| 94 | Entegris | stock | Safe | diversified / safe | 8% | 23% | 0.61 | 0.67 |
| 95 | Salesforce | stock | Safe | diversified / safe | 7% | 21% | 0.6 | 0.65 |
| 96 | MKS Instruments | stock | Safe | diversified / safe | 7% | 21% | 0.6 | 0.65 |
| 97 | Navitas Semiconductor | stock | Safe | diversified / safe | 10% | 30% | 0.58 | 0.64 |
| 98 | Power Integrations | stock | Safe | diversified / safe | 8% | 25% | 0.57 | 0.62 |
| 99 | Apple | stock | Safe | diversified / safe | 7% | 23% | 0.54 | 0.59 |
| 100 | United Microelectronics | stock | Safe | diversified / safe | 6% | 20% | 0.53 | 0.58 |
| 101 | NXP Semiconductors | stock | Safe | diversified / safe | 6% | 20% | 0.53 | 0.58 |
| 102 | Equinix | stock | Safe | diversified / safe | 8% | 27% | 0.53 | 0.58 |
| 103 | IBM | stock | Safe | diversified / safe | 5% | 17% | 0.52 | 0.57 |
| 104 | GE Vernova | stock | Safe | diversified / safe | 8% | 27% | 0.52 | 0.57 |
| 105 | Kioxia | stock | Safe | cyclical — rebound-dep | 5% | 17% | 0.51 | 0.56 |
| 106 | Ultra Clean Holdings | stock | Safe | diversified / safe | 6% | 21% | 0.5 | 0.54 |
| 107 | Applied Materials | stock | Safe | diversified / safe | 6% | 21% | 0.49 | 0.54 |
| 108 | BigBear.ai | stock | Safe | diversified / safe | 8% | 31% | 0.46 | 0.5 |
| 109 | Adobe | stock | Safe | diversified / safe | 5% | 19% | 0.46 | 0.5 |
| 110 | Microchip Technology | stock | Safe | diversified / safe | 6% | 24% | 0.43 | 0.47 |
| 111 | Juniper Networks | stock | Safe | diversified / safe | 4% | 18% | 0.4 | 0.44 |
| 112 | GlobalFoundries | stock | Safe | diversified / safe | 5% | 22% | 0.39 | 0.43 |
| 113 | Digital Realty Trust | stock | Safe | diversified / safe | 6% | 27% | 0.39 | 0.43 |
| 114 | Pegasystems | stock | Safe | diversified / safe | 5% | 23% | 0.39 | 0.42 |
| 115 | ON Semiconductor | stock | Safe | diversified / safe | 4% | 21% | 0.33 | 0.36 |
| 116 | Wolfspeed | stock | Safe | diversified / safe | 5% | 29% | 0.3 | 0.33 |
| 117 | Recursion Pharmaceuticals | stock | Safe | diversified / safe | 5% | 31% | 0.28 | 0.31 |
| 118 | Photronics | stock | Safe | diversified / safe | 3% | 20% | 0.27 | 0.29 |
| 119 | Skyworks Solutions | stock | Safe | diversified / safe | 2% | 19% | 0.18 | 0.2 |
| 120 | Qorvo | stock | Safe | diversified / safe | 2% | 21% | 0.17 | 0.18 |
| 121 | Oklo | stock | Safe | diversified / safe | 0% | 31% | — | — |
| 122 | Aehr Test Systems | stock | Safe | diversified / safe | -15% | 27% | -0.99 | -1.08 |

### Trading vehicles — excluded from the ranking (path-dependent decay)

| Name | P(>25% fall) | >3y tail | note |
|---|--:|--:|---|
| SOXL (3x Semis) | 100% | 30% | 3x daily reset; volatility decay; not a growth holding |
| TECL (3x Tech) | 97% | 30% | 3x daily reset; volatility decay; not a growth holding |
| TQQQ (3x NDX) | 97% | 30% | 3x daily reset; volatility decay; not a growth holding |

*(The tiered tables below are the same names sorted by growth within tier — a different sort, same data.)*

## TIER 1  ·  HIGH growth (>40% expected, 18m)

| Name | Type | Recovery | Growth | P(>25% fall) | recover 2y | >3y tail | ×S&P | vs S&P | vs SCHD |
|---|---|---|--:|--:|--:|--:|--:|--:|--:|
| IonQ | stock | ⚠ broken — avoid | 60% | 75% | 29% | 41% | 2.58× | 2.58 | 2.81 |
| CoreWeave | stock | cyclical — rebound-dep | 60% | 82% | 37% | 37% | 2.35× | 2.84 | 3.1 |
| Astera Labs | stock | PEG-fast / MC-uncertain | 55% | 70% | 61% | 15% | 0.98× | 6.25 | 6.81 |
| Credo Technology | stock | PEG-fast / MC-uncertain | 55% | 74% | 46% | 27% | 1.69× | 3.62 | 3.94 |
| Palantir | stock | PEG-fast / MC-uncertain | 45% | 54% | 56% | 13% | 0.81× | 6.18 | 6.73 |
| Applied Optoelectronics | stock | cyclical — rebound-dep | 45% | 74% | 39% | 33% | 2.09× | 2.39 | 2.6 |
| Micron | stock | cyclical — rebound-dep | 45% | 64% | 44% | 23% | 1.48× | 3.38 | 3.68 |
| NVIDIA | stock | PEG-fast / MC-uncertain | 45% | 49% | 60% | 10% | 0.64× | 7.77 | 8.47 |
| DRAM (Roundhill Memory) | ETF | cyclical — rebound-dep | 45% | 58% | 44% | 21% | 1.3× | 3.85 | 4.19 |
| SoundHound AI | stock | watch | 45% | 84% | 47% | 30% | 1.92× | 2.6 | 2.83 |
| ARKK (ARK Innovation) | ETF | ⚠ broken — avoid | 42% | 74% | 33% | 35% | 2.19× | 2.13 | 2.32 |

## TIER 2  ·  MODERATE growth (15-40%)

| Name | Type | Recovery | Growth | P(>25% fall) | recover 2y | >3y tail | ×S&P | vs S&P | vs SCHD |
|---|---|---|--:|--:|--:|--:|--:|--:|--:|
| Lumentum | stock | cyclical — rebound-dep | 40% | 67% | 41% | 28% | 1.77× | 2.51 | 2.73 |
| AMD | stock | cyclical — rebound-dep | 40% | 47% | 50% | 11% | 0.72× | 6.2 | 6.75 |
| Broadcom | stock | diversified / safe | 38% | 46% | 51% | 13% | 0.85× | 4.99 | 5.44 |
| Marvell | stock | cyclical — rebound-dep | 35% | 52% | 57% | 12% | 0.77× | 5.06 | 5.51 |
| CHAT (Roundhill GenAI) | ETF | diversified / safe | 32% | 45% | 42% | 16% | 1.03× | 3.45 | 3.76 |
| AppLovin | stock | cyclical — rebound-dep | 30% | 83% | 48% | 26% | 1.64× | 2.04 | 2.22 |
| SMH (VanEck Semis) | ETF | diversified / safe | 30% | 47% | 44% | 17% | 1.05× | 3.19 | 3.48 |
| Taiwan Semiconductor | stock | diversified / safe | 30% | 50% | 38% | 21% | 1.32× | 2.52 | 2.74 |
| Samsara | stock | diversified / safe | 30% | 69% | 40% | 30% | 1.87× | 1.79 | 1.95 |
| Tempus AI | stock | diversified / safe | 30% | 75% | 42% | 31% | 1.96× | 1.7 | 1.85 |
| NuScale Power | stock | diversified / safe | 30% | 84% | 46% | 31% | 1.94× | 1.72 | 1.87 |
| Vertiv | stock | cyclical — rebound-dep | 28% | 60% | 35% | 25% | 1.58× | 1.97 | 2.15 |
| SOXX (iShares Semis) | ETF | diversified / safe | 28% | 45% | 42% | 17% | 1.05× | 2.97 | 3.24 |
| Snowflake | stock | diversified / safe | 26% | 64% | 36% | 30% | 1.87× | 1.54 | 1.68 |
| Coherent | stock | cyclical — rebound-dep | 25% | 69% | 41% | 29% | 1.8× | 1.54 | 1.68 |
| ARM | stock | diversified / safe | 25% | 49% | 45% | 17% | 1.1× | 2.52 | 2.74 |
| AIQ (Global X AI) | ETF | diversified / safe | 25% | 44% | 41% | 16% | 1.03× | 2.69 | 2.93 |
| Camtek | stock | diversified / safe | 25% | 64% | 43% | 25% | 1.55× | 1.79 | 1.95 |
| Super Micro Computer | stock | diversified / safe | 25% | 76% | 56% | 21% | 1.32× | 2.11 | 2.3 |
| ServiceTitan | stock | diversified / safe | 24% | 67% | 37% | 30% | 1.93× | 1.38 | 1.51 |
| QTUM (Defiance Quantum) | ETF | ⚠ broken — avoid | 22% | 49% | 29% | 21% | 1.33× | 1.84 | 2.01 |
| NUKE (Nuclear/Uranium) | ETF | diversified / safe | 22% | 53% | 38% | 22% | 1.41× | 1.73 | 1.89 |
| SiTime | stock | diversified / safe | 22% | 70% | 40% | 29% | 1.85× | 1.32 | 1.44 |
| CrowdStrike | stock | diversified / safe | 22% | 55% | 31% | 28% | 1.79× | 1.37 | 1.49 |
| Datadog | stock | diversified / safe | 22% | 61% | 35% | 29% | 1.82× | 1.35 | 1.47 |
| GitLab | stock | diversified / safe | 22% | 66% | 39% | 28% | 1.79× | 1.36 | 1.49 |
| C3.ai | stock | diversified / safe | 22% | 80% | 45% | 30% | 1.93× | 1.27 | 1.38 |
| Talen Energy | stock | diversified / safe | 22% | 55% | 38% | 24% | 1.5× | 1.62 | 1.77 |
| IGV (Software) | ETF | diversified / safe | 20% | 46% | 32% | 22% | 1.41× | 1.58 | 1.72 |
| ServiceNow | stock | diversified / safe | 20% | 53% | 34% | 25% | 1.6× | 1.39 | 1.52 |
| Confluent | stock | diversified / safe | 20% | 63% | 37% | 29% | 1.8× | 1.23 | 1.34 |
| Arista Networks | stock | diversified / safe | 20% | 56% | 37% | 24% | 1.54× | 1.44 | 1.57 |
| Meta | stock | diversified / safe | 18% | 45% | 44% | 16% | 1.0× | 1.99 | 2.17 |
| Oracle | stock | diversified / safe | 18% | 41% | 32% | 20% | 1.24× | 1.61 | 1.76 |
| GRID (Smart Grid) | ETF | diversified / safe | 18% | 38% | 28% | 19% | 1.21× | 1.66 | 1.8 |
| Monolithic Power Systems | stock | diversified / safe | 18% | 62% | 39% | 27% | 1.69× | 1.18 | 1.29 |
| Dell Technologies | stock | diversified / safe | 18% | 47% | 42% | 17% | 1.08× | 1.85 | 2.02 |
| Teradyne | stock | diversified / safe | 17% | 58% | 38% | 25% | 1.57× | 1.21 | 1.31 |
| QQQ (Nasdaq-100) | ETF | diversified / safe | 16% | 38% | 28% | 19% | 1.22× | 1.46 | 1.59 |
| HubSpot | stock | diversified / safe | 16% | 61% | 37% | 27% | 1.7× | 1.04 | 1.14 |

## TIER 3  ·  SAFE / smaller growth (<15%)

| Name | Type | Recovery | Growth | P(>25% fall) | recover 2y | >3y tail | ×S&P | vs S&P | vs SCHD |
|---|---|---|--:|--:|--:|--:|--:|--:|--:|
| Tesla | stock | cyclical — rebound-dep | 15% | 82% | 40% | 33% | 2.06× | 0.81 | 0.88 |
| VGT (Info Tech) | ETF | diversified / safe | 15% | 39% | 29% | 19% | 1.23× | 1.36 | 1.48 |
| ASML Holding | stock | diversified / safe | 15% | 56% | 36% | 25% | 1.57× | 1.06 | 1.15 |
| Microsoft | stock | diversified / safe | 14% | 41% | 39% | 16% | 1.04× | 1.5 | 1.63 |
| Texas Instruments | stock | cyclical — rebound-dep | 14% | 47% | 30% | 23% | 1.48× | 1.05 | 1.15 |
| DTCR (Data Ctr Infra) | ETF | diversified / safe | 14% | 32% | 22% | 19% | 1.19× | 1.31 | 1.42 |
| MongoDB | stock | diversified / safe | 14% | 63% | 33% | 31% | 1.93× | 0.81 | 0.88 |
| Elastic | stock | diversified / safe | 14% | 60% | 38% | 26% | 1.64× | 0.95 | 1.04 |
| Pure Storage | stock | diversified / safe | 14% | 58% | 38% | 25% | 1.59× | 0.98 | 1.07 |
| Amazon | stock | diversified / safe | 13% | 58% | 44% | 22% | 1.36× | 1.06 | 1.16 |
| Alphabet | stock | diversified / safe | 12% | 42% | 33% | 19% | 1.21× | 1.1 | 1.2 |
| Lam Research | stock | diversified / safe | 12% | 56% | 40% | 22% | 1.39× | 0.96 | 1.04 |
| KLA Corporation | stock | diversified / safe | 12% | 55% | 39% | 23% | 1.42× | 0.94 | 1.02 |
| Cadence Design Systems | stock | diversified / safe | 12% | 51% | 32% | 25% | 1.6× | 0.84 | 0.91 |
| Lattice Semiconductor | stock | diversified / safe | 12% | 66% | 40% | 27% | 1.72× | 0.78 | 0.85 |
| MACOM Technology | stock | diversified / safe | 12% | 62% | 38% | 27% | 1.7× | 0.79 | 0.86 |
| Onto Innovation | stock | diversified / safe | 12% | 64% | 43% | 24% | 1.54× | 0.87 | 0.94 |
| Ichor Holdings | stock | diversified / safe | 12% | 70% | 45% | 25% | 1.61× | 0.83 | 0.9 |
| Impinj | stock | diversified / safe | 12% | 68% | 43% | 26% | 1.66× | 0.8 | 0.88 |
| Semtech | stock | diversified / safe | 12% | 71% | 47% | 25% | 1.57× | 0.85 | 0.92 |
| Rambus | stock | diversified / safe | 12% | 60% | 42% | 23% | 1.48× | 0.9 | 0.98 |
| Indie Semiconductor | stock | diversified / safe | 12% | 80% | 44% | 31% | 1.95× | 0.68 | 0.74 |
| Ciena | stock | diversified / safe | 12% | 58% | 41% | 23% | 1.44× | 0.92 | 1.01 |
| Fabrinet | stock | diversified / safe | 12% | 56% | 41% | 22% | 1.37× | 0.97 | 1.06 |
| Western Digital | stock | diversified / safe | 12% | 61% | 48% | 20% | 1.29× | 1.03 | 1.12 |
| Seagate Technology | stock | diversified / safe | 12% | 58% | 46% | 20% | 1.26× | 1.06 | 1.15 |
| Constellation Energy | stock | diversified / safe | 12% | 45% | 29% | 23% | 1.46× | 0.91 | 0.99 |
| Vistra | stock | diversified / safe | 12% | 52% | 38% | 22% | 1.38× | 0.96 | 1.05 |
| nVent Electric | stock | diversified / safe | 12% | 50% | 38% | 20% | 1.28× | 1.04 | 1.13 |
| Synopsys | stock | diversified / safe | 11% | 53% | 35% | 25% | 1.55× | 0.79 | 0.86 |
| Hewlett Packard Enterprise | stock | diversified / safe | 11% | 50% | 42% | 19% | 1.18× | 1.03 | 1.13 |
| Analog Devices | stock | diversified / safe | 10% | 47% | 34% | 21% | 1.34× | 0.83 | 0.9 |
| Allegro MicroSystems | stock | diversified / safe | 10% | 65% | 40% | 27% | 1.69× | 0.66 | 0.71 |
| Advanced Energy Industries | stock | diversified / safe | 10% | 57% | 38% | 24% | 1.54× | 0.72 | 0.79 |
| Navitas Semiconductor | stock | diversified / safe | 10% | 84% | 47% | 30% | 1.9× | 0.58 | 0.64 |
| Iron Mountain | stock | diversified / safe | 10% | 44% | 26% | 24% | 1.51× | 0.74 | 0.8 |
| Quanta Services | stock | diversified / safe | 10% | 51% | 32% | 25% | 1.55× | 0.72 | 0.78 |
| VOO (S&P 500) | ETF | diversified / safe | 9% | 29% | 24% | 16% | 1.0× | 1.0 | 1.09 |
| FormFactor | stock | diversified / safe | 9% | 61% | 40% | 25% | 1.56× | 0.64 | 0.7 |
| Qualcomm | stock | cyclical — rebound-dep | 8% | 43% | 51% | 11% | 0.72× | 1.24 | 1.35 |
| Entegris | stock | diversified / safe | 8% | 58% | 41% | 23% | 1.45× | 0.61 | 0.67 |
| Power Integrations | stock | diversified / safe | 8% | 51% | 32% | 25% | 1.57× | 0.57 | 0.62 |
| BigBear.ai | stock | diversified / safe | 8% | 86% | 48% | 31% | 1.93× | 0.46 | 0.5 |
| Equinix | stock | diversified / safe | 8% | 41% | 19% | 27% | 1.68× | 0.53 | 0.58 |
| GE Vernova | stock | diversified / safe | 8% | 57% | 34% | 27% | 1.7× | 0.52 | 0.57 |
| Eaton | stock | diversified / safe | 8% | 49% | 35% | 23% | 1.42× | 0.62 | 0.68 |
| Apple | stock | diversified / safe | 7% | 46% | 32% | 23% | 1.44× | 0.54 | 0.59 |
| MKS Instruments | stock | diversified / safe | 7% | 58% | 45% | 21% | 1.3× | 0.6 | 0.65 |
| Salesforce | stock | diversified / safe | 7% | 49% | 39% | 21% | 1.3× | 0.6 | 0.65 |
| Cisco | stock | diversified / safe | 6% | 33% | 33% | 15% | 0.93× | 0.71 | 0.78 |
| SCHD (Dividend) | ETF | diversified / safe | 6% | 20% | 21% | 12% | 0.73× | 0.92 | 1.0 |
| Applied Materials | stock | diversified / safe | 6% | 55% | 42% | 21% | 1.35× | 0.49 | 0.54 |
| NXP Semiconductors | stock | diversified / safe | 6% | 52% | 41% | 20% | 1.25× | 0.53 | 0.58 |
| Microchip Technology | stock | diversified / safe | 6% | 57% | 38% | 24% | 1.54× | 0.43 | 0.47 |
| United Microelectronics | stock | diversified / safe | 6% | 52% | 42% | 20% | 1.25× | 0.53 | 0.58 |
| Ultra Clean Holdings | stock | diversified / safe | 6% | 68% | 50% | 21% | 1.34× | 0.5 | 0.54 |
| Digital Realty Trust | stock | diversified / safe | 6% | 42% | 18% | 27% | 1.71× | 0.39 | 0.43 |
| IBM | stock | diversified / safe | 5% | 28% | 20% | 17% | 1.06× | 0.52 | 0.57 |
| Kioxia | stock | cyclical — rebound-dep | 5% | 57% | 50% | 17% | 1.08× | 0.51 | 0.56 |
| GlobalFoundries | stock | diversified / safe | 5% | 56% | 40% | 22% | 1.42× | 0.39 | 0.43 |
| Wolfspeed | stock | diversified / safe | 5% | 83% | 48% | 29% | 1.86× | 0.3 | 0.33 |
| Adobe | stock | diversified / safe | 5% | 48% | 41% | 19% | 1.22× | 0.46 | 0.5 |
| Pegasystems | stock | diversified / safe | 5% | 54% | 39% | 23% | 1.43× | 0.39 | 0.42 |
| Recursion Pharmaceuticals | stock | diversified / safe | 5% | 82% | 46% | 31% | 1.95× | 0.28 | 0.31 |
| ON Semiconductor | stock | diversified / safe | 4% | 59% | 44% | 21% | 1.34× | 0.33 | 0.36 |
| Juniper Networks | stock | diversified / safe | 4% | 40% | 34% | 18% | 1.11× | 0.4 | 0.44 |
| Photronics | stock | diversified / safe | 3% | 50% | 41% | 20% | 1.23× | 0.27 | 0.29 |
| Skyworks Solutions | stock | diversified / safe | 2% | 50% | 41% | 19% | 1.22× | 0.18 | 0.2 |
| Qorvo | stock | diversified / safe | 2% | 58% | 44% | 21% | 1.32× | 0.17 | 0.18 |
| Oklo | stock | diversified / safe | 0% | 86% | 47% | 31% | 1.95× | — | — |
| Aehr Test Systems | stock | diversified / safe | -15% | 78% | 48% | 27% | 1.69× | -0.99 | -1.08 |

## Trading vehicles — 3x leveraged (volatility decay; excluded from tiers & rankings)

| Name | Type | Recovery | Growth | P(>25% fall) | recover 2y | >3y tail | ×S&P | vs S&P | vs SCHD |
|---|---|---|--:|--:|--:|--:|--:|--:|--:|
| SOXL (3x Semis) | ETF | — | 60% | 100% | 58% | 30% | 1.87× | 3.56 | 3.88 |
| TECL (3x Tech) | ETF | — | 50% | 97% | 57% | 30% | 1.89× | 2.94 | 3.21 |
| TQQQ (3x NDX) | ETF | — | 45% | 97% | 57% | 30% | 1.89× | 2.65 | 2.89 |

## How to read it
- **Growth** sets the tier (>40% / 15–40% / <15%, expected 18m).
- **>3y tail** = chance a >25% fall is still underwater at ~3.5y.
- **×S&P** = that tail as a multiple of the S&P's.
- **vs S&P / vs SCHD** = (growth ÷ benchmark growth) × (benchmark tail ÷ name tail); benchmark = 1.00; above 1 = more growth per unit of long-drawdown risk than the benchmark.

## Caveats
The scaling is growth-tilted, so it under-penalizes the fat tails of leveraged ETFs (read their ~100% P(>25% fall) directly). Correlation is high (~0.9) and surfaced as a warning, not in per-name cells. Company-specific blow-ups, total return (dividends/fees/taxes), and the judgment inputs (TAM, permanence, scores) are limitations. Permanence-weighted 'true permanent loss' is in tier_table.csv as the risk-tilted alternative.

### Known calibration gap — recovery *timing* (stated up front)
A backtest on **160 real >25% drawdowns across 25 names since 2008** shows the model **under-estimates how fast prices actually recover**. Realized vs model odds of being back to the prior peak: at 12 months **66% actual vs 23% model**, at 24 months **90% vs 40%**, at 36 months **95% vs 48%**. **So treat the recovery columns and the drawdown × recovery matrix below as a conservative (pessimistic) floor, not a center estimate.** Two honest limits on the backtest itself: it covers *survivors* (names still trading today, which biases realized recovery upward), and the macro dial is set to history, not forecast. The *depth* side is the validated part (the 7-crash backtest brackets the realized fall in 6 of 7); recovery *timing* is the least-certain layer, which is why it is flagged here rather than buried.

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
| NVIDIA | stock | 45% | secular | 0.0y | 53% | PEG-fast / MC-uncertain |
| Micron | stock | 45% | cyclical | 0.4y | 38% | cyclical high-growth / rebound-dependent |
| Credo Technology | stock | 55% | secular | 0.8y | 40% | PEG-fast / MC-uncertain |
| Palantir | stock | 45% | secular | 1.1y | 49% | PEG-fast / MC-uncertain |
| Astera Labs | stock | 55% | secular | 1.2y | 54% | PEG-fast / MC-uncertain |
| DRAM (Roundhill Memory) | ETF | 45% | cyclical | 1.5y | 37% | cyclical — needs TAM rebound |
| Applied Optoelectronics | stock | 45% | cyclical | 6.0y | 34% | cyclical — needs TAM rebound |
| ARKK (ARK Innovation) | ETF | 42% | broken | 7.9y | 27% | broken thesis — avoid unless evidence changes |
| SoundHound AI | stock | 45% | secular | ∞ | 42% | watch |
| CoreWeave | stock | 60% | cyclical | ∞ | 32% | cyclical — needs TAM rebound |
| IonQ | stock | 60% | broken | ∞ | 24% | broken thesis — avoid unless evidence changes |

## Drawdown × recovery probability matrix

*The model's central question, as probabilities — never exact timing. For each drawdown horizon: the chance of a >25% fall by then, and IF it falls, the chance it's back to its prior peak within 6 / 12 / 18 / 24 months (the rest is still underwater past 36m — slow, cyclical-wait, or impaired). Cyclical names are back-loaded by an explicit demand-trough: near-zero early recovery, catching up only after the demand cycle clears.*

**NVIDIA** — secular

| If >25% fall within | P(that fall) | recover ≤6m | ≤12m | ≤18m | ≤24m | ≤36m | still down >36m |
|---|--:|--:|--:|--:|--:|--:|--:|
| 6m | 13% | 20% | 37% | 49% | 57% | 67% | 33% |
| 12m | 33% | 21% | 40% | 52% | 59% | 69% | 31% |
| 18m | 49% | 20% | 41% | 53% | 60% | 70% | 30% |

**Microsoft** — secular

| If >25% fall within | P(that fall) | recover ≤6m | ≤12m | ≤18m | ≤24m | ≤36m | still down >36m |
|---|--:|--:|--:|--:|--:|--:|--:|
| 6m | 9% | 8% | 19% | 28% | 35% | 46% | 54% |
| 12m | 26% | 8% | 21% | 31% | 38% | 47% | 53% |
| 18m | 41% | 8% | 22% | 32% | 39% | 48% | 52% |

**Micron** — cyclical

| If >25% fall within | P(that fall) | recover ≤6m | ≤12m | ≤18m | ≤24m | ≤36m | still down >36m |
|---|--:|--:|--:|--:|--:|--:|--:|
| 6m | 20% | 0% | 0% | 37% | 43% | 53% | 47% |
| 12m | 46% | 0% | 0% | 38% | 44% | 53% | 47% |
| 18m | 64% | 0% | 0% | 38% | 44% | 52% | 48% |

**AMD** — cyclical

| If >25% fall within | P(that fall) | recover ≤6m | ≤12m | ≤18m | ≤24m | ≤36m | still down >36m |
|---|--:|--:|--:|--:|--:|--:|--:|
| 6m | 13% | 13% | 27% | 37% | 46% | 57% | 43% |
| 12m | 31% | 13% | 29% | 40% | 49% | 59% | 41% |
| 18m | 47% | 13% | 30% | 42% | 50% | 60% | 40% |

**IonQ** — broken

| If >25% fall within | P(that fall) | recover ≤6m | ≤12m | ≤18m | ≤24m | ≤36m | still down >36m |
|---|--:|--:|--:|--:|--:|--:|--:|
| 6m | 28% | 10% | 20% | 26% | 31% | 38% | 62% |
| 12m | 58% | 9% | 19% | 26% | 30% | 37% | 63% |
| 18m | 75% | 8% | 18% | 24% | 29% | 35% | 65% |

**SMH (VanEck Semis)** — secular

| If >25% fall within | P(that fall) | recover ≤6m | ≤12m | ≤18m | ≤24m | ≤36m | still down >36m |
|---|--:|--:|--:|--:|--:|--:|--:|
| 6m | 12% | 12% | 23% | 33% | 40% | 49% | 51% |
| 12m | 31% | 12% | 26% | 35% | 42% | 52% | 48% |
| 18m | 47% | 11% | 26% | 36% | 44% | 53% | 47% |

**DRAM (Roundhill Memory)** — cyclical

| If >25% fall within | P(that fall) | recover ≤6m | ≤12m | ≤18m | ≤24m | ≤36m | still down >36m |
|---|--:|--:|--:|--:|--:|--:|--:|
| 6m | 16% | 0% | 0% | 34% | 41% | 51% | 49% |
| 12m | 40% | 0% | 0% | 37% | 44% | 52% | 48% |
| 18m | 58% | 0% | 0% | 37% | 44% | 53% | 47% |

**QQQ (Nasdaq-100)** — secular

| If >25% fall within | P(that fall) | recover ≤6m | ≤12m | ≤18m | ≤24m | ≤36m | still down >36m |
|---|--:|--:|--:|--:|--:|--:|--:|
| 6m | 8% | 7% | 14% | 20% | 25% | 33% | 67% |
| 12m | 24% | 6% | 14% | 21% | 27% | 36% | 64% |
| 18m | 38% | 6% | 15% | 22% | 28% | 37% | 63% |

**VOO (S&P 500)** — secular

| If >25% fall within | P(that fall) | recover ≤6m | ≤12m | ≤18m | ≤24m | ≤36m | still down >36m |
|---|--:|--:|--:|--:|--:|--:|--:|
| 6m | 5% | 5% | 10% | 15% | 21% | 30% | 70% |
| 12m | 17% | 4% | 10% | 17% | 23% | 33% | 67% |
| 18m | 29% | 4% | 11% | 18% | 24% | 33% | 67% |

**ARKK (ARK Innovation)** — broken

| If >25% fall within | P(that fall) | recover ≤6m | ≤12m | ≤18m | ≤24m | ≤36m | still down >36m |
|---|--:|--:|--:|--:|--:|--:|--:|
| 6m | 27% | 10% | 21% | 28% | 34% | 41% | 59% |
| 12m | 56% | 9% | 21% | 29% | 34% | 41% | 59% |
| 18m | 74% | 8% | 19% | 27% | 33% | 40% | 60% |