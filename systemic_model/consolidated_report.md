# Systemic + TAM Risk Agent — Consolidated Report

*Run date: 2026-06-03 · Model calibrated: 2026-06-02 · 30,000 paths · mandate 18m*

**Research model, not investment advice.**

## 1. Discovery shortlist

**Stocks (top picks by blended screen score):**

- **Palantir (PLTR)** — score 0.492  _(AI software)_
- **AppLovin (APP)** — score 0.439  _(AI ad-tech)_
- **Meta (META)** — score 0.211  _(AI/advertising)_
- **Microsoft (MSFT)** — score 0.200  _(cloud/AI software)_
- **Amazon (AMZN)** — score 0.164  _(cloud/retail)_

**ETFs:**

- **DRAM (Roundhill Memory)** — score 0.557  _(AI/semis-memory)_
- **CHAT (Roundhill GenAI)** — score 0.399  _(generative AI)_
- **AIQ (Global X AI)** — score 0.348  _(AI broad)_
- **QTUM (Defiance Quantum)** — score 0.296  _(quantum/compute)_
- **TECL (3x Tech, leveraged)** — score 0.251  _(tech (3x leveraged))_

**Run-over-run movement (penetration):**

- Moved up: none
- Moved down: none
- Entered: none
- Exited: none

## 2. Model verdict, joined to discovery

Ordered by **P(deep & permanent)** = P(drawdown >25% AND never recovers within the simulation) — worst first. This is the unconditional permanent-loss probability and is **comparable across betas**. `P(never|DD)` is conditional on a >25% drawdown and is only comparable *within* a similar-beta cohort, because a high-beta name dips past −25% on shallow, recoverable moves that flatter its conditional figure.

| Company | In shortlist | β | Fragility | P(DD>25%) | P(never\|DD) | **P(deep & perm)** |
|---|---|---|---|---|---|---|
| IonQ | no | 1.90 | 78% | 70% | 43% | **30%** |
| Applied Optoelectronics | no | 1.70 | 55% | 64% | 46% | **29%** |
| AppLovin | yes | 2.37 | 37% | 80% | 36% | **29%** |
| Coherent | no | 1.55 | 43% | 57% | 48% | **27%** |
| Lumentum | no | 1.50 | 45% | 56% | 48% | **27%** |
| Kioxia | no | 1.30 | 28% | 49% | 54% | **26%** |
| Amazon | yes | 1.47 | 27% | 54% | 48% | **26%** |
| Palantir | yes | 1.52 | 45% | 55% | 46% | **25%** |
| AMD | no | 1.40 | 28% | 51% | 50% | **25%** |
| DRAM (Roundhill Memory) | yes | 1.35 | 22% | 49% | 51% | **25%** |
| Micron | no | 1.35 | 22% | 49% | 51% | **25%** |
| ARM | no | 1.30 | 39% | 48% | 53% | **25%** |
| Marvell | no | 1.40 | 25% | 51% | 49% | **25%** |
| QTUM (Defiance Quantum) | yes | 1.39 | 26% | 50% | 48% | **24%** |
| SOXX (iShares Semis) | no | 1.35 | 21% | 48% | 50% | **24%** |
| SMH (VanEck Semis) | no | 1.37 | 21% | 49% | 48% | **24%** |
| AIQ (Global X AI) | yes | 1.34 | 21% | 48% | 49% | **24%** |
| CHAT (Roundhill GenAI) | yes | 1.35 | 21% | 48% | 49% | **23%** |
| Qualcomm | no | 1.15 | 12% | 41% | 56% | **23%** |
| NVIDIA | no | 1.45 | 22% | 51% | 45% | **23%** |
| Broadcom | no | 1.30 | 26% | 46% | 50% | **23%** |
| Meta | yes | 1.23 | 6% | 43% | 52% | **22%** |
| Microsoft | yes | 1.10 | 14% | 38% | 55% | **21%** |

## 3. Gaps to adjudicate (red-team checkpoint)

- **Discovery picks not yet modeled** (need the TAM stage before they enter the engine): TECL (3x Tech, leveraged)
- **Modeled names not surfaced by the screen** (why still carried?): AMD, ARM, Applied Optoelectronics, Broadcom, Coherent, IonQ, Kioxia, Lumentum, Marvell, Micron, NVIDIA, Qualcomm, SMH (VanEck Semis), SOXX (iShares Semis)

## 4. Human checkpoints recorded this run

- **narrow** — Confirm or edit the shortlist above before the (expensive) analysis stage. Does the AI/semis-foundation hypothesis still hold against this run's evidence?
- **redteam_pre_earnings** — ['IonQ'] have no real earnings; their forward P/E is a sentinel, so the model will show their premium as almost entirely floating (max fragility). Confirm you want them priced rather than held out.
- **signoff** — Review the sensitivity sweep (TABLE 5) and the systemic-tail reconciliation before treating any conclusion as final. Read by tier, not by exact rank; manage to the range, not the decimal.
- **redteam** — Adjudicate the gaps above. Discovery picks not yet modeled need the TAM stage (rev/TAM/penetration + judgment scores) before they enter the engine. Modeled names the screen did not surface deserve a 'why are we still carrying this?' look.
