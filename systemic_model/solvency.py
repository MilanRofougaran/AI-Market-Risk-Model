"""
============================================================================
 SOLVENCY -- financing/impairment hazard, GATED BY revenue durability
============================================================================
 Encodes the user's thesis: a high-growth name with weak financials (cash burn
 and/or heavy debt) is NOT doomed by a crash -- it recovers fine IF its revenue
 keeps compounding (it can refinance / raise equity on the strength of the
 growth, and grows into the balance sheet). It becomes a PERMANENT impairment
 only if revenue ALSO craters: then the equity raise happens at the lows
 (dilution death-spiral), debt can't be refinanced (distress), or it fails.

 So solvency risk is an INTERACTION, not a sum:

     financing_fragility = 0.60*funding_need + 0.40*debt_load        (0..1)
     impairment_hazard   = SOLVENCY_MAX * financing_fragility
                                        * (1 - rev_durability)        (0..1)

 - Strong revenue durability (mission-critical, diversified, secular) -> the
   (1 - rev_durability) term -> ~0, so even a cash-burner gets ~no extra
   permanent risk (growth funds the recovery). This is the "unless revenue
   stays solid" clause you described.
 - Weak revenue durability AND weak financials -> hazard is large.

 The hazard is applied ONLY to DEEP, crisis-driven drawdowns (a >25% fall is
 the proxy for the bad regime actually hitting): on those paths the firm has
 probability `impairment_hazard` of NOT recovering (capital markets shut while
 it still needs cash). It therefore fattens the PERMANENT-loss tail
 (p_deep_permanent / p_never) for fragile names -- it does NOT change drawdown
 DEPTH (beta still sets depth). Mega-caps and durable-revenue names are ~0.

 Estimates; refresh like calibration.MACRO.  RESEARCH MODEL, NOT INVESTMENT ADVICE.
============================================================================
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "discovery"))
import extension_data as X

SOLVENCY_MAX = 0.60   # a fully-fragile, zero-durability name: up to 60% of its
                      # deep crisis drawdowns become permanent impairments
MIN_DEPTH = 0.30      # only drawdowns at least this deep can trigger impairment


def financing_fragility(funding_need, debt_load):
    return max(0.0, min(1.0, 0.60 * funding_need + 0.40 * debt_load))


def impairment_hazard(name):
    """P(a deep crisis-driven drawdown becomes PERMANENT) for this name.
    For a mapped ETF: diversification-damped holdings-weighted average.
    For a mapless ETF: an explicit class override (broad ~0, ARKK elevated)."""
    agg = etf_aggregate(name)
    if agg is not None:
        return agg["hazard"]
    if name in ETF_SOLV_OVERRIDE:
        return ETF_SOLV_OVERRIDE[name][0]
    return round(_stock_impairment(name), 4)


def report(names=None):
    """Per-name solvency table; high hazard = the bull/bear fork is dangerous."""
    import calibration as C, tam_bridge as TB
    if names is None:
        new, _ = TB.build_company_universe(base_companies=C.COMPANIES, verbose=False)
        for k, v in new.items():
            C.COMPANIES.setdefault(k, v)
        names = list(C.COMPANIES.keys())
    rows = []
    for nm in names:
        fn, dl, rd = X.solvency_inputs(nm)
        rows.append((nm, fn, dl, rd, financing_fragility(fn, dl), impairment_hazard(nm)))
    rows.sort(key=lambda r: -r[5])
    return rows


if __name__ == "__main__":
    print(f"{'Name':24s} {'fund':>5s} {'debt':>5s} {'revDur':>6s} {'fragility':>9s} {'IMPAIR-HAZ':>10s}")
    print("-" * 66)
    for nm, fn, dl, rd, fr, h in report():
        flag = "  <-- fragile fork" if h >= 0.10 else ("" if h > 0.01 else "  (durable/strong)")
        print(f"{nm[:24]:24s} {fn:5.2f} {dl:5.2f} {rd:6.2f} {fr:9.2f} {h*100:9.0f}%{flag}")


# ---------------------------------------------------------------------------
# TOXIC DILUTION ("reverse slingshot") -- the dark mirror of the buyback.
# A cash-poor / levered name that must RAISE equity at a deep crash low expands
# its float to survive, permanently crippling per-share value: even if total
# revenue recovers, the price never reclaims the peak because the pie was cut
# into more pieces. This is a CONTINUOUS per-share haircut applied to the paths
# that SURVIVE (the binary impairment_hazard wipes the rest), so it deepens the
# slow/incomplete-recovery middle of the distribution -- NOT the drawdown depth.
# Durable revenue eases the TERMS (raise higher, less dilutive); a fortress
# balance sheet never has to raise at the low, so its severity is ~0.
# ---------------------------------------------------------------------------
DILUTION_MAX = 0.20        # max permanent per-share haircut on a deep forced raise
DILUTION_MIN_DEPTH = 0.40  # only a deep crash (>40%) forces an emergency raise


def dilution_severity(name):
    """Per-share haircut a forced equity raise inflicts on a deep crash path.
    For a mapped ETF: diversification-damped holdings-weighted average.
    For a mapless ETF: an explicit class override."""
    agg = etf_aggregate(name)
    if agg is not None:
        return agg["dilution"]
    if name in ETF_SOLV_OVERRIDE:
        return ETF_SOLV_OVERRIDE[name][1]
    return round(max(0.0, _stock_dilution(name)), 4)

# ---------------------------------------------------------------------------
# ETF AGGREGATION -- why a basket is MORE predictable than its holdings.
# A single name's crash outcome is an idiosyncratic lottery (does THIS company
# hit the solvency wall, dilute, lose a customer). An ETF averages that away;
# what's left is the structural question: is the theme's TAM/SAM intact and
# still growing, and can the MAJORITY of holdings self-fund a recovery.
# So an ETF's solvency/dilution tail is the holdings-weighted average of its
# constituents' hazards, DAMPED by diversification (the whole basket almost
# never hits the wall at once -> idiosyncratic impairments cancel). A pure
# cash-burner thematic basket (quantum/SaaS) keeps a higher residual tail than
# a mega-cap basket, but BOTH are far below any single burner -- which is
# exactly why ETFs are "much less of a prediction issue."
# ---------------------------------------------------------------------------
# Concentration-aware diversification damp: a basket only cancels idiosyncratic
# impairments if it actually HAS many independent names. A 3-name correlated
# basket (DRAM) barely diversifies; a 10-name one does. damp = 0.95/sqrt(effN),
# clamped [0.2, 1.0] -> effN 3 -> 0.55, 7 -> 0.36, 10 -> 0.30, 1 -> ~1 (single name).
def _etf_damp(eff_n):
    import math as _m
    return max(0.20, min(1.0, 0.95 / _m.sqrt(max(eff_n, 1.0))))

# Mapless ETFs (no holdings map in ETF_HOLDINGS) get an explicit solvency class
# rather than the single-name SOLVENCY_DEFAULT -- so a broad index is ~0 and a
# concentrated cash-burner basket (ARKK) is correctly HIGH. (hazard, dilution)
ETF_SOLV_OVERRIDE = {
    "VOO (S&P 500)":        (0.000, 0.000),
    "SCHD (Dividend)":      (0.000, 0.000),
    "QQQ (Nasdaq-100)":     (0.005, 0.002),
    "VGT (Info Tech)":      (0.010, 0.004),
    "IGV (Software)":       (0.020, 0.008),
    "DTCR (Data Ctr Infra)":(0.020, 0.008),
    "GRID (Smart Grid)":    (0.020, 0.008),
    "NUKE (Nuclear/Uranium)":(0.030, 0.012),
    "ARKK (ARK Innovation)":(0.130, 0.055),   # concentrated basket of unprofitable burners
}


def _etf_holdings(name):
    try:
        import tam_bridge as TB
    except Exception:
        return None
    for etf, holds in getattr(TB, "ETF_HOLDINGS", {}).items():
        if etf == name or etf.split(" (")[0] == name.split(" (")[0]:
            return [(h, w) for h, w in holds.items() if not h.startswith("_")]
    return None


def etf_aggregate(name):
    """Holdings-weighted (hazard, dilution, theme_durability) for an ETF basket,
    damped by diversification (CONCENTRATION-AWARE: a narrow basket like DRAM
    behaves like its few holdings, a broad one diversifies). Returns None for
    non-ETF names; mapless ETFs are handled by ETF_SOLV_OVERRIDE in the callers."""
    items = _etf_holdings(name)
    if not items:
        return None
    tot = sum(w for _, w in items) or 1.0
    eff_n = 1.0 / sum((w / tot) ** 2 for _, w in items)     # effective # of holdings
    damp = _etf_damp(eff_n)
    haz = dil = dur = 0.0
    for h, w in items:
        wn = w / tot
        haz += wn * _stock_impairment(h)
        dil += wn * _stock_dilution(h)
        dur += wn * X.solvency_inputs(h)[2]
    return dict(hazard=round(damp * haz, 4), dilution=round(damp * dil, 4),
                theme_durability=round(dur, 3), eff_n=round(eff_n, 1), damp=round(damp, 2))


# rename the single-name primitives so the ETF aggregate can call them, and
# route the public functions through the ETF path when the name is a basket.
def _stock_impairment(name):
    fn, dl, rd = X.solvency_inputs(name)
    return SOLVENCY_MAX * financing_fragility(fn, dl) * (1.0 - rd)


def _stock_dilution(name):
    fn, dl, rd = X.solvency_inputs(name)
    bal = X.balance(name)
    cash_poor = max(0.0, (0.30 - bal) / 0.30)
    forced = max(fn, cash_poor)
    return min(DILUTION_MAX, DILUTION_MAX * forced * (0.5 + 0.5 * dl) * (1.0 - 0.5 * rd))
