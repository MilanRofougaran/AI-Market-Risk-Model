"""
reverse_dcf.py -- implied-expectations readout (NOT a price target).
"What must you believe to justify today's premium?" Using the model's own duration +
competitive machinery, it solves for the company growth rate g* at which the CURRENT premium
would be fully justified (zero floating). Two outcomes:
  (a) a reachable g* -> "the market is implicitly pricing in g*% growth (vs your input g%)."
  (b) unreachable at any plausible g -> the premium is STRUCTURALLY unjustifiable by growth
      alone; the floating is from weak pricing power / earnings quality, not a short runway.
      You cannot grow your way out of weak pricing power. Reports the structural ceiling.
This fits the model's philosophy: it states implied expectations, never a "fair price".
RESEARCH MODEL -- NOT INVESTMENT ADVICE.
"""
import sys
import calibration as C
import engine as E
sys.path.insert(0, "discovery"); import tam_bridge as TB

R = getattr(C, "R_GROWTH", 0.09)
CAP = getattr(C, "GROWTH_DURATION_CAP", 15)

def _facts(name):
    if name in C.COMPANIES:
        return C.COMPANIES[name]
    return TB.STOCK_TAM_FACTS[name]

def _frac_at(name, g):
    """justified fraction dur(g)*gq(g) at trial company growth g (other inputs fixed)."""
    comp = C.COMPETITIVE[name]; d = _facts(name)
    m = comp["m"]; ss = comp["struct_share"]; moat = comp["moat"]; pp = comp["pricing_power"]
    eq = d["earn_quality"]
    s_star = min(ss * moat + ss * (1 - moat) * 0.5, 0.95)
    Tsat = E._years_to_saturation(d["rev_bn"], d["tam_bn"], s_star, g, m, CAP)
    anchor = E._growth_annuity(0.30, R, 8)
    dur = min(E._growth_annuity(g, R, Tsat) / anchor, 1.0) if anchor > 0 else 0.0
    g_share = max(g - m, 0.0)
    durab = (g - g_share + g_share * moat) / g if g > 0 else 0.0
    gq = (durab + pp + eq) / 3.0
    return dur * gq, dur, gq, Tsat

def implied(name):
    comp = C.COMPETITIVE.get(name)
    if not comp:
        return None
    dec = E.decompose_premium() if name in C.COMPANIES else \
          E.decompose_premium({name: dict(_facts(name), name=name)})
    o = dec[name]
    premium = o["premium_pts"]
    g0 = comp["g"]
    if premium <= 0:
        return dict(name=name, premium_pts=premium, note="no premium (P/E <= base); nothing to justify")
    # justified fraction is NON-monotonic in g (ultra-high g saturates the TAM instantly ->
    # short runway -> low duration credit). Scan a sensible range and track the PEAK.
    best_frac, best_g = -1.0, comp["m"]
    g = comp["m"]
    while g <= 0.80 + 1e-9:
        frac, dur, gq, Tsat = _frac_at(name, g)
        if frac > best_frac:
            best_frac, best_g = frac, g
        g += 0.01
    frac0, dur0, gq0, Tsat0 = _frac_at(name, g0)
    reachable = best_frac >= 0.999
    return dict(name=name, premium_pts=premium, g_input=g0, T_sat_credited=Tsat0,
                justified_frac_now=frac0, growth_quality=gq0,
                g_star=(best_g if reachable else None),
                max_justifiable=min(best_frac, 1.0), g_at_max=best_g)

def fmt(r):
    if "note" in r:
        return f"{r['name']}: {r['note']}"
    L = [f"{r['name']}: premium {r['premium_pts']:.1f} P/E pts; model justifies {r['justified_frac_now']:.0%} "
         f"at your inputs (g={r['g_input']:.0%}, runway {r['T_sat_credited']:.1f}y credited)"]
    if r["g_star"] is not None:
        L.append(f"  Implied: the market would need ~{r['g_star']:.0%} company growth for the premium to be "
                 f"FULLY justified (zero floating). You assume {r['g_input']:.0%}.")
    else:
        L.append(f"  Implied: NOT fully justifiable by growth -- the most the premium can justify is "
                 f"{r['max_justifiable']:.0%} (peak at g~{r['g_at_max']:.0%}). The remaining "
                 f"{1-r['max_justifiable']:.0%} is STRUCTURAL -- capped by pricing power & earnings "
                 f"quality, not runway. You cannot grow out of weak pricing power.")
    return "\n".join(L)

if __name__ == "__main__":
    names = sys.argv[1:] or list(C.COMPETITIVE.keys())
    for nm in names:
        r = implied(nm)
        if r: print(fmt(r)); print()
