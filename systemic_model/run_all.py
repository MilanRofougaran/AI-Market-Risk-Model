"""
============================================================================
 RUN_ALL  --  systemic_model  ·  the complete pipeline, start to finish
============================================================================
 One command runs EVERYTHING in order, for the full universe (stocks + ETFs +
 leveraged), and regenerates every output:

   1. DISCOVERY     screen the candidate universe (warm-started from registry)
   2. BRIDGE        turn discovery picks + ETFs into priceable companies
   3. MACRO/STRESS  compute the systemic-stress index from the dashboard
   4. MODEL         regime-switching Monte Carlo over all names -> results.json
   5. LEVERAGED     price 3x ETFs through the volatility-decay path, inject
   6. LEDGER        record this run to the 30-day change history
   7. ANALYSIS      stress ladder + correlation/concentration + runway decay
   8. OUTPUTS       dashboards, interactive artifacts, CSVs, one-pager, and a
                    complete report (complete_report.md)

 Usage:  python3 run_all.py [--paths 30000] [--light]
   --light skips the heavier stress-test / correlation sims for a fast refresh.

 RESEARCH MODEL, NOT INVESTMENT ADVICE.
============================================================================
"""
import argparse, importlib, json, os, sys, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "discovery"))

import calibration as C
import macro_stress as MS
import tam_bridge as TB


def banner(t):
    print("\n" + "#" * 76 + f"\n#  {t}\n" + "#" * 76)


def main(paths=30000, light=False):
    if light:
        paths = min(paths, 800)      # GPT: make --light genuinely light (was 4000)
    t0 = dt.datetime.now()
    banner(f"RUN_ALL  ·  {t0:%Y-%m-%d %H:%M}  ·  full pipeline")

    # 1. DISCOVERY -----------------------------------------------------------
    banner("1/8  DISCOVERY  (screen the candidate universe)")
    import agent as DA, screen_rules as SR, registry as R
    reg = R.load_registry()
    uni = R.current_universe(reg)
    if uni:
        etfs = SR.rank(uni, kind="etf"); stocks = SR.rank(uni, kind="stock")
        print(f"  registry universe: {len(uni)} candidates "
              f"({len(stocks)} stocks, {len(etfs)} etfs) re-scored by the blended screen")
        top = (stocks[:3] + etfs[:2])
        print("  top by screen: " + ", ".join(f"{c['name'].split(' (')[0]}={c['score']:.2f}" for c in top))
    else:
        print("  (no registry universe; using the modeled universe directly)")

    # 2. BRIDGE --------------------------------------------------------------
    banner("2/8  TAM BRIDGE  (make every pick priceable)")
    new, _ = TB.build_company_universe(base_companies=C.COMPANIES, verbose=True)
    for k, v in new.items():
        C.COMPANIES.setdefault(k, v)
    print(f"  modeled universe now: {len(C.COMPANIES)} priceable names")

    # 3. MACRO / STRESS ------------------------------------------------------
    banner("3/8  MACRO + SYSTEMIC STRESS")
    MS.print_report(C.MACRO)

    # 4. MODEL ---------------------------------------------------------------
    banner(f"4/8  MONTE CARLO  ({paths:,} paths)")
    C.SIM["n_paths"] = paths
    import run as RUN
    importlib.reload(RUN)
    RUN.main()

    # 5. LEVERAGED -----------------------------------------------------------
    banner("5/8  LEVERAGED ETFs  (volatility-decay path)")
    import add_leveraged
    try:
        add_leveraged.run(n_paths=(min(1500, max(500, paths)) if light else None))
    except TypeError:               # older signature without n_paths
        add_leveraged.run()

    # 6. LEDGER --------------------------------------------------------------
    banner("6/8  CHANGE LEDGER")
    import track_changes as TC
    TC.record()

    # 7. ANALYSIS ------------------------------------------------------------
    banner("7/8  ANALYSIS LAYERS")
    if light:
        print("  (--light: skipping stress-test / correlation / valuation-link sims)")
    else:
        import stress_test, correlation, runway_decay
        stress_test.run(n_paths=max(15000, paths // 2))
        correlation.run(n_paths=max(12000, paths // 3))
        runway_decay.run()
        import valuation_link            # SAM + short-interest -> price-risk overlay
        valuation_link.run(n_paths=max(8000, paths // 4))
        import backtest_2022             # honest validation vs the 2022 bear
        backtest_2022.run(n_paths=max(8000, paths // 4))
        import backtest_historical       # out-of-sample 2000/2008/2020 stress check
        _bh = backtest_historical.run(n_paths=max(8000, paths // 4), verbose=False)
        print(f"  backtest_historical: {_bh['captured']}/{_bh['n']} crashes captured in p90 tail")
        import portfolio_risk            # joint-risk demos on the contagion engine (full only)
        portfolio_risk.analyze_portfolio({"NVIDIA": 0.4, "Broadcom": 0.3, "Micron": 0.3},
                                         "Concentrated AI-infra",
                                         n_paths=max(8000, paths // 4), quiet=True)
    # earn-back clock is deterministic & fast -> run in light AND full modes
    try:
        import fundamental_catchup
        fundamental_catchup.run(verbose=False)
    except Exception as e:
        print("  earn-back note:", e)
    try:
        import solvency, solvency_cases
        print("  solvency fork (top fragile):", ", ".join(
            f"{nm.split(' (')[0]} {h*100:.0f}%" for nm,_,_,_,_,h in solvency.report()[:5]))
        _sc = solvency_cases.run(verbose=False)
        print(f"  solvency 2021->2024 case AUC: {_sc['auc']:.2f}")
        import etf_lens
        etf_lens.run(verbose=False)
        print("  etf_lens.md written (basket recovery scorecard)")
        import growth_recovery
        growth_recovery.run(verbose=False)
        print("  growth_recovery.md written (high-growth PEG vs safe earn-back ranking)")
        import etf_horizon_rank
        _ehr = etf_horizon_rank.run(n_paths=(1500 if light else 30000), verbose=False)
        print(f"  etf_horizon_rank.md written (per-horizon ETF expected-return ranking, {len(_ehr)} ETFs)")
    except Exception as e:
        print("  solvency note:", e)

    # 8. OUTPUTS -------------------------------------------------------------
    banner("8/8  BUILD OUTPUTS")
    import build_dashboard, build_artifact   # build_onepager imported only in full mode
    build_dashboard.build()
    build_dashboard.build(kind="ETF", cap=3, title_suffix=" — ETFs only (1-3 per tier)",
                          out_path=os.path.join(HERE, "tier_dashboard_etf.html"),
                          csv_path=os.path.join(HERE, "tier_table_etf.csv"))
    build_artifact.build()
    build_artifact.build(kind="ETF", cap=3, title_suffix=" · ETFs only",
                         out_path=os.path.join(HERE, "tier_artifact_etf.html"))
    if not light:
        try:
            import build_onepager   # PDF (reads current results.json); skip in --light
        except Exception as e:
            print("  one-pager note:", e)
    else:
        print("  (--light: skipping one-pager PDF)")
    _write_complete_report(light=light)

    pdf = "" if light else ", Systemic_TAM_onepager.pdf"
    print(f"\nDONE in {(dt.datetime.now()-t0).seconds}s.  "
          f"Outputs: complete_report.md, tier_dashboard*.html, tier_artifact*.html, "
          f"tier_table*.csv, fundamental_catchup.md{pdf}")


def _write_complete_report(light=False):
    import tiering as T, build_dashboard as B
    res = json.load(open(os.path.join(HERE, "results.json")))
    st = MS.compute(res.get("macro", {}))
    rows = T.build_rows(res)
    tiers = T.tier_rows(rows)
    # in --light the correlation sim is skipped; do NOT fold a stale full-run
    # correlation_report.json into the report (GPT review).
    cr = {} if light else (B._load(os.path.join(HERE, "correlation_report.json")) or {})
    L = []
    L.append("# Systemic + TAM Risk — complete report")
    L.append(f"\n*Full universe ({len(rows)} names: stocks + ETFs + leveraged) · "
             f"model as of {res.get('as_of')} · generated {dt.date.today()} · "
             f"{res.get('macro',{}).get('sp500_forward_pe','?')} S&P fwd P/E*")
    L.append("\n**Research model — not investment advice. Read tiers and ranges, not decimals.**")
    L.append(f"\n## Macro & systemic stress\nIndex **{round(st['score']*100)}/100** "
             f"({MS.stress_label(st['score'])}) — structural fragility {round(st['structural']*100)}, "
             f"acute trigger {round(st['acute']*100)}; scales the crisis odds ×{MS.crisis_mult(st['score']):.2f}. "
             f"Inputs: CAPE {res['macro'].get('shiller_cape')}, real 10y {res['macro'].get('ust_10y_real')}%, "
             f"VIX {res['macro'].get('vix')}, Brent ${res['macro'].get('brent_usd')}, "
             f"HY spread {res['macro'].get('hy_oas_bps')}bps, margin-debt YoY {round(res['macro'].get('margin_debt_yoy',0)*100)}%.")
    if cr.get("baskets"):
        u = next((b for b in cr["baskets"] if "universe" in b["label"].lower()), cr["baskets"][0])
        L.append(f"\n## Concentration\n~{u['neff_with']:.0f} effective independent bets across "
                 f"{u['n']} names (avg correlation {u['rho_with']:.2f}) — essentially one AI-capex bet; "
                 f"specialized ETFs are ~0.95 correlated with their lead holding.")
    # ---- how the ranking works ----
    L.append("\n## How the ranking works")
    L.append("Two axes, two sort keys — so different views order names differently on the same data:")
    L.append("- **Growth** (expected 18-month revenue growth) sets the **tier** (>40% / 15–40% / <15%). "
             "The tiered tables below and the dashboard's recovery bars are **sorted by growth** within each tier.")
    L.append("- **Risk is simulated**, not assigned: a regime-switching Monte Carlo where **beta sets how deep "
             "a name falls** and **TAM-penetration sets whether it recovers**. Headline = the **>3y tail** "
             "(P of a >25% fall still underwater at ~3.5y); macro-stress scales the crisis odds.")
    L.append("- **vs S&P / vs SCHD** combine both: (growth ÷ benchmark growth) × (benchmark tail ÷ name tail), "
             "benchmark = 1.00. **Sorting by this gives a different order than sorting by growth** — it can rank a "
             "lower-tail name above a faster grower. (This is why a growth-sorted plot and the vs-S&P ranking look different.)")
    L.append("- Not an expected-return forecast or a buy list. Growth and the judgment scores are opinions the model sweeps.")

    # ---- master ranking by reward-to-risk (vs S&P) ----
    def _md(x):
        return f"{round(x*100)}%" if isinstance(x, (int, float)) else "—"
    # recovery_rank (crash-growth-aware) so the vs-S&P ranking can't make a BROKEN or
    # cyclical name look like a clean positive (GPT reporting-consistency review). Short
    # tags here; the full verdicts are in tier_table.csv + the growth-recovery section.
    _grj = B._load(os.path.join(HERE, "growth_recovery.json")) or {}
    _rank_map = _grj.get("recovery_rank", {}) or {}
    def _short_rank(nm):
        lbl = _rank_map.get(nm, "")
        if not lbl:
            try:
                import crash_growth as _CG; a = _CG.archetype(nm)
            except Exception:
                a = ""
            lbl = ("broken thesis — avoid unless evidence changes" if a == "broken"
                   else "cyclical high-growth / rebound-dependent" if a == "cyclical" else "")
        if lbl.startswith("broken"):              return "⚠ broken — avoid"
        if lbl.startswith("cyclical"):            return "cyclical — rebound-dep"
        if lbl.startswith("secular"):             return "secular high-growth"
        if lbl.startswith("PEG-fast"):            return "PEG-fast / MC-uncertain"
        if lbl.startswith("diversified"):         return "diversified / safe"
        return lbl or "—"
    L.append("\n## Master ranking — by reward-to-risk (vs S&P, high to low)")
    L.append("\n*The **Recovery** column is the crash-growth-aware verdict: vs-S&P sorts by "
             "reward-to-risk and can float a broken or cyclical name up the list, so read it "
             "alongside Recovery — a '⚠ broken — avoid' or 'cyclical — rebound-dependent' tag "
             "overrides a flattering vs-S&P number.*")
    L.append("\n| # | Name | Type | Tier | Recovery | Growth | >3y tail | vs S&P | vs SCHD |")
    L.append("|--:|---|---|---|---|--:|--:|--:|--:|")
    def _tier(g):
        return "High" if g > 0.40 else ("Moderate" if g >= 0.15 else "Safe")
    core = [x for x in rows if x["name"] not in T.LEVERAGED]
    for i, r in enumerate(sorted(core, key=lambda r: -(r["vs_sp"] or 0)), 1):
        L.append(f"| {i} | {r['name']} | {r['kind']} | {_tier(r['growth'])} "
                 f"| {_short_rank(r['name'])} "
                 f"| {_md(r['growth'])} | {_md(r['p_deep_permanent'])} "
                 f"| {round(r['vs_sp'],2) if r.get('vs_sp') else '—'} "
                 f"| {round(r['vs_schd'],2) if r.get('vs_schd') else '—'} |")
    L.append("\n### Trading vehicles — excluded from the ranking (path-dependent decay)")
    L.append("\n| Name | P(>25% fall) | >3y tail | note |")
    L.append("|---|--:|--:|---|")
    for r in rows:
        if r["name"] in T.LEVERAGED:
            L.append(f"| {r['name']} | {_md(r['p_dd25'])} | {_md(r['p_deep_permanent'])} "
                     "| 3x daily reset; volatility decay; not a growth holding |")
    L.append("\n*(The tiered tables below are the same names sorted by growth within tier — a different sort, same data.)*")

    sp_tail = B._buckets(res, "VOO (S&P 500)")["gt3"] or 0.21
    for label, mem in tiers:
        L.append(f"\n## {label}")
        L.append("\n| Name | Type | Recovery | Growth | P(>25% fall) | recover 2y | >3y tail | ×S&P | vs S&P | vs SCHD |")
        L.append("|---|---|---|--:|--:|--:|--:|--:|--:|--:|")
        for r in mem:
            L.append(f"| {r['name']} | {r['kind']} | {_short_rank(r['name'])} | {_md(r['growth'])} | {_md(r['p_dd25'])} "
                     f"| {_md(r['p_recover_24m'])} | {_md(r['p_deep_permanent'])} "
                     f"| {round(r['perm_vs_sp'],2) if r.get('perm_vs_sp') else '—'}× "
                     f"| {round(r['vs_sp'],2) if r.get('vs_sp') else '—'} "
                     f"| {round(r['vs_schd'],2) if r.get('vs_schd') else '—'} |")
    L.append("\n## How to read it")
    L.append("- **Growth** sets the tier (>40% / 15–40% / <15%, expected 18m).")
    L.append("- **>3y tail** = chance a >25% fall is still underwater at ~3.5y.")
    L.append("- **×S&P** = that tail as a multiple of the S&P's.")
    L.append("- **vs S&P / vs SCHD** = (growth ÷ benchmark growth) × (benchmark tail ÷ name tail); "
             "benchmark = 1.00; above 1 = more growth per unit of long-drawdown risk than the benchmark.")
    L.append("\n## Caveats\nThe scaling is growth-tilted, so it under-penalizes the fat tails of "
             "leveraged ETFs (read their ~100% P(>25% fall) directly). Correlation is high (~0.9) "
             "and surfaced as a warning, not in per-name cells. Company-specific blow-ups, total "
             "return (dividends/fees/taxes), and the judgment inputs (TAM, permanence, scores) are "
             "limitations. Permanence-weighted 'true permanent loss' is in tier_table.csv as the risk-tilted alternative.")
    # ---- ETF recovery lens section (basket scorecard) ----
    try:
        import etf_lens as _EL
        el = _EL.run(verbose=False)
        L.append("\n## ETF recovery lens (basket > single-name)")
        L.append("A single stock's crash is an idiosyncratic lottery; an ETF averages it away, so the "
                 "question becomes theme TAM/SAM durability + basket financial resilience, not one CEO. "
                 "theme/resilience/top-3-cov are over the model-COVERED subset; **top-3 fund** is whole-fund; "
                 "LOW coverage = decimals default-driven, trust the class only.")
        L.append("\n| ETF | class | coverage | conf | theme dur | fin resil | fragile wt | top-3 fund | top-3 cov | eff N | fast/slow/perm |")
        L.append("|---|---|--:|:--:|--:|--:|--:|--:|--:|--:|---|")
        mp = sorted([(k, v) for k, v in el.items() if "theme_durability" in v],
                    key=lambda kv: -kv[1]["theme_durability"])
        for etf, v in mp:
            L.append(f"| {etf} | {v['class'].split(' (')[0]} | {v['known_coverage']*100:.0f}% | "
                     f"{v['confidence'][:4]} | {v['theme_durability']:.2f} | {v['fin_resilience']:.2f} | "
                     f"{v['fragile_weight']*100:.0f}% | {v['top3_fund']*100:.0f}% | {v['top3']*100:.0f}% | "
                     f"{v['neff']:.1f} | {v['fast_weight']*100:.0f}/{v['slow_weight']*100:.0f}/{v['permanent_weight']*100:.0f}% |")
        L.append("\n*Class-only (no holdings map): " + ", ".join(
            f"{k.split(' (')[0]} = {v['class'].split(' (')[0]}" for k, v in el.items()
            if "theme_durability" not in v) + ".*")
    except Exception as e:
        L.append("\n*(ETF lens unavailable: %s)*" % e)
    try:
        import growth_recovery as _GR
        gr = _GR.run(verbose=False)
        L.append("\n## Growth-regime recovery ranking")
        L.append(f"High-growth names grow INTO the multiple (PEG-anchored), so recovery time is the "
                 f"PEG earn-back; they rank HIGH when likely to reclaim within 18m. Safe/diversified "
                 f"names recover via buyback + adjusted-PE, ranked by vs-S&P.")
        L.append("\n**High-growth (>40%) — by PEG earn-back:**")
        L.append("\n| Name | type | growth | crash-growth | PEG earn-back | P(rec≤18m) | rank |")
        L.append("|---|---|--:|:--:|--:|--:|:--:|")
        for x in gr["high_growth"]:
            py = "∞" if x["peg_years"] in (None, float('inf')) else f"{x['peg_years']:.1f}y"
            pr = "—" if x["p_recover"] is None else f"{x['p_recover']*100:.0f}%"
            lbl = x.get("rank_label", "HIGH" if x["rank_high"] else "watch")
            L.append(f"| {x['name']} | {x['kind']} | {x['growth']*100:.0f}% | {x.get('crash_growth','')} | "
                     f"{py} | {pr} | {('**'+lbl+'**') if x['rank_high'] else lbl} |")
    except Exception as e:
        L.append("\n*(growth-recovery unavailable: %s)*" % e)

    # ---- drawdown x recovery probability matrix (the core question, per name) ----
    try:
        rcond = res.get("companies", {}).get("recovery_cond", {})
        L.append("\n## Drawdown × recovery probability matrix")
        L.append("\n*The model's central question, as probabilities — never exact timing. For "
                 "each drawdown horizon: the chance of a >25% fall by then, and IF it falls, the "
                 "chance it's back to its prior peak within 6 / 12 / 18 / 24 months (the rest is "
                 "still underwater past 36m — slow, cyclical-wait, or impaired). Cyclical names are "
                 "back-loaded by an explicit demand-trough: near-zero early recovery, catching up "
                 "only after the demand cycle clears.*")
        def _p(x):
            return f"{round(x*100)}%" if isinstance(x, (int, float)) else "—"
        # a readable curated set spanning the archetypes + broad/narrow ETFs
        want = ["NVIDIA", "Microsoft", "Micron", "AMD", "IonQ",
                "SMH (VanEck Semis)", "DRAM (Roundhill Memory)", "QQQ (Nasdaq-100)",
                "VOO (S&P 500)", "ARKK (ARK Innovation)"]
        shown = [n for n in want if n in rcond and rcond[n].get("dd_recovery_matrix")]
        for nm in shown:
            mtx = rcond[nm]["dd_recovery_matrix"]
            cg = ""
            try:
                import crash_growth as _CGx; cg = _CGx.archetype(nm)
            except Exception:
                pass
            L.append(f"\n**{nm}**{(' — ' + cg) if cg else ''}")
            L.append("\n| If >25% fall within | P(that fall) | recover ≤6m | ≤12m | ≤18m | ≤24m | ≤36m | still down >36m |")
            L.append("|---|--:|--:|--:|--:|--:|--:|--:|")
            for hz in ("6m", "12m", "18m"):
                r = mtx.get(hz, {})
                L.append(f"| {hz} | {_p(r.get('p_drawdown'))} | {_p(r.get('recover_6m'))} "
                         f"| {_p(r.get('recover_12m'))} | {_p(r.get('recover_18m'))} "
                         f"| {_p(r.get('recover_24m'))} | {_p(r.get('recover_36m'))} "
                         f"| {_p(r.get('not_recovered_36m'))} |")
        if not shown:
            L.append("\n*(matrix unavailable — re-run the full pipeline to populate it)*")
    except Exception as e:
        L.append("\n*(drawdown×recovery matrix unavailable: %s)*" % e)

    with open(os.path.join(HERE, "complete_report.md"), "w") as f:
        f.write("\n".join(L))
    print("  wrote complete_report.md")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", type=int, default=30000)
    ap.add_argument("--light", action="store_true")
    a = ap.parse_args()
    main(paths=a.paths, light=a.light)
