"""
============================================================================
 CORRELATION  --  systemic_model
============================================================================
 The portfolio / contagion layer. The per-name model shares one market factor
 but treats each name's idiosyncratic shock as INDEPENDENT — so it understates
 how tightly this universe moves together. This module adds a shared SUB-FACTOR
 per group (AI-infra, AI-platform, defensive), so names in the same complex
 fall together, and measures the thing that actually changes: JOINT / basket
 risk and how concentrated the bet really is.

 KEY IDEA (why per-name numbers don't move): a name's idiosyncratic variance is
 split into a group-shared part and a private part of the SAME total size. Its
 own volatility — and thus its standalone drawdown — is unchanged. What changes
 is co-movement: P(the whole basket craters at once) and the "effective number
 of independent bets."

 ETF POINT: a specialized ETF (SMH, SOXX, DRAM, CHAT, ...) is, by design, a
 basket of the SAME correlated names — so it loads on its group sub-factor and
 earns almost no diversification. The report flags how nearly identical an ETF
 is to its lead constituent.

 RESEARCH MODEL, NOT INVESTMENT ADVICE.
============================================================================
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "discovery"))

import calibration as C
import engine as E
import tam_bridge as TB

# group -> intra-group idiosyncratic correlation (the EXTRA co-movement beyond
# the shared market factor). AI complex is tightly coupled (shared AI-capex
# cycle); megacap platforms less so; mature/defensive least.
GROUP_RHO = C.GROUP_RHO   # canonical home: calibration.py
GROUP = C.GROUP

DT = 1.0 / 252.0
HZ = 378  # 18 months


def _ensure_universe():
    new, _ = TB.build_company_universe(base_companies=C.COMPANIES, verbose=False)
    for nm, spec in new.items():
        C.COMPANIES.setdefault(nm, spec)


def _specs(names):
    dec = E.decompose_premium()
    # pass name=nm so each spec carries its REAL group, ETF idio, crash-growth recovery
    # shift, grind_drag, buyback, and solvency/dilution gates -- without the name,
    # company_to_spec collapses every name to group="defensive", idio=0.11, and skips
    # crash-growth (the same staleness GPT caught in the dominance sweep). (Gemini bug A.)
    return {nm: E.company_to_spec(dec[nm], name=nm) for nm in names if nm in dec}


def simulate(names, n_paths=20000, group_corr=True, seed=None):
    """Jointly simulate `names`; return per-name 18m max drawdowns and the
    equal-weight basket's 18m max drawdown, all on the SAME paths.

    Routes through engine._price_path so the joint sim uses the SAME v3 mechanics
    as the main run: crisis-spiking intra-group correlation (rho->0.92 in panic),
    crisis-only tail widening (tail_mult), de-rating grind multiple-compression
    bleed (grind_drag), and the buyback/solvency channels. Previously this module
    hand-rebuilt the price path and silently omitted all of those, structurally
    UNDERSTATING joint tail risk for fragile names. (Gemini bug A.)

    The basket is equal-weighted on PRICE paths (a buy-and-hold basket) rather than
    by summing daily returns, which avoids the daily-rebalancing volatility drag."""
    specs = _specs(names)
    names = [n for n in names if n in specs]
    rng = np.random.default_rng(seed if seed is not None else C.SIM["seed"])
    CH = C.SIM["chunk"]
    name_mdd = {nm: [] for nm in names}
    port_mdd = []
    done = 0
    while done < n_paths:
        n = min(CH, n_paths - done)
        factor, crisis, grind = E._simulate_factor(rng, n, HZ, return_grind=True)
        # shared group sub-factors -> cross-name contagion (the common stream that
        # _price_path spikes toward rho_max in the crisis/grind states)
        subfactors = ({g: rng.standard_normal((n, HZ)) for g in GROUP_RHO}
                      if group_corr else None)
        port_price = np.zeros((n, HZ))
        for nm in names:
            s = specs[nm]
            price = E._price_path(rng, factor, crisis, s, n, HZ,
                                  tail_mult=s.get("tail_mult", 1.0),
                                  subfactors=subfactors, grind=grind)
            peak = np.maximum.accumulate(price, axis=1)
            name_mdd[nm].append((price / peak - 1).min(axis=1))
            port_price += price / len(names)
        ppeak = np.maximum.accumulate(port_price, axis=1)
        port_mdd.append((port_price / ppeak - 1).min(axis=1))
        done += n
    name_mdd = {nm: np.concatenate(v) for nm, v in name_mdd.items()}
    return name_mdd, np.concatenate(port_mdd)


def basket_terminal(weights, n_paths=8000, seed=None):
    """Weighted-basket P(never) using the CANONICAL definition (P(never recover | drawdown>DEPTH),
    via E._drawdown_and_recovery + E.recovery_curve on the weighted portfolio price path) -- so it
    is apples-to-apples with single-name / real-ETF P(never). Same joint-sim machinery as simulate()
    (crisis-spiking rho, tail widening, grind). RESEARCH MODEL -- NOT INVESTMENT ADVICE."""
    names = [n for n in weights if n in _specs(list(weights))]
    specs = _specs(names)
    names = [n for n in names if n in specs]
    if not names:
        return {"error": "no priceable names"}
    tot = sum(weights[n] for n in names) or 1.0
    w = {n: weights[n] / tot for n in names}
    DEPTH = getattr(E, "DEPTH", getattr(C, "DEPTH", 0.25))
    DAYS = C.SIM["days"]; CH = C.SIM["chunk"]
    rng = np.random.default_rng(seed if seed is not None else C.SIM["seed"])
    mdds, recs, name_mdd, done = [], [], {nm: [] for nm in names}, 0
    while done < n_paths:
        n = min(CH, n_paths - done)
        factor, crisis, grind = E._simulate_factor(rng, n, DAYS, return_grind=True)
        freeze = E._systemic_freeze(factor, DAYS)
        sub = {g: rng.standard_normal((n, DAYS)) for g in GROUP_RHO}
        port_price = np.zeros((n, DAYS))
        for nm in names:
            s = specs[nm]
            price = E._price_path(rng, factor, crisis, s, n, DAYS,
                                  tail_mult=s.get("tail_mult", 1.0), subfactors=sub, grind=grind)
            port_price += w[nm] * (price / price[:, [0]])     # weighted portfolio index, start=1.0
            pk = np.maximum.accumulate(price, axis=1)
            name_mdd[nm].append((price / pk - 1).min(axis=1))
        mdd, rec = E._drawdown_and_recovery(port_price, 378, path_offset=done, freeze=freeze)
        mdds.append(mdd); recs.append(rec); done += n
    mdd = np.concatenate(mdds); rec = np.concatenate(recs)
    rc = E.recovery_curve(mdd, rec, DEPTH)
    name_mdd = {nm: np.concatenate(v) for nm, v in name_mdd.items()}
    if len(names) < 2:
        rho, neff = float("nan"), 1.0
    else:
        rho, neff, _ = _avg_corr_and_neff(name_mdd, names)
    return {"p_never": rc["p_never"],                          # canonical: P(never | DD>DEPTH)
            "p_fall_25pct": float((mdd <= -DEPTH).mean()),
            "correlation_adjusted_effN": (round(neff, 1) if neff == neff else 1.0),
            "avg_crisis_correlation": (round(rho, 2) if rho == rho else None),
            "n_names": len(names)}


def _avg_corr_and_neff(name_mdd, names):
    M = np.vstack([name_mdd[nm] for nm in names])
    cm = np.corrcoef(M)
    off = cm[np.triu_indices(len(names), 1)]
    rho_bar = float(np.nanmean(off))
    n = len(names)
    neff = n / (1 + (n - 1) * max(rho_bar, 0))
    return rho_bar, neff, cm


def basket_report(names, label, n_paths=20000):
    nm_g, port_g = simulate(names, n_paths, group_corr=True)
    nm_i, port_i = simulate(names, n_paths, group_corr=False)
    rho_g, neff_g, _ = _avg_corr_and_neff(nm_g, [n for n in names if n in nm_g])
    rho_i, neff_i, _ = _avg_corr_and_neff(nm_i, [n for n in names if n in nm_i])
    out = dict(
        label=label, n=len([n for n in names if n in nm_g]),
        rho_with=round(rho_g, 2), neff_with=round(neff_g, 1),
        rho_indep=round(rho_i, 2), neff_indep=round(neff_i, 1),
        port_dd25_with=float((port_g <= -0.25).mean()),
        port_dd25_indep=float((port_i <= -0.25).mean()),
        port_dd35_with=float((port_g <= -0.35).mean()),
        port_dd35_indep=float((port_i <= -0.35).mean()),
    )
    return out


def etf_vs_lead(etf, lead, n_paths=20000):
    """Correlation between a specialized ETF and its lead constituent."""
    nm, _ = simulate([etf, lead], n_paths, group_corr=True)
    if etf not in nm or lead not in nm:
        return None
    return float(np.corrcoef(nm[etf], nm[lead])[0, 1])


def run(n_paths=20000):
    _ensure_universe()
    import tiering as T
    allnames = [n for n in T.UNIVERSE if n in C.COMPANIES]
    tier1 = [n for n, (k, th, g) in T.UNIVERSE.items() if g > 0.40 and n in C.COMPANIES]

    print("#" * 74)
    print("#  CORRELATION / CONCENTRATION  --  is this universe really many bets?")
    print("#  per-name drawdowns are UNCHANGED; this is the JOINT picture.")
    print("#" * 74)

    grp_counts = {}
    for n in allnames:
        grp_counts[GROUP.get(n, "?")] = grp_counts.get(GROUP.get(n, "?"), 0) + 1
    print("\nGroups (shared sub-factor):")
    for g, c in sorted(grp_counts.items(), key=lambda x: -x[1]):
        print(f"  {g:12s} {c:2d} names   (intra-group idiosyncratic corr rho={GROUP_RHO.get(g,0):.2f})")

    reports = []
    for names, lbl in [(allnames, "Whole universe (equal-weight)"),
                       (tier1, "Tier-1 high-growth basket")]:
        r = basket_report(names, lbl, n_paths)
        reports.append(r)
        print("\n" + "=" * 74)
        print(f"{lbl}  ({r['n']} names)")
        print("=" * 74)
        print(f"  effective independent bets:  {r['neff_with']:.1f}   "
              f"(naive / independent-idio view would say {r['neff_indep']:.1f})")
        print(f"  avg pairwise correlation:    {r['rho_with']:.2f}   "
              f"(vs {r['rho_indep']:.2f} if idio were independent)")
        print(f"  P(equal-weight basket falls >25% in 18m):  "
              f"{r['port_dd25_with']*100:4.0f}%   "
              f"(model-without-sector-corr: {r['port_dd25_indep']*100:.0f}%)")
        print(f"  P(basket falls >35%):                      "
              f"{r['port_dd35_with']*100:4.0f}%   "
              f"(without: {r['port_dd35_indep']*100:.0f}%)")

    # ETF vs lead constituent
    print("\n" + "=" * 74)
    print("SPECIALIZED ETF ≈ ITS CONSTITUENTS  (diversification is largely illusory)")
    print("=" * 74)
    pairs = [("SMH (VanEck Semis)", "NVIDIA"), ("SOXX (iShares Semis)", "Micron"),
             ("DRAM (Roundhill Memory)", "Micron"), ("CHAT (Roundhill GenAI)", "NVIDIA")]
    etf_corr = {}
    for etf, lead in pairs:
        c = etf_vs_lead(etf, lead, n_paths)
        if c is not None:
            etf_corr[etf] = dict(lead=lead, corr=round(c, 2))
            print(f"  {etf:26s} vs {lead:10s}  correlation {c:.2f}")

    out = dict(groups=grp_counts, group_rho=GROUP_RHO, baskets=reports, etf_corr=etf_corr)
    with open(os.path.join(HERE, "correlation_report.json"), "w") as f:
        json.dump(out, f, indent=1, default=float)
    print("\n  Takeaway: the headline 'effective bets' is far below the name count —")
    print("  this list is mostly ONE bet (the AI-capex cycle). Sizing to the name")
    print("  count, or trusting a specialized ETF to diversify, overstates safety.")
    print("Saved correlation_report.json")
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", type=int, default=20000)
    ap.parse_args()
    run(ap.parse_args().paths)
