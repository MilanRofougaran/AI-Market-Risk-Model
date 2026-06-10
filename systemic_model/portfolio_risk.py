"""
============================================================================
 PORTFOLIO_RISK -- joint risk for custom weighted portfolios
============================================================================
 Because the engine now natively simulates sub-factor contagion (shared
 sector shocks blended into each name's idiosyncratic noise, variance-
 preserving), a weighted portfolio's JOINT drawdown is finally honest:
 names in the same group cascade together on bad sector paths.

 Usage:
   python3 portfolio_risk.py                      # runs the demo comparisons
   from portfolio_risk import analyze_portfolio
   analyze_portfolio({"NVIDIA": 0.4, "SCHD (Dividend)": 0.6}, "My mix")

 RESEARCH MODEL, NOT INVESTMENT ADVICE.
============================================================================
"""
import os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "discovery"))

import calibration as C
import engine as E
import tam_bridge as TB


def _ensure_universe():
    new, _ = TB.build_company_universe(base_companies=C.COMPANIES, verbose=False)
    for nm, spec in new.items():
        C.COMPANIES.setdefault(nm, spec)


def analyze_portfolio(weights, name="Custom Allocation", n_paths=20000, quiet=False):
    _ensure_universe()
    decomp = E.decompose_premium()
    total_w = sum(weights.values())
    w = {nm: v / total_w for nm, v in weights.items()}
    names = [nm for nm in w if nm in decomp]
    missing = [nm for nm in w if nm not in decomp]
    if missing:
        for nm in missing:
            print(f"  WARNING: {nm} not in modeled universe -- dropped & weights renormalized")
        # AUTO-RENORMALIZE over the valid names (Gemini review): otherwise the missing weight
        # is silently held as a 0%-return 'cash' sleeve, damping the drawdown and flattering risk.
        _wsum = sum(w[nm] for nm in names)
        if _wsum > 0:
            w = {nm: w[nm] / _wsum for nm in names}

    rng = np.random.default_rng(C.SIM["seed"])
    CH, DAYS = C.SIM["chunk"], C.SIM["days"]
    hd18 = C.HORIZON_DAYS[C.HORIZON_LABELS.index("18m")]
    groups = list(getattr(C, "GROUP_RHO", {}).keys())

    mdds, recs = [], []
    done = 0
    while done < n_paths:
        n = min(CH, n_paths - done)
        factor, crisis, grind = E._simulate_factor(rng, n, DAYS, return_grind=True)
        subfactors = {g: rng.standard_normal((n, DAYS)) for g in groups}
        freeze = E._systemic_freeze(factor, DAYS)        # systemic-freeze recovery contagion
        # portfolio freeze dependency = weighted average of holdings' keystone dependence
        port_fdep = sum(w[nm] * E.company_to_spec(decomp[nm], name=nm).get("freeze_dep", 1.0)
                        for nm in names) or 1.0
        port_daily = np.zeros((n, DAYS))
        for nm in names:
            spec = E.company_to_spec(decomp[nm], name=nm)
            # pass grind so the de-rating-regime multiple-compression bleed (grind_drag)
            # is applied here too, matching the main run (Gemini bug A / polish).
            price = E._price_path(rng, factor, crisis, spec, n, DAYS,
                                  tail_mult=spec["tail_mult"], subfactors=subfactors,
                                  grind=grind)
            daily = np.concatenate([price[:, :1] - 1.0,
                                    price[:, 1:] / price[:, :-1] - 1.0], axis=1)
            port_daily += w[nm] * daily
        port_price = np.cumprod(1 + port_daily, axis=1)
        port_shift = sum(w[nm] * E.company_to_spec(decomp[nm], name=nm)["recov_shift"]
                         for nm in names)
        mdd, rec = E._drawdown_and_recovery(port_price, hd18, recov_shift=port_shift,
                                            freeze=freeze, freeze_dep=port_fdep)
        mdds.append(mdd); recs.append(rec)
        done += n

    mdd = np.concatenate(mdds); rec = np.concatenate(recs)
    rc = E.recovery_curve(mdd, rec, 0.25)
    p25 = float((mdd <= -0.25).mean()); p35 = float((mdd <= -0.35).mean())
    p40 = float((mdd <= -0.40).mean())
    p_never = float(rc.get("p_never") or 0.0)

    lines = ["", "=" * 70, f"PORTFOLIO  --  {name}", "=" * 70]
    for nm, wv in sorted(w.items(), key=lambda x: -x[1]):
        grp = getattr(C, "GROUP", {}).get(nm, "defensive")
        lines.append(f"  {wv*100:4.1f}%  {nm:<28s} [{grp}]")
    gset = {getattr(C, "GROUP", {}).get(nm, "defensive") for nm in names}
    lines += [f"\n  Joint drawdown (18m): P(>25%) {p25:.0%}   P(>35%) {p35:.0%}   P(>40%) {p40:.0%}",
              f"  Permanent risk: >3y tail (cond.) {p_never:.0%}   "
              f"true permanent (uncond.) {p25 * p_never:.1%}",
              f"  Groups held: {len(gset)} of 4 ({', '.join(sorted(gset))})",
              # HONEST SCOPE (GPT review): this is a DAILY-REBALANCED joint-drawdown /
              # contagion simulation (weighted sum of daily returns). It captures the joint
              # path -- crisis-spiking correlation, tail widening, grind -- but it does NOT
              # aggregate each holding's PATH-SPECIFIC permanent events (solvency impairment,
              # toxic dilution, trough buyback) into the portfolio recovery tail. A single
              # fragile holding can permanently impair while the basket partially recovers,
              # so the portfolio permanent-tail here can UNDERSTATE name-level blow-up risk.
              "  NOTE: daily-rebalanced joint-drawdown; per-name permanent impairment not aggregated.",
              "=" * 70]
    txt = "\n".join(lines)
    if not quiet:
        print(txt)
    return dict(name=name, p25=p25, p35=p35, p40=p40, p_never=p_never,
                true_perm=p25 * p_never, text=txt)


if __name__ == "__main__":
    r1 = analyze_portfolio({"NVIDIA": 0.40, "Broadcom": 0.30, "Micron": 0.30},
                           "Concentrated AI-infra (3 names, 1 group)")
    r2 = analyze_portfolio({"NVIDIA": 0.34, "Microsoft": 0.33, "Amazon": 0.33},
                           "Cross-group tech (infra + platform)")
    r3 = analyze_portfolio({"NVIDIA": 0.25, "Microsoft": 0.25,
                            "SCHD (Dividend)": 0.30, "Tesla": 0.20},
                           "Four-group mix (incl. defensive)")
    with open(os.path.join(HERE, "portfolio_risk_demo.md"), "w") as f:
        f.write("# Portfolio joint-risk demos (native contagion engine)\n```"
                + r1["text"] + r2["text"] + r3["text"] + "\n```\n"
                "\nSame-group names cascade together (shared sector shock, rho=0.55 "
                "for AI-infra); cross-group mixes genuinely diversify the idiosyncratic "
                "layer -- but ALL names still share the macro factor, so no mix escapes "
                "a systemic event. Research model, not investment advice.\n")
    print("\nwrote portfolio_risk_demo.md")
