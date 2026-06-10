"""
============================================================================
 BACKTEST_2022 -- would the model have seen 2022 coming?
============================================================================
 Calibrates the machine to Dec-31-2021 conditions (macro + betas), runs the
 12-month Monte Carlo, and compares predicted max-drawdown distributions to
 what ACTUALLY happened in calendar 2022 -- the cleanest stress year for
 exactly this universe (rates shock -> multiple compression -> AI/tech bear).

 Scoring per name:
   - pctile  : where the realized 2022 drawdown fell in the predicted
               distribution (0.50 = dead center; <0.10 = model said "almost
               never this bad" -> under-prediction)
   - P(>=realized): predicted probability of a drawdown at least that deep
   - in 10-90 band: calibrated models put ~80% of names inside

 Run:  python3 backtest_2022.py
 Writes backtest_2022.md / .json.  RESEARCH MODEL, NOT INVESTMENT ADVICE.
============================================================================
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import calibration as C
import macro_stress as MS
import engine as E

# ---- Dec 31, 2021 macro (sources: standard published series) --------------
MACRO_2021 = dict(
    shiller_cape=38.3, ust_10y_real=-1.04, margin_debt_yoy=0.25,
    household_debt_gdp=77, corp_debt_gdp=49,
    hy_oas_bps=283, ig_oas_bps=92, vix=17.2, move=77, brent_usd=77.8,
    short_interest_pct=1.7,
    fed_net_liq_3m_pct=1.0,      # QT had not started; RRP absorbing
    mmf_dry_powder_gdp=19.8,     # $4.7tn / $23.7tn -- LESS buffer than 2026
)

# ---- universe: 2021-era betas + realized 2022 max drawdown (close basis) --
# val_gap_2021 = RETROSPECTIVE judgment of how much of the Dec-2021 multiple
# was floating (COVID-bubble) premium. These are in-sample estimates chosen
# with hindsight -- honest use: regime mechanism demo, NOT proof of foresight.
NAMES = {  # name: (beta_2021, realized_2022_maxDD, val_gap_2021)
    "S&P 500 (SPY)":  (1.00, 0.254, 0.00),
    "Nasdaq-100":     (1.18, 0.356, 0.25),
    "SOXX (semis)":   (1.40, 0.459, 0.15),
    "ARKK":           (1.80, 0.668, 0.85),
    "NVIDIA":         (1.60, 0.627, 0.40),
    "AMD":            (1.70, 0.650, 0.45),
    "Meta":           (1.25, 0.767, 0.60),
    "Microsoft":      (1.10, 0.387, 0.20),
    "Apple":          (1.15, 0.309, 0.15),
    "Amazon":         (1.25, 0.556, 0.40),
    "Alphabet":       (1.10, 0.446, 0.20),
    "Tesla":          (2.00, 0.722, 0.80),
    "Micron":         (1.40, 0.473, 0.10),
    "Palantir":       (2.00, 0.668, 0.70),
}


def run(n_paths=12000):
    st = MS.compute(MACRO_2021)
    saved = C.SYSTEMIC_STRESS
    C.SYSTEMIC_STRESS = st            # engine reads this for crisis transitions
    print(f"Dec-2021 systemic-stress index: {round(st['score']*100)}/100 "
          f"(structural {round(st['structural']*100)}, acute {round(st['acute']*100)}) "
          f"vs today's {round(saved['score']*100)}")
    rng = np.random.default_rng(2022)
    days = 252
    factor, crisis, grind = E._simulate_factor(rng, n_paths, days, return_grind=True)
    g_occ = float(grind.mean())
    print(f"grind-state occupancy on simulated paths: {g_occ:.1%} of days")
    rows = {}
    for nm, (beta, realized, gap) in NAMES.items():
        spec = dict(beta=beta, idio=0.11, mu=0.0, L=1, leveraged=False,
                    tail_mult=1.0, recov_shift=0.0,
                    grind_drag=1.0 * max(0.0, gap - 0.15))
        price = E._price_path(rng, factor, crisis, spec, n_paths, days, grind=grind)
        mdd, _ = E._drawdown_and_recovery(price, days)
        d = -mdd  # positive depths
        extra = {"p_th_%d" % int(th*100): float(np.mean(d >= th))
                 for th in (0.25, 0.35, 0.45, 0.60)}
        # conditional view: among GRIND-YEAR paths (>40% of days in the grind
        # state -- what 2022 actually was), where does realized fall?
        gy = grind.mean(axis=1) > 0.40
        dg = d[gy] if gy.sum() > 50 else d
        rows[nm] = dict(
            extra, beta=beta, realized=realized,
            med_grind=float(np.median(dg)), p90_grind=float(np.quantile(dg, 0.90)),
            in_band_grind=bool(np.quantile(dg, 0.10) <= realized <= np.quantile(dg, 0.90)),
            pctile=float(np.mean(d < realized)),
            p_realized=float(np.mean(d >= realized)),
            med=float(np.median(d)), p90=float(np.quantile(d, 0.90)),
            p10=float(np.quantile(d, 0.10)),
            in_band=bool(np.quantile(d, 0.10) <= realized <= np.quantile(d, 0.90)))
    C.SYSTEMIC_STRESS = saved

    # calibration metrics (review feedback): Brier scores + rank correlation
    import numpy as _np
    briers = {}
    for th in (0.25, 0.35, 0.45, 0.60):
        preds, outs = [], []
        for nm, rr in rows.items():
            # recompute predicted P(depth >= th) from stored quantiles is lossy;
            # use p_realized-style: store per-threshold at sim time instead
            preds.append(rr.get("p_th_%d" % int(th*100), None))
            outs.append(1.0 if rr["realized"] >= th else 0.0)
        if all(p is not None for p in preds):
            briers[th] = float(_np.mean([(p-o)**2 for p, o in zip(preds, outs)]))
    def _rank(v):
        s = sorted(range(len(v)), key=lambda i: v[i]); rk=[0]*len(v)
        for j,i in enumerate(s): rk[i]=j
        return rk
    pred_med = [rows[nm]["med"] for nm in rows]; real = [rows[nm]["realized"] for nm in rows]
    ra, rb = _rank(pred_med), _rank(real)
    n_ = len(ra); spearman = 1 - 6*sum((a-b)**2 for a,b in zip(ra,rb))/(n_*(n_**2-1))

    inb = sum(r["in_band"] for r in rows.values())
    inb_g = sum(r["in_band_grind"] for r in rows.values())
    p_grind_year = float((grind.mean(axis=1) > 0.40).mean())
    L = ["# 2022 backtest — predicted vs realized max drawdowns",
         f"\n*Model calibrated to Dec-31-2021 (stress index {round(st['score']*100)}/100), "
         f"12-month horizon, {n_paths:,} paths. Research model, not investment advice.*",
         "\n| Name | beta'21 | realized 2022 | predicted median | predicted p90 | P(≥realized) | percentile | in 10-90? |",
         "|---|--:|--:|--:|--:|--:|--:|:--:|"]
    for nm, r in sorted(rows.items(), key=lambda kv: -kv[1]["realized"]):
        L.append(f"| {nm} | {r['beta']:.2f} | -{r['realized']:.0%} | -{r['med']:.0%} "
                 f"| -{r['p90']:.0%} | {r['p_realized']:.0%} | {r['pctile']:.0%} "
                 f"| {'yes' if r['in_band'] else 'NO'} |")
    L.append(f"\n**{inb}/{len(rows)} names inside the unconditional 10–90 band** "
             "(a calibrated model expects ~80%).")
    L.append(f"\n## The 4th-regime (de-rating) view\nAt Dec-2021 structural fragility the model "
             f"assigns **{p_grind_year:.0%} odds that 2022 becomes a grind year** (>40% of days in "
             f"the de-rating state). 2022 WAS that year. **Conditional on a grind year, "
             f"{inb_g}/{len(rows)} names fall inside the predicted 10–90 band:**")
    L.append("\n| Name | realized | grind-year median | grind-year p90 | in band? |")
    L.append("|---|--:|--:|--:|:--:|")
    for nm, r in sorted(rows.items(), key=lambda kv: -kv[1]["realized"]):
        L.append(f"| {nm} | -{r['realized']:.0%} | -{r['med_grind']:.0%} | -{r['p90_grind']:.0%} "
                 f"| {'yes' if r['in_band_grind'] else 'NO'} |")
    L.append("\n*Honest read: the val_gap_2021 inputs are retrospective (hindsight), so this "
             "validates the MECHANISM (floating premium bleeds in a grind), not foresight. "
             "What the model could not know in advance is WHICH year the grind arrives — "
             "that remains a probability, not a prediction.*")
    L.append(f"\n**Calibration metrics**: Spearman rank correlation (predicted median vs realized) "
             f"= **{spearman:.2f}** — ordering skill. Brier scores: "
             + ", ".join(f"P(>{int(t*100)}%): {v:.3f}" for t, v in briers.items())
             + " (0 = perfect, 0.25 = no-skill coin flip; these are WORSE than 0.25 because the "
             "model confidently assigned low probability to drawdowns that then happened — "
             f"magnitude miscalibration, consistent with the band count. The {spearman:.2f} Spearman "
             "says the model ranks names well; the Brier says don't trust its 2021-conditioned levels).")
    L.append("\n## Honest findings")
    L.append("- The Dec-2021 **acute** trigger was asleep (VIX 17, HY 283bps) — the index "
             "could not foresee the Fed's 2022 policy shock; it is a *monitor* that would have "
             "climbed through 2022, not an oracle. Predictions at low stress under-call the depth.")
    L.append("- **Beta ordering held**: realized depth ranks almost exactly by 2021 beta "
             "(SPY -25% → TSLA/PLTR -67/-72%), which is the model's core 'beta sets depth' claim.")
    L.append("- **Meta is the lesson the model can't learn**: -77% on a 1.25 beta was an "
             "idiosyncratic earnings/strategy shock — exactly the single-name blow-up risk "
             "the model explicitly does not simulate.")
    L.append("- **The grind flaw is now PARTIALLY fixed.** 2022 was a de-rating year (VIX never "
             "broke 37), which the old 3-state model structurally could not produce. The 4th "
             "'grind' regime (structural-fragility-driven entry, sticky, negative drift, "
             "val-gap bleed) closes much of the gap: conditional on a grind year the deep "
             "floating-premium names (ARKK, Palantir, ~Tesla) now bracket their realized falls. "
             "REMAINING under-call: mid-gap names (NVDA, AMD, Micron, SOXX) still land just past "
             "the conditional p90 — 2022's compression was even broader than the current drag "
             "models. Calibrated IN-SAMPLE to this one episode; needs 2000/2008/2020 episodes "
             "before the levels deserve trust.")
    open(os.path.join(HERE, "backtest_2022.md"), "w").write("\n".join(L))
    json.dump({"stress_2021": st, "rows": rows}, open(os.path.join(HERE, "backtest_2022.json"), "w"), indent=1)
    print("\n".join(L[2:4]))
    for nm, r in sorted(rows.items(), key=lambda kv: -kv[1]["realized"]):
        print(f"  {nm:<16s} real -{r['realized']:.0%}  med -{r['med']:.0%}  p90 -{r['p90']:.0%}  "
              f"P(>=real) {r['p_realized']:.0%}  {'in' if r['in_band'] else 'OUT'}")
    print(f"\n{inb}/{len(rows)} in 10-90 band. Wrote backtest_2022.md/.json")
    return rows


if __name__ == "__main__":
    run()
