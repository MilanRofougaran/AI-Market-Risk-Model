"""
option_gated_screener.py -- a GATED option SCREENER (NOT a validated optimizer).
SCOPE: single calls + DEBIT CALL VERTICALS. Butterflies, broken-wing flies, tail-kickers, and custom
signed-leg structures are NOT screened here yet (they have multi-region payoffs / multiple breakevens, so
a single-breakeven P(profit) would be wrong) -- those remain in spread_lens.py + premium_check.py. A
future payoff-grid engine will add them. So: this is a single-call + vertical-spread gated screener.

We optimize for probability of success UNDER THE MODEL'S THESIS AND GATES. We still CANNOT guarantee
real-market profitability unless the live option premium, IV, spread, liquidity, and event risk also
pass. This is a disciplined screener, not a crystal ball.

WHY THIS BEATS A NORMAL OPTION-CHAIN SCREEN: a standard screener ranks by Greeks / log-normal IV and is
blind to business reality (it will flag a 6-month Micron ATM call as "cheap, high-prob" while memory
earnings are in a cyclical bust). This screener applies the model's HARD GATES *before* ranking, so it
amputates wrong-tenor / broken-gate / cyclical-theta-trap candidates that a Greeks screener would surface.

ARCHITECTURE (per 3 converging reviews): LEXICOGRAPHIC filter-then-rank, NOT a weighted score.
A weighted success_score is deliberately NOT used: a large edge or P(profit) must NEVER buy back a failed
safety gate. Gates are hard vetoes; only survivors are ranked.

  Veto order:  gate(archetype/broken/survivability) -> tenor vs recovery-prior -> structure legality
               -> premium-vs-fair (live only) -> broker/IV/liquidity (broker data only)
               -> execution-cost (multi-leg only) -> max-debit
  Rank survivors by P(profit); tie-break edge/debit, then lower max-loss, then longer-tenor confidence.

P(profit) = P(S_T > K + premium*e^{rT}), computed by interpolating options_lens p_itm at the BREAKEVEN
strike ratio r' = strike_ratio + (premium% /100)*e^{rT}. This is P(ITM at breakeven) -- it correctly
distinguishes a deep-ITM call that finishes ITM but doesn't clear its premium. It is PHYSICAL-MEASURE,
IV-BLIND, and its RECOVERY TIMING is UNVALIDATED -- so P(profit) is stamped HIGH only for the long-dated
deep-ITM regime where timing barely moves the payoff, and LOW/medium where it leans on the timing axis.

WHAT THIS DOES NOT DO: no weighted score, no expected-return ranking (leans hardest on the unvalidated
growth/timing axis), no position sizing, no order recommendation, no fabricated live premium or IV, no
calendars/diagonals/short-vol. It ranks; you size. RESEARCH MODEL -- NOT INVESTMENT ADVICE.
"""
import os, sys, math, json, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "discovery"))
import calibration as C

LENS = json.load(open(os.path.join(HERE, "options_lens.json")))
SPREADS = json.load(open(os.path.join(HERE, "spread_lens.json"))) if os.path.exists(os.path.join(HERE, "spread_lens.json")) else {"names": {}}
RATE = (C.MACRO.get("ust_10y") or 4.0) / 100.0
TENOR_Y = {"6m": 0.5, "12m": 1.0, "18m": 1.5, "24m": 2.0, "36m": 3.0}
DEFAULT_STRIKES = [0.50, 0.60, 0.70, 0.75, 0.80, 0.85, 0.90, 1.00, 1.10, 1.20, 1.50, 2.00, 2.25]

# recovery-prior -> minimum tenor (the tenor GATE). PRIOR-based (not calibrated) -- conservative by design.
RECOVERY_TENOR_FLOOR = {            # archetype key from drawdown_normalization._recovery_prior_for
    "secular": "6m", "defensive": "6m", "cyclical_broad": "12m", "optical": "18m",
    "cyclical_memory": "24m", "hyperscaler": None, "broken": None}   # None => no single-call tenor clears it
_TENOR_ORDER = ["6m", "12m", "18m", "24m", "36m"]


def _gate_label(name):
    g = SPREADS["names"].get(name, {}).get("gate")
    if g:
        return g
    try:
        import crash_growth as CG
        return CG.archetype(name)
    except Exception:
        return "secular"


def _recovery_prior(name):
    import drawdown_normalization as DN
    return DN._recovery_prior_for(name)   # (key, lo, hi, desc)


def _strike_table(name, tenor):
    nm = LENS["names"].get(name)
    if not nm or tenor not in nm:
        return None
    return nm[tenor]["strikes"]


def _grid_max(name, tenor):
    t = _strike_table(name, tenor)
    return max(float(k) for k in t) if t else None


def _interp(table, field, ratio):
    """Linear interpolation of a strike-grid field at an arbitrary strike ratio.
    Returns (value, in_grid). in_grid=False when ratio is past the TOP of the grid (clamping there would
    OVERSTATE P(profit) -- true value is lower), so callers flag rather than silently clamp. Below the
    grid bottom is safe (deep-ITM -> p_itm ~1), so in_grid stays True there."""
    if table is None:
        return None, True
    pts = sorted((float(k), v[field]) for k, v in table.items())
    if ratio <= pts[0][0]:
        return pts[0][1], True
    if ratio >= pts[-1][0]:
        return pts[-1][1], (ratio <= pts[-1][0] + 1e-9)
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= ratio <= x1:
            w = (ratio - x0) / (x1 - x0) if x1 > x0 else 0.0
            return y0 + w * (y1 - y0), True
    return pts[-1][1], True


def p_itm(name, tenor, ratio):
    v, _ = _interp(_strike_table(name, tenor), "p_itm", ratio)
    return v


def fair_pct(name, tenor, ratio):
    v, _ = _interp(_strike_table(name, tenor), "fair_value_pct_of_spot", ratio)
    return v


def p_profit(name, tenor, ratio, premium_pct):
    """P(S_T > K + premium*e^{rT}) = P(ITM at breakeven strike ratio).
    Returns (p_profit, in_grid). in_grid=False => breakeven past the strike grid; do NOT trust the number
    (clamped/overstated) -- flag it and extend the lens instead."""
    be = ratio + (premium_pct / 100.0) * math.exp(RATE * TENOR_Y[tenor])
    return _interp(_strike_table(name, tenor), "p_itm", be)


def _timing_confidence(gate, tenor, ratio):
    sec = ("secular" in gate) and ("cyclical" not in gate)
    long_dated = _TENOR_ORDER.index(tenor) >= _TENOR_ORDER.index("18m")
    deep = ratio <= 0.85
    if "broken" in gate.lower() or "survivability" in gate.lower():
        return "rejected"
    if sec and long_dated and deep:
        return "high"
    if sec:
        return "medium"
    if ("cyclical" in gate) and long_dated and deep:
        return "medium"
    return "low"


def screen_single(name, tenor, ratio, mode="analysis", live_premium_pct=None,
                  min_edge=0.0, max_debit_pct=None):
    """Evaluate one single-call candidate through the lexicographic gates."""
    gate = _gate_label(name)
    rkey, rlo, rhi, rdesc = _recovery_prior(name)
    gmax = _grid_max(name, tenor)
    # strike itself beyond the lens grid -> fair value would be a clamp artifact; reject, don't trade on it
    if gmax is not None and ratio > gmax + 1e-9:
        return {"name": name, "structure": "single-call", "tenor": tenor, "strike_ratio": round(ratio, 3),
                "gate": gate, "verdict": "REJECT",
                "reason": f"strike ratio {ratio} outside options_lens grid [.. {gmax}] -- extend the lens; "
                          "won't trade on a clamped fair value"}
    fv = fair_pct(name, tenor, ratio); pi = p_itm(name, tenor, ratio)
    base = {"name": name, "structure": "single-call", "tenor": tenor, "strike_ratio": round(ratio, 3),
            "gate": gate, "recovery_prior": f"B{rlo}-{rhi}" if rlo != rhi else f"B{rlo}",
            "model_fair_pct": round(fv, 1) if fv is not None else None,
            "p_itm": round(pi, 3) if pi is not None else None,
            "timing_confidence": _timing_confidence(gate, tenor, ratio),
            "stamps": {"physical_measure": True, "risk_neutral": False, "iv_blind": True,
                       "timing_validated": False, "live_premium_supplied": live_premium_pct is not None,
                       "broker_bridge_passed": "NA"}}
    # ---- VETO 1: archetype / broken / survivability ----
    gl = gate.lower()
    if "broken" in gl:
        return {**base, "verdict": "REJECT", "reason": "broken gate -- duration does not repair the thesis"}
    if "survivability" in gl:
        return {**base, "verdict": "REJECT",
                "reason": "survivability gate -- single naked call not allowed; defined-risk spreads only"}
    # ---- VETO 2: tenor vs recovery prior ----
    floor = RECOVERY_TENOR_FLOOR.get(rkey, "12m")
    if floor is None:
        return {**base, "verdict": "REJECT", "reason": f"recovery prior {rkey}: no single-call tenor clears it (defined-risk only)"}
    if _TENOR_ORDER.index(tenor) < _TENOR_ORDER.index(floor):
        return {**base, "verdict": "REJECT",
                "reason": f"tenor {tenor} < {floor} floor for {rkey} recovery prior (wrong-tenor for the cycle)"}
    if rkey == "cyclical_memory" and ratio >= 0.95:
        return {**base, "verdict": "REJECT",
                "reason": "memory cyclical: no near-ATM calls (denominator collapses in the trough); deep-ITM only"}
    # ---- VETO 3: structure legality (single long call is always legal) ----
    # ---- VETO 4: premium vs fair (live only) ----
    if mode == "live" and live_premium_pct is not None:
        edge = fv - live_premium_pct
        base["market_premium_pct"] = round(live_premium_pct, 1); base["edge_pct"] = round(edge, 1)
        pp, in_grid = p_profit(name, tenor, ratio, live_premium_pct)
        base["p_profit"] = round(pp, 3) if (pp is not None and in_grid) else None
        base["p_profit_in_grid"] = in_grid
        if edge < min_edge:
            return {**base, "verdict": "REJECT", "reason": f"premium {live_premium_pct}% >= model fair {fv:.1f}% (no edge)"}
        if max_debit_pct is not None and live_premium_pct > max_debit_pct:
            return {**base, "verdict": "REJECT", "reason": f"debit {live_premium_pct}% > max {max_debit_pct}%"}
        if not in_grid:
            return {**base, "verdict": "CAUTION",
                    "reason": f"edge>0 but P(profit) UNAVAILABLE -- breakeven beyond strike grid (max {_grid_max(name,tenor)}x); "
                              "extend options_lens strike grid; do not trust a clamped probability"}
        watch = any(w in gl for w in ("watch", "uncertain", "lean", "peg"))
        return {**base, "verdict": "CAUTION" if watch else "PASS",
                "reason": ("passes gates; edge>0; " + ("watch/uncertain gate -> size as satellite" if watch else "clean"))
                + " -- broker_bridge (IV/spread/liquidity) still required before trading"}
    # ---- analysis mode: never PASS; show P(profit AT FAIR) + required max premium ----
    pp, in_grid = p_profit(name, tenor, ratio, fv) if fv is not None else (None, True)
    base["p_profit_at_fair"] = round(pp, 3) if (pp is not None and in_grid) else None
    base["p_profit_in_grid"] = in_grid
    base["required_max_premium_pct"] = round(fv, 1) if fv is not None else None
    base["market_premium_pct"] = None; base["edge_pct"] = None
    return {**base, "verdict": "NEEDS LIVE PREMIUM",
            "reason": "passes model gates; supply a live premium to check edge + run broker_bridge"
                      + ("" if in_grid else " (NOTE: P(profit) breakeven beyond strike grid -- extend lens)")}


def screen_vertical(name, tenor, k_long, k_short, struct, mode="analysis", live_premium_pct=None,
                    min_edge=0.0, max_debit_pct=None):
    """Evaluate a DEBIT CALL VERTICAL (long lower strike k_long, short higher k_short) through the same
    lexicographic gates. A debit vertical has ONE practical breakeven = k_long + net_debit, so
    P(profit)=P(S_T > k_long + debit*e^{rT}) is single-valued and computable by the same interpolation.
    struct = spread_lens cell {width_pct, fair_debit_pct, p_max, p_between, tail_giveup}."""
    gate = _gate_label(name)
    rkey, rlo, rhi, rdesc = _recovery_prior(name)
    fair_debit = struct.get("fair_debit_pct"); width = struct.get("width_pct")
    # vertical not in spread_lens (no fair debit) -> reject cleanly rather than do None arithmetic
    if fair_debit is None:
        return {"name": name, "structure": "vertical", "tenor": tenor,
                "strike_ratio": f"{k_long:.2f}/{k_short:.2f}", "gate": gate, "verdict": "REJECT",
                "reason": f"vertical {k_long:.2f}/{k_short:.2f} not in spread_lens for {tenor} -- "
                          "run/add the spread_lens cell before live screening"}
    gmax = _grid_max(name, tenor)
    if gmax is not None and (k_long > gmax + 1e-9 or k_short > gmax + 1e-9):
        return {"name": name, "structure": "vertical", "tenor": tenor,
                "strike_ratio": f"{k_long:.2f}/{k_short:.2f}", "gate": gate, "verdict": "REJECT",
                "reason": f"vertical strike(s) outside options_lens grid [.. {gmax}] -- extend the lens"}
    base = {"name": name, "structure": "vertical", "tenor": tenor,
            "strike_ratio": f"{k_long:.2f}/{k_short:.2f}", "k_long": k_long, "k_short": k_short,
            "gate": gate, "recovery_prior": f"B{rlo}-{rhi}" if rlo != rhi else f"B{rlo}",
            "model_fair_pct": round(fair_debit, 1) if fair_debit is not None else None,
            "width_pct": round(width, 1) if width is not None else None,
            "p_itm": round(struct.get("p_max", 0), 3),     # ~P(reach full width)
            "timing_confidence": _timing_confidence(gate, tenor, k_long),
            "stamps": {"physical_measure": True, "risk_neutral": False, "iv_blind": True,
                       "timing_validated": False, "live_premium_supplied": live_premium_pct is not None,
                       "broker_bridge_passed": "NA"}}
    gl = gate.lower()
    # VETO 1: archetype / broken / survivability  (survivability ALLOWS defined-risk verticals)
    if "broken" in gl:
        return {**base, "verdict": "REJECT", "reason": "broken gate -- duration does not repair the thesis"}
    # NOTE: verticals ARE the defined-risk structure survivability names are restricted to, so NOT vetoed here.
    # VETO 2: tenor vs recovery prior
    floor = RECOVERY_TENOR_FLOOR.get(rkey, "12m")
    if floor is None:
        # hyperscaler/survivability: defined-risk only -> a vertical is allowed, but require the longest tenor
        floor = "24m"
    if _TENOR_ORDER.index(tenor) < _TENOR_ORDER.index(floor):
        return {**base, "verdict": "REJECT",
                "reason": f"tenor {tenor} < {floor} floor for {rkey} recovery prior (wrong-tenor for the cycle)"}
    if rkey == "cyclical_memory" and k_long >= 0.95:
        return {**base, "verdict": "REJECT",
                "reason": "memory cyclical: long leg must be deep-ITM (no near-ATM); demand-trough gate"}
    # VETO 3: structure legality -- spread_lens only emits legal debit call spreads (k_long<k_short). OK.
    def _pp(debit):
        be = k_long + (debit / 100.0) * math.exp(RATE * TENOR_Y[tenor])
        return _interp(_strike_table(name, tenor), "p_itm", be)
    # VETO 4: premium vs fair (live only)
    if mode == "live" and live_premium_pct is not None:
        edge = fair_debit - live_premium_pct
        base["market_premium_pct"] = round(live_premium_pct, 1); base["edge_pct"] = round(edge, 1)
        base["max_loss_pct"] = round(live_premium_pct, 1)
        base["max_profit_pct"] = round(width - live_premium_pct, 1) if width is not None else None
        pp, in_grid = _pp(live_premium_pct)
        base["p_profit"] = round(pp, 3) if (pp is not None and in_grid) else None
        base["p_profit_in_grid"] = in_grid
        if edge < min_edge:
            return {**base, "verdict": "REJECT", "reason": f"debit {live_premium_pct}% >= fair {fair_debit:.1f}% (no edge)"}
        if max_debit_pct is not None and live_premium_pct > max_debit_pct:
            return {**base, "verdict": "REJECT", "reason": f"debit {live_premium_pct}% > max {max_debit_pct}%"}
        if not in_grid:
            return {**base, "verdict": "CAUTION",
                    "reason": f"edge>0 but P(profit) UNAVAILABLE -- breakeven beyond strike grid (max {_grid_max(name,tenor)}x)"}
        watch = any(w in gl for w in ("watch", "uncertain", "lean", "peg"))
        return {**base, "verdict": "CAUTION" if watch else "PASS",
                "reason": "defined-risk vertical passes gates; edge>0 -- broker_bridge + execution_cost still required"}
    pp, in_grid = _pp(fair_debit) if fair_debit is not None else (None, True)
    base["p_profit_at_fair"] = round(pp, 3) if (pp is not None and in_grid) else None
    base["p_profit_in_grid"] = in_grid
    base["max_loss_pct"] = round(fair_debit, 1) if fair_debit is not None else None
    base["max_profit_pct"] = round(width - fair_debit, 1) if (width is not None and fair_debit is not None) else None
    base["required_max_premium_pct"] = round(fair_debit, 1) if fair_debit is not None else None
    base["market_premium_pct"] = None; base["edge_pct"] = None
    return {**base, "verdict": "NEEDS LIVE PREMIUM",
            "reason": "defined-risk vertical passes model gates; supply a live net-debit to check edge"
                      + ("" if in_grid else " (NOTE: breakeven beyond strike grid)")}


def _verticals_for(name, tenor):
    """Return list of (k_long, k_short, struct_cell) debit call spreads from spread_lens for name/tenor."""
    out = []
    cell = SPREADS["names"].get(name, {}).get("tenors", {}).get(tenor, {})
    for key, struct in cell.items():
        if "/" in key and isinstance(struct, dict) and "fair_debit_pct" in struct:
            try:
                kl, ks = (float(x) for x in key.split("/"))
            except ValueError:
                continue
            if kl < ks:                      # debit call spread (long lower strike)
                out.append((kl, ks, struct))
    return out


def run(names, tenors=None, strikes=None, structures=("single",), mode="analysis", live_premiums=None,
        min_edge=0.0, min_p_profit=None, max_debit_pct=None):
    tenors = tenors or _TENOR_ORDER
    strikes = strikes or DEFAULT_STRIKES
    structures = tuple(structures)
    survivors, rejected, pending = [], [], []

    def _emit(r):
        if r["verdict"] in ("PASS", "CAUTION"):
            pp = r.get("p_profit")
            if min_p_profit is not None and (pp is None or pp < min_p_profit) and r["verdict"] == "PASS":
                rejected.append({**r, "verdict": "REJECT", "reason": f"P(profit) {pp} < min {min_p_profit}"}); return
            survivors.append(r)
        elif r["verdict"] == "NEEDS LIVE PREMIUM":
            (pending if mode == "live" else survivors).append(r)
        else:
            rejected.append(r)

    if mode == "live" and live_premiums:
        # structure-aware keys: 'NAME|tenor|ratio'  OR  'NAME|tenor|single|ratio'  OR 'NAME|tenor|vertical|kl/ks'
        for key, prem in live_premiums.items():
            parts = key.split("|")
            if len(parts) == 3:
                name, tenor, spec = parts; struct = "single"
            elif len(parts) == 4:
                name, tenor, struct, spec = parts
            else:
                rejected.append({"name": key, "verdict": "REJECT", "reason": "bad key (NAME|tenor|ratio or NAME|tenor|struct|spec)"}); continue
            if name not in LENS["names"] or tenor not in LENS["names"].get(name, {}):
                rejected.append({"name": name, "verdict": "REJECT", "reason": f"{name} {tenor} not in options_lens"}); continue
            if struct == "single":
                _emit(screen_single(name, tenor, float(spec), mode="live", live_premium_pct=prem,
                                    min_edge=min_edge, max_debit_pct=max_debit_pct))
            elif struct == "vertical":
                kl, ks = (float(x) for x in spec.split("/"))
                cells = {f"{a:.2f}/{b:.2f}": s for a, b, s in _verticals_for(name, tenor)}
                struct_cell = cells.get(f"{kl:.2f}/{ks:.2f}") or {"fair_debit_pct": None, "width_pct": (ks-kl)*100}
                _emit(screen_vertical(name, tenor, kl, ks, struct_cell, mode="live", live_premium_pct=prem,
                                      min_edge=min_edge, max_debit_pct=max_debit_pct))
    else:
        for name in names:
            if name not in LENS["names"]:
                rejected.append({"name": name, "verdict": "REJECT", "reason": f"{name} not in options_lens"}); continue
            for tenor in tenors:
                if tenor not in LENS["names"][name]:
                    continue
                if "single" in structures:
                    for ratio in strikes:
                        _emit(screen_single(name, tenor, ratio, mode="analysis", min_edge=min_edge, max_debit_pct=max_debit_pct))
                if "vertical" in structures:
                    for kl, ks, struct_cell in _verticals_for(name, tenor):
                        _emit(screen_vertical(name, tenor, kl, ks, struct_cell, mode="analysis",
                                              min_edge=min_edge, max_debit_pct=max_debit_pct))

    _TIMING_RANK = {"high": 0, "medium": 1, "low": 2, "rejected": 3}
    if mode == "live":
        def keyf(r):
            pp = r.get("p_profit") or 0
            debit = r.get("market_premium_pct") or r.get("model_fair_pct") or 1
            edge = r.get("edge_pct") or 0
            return (-pp, -(edge / debit if debit else 0), _TENOR_ORDER.index(r["tenor"]))
    else:
        def keyf(r):
            return (_TIMING_RANK.get(r["timing_confidence"], 3), -(r.get("p_itm") or 0),
                    _TENOR_ORDER.index(r["tenor"]))
    survivors.sort(key=keyf)
    return {"mode": mode, "rate": RATE, "structures": list(structures),
            "survivors": survivors, "rejected": rejected, "pending": pending,
            "disclaimer": "GATED SCREENER (single calls + debit verticals) -- NOT a validated optimizer; NOT advice. Ranks, does not size."}


def _fmt(out, top=12):
    print(f"MODE: {out['mode']}   (rate {out['rate']:.3f})   structures: {','.join(out.get('structures',['single']))}"
          f"   survivors: {len(out['survivors'])}   rejected: {len(out['rejected'])}")
    if out["mode"] == "analysis":
        print("ANALYSIS MODE: no live premium supplied -- NO candidate can read PASS.")
        print("Rows are ordered by GATE QUALITY / TIMING CONFIDENCE / P(ITM), NOT by P(profit).")
        print("(P(profit at fair) ~ 0.5 by construction, so it is not a discriminator here.)")
        print("Live mode (--premiums) is required for a P(profit) ranking.\n")
    pcol = "P(prof)" if out["mode"] == "live" else "P@fair"
    hdr = f"{'name':10s}{'struct':10s}{'ten':5s}{'strike':>11s}{'gate':26s}{'fair%':>6s}{'P(ITM)':>7s}{pcol:>8s}{'timing':>8s}  verdict"
    print(hdr); print("-" * len(hdr))
    for r in out["survivors"][:top]:
        pp = r.get("p_profit"); pp = pp if pp is not None else r.get("p_profit_at_fair")
        sr = r["strike_ratio"]; sr = f"{sr:.2f}" if isinstance(sr, (int, float)) else str(sr)
        pp_txt = f"{pp:.2f}" if pp is not None else ("n/a*" if not r.get("p_profit_in_grid", True) else "n/a")
        print(f"{r['name'][:10]:10s}{r['structure'][:10]:10s}{r['tenor']:5s}{sr:>11s}"
              f"{r['gate'][:26]:26s}{(r['model_fair_pct'] or 0):>6.1f}{(r['p_itm'] or 0):>7.2f}"
              f"{pp_txt:>8s}{r['timing_confidence']:>8s}  {r['verdict']}")
    order = "P(profit)" if out["mode"] == "live" else "timing/P(ITM)"
    print(f"\n  [showing top {min(top,len(out['survivors']))} of {len(out['survivors'])} survivors, ordered by {order}]")
    if out.get("pending"):
        print(f"  [{len(out['pending'])} more passed gates but await a live premium -- not ranked]")
    print("  n/a* = P(profit) breakeven beyond the model strike grid -- extend options_lens, do not trust a clamp.")
    from collections import Counter
    tally = Counter(r["reason"].split(" -- ")[0].split(" (")[0] for r in out["rejected"])
    print("\nREJECTED (by reason):")
    for reason, n in tally.most_common(8):
        print(f"  {n:4d}  {reason}")
    print("\nP(profit) is HIGH-confidence only in the long-dated deep-ITM regime; LOW where it leans on the")
    print("unvalidated recovery-timing axis. Every row is physical-measure / IV-blind / timing-unvalidated.")
    print("A live premium + broker_bridge (IV/spread/liquidity) are REQUIRED before any 'PASS' is a real trade.")
    print("GATED SCREENER -- NOT a validated optimizer. Ranks candidates; sizes nothing. NOT INVESTMENT ADVICE.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="gated option screener: single calls + debit verticals (lexicographic vetoes, then rank)")
    ap.add_argument("names", nargs="*", help="names to screen (default: representative set)")
    ap.add_argument("--mode", choices=["analysis", "live"], default="analysis")
    ap.add_argument("--structures", nargs="+", choices=["single", "vertical"], default=["single", "vertical"],
                    help="structure types to screen (single calls and/or debit verticals; flies/tail-kickers NOT yet supported -- use spread_lens/premium_check)")
    ap.add_argument("--premiums", help="JSON of live premiums keyed 'NAME|tenor|ratio' or 'NAME|tenor|vertical|kl/ks' -> %% (auto-sets live mode)")
    ap.add_argument("--min-edge", type=float, default=0.0)
    ap.add_argument("--min-pprofit", type=float, default=None)
    ap.add_argument("--max-debit", type=float, default=None)
    ap.add_argument("--top", type=int, default=12)
    args = ap.parse_args()
    names = args.names or ["NVIDIA", "AMD", "Micron", "Broadcom", "Qualcomm", "Marvell", "Palantir",
                           "Astera Labs", "ARM", "CoreWeave", "IonQ", "DRAM (Roundhill Memory)", "SMH (VanEck Semis)"]
    live = None; mode = args.mode
    if args.premiums:
        live = json.load(open(args.premiums)); mode = "live"   # supplying real premiums auto-upgrades to live
    out = run(names, structures=args.structures, mode=mode, live_premiums=live, min_edge=args.min_edge,
              min_p_profit=args.min_pprofit, max_debit_pct=args.max_debit)
    _fmt(out, top=args.top)
