"""
profit_sensitivity_attribution.py -- turn a fragility NUMBER into a DIAGNOSIS.

For each name it decomposes the tier-gate worst-case fragility into the contribution of each
stress panel (TAM haircut, moat haircut, margin haircut, rate+input shock) versus the base,
and names the BINDING panel -- so you can see WHY a name worsens, not just that it does. It
also shows the earnings-cyclicality build-up (operating leverage + input cost + interest)
from the waterfall. Pure decomposition of numbers the model already computes -- no new inputs.
RESEARCH MODEL -- NOT INVESTMENT ADVICE.
"""
import sys
import tier_gate
import earnings_waterfall as W


def attribution(names=None):
    rows = tier_gate.run(names)
    out = {}
    for nm, r in rows.items():
        fr = r["fragility"]
        base = fr["base"]
        deltas = {}
        for panel, val in fr.items():
            if panel == "base":
                continue
            deltas[panel] = round(val - base, 3)          # how much THIS panel adds over base
        binding = max(fr, key=lambda k: fr[k])             # which panel is the worst-case
        w = W.waterfall(nm)
        cyc_attr = w["attribution"] if w else None
        out[nm] = {
            "base_fragility": round(base, 3),
            "panel_deltas": deltas,                        # +pts each stress panel adds
            "worst_fragility": round(r["worst"], 3),
            "binding_panel": binding,
            "tier": r["tier"],
            "earnings_cyclicality_drivers": cyc_attr,      # operating_leverage / input_cost / interest
        }
    return out


def fmt(out):
    lines = []
    for nm, a in sorted(out.items(), key=lambda kv: kv[1]["worst_fragility"]):
        lines.append(f"\n{nm}  (Tier {a['tier']})")
        lines.append(f"  base fragility           {a['base_fragility']}")
        for panel, dlt in a["panel_deltas"].items():
            mark = "  <-- BINDING" if panel == a["binding_panel"] and dlt > 0 else ""
            sign = "+" if dlt >= 0 else ""
            lines.append(f"    {panel:18s} {sign}{dlt}{mark}")
        lines.append(f"  worst-case fragility     {a['worst_fragility']}  (binding: {a['binding_panel']})")
        if a["earnings_cyclicality_drivers"]:
            d = a["earnings_cyclicality_drivers"]
            lines.append(f"  EPS-trough drivers: op-leverage {d['operating_leverage']} | "
                         f"input-cost {d['input_cost']} | interest {d['interest_expense']}")
    return "\n".join(lines)


if __name__ == "__main__":
    out = attribution(sys.argv[1:] or None)
    print("FRAGILITY ATTRIBUTION -- what drives each name's worst case (sorted safest-first)")
    print(fmt(out))
    print("\nReads the same tier-gate panels and waterfall the model already computes; no new inputs.")
    print("RESEARCH MODEL -- NOT INVESTMENT ADVICE.")
