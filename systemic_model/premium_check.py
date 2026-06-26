"""
premium_check.py -- the operating rule as an executable checklist.
   archetype -> matrix gate -> tenor -> premium vs model fair -> macro gate

USAGE:
  python3 premium_check.py "NVIDIA" 24m 0.75 32          (single call)
  python3 premium_check.py "Micron" 24m 0.90/1.20 12      (bull call spread, debit as % of spot)
  python3 premium_check.py "Micron" 24m 0.80/1.00/1.20 3   (call butterfly 1-2-1, net debit; negative = credit)
  python3 premium_check.py "NVIDIA" 36m tail:0.75/1.50/2.25 38   (tail-kicker +1/-1/+1: cap a band, keep the far tail)
  python3 premium_check.py "NVIDIA" 24m custom:+1@0.75,-2@1.00,+1@1.20 8   (any signed legs; net-naked upside = banned)
                            name    tenor strike(s)    market-premium-as-%-of-spot
Reads options_lens.json (fair values + gates) and calibration (macro stress).
In-grid off-grid strikes are linearly INTERPOLATED between bounding cells;
snapping (MAX_SNAP=0.15) applies only at grid edges; farther strikes are refused.
Off-grid tenors (e.g. 30m for a Dec-2028 LEAPS) interpolate between bracketing
tenor columns: python3 premium_check.py "NVIDIA" 30m 0.75 45.3
Prints PASS/REJECT per gate. RESEARCH MODEL -- NOT INVESTMENT ADVICE.
"""
import json
import sys
import calibration as C


MAX_SNAP = 0.15   # reject strikes farther than this from any grid cell

def _nearest_strike_key(strikes, requested):
    vals = sorted(float(k) for k in strikes.keys())
    nearest = min(vals, key=lambda x: abs(x - requested))
    return f"{nearest:.2f}", nearest

def _resolve(strikes, requested, snaps):
    """Return (label, kval, fair, p_itm, exact). In-range off-grid strikes are
    LINEARLY INTERPOLATED between bounding cells (credit: Gemini review);
    outside the grid range, snap within MAX_SNAP or refuse."""
    vals = sorted(float(k) for k in strikes.keys())
    for v in vals:
        if abs(v - requested) < 1e-9:
            c = strikes[f"{v:.2f}"]
            return f"{v:.2f}", v, c["fair_value_pct_of_spot"], c["p_itm"], True
    if vals[0] <= requested <= vals[-1]:
        lo = max(v for v in vals if v < requested); hi = min(v for v in vals if v > requested)
        w = (requested - lo) / (hi - lo)
        cl, ch = strikes[f"{lo:.2f}"], strikes[f"{hi:.2f}"]
        fair = round((1 - w) * cl["fair_value_pct_of_spot"] + w * ch["fair_value_pct_of_spot"], 1)
        pit = round((1 - w) * cl["p_itm"] + w * ch["p_itm"], 3)
        snaps.append((requested, None, f"{requested:.2f} interpolated between {lo:.2f}/{hi:.2f}"))
        return f"{requested:.2f}", requested, fair, pit, False
    key, val = _nearest_strike_key(strikes, requested)
    if abs(val - requested) > MAX_SNAP + 1e-9:
        print(f"  strike {requested:.2f} outside grid (nearest {key}, max snap {MAX_SNAP}) — "
              f"extend STRIKES in options_lens.py and re-run the lens")
        return None
    snaps.append((requested, val, f"{requested:.2f} snapped to grid edge {key}"))
    return key, val, strikes[key]["fair_value_pct_of_spot"], strikes[key]["p_itm"], True


import math as _math

def _survival(strikes, x):
    """P(S_T > x) interpolated from the (strike, p_itm) grid -- p_itm at each strike
    IS the survival curve of S_T. Clamps below the lowest / above the highest strike."""
    pts = sorted((float(k), v["p_itm"]) for k, v in strikes.items())
    if x <= pts[0][0]:
        return pts[0][1]
    if x >= pts[-1][0]:
        return pts[-1][1]
    for (k0, p0), (k1, p1) in zip(pts, pts[1:]):
        if k0 <= x <= k1:
            w = (x - k0) / (k1 - k0)
            return (1 - w) * p0 + w * p1
    return pts[-1][1]


def main():
    if len(sys.argv) < 5:
        print(__doc__)
        return

    name = sys.argv[1]
    tenor = sys.argv[2]
    arg3 = sys.argv[3]
    tailk = custom = False
    legs = None
    if arg3.startswith("tail:"):
        tailk = True; arg3 = arg3[5:]
    elif arg3.startswith("custom:"):
        custom = True
        legs = []
        for piece in arg3[7:].split(","):
            q, k = piece.split("@")
            legs.append((int(q), float(k)))
    elif arg3.startswith("fly:"): arg3 = arg3[4:]
    elif arg3.startswith("spread:"): arg3 = arg3[7:]
    parts = arg3.split("/") if not custom else []
    spread = (len(parts) == 2) and not tailk
    fly = (len(parts) == 3) and not tailk
    if custom:
        requested_strike = legs[0][1]
    elif fly or tailk:
        requested_strike, requested_k2, requested_k3 = (float(x) for x in parts)
        if not (requested_strike < requested_k2 < requested_k3):
            print(f"invalid strike order {sys.argv[3]} — write strikes ascending (K1 < K2 < K3)"); return
    elif spread:
        requested_strike, requested_k2 = float(parts[0]), float(parts[1])
    else:
        requested_strike = float(parts[0])
    if spread:
        requested_strike, requested_k2 = float(parts[0]), float(parts[1])
        if not (requested_strike < requested_k2):
            print(f"reversed spread {sys.argv[3]} — write the long (lower) strike first: "
                  f"{requested_k2}/{requested_strike}"); return
    mkt = float(sys.argv[4])

    o = json.load(open("options_lens.json"))
    if name not in o["names"]:
        print(f"'{name}' not in lens. Available: {', '.join(o['names'])}")
        return

    nm = o["names"][name]
    gate = nm.get("gate", "")
    tenor_row = nm.get(tenor)
    tenor_interp_note = None
    if not tenor_row:
        # tenor interpolation (credit: GPT review) — e.g. 30m between 24m and 36m
        try:
            months = int(tenor.rstrip("m"))
        except ValueError:
            months = None
        grid_t = sorted((int(k.rstrip("m")), k) for k in nm if k != "gate")
        if months and grid_t and grid_t[0][0] <= months <= grid_t[-1][0]:
            lo = max(t for t in grid_t if t[0] <= months); hi = min(t for t in grid_t if t[0] >= months)
            if lo == hi:
                tenor_row = nm[lo[1]]
            else:
                w = (months - lo[0]) / (hi[0] - lo[0])
                synth = {}
                for k in nm[lo[1]]["strikes"]:
                    a, b = nm[lo[1]]["strikes"][k], nm[hi[1]]["strikes"][k]
                    synth[k] = {"fair_value_pct_of_spot": round((1-w)*a["fair_value_pct_of_spot"] + w*b["fair_value_pct_of_spot"], 1),
                                "p_itm": round((1-w)*a["p_itm"] + w*b["p_itm"], 3)}
                tenor_row = {"strikes": synth}
                tenor_interp_note = f"tenor {tenor} interpolated between {lo[1]}/{hi[1]}"
        if not tenor_row:
            print(f"tenor {tenor} not in lens (range {grid_t[0][1]}–{grid_t[-1][1]}). "
                  f"Available: {', '.join(k for _, k in grid_t)}")
            return

    strikes = tenor_row.get("strikes", {})
    snaps = []
    r1 = _resolve(strikes, requested_strike, snaps)
    if r1 is None: return
    strike_key, k1v, fair0, pitm0, exact1 = r1
    row = {"fair_value_pct_of_spot": fair0, "p_itm": pitm0}
    all_exact = exact1
    fair = row["fair_value_pct_of_spot"]
    pitm = row["p_itm"]
    giveup = None; pbody = None; ptail = None
    if custom:
        net_slope = sum(q for q, _ in legs)
        # negative-payoff-zone check (credit: GPT review). Expiry payoff is piecewise
        # linear with kinks at the strikes; payoff(K_j) = sum q_i * max(K_j - K_i, 0).
        # An interior negative zone (or a negative top kink with rising slope) means a
        # net-short region — outside this tool's long-thesis risk model. The one
        # exception: slope==0 with negativity ONLY at the top kink is the flat
        # broken-wing case, deferred to the archetype gate below.
        kstrikes = sorted({k for _, k in legs})
        kpay = {kj: sum(q * max(kj - ki, 0.0) for q, ki in legs) * 100 for kj in kstrikes}
        topk = kstrikes[-1]
        neg = {kj: v for kj, v in kpay.items() if v < -1e-9}
        if neg and not (net_slope == 0 and set(neg) == {topk}):
            worst = min(neg, key=neg.get)
            print(f"\n{name}  {tenor}  custom {sys.argv[3][7:]}")
            print(f"  structure ban   REJECT   negative payoff zone at expiry "
                  f"(min {neg[worst]:+.0f}% of spot around S~{worst:.2f}x) — net-short region, "
                  f"outside this tool's long-thesis risk model")
            print("  -> REJECT.  Research model -- not investment advice.")
            return
        if net_slope < 0:
            print(f"\n{name}  {tenor}  custom {sys.argv[3][7:]}")
            print("  structure ban   REJECT   net-naked upside short (slope above top strike = "
                  f"{net_slope:+d}) — the fat right tail is the one thing this engine is most sure of")
            print("  -> REJECT.  Research model -- not investment advice.")
            return
        fair = 0.0; pieces = []
        for q, k in legs:
            rr = _resolve(strikes, k, snaps)
            if rr is None: return
            kk, _kv, fv, _pv, _e = rr
            fair += q * fv
            pieces.append(f"{q:+d}@{kk}")
        fair = round(fair, 1)
        top_key, _ = _nearest_strike_key(strikes, max(k for _, k in legs))
        pitm = strikes[top_key]["p_itm"]
        strike_key = ",".join(pieces)
        custom_above = -sum(q * k for q, k in legs) * 100 if net_slope == 0 else None
        custom_diag = (f"top strike {top_key} · slope above top {net_slope:+d} · P(above top) {pitm:.0%}"
                       + (f" · flat payoff above top {custom_above:+.0f}%" if custom_above is not None else ""))
    if tailk:
        r2 = _resolve(strikes, requested_k2, snaps); r3 = _resolve(strikes, requested_k3, snaps)
        if r2 is None or r3 is None: return
        k2_key, k2v, f2, _p2, e2 = r2; k3_key, k3v, f3, p3, e3 = r3
        all_exact = all_exact and e2 and e3
        f1 = fair
        fair = round(f1 - f2 + f3, 1)
        ptail = p3
        pitm = ptail
        strike_key = f"+{strike_key}/-{k2_key}/+{k3_key}"
    if fly:
        r2 = _resolve(strikes, requested_k2, snaps); r3 = _resolve(strikes, requested_k3, snaps)
        if r2 is None or r3 is None: return
        k2_key, k2v, f2, _p2, e2 = r2; k3_key, k3v, f3, p3, e3 = r3
        all_exact = all_exact and e2 and e3
        f1 = fair
        fair = round(f1 - 2*f2 + f3, 1)
        fly_above = round(((k2v - k1v) - (k3v - k2v)) * 100, 0)
        pbody = round(row["p_itm"] - p3, 3)
        pitm = pbody
        strike_key = f"{strike_key}/{k2_key}/{k3_key}"
    if spread:
        r2 = _resolve(strikes, requested_k2, snaps)
        if r2 is None: return
        k2_key, k2v, f2, p2v, e2 = r2
        all_exact = all_exact and e2
        f1 = fair
        giveup = (f2 / f1) if f1 > 0 else None
        fair = round(f1 - f2, 1)            # spread fair debit
        pitm = p2v                          # P(finish at max)
        strike_key = f"{strike_key}/{k2_key}"
    edge = fair - mkt
    # ---- P(profit): probability the discounted payoff beats the premium paid ----
    # P(ITM) is NOT P(profit): a deep-ITM call can finish ITM yet lose if the premium
    # was too rich. profit <=> discounted payoff > premium <=> S_T > breakeven.
    pprofit = None
    try:
        months = int(tenor.rstrip("m")); Ty = months / 12.0
        rr = o.get("discount_10y", 0.045)
        comp_factor = _math.exp(rr * Ty)            # de-discount the premium to expiry
        be_prem = (mkt / 100.0) * comp_factor       # premium in spot units, carried to expiry
        if not (spread or fly or tailk or custom):  # single call: breakeven = K + premium
            pprofit = _survival(strikes, k1v + be_prem)
        elif spread:                                # vertical: profit if S_T > K1 + debit, capped at K2
            be = k1v + be_prem
            pprofit = _survival(strikes, be) if be < k2v else 0.0
    except Exception:
        pprofit = None
    stress = C.SYSTEMIC_STRESS["score"]
    acute = C.SYSTEMIC_STRESS["acute"]

    g = gate.lower()
    checks = []
    checks.append((
        "archetype gate",
        "REJECT" if "broken" in g else ("CAUTION" if ("survivability" in g or "watch" in g or "uncertain" in g) else "pass"),
        gate or "secular",
    ))
    try:
        short = int(tenor.rstrip("m")) <= 12
    except ValueError:
        short = tenor in ("6m", "12m")
    checks.append((
        "tenor vs cycle",
        "REJECT" if (short and "cyclical" in g and "no short" in g) else ("CAUTION" if short and "cyclical" in g else "pass"),
        f"{tenor}" + (" on a cyclical" if "cyclical" in g else ""),
    ))
    checks.append((
        "premium vs fair",
        "pass" if edge > 0 else "REJECT",
        f"model fair {fair:.1f}% vs market {mkt:.1f}%  (edge {edge:+.1f} pts, physical measure)",
    ))
    if pprofit is not None:
        checks.append((
            "profit odds",
            "pass",
            f"P(payoff > premium paid) = {pprofit:.0%}   (vs P(ITM) {pitm:.0%} -- ITM is not profit)",
        ))
    if custom:
        sec = ("secular" in g) and ("cyclical" not in g)
        if custom_above is not None and custom_above < -1e-9 and sec:
            checks.append(("structure fit", "REJECT",
                f"custom structure loses {-custom_above:.0f}% flat in the secular right tail "
                f"(broken-wing in custom clothing)"))
        elif custom_above is not None and custom_above < -1e-9:
            checks.append(("structure fit", "CAUTION",
                f"bounded {custom_above:+.0f}% payoff above top — acceptable only as a cyclical body bet"))
        checks.append(("structure info", "pass", custom_diag))
    if tailk:
        sec = ("secular" in g) and ("cyclical" not in g)
        checks.append(("structure fit", "pass",
            ("tail-retaining 3-leg — the secular-consistent shape" if sec else
             "caps a middle band, keeps the far tail") + f"; P(tail kept) {ptail:.0%}"))
    if fly:
        sec = ("secular" in g) and ("cyclical" not in g)
        if fly_above < 0 and sec:
            checks.append(("structure fit", "REJECT",
                f"broken-wing fly loses {-fly_above:.0f}% flat in the secular right tail — being right hard = losing"))
        elif fly_above < 0:
            checks.append(("structure fit", "CAUTION",
                f"bounded {fly_above:+.0f}% payoff above the top wing — acceptable only as a cyclical body bet"))
        else:
            checks.append(("structure fit",
                "CAUTION" if sec else "pass",
                "butterfly sells the secular tail twice — body bet against your own thesis" if sec
                else "body bet on a bounded rebound — the cyclical use case"))
    if spread and giveup is not None:
        sec = ("secular" in g) and ("cyclical" not in g)
        if sec and giveup > 0.55:
            gu_status, gu_note = "CAUTION", f"selling {giveup:.0%} of the long call's fair — large secular tail cap"
        elif sec and giveup > 0.35:
            gu_status, gu_note = "CAUTION", f"selling {giveup:.0%} of the long call's fair — moderate secular tail cap"
        else:
            gu_status, gu_note = "pass", f"selling {giveup:.0%} of the long call's fair"
        checks.append(("tail give-up", gu_status, gu_note))
    checks.append((
        "macro gate",
        "pass" if acute < 0.5 else "CAUTION: acute stress elevated -- roll long",
        f"stress {stress:.2f}, acute {acute:.2f}",
    ))

    notes = ([tenor_interp_note] if tenor_interp_note else []) + [t for *_x, t in snaps]
    snap_note = ("  [" + "; ".join(notes) + "]") if notes else ""

    try:
        sl = json.load(open("spread_lens.json"))
        cell_key = (f"+{strike_key.split('/')[0].lstrip('+')}" if False else None)
        lookup = None
        if tailk: lookup = f"+{strike_key.split('/')[0][1:]}/-{k2_key}/+{k3_key}".replace("++","+")
        elif fly: lookup = strike_key
        elif spread: lookup = strike_key
        if lookup and all_exact and tenor_interp_note is None:
            cell = sl.get("names", {}).get(name, {}).get("tenors", {}).get(tenor, {}).get(lookup)
            if cell:
                extras = " · ".join(f"{k} {v}" for k, v in cell.items() if k != "fair_pct" and k != "fair_debit_pct")
                checks.append(("lens detail", "pass", extras))
    except Exception:
        pass
    print(f"\n{name}  {tenor}  K={strike_key}   " + ("P(tail kept)" if tailk else ("P(above top)" if custom else ("P(body)" if fly else ("P(max)" if spread else "P(ITM)")))) + f"={pitm:.0%}{snap_note}")
    verdict = "PASS"
    for label, status, note in checks:
        print(f"  {label:16s} {status:8s} {note}")
        if status == "REJECT":
            verdict = "REJECT"
        elif "CAUTION" in status and verdict == "PASS":
            verdict = "PASS WITH CAUTION"
    print(f"  -> {verdict}.  Thesis-conditional edge only; no IV/vega; size and breakeven are yours.")
    print("  Research model -- not investment advice.")


if __name__ == "__main__":
    main()
