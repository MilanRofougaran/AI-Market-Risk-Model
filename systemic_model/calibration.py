"""
============================================================================
 CALIBRATION  --  systemic_model
============================================================================
 THIS IS THE ONLY FILE YOU EDIT WHEN THE WORLD CHANGES.

 Everything here is a description of the market as of a point in time. The
 engine (engine.py) reads these numbers but never contains them, so to bring
 the model up to date you change values HERE and re-run. You should not need
 to touch the mathematics.

 HOW TO UPDATE (the monthly / quarterly ritual):
   1. Update AS_OF_DATE.
   2. Update MACRO (valuation, rates, credit, vol) from your dashboard.
   3. Re-derive REGIME_PROBS if your view of the cycle has shifted
      (the helper at the bottom shows how the hazard transform produces them).
   4. Update each company's revenue, TAM, and the four judgment scores in
      COMPANIES as new earnings / TAM estimates arrive.
   5. Re-run run.py.  Everything downstream updates automatically.

 EVERY number below is tagged:
   [MEASURED]  = an observed market figure (update from primary sources)
   [DERIVED]   = a modeled value (changes only if your method changes)
   [JUDGMENT]  = a calibrated opinion (the honest, sweepable inputs)
============================================================================
"""
import macro_stress as MS

AS_OF_DATE = "2026-06-05"

# ---------------------------------------------------------------------------
# 1. MACRO DASHBOARD  [MEASURED]
#    The live tape. These do not enter the simulation arithmetic directly
#    (the engine works in regimes and betas), but they are the evidence base
#    that justifies the regime probabilities and the catalyst premium below,
#    and they are recorded here so the model is self-documenting: anyone
#    reading it can see exactly what world it was calibrated to.
# ---------------------------------------------------------------------------
MACRO = {
    "sp500_forward_pe":       21.9,    # Jun 5: down on the -2.6% S&P selloff
    "sp500_trailing_pe":      28.6,    # provider-dependent (25-32x range)
    "shiller_cape":           39.4,    # Jun 5: down on the selloff
    "buffett_indicator_pct":  238.0,   # GuruFocus, record
    "equity_risk_premium":    -1.4,    # MacroMicro (StreetStats shows +5.3; wide disagreement)
    "ust_10y":                4.70,    # Jun 5: hot jobs spiked yields, 20/30y > 5%
    "ust_10y_real":           2.25,    # TIPS; >2% real is a structural headwind
    "fed_funds_mid":          3.625,   # 3.50-3.75 band; Warsh sworn in mid-May 2026
    "fed_next_move_bias":     "hike",  # Jun 5: hot jobs (172k) revived hike bets
    "core_pce_yoy":           3.3,
    "vix":                    24.0,    # Jun 5: SPIKED on the -2.6% S&P / semis crash
    "move":                   95.0,    # rates vol jumped with the yield spike
    "brent_usd":              96.0,    # not today's driver (jobs/rates were)
    "hormuz_status":          "subdued; today's shock was jobs->rates, not oil",
    "margin_debt_tn":         1.304,   # FINRA record
    "hyperscaler_capex_bn":   700,     # ~$602-725B 2026, ~75% AI-directed
    # ---- balance-sheet & credit stress inputs (feed macro_stress.py) ----
    "hy_oas_bps":             312,     # Jun 5: spreads widened on the risk-off move
    "ig_oas_bps":             85,      # ICE BofA US IG OAS (tight)
    "household_debt_gdp":     60.3,    # Fed Z.1, Q1 2026 (healthy, ~60%)
    "corp_debt_gdp":          47.0,    # nonfinancial corp debt ~$14.2T / GDP
    "margin_debt_yoy":        0.45,    # FINRA margin debt ~$1.3T, +45-53% YoY, record (LEVERAGE)
    "short_interest_pct":     2.0,     # market-level short interest (~normal)
    # liquidity (the 2026 failure mode: air-pockets, not credit rot). ESTIMATES.
    "fed_net_liq_3m_pct":     -1.5,    # Fed bal.sheet - TGA - RRP, 3m % change (QT drains)
    "mmf_dry_powder_gdp":     25.5,    # money-market fund assets ~$7.5tn / GDP ~$29.5tn (%)
}

# ---------------------------------------------------------------------------
# 1b. SYSTEMIC-STRESS INDEX  [DERIVED from MACRO]
#     Composite of the balance-sheet/credit/leverage readings above, split into
#     structural fragility and acute trigger. It feeds the catalyst premium and
#     the crisis-entry transition probabilities so the macro environment
#     mechanically moves the tail. See macro_stress.py for the bands.
# ---------------------------------------------------------------------------
SYSTEMIC_STRESS = MS.compute(MACRO)
STRESS_CRISIS_MULT = MS.crisis_mult(SYSTEMIC_STRESS["score"])

# ---------------------------------------------------------------------------
# SYSTEMIC FREEZE  --  total-collapse recovery contagion (the 2008 case)
# ---------------------------------------------------------------------------
# Every other recovery channel assumes NO total collapse: each name heals at its
# own fundamental speed. But when the macro economy fails -- a keystone sub-market
# (banking/credit) freezing the plumbing the whole economy runs on -- recovery is
# suspended for EVERY sub-market at once, healthy names included (2008: the S&P
# took ~5.5 years to reclaim its peak). This is recovery-SIDE contagion, the
# complement to the drawdown-side correlation spike we already model.
#   - It fires only on the deep-collapse TAIL: paths where the broad market itself
#     falls past COLLAPSE_DEPTH (a normal -25/-35% bear does NOT freeze the system).
#   - When it fires, recovery for any name that fell is floored at a freeze window.
#   - The window is longer when FUNDING stress (HY/IG spreads, MOVE, net liquidity,
#     VIX) is acute -- a true credit seizure freezes longer than a liquidity scare.
SYSTEMIC_FREEZE = dict(
    collapse_depth=0.55,        # broad-market drawdown that breaks the plumbing (systemic tail, not a normal bear)
    base_freeze_months=30,      # recovery DELAY added at full severity (2008 took ~5.5y peak-to-peak)
    min_severity_floor=0.40,    # even a mild freeze adds this fraction of the base delay
    # CROSS-SUBMARKET DEPENDENCY: the freeze is NOT uniform. Its severity scales by how
    # dependent each sub-market is on the frozen keystone (AI-infra = the compute/datacenter
    # "plumbing"). Infra freezes longest; a self-funded defensive sector thaws first. This
    # is "the collapse affected all layers — but unevenly" (the user's point).
    keystone_group="AI-infra",
    dependency={"AI-infra": 1.00, "AI-platform": 0.80, "disruptive": 0.65, "defensive": 0.35},
    dependency_default=0.70,
)
FREEZE_SEVERITY = MS.freeze_severity(MACRO)   # [0,1] from acute funding stress; low in calm regimes

# ---------------------------------------------------------------------------
# 2. REGIME PROBABILITIES  [DERIVED]
#    The probability that the WORST drawdown event within each horizon falls
#    in each regime bucket. These are mutually exclusive and sum to 1.0.
#    Derived via the hazard transform (see helper at bottom) from 5-year base
#    rates, then lifted by a horizon-growing catalyst premium for the live
#    oil / Fed-hike backdrop. To re-derive, edit BASE_RATES_5YR and the
#    CATALYST_PREMIUM below and call derive_regime_probs().
# ---------------------------------------------------------------------------
REGIME_PROBS = {
    #            6m     12m    18m
    "benign":    [0.48, 0.38, 0.31],   # max drawdown < 10%
    "correction":[0.38, 0.40, 0.40],   # 10-20%, fast recovery
    "bear":      [0.11, 0.16, 0.20],   # 20-35%
    "systemic":  [0.03, 0.06, 0.09],   # >35% + credit/funding freeze
}
HORIZON_LABELS = ["6m", "12m", "18m"]
HORIZON_DAYS   = [126, 252, 378]       # trading days

# Recover-after-trough horizons for the drawdown x recovery probability matrix
# (the answer to "if it falls within 6/12/18m, P(it's recovered within 6/12/18/24/36m?)").
RECOVERY_AFTER_TROUGH_MONTHS = [6, 12, 18, 24, 36]

# ---------------------------------------------------------------------------
# CYCLICAL DEMAND PATH (per theme; "only edit when the world changes")
# ---------------------------------------------------------------------------
# A cyclical name's crash usually COINCIDES with a demand down-cycle: the price
# rolls over as the cycle turns and earnings keep falling for a while AFTER the
# drawdown, so the price genuinely cannot reclaim its prior peak in the first
# few months -- recovery is BACK-LOADED, not just uniformly slower. We model an
# explicit two-phase trough: demand falls (a deeper second leg) and recovery is
# SUPPRESSED until the demand cycle clears (demand_down + stabilization months),
# after which the rebound is allowed. Memory (DRAM/NAND) cycles have historically
# run ~12-18 months peak-to-trough; we use 9 + 6 = ~15 months of suppression.
# This is distinct from (and replaces, for cyclicals) the flat crash-growth
# recov_shift slowdown -- it shapes the recovery curve flat-early / steep-late.
CYCLICAL_DEMAND_PATH = {
    # theme -> demand-down + stabilization window (suppression) and second-leg depth.
    # Memory has the longest, deepest demand cycle; optical is shorter/milder; broad
    # analog/industrial semis are mild and short. Calibrate from each cycle's history.
    "memory":      dict(demand_down_months=9, stabilization_months=6, second_leg=0.15),
    "optical":     dict(demand_down_months=6, stabilization_months=3, second_leg=0.08),
    "broad_semis": dict(demand_down_months=4, stabilization_months=4, second_leg=0.06),
}
# Explicit name -> cycle theme. ONLY names with a genuine, identifiable demand cycle
# are mapped; the two-phase trough is then shaped by that theme. A cyclical-archetype
# name that is NOT mapped here gets CYCLICAL_DEFAULT_THEME (None) -> it falls back to the
# flat crash-growth recovery slowdown rather than wrongly inheriting the memory clock.
# (Reviewer consensus: do not apply the memory 9+6m / 15% trough to every "cyclical" name
# -- AMD, Tesla, CoreWeave, AppLovin, Vertiv do not follow a memory-style demand cycle.)
CYCLICAL_THEME = {
    "Micron": "memory", "Kioxia": "memory", "SK Hynix": "memory",
    "Samsung": "memory", "DRAM (Roundhill Memory)": "memory",
    "Lumentum": "optical", "Coherent": "optical", "Applied Optoelectronics": "optical",
    "Marvell": "broad_semis", "Qualcomm": "broad_semis", "Texas Instruments": "broad_semis",
}
CYCLICAL_DEFAULT_THEME = None          # unmapped cyclicals -> flat proxy, NOT memory

# Inputs that PRODUCE the systemic row above, kept so the derivation is auditable.
BASE_RATES_5YR = {                     # P(>=1 occurrence in 5 years), historical
    "bear":     0.28,                  # ~1 bear / 6.5y
    "systemic": 0.12,                  # ~5 systemic episodes / 97y
}
CATALYST_PREMIUM = {                   # horizon-growing multiplier on the hazard tail
    "bear":     [1.6, 1.9, 2.2],
    "systemic": [1.8, 2.4, 3.0],
}
# Independent cross-check: the simulation's emergent systemic tail vs. this
# hazard-derived one. We report BOTH and reconcile to a range in the output.
SYSTEMIC_TAIL_RECONCILED = {"6m": (0.02, 0.03), "12m": (0.04, 0.06), "18m": (0.06, 0.09)}

# ---------------------------------------------------------------------------
# 3. THE MACRO FACTOR (Phi): three-state daily volatility process  [DERIVED]
#    This is the engine's beating heart. Phi is the broad-market daily return;
#    every asset inherits it through beta. Three regimes, each an annualized
#    vol and drift; a transition matrix governs switching; Student-t adds tails.
#    These were tuned so the simulation's emergent regime mix matches
#    REGIME_PROBS and the deep tail matches history -- NOT fit to a price
#    series. Change them only if your view of how markets behave changes.
# ---------------------------------------------------------------------------
# FOUR states (2022-backtest finding: panics are not the only bear shape).
# State 3 "de-rating/grind" = sustained rate-driven multiple compression:
# moderate vol (VIX never spikes), persistent negative drift, very sticky.
# Entry is driven by STRUCTURAL fragility (CAPE, real rates, leverage), not
# the acute trigger -- exactly the regime 2022 lived in while VIX sat <37.
# Calibrated IN-SAMPLE to the 2022 episode; not yet validated out-of-sample.
FACTOR = {
    "vol_annual":   [0.115, 0.30, 0.55, 0.16],   # calm / stress / crisis / grind
    "drift_annual": [0.075, -0.06, -0.85, -0.09],
    "student_t_df": 4.0,                     # >2 keeps variance finite; 4 = realistic crashes
    # daily transition matrix rows: [stay, ->stress, ->crisis, ->grind]. Rows sum to 1.
    # GRIND CALIBRATION (fixed 2026-06-08): the grind is a MINORITY de-rating
    # regime, NOT a secular bear. The prior calibration (entry 0.0030, stay
    # 0.990, drift -20%) made grind occupy ~31% of the stationary timeline and
    # dragged the blended long-run market drift to -5.4%/yr -- so NOTHING
    # recovered (even VOO showed ~78% never-recover-by-4.5y). A beta=1 equity
    # must have POSITIVE long-run drift. Now: rarer entry, ~56-day spells, and a
    # milder -9%/yr grind drift -> grind ~7% occupancy at today's stress and
    # blended drift +1.3%/yr (near the validated pre-grind +2.3%). The grind
    # still BITES while active (drift + grind_drag on high-val-gap names) and
    # still fires in the 2022 backtest -- it just no longer breaks recovery.
    "transition": [
        [0.9910, 0.0077, 0.0005, 0.0008],   # from calm   (->grind 0.0008, x stress-mult at runtime)
        [0.0680, 0.9255, 0.0055, 0.0010],   # from stress (->grind 0.0010)
        [0.0000, 0.0240, 0.9760, 0.0000],   # from crisis (snaps back via stress)
        [0.0030, 0.0150, 0.0000, 0.9820],   # from grind  (mean spell ~56d, re-enterable)
    ],
}

# ---------------------------------------------------------------------------
# 4. BROAD EXPOSURES  [DERIVED betas, JUDGMENT alphas]
#    The index-level sleeves. beta is the loading on Phi; idio is the width of
#    the private daily wobble; alpha is a small annual drift tilt; L is the
#    leverage multiple (with a daily reset + fee/borrow drag for L>1).
# ---------------------------------------------------------------------------
EXPOSURES = {
    "S&P 500":          dict(beta=1.00, idio=0.00, alpha= 0.000, L=1, leveraged=False),
    "Equal-weight S&P": dict(beta=0.90, idio=0.04, alpha=-0.005, L=1, leveraged=False),
    "Mega-cap tech":    dict(beta=1.20, idio=0.05, alpha= 0.015, L=1, leveraged=False),
    "Nasdaq-100":       dict(beta=1.15, idio=0.06, alpha= 0.010, L=1, leveraged=False),
    "Semis (SOXX)":     dict(beta=1.35, idio=0.12, alpha= 0.030, L=1, leveraged=False),
    "Russell 2000":     dict(beta=1.15, idio=0.10, alpha=-0.020, L=1, leveraged=False),
    "HY credit proxy":  dict(beta=0.40, idio=0.03, alpha= 0.005, L=1, leveraged=False),
    "SOXL (3x semis)":  dict(beta=1.35, idio=0.12, alpha= 0.030, L=3, leveraged=True),
    "TQQQ (3x NDX)":    dict(beta=1.15, idio=0.06, alpha= 0.010, L=3, leveraged=True),
    # TECL is a 3x DAILY-RESET leveraged tech ETF -- a trading vehicle, not a
    # growth holding. Modeled here (not as a TAM company) so the engine applies
    # its volatility-decay math honestly over the mandate. [added Jun 2026]
    "TECL (3x tech)":   dict(beta=1.15, idio=0.06, alpha= 0.010, L=3, leveraged=True),
}
LEVERAGE_DRAG = {"fee": 0.010, "borrow": 0.0125}   # annual, for leveraged products

# ---------------------------------------------------------------------------
# 5. COMPANY-LEVEL TAM DATA  --  the bottom-up layer
#    For each name we store the MEASURED facts (revenue, TAM, multiple) and the
#    JUDGMENT scores. The engine turns these into a premium decomposition and a
#    recovery modifier. Every judgment score is swept in run.py so you can see
#    which conclusions are robust.
#
#    Fields:
#      rev_bn        [MEASURED]  current relevant-segment revenue ($bn)
#      tam_bn        [MEASURED]  narrow hardware TAM it addresses ($bn)
#      tam_cagr      [MEASURED]  growth rate of that TAM (decimal/yr)
#      fwd_pe        [MEASURED]  forward P/E (the observed premium)
#      beta          [DERIVED]   loading on the macro factor
#      quality       [JUDGMENT]  TAM credibility (1=customer-anchored, low=soft/cyclical)
#      earn_quality  [JUDGMENT]  earnings durability (1=secular, low=price-spike/cyclical)
#      dominance     [JUDGMENT]  market-share capture / moat (1=monopoly, low=fragmented)
#                                ^ imported from Gemini's TDVM: a large TAM is
#                                  worth less if you cannot defend your share.
#      capex_elastic [JUDGMENT]  does demand survive a credit crash?
#                                (1=physical/inelastic, low=discretionary)
#                                ^ also from TDVM: governs crisis-state survival.
#      role          note
# ---------------------------------------------------------------------------
COMPANIES = {
 "NVIDIA":   dict(rev_bn=193.7, tam_bn=500, tam_cagr=0.45, fwd_pe=30, beta=1.45,
                  quality=0.90, earn_quality=0.85, dominance=0.85, capex_elastic=0.55,
                  role="DC accelerator leader; ~80-85% share"),
 "Broadcom": dict(rev_bn=20.0,  tam_bn=75,  tam_cagr=0.40, fwd_pe=29, beta=1.30,
                  quality=0.85, earn_quality=0.85, dominance=0.70, capex_elastic=0.70,
                  role="custom ASIC + networking; ~70% custom-AI design"),
 "Micron":   dict(rev_bn=8.0,   tam_bn=35,  tam_cagr=0.40, fwd_pe=12, beta=1.35,
                  quality=0.65, earn_quality=0.45, dominance=0.30, capex_elastic=0.50,
                  role="HBM; revenue ASP-inflated, cyclical"),
 "Kioxia":   dict(rev_bn=14.8,  tam_bn=147, tam_cagr=0.05, fwd_pe=10, beta=1.30,
                  quality=0.25, earn_quality=0.30, dominance=0.20, capex_elastic=0.40,
                  role="NAND; commodity cycle, price-spike revenue"),
 "Marvell":  dict(rev_bn=6.0,   tam_bn=94,  tam_cagr=0.35, fwd_pe=24, beta=1.40,
                  quality=0.70, earn_quality=0.80, dominance=0.40, capex_elastic=0.70,
                  role="DC custom silicon + optics; contested vs AVGO"),
 "Qualcomm": dict(rev_bn=44.3,  tam_bn=900, tam_cagr=0.20, fwd_pe=14, beta=1.15,
                  quality=0.35, earn_quality=0.70, dominance=0.45, capex_elastic=0.50,
                  role="edge-AI leader; soft aggregate TAM, mature handset base"),
 "AMD":      dict(rev_bn=16.6,  tam_bn=500, tam_cagr=0.50, fwd_pe=27, beta=1.40,
                  quality=0.75, earn_quality=0.80, dominance=0.25, capex_elastic=0.55,
                  role="DC #2 + edge secondary; share-taker vs NVDA"),
 "ARM":      dict(rev_bn=4.0,   tam_bn=8,   tam_cagr=0.30, fwd_pe=70, beta=1.30,
                  quality=0.80, earn_quality=0.90, dominance=0.90, capex_elastic=0.70,
                  role="licensing/royalty; near-universal penetration, thin per-unit"),
}

# Baseline "no growth premium" multiple. Premium above this is what TAM must justify.
def _dynamic_base_pe(macro_dict):
    """v3: the no-growth base multiple FLOATS with the real rate. Anchored 18.0x
    (E/P 5.56%) at a 1.5% real 10y; E/P shifts ~1:1 with real rates away from that,
    bounded to [8.3x, 25x]. Higher real rates demand higher earnings yields and
    mechanically compress the base multiple TAM is allowed to justify."""
    if not macro_dict or "ust_10y_real" not in macro_dict:
        return 18.0
    real_rate = macro_dict.get("ust_10y_real", 2.25)
    ep_yield = 0.0556 + ((real_rate - 1.5) / 100.0)
    ep_yield = max(0.04, min(0.12, ep_yield))
    return float(round(1.0 / ep_yield, 1))

BASE_PE = _dynamic_base_pe(MACRO)

# After-tax yield forfeited when a firm spends cash on buybacks (≈0.75 × short
# T-bill, ~4.5% pre-tax in Jun-2026). Single source for the buyback accretion
# test (E/P > this) used by both fundamental_catchup and the engine slingshot.
CASH_YIELD_AFTER_TAX = 0.035

# ---------------------------------------------------------------------------
# 6. SIMULATION SETTINGS
# ---------------------------------------------------------------------------
SIM = {
    "n_paths":   150_000,   # raise for smoother tails (300k for final runs)
    "chunk":     25_000,    # memory-frugal batch size
    # Simulation length is kept GENEROUS on purpose. The model's job is to
    # DISTINGUISH a drawdown that recovers at month 16 from one that recovers at
    # month 30 from one that never recovers. To classify a drawdown as "did not
    # recover within the mandate," the sim must keep watching long enough to
    # confirm the recovery truly didn't arrive in time -- and long enough to see
    # where it eventually lands, so the dangerous tail is CHARACTERIZED, not
    # censored. A late-18m-horizon drawdown troughs near day 378 and needs ~18
    # more months to be judged fairly, so we run to ~882 days (378 + 504).
    # (This is the OPPOSITE of truncating to 378 -- truncation would blind the
    #  model to the very distinction it exists to make.)
    # The window grew over the review history as new mechanics needed more room to be
    # judged fairly: 378 -> 882 (38m) -> 1134 (full 36m after a late 18m trough) -> and now
    # 1764 once the SYSTEMIC-FREEZE layer was added, because a 2008-style freeze can stretch
    # recovery to ~5.5 years -- at 1134 days that heal would be right-censored into a false
    # "permanent loss". 7 years observes it as the long-but-finite recovery it is.
    "days":      1764,      # 7 trading years (see note above): observes multi-year systemic-freeze heals, uncensored
    "seed":      20260603,
}

# Recovery buckets for the recovery-time table (drawdown depth -> recovery stats)
RECOVERY_BUCKETS = [(0.10,0.15),(0.15,0.20),(0.20,0.25),(0.25,0.30),(0.30,0.40),(0.40,0.99)]

# ---------------------------------------------------------------------------
# THE ACCEPTABILITY MANDATE  --  what "survivable" means
# ---------------------------------------------------------------------------
# The model's true purpose is CATASTROPHE AVOIDANCE: prevent the permanent,
# systemic, mandate-breaking loss. Recovery is not the goal -- it is the
# EVIDENCE that a drawdown was survivable rather than fatal. The stated
# tolerance: a drawdown that recovers within ~4-18 months is acceptable; one
# that drags past 18 months is a systemic threat.
#
# So the recovery-credit deadline is 18 months (NOT a forced-liquidation wall,
# and NOT the old 2-year ceiling) -- it is the OUTER EDGE OF ACCEPTABILITY.
# Recoveries past this line are the tail we are defending against.
MANDATE_MONTHS = 18.0                 # outer edge of acceptable recovery
MANDATE_YEARS  = MANDATE_MONTHS / 12  # kept for backward-compat with engine calls
# The comfortable band: recovery here is unambiguously fine. Reported alongside
# the 18m figure so output speaks in the language of the actual tolerance,
# rather than collapsing a nuanced view into one pass/fail number.
ACCEPTABLE_BAND_MONTHS = (4.0, 18.0)

# ---------------------------------------------------------------------------
# DYNAMIC RECOVERY SCHEDULE  --  recovery as a curve, not a hard threshold
# ---------------------------------------------------------------------------
# Rather than force a single pass/fail cutoff, the model reports the cumulative
# probability of recovery at EACH of these horizons. Horizons past MANDATE_MONTHS
# are FLAGGED (beyond_suggested=True) and surfaced for the user to decide whether
# to count -- the threshold becomes a movable suggestion, not a wall. The model
# also reports p_never (still underwater at the end of the generous sim window),
# which is the truly permanent / systemic-failure class -- the signal that most
# matters, and the one a hard threshold would hide.
RECOVERY_SCHEDULE_MONTHS = [6, 9, 12, 15, 18, 24, 30, 36]


# ===========================================================================
#  DERIVATION HELPER  (kept in the calibration file so the link from base
#  rates to regime probabilities is transparent and re-runnable)
# ===========================================================================
import math

def derive_regime_probs():
    """Reproduce the systemic/bear rows of REGIME_PROBS from BASE_RATES_5YR
    via the constant-hazard survival transform, times the catalyst premium.
    Returns a dict you can compare against the hard-coded REGIME_PROBS above.
    This is the bridge between '5 systemic episodes in 97 years' and the
    3/6/9% systemic tail -- every step visible and adjustable."""
    out = {}
    years = [0.5, 1.0, 1.5]
    sm = STRESS_CRISIS_MULT                     # macro-stress scales the premium
    for regime in ("bear", "systemic"):
        p5 = BASE_RATES_5YR[regime]
        lam = -math.log(1 - p5) / 5.0          # implied annual hazard
        prem = CATALYST_PREMIUM[regime]
        out[regime] = [round((1 - math.exp(-lam * h)) * prem[i] * sm, 4)
                       for i, h in enumerate(years)]
    return out


if __name__ == "__main__":
    # Quick self-check: print the derived tail next to the hard-coded one.
    print("Calibration self-check  (as of", AS_OF_DATE, ")")
    print("Hazard-derived tail vs. calibrated REGIME_PROBS:")
    d = derive_regime_probs()
    for regime in ("bear", "systemic"):
        print(f"  {regime:9s} derived={d[regime]}  calibrated={REGIME_PROBS[regime]}")
    print(f"\n{len(COMPANIES)} companies, {len(EXPOSURES)} exposures loaded.")


# ---------------------------------------------------------------------------
# 7. CORRELATION GROUPS (sub-factors) -- canonical home (correlation.py imports
#    these now). Idiosyncratic co-movement BEYOND the shared macro factor, so
#    the core engine natively simulates sector cascades / contagion.
# ---------------------------------------------------------------------------
GROUP_RHO = {"AI-infra": 0.55, "AI-platform": 0.40, "defensive": 0.30, "disruptive": 0.35}
GROUP_RHO_CRISIS = 0.92   # intra-group correlation in a panic (liquidity -> ~1)

# Per-ETF idiosyncratic-noise width: baskets diversify away single-name private
# noise. Broad index ~0.05, sector/thematic ~0.08, vs single stocks 0.11. This
# gives ETFs an EMERGENT (not hand-asserted) drawdown-depth benefit.
ETF_IDIO = {
    "VOO (S&P 500)": 0.045, "SCHD (Dividend)": 0.045, "QQQ (Nasdaq-100)": 0.05,
    "VGT (Info Tech)": 0.06, "IGV (Software)": 0.07, "DTCR (Data Ctr Infra)": 0.07,
    "GRID (Smart Grid)": 0.07, "NUKE (Nuclear/Uranium)": 0.085,
    "SMH (VanEck Semis)": 0.075, "SOXX (iShares Semis)": 0.075,
    "AIQ (Global X AI)": 0.07, "CHAT (Roundhill GenAI)": 0.08,
    "DRAM (Roundhill Memory)": 0.09, "QTUM (Defiance Quantum)": 0.08,
    "ARKK (ARK Innovation)": 0.09,
}

GROUP = {
    "NVIDIA": "AI-infra", "Broadcom": "AI-infra", "AMD": "AI-infra",
    "Marvell": "AI-infra", "Micron": "AI-infra", "Kioxia": "AI-infra",
    "ARM": "AI-infra", "Qualcomm": "AI-infra", "Lumentum": "AI-infra",
    "Coherent": "AI-infra", "Applied Optoelectronics": "AI-infra", "IonQ": "AI-infra",
    "Astera Labs": "AI-infra", "CoreWeave": "AI-infra", "Vertiv": "AI-infra",
    "DRAM (Roundhill Memory)": "AI-infra", "SMH (VanEck Semis)": "AI-infra",
    "SOXX (iShares Semis)": "AI-infra", "CHAT (Roundhill GenAI)": "AI-infra",
    "AIQ (Global X AI)": "AI-infra", "QTUM (Defiance Quantum)": "AI-infra",
    "DTCR (Data Ctr Infra)": "AI-infra", "GRID (Smart Grid)": "AI-infra",
    "NUKE (Nuclear/Uranium)": "AI-infra",
    "Tesla": "disruptive", "ARKK (ARK Innovation)": "disruptive",
    "Microsoft": "AI-platform", "Alphabet": "AI-platform", "Amazon": "AI-platform",
    "Meta": "AI-platform", "Oracle": "AI-platform", "Palantir": "AI-platform",
    "AppLovin": "AI-platform", "IGV (Software)": "AI-platform",
    "VGT (Info Tech)": "AI-platform", "QQQ (Nasdaq-100)": "AI-platform",
    "Apple": "defensive", "Cisco": "defensive", "IBM": "defensive",
    "Texas Instruments": "defensive", "VOO (S&P 500)": "defensive",
    "SCHD (Dividend)": "defensive",
}

# ---------------------------------------------------------------------------
# 8. LIQUIDITY -- the remaining failure mode in a profitable, low-credit-risk
#    market (2026 != 2000/2008: real earnings, cash-rich balance sheets, no
#    CDS rot -- what breaks is liquidity air-pockets). ESTIMATES; refresh.
# ---------------------------------------------------------------------------
# (liquidity fields now live in the MACRO dict above so SYSTEMIC_STRESS — computed
#  right after it — actually includes them. The earlier bug computed stress BEFORE
#  this update, so the engine ran on a stale score while reports showed the new one.)
