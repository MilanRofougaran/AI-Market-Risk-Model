"""
stock_premium.py -- STOCK-side ledger: anchored value vs floating premium, $ and scale-free,
with an AUTOMATIC TAM-haircut so borrowed resilience cannot hide.

   base value      = EPS x BASE_PE            (no-growth anchor)
   anchored value  = EPS x (BASE_PE + justified_pts)   # FRAGILITY FLOOR, not a price target
   floating $      = EPS x unsupported_pts    (sentiment; evaporates first in stress)
   floating %      = unsupported_frac         (scale-free)
   fragility       base AND haircut (tam x0.5, cagr -15pts) shown side by side

 If a name's fragility/floating jumps under the haircut, its low base fragility was BORROWED
 from an aggressive TAM thesis (e.g. ARM 42%->77%). NVIDIA-type names barely move (robust).

 ANCHORED VALUE IS A FRAGILITY FLOOR, NOT A FAIR-VALUE TARGET. (current - anchored) is NOT
 upside/downside; the model never says what a price "should" be. Justified premium is capped at
 the actual premium, so this layer emits NO "cheap/undervalued" signal.
 RESEARCH MODEL -- NOT INVESTMENT ADVICE.
"""
import copy, json, sys
import calibration as C
import engine as E

TAM_MULT = 0.5
CAGR_CUT = 0.15


def _extended(dec):
    try:
        sys.path.insert(0, "discovery"); import tam_bridge as TB
        for nm in ["Palantir", "Astera Labs", "CoreWeave"]:
            if nm in TB.STOCK_TAM_FACTS:
                inp = dict(TB.STOCK_TAM_FACTS[nm]); inp["name"] = nm
                dec[nm] = E.decompose_premium({nm: inp})[nm]
    except Exception:
        pass
    return dec


def _haircut_decomp():
    """re-decompose with TAM halved and CAGR cut, returning {name: (frag, floatfrac)}."""
    src = copy.deepcopy(dict(C.COMPANIES))
    for d in src.values():
        d["tam_bn"] *= TAM_MULT; d["tam_cagr"] = max(0.0, d["tam_cagr"] - CAGR_CUT)
    saved = getattr(C, "COMPETITIVE", {})
    hc_comp = copy.deepcopy(saved)
    for d in hc_comp.values():
        d["m"] = max(0.0, d["m"] - CAGR_CUT); d["g"] = max(0.0, d["g"] - CAGR_CUT)
    C.COMPETITIVE = hc_comp
    hc = E.decompose_premium(src)
    # extended names too
    try:
        sys.path.insert(0, "discovery"); import tam_bridge as TB
        for nm in ["Palantir", "Astera Labs", "CoreWeave"]:
            if nm in TB.STOCK_TAM_FACTS:
                inp = dict(TB.STOCK_TAM_FACTS[nm])
                inp["tam_bn"] *= TAM_MULT; inp["tam_cagr"] = max(0.0, inp["tam_cagr"] - CAGR_CUT)
                inp["name"] = nm
                hc[nm] = E.decompose_premium({nm: inp})[nm]
    except Exception:
        pass
    C.COMPETITIVE = saved
    return {nm: (o["fragility"], o["unsupported_frac"]) for nm, o in hc.items()}


def rows(names=None):
    dec = _extended(E.decompose_premium())
    hc = _haircut_decomp()
    out = {}
    for nm, o in dec.items():
        if names and nm not in names:
            continue
        fwd = o["fwd_pe"]
        frag_hc, float_hc = hc.get(nm, (o["fragility"], o["unsupported_frac"]))
        r = {"fwd_pe": fwd, "base_pe": C.BASE_PE,
             "premium_pts": o["premium_pts"], "justified_pts": o["justified_pts"],
             "floating_pts": o["unsupported_pts"], "floating_pct_of_price": o["unsupported_frac"],
             "fragility": o["fragility"], "recovery_quality": o["recovery_quality"],
             "T_sat": o.get("T_sat"),
             "fragility_haircut": round(frag_hc, 2), "floating_pct_haircut": round(float_hc, 3)}
        price = (C.__dict__.get("PRICES") or {}).get(nm)
        if price:
            eps = price / fwd if fwd > 0 else None
            r.update(price=price, eps=round(eps, 2),
                     base_value=round(eps * C.BASE_PE, 2),
                     floating_dollars=round(eps * o["unsupported_pts"], 2),
                     anchored_value=round(eps * (C.BASE_PE + o["justified_pts"]), 2))
        out[nm] = r
    return out


def fmt(nm, r):
    L = [f"{nm}"]
    if "price" in r:
        L.append(f"  price ${r['price']:.2f}  |  base (no-growth) ${r['base_value']:.0f}  |  "
                 f"anchored ${r['anchored_value']:.0f}  |  floating ${r['floating_dollars']:.0f} "
                 f"({r['floating_pct_of_price']:.0%} of price)")
        L.append(f"  [anchored = price level where no premium is unsupported; a fragility floor, NOT a target]")
    else:
        L.append(f"  (no price set -- scale-free) floating premium {r['floating_pct_of_price']:.0%} of price")
    L.append(f"  fwd P/E {r['fwd_pe']:.0f} = {r['base_pe']:.1f} base + {r['premium_pts']:.1f} premium "
             f"({r['justified_pts']:.1f} justified / {r['floating_pts']:.1f} floating) | runway {r['T_sat']:.1f}y")
    fb, fh = r["fragility"], r["fragility_haircut"]
    flag = "  <-- BORROWED resilience (anchoring leans on the TAM thesis)" if (fh - fb) > 0.10 else \
           ("  (robust to TAM haircut)" if (fh - fb) < 0.03 else "")
    L.append(f"  fragility {fb:.2f} -> {fh:.2f} under TAM haircut (tam x0.5, cagr -15pts); "
             f"floating {r['floating_pct_of_price']:.0%} -> {r['floating_pct_haircut']:.0%}{flag}")
    return "\n".join(L)


if __name__ == "__main__":
    R = rows(sys.argv[1:] or None)
    for nm, r in R.items():
        print(fmt(nm, r)); print()
    json.dump(R, open("stock_premium.json", "w"), indent=1)
