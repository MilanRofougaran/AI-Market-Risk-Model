"""
tax_and_policy_scenarios.py -- LONG-HORIZON tax / tariff / subsidy scenarios.

QUARANTINED BY DESIGN. Taxes and policy are slow and telegraphed -- they cause permanent
re-ratings, NOT the 6-18 month liquidity panics the engine models. So this panel touches ONLY
long-horizon valuation:
    - anchored value (the fragility floor)        - reverse-DCF expectations
    - buyback / cash capacity
and NEVER touches:
    - P(never) / the recovery matrix              - the drawdown engine
    - the short-term option gate / premium_check
This separation is deliberate; do not wire it into the panic core. RESEARCH MODEL -- NOT
INVESTMENT ADVICE.
"""
import sys

# illustrative long-horizon scenarios (effective-tax-rate-equivalent drag on net income)
SCENARIOS = {
    "tax_+5pt":          {"eff_tax_delta": 0.05, "note": "+5pt effective tax rate"},
    "chips_subsidy_loss":{"eff_tax_delta": 0.03, "note": "CHIPS-Act subsidy reduction (margin-equiv)"},
    "tariff_shock":      {"eff_tax_delta": 0.04, "note": "import tariff / trade-policy drag (margin-equiv)"},
    "rnd_capitalization":{"eff_tax_delta": 0.02, "note": "R&D capitalization / cash-tax timing"},
}


def apply(anchored_value_dollars, scenario="tax_+5pt", base_eff_tax=0.15):
    """Long-horizon haircut to ANCHORED value from a tax/policy scenario.
    Higher effective tax lowers durable earnings power -> lower justified multiple/anchored value.
    Returns the adjusted anchored value and the implied change. Does NOT touch P(never)/recovery/options."""
    sc = SCENARIOS.get(scenario)
    if sc is None:
        raise ValueError(f"scenario must be one of {list(SCENARIOS)}")
    dtax = sc["eff_tax_delta"]
    # net income scales by (1 - new_tax)/(1 - base_tax); anchored value scales with durable earnings
    factor = (1.0 - (base_eff_tax + dtax)) / (1.0 - base_eff_tax)
    adj = anchored_value_dollars * factor
    return {"scenario": scenario, "note": sc["note"],
            "eff_tax_delta": dtax, "earnings_factor": round(factor, 3),
            "anchored_base": round(anchored_value_dollars, 2),
            "anchored_long_horizon": round(adj, 2),
            "anchored_change_pct": round(100 * (factor - 1), 1),
            "scope": "LONG-HORIZON anchored value / reverse-DCF / buyback only -- NOT P(never), recovery, or the option gate"}


def panel(anchored_value_dollars, base_eff_tax=0.15):
    return {s: apply(anchored_value_dollars, s, base_eff_tax) for s in SCENARIOS}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="LONG-HORIZON tax/policy scenarios on anchored value (quarantined)")
    ap.add_argument("anchored", nargs="?", type=float, default=None, help="anchored value in $ (e.g. 100)")
    ap.add_argument("--name", help="pull anchored value for a ticker from stock_premium (needs a price in C.PRICES)")
    ap.add_argument("--base-tax", type=float, default=0.15, help="base effective tax rate")
    args = ap.parse_args()
    base = args.anchored
    if args.name:
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "discovery"))
        import stock_premium as SP
        r = SP.rows([args.name]).get(args.name, {})
        av = r.get("anchored_value")
        if av is None:
            sys.exit(f"No anchored value for {args.name} (needs a price in C.PRICES). "
                     f"Pass a numeric anchored value instead, e.g. `python3 tax_and_policy_scenarios.py 100`.")
        base = av
        print(f"anchored value for {args.name} (from stock_premium) = ${base:.2f}")
    if base is None:
        base = 100.0
        print("(no anchored value given; using $100.00 illustrative. Pass a number or --name <ticker>.)")
    print(f"TAX / POLICY SCENARIO PANEL on anchored value = ${base:.2f} (LONG-HORIZON ONLY)\n")
    print(f"{'scenario':22s}{'factor':>8s}{'anchored':>11s}{'change':>9s}  note")
    for s, r in panel(base, args.base_tax).items():
        print(f"{s:22s}{r['earnings_factor']:>8}{r['anchored_long_horizon']:>11}{r['anchored_change_pct']:>8}%  {r['note']}")
    print("\nQUARANTINED: affects anchored value / reverse-DCF / buyback capacity ONLY.")
    print("Does NOT touch P(never), the recovery matrix, or the short-term option gate. NOT INVESTMENT ADVICE.")
