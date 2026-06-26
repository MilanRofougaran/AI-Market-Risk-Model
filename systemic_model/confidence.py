"""
confidence.py -- how much to TRUST each output, not just the number. Combines:
  input_confidence      -- competitive-input confidence (competitive_assumptions) + price status
  validation_confidence -- DEPTH validated (backtest 7/7) but recovery TIMING not -> options/timing
                           outputs capped lower; ranking firmer than magnitude
  robustness            -- survives the tier_gate haircut panel? (Tier 1 high ... Tier 3 low)
Then per-output grades. An option-fair grade is additionally capped (model is IV-blind: it can say
"good under our thesis", never "good trade"). RESEARCH MODEL -- NOT INVESTMENT ADVICE.
"""
import sys
import calibration as C
import engine as E
import tier_gate as TG
try:
    from competitive_review import RATIONALE
except Exception:
    RATIONALE = {}

CONF = {"high": 0.9, "medium": 0.6, "low": 0.35}
DEPTH_VAL = 0.80     # backtest validates drawdown depth
TIMING_VAL = 0.50    # recovery timing NOT validated
def _grade(x): return "High" if x >= 0.72 else ("Medium" if x >= 0.5 else "Low")

def run(names=None):
    dec = E.decompose_premium()
    for nm in ["Palantir", "Astera Labs", "CoreWeave"]:
        try:
            sys.path.insert(0, "discovery"); import tam_bridge as TB
            inp = dict(TB.STOCK_TAM_FACTS[nm]); inp["name"] = nm
            dec[nm] = E.decompose_premium({nm: inp})[nm]
        except Exception:
            pass
    tiers = TG.run(list(dec.keys()))
    prices = getattr(C, "PRICES", {})
    rows = {}
    for nm in (names or dec.keys()):
        o = dec.get(nm)
        if o is None: continue
        comp_conf = CONF.get(RATIONALE.get(nm, ("low",))[0], 0.5)
        price = prices.get(nm)
        price_conf = 0.9 if (nm == "NVIDIA" and price) else (0.5 if price else 0.4)
        pre_earn = o["fwd_pe"] >= 150
        inp_conf = (comp_conf + price_conf) / 2 * (0.6 if pre_earn else 1.0)
        tier = tiers.get(nm, {}).get("tier", "3")
        robust = 0.9 if tier.startswith("1") else (0.6 if tier.startswith("2") else 0.35)
        depth_grade = _grade((inp_conf + DEPTH_VAL + robust) / 3)
        option_grade = _grade((inp_conf + TIMING_VAL + robust) / 3)   # timing-sensitive + IV-blind
        anchor_grade = _grade((inp_conf + robust) / 2)
        rows[nm] = dict(tier=tier.split()[0], input_conf=round(inp_conf, 2),
                        pnever_conf=depth_grade, option_conf=option_grade, anchor_conf=anchor_grade)
    return rows

if __name__ == "__main__":
    rows = run(sys.argv[1:] or None)
    print(f"{'Name':12s} {'Tier':>4s} {'inputConf':>9s} {'P(never)':>9s} {'optionFair':>10s} {'anchored$':>9s}")
    for nm, r in rows.items():
        print(f"{nm:12s} {r['tier']:>4s} {r['input_conf']:>9.2f} {r['pnever_conf']:>9s} "
              f"{r['option_conf']:>10s} {r['anchor_conf']:>9s}")
    print("\noptionFair is timing-sensitive AND IV-blind -> capped lower; it means 'good under thesis', not 'good trade'.")
