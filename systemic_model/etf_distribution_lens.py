"""
etf_distribution_lens.py -- distribution-aware ETF risk & valuation (one level deeper than the
weighted-average synthetic-company view). Runs on REAL ETFs (covered subset, coverage-vetoed) AND
on custom baskets. NON-DESTRUCTIVE: adds metrics + diagnostics; never overwrites etf_lens outputs.

Adds, beyond basket_builder's per-custom-basket metrics:
  - the same distribution math on REAL ETFs over their covered holdings (coverage<0.40 => diagnostic-only)
  - recovery & premium ATTRIBUTION (which names drive fast/slow/perm and the floating premium)
  - premium_effective_N and weak_tail_effective_N (distinct from weight-effN)
  - balance-sheet distribution + recovery_barbell (fortress+fragile bimodality the average hides)
  - a CONSTRAINT-CHECKER (pass/fail per rule) -- NOT a return optimizer
  - a side-by-side COMPARISON CARD (custom baskets vs SMH/CHAT/SOXX/DRAM/NVDA-only)

Held lines: NO return-maximizing weight search (overfits one cycle path). Virtual basket option is
analytics-only / non-tradable. No sizing. RESEARCH MODEL -- NOT INVESTMENT ADVICE.
"""
import os, sys, json, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "discovery"))
import calibration as C, engine as E, extension_data as X, solvency as SV


def _uni():
    import tam_bridge as TB
    new, _ = TB.build_company_universe(base_companies=C.COMPANIES, verbose=False)
    for k, v in new.items():
        C.COMPANIES.setdefault(k, v)
    d = E.decompose_premium()
    uni = {}
    for n, dd in d.items():
        uni[n] = dict(floating=dd.get("unsupported_frac", 0.0),
                      fragility=dd.get("fragility", 0.0),
                      cyclicality=dd.get("earnings_cyclicality", 0.0),
                      net_cash=dd.get("net_cash_to_mcap", 0.0),
                      balance=X.balance(n) if hasattr(X, "balance") else 0.5,
                      impairment=SV._stock_impairment(n) if hasattr(SV, "_stock_impairment") else 0.0)
    return uni


def _effN(shares):
    tot = sum(shares) or 1.0
    return round(1.0 / sum((s / tot) ** 2 for s in shares), 1) if any(shares) else 0.0


def _wstd(vals, ws):
    tot = sum(ws) or 1.0
    mean = sum(v * w for v, w in zip(vals, ws)) / tot
    var = sum(w * (v - mean) ** 2 for v, w in zip(vals, ws)) / tot
    return math.sqrt(max(0.0, var)), mean


def _pctile(vals, q):
    if not vals:
        return None
    s = sorted(vals); k = (len(s) - 1) * q
    lo = int(math.floor(k)); hi = int(math.ceil(k))
    return round(s[lo] + (s[hi] - s[lo]) * (k - lo), 3)


def distribution_metrics(weights, uni):
    """Distribution-aware metrics for any {name: weight} (custom basket OR real-ETF covered subset)."""
    names = [n for n in weights if n in uni]
    if not names:
        return {"error": "no covered names"}
    w = {n: weights[n] for n in names}
    tot = sum(w.values()) or 1.0
    w = {n: w[n] / tot for n in names}                         # renormalize over covered
    frg = [uni[n]["fragility"] for n in names]; wl = [w[n] for n in names]

    # balance-sheet distribution
    net_cash_wt = sum(w[n] for n in names if uni[n]["net_cash"] > 0)
    net_debt_wt = sum(w[n] for n in names if uni[n]["net_cash"] < 0)
    bs_disp, _ = _wstd([uni[n]["balance"] for n in names], wl)
    # fragility distribution + barbell
    frag_disp, frag_mean = _wstd(frg, wl)
    p75, p90 = _pctile(frg, 0.75), _pctile(frg, 0.90)
    barbell = round(sum(w[n] for n in names if uni[n]["fragility"] < 0.15) *
                    sum(w[n] for n in names if uni[n]["fragility"] > 0.40), 3)
    cyclical_wt = sum(w[n] for n in names if uni[n]["cyclicality"] >= 0.50)
    surv_risk_wt = sum(w[n] for n in names if uni[n]["impairment"] > 0.20)
    weak = {n: w[n] for n in names if uni[n]["fragility"] >= 0.40 or uni[n]["impairment"] > 0.15}
    weak_tail_wt = sum(weak.values())
    weak_tail_effN = _effN(list(weak.values())) if weak else 0.0

    # premium distribution
    contrib = {n: w[n] * uni[n]["floating"] for n in names}
    tot_fl = sum(contrib.values())
    floating = sum(w[n] * uni[n]["floating"] for n in names)
    if tot_fl > 0:
        sc = sorted(contrib.values(), reverse=True)
        top1 = sc[0] / tot_fl; top3 = sum(sc[:3]) / tot_fl
        premium_hhi = sum((c / tot_fl) ** 2 for c in contrib.values())
        premium_effN = round(1.0 / premium_hhi, 1)
        prem_contrib_names = sorted(contrib, key=contrib.get, reverse=True)[:3]
    else:
        top1 = top3 = premium_hhi = 0.0; premium_effN = 0.0; prem_contrib_names = []

    # recovery split + attribution (same rule as etf_lens, computed over these weights)
    fast = {n: w[n] for n in names if uni[n]["balance"] >= 0.70 and uni[n]["impairment"] < 0.05}
    perm_w = sum(w[n] * uni[n]["impairment"] for n in names)
    fast_w = sum(fast.values()); slow_w = max(0.0, 1.0 - fast_w - perm_w)
    perm_contrib = sorted(names, key=lambda n: w[n] * uni[n]["impairment"], reverse=True)[:3]

    return {
        "n_covered": len(names),
        "balance": {"net_cash_weight": round(net_cash_wt, 3), "net_debt_weight": round(net_debt_wt, 3),
                    "balance_sheet_dispersion": round(bs_disp, 3)},
        "fragility": {"mean": round(frag_mean, 3), "dispersion": round(frag_disp, 3),
                      "p75": p75, "p90": p90, "recovery_barbell": barbell,
                      "cyclical_weight": round(cyclical_wt, 3),
                      "survivability_risk_weight": round(surv_risk_wt, 3),
                      "weak_tail_weight": round(weak_tail_wt, 3),
                      "weak_tail_effN": weak_tail_effN,
                      "weak_tail_contributors": sorted(weak, key=weak.get, reverse=True)[:3]},
        "premium": {"floating_premium_pct": round(floating * 100, 1),
                    "floating_top1": round(top1, 2), "floating_top3": round(top3, 2),
                    "premium_hhi": round(premium_hhi, 2), "premium_effN": premium_effN,
                    "premium_contributors": prem_contrib_names,
                    "single_name_dependency": top1 >= 0.50},
        "recovery": {"fast_weight": round(fast_w, 3), "slow_weight": round(slow_w, 3),
                     "permanent_weight": round(perm_w, 3),
                     "fast_contributors": sorted(fast, key=fast.get, reverse=True)[:3],
                     "permanent_tail_contributors": perm_contrib},
    }


def real_etf(etf_name, uni):
    """Distribution metrics for a REAL ETF over its covered holdings, with the coverage veto."""
    import tam_bridge as TB
    facts = dict(C.COMPANIES)
    try:
        _, info = TB.etf_spec(etf_name, facts)
    except Exception as e:
        return {"etf": etf_name, "error": str(e)}
    cov = info["coverage"]; w = info["weights"]
    m = distribution_metrics(w, uni)
    conf = "high" if cov >= 0.60 else ("medium" if cov >= 0.40 else "LOW")
    m.update({"etf": etf_name, "coverage": round(cov, 2), "confidence": conf,
              "diagnostic_only": cov < 0.40,
              "_coverage_note": ("coverage < 40% -> metrics are DIAGNOSTIC ONLY, not ranking-grade "
                                 "(QTUM-style veto)" if cov < 0.40 else "coverage adequate")})
    return m


DEFAULT_CONSTRAINTS = dict(max_single=0.30, max_top3=0.60, min_effN_weight=4.0, max_weak_tail=0.08,
                           max_surv_risk=0.05, max_floating_top1=0.40, max_cyclical=0.15, min_coverage=0.70)


def constraint_check(weights, uni, label="basket", **overrides):
    """Pass/fail per rule. NOT an optimizer -- it flags violations of risk/structure limits."""
    cons = dict(DEFAULT_CONSTRAINTS); cons.update(overrides)
    tot = sum(weights.values()) or 1.0
    w = {n: weights[n] / tot for n in weights}
    m = distribution_metrics(w, uni)
    ws = sorted(w.values(), reverse=True)
    weff = _effN(list(w.values()))
    checks = {
        "max_single_weight": (ws[0] <= cons["max_single"], round(ws[0], 3), cons["max_single"]),
        "max_top3_weight": (sum(ws[:3]) <= cons["max_top3"], round(sum(ws[:3]), 3), cons["max_top3"]),
        "min_weight_effN": (weff >= cons["min_effN_weight"], weff, cons["min_effN_weight"]),
        "max_weak_tail": (m["fragility"]["weak_tail_weight"] <= cons["max_weak_tail"],
                          m["fragility"]["weak_tail_weight"], cons["max_weak_tail"]),
        "max_survivability_risk": (m["fragility"]["survivability_risk_weight"] <= cons["max_surv_risk"],
                                   m["fragility"]["survivability_risk_weight"], cons["max_surv_risk"]),
        "max_floating_top1": (m["premium"]["floating_top1"] <= cons["max_floating_top1"],
                              m["premium"]["floating_top1"], cons["max_floating_top1"]),
        "max_cyclical_weight": (m["fragility"]["cyclical_weight"] <= cons["max_cyclical"],
                                m["fragility"]["cyclical_weight"], cons["max_cyclical"]),
    }
    fails = [k for k, (ok, _, _) in checks.items() if not ok]
    return {"label": label, "passes": not fails, "violations": fails,
            "detail": {k: {"ok": ok, "value": val, "limit": lim} for k, (ok, val, lim) in checks.items()},
            "_note": "constraint-checker, not an optimizer; flags risk/structure limit breaches. NOT ADVICE."}


ETF_OPTION_GATE_OVERRIDE = {
    # explicit class/gate beats the computed cyclical-weight threshold (GPT audit #4)
    "DRAM": "deep-ITM / long-duration only (cyclical MEMORY basket -- demand-trough gate; overrides computed cyclical wt)",
    "Memory": "deep-ITM / long-duration only (cyclical memory basket -- demand-trough gate)",
    "Kioxia": "deep-ITM / long-duration only (memory)",
}
SECULAR_WITH_SLEEVE = {"SMH", "SOXX"}   # secular baskets with a cyclical semi sleeve


def option_suitability(m, coverage=1.0, name=None):
    """Derived option-structure flag from the distribution (NOT a score). Explicit ETF class/gate
    OVERRIDES the computed cyclical-weight threshold (a memory basket is long-only even if its
    covered-subset cyclical weight computes under 40%). Operationalizes: cyclical -> no short tenor;
    concentrated premium -> single-name-like; weak tail -> defined-risk; low coverage -> speculative."""
    if name:
        for key, verdict in ETF_OPTION_GATE_OVERRIDE.items():
            if key.lower() in name.lower():
                return verdict
    if coverage < 0.40:
        return "speculative / low-confidence only (coverage <40%)"
    if m["fragility"]["cyclical_weight"] >= 0.40:
        if name and any(s.lower() in name.lower() for s in SECULAR_WITH_SLEEVE):
            return ("secular basket with a cyclical semiconductor sleeve -- short-tenor calls need EXTRA "
                    "CAUTION, not memory-style auto-rejection; deep-ITM/long preferred")
        return "no short-tenor; deep-ITM / long-duration only (cyclical-heavy)"
    if m["premium"]["floating_top1"] >= 0.50:
        return "behaves single-name-like (premium concentrated); treat as such"
    if m["fragility"]["weak_tail_weight"] >= 0.08:
        return "defined-risk structures only (weak tail)"
    return "standard ETF-option candidate (still must pass premium_check + broker_bridge)"


def comparison_card(custom_baskets, real_etfs, uni, with_pnever=False, pnever_paths=4000):
    """Run custom baskets AND real ETFs through identical distribution metrics -> one table.
    with_pnever=True adds the CANONICAL P(never) (portfolio-of-paths, distribution-aware) via
    correlation.basket_terminal -- slower (a joint sim per row), +-1-2pt sampling noise."""
    import tam_bridge as TB
    rows = []
    def _pn(weights):
        if not with_pnever:
            return None
        try:
            import correlation as COR
            return COR.basket_terminal(weights, n_paths=pnever_paths)
        except Exception:
            return None
    for label, w in custom_baskets.items():
        tot = sum(w.values()) or 1.0
        wn = {n: x / tot for n, x in w.items()}
        m = distribution_metrics(wn, uni)
        rows.append(("custom", label, 1.00, "high", m, option_suitability(m, 1.0, name=label), _pn(wn)))
    for etf in real_etfs:
        r = real_etf(etf, uni)
        if "error" not in r:
            # real-ETF P(never): portfolio-of-paths over its covered holdings (distribution-aware)
            try:
                _, info = TB.etf_spec(etf, dict(C.COMPANIES)); pnw = info["weights"]
            except Exception:
                pnw = {}
            rows.append(("real", etf, r["coverage"], r["confidence"], r,
                         option_suitability(r, r["coverage"], name=etf), _pn(pnw) if pnw else None))
    return rows


def _fmt_card(rows):
    print(f"\n{'basket / ETF':28s}{'cov':>5s}{'float%':>7s}{'top1':>5s}{'premEffN':>9s}"
          f"{'weakTl':>7s}{'cyc':>5s}{'P(nvr)':>7s}{'fast/slow/perm':>15s}")
    print("-" * 104)
    for row in rows:
        kind, label, cov, conf, m = row[:5]
        pn = row[6] if len(row) > 6 else None
        if "premium" not in m:
            continue
        rec = m["recovery"]
        pnstr = (f"{pn['p_never']*100:.0f}%" if pn and "p_never" in pn else "  -")
        print(f"{label[:28]:28s}{cov*100:>4.0f}%{m['premium']['floating_premium_pct']:>6.1f}%"
              f"{m['premium']['floating_top1']:>5.2f}{m['premium']['premium_effN']:>9}"
              f"{m['fragility']['weak_tail_weight']*100:>6.0f}%{m['fragility']['cyclical_weight']*100:>4.0f}%"
              f"{pnstr:>7s}{rec['fast_weight']*100:>5.0f}/{rec['slow_weight']*100:>3.0f}/{rec['permanent_weight']*100:>3.0f}%")
    print("\noption suitability:")
    for row in rows:
        label = row[1]; sut = row[5] if len(row) > 5 else "?"
        print(f"  {label[:28]:28s} {sut}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="distribution-aware ETF lens (real ETFs + custom baskets)")
    ap.add_argument("--with-pnever", action="store_true",
                    help="add canonical P(never) per row (slower: a joint sim per row)")
    ap.add_argument("--pnever-paths", type=int, default=4000, help="paths for P(never) sims")
    args = ap.parse_args()
    uni = _uni()
    print("ETF DISTRIBUTION LENS -- distribution-aware risk & valuation (real ETFs + custom baskets)")
    print("Non-destructive diagnostic; coverage<40% => diagnostic-only. NOT INVESTMENT ADVICE.")
    if not args.with_pnever:
        print("(P(never) column off by default -- pass --with-pnever to compute it, slower)")

    # custom baskets to compare (the reviewer's templates) + NVDA-only benchmark
    customs = {
        "Model Core AI/Semi": {"NVIDIA": .28, "Qualcomm": .16, "AMD": .15, "Marvell": .13,
                               "Broadcom": .10, "Palantir": .08, "Astera Labs": .06, "Micron": .04},
        "Tier-1 equal": {"NVIDIA": .25, "Qualcomm": .25, "AMD": .25, "Marvell": .25},
        "NVDA-only": {"NVIDIA": 1.0},
    }
    reals = ["SMH (VanEck Semis)", "CHAT (Roundhill GenAI)", "SOXX (iShares Semis)", "DRAM (Roundhill Memory)"]
    _fmt_card(comparison_card(customs, reals, uni, with_pnever=args.with_pnever, pnever_paths=args.pnever_paths))

    print("\n--- premium & recovery attribution (who drives the buckets) ---")
    for label, w in [("Model Core AI/Semi", customs["Model Core AI/Semi"])]:
        m = distribution_metrics(w, uni)
        print(f"  {label}: premium concentrated in {m['premium']['premium_contributors']} "
              f"(top1 {m['premium']['floating_top1']:.0%}); perm-tail driven by {m['recovery']['permanent_tail_contributors']}")
    dramr = real_etf("DRAM (Roundhill Memory)", uni)
    print(f"  DRAM: weak-tail {dramr['fragility']['weak_tail_weight']:.0%} in {dramr['fragility']['weak_tail_contributors']}; "
          f"barbell {dramr['fragility']['recovery_barbell']}; {dramr['_coverage_note']}")

    print("\n--- constraint check (Model Core AI/Semi vs default limits) ---")
    cc = constraint_check(customs["Model Core AI/Semi"], uni, "Model Core AI/Semi")
    print(f"  passes={cc['passes']}  violations={cc['violations'] or 'none'}")
    for k, v in cc["detail"].items():
        flag = "" if v["ok"] else "  <-- VIOLATION"
        print(f"    {k:24s} {v['value']} (limit {v['limit']}){flag}")

    out = {"comparison": [(k, l, c) for k, l, c, _, _ in []], "note": "see stdout"}
    json.dump({"customs": {k: distribution_metrics(v, uni) for k, v in customs.items()},
               "reals": {e: real_etf(e, uni) for e in reals}},
              open(os.path.join(HERE, "etf_distribution_lens.json"), "w"), indent=1, default=str)
    print("\nwrote etf_distribution_lens.json. RESEARCH MODEL -- NOT INVESTMENT ADVICE.")
