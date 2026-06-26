"""
tam_haircut.py -- honesty check for Gemini red-team point #2 ("garbage in on TAM").
Re-runs the premium decomposition with every TAM halved and every TAM-CAGR cut 15pts,
then shows how far floating-premium% and fragility move. If a name's anchoring
collapses under a haircut, its low fragility was resting on the TAM thesis.
RESEARCH MODEL -- NOT INVESTMENT ADVICE.
"""
import copy, json, sys
import calibration as C
import engine as E

TAM_MULT = 0.5
CAGR_CUT = 0.15

def run(names=None):
    base = E.decompose_premium()
    hc_src = copy.deepcopy(dict(C.COMPANIES))
    for n, d in hc_src.items():
        d["tam_bn"] = d["tam_bn"] * TAM_MULT
        d["tam_cagr"] = max(0.0, d["tam_cagr"] - CAGR_CUT)
    # also haircut the competitive growth inputs so duration shrinks consistently
    saved = getattr(C, "COMPETITIVE", {})
    hc_comp = copy.deepcopy(saved)
    for n, d in hc_comp.items():
        d["m"] = max(0.0, d["m"] - CAGR_CUT); d["g"] = max(0.0, d["g"] - CAGR_CUT)
    C.COMPETITIVE = hc_comp
    hc = E.decompose_premium(hc_src)
    C.COMPETITIVE = saved
    print(f"TAM haircut: tam x{TAM_MULT}, tam_cagr -{CAGR_CUT:.0%}  (does anchoring survive?)")
    print(f"{'Name':10s} {'floating% base->hc':>20s} {'fragility base->hc':>20s}  {'T_sat':>11s}")
    for nm in (names or base):
        if nm not in hc: continue
        b, h = base[nm], hc[nm]
        print(f"{nm:10s} {b['unsupported_frac']:>9.0%} -> {h['unsupported_frac']:<7.0%}  "
              f"{b['fragility']:>9.2f} -> {h['fragility']:<7.2f}  "
              f"{b.get('T_sat',0):>4.1f}->{h.get('T_sat',0):<4.1f}")

if __name__ == "__main__":
    run(sys.argv[1:] or None)
