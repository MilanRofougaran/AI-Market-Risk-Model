# Owner guide — full system (master copy)

This is the **complete, editable** model — your master. (The analyst distribution is the read-only subset; this is the full thing, including the calibration files you edit.) Research model, not investment advice.

Requirements: Python 3 + `numpy` (and `reportlab` for the one-pager PDF). `pip install numpy reportlab`.

---

## The pipeline, end to end

```
discovery  ->  TAM bridge  ->  calibration  ->  engine (macro-stress-aware MC)  ->  results.json
   |                                                                                    |
screen + registry                                              tiering / dashboards / charts / tables
                                                               drift + 30-day ledger / stress test / correlation
```

Run the whole model over the full universe (this is the command the daily task uses):
```bash
python3 -c "import calibration as C,sys; sys.path.insert(0,'discovery'); import tam_bridge as TB; \
new,_=TB.build_company_universe(base_companies=C.COMPANIES,verbose=False); \
[C.COMPANIES.setdefault(k,v) for k,v in new.items()]; import run; run.main()"
```
Then refresh everything:
```bash
python3 track_changes.py --record      # append to the 30-day ledger
python3 build_dashboard.py             # tier_dashboard.html + _etf.html + CSVs
python3 build_artifact.py              # tier_artifact.html + _etf.html (charts/toggle/ask)
python3 build_onepager.py              # Systemic_TAM_onepager.pdf
python3 drift_report.py --snapshot     # set tomorrow's baseline
```

---

## File map

**Model core (the math + the numbers) — edit `calibration.py`/`tam_bridge.py` to update the world; rarely touch `engine.py`.**
- `calibration.py` — ALL real-world numbers: macro dashboard (incl. the systemic-stress inputs), regime probs, the 8 base companies, sim settings. *This is the file you edit when the world changes.*
- `engine.py` — the mathematics: regime-switching Monte Carlo, premium decomposition, recovery curve, drawdown/recovery. Reads the macro-stress multiplier.
- `macro_stress.py` — composite systemic-stress index (structural fragility + acute trigger) that drives the crisis odds. Bands/weights live here.
- `run.py` — the driver: runs the model, prints the tables, writes `results.json`.
- `run_dominance_sweep.py` — heavier moat-sensitivity sweep.

**Discovery (`discovery/`)**
- `screen_rules.py` — the blended growth-screen scoring.
- `registry.py` — the persistent candidate memory + run-over-run diffs.
- `agent.py` — the stage-plan orchestration + red-team filter.
- `first_run.py` — the seed run.
- `tam_bridge.py` — converts discovery picks into priceable companies; per-stock TAM facts, ETF-from-holdings aggregation, and broad-ETF direct specs (ARKK/QQQ/VOO/SCHD). **Add new names here.**
- `candidate_registry.json` — the registry state.

**Universe + presentation**
- `tiering.py` — the full ranked universe (`UNIVERSE`: name → kind/theme/expected-growth) and the tier logic. **Add a name's growth/theme here too.**
- `build_dashboard.py` — regenerates the self-contained HTML dashboards + CSV tables (full and ETF-only).
- `build_artifact.py` — regenerates the interactive Cowork artifacts (recovery bars + sortable table + selectable charts + All/Stocks/ETFs toggle + Ask box).
- `build_onepager.py` — the one-page PDF handout.
- `index.html` — the front door for the shared package.

**Monitoring**
- `drift_report.py` — day-over-day change flagger (`--snapshot` to set baseline).
- `track_changes.py` — the 30-day ledger + cumulative-drift detector (`--record`, `--window 30`).
- `_demo_history.py` — seeds an *illustrative* month of history (demo only; real history accrues from daily runs).

**Analysis tools**
- `analyze_name.py` — on-demand: price any new ticker and rank it vs the universe (non-destructive).
- `stress_test.py` — the macro stress ladder (benign → critical).
- `correlation.py` — concentration / joint-drawdown / effective-bets.
- `runway_decay.py` — the 5-year cushion projection.
- `run_agent.py` — the end-to-end orchestrator (discovery → bridge → analysis → consolidated report).

**Outputs (regenerated; safe to delete, they rebuild)**
- `results.json` (master model output), `results_baseline.json`, `drift_history.json`, `*_report.json`, `*.csv`, `tier_*.html`, `*.md` reports, `Systemic_TAM_onepager.pdf`.

**Docs**
- `README.md`, `VERIFICATION.md` — the model's own design/change record.
- `ANALYST_GUIDE.md` — the read-only guide shipped to analysts.
- `OWNER_GUIDE.md` — this file.

---

## The monthly / quarterly update ritual

1. **Monthly (light):** refresh `MACRO` in `calibration.py` — valuation, rates, VIX/MOVE, oil, and the stress inputs (`hy_oas_bps`, `ig_oas_bps`, `household_debt_gdp`, `corp_debt_gdp`, `margin_debt_yoy`, `short_interest_pct`). Update `AS_OF_DATE`. Re-run.
2. **Quarterly (full, at earnings):** update each name's `rev_bn`, `tam_bn`, `tam_cagr`, `fwd_pe`, `beta`, and the four judgment scores — in `calibration.COMPANIES` (the 8 base names) or `discovery/tam_bridge.py` (bridged names). Re-run.
3. **Reset the stress baseline** if you do a full recalibration: set `macro_stress.STRESS_BASELINE` to the freshly computed index so the crisis multiplier re-centres at ~1.0.

## Add a new name permanently
1. Add its inputs to `discovery/tam_bridge.py` (`STOCK_TAM_FACTS`, or `ETF_HOLDINGS` / `ETF_DIRECT_SPECS` for funds).
2. Add it to `tiering.UNIVERSE` with its kind, theme, and expected 18-month growth.
3. (Optional) add a correlation group in `correlation.py` `GROUP`.
4. Re-run. (Use `analyze_name.py` first if you just want a what-if without committing it.)

## The daily scheduled task
A Cowork task ("systemic-model-daily-drift") runs each morning: refresh macro → re-run → drift + 30-day cumulative → rebuild dashboards/artifacts → report only what moved → snapshot. It needs this folder to live in a connected Cowork folder. Edit its prompt via the Scheduled sidebar.

## Known limitations (carry these in mind)
Strong on systematic depth + earned-premium recovery and macro-stress. Weak on: correlation/contagion (surfaced as a warning — the universe is ~1 bet), company-specific blowups (fraud/guidance/obsolescence), total return (no dividends/fees/taxes), and the judgment inputs are opinions. The idiosyncratic term is set low, which makes modeled correlation high (~0.9) and ETFs look like their constituents — a deeper recalibration if you ever want realistic single-name dispersion. Read tiers and ranges, not decimals.
