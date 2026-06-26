"""
tier_gate.py -- MANDATORY haircut panel + Tier assignment. Enforces the discipline that was
advisory: a name cannot earn a "clean core" (Tier 1) label unless its fragility survives every
input haircut. Panel per name: base, TAM haircut (tam x0.5, cagr -15pts), moat -0.15,
margin haircut (earn_quality -0.15 AND pricing_power -0.15). Reports fragility under each and a
Tier. RESEARCH MODEL -- NOT INVESTMENT ADVICE.
"""
import copy, sys
import calibration as C
import engine as E
sys.path.insert(0, "discovery"); import tam_bridge as TB

def _decomp(tam_mult=1.0, cagr_cut=0.0, moat_d=0.0, eq_d=0.0, pp_d=0.0):
    comp = copy.deepcopy(getattr(C, "COMPETITIVE", {}))
    for v in comp.values():
        v["moat"] = max(0.0, min(1.0, v["moat"] + moat_d))
        v["pricing_power"] = max(0.0, min(1.0, v["pricing_power"] + pp_d))
        v["m"] = max(0.0, v["m"] - cagr_cut); v["g"] = max(0.0, v["g"] - cagr_cut)
    co = copy.deepcopy(dict(C.COMPANIES))
    for d in co.values():
        d["tam_bn"] *= tam_mult; d["tam_cagr"] = max(0.0, d["tam_cagr"] - cagr_cut)
        d["earn_quality"] = max(0.0, min(1.0, d["earn_quality"] + eq_d))
    saved = C.COMPETITIVE; C.COMPETITIVE = comp
    out = E.decompose_premium(co)
    for nm in ["Palantir", "Astera Labs", "CoreWeave"]:
        if nm in TB.STOCK_TAM_FACTS:
            inp = dict(TB.STOCK_TAM_FACTS[nm])
            inp["tam_bn"] *= tam_mult; inp["tam_cagr"] = max(0.0, inp["tam_cagr"] - cagr_cut)
            inp["earn_quality"] = max(0.0, min(1.0, inp["earn_quality"] + eq_d)); inp["name"] = nm
            out[nm] = E.decompose_premium({nm: inp})[nm]
    C.COMPETITIVE = saved
    return {nm: o["fragility"] for nm, o in out.items()}

PANEL = [("base", {}), ("TAM", dict(tam_mult=0.5, cagr_cut=0.15)),
         ("moat-.15", dict(moat_d=-0.15)), ("margin", dict(eq_d=-0.15, pp_d=-0.15))]


def _rate_input_col():
    """Per-name fragility under a combined rate + input-cost shock: the profit-sensitivity
    addons (interest-expense, input-cost) compress earn_quality and balance. Levered /
    low-pricing-power names worsen; net-cash / high-pricing-power names barely move."""
    base = E.decompose_premium()
    for nm in ["Palantir", "Astera Labs", "CoreWeave"]:
        if nm in TB.STOCK_TAM_FACTS:
            inp = dict(TB.STOCK_TAM_FACTS[nm]); inp["name"] = nm
            base[nm] = E.decompose_premium({nm: inp})[nm]
    out = {}
    for nm, o in base.items():
        eq = o.get("earn_quality", 0.6); bal = o.get("balance_sheet", 0.6)
        uf = o.get("unsupported_frac", 0.0)
        ic = o.get("input_cost_addon", 0.0); ie = o.get("interest_expense_addon", 0.0)
        eq_s = max(0.0, eq - ic); bal_s = max(0.0, bal - ie)
        out[nm] = max(0.0, min(1.0, 0.5 * uf + 0.3 * (1 - eq_s) + 0.2 * (1 - bal_s)))
    return out


def run(names=None):
    cols = {lbl: _decomp(**kw) for lbl, kw in PANEL}
    if getattr(C, "USE_PROFIT_SENSITIVITY", False):
        cols["rate+input"] = _rate_input_col()
    panel_labels = list(cols.keys())
    order = names or list(cols["base"].keys())
    rows = {}
    for nm in order:
        fr = {lbl: cols[lbl].get(nm) for lbl in panel_labels}
        if None in fr.values(): continue
        base = fr["base"]; worst = max(fr.values())
        if base < 0.20 and worst < 0.30:
            tier = "1  CLEAN CORE"
        elif base < 0.35 and worst < 0.48:
            tier = "2  ownable, watch"
        else:
            tier = "3  gated / fragile"
        rows[nm] = dict(fragility=fr, base=base, worst=worst, tier=tier)
    return rows


if __name__ == "__main__":
    rows = run(sys.argv[1:] or None)
    hdr = f"{'Name':12s} {'base':>5s} {'TAM':>5s} {'moat':>5s} {'margin':>6s} {'rate+in':>7s} {'worst':>6s}  Tier"
    print(hdr)
    for nm, r in sorted(rows.items(), key=lambda kv: kv[1]["worst"]):
        f = r["fragility"]
        ri = f.get("rate+input")
        ri_s = f"{ri:>7.2f}" if ri is not None else f"{'-':>7s}"
        print(f"{nm:12s} {f['base']:>5.2f} {f['TAM']:>5.2f} {f['moat-.15']:>5.2f} {f['margin']:>6.2f} "
              f"{ri_s} {r['worst']:>6.2f}  Tier {r['tier']}")
    print("\nTier 1 requires base<0.20 AND worst-across-haircuts<0.30. No clean-core label without surviving the panel.")
