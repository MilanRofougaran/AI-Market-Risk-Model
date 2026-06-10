"""
============================================================================
 MACRO_STRESS  --  systemic_model
============================================================================
 Turns the macro dashboard from DOCUMENTATION into a DRIVER of the tail.

 Until now the systemic-failure probability came from a hand-set catalyst
 premium; the debt / credit / leverage readings were recorded but never moved
 the math. This module builds a composite SYSTEMIC-STRESS INDEX from those
 readings and exposes multipliers that feed two places in the engine:
     1. the catalyst premium in calibration.derive_regime_probs() (reported tail)
     2. the crisis-entry transition probabilities in engine._simulate_factor()
        (the EMERGENT Monte-Carlo tail)
 so a stretched balance-sheet environment mechanically raises P(systemic) and a
 benign one lowers it.

 TWO SUB-SCORES, because they behave differently:
   STRUCTURAL FRAGILITY  -- how BAD a break would be: stretched valuation,
       record margin/leverage, high real rates, elevated household/corporate
       debt. A fragile system cracks hard from a small shock.
   ACUTE TRIGGER         -- how LIKELY a break is SOON: credit spreads (the
       CDS/credit proxy), volatility, a live oil/geopolitical shock, short
       interest. These spike right before/inside a crisis.
 A calm-but-stretched market (high structural, low acute) is the dangerous
 "complacency at the top" case — a moderate but FAT tail that can snap.

 Each factor is scored 0 (benign) -> 1 (critical) against documented bands, so
 every contribution is auditable. RESEARCH MODEL, NOT INVESTMENT ADVICE.
============================================================================
"""

# fixed reference for "neutral" macro; the crisis multiplier is computed
# relative to the stress level captured at the last full calibration, so today's
# tuned tail is preserved and DRIFT in any factor moves it. Reset at a quarterly
# recalibration via recalibrate_baseline().
STRESS_BASELINE = 0.49
SENS = 1.15            # how hard stress moves the crisis odds around baseline

# field, label, benign(0), critical(1), weight, group. higher value = more stress
# unless invert=True. Bands are documented judgments from long-run history.
FACTORS = [
    # ---- STRUCTURAL FRAGILITY (how bad if it breaks) ----
    dict(key="shiller_cape",     label="valuation (CAPE)",        benign=24,  critical=45,  weight=0.17, group="structural"),
    dict(key="ust_10y_real",     label="real 10y yield",          benign=0.3, critical=2.6, weight=0.11, group="structural"),
    dict(key="margin_debt_yoy",  label="margin-debt growth (leverage)", benign=0.0, critical=0.40, weight=0.15, group="structural"),
    dict(key="household_debt_gdp", label="household debt / GDP",   benign=60,  critical=95,  weight=0.08, group="structural"),
    dict(key="corp_debt_gdp",    label="corporate debt / GDP",    benign=42,  critical=75,  weight=0.09, group="structural"),
    # ---- ACUTE TRIGGER (how likely to break soon) ----
    dict(key="hy_oas_bps",       label="high-yield credit spread", benign=300, critical=800, weight=0.14, group="acute"),
    dict(key="ig_oas_bps",       label="investment-grade spread",  benign=80,  critical=250, weight=0.05, group="acute"),
    dict(key="vix",              label="equity vol (VIX)",         benign=14,  critical=40,  weight=0.07, group="acute"),
    dict(key="move",             label="rates vol (MOVE)",         benign=60,  critical=140, weight=0.03, group="acute"),
    dict(key="brent_usd",        label="oil / geopolitical shock", benign=70,  critical=120, weight=0.06, group="acute"),
    dict(key="short_interest_pct", label="short interest",         benign=1.5, critical=5.0, weight=0.05, group="acute"),
    # ---- LIQUIDITY (the 2026 failure mode: air-pockets, not credit rot) ----
    dict(key="fed_net_liq_3m_pct", label="Fed net liquidity 3m chg", benign=2.0, critical=-6.0, weight=0.08, group="acute"),
    dict(key="mmf_dry_powder_gdp", label="MMF dry powder /GDP (buffer)", benign=26.0, critical=15.0, weight=0.06, group="structural"),
]


def _clip01(x):
    return max(0.0, min(1.0, x))


def _score_factor(f, macro):
    v = macro.get(f["key"])
    if v is None:
        return None
    lo, hi = f["benign"], f["critical"]
    s = (v - lo) / (hi - lo) if hi != lo else 0.0
    if f.get("invert"):
        s = 1 - s
    return _clip01(s)


def compute(macro):
    """Return the systemic-stress index and its full breakdown."""
    comps = []
    g_sum = {"structural": 0.0, "acute": 0.0}
    g_w = {"structural": 0.0, "acute": 0.0}
    for f in FACTORS:
        s = _score_factor(f, macro)
        if s is None:
            continue
        comps.append(dict(key=f["key"], label=f["label"], group=f["group"],
                          value=macro.get(f["key"]), score=round(s, 3), weight=f["weight"]))
        g_sum[f["group"]] += s * f["weight"]
        g_w[f["group"]] += f["weight"]
    structural = g_sum["structural"] / g_w["structural"] if g_w["structural"] else 0.0
    acute = g_sum["acute"] / g_w["acute"] if g_w["acute"] else 0.0
    # combine: structural carries the tail; acute adds the trigger; the max-term
    # means EITHER being high lifts the index (a fragile system OR an acute shock).
    score = _clip01(0.50 * structural + 0.30 * acute + 0.20 * max(structural, acute))
    return dict(score=round(score, 3), structural=round(structural, 3),
                acute=round(acute, 3), components=comps)


def crisis_mult(score, baseline=STRESS_BASELINE, sens=SENS):
    """Multiplier on crisis-entry probability / catalyst premium, relative to the
    baseline environment. >1 when stress exceeds baseline, <1 when calmer."""
    return max(0.5, min(1.8, 1.0 + sens * (score - baseline)))


# ---------------------------------------------------------------------------
# SYSTEMIC-FREEZE SEVERITY  --  how badly the financial plumbing is/can seize
# ---------------------------------------------------------------------------
# Distinct from the general 'acute' trigger: these are specifically the FUNDING-
# FREEZE signals. When they blow out (2008), credit intermediation stops, and a
# market collapse takes YEARS not months to recover -- the systemic-freeze layer
# in the engine uses this severity to set how long recovery is suspended.
# PANIC signals: how seized are credit & volatility markets (the freeze pressure).
FREEZE_SIGNALS = [
    dict(key="hy_oas_bps", benign=350, freeze=1400.0, w=0.35),  # junk credit shut
    dict(key="ig_oas_bps", benign=90,  freeze=450.0,  w=0.20),  # even IG stressed
    dict(key="move",       benign=70,  freeze=180.0,  w=0.20),  # rates/Treasury dislocation
    dict(key="vix",        benign=16,  freeze=65.0,   w=0.25),  # equity panic
]


def freeze_severity(macro):
    """[0,1] severity of a FUNDING freeze — how long the systemic-freeze layer suspends
    market-wide recovery after a deep collapse. The crucial historical lesson (2008 vs
    2020): panic alone doesn't freeze the system — a central-bank LIQUIDITY backstop can
    avert it. 2008 = panic + DRAINING liquidity -> multi-year freeze; 2020 = panic + a
    massive liquidity FLOOD -> no freeze, months-long recovery. So:
        severity = panic(credit+vol)  ×  liquidity_gate
    where the gate is ~1 when net liquidity is draining and falls toward a floor when the
    Fed is flooding (the backstop that breaks a freeze)."""
    s = w = 0.0
    for sig in FREEZE_SIGNALS:
        v = macro.get(sig["key"])
        if v is None:
            continue
        b, f = sig["benign"], sig["freeze"]
        s += max(0.0, min(1.0, (v - b) / (f - b))) * sig["w"]; w += sig["w"]
    panic = (s / w) if w else 0.0
    liq = macro.get("fed_net_liq_3m_pct", 0.0)          # +ve = injecting, -ve = draining
    gate = max(0.15, min(1.0, (2.0 - liq) / 14.0))      # drain(-12)->1.0 ; flood(+15)->floor 0.15
    return round(panic * gate, 3)


def grind_mult(structural, baseline=0.40, sens=3.0):
    """Multiplier on GRIND-entry probability. Driven purely by STRUCTURAL
    fragility (valuation, real rates, leverage, thin dry powder) -- a market
    can slide into a de-rating year while the acute trigger (VIX, spreads)
    stays asleep. That decoupling is the 2022 lesson."""
    return max(0.2, min(4.0, 1.0 + sens * (structural - baseline)))


def effective_transition(base_transition, stress):
    """Scale escalation probabilities and renormalize each row.
    - ACUTE/composite stress scales crisis-entry (panic channel).
    - STRUCTURAL stress scales grind-entry (de-rating channel) on 4x4 matrices.
    `stress` may be the full compute() dict, or a float score (legacy 3x3)."""
    if isinstance(stress, dict):
        score = stress["score"]; structural = stress.get("structural", score)
    else:
        score = float(stress); structural = score
    cm = crisis_mult(score)
    dm = grind_mult(structural)
    T = [row[:] for row in base_transition]
    four = len(T[0]) > 3
    for i, esc_cols in [(0, (1, 2)), (1, (2,))]:
        for j in esc_cols:
            T[i][j] = T[i][j] * cm
        if four:
            T[i][3] = T[i][3] * dm          # structural drives the grind door
    if four and len(T) > 3:
        T[3][1] *= cm; T[3][2] *= cm        # a grind can still snap into panic
    for i in range(len(T)):
        off = sum(T[i][j] for j in range(len(T[i])) if j != i)
        T[i][i] = max(0.0, 1.0 - off)
    return T


def stress_label(score):
    if score < 0.35:
        return "benign"
    if score < 0.55:
        return "moderate (watch-zone)"
    if score < 0.72:
        return "elevated"
    return "critical"


def print_report(macro):
    r = compute(macro)
    m = crisis_mult(r["score"])
    print("=" * 70)
    print(f"SYSTEMIC-STRESS INDEX = {r['score']*100:.0f}/100  ({stress_label(r['score'])})")
    print(f"  structural fragility {r['structural']*100:.0f}  |  acute trigger {r['acute']*100:.0f}"
          f"  ->  crisis multiplier x{m:.2f}  (baseline {STRESS_BASELINE*100:.0f})")
    print("=" * 70)
    for grp in ("structural", "acute"):
        print(f"\n  {grp.upper()}:")
        for c in r["components"]:
            if c["group"] == grp:
                bar = "#" * int(c["score"] * 20)
                print(f"    {c['label']:30s} {str(c['value']):>8} -> {c['score']*100:3.0f}  {bar}")
    print(f"\n  Reading: structural = how deep a break would be; acute = how soon."
          f"\n  x{m:.2f} scales the crisis-entry odds and the catalyst premium vs baseline.")
    return r


if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import calibration as C
    print_report(C.MACRO)
