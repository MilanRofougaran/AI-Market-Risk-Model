# Analyst guide — Systemic + TAM Risk model (read & analyze)

**This is a research model. It is not investment advice, and its author is not a licensed financial advisor.** Every probability is a transparent function of stated assumptions, not a forecast.

**Start at `index.html`** — it's the front door that links to everything below (open it in any browser).

You have **analyst access**: you can view the results, run your own analyses and stress tests, and ask questions. You are **not** expected to change the model's calibration — that stays with the model owner, who refreshes it (the figures, the macro dashboard, the company inputs) so everyone works from one consistent source. See "What not to edit" at the end.

---

## 1. Just want to look? Open the dashboards (no setup)

These are self-contained HTML files — double-click to open in any browser:

- **`tier_dashboard.html`** — all names, growth-tiered, with the recovery-profile bars and the full numbers table. Includes the All / Stocks / ETFs toggle.
- **`tier_dashboard_etf.html`** — ETFs only (1–3 per tier).
- **`tier_table.csv` / `tier_table_etf.csv`** — the exact numbers, open in Excel.
- **`five_year_thesis.md`, `test_jun2026_results.md`** — written analyses.

How to read the two percentages:
- **Growth %** = expected revenue growth over the next ~18 months (sets the tier: high >40%, moderate 15–40%, safe <15%).
- **>3y tail %** = chance a >25% fall takes more than ~3 years to recover (the long, uncertain, "execution-risk" tail). Lower is safer. It is *not* the chance of a drop — drops are common and usually recover.

---

## 2. Want to analyze? Run the read-only tools (Python 3 + numpy)

Install once: `pip install numpy`. Then, from the package folder:

**Check a stock or ETF that isn't in the list** (non-destructive — it doesn't change anything):
```bash
python3 analyze_name.py --name "Nebius" --kind stock --theme "AI cloud" \
  --growth 0.65 --rev_bn 1.5 --tam_bn 200 --tam_cagr 0.40 --fwd_pe 90 \
  --beta 2.1 --quality 0.6 --earn_quality 0.4 --dominance 0.4 --capex_elastic 0.4
```
It prints the name's tier, recovery profile (recover in 1/2/3y, and the >3y tail), and ranks it against the current universe. (Don't have the inputs? Ask the owner, or ask Claude to research them.)

**See how the macro environment moves the tail:**
```bash
python3 stress_test.py        # tail across benign / current / elevated / critical macro
python3 macro_stress.py       # the current systemic-stress index + its components
```

**See the concentration / correlation picture:**
```bash
python3 correlation.py        # effective independent bets, joint-drawdown, ETF≈constituent
```

**Refresh the dashboards from the current results** (regenerates the HTML/CSV; doesn't change the model):
```bash
python3 build_dashboard.py
```

---

## 3. Want to ask questions?

- **In Cowork:** open the artifact ("systemic-tam-dashboard") — it has an **Ask** box that answers from the data in-page, plus the All/Stocks/ETFs toggle.
- **Anywhere else:** the dashboards + `analyze_name.py` answer most "where does X sit / how risky is Y" questions directly. For interpretation, paste the table or a dashboard into any Claude chat and ask.

---

## 4. What the model does — and does not — capture (read before relying on it)

Strong at: how deep beta takes a name in a panic, and whether its valuation premium is earned enough to recover. Captures macro stress (debt, credit spreads, leverage, liquidity) driving the systemic tail, and flags concentration.

Does **not** capture well: correlation/contagion is summarized as a warning (the names are ~1 bet, not many); company-specific blowups (fraud, guidance cuts, obsolescence); total return (dividends, fees, taxes); and the recovery/judgment inputs (TAM, penetration, the 0–1 scores) are opinions, not measurements. ETF figures for broad funds are estimates. Read tiers and ranges, not decimals.

---

## 5. What NOT to edit (analyst access)

Please don't change these — they are the owner's calibration and define the shared baseline:

- **`calibration.py`** — all the real-world numbers (macro dashboard, company revenue/TAM/multiples, judgment scores).
- **`discovery/tam_bridge.py`** — the per-name and ETF inputs.
- **`tiering.py`** — the universe list and expected-growth assumptions.
- **`engine.py`, `macro_stress.py`** — the mathematics.

If you think a number is stale or wrong, send it to the owner rather than editing — that keeps everyone on one consistent model. The tools in section 2 are all read-only with respect to these files (except `build_dashboard.py`, which only rewrites the HTML/CSV views).
