# ETF recovery lens — the basket scorecard

*A single stock's crash outcome is an idiosyncratic lottery; an ETF averages it away, leaving the more forecastable question: is the theme's aggregate TAM/SAM intact, and can the majority of the basket self-fund a recovery? 'Conservation of TAM' — demand doesn't die in a crash, it changes hands among survivors. Research model, not investment advice.*

| ETF | class | coverage | conf | theme dur | fin. resil | fragile wt | top-3 fund | top-3 cov | eff N | fast/slow/perm |
|---|---|--:|:--:|--:|--:|--:|--:|--:|--:|---|
| CHAT (Roundhill GenAI) | thematic-diversified | 46% | medi | 0.69 | 0.76 | 0% | 18% | 39% | 9.3 | 67/29/4% |
| SMH (VanEck Semis) | thematic-diversified | 45% | medi | 0.66 | 0.74 | 0% | 32% | 68% | 5.0 | 66/31/4% |
| AIQ (Global X AI) | thematic-diversified | 43% | medi | 0.62 | 0.73 | 0% | 18% | 42% | 9.0 | 63/33/4% |
| SOXX (iShares Semis) | thematic-diversified | 46% | medi | 0.60 | 0.65 | 0% | 27% | 59% | 6.0 | 48/47/5% |
| QTUM (Defiance Quantum) | thematic-diversified | 16% | LOW  | 0.59 | 0.65 | 9% | 8% | 44% | 7.6 | 46/48/6% |
| DRAM (Roundhill Memory) | narrow/concentrated | 73% | high | 0.38 | 0.67 | 0% | 73% | 100% | 3.0 | 34/58/8% |

## Predictability class (GPT taxonomy)
- **broad index**: QQQ (Nasdaq-100), SCHD (Dividend), VOO (S&P 500)
- **thematic-diversified**: AIQ (Global X AI), CHAT (Roundhill GenAI), DTCR (Data Ctr Infra), GRID (Smart Grid), NUKE (Nuclear/Uranium), QTUM (Defiance Quantum), SMH (VanEck Semis), SOXX (iShares Semis)
- **narrow/concentrated**: ARKK (ARK Innovation), DRAM (Roundhill Memory)
- **leveraged**: SOXL (3x Semis), TECL (3x Tech), TQQQ (3x NDX)

## How to read it
- **theme durability / fin. resilience**: holdings-weighted; higher = the basket's market and balance sheets bridge a crash.
- **fragile wt**: share of the basket in weak-balance-sheet names — the dangerous tail an average can hide.
- **top-3 / eff. N**: concentration. A high top-3 or low effective-N means the ETF still behaves like its lead holdings (the `correlation.py` ~0.95 lead-correlation warning).
- **fast/slow/perm weight**: instead of forecasting every holding, the share of basket weight expected to recover fast, slowly, or impair permanently.
- **coverage / conf**: share of the fund in holdings the model scores explicitly. theme/resilience/fragile and top-3-cov are over that COVERED subset; **top-3 fund** is over the whole fund. LOW confidence (coverage <40%) means the decimals are default-driven and only the class is reliable (e.g. DRAM, QTUM, AIQ).