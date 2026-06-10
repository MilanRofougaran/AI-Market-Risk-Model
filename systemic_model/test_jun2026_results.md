# Agent test run — 10-name growth & risk screen (June 2026)

*Discovery run_003 · model calibrated 2026-06-02 · 30,000 paths · 18-month mandate*
**Research model, not investment advice.**

Names tested: TECL, DRAM, PLTR, APP, META, MSFT, AMZN, CHAT, AIQ, QTUM.

## 1. Growth screen (discovery) — "where is the growth?"

The blended screen (0.55 demonstrated growth + 0.45 forward runway, discounted for hype/soft TAM) ranked them:

| Rank | Name | Type | Score |
|---|---|---|---|
| 1 | DRAM (Roundhill Memory) | ETF | 0.557 |
| 2 | Palantir (PLTR) | stock | 0.492 |
| 3 | AppLovin (APP) | stock | 0.439 |
| 4 | CHAT (Roundhill GenAI) | ETF | 0.399 |
| 5 | AIQ (Global X AI) | ETF | 0.348 |
| 6 | QTUM (Defiance Quantum) | ETF | 0.296 |
| 7 | TECL (3x Tech, leveraged) | ETF | 0.251 |
| 8 | Meta (META) | stock | 0.211 |
| 9 | Microsoft (MSFT) | stock | 0.200 |
| 10 | Amazon (AMZN) | stock | 0.164 |

The memory super-cycle (DRAM) and the two high-growth single names (PLTR, APP) top the list; the mature megacaps (MSFT, AMZN, META) score lowest because their growth, while durable, is slow relative to their size.

## 2. Risk verdict (analysis) — "would it survive a panic?"

Ranked by **P(deep & permanent)** = probability of a >25% drawdown that never recovers within the simulation (the permanent-loss tail, comparable across betas; lower is safer):

| Name | β | Fragility | P(DD>25%) | Recover by 18m | **P(deep & perm)** |
|---|---|---|---|---|---|
| Microsoft | 1.10 | 14% | 38% | 35% | **21%** |
| Meta | 1.23 | 6% | 43% | 39% | **22%** |
| CHAT (GenAI ETF) | 1.35 | 21% | 48% | 40% | **23%** |
| AIQ (AI ETF) | 1.34 | 21% | 48% | 40% | **24%** |
| QTUM (Quantum ETF) | 1.39 | 26% | 50% | 41% | **24%** |
| DRAM (Memory ETF) | 1.35 | 22% | 49% | 38% | **25%** |
| Palantir | 1.52 | 45% | 55% | 42% | **25%** |
| Amazon | 1.47 | 27% | 54% | 41% | **26%** |
| AppLovin | 2.37 | 37% | 80% | 54% | **29%** |
| TECL (3x leveraged) | — | — | **97%** | — | see §4 |

## 3. The headline: growth rank ≠ survivability rank

This is exactly the split the model is built to expose.

The screen's top growth picks are among the *riskiest* on a downturn. **AppLovin** has the highest demonstrated growth of any single name (+70%) but the worst survivability of the set: beta 2.37 means it falls >25% in 80% of simulated paths, and its demand is discretionary ad spend that freezes in a credit crunch, so its recovery floor is weak. **Palantir** ranks #2 on growth but carries a fragility of 45% — a forward P/E near 95 means most of its multiple is a floating premium that a correction punishes first.

The screen's *lowest* growth picks are the safest. **Microsoft** (lowest beta, sticky enterprise demand) and **Meta** (modest 18× multiple, durable earnings) have the lowest permanent-loss risk in the group. They won't compound fastest, but they are the least likely to inflict a loss that doesn't come back.

The diversified AI ETFs (**CHAT, AIQ, QTUM**) cluster in the safe-ish middle — diversification damps single-name fragility. **DRAM** is the exception among ETFs: despite topping the growth screen, memory is cyclical (low earnings quality), so its permanent-loss risk (25%) sits above the diversified AI baskets (23–24%).

## 4. TECL — not a growth holding, a decay machine

TECL is a 3×, daily-reset leveraged tech ETF, so it is modeled as a leveraged exposure rather than a company (it has no TAM). Over 18 months the simulation gives it a **97% chance of a >25% drawdown, 91% chance of >30%, and a 52% chance of losing more than half its value** — identical to TQQQ, and driven by volatility decay rather than any view on tech fundamentals. It belongs in a short-horizon trading sleeve, not an 18-month growth allocation; the model flags it accordingly.

## 5. Caveats

The four per-name judgment scores (TAM credibility, earnings durability, dominance, capex-elasticity) are honest opinions, not measurements — read the tiers, not the third decimal. The ETF figures are built from each fund's holdings, but only the constituents the model can price are included: coverage is **DRAM 24%** (only Micron; Samsung and SK Hynix are not modeled), **QTUM 16%**, **AIQ 31%**, **CHAT 35%**. The uncovered remainder is assumed to behave like the covered subset — reasonable for same-sector funds, but the DRAM number in particular leans almost entirely on Micron. AppLovin's beta (2.37) and Palantir's forward P/E (~95) are the two inputs most worth pressure-testing, since they drive those names' risk verdicts.
