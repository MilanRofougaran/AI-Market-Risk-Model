"""
============================================================================
 CRASH_GROWTH -- does the theme's GROWTH RATE persist, dip, or break post-crash?
============================================================================
 The single most important ETF/stock recovery variable (per the reviewers and
 the user's thesis): after a crash, what happens to the REVENUE-GROWTH RATE of
 the underlying market -- not just the stock price. The model previously treated
 tam_cagr as constant and leaned on the impairment hazard to stand in for
 cyclicality. This module makes the growth response explicit, in three archetypes:

   SECULAR  -- demand is mission-critical and keeps compounding straight through
               a financial selloff (AI compute, networking, data-center power,
               software). Growth HOLDS or slightly ACCELERATES (survivors take
               share). recovery_g_mult ~ 1.0-1.1  -> fast recovery.
   CYCLICAL -- the dollar-TAM itself is cyclical (memory/DRAM, commodity chips):
               in a glut ASPs and revenue collapse, then snap back with the next
               upcycle. A V-shape: growth DIPS then REBOUNDS, so net recovery
               growth over the window is DAMPED but positive. recovery_g_mult ~
               0.7-0.85  -> deeper/slower but still recovers (NOT a permanent trap).
   BROKEN   -- the crash invalidates the demand thesis (over-hyped niche, demand
               was the bubble). Growth STEPS DOWN persistently. recovery_g_mult ~
               0.4-0.6  -> structural impairment.

 Classification is derived from existing inputs (revenue durability, earnings
 quality) plus an explicit per-name/theme override, so it stays auditable.
 The multiplier feeds the DETERMINISTIC earn-back clock's effective growth
 (fundamental_catchup) -- a cyclical theme earns back on a depressed-then-rebound
 growth path. ESTIMATES. RESEARCH MODEL, NOT INVESTMENT ADVICE.
============================================================================
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "discovery"))
import extension_data as X

# Explicit overrides where the archetype is clear and not well-captured by the
# durability/earn-quality heuristic alone. (name or ETF -> archetype)
ARCHETYPE = {
    # cyclical dollar-TAM (the demand & pricing itself cycles, not just the stock)
    "Micron": "cyclical", "Kioxia": "cyclical", "DRAM (Roundhill Memory)": "cyclical",
    "Applied Optoelectronics": "cyclical",
    # broken-thesis risk (price is a call option on a not-yet-real market)
    "IonQ": "broken", "QTUM (Defiance Quantum)": "broken",
    # ARKK: concentrated basket of unprofitable disruptive names; re-rated
    # permanently lower after 2021 (never reclaimed highs) and flagged fragile in
    # ETF_SOLV_OVERRIDE (0.13 hazard). "broken" keeps the two channels consistent;
    # change to "cyclical" if you view it as deeper-but-eventually-recovering.
    "ARKK (ARK Innovation)": "broken",
    # everything else falls through to the heuristic below
}
# recovery-growth multiplier per archetype (net over the recovery window)
MULT = {"secular": 1.05, "cyclical": 0.78, "broken": 0.50}


def archetype(name):
    """secular / cyclical / broken, from override else durability+earn_quality."""
    base = name.split(" (")[0].strip()
    for k, v in ARCHETYPE.items():
        if k.split(" (")[0].lower() == base.lower() or k == name:
            return v
    fn, dl, rd = X.solvency_inputs(name)          # rd = revenue durability
    earnq_proxy = 1.0 - fn                          # crude: heavy funding-need => weak earnings
    if rd >= 0.70:
        return "secular"
    if rd >= 0.45:
        return "cyclical"
    return "broken" if (fn >= 0.6 or rd < 0.35) else "cyclical"


def recovery_g_mult(name):
    """Multiplier on the EARN-BACK effective growth (dip-then-rebound for cyclical;
    hold/accelerate for secular; step-down for broken)."""
    return MULT[archetype(name)]


def report(names):
    return [(nm, archetype(nm), recovery_g_mult(nm)) for nm in names]


if __name__ == "__main__":
    import calibration as C, tam_bridge as TB
    new, _ = TB.build_company_universe(base_companies=C.COMPANIES, verbose=False)
    for k, v in new.items():
        C.COMPANIES.setdefault(k, v)
    rows = sorted(((nm, archetype(nm), recovery_g_mult(nm)) for nm in C.COMPANIES),
                  key=lambda r: r[2])
    print(f"{'Name':26s} {'archetype':10s} {'recov-g x':>9s}  growth response after a crash")
    print("-" * 78)
    desc = {"secular": "holds / accelerates -> fast recovery",
            "cyclical": "dips then V-rebounds -> deeper but recovers",
            "broken": "steps down -> structural impairment"}
    for nm, a, m in rows:
        print(f"{nm[:26]:26s} {a:10s} {m:9.2f}  {desc[a]}")
