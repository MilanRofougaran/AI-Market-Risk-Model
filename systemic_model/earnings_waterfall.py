"""
earnings_waterfall.py -- TRACEABLE income-statement view of the EPS collapse.

The engine compresses the earnings trough into one number (earnings_cyclicality). This
module shows the SAME number as an explicit waterfall, so you can see WHAT crushed EPS --
revenue, variable cost, fixed-cost absorption, input cost, or interest -- not just THAT it
collapsed. It RECONCILES to the model: waterfall EPS-trough == engine earnings_cyclicality.

It adds traceability, NOT new data or new philosophy. All line items come from inputs the
model already uses (op_margin m, fixed_cost_ratio f, rev_drawdown d, the rate/input addons).
The recovery-delay it reports is on the model's LEAST-VALIDATED axis (recovery timing) -- it
is the model's own estimate, not a historically validated figure.
RESEARCH MODEL -- NOT INVESTMENT ADVICE.
"""
import sys
import calibration as C
import engine as E


def effective_cogs_fragility(name):
    """Delegates to engine._effective_cogs_fragility (single source of truth: buckets or scalar)."""
    return E._effective_cogs_fragility(name)


def waterfall(name, apply_tax_scenario=False, tax_rate_delta=0.0):
    ol = getattr(C, "OPERATING_LEVERAGE", {}).get(name)
    if ol is None:
        return None
    ps = getattr(C, "PROFIT_SENSITIVITY", {}).get(name, {})
    pp = getattr(C, "COMPETITIVE", {}).get(name, {}).get("pricing_power", 0.5)
    m, f, d = ol["op_margin"], ol["fixed_cost_ratio"], ol["rev_drawdown"]

    # normalized: base revenue = 1.0 ; base EBIT (operating income) = m
    base_cost = 1.0 - m
    fixed_cost = base_cost * f
    var_cost_base = base_cost * (1.0 - f)
    base_ebit = m

    # revenue shock -> variable cost scales, fixed cost does NOT
    stressed_rev = 1.0 - d
    stressed_var_cost = var_cost_base * (1.0 - d)
    ebit_opleverage = stressed_rev - stressed_var_cost - fixed_cost
    endo_cyc = 1.0 - ebit_opleverage / base_ebit            # operating-leverage EPS drop

    # the two profit-sensitivity channels (as additional EPS-trough drags, per the engine)
    ie_addon = min(0.30, max(0.0, ps.get("net_debt_to_ebitda", 0.0)) *
                   ps.get("floating_rate_share", 0.0) * getattr(C, "RATE_SHOCK_K", 0.06))
    cf = effective_cogs_fragility(name)
    ic_addon = min(0.30, cf * (1.0 - pp) * getattr(C, "INPUT_SHOCK_K", 0.35))

    eps_trough = min(0.95, endo_cyc + ie_addon + ic_addon)  # == model earnings_cyclicality
    # optional, quarantined long-horizon tax drag (NOT part of panic EPS-trough by default)
    tax_drag = 0.0
    if apply_tax_scenario and tax_rate_delta:
        tax_drag = round(tax_rate_delta * (1.0 - eps_trough), 4)

    pe_expansion = round(1.0 / (1.0 - eps_trough), 1) if eps_trough < 1 else None
    recovery_delay = round(eps_trough * 0.6 + (1.0 - pp) * 0.2, 3)   # MODEL ESTIMATE (timing: unvalidated)

    return {
        "name": name,
        "lines": {
            "base_revenue": 1.0,
            "revenue_drawdown": -round(d, 3),
            "stressed_revenue": round(stressed_rev, 3),
            "less_variable_cost": -round(stressed_var_cost, 3),
            "less_fixed_cost (does not scale)": -round(fixed_cost, 3),
            "= EBIT_operating_leverage": round(ebit_opleverage, 3),
            "input_cost_drag (cyc pts)": round(ic_addon, 3),
            "interest_expense_drag (cyc pts)": round(ie_addon, 3),
            "tax_scenario_drag (long-horizon only)": tax_drag,
        },
        "base_ebit_margin": m,
        "eps_trough_depth": round(eps_trough, 3),
        "pe_expansion_at_trough": pe_expansion,
        "attribution": {"operating_leverage": round(endo_cyc, 3),
                        "input_cost": round(ic_addon, 3),
                        "interest_expense": round(ie_addon, 3)},
        "recovery_delay_estimate": recovery_delay,
        "_timing_note": "recovery_delay is the model's own estimate; recovery TIMING is NOT historically validated",
    }


def reconcile(name):
    """Confirm the waterfall EPS-trough equals the engine's earnings_cyclicality."""
    w = waterfall(name)
    if w is None:
        return None
    d = E.decompose_premium()
    if name not in d:
        import sys as _s, os; _s.path.insert(0, "discovery")
        import tam_bridge as TB
        if name in TB.STOCK_TAM_FACTS:
            inp = dict(TB.STOCK_TAM_FACTS[name]); inp["name"] = name
            d[name] = E.decompose_premium({name: inp})[name]
    model_cyc = d.get(name, {}).get("earnings_cyclicality")
    return {"name": name, "waterfall_eps_trough": w["eps_trough_depth"],
            "model_cyclicality": round(model_cyc, 3) if model_cyc is not None else None,
            "reconciles": (model_cyc is not None and abs(model_cyc - w["eps_trough_depth"]) < 0.011)}


if __name__ == "__main__":
    names = sys.argv[1:] or ["NVIDIA", "AMD", "Micron", "CoreWeave"]
    for nm in names:
        w = waterfall(nm)
        if w is None:
            print(f"{nm}: no operating-leverage inputs"); continue
        print(f"\n=== {nm} earnings waterfall (normalized; revenue=1.0) ===")
        for k, v in w["lines"].items():
            print(f"  {k:42s} {v:>7}")
        print(f"  EPS trough depth: {w['eps_trough_depth']:.0%}  |  P/E expansion ~{w['pe_expansion_at_trough']}x")
        print(f"  attribution: {w['attribution']}  | recovery-delay est {w['recovery_delay_estimate']} (timing UNVALIDATED)")
        r = reconcile(nm)
        print(f"  reconcile vs model cyclicality: waterfall={r['waterfall_eps_trough']} model={r['model_cyclicality']} -> {'OK' if r['reconciles'] else 'MISMATCH'}")
