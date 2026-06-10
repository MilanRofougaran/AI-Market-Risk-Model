"""
============================================================================
 VALUATION_LINK -- SAM + short interest -> valuation gap -> price risk
============================================================================
 HOW VALUATION AND PRICE CONNECT IN THIS MODEL (stocks):

   1. The market pays a PREMIUM multiple over the base market multiple.
   2. The JUSTIFIED part of that premium is what the TAM runway supports.
      The base model justified it against TAM (the long-run ceiling).
      This module re-justifies it against SAM -- the market the company can
      serve in the next 2-3 years -- blended 60% SAM / 40% TAM, because
      near-term price must be earned in the serviceable market first.
   3. What's left is FLOATING premium: priced hope. val_gap = floating
      premium as a share of the whole multiple = the % of today's PRICE
      that is not supported by the serviceable runway.
   4. In a stress regime the floating premium evaporates FIRST (depth),
      and a name must regrow into its SAM to recover (speed). So val_gap
      raises crisis-only fragility; it does not change calm-market behavior.
   5. SHORT INTEREST (crowding) amplifies crisis depth (forced unwinds hit
      crowded names hardest) and adds a small early-recovery kick (covering).

 For ETFs: every quantity is the holdings-weighted aggregate (an ETF's
 valuation gap IS its holdings' gap); sector ETFs get a small hedge-flow
 cushion (they are shorted as hedges, which is stabilizing, not crowding).

 Output: valuation_report.json / .md -- per name: fwd P/E, justified P/E
 (SAM-blended), val_gap, SI, crowd, and adjusted P(>25/40% fall) vs base.

 RESEARCH MODEL, NOT INVESTMENT ADVICE.
============================================================================
"""
import json, os, sys, zlib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "discovery"))

import calibration as C
import engine as E
import extension_data as X
import tam_bridge as TB


def sam_decompose():
    """Re-run the premium decomposition with SAM-blended runway."""
    new, _ = TB.build_company_universe(base_companies=C.COMPANIES, verbose=False)
    for k, v in new.items():
        C.COMPANIES.setdefault(k, v)
    decomp = E.decompose_premium()
    out = {}
    for nm, o in decomp.items():
        sam_frac, si = X.get(nm)
        pen_tam = o["pen"]
        pen_sam = min(o["rev_bn"] / max(o["tam_bn"] * sam_frac, 1e-9), 1.0)
        # runway against SAM scales with remaining SAM headroom
        shrink = (1.0 - pen_sam) / max(1.0 - pen_tam, 1e-9)
        shrink = max(0.0, min(shrink, 1.0))
        runway_eff = o["runway_norm"] * (0.6 * shrink + 0.4)      # 60% SAM / 40% TAM
        justified_eff = o["justified_pts"] * (runway_eff / max(o["runway_norm"], 1e-9))
        floating_eff = max(o["premium_pts"] - justified_eff, 0.0)
        val_gap = floating_eff / max(o["fwd_pe"], 1e-9)            # % of price = hope
        val_gap_base = o["unsupported_pts"] / max(o["fwd_pe"], 1e-9)
        crowd = X.crowd_score(si)
        bal = X.balance(nm)
        # crisis-only adjustments (bounded, additive to the base channels)
        frag_adj = min(1.0, o["fragility"] + 0.45 * max(val_gap - val_gap_base, 0.0)
                       + 0.20 * crowd)
        out[nm] = dict(o, pen_sam=pen_sam, sam_frac=sam_frac, si=si, crowd=crowd, balance=bal,
                       justified_eff=justified_eff, floating_eff=floating_eff,
                       val_gap=val_gap, val_gap_base=val_gap_base,
                       fragility_adj=frag_adj)
    return out


def spec_adjusted(o, name=None):
    """company_to_spec (name-resolved, so it carries group/ETF-idio/grind/buyback/
    solvency/dilution) with SAM/SI-adjusted crisis channels layered on top."""
    s = E.company_to_spec(o, name=name)
    base_recov = s["recov_shift"]   # already includes the crash-growth recovery term
    s["tail_mult"] = 1.0 + 0.5 * o["fragility_adj"] + 0.30 * o["crowd"]
    # rebuild recov_shift from the SAM/SI-adjusted fragility, but PRESERVE the crash-
    # growth contribution that company_to_spec folded in (base_recov minus its own
    # fragility/recovery_quality terms == the crash-growth delta).
    cg_delta = base_recov - (0.30 * o["recovery_quality"] - 0.25 * o["fragility"])
    s["recov_shift"] = (0.30 * o["recovery_quality"] - 0.25 * o["fragility_adj"]
                        + 0.05 * o["crowd"]                       # covering kick
                        + 0.24 * (o.get("balance", 0.55) - 0.55)  # cash powers the climb-back
                        + cg_delta)                               # keep crash-growth recovery
    return s


def crisis_amp(o):
    """Crisis-only beta amplification: forced unwinds hit crowded names (SI)
    and floating premium evaporates first (val_gap). Calm regimes unchanged —
    this is why the effect belongs in crisis beta, not the small idio channel."""
    return 0.20 * o["crowd"] + 0.30 * max(o["val_gap"] - 0.30, 0.0)


def _price_path_amped(seed, factor, crisis, spec, n, days, amp):
    """Like engine._price_path but with crisis-conditional beta. Fixed seed so
    base and adjusted runs see identical idio draws (clean delta)."""
    rng = np.random.default_rng(seed)
    dt = 1.0 / 252.0
    idio = rng.standard_normal((n, days)) * (spec["idio"] * np.sqrt(dt))
    idio = idio * (1 + (spec["tail_mult"] - 1) * crisis)
    beta_t = spec["beta"] * (1 + amp * crisis)
    daily = beta_t * factor + spec.get("mu", 0.0) * dt + idio
    return np.exp(np.cumsum(daily, axis=1))


def run(n_paths=8000, verbose=True):
    decomp = sam_decompose()
    rng = np.random.default_rng(C.SIM["seed"] + 7)
    days = C.SIM["days"]; hd18 = C.HORIZON_DAYS[C.HORIZON_LABELS.index("18m")]
    names = list(decomp.keys())
    res = {}
    # route through the SAME engine path as the main run (Gemini bug A / GPT review): shared
    # macro factor + group sub-factors (crisis-spiking contagion) + de-rating grind, so the
    # overlay's probabilities are directly comparable to the main model rather than a
    # simplified stand-alone path.
    factor, crisis, grind = E._simulate_factor(rng, n_paths, days, return_grind=True)
    groups = list(getattr(C, "GROUP_RHO", {}).keys())
    subfactors = {g: rng.standard_normal((n_paths, days)) for g in groups}
    freeze = E._systemic_freeze(factor, days)            # systemic-freeze recovery contagion
    for nm in names:
        o = decomp[nm]
        rows = {}
        amp = crisis_amp(o)
        for label, spec, a in (("base", E.company_to_spec(o, name=nm), 0.0),
                               ("adj", spec_adjusted(o, name=nm), amp)):
            # name-seeded deterministically (crc32, NOT Python hash() which is per-session
            # randomized) so the base-vs-adj A/B deltas are reproducible run-over-run and
            # order-invariant. Re-seed per label so base and adj see IDENTICAL private
            # shocks -> the delta isolates the SAM/SI adjustment. (Gemini bug C.)
            seed_val = (C.SIM["seed"] ^ (zlib.crc32(nm.encode()) & 0xFFFFFFFF)) & 0xFFFFFFFF
            name_rng = np.random.default_rng(seed_val)
            price = E._price_path(name_rng, factor, crisis, spec, n_paths, days,
                                  tail_mult=spec["tail_mult"], subfactors=subfactors,
                                  grind=grind, idio_rng=name_rng, beta_amp=a)
            mdd, rec = E._drawdown_and_recovery(price, hd18, recov_shift=spec["recov_shift"],
                                                bb=spec.get("bb"), solv=spec.get("solv"),
                                                dilution=spec.get("dilution"), cycle=spec.get("cycle"),
                                                freeze=freeze, freeze_dep=spec.get("freeze_dep", 1.0))
            ex = E.exceedance(mdd, (0.25, 0.40))
            rc = E.recovery_curve(mdd, rec, 0.25)
            rows[label] = dict(p25=float(ex[0]), p40=float(ex[1]),
                               perm=float(ex[0]) * float(rc.get("p_never") or 0.0))
        bal_v = o.get("balance", 0.55)
        res[nm] = dict(fwd_pe=o["fwd_pe"], justified_pe_sam=round(o["justified_eff"], 1),
                       val_gap=round(o["val_gap"], 3), val_gap_tam=round(o["val_gap_base"], 3),
                       pen_sam=round(o["pen_sam"], 3), pen_tam=round(o["pen"], 3),
                       si=o["si"], crowd=round(o["crowd"], 2),
                       balance=bal_v,
                       p25_base=round(rows["base"]["p25"], 3), p25_adj=round(rows["adj"]["p25"], 3),
                       p40_base=round(rows["base"]["p40"], 3), p40_adj=round(rows["adj"]["p40"], 3),
                       perm_base=round(rows["base"]["perm"], 3), perm_adj=round(rows["adj"]["perm"], 3))
        if verbose:
            print(f"  {nm:<26s} gap {res[nm]['val_gap']:.0%} (tam-based {res[nm]['val_gap_tam']:.0%}) "
                  f"si {o['si']:.1%}  P>25 {rows['base']['p25']:.0%}->{rows['adj']['p25']:.0%}  "
                  f"P>40 {rows['base']['p40']:.0%}->{rows['adj']['p40']:.0%}")

    # ---- ETF aggregation (holdings-weighted) ----
    etfs = {}
    for etf, holds in TB.ETF_HOLDINGS.items():
        items = [(h, w) for h, w in holds.items() if not h.startswith("_")]
        tot = sum(w for _, w in items) or 1.0
        acc = dict(val_gap=0., si=0., pen_sam=0.)
        used = 0.
        for hname, w in items:
            m = next((res[k] for k in res if k.split(' (')[0].lower() == hname.split(' (')[0].lower()), None)
            if m:
                for f in acc: acc[f] += m[f] * w
                used += w
        if used > 0.3:
            for f in acc: acc[f] = round(acc[f] / used, 3)
            hedge = X.ETF_HEDGE_SI.get(etf.split(' ')[0], 0.0)
            etfs[etf] = dict(acc, coverage=round(used / tot, 2), hedge_si=hedge,
                             note="holdings-weighted; hedge SI cushions, not amplifies")
    out = {"stocks": res, "etfs": etfs,
           "method": "val_gap = floating premium share of price, SAM-blended (60/40); "
                     "crisis-only: tail_mult += 0.45*(gap-sam_minus_tam)+0.20*crowd"}
    json.dump(out, open(os.path.join(HERE, "valuation_report.json"), "w"), indent=1)

    # markdown table
    L = ["# Valuation–price linkage (SAM + short interest overlay)",
         "\n*How much of each price is serviceable-market-supported vs floating hope, "
         "and what crowding does to crisis depth. Estimates — refresh like MACRO. "
         "Research model, not investment advice.*",
         "\n| Name | fwd P/E | justified (SAM) | val gap | SI | balance | P>25 base→adj | P>40 base→adj | perm base→adj |",
         "|---|--:|--:|--:|--:|--:|---|---|---|"]
    for nm, m in sorted(res.items(), key=lambda kv: -kv[1]["val_gap"]):
        L.append(f"| {nm} | {m['fwd_pe']} | {m['justified_pe_sam']} | {m['val_gap']:.0%} "
                 f"| {m['si']:.1%} | {m['balance']:.2f} | {m['p25_base']:.0%}→{m['p25_adj']:.0%} "
                 f"| {m['p40_base']:.0%}→{m['p40_adj']:.0%} "
                 f"| {m['perm_base']:.0%}→{m['perm_adj']:.0%} |")
    L.append("\n## ETFs (holdings-weighted)")
    L.append("\n| ETF | val gap | holdings SI | hedge SI | coverage |")
    L.append("|---|--:|--:|--:|--:|")
    for etf, m in sorted(etfs.items(), key=lambda kv: -kv[1]["val_gap"]):
        L.append(f"| {etf} | {m['val_gap']:.0%} | {m['si']:.1%} | {m['hedge_si']:.0%} | {m['coverage']:.0%} |")
    open(os.path.join(HERE, "valuation_report.md"), "w").write("\n".join(L))
    if verbose:
        print("  wrote valuation_report.json / .md")
    return out


if __name__ == "__main__":
    run()
