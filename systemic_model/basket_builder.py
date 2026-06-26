"""
basket_builder.py -- build your OWN basket from names the model already analyzes, and
evaluate it as ONE object (a self-constructed ETF), for stocks AND for option structures.

WHY THIS IS THE MODEL'S CLEANEST FORM: an existing ETF forces the model to reverse-engineer a
black box (QTUM = 16% coverage). A self-built basket is 100% coverage by construction -- every
constituent already has a tier, premium decomposition, fragility, balance, and impairment. So
this aggregates analysis you already trust instead of guessing holdings.

WHAT IT OPTIMIZES: risk + value -- it can tilt weight toward low-fragility / low-floating-premium
names, and it reports the DISTRIBUTION across holdings (fragility dispersion, weak-tail weight,
premium concentration), not just the weighted mean. Two baskets with identical average fragility
behave differently if one is bimodal; the mean hides the tail, so this surfaces the tail.

WHAT IT WILL NOT DO (by design, same discipline as the rest of the model):
  - It does NOT optimize for return / find the "best" weights by historical performance. That
    needs P&L data the model doesn't have and would overfit one realized path -> false precision.
  - It does NOT claim the basket is diversified when it isn't. It REPORTS effective-N and the
    correlation reality (the AI/semi universe is ~1 effective bet in a panic) and lets you decide.
  - It does NOT size your positions or place orders.
RESEARCH MODEL -- NOT INVESTMENT ADVICE.
"""
import os, sys, json, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "discovery"))
import calibration as C, engine as E, extension_data as X, solvency as SV
import etf_lens as EL


def _universe():
    """All priceable names with their model analysis (floating, fragility, cyc, balance, impair)."""
    import tam_bridge as TB
    new, _ = TB.build_company_universe(base_companies=C.COMPANIES, verbose=False)
    for k, v in new.items():
        C.COMPANIES.setdefault(k, v)
    d = E.decompose_premium()
    # try to attach P(never) from a prior run if present
    pnever = {}
    try:
        R = json.load(open(os.path.join(HERE, "results.json")))
        rc = R.get("companies", {}).get("recovery_cond", {})
        pnever = {n: rc[n].get("p_never") for n in rc}
    except Exception:
        pass
    uni = {}
    for n, dd in d.items():
        uni[n] = dict(floating=dd.get("unsupported_frac", 0.0),
                      fragility=dd.get("fragility", 0.0),
                      cyclicality=dd.get("earnings_cyclicality", 0.0),
                      balance=X.balance(n) if hasattr(X, "balance") else None,
                      impairment=SV._stock_impairment(n) if hasattr(SV, "_stock_impairment") else None,
                      p_never=pnever.get(n))
    return uni


AI_SEMI_THEME = {"NVIDIA", "AMD", "Broadcom", "Marvell", "ARM", "Qualcomm", "Micron", "Kioxia",
                 "Astera Labs", "CoreWeave", "Palantir"}   # the canonical AI/Semi thematic universe


def select(uni, tier=None, max_pnever=None, max_floating=None, max_fragility=None, names=None, theme=None):
    """Filter the universe by the model's own gates -> a candidate set. theme='AI/Semi' restricts to
    the canonical AI/Semi thematic names (so a themed basket is distinct from ALL-model Tier 1, which
    also includes names like Microsoft/Meta/Cisco/SCHD). (GPT audit #5: label/scope clarity.)"""
    if names:
        return [n for n in names if n in uni]
    import tier_gate
    tg = tier_gate.run() if tier is not None else {}
    themeset = AI_SEMI_THEME if (theme and "semi" in theme.lower()) else None
    out = []
    for n, v in uni.items():
        if themeset is not None and n not in themeset:
            continue
        if tier is not None:
            t = tg.get(n, {}).get("tier")
            if t is None or int(str(t).split()[0]) > tier:
                continue
        if max_pnever is not None and (v["p_never"] is None or v["p_never"] * 100 > max_pnever):
            continue
        if max_floating is not None and v["floating"] * 100 > max_floating:
            continue
        if max_fragility is not None and v["fragility"] > max_fragility:
            continue
        out.append(n)
    return out


def weight(uni, names, scheme="equal", cap=None):
    """equal | inv_fragility (risk-tilt: robust names get more) | inv_floating (value-tilt)."""
    if not names:
        return {}
    if scheme == "equal":
        raw = {n: 1.0 for n in names}
    elif scheme == "inv_fragility":
        raw = {n: 1.0 / max(0.05, uni[n]["fragility"]) for n in names}
    elif scheme == "inv_floating":
        raw = {n: 1.0 / max(0.02, uni[n]["floating"] + 0.02) for n in names}
    else:
        raise ValueError("scheme must be equal | inv_fragility | inv_floating")
    tot = sum(raw.values())
    w = {n: raw[n] / tot for n in names}
    if cap:                                   # cap any single name, redistribute
        for _ in range(50):
            over = {n: x for n, x in w.items() if x > cap}
            if not over:
                break
            excess = sum(x - cap for x in over.values())
            for n in over:
                w[n] = cap
            room = [n for n in w if w[n] < cap]
            add = excess / len(room) if room else 0
            for n in room:
                w[n] += add
            tot = sum(w.values()); w = {n: x / tot for n, x in w.items()}
    return w


def _weighted_stats(uni, w):
    fl = sum(w[n] * uni[n]["floating"] for n in w)              # basket floating premium (overvaluation)
    fr = sum(w[n] * uni[n]["fragility"] for n in w)             # mean fragility
    # fragility DISPERSION (the distribution-aware part): weighted stdev
    var = sum(w[n] * (uni[n]["fragility"] - fr) ** 2 for n in w)
    disp = math.sqrt(max(0.0, var))
    # weak-tail weight: basket weight in fragile/impairment-prone names (a mean can hide this)
    weak = sum(w[n] for n in w if uni[n]["fragility"] >= 0.40 or (uni[n]["impairment"] or 0) > 0.15)
    # premium concentration: share of the basket's floating premium sitting in its single top contributor
    contrib = {n: w[n] * uni[n]["floating"] for n in w}
    tot_fl = sum(contrib.values())
    prem_conc = (max(contrib.values()) / tot_fl) if tot_fl > 0 else 0.0
    return dict(floating=fl, mean_fragility=fr, fragility_dispersion=disp,
                weak_tail_weight=weak, premium_concentration=prem_conc)


def evaluate_stock_basket(uni, w, label="custom basket", corr_paths=4000):
    """Evaluate a self-built equity basket as ONE object: recovery split + effN (etf_lens),
    aggregate over/undervaluation, and the DISTRIBUTION (dispersion, weak-tail, premium concentration).
    Diversification uses the CANONICAL correlation engine (crisis rho->0.92), not weights."""
    sc = EL.scorecard(label, dict(w))          # 100% coverage: all names are model-known
    st = _weighted_stats(uni, w)
    weight_effN = sc["neff"]                    # weight-concentration only (Herfindahl) -- NOT diversification
    n = len(w)
    # REAL diversification: correlation-adjusted effN under the model's crisis correlation
    try:
        import correlation as COR
        br = COR.basket_report(list(w.keys()), label, n_paths=corr_paths)
        corr_effN = br["neff_with"]; rho = br["rho_with"]; port_dd25 = br["port_dd25_with"]
    except Exception:
        corr_effN = rho = port_dd25 = None
    real_div = (corr_effN / n) if (corr_effN and n) else None
    return {
        "label": label, "n_holdings": n, "weights": {k: round(v, 3) for k, v in w.items()},
        "value": {"basket_floating_premium_pct": round(st["floating"] * 100, 1),
                  "premium_concentration": round(st["premium_concentration"], 2),
                  "_read": "floating premium = how much of basket price is unsupported; "
                           "concentration = share of that premium in one name"},
        "risk": {"mean_fragility": round(st["mean_fragility"], 3),
                 "fragility_dispersion": round(st["fragility_dispersion"], 3),
                 "weak_tail_weight": round(st["weak_tail_weight"], 3),
                 "_read": "dispersion + weak-tail are what the mean hides; a bimodal basket impairs "
                          "its weak half in a panic even at a benign average"},
        "recovery": {"fast_weight": sc["fast_weight"], "slow_weight": sc["slow_weight"],
                     "permanent_weight": sc["permanent_weight"],
                     "theme_durability": sc.get("theme_durability"),
                     "fin_resilience": sc.get("fin_resilience")},
        "diversification": {"correlation_adjusted_effN": corr_effN, "n_names": n,
                            "avg_crisis_correlation": rho,
                            "real_diversification_ratio": (round(real_div, 2) if real_div else None),
                            "weight_concentration_effN": weight_effN,
                            "portfolio_p_fall_25pct": (round(port_dd25, 3) if port_dd25 is not None else None),
                            "_read": "correlation_adjusted_effN (crisis rho->0.92) is REAL diversification; "
                                     "weight_concentration_effN only measures weight spread. A pure-theme "
                                     "basket collapses toward effN~1 regardless of name count -- the model "
                                     "REPORTS it; YOU decide if that's acceptable."},
        "disclaimer": "RESEARCH MODEL -- NOT INVESTMENT ADVICE. Risk/value X-ray of the basket, NOT a "
                      "return forecast, NOT a backtested profitability claim, NOT position sizing."}


def evaluate_option_basket(uni, w, tenor_months, label="custom option basket"):
    """Evaluate a basket of (long, net-debit) option structures. KEY CAUTION: long options on
    correlated names do NOT offset in a panic -- they COMPOUND. So the combined tail is worse
    than the average, and the timing risk is shared. Per-name timing via option_timing_overlay."""
    import option_timing_overlay as OTO
    legs = {}
    rejects = []
    for n in w:
        r = OTO.timing_overlay(n, tenor_months, base_p_profit=0.5)
        legs[n] = {"weight": round(w[n], 3), "cyc": r.get("eps_trough_depth"),
                   "timing_status": r.get("timing_status"),
                   "est_recovery_months": r.get("est_recovery_months")}
        if "REJECT" in str(r.get("timing_status", "")):
            rejects.append(n)
    # combined tail: weight in names whose option leg the timing gate rejects + impairment-weighted tail
    rej_w = sum(w[n] for n in rejects)
    imp_tail = sum(w[n] * (uni[n]["impairment"] or 0) for n in w)
    sc = EL.scorecard(label, dict(w)); effN = sc["neff"]
    return {
        "label": label, "tenor_months": tenor_months, "n_legs": len(w), "legs": legs,
        "combined": {"weight_in_timing_rejected_legs": round(rej_w, 3),
                     "impairment_weighted_tail": round(imp_tail, 3),
                     "effective_N": effN,
                     "_caution": "long options on correlated names COMPOUND in a panic (they do not "
                                 "offset). A basket of long calls is a LEVERAGED bet on one factor; "
                                 "the combined tail is worse than the per-leg average."},
        "rejected_legs": rejects,
        "verdict_note": ("CONTAINS TIMING-REJECTED LEGS -- the basket inherits those rejections; "
                         "the model does not net them away." if rejects else
                         "no leg is timing-rejected at this tenor, but the legs still share factor risk"),
        "disclaimer": "RESEARCH MODEL -- NOT INVESTMENT ADVICE. Per-leg timing is the model's own "
                      "estimate (UNVALIDATED axis). Live IV/event/liquidity must still pass broker_bridge. "
                      "No sizing, no order endorsement."}


def _print_stock(ev):
    print(f"\n=== {ev['label']}  ({ev['n_holdings']} holdings) ===")
    print("  weights:", ", ".join(f"{k} {v:.0%}" for k, v in ev["weights"].items()))
    v, r, rec, dv = ev["value"], ev["risk"], ev["recovery"], ev["diversification"]
    print(f"  VALUE   floating premium {v['basket_floating_premium_pct']}%  | premium concentration {v['premium_concentration']}")
    print(f"  RISK    mean fragility {r['mean_fragility']}  dispersion {r['fragility_dispersion']}  weak-tail {r['weak_tail_weight']:.0%}")
    print(f"  RECOVER fast/slow/perm {rec['fast_weight']:.0%}/{rec['slow_weight']:.0%}/{rec['permanent_weight']:.0%}  | theme dur {rec['theme_durability']}")
    ce = dv['correlation_adjusted_effN']; rd = dv['real_diversification_ratio']
    pf = dv['portfolio_p_fall_25pct']
    print(f"  DIVERS  correlation-adj effN {ce} of {dv['n_names']} names (real-div {rd}, rho {dv['avg_crisis_correlation']})"
          f"{f' | portfolio P(fall25%) {pf:.0%}' if pf is not None else ''}  <- REAL diversification, not weights")


if __name__ == "__main__":
    uni = _universe()
    print("BASKET BUILDER -- self-constructed ETFs from analyzed names (100% coverage)")
    print("Risk+value weighting; effective-N and tail REPORTED, you decide. NOT INVESTMENT ADVICE.")

    # Example A: ALL-MODEL Tier-1 equal-weight (incl. non-semis like MSFT/Meta/Cisco/SCHD)
    t1 = select(uni, tier=1)
    if t1:
        _print_stock(evaluate_stock_basket(uni, weight(uni, t1, "equal"), "All-model Tier-1 equal-weight"))
    # Example A2: canonical AI/SEMI Tier-1 only (NVIDIA/Qualcomm/AMD/Marvell) -- the thematic four
    t1_semi = select(uni, tier=1, theme="AI/Semi")
    if t1_semi:
        _print_stock(evaluate_stock_basket(uni, weight(uni, t1_semi, "equal"), "AI/Semi Tier-1 only (thematic)"))
    # Example B: all-model Tier-1, risk-tilted (inverse-fragility), capped at 35%
    if t1:
        _print_stock(evaluate_stock_basket(uni, weight(uni, t1, "inv_fragility", cap=0.35), "All-model Tier-1 risk-tilted (cap 35%)"))
    # Example C: low-floating value screen (<=15% floating), equal-weight
    val = select(uni, max_floating=15)
    if val:
        _print_stock(evaluate_stock_basket(uni, weight(uni, val[:6], "equal"), "Low-floating value screen"))

    # Example D: option basket on the Tier-1 names at 24m, to show the compounding caution
    if t1:
        ob = evaluate_option_basket(uni, weight(uni, t1, "equal"), 24, "Tier-1 option basket (24m)")
        print(f"\n=== {ob['label']} ===")
        for n, l in ob["legs"].items():
            print(f"  {n:10s} {l['weight']:.0%}  cyc {l['cyc']}  {l['timing_status']}")
        print(f"  COMBINED effective-N {ob['combined']['effective_N']} | impairment-weighted tail {ob['combined']['impairment_weighted_tail']}")
        print(f"  {ob['combined']['_caution']}")
    print("\nRESEARCH MODEL -- NOT INVESTMENT ADVICE. Risk/value X-ray, not a return forecast or sizing.")
