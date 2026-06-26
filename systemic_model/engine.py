"""
============================================================================
 ENGINE  --  systemic_model
============================================================================
 THE MATHEMATICS. This file is meant to be STABLE: it reads calibration.py
 and turns those numbers into drawdown probabilities, recovery distributions,
 and the TAM premium decomposition. You should rarely need to edit it. When
 the world changes you edit calibration.py, not this.

 The engine has three parts, each a small, testable function:

   PART A -- the macro factor and the Monte Carlo path generator
             (regime-switching daily vol, Student-t tails, beta loading,
              leveraged daily-reset compounding)

   PART B -- the TAM premium decomposition
             (splits each multiple into earned vs. floating premium, folds in
              the dominance and capex-elasticity factors from the TDVM review,
              and produces a fragility score and a recovery-quality score)

   PART C -- drawdown / recovery measurement on the simulated paths
             (max drawdown, time-to-recovery, conditional recovery odds)

 Design note on WHERE TAM enters (the central modeling decision):
   beta sets how DEEP a name falls in a panic  (Part A, short-timescale).
   TAM-penetration sets whether it RECOVERS     (Part B -> Part C).
   We deliberately route TAM into drift (small) and recovery (large) and into
   a BOUNDED crisis-only tail widening -- never into beta -- because beta
   governs the fall and TAM governs the climb out, and because letting TAM
   swing the drawdown depth would double-count the bull case the market has
   already priced.
============================================================================
"""
import numpy as np
import zlib
try:
    from numba import njit
    NUMBA_AVAILABLE = True
except Exception:
    NUMBA_AVAILABLE = False
    def njit(*a, **k):
        def w(f): return f
        return a[0] if (len(a) == 1 and callable(a[0])) else w
import calibration as C
import extension_data as X   # net-cash / balance lookups for the trough-buyback slingshot


# ===========================================================================
#  PART A -- MACRO FACTOR + PATH GENERATION
# ===========================================================================



@njit(fastmath=True, cache=True)
def _fast_markov_walk(Pcum, u, days, n, num_states):
    """C-compiled regime-transition walk (Numba). Identical logic to the vectorized
    fallback; ~15-30x faster, enabling 300k+ paths. Falls back to NumPy if Numba
    is absent. Uses the SAME pre-drawn uniforms u, so results are unchanged."""
    state = np.zeros((n, days), dtype=np.int8)
    for i in range(n):
        for t in range(1, days):
            val = u[i, t]; row = state[i, t-1]
            for s in range(num_states):
                if val <= Pcum[row, s]:
                    state[i, t] = s
                    break
            else:
                # defensive (Gemini bug E): if float cumsum leaves Pcum[row,-1] a hair
                # below 1.0 and u lands in that gap, fall to the last state instead of
                # silently leaving state at 0. Unreachable today (rows sum to exactly 1.0)
                # but robust if the transition matrix is ever perturbed.
                state[i, t] = num_states - 1
    return state


def _simulate_factor(rng, n, days, return_grind=False):
    """Generate `n` paths of the daily macro-factor return Phi over `days`.

    Phi switches between three volatility regimes via the transition matrix,
    draws Student-t innovations (fat tails), and applies each regime's drift.
    Returns (factor_returns[n,days], crisis_mask[n,days]).
    The crisis mask is exported so Part C can apply the bounded crisis-only
    de-rate for fragile names.
    """
    vol   = np.array(C.FACTOR["vol_annual"])
    drift = np.array(C.FACTOR["drift_annual"])
    nu    = C.FACTOR["student_t_df"]
    # macro-stress endogenously scales the crisis-entry transition probabilities:
    # a stretched balance-sheet / credit environment escalates into crisis more
    # often (fatter emergent tail); a benign one less often.
    import macro_stress as _MS
    _trans = _MS.effective_transition(C.FACTOR["transition"], C.SYSTEMIC_STRESS)
    Pcum  = np.cumsum(np.array(_trans), axis=1)
    dt    = 1.0 / 252.0

    # Walk the regime state forward day by day.
    u = rng.random((n, days))
    if NUMBA_AVAILABLE:
        state = _fast_markov_walk(np.ascontiguousarray(Pcum), u, days, n, Pcum.shape[1])
    else:
        state = np.zeros((n, days), dtype=np.int8)
        last = Pcum.shape[1] - 1
        for t in range(1, days):
            # clamp to the last state so a u just above a sub-1.0 row-sum can't index
            # out of bounds (matches the numba for-else fallback). (Gemini bug E.)
            state[:, t] = np.minimum((u[:, t][:, None] > Pcum[state[:, t-1]]).sum(axis=1), last)

    # Student-t innovations, rescaled so the realized vol matches vol_annual
    z = rng.standard_t(nu, size=(n, days)) * np.sqrt((nu - 2) / nu)
    factor = drift[state] * dt + vol[state] * np.sqrt(dt) * z
    if return_grind:
        grind = (state == 3) if len(vol) > 3 else np.zeros((n, days), dtype=bool)
        return factor, (state == 2), grind
    return factor, (state == 2)


def _price_path(rng, factor, crisis, spec, n, days, tail_mult=1.0, subfactors=None,
                grind=None, idio_rng=None, beta_amp=0.0):
    """Turn the shared macro factor into one exposure's price path.

    spec carries beta, idio, alpha (mu), leverage L, and the leveraged flag.
    tail_mult > 1 widens the idiosyncratic shock ONLY in the crisis state
    (used for fragile TAM names in Part C); leave at 1.0 for plain exposures.
    beta_amp > 0 amplifies beta ONLY in the crisis state (beta -> beta*(1+beta_amp))
    -- used by the valuation overlay for forced-unwind / floating-premium evaporation;
    leave at 0.0 for plain exposures so the standard path is unchanged.
    """
    dt = 1.0 / 252.0
    if spec["idio"] > 0:
        # NATIVE CONTAGION: blend a shared sector shock with the private shock.
        # sqrt(rho)^2 + sqrt(1-rho)^2 = 1, so each name's STANDALONE volatility
        # and marginal drawdown distribution are unchanged -- only the JOINT
        # behavior changes: on paths where the sector shock is bad, the whole
        # group cascades together (what June 5 2026 looked like).
        # REPRODUCIBILITY (Claude red-team): draw the PRIVATE shock from a
        # per-name stable-seeded stream when provided, so a name's result is
        # invariant to universe-assembly order and to which other names exist.
        # The shared macro factor + group sub-factors stay on the common stream,
        # so the crisis-spiking contagion is untouched.
        shock = (idio_rng if idio_rng is not None else rng).standard_normal((n, days))
        if subfactors is not None and spec.get("group") in subfactors:
            rho = getattr(C, "GROUP_RHO", {}).get(spec["group"], 0.0)
            if rho > 0:
                # CRISIS-SPIKING CORRELATION (Gemini/Claude red-team): in a panic,
                # liquidity evaporates and intra-group correlation converges toward
                # ~1 (forced selling, blind ETF liquidation) -- diversification
                # vanishes exactly when you need it. A de-rating grind correlates
                # too, but less violently. rho_t is per-cell, so sqrt(rho_t)^2 +
                # sqrt(1-rho_t)^2 = 1 STILL holds -> each name's marginal vol is
                # preserved; only the JOINT tail fattens in the bad states.
                rho_max = getattr(C, "GROUP_RHO_CRISIS", 0.92)
                rho_t = np.full((n, days), rho, dtype=float)
                rho_t = rho_t + (rho_max - rho_t) * crisis
                if grind is not None:
                    rho_t = rho_t + (rho_max - rho_t) * (0.5 * grind)
                rho_t = np.clip(rho_t, 0.0, 0.999)
                shock = (np.sqrt(rho_t) * subfactors[spec["group"]]
                         + np.sqrt(1.0 - rho_t) * shock)
        idio = shock * (spec["idio"] * np.sqrt(dt))
    else:
        idio = 0.0
    if tail_mult != 1.0 and not np.isscalar(idio):
        idio = idio * (1 + (tail_mult - 1) * crisis)   # extra hit in crisis only

    beta_t = spec["beta"] * (1.0 + beta_amp * crisis) if beta_amp else spec["beta"]
    daily = beta_t * factor + spec.get("mu", spec.get("alpha", 0.0)) * dt + idio
    if grind is not None and spec.get("grind_drag", 0.0) > 0.0:
        daily = daily - spec["grind_drag"] * grind * dt   # multiple-compression bleed

    if not spec["leveraged"]:
        return np.exp(np.cumsum(daily, axis=1))        # log-return compounding
    # leveraged products: daily-reset on SIMPLE returns, minus fee+borrow drag
    L = spec["L"]
    drag = (C.LEVERAGE_DRAG["fee"] + C.LEVERAGE_DRAG["borrow"]) * dt
    simple = np.expm1(daily)
    lev_daily = L * simple - drag
    return np.cumprod(1 + lev_daily, axis=1)


# ===========================================================================
#  PART B -- TAM PREMIUM DECOMPOSITION
# ===========================================================================

import math as _math

def _growth_annuity(g, r, T):
    """PV of supernormal growth over T years: sum_{t=1..T} ((1+g)/(1+r))^t. Convex in T."""
    if T <= 0:
        return 0.0
    q = (1.0 + g) / (1.0 + r)
    n = int(T)
    frac = T - n
    s = sum(q ** t for t in range(1, n + 1))
    return s + (q ** (n + 1)) * frac


def _years_to_saturation(rev, tam, s_star, g, m, cap):
    """Years for revenue (growing at g) to reach a ceiling s_star*TAM that is itself
    growing at m. If g<=m the ceiling rises as fast as revenue => runway ~ infinite (cap)."""
    ceil = s_star * tam
    if ceil <= rev:
        return 0.0
    if g <= m:
        return cap
    return min(cap, _math.log(ceil / rev) / _math.log((1.0 + g) / (1.0 + m)))


def _effective_cogs_fragility(name):
    """COGS fragility: weighted cost-driver buckets if USE_COGS_BUCKETS and a template exists,
    else the scalar cogs_fragility. effective = sum(bucket_weight * bucket_shock). At baseline
    (shocks=1.0) the buckets roll up to the original scalar, so baseline numbers are unchanged;
    raise a bucket's shock to stress that cost driver (energy, wafers, packaging, ...)."""
    ps = getattr(C, "PROFIT_SENSITIVITY", {}).get(name, {})
    if getattr(C, "USE_COGS_BUCKETS", False):
        buckets = getattr(C, "COGS_BUCKETS", {}).get(name)
        shocks = getattr(C, "COGS_BUCKET_SHOCKS", {})
        if buckets:
            cf = sum(w * shocks.get(b, 1.0) for b, w in buckets.items())
            return float(min(1.0, max(0.0, cf)))
    return float(ps.get("cogs_fragility", 0.0))


def _endogenous_cyclicality(op_margin, fixed_cost_ratio, rev_drawdown):
    """Derive the EPS trough depth from operating leverage instead of a manual number.
    Costs split into fixed (do not scale) and variable (scale with revenue). In a bust
    revenue falls by `rev_drawdown`; variable costs fall with it, fixed costs do not, so
    operating income (the EPS denominator) falls FASTER than revenue. Returns the fraction
    EPS collapses (0..0.95); >=1 (EPS turns negative) clamps to 0.95. Inputs op_margin (m),
    fixed_cost_ratio (f), rev_drawdown (d) are each more groundable in real financials than
    a single cyclicality guess -- but note this sharpens trough DEPTH and recovery TIMING,
    the model's least-validated axis."""
    m = max(1e-6, float(op_margin)); f = float(fixed_cost_ratio); d = float(rev_drawdown)
    base_oi = m
    new_oi = (1.0 - d) * (1.0 - (1.0 - m) * (1.0 - f)) - (1.0 - m) * f
    drop = 1.0 - new_oi / base_oi
    return float(min(0.95, max(0.0, drop)))


def decompose_premium(companies=None):
    """The bottom-up valuation layer. For each company, split its P/E premium
    into the part runway can JUSTIFY and the part that FLOATS free, then
    combine with earnings-quality, dominance, and capex-elasticity into a
    composite FRAGILITY score and a RECOVERY-QUALITY score.

    Returns a dict keyed by company with all intermediate quantities exposed,
    so the logic is fully auditable (nothing is a black box).

    The math, step by step:
      penetration  = revenue / TAM
      runway       = (1 - penetration) * tam_cagr * quality * dominance
                     ^ headroom * how-fast-the-ceiling-rises * credibility
                       * can-you-defend-your-share   (dominance from TDVM)
      premium_pts  = max(fwd_pe - BASE_PE, 0)        (premium above no-growth)
      justified    = premium_pts * runway_norm        (backed by runway)
      unsupported  = premium_pts - justified          (floating, fragile)
      eq_fragility = 1 - earn_quality                 (denominator-inflation risk)
      fragility    = 0.6*unsupported_frac + 0.4*eq_fragility
      recovery_q   = 0.5*runway_norm + 0.5*earn_quality - 0.4*unsupported_frac,
                     then scaled by capex_elastic so names whose demand
                     survives a credit crash keep their floor (TDVM idea).
    """
    src = companies if companies is not None else C.COMPANIES
    out = {}
    # first pass: runway (raw)
    for n, d in src.items():
        pen = d["rev_bn"] / d["tam_bn"]
        runway = (1 - pen) * d["tam_cagr"] * d["quality"] * d["dominance"]
        out[n] = dict(pen=pen, runway_raw=runway, **d)
    # ----------------------------------------------------------------------
    # NORMALIZATION ANCHOR  (fixed, not relative).
    # Previously runway was normalized against the MAX runway in the current
    # dataset. That is fine for a fixed list, but it BREAKS when the universe
    # changes: adding an earlier-stage name (exactly what the discovery agent
    # does) would become the new max and silently rebase every existing score.
    # So we anchor to a fixed theoretical "ideal" candidate instead: near-zero
    # penetration, a fast-but-plausible TAM CAGR, and full quality+dominance.
    # Real names are then measured on an ABSOLUTE scale that does not move when
    # candidates are added or removed. (This is the fix Gemini's red-team note
    # correctly flagged, now made live by the universe expansion.)
    RUNWAY_ANCHOR = (1 - 0.02) * 0.50 * 1.0 * 1.0   # ideal: 2% penetration, 50% TAM CAGR
    mx = RUNWAY_ANCHOR
    # second pass: premium split + composite scores
    for n, o in out.items():
        o["runway_norm"] = min(o["runway_raw"] / mx, 1.0)   # cap at 1.0 (can't exceed the ideal)
        # ---- cash / buyback adjustment to the EFFECTIVE multiple -------------
        # Net cash is not part of the operating multiple; deploying BUYBACK_PCT of
        # it into an ACCRETIVE buyback (E/P > after-tax cash yield) retires float
        # and de-rates the P/E. Net DEBT gets no buyback credit. Static valuation
        # effect; distinct from the crisis trough-buyback slingshot (recovery path).
        eff_pe = o["fwd_pe"]
        if getattr(C, "USE_CASH_ADJUSTMENT", False):
            try:
                ncash = max(X.net_cash(n), 0.0)             # net cash / mcap; only positive funds buybacks
            except Exception:
                ncash = 0.0
            bb = getattr(C, "BUYBACK_PCT_BY_NAME", {}).get(n, getattr(C, "BUYBACK_PCT", 0.0))
            cy = getattr(C, "CASH_YIELD_AFTER_TAX", 0.035)
            accretive = (1.0 / o["fwd_pe"]) > cy if o["fwd_pe"] > 0 else False   # E/P > after-tax cash yield
            eff_pe = o["fwd_pe"] * (1.0 - bb * ncash) if accretive else o["fwd_pe"]
            o["net_cash_to_mcap"] = round(ncash, 3)
            o["buyback_pct"] = bb
            o["buyback_accretive"] = bool(accretive)
            o["eff_pe"] = round(eff_pe, 2)
        premium = max(eff_pe - C.BASE_PE, 0)
        justified = premium * o["runway_norm"]
        unsupported = premium - justified
        o["premium_pts"]      = premium
        o["justified_pts"]    = justified
        o["unsupported_pts"]  = unsupported
        o["unsupported_frac"] = unsupported / eff_pe if eff_pe > 0 else 0.0
        # ---- competitive / duration-aware justified premium (override) -------
        # Replaces the slope-only justified premium with a duration- and
        # competition-aware one when calibration provides inputs. Both versions
        # are preserved in the output (auditable). See calibration.COMPETITIVE.
        comp = getattr(C, "COMPETITIVE", {}).get(n)
        if getattr(C, "USE_COMPETITIVE_PREMIUM", False) and comp:
            o["justified_pts_slope"]    = justified
            o["unsupported_pts_slope"]  = unsupported
            o["unsupported_frac_slope"] = o["unsupported_frac"]
            o["runway_norm_slope"]      = o["runway_norm"]
            g = comp["g"]; m = comp["m"]; ss = comp["struct_share"]
            moat = comp["moat"]; pp = comp["pricing_power"]
            r_g = getattr(C, "R_GROWTH", 0.09)
            cap = getattr(C, "GROWTH_DURATION_CAP", 15)
            s_star = min(ss * moat + ss * (1 - moat) * 0.5, 0.95)   # ceiling set by structure, sharpened by moat
            Tsat = _years_to_saturation(o["rev_bn"], o["tam_bn"], s_star, g, m, cap)
            anchor = _growth_annuity(0.30, r_g, 8)
            dur = min(_growth_annuity(g, r_g, Tsat) / anchor, 1.0) if anchor > 0 else 0.0
            g_share = max(g - m, 0.0)
            durab = (g - g_share + g_share * moat) / g if g > 0 else 0.0  # price-led share gain discounted by moat
            gqual = (durab + pp + o["earn_quality"]) / 3.0               # averaged, not multiplied
            justified = min(premium * dur * gqual, premium)              # cap at premium (fragility detector, no cheapness signal)
            unsupported = premium - justified
            o["s_star"] = s_star; o["T_sat"] = Tsat; o["duration_credit"] = dur
            o["growth_quality"] = gqual; o["share_durability"] = durab
            o["justified_pts"] = justified
            o["unsupported_pts"] = unsupported
            o["unsupported_frac"] = unsupported / eff_pe if eff_pe > 0 else 0.0
            o["runway_norm"] = dur                                       # recovery uses duration credit as room-to-grow
        o["eq_fragility"]     = 1 - o["earn_quality"]
        if getattr(C, "USE_CASH_ADJUSTMENT", False):
            try:
                bal = X.balance(n)                          # 0..1 balance-sheet strength (net cash, no debt = high)
            except Exception:
                bal = 0.55
            o["balance_sheet"] = round(bal, 2)
            o["fragility_precash"] = 0.6 * o["unsupported_frac"] + 0.4 * o["eq_fragility"]
            # net-cash / no-debt cushion lowers fragility; net debt raises it
            o["fragility"] = 0.5 * o["unsupported_frac"] + 0.3 * o["eq_fragility"] + 0.2 * (1 - bal)
        else:
            o["fragility"]        = 0.6 * o["unsupported_frac"] + 0.4 * o["eq_fragility"]
        rq = 0.5 * o["runway_norm"] + 0.5 * o["earn_quality"] - 0.4 * o["unsupported_frac"]
        # capex-elasticity scaling: inelastic (physical) demand keeps its floor
        # in a crisis; discretionary demand loses it. Centered so elastic=0.7
        # is roughly neutral.
        rq = rq * (0.7 + 0.5 * (o["capex_elastic"] - 0.5))
        # v3 CAPEX-INTENSITY PENALTY: capex/revenue >> 15% is severe operating
        # leverage -- if demand slows or credit freezes, margins crater and the
        # recovery drags. Hardware buyers (Meta/MSFT/CoreWeave) penalized; sellers
        # (NVDA) ~untouched. Drags recovery_quality only (not depth).
        try:
            ci = X.capex_intensity(n)
        except Exception:
            ci = 0.10
        rq = max(0.0, rq - max(0.0, ci - 0.15) * 0.8)
        # ---- cyclical EARNINGS-COLLAPSE (denominator) drag -------------------
        # operating leverage makes EPS fall faster than price in a bust -> the P/E
        # EXPANDS when you need it to compress, and recovery must wait for the
        # earnings denominator to heal first. Drags recovery_quality only (depth stays
        # set by beta/correlation); distinct from the capex penalty and the two-phase
        # demand trough. recovery_quality_precollapse preserved for audit.
        ec = getattr(C, "EARNINGS_CYCLICALITY", {}).get(n)
        # ENDOGENOUS operating leverage: derive the trough from op-margin / fixed-cost
        # ratio / revenue drawdown instead of the manual cyclicality, when inputs exist.
        ec_endo = None
        ol_inp = getattr(C, "OPERATING_LEVERAGE", {}).get(n)
        if getattr(C, "USE_ENDOGENOUS_EARNINGS", False) and ol_inp is not None:
            ec_endo = _endogenous_cyclicality(ol_inp["op_margin"], ol_inp["fixed_cost_ratio"],
                                              ol_inp["rev_drawdown"])
        if getattr(C, "USE_EARNINGS_COLLAPSE", False) and (ec is not None or ec_endo is not None):
            o["recovery_quality_precollapse"] = float(np.clip(rq, 0.0, 1.0))
            o["earnings_cyclicality_manual"] = ec
            if ec_endo is not None:
                o["earnings_cyclicality_endogenous"] = ec_endo
                o["earnings_cyclicality_source"] = "endogenous"
                ec = ec_endo
            else:
                o["earnings_cyclicality_source"] = "manual"
            # ---- PROFIT-SENSITIVITY addons (interest expense + input cost) -----
            # Two drawdown-EPS channels the demand model misses: (1) levered names see
            # interest expense rise in a rate shock; (2) high-COGS-fragility names eat
            # input-cost shocks UNLESS pricing power lets them pass it on. Both DEEPEN
            # the earnings trough (added to cyclicality, which already drives the
            # recovery-quality drag AND tail depth). Net-cash / high-pricing-power names
            # are ~immune. Each input is auditable via the provenance layer.
            if getattr(C, "USE_PROFIT_SENSITIVITY", False):
                ps = getattr(C, "PROFIT_SENSITIVITY", {}).get(n, {})
                pp = getattr(C, "COMPETITIVE", {}).get(n, {}).get("pricing_power", 0.5)
                nde = max(0.0, ps.get("net_debt_to_ebitda", 0.0))
                fl  = ps.get("floating_rate_share", 0.0)
                cf  = _effective_cogs_fragility(n)
                ie_addon = min(0.30, nde * fl * getattr(C, "RATE_SHOCK_K", 0.06))
                ic_addon = min(0.30, cf * (1.0 - pp) * getattr(C, "INPUT_SHOCK_K", 0.35))
                o["interest_expense_addon"] = round(ie_addon, 4)
                o["input_cost_addon"] = round(ic_addon, 4)
                o["cyclicality_base_preprofit"] = ec
                ec = min(0.95, ec + ie_addon + ic_addon)
            o["earnings_cyclicality"] = ec
            sev = getattr(C, "DOWNTURN_SEVERITY", 1.0)
            o["eps_trough_depth"] = min(0.95, ec * sev)                 # illustrative EPS fall in a severe bust
            o["pe_expansion_at_trough"] = round(1.0 / (1.0 - o["eps_trough_depth"]), 1)
            rq = rq * (1.0 - ec * getattr(C, "EARNINGS_COLLAPSE_DRAG", 0.40))
        o["recovery_quality"] = float(np.clip(rq, 0.0, 1.0))
    return out


def company_to_spec(o, name=None):
    """Translate a decomposed company into a path-generator spec, mapping the
    fragility/recovery scores onto the three TAM channels:
      drift channel    : runway raises drift, fragility trims it (small effect)
      tail channel     : fragility widens crisis-only idiosyncratic shock (bounded)
      recovery channel : recovery_quality vs fragility -> recovery speed shift
    """
    drift_alpha = 0.06 * o["runway_norm"] - 0.05 * o["fragility"]
    tail_mult   = 1.0 + 0.5 * o["fragility"]          # bounded: max 1.5x in crisis
    # cyclical earnings collapse erodes the valuation FLOOR in a bust (EPS craters ->
    # P/E expands -> no earnings to anchor the price), deepening the crisis trough.
    # Bounded add-on, high-cyclicality (memory) names only; depth still mostly beta.
    ec = o.get("earnings_cyclicality")
    if ec is not None:
        tail_mult += min(0.30, ec * getattr(C, "EARNINGS_COLLAPSE_DEPTH", 0.30))
    recov_shift = 0.30 * o["recovery_quality"] - 0.25 * o["fragility"]
    # CRASH-CONDITIONAL GROWTH in the MC recovery channel: the same secular/cyclical/
    # broken growth response that drives the earn-back clock also speeds or slows the
    # SIMULATED recovery -- and ONLY the recovery (beta still sets depth). Setting the
    # shift to (cg_mult - 1) makes the MC recovery-time factor 1/(1+shift) ~ 1/cg_mult
    # match the clock's earn-back scaling (1/cg_mult): secular +0.05 (faster), cyclical
    # -0.22 (slower but recovers), broken -0.50 (slowest; clipped to -0.4 downstream).
    # For CYCLICAL names the recovery timing is now handled by an explicit two-phase
    # demand trough (cycle dict below), so we do NOT also apply the flat recov_shift
    # proxy to them -- that would double-count the slowdown. Secular (+0.05, faster) and
    # broken (-0.50, slowest) still use the proxy.
    cycle = None
    if name:
        try:
            import crash_growth as _CG
            arch = _CG.archetype(name)
            theme = None
            if arch == "cyclical":
                # ONLY names with an explicit cycle theme get the two-phase demand trough,
                # shaped by THAT theme (memory vs optical vs broad-semis). An unmapped
                # cyclical falls through to the flat crash-growth proxy below -- it does NOT
                # inherit the memory clock. (Reviewer consensus fix.)
                theme = getattr(C, "CYCLICAL_THEME", {}).get(name, getattr(C, "CYCLICAL_DEFAULT_THEME", None))
                cp = getattr(C, "CYCLICAL_DEMAND_PATH", {}).get(theme) if theme else None
                if cp:
                    freeze_m = cp.get("demand_down_months", 9) + cp.get("stabilization_months", 6)
                    cycle = dict(theme=theme, freeze_days=int(freeze_m * 21),
                                 second_leg=cp.get("second_leg", 0.15), min_depth=0.15)
            if cycle is None:
                # secular, broken, or an unmapped cyclical: flat crash-growth recovery proxy.
                recov_shift += _CG.recovery_g_mult(name) - 1.0
        except Exception:
            pass
    grp = getattr(C, "GROUP", {}).get(name, "defensive") if name else "defensive"
    # ETF DIVERSIFICATION (Claude red-team): a basket's private noise is much
    # smaller than a single stock's. Without this, a 70-holding fund got the same
    # idio=0.11 as one name, so ETFs showed almost no drawdown-depth benefit.
    idio = getattr(C, "ETF_IDIO", {}).get(name, 0.11) if name else 0.11
    # 4TH-REGIME OVERLAY: in a de-rating grind the market refuses to pay for
    # FLOATING premium, so names whose multiple is mostly unsupported bleed
    # an extra compounding drag while the grind state is active.
    grind_drag = 1.0 * max(0.0, o.get("val_gap", o.get("unsupported_frac", 0.0)) - 0.15)
    # TROUGH-BUYBACK SLINGSHOT (MC path-keyed): a cash-rich, durable firm can fire
    # excess cash at a DEEP panic low, retiring a depth-scaled slice of float that
    # permanently lifts the post-trough per-share path -> faster recovery to the
    # old price. Unlike the closed-form clock (which only sees the mild multiple-
    # compression drop), the MC produces the deep troughs where this is genuinely
    # accretive. Whether it fires, and how much, is decided per-path in
    # _drawdown_and_recovery from the realized drawdown depth. We only attach the
    # capacity here (cash + procyclical willingness); ETFs aren't in NET_CASH_TO_MCAP
    # so net_cash -> 0 -> no slingshot, which is correct (a fund doesn't self-repurchase).
    ncash = X.net_cash(name) if name else 0.0
    bal_sheet = X.balance(name) if name else 0.55
    # SOLVENCY impairment hazard (financing fragility x (1 - revenue durability)),
    # applied to deep crisis drawdowns in _drawdown_and_recovery.
    solv = None
    dilution = None
    if name:
        try:
            import solvency as _SV
            _h = _SV.impairment_hazard(name)
            if _h > 0.0:
                solv = dict(hazard=_h, min_depth=_SV.MIN_DEPTH,
                            seed=(zlib.crc32(("solv:" + name).encode()) & 0xFFFFFFFF))
            _d = _SV.dilution_severity(name)
            if _d > 0.005:
                dilution = dict(severity=_d, min_depth=_SV.DILUTION_MIN_DEPTH)
        except Exception:
            solv = None; dilution = None
    excess = max(0.0, ncash - 0.05)                       # keep 5% of mcap as working cash
    deploy = (0.65 if (bal_sheet >= 0.80 and o["earn_quality"] >= 0.70)
              else (0.30 if bal_sheet >= 0.60 else 0.0))
    bb = None
    if excess > 0 and deploy > 0:
        bb = dict(cash_used=deploy * excess, pe_peak=o["fwd_pe"],
                  unsup=o.get("unsupported_frac", 0.0),
                  cash_yield=getattr(C, "CASH_YIELD_AFTER_TAX", 0.035),
                  min_depth=0.25)                          # only a real panic triggers a deliberate buyback
    # systemic-freeze dependency: how hard THIS sub-market is frozen when the keystone
    # (AI-infra plumbing) seizes -- infra most, defensive least (cross-submarket coupling).
    _fz = getattr(C, "SYSTEMIC_FREEZE", {}) or {}
    freeze_dep = _fz.get("dependency", {}).get(grp, _fz.get("dependency_default", 0.7))
    return dict(beta=o["beta"], idio=idio, mu=drift_alpha, L=1, leveraged=False,
                tail_mult=tail_mult, recov_shift=recov_shift, group=grp,
                grind_drag=grind_drag, bb=bb, solv=solv, dilution=dilution, cycle=cycle,
                freeze_dep=freeze_dep)


# ===========================================================================
#  PART C -- DRAWDOWN / RECOVERY MEASUREMENT
# ===========================================================================

def _drawdown_and_recovery(price, horizon_days, recov_shift=0.0, bb=None, solv=None,
                           dilution=None, cycle=None, path_offset=0, freeze=None, freeze_dep=1.0):
    """For each path: maximum peak-to-trough drawdown within the horizon, and
    the time (in trading days) from that trough back to the prior peak,
    searched across the FULL simulated length so recoveries past the horizon
    are still captured. recov_shift > 0 speeds recovery (strong fundamentals),
    < 0 slows it (fragile) -- this is the TAM recovery channel.

    bb (optional): trough-buyback 'slingshot' capacity from company_to_spec. On
    paths whose realized drawdown is deep enough to be a panic AND deep enough
    that retiring cheap shares is accretive (the discount beats the forfeited
    cash yield), the firm deploys cash at the trough; retiring a depth-scaled
    slice of float permanently lifts the post-trough per-share path, so the old
    price is reached sooner. The buyback is an OPTION -- it never SLOWS recovery
    (eps_lift is clamped to >=1), and it never changes the drawdown DEPTH (the
    fall already happened; cash only speeds the climb out).
    """
    n = price.shape[0]
    window = price[:, :horizon_days]
    peak = np.maximum.accumulate(window, axis=1)
    dd = window / peak - 1.0
    mdd = dd.min(axis=1)                       # most negative point = max drawdown
    trough_i = dd.argmin(axis=1)
    peak_at_trough = peak[np.arange(n), trough_i]

    # ---- per-path EPS lift: trough-buyback slingshot (>1) and/or toxic dilution (<1) ----
    eps_lift = None
    depth = np.maximum(0.0, -mdd)                                  # panic depth, per path
    if bb is not None and bb.get("cash_used", 0.0) > 0:
        buy_price_frac = np.maximum(0.20, 1.0 - depth * 0.75)     # avg buy price vs prior peak
        cash_used = bb["cash_used"]                                # scalar: frac of peak mcap deployed
        float_cut = np.minimum(0.25, cash_used / buy_price_frac)
        float_cut = float_cut * max(0.0, 1.0 - bb.get("unsup", 0.0))   # no credit for punctured premium
        interest_drag = min(0.25, cash_used * bb.get("cash_yield", 0.035) * bb["pe_peak"])
        bb_lift = (1.0 - interest_drag) / np.maximum(1.0 - float_cut, 0.01)
        trigger = (depth >= bb.get("min_depth", 0.25)) & (bb_lift > 1.0)   # only accretive panics
        eps_lift = np.where(trigger, bb_lift, 1.0)
    # TOXIC DILUTION (reverse slingshot): a cash-poor/levered name forced to RAISE
    # equity at a deep low expands its float -> permanent per-share haircut on the
    # paths that survive. Mirrors the buyback; multiplies eps_lift DOWN (<1). It
    # only fires on a deep crash and never deepens the drawdown (the fall already
    # happened) -- it caps how far the per-share price climbs back.
    if dilution is not None and dilution.get("severity", 0.0) > 0:
        if eps_lift is None:
            eps_lift = np.ones(n)
        forced = depth >= dilution.get("min_depth", 0.40)
        eps_lift = np.where(forced, eps_lift * (1.0 - dilution["severity"]), eps_lift)

    rec = np.full(n, np.nan)
    for i in range(n):
        if mdd[i] > -1e-9:                     # never drew down
            rec[i] = 0.0
            continue
        seg = price[i, trough_i[i]:]           # from trough to end of full sim
        if eps_lift is not None and eps_lift[i] != 1.0:
            seg = seg * eps_lift[i]            # buyback permanently lifts the post-trough path
        hit = np.where(seg >= peak_at_trough[i])[0]
        if len(hit):
            rec[i] = hit[0]
    # apply the recovery-quality shift as a multiplicative speed factor
    speed = 1.0 / (1.0 + np.clip(recov_shift, -0.4, 0.4))
    rec = rec * speed
    # ---- SOLVENCY / FINANCING IMPAIRMENT (gated by revenue durability) ----
    # On DEEP, crisis-driven drawdowns, a financially fragile name whose revenue
    # is NOT durable has probability `hazard` of never recovering (capital
    # markets shut while it still needs cash -> dilution/distress/insolvency).
    # This fattens the PERMANENT-loss tail for those names ONLY; it does not
    # touch drawdown DEPTH (beta set that), and durable-revenue / strong names
    # have hazard ~0 so they are untouched. Reproducible via a name-seeded RNG.
    if solv is not None and solv.get("hazard", 0.0) > 0.0:
        h = solv["hazard"]; md = solv.get("min_depth", 0.30)
        deep = mdd <= -md
        if deep.any():
            # path_offset (the chunk's starting index) must perturb the seed, or every
            # memory-frugal chunk re-draws the IDENTICAL uniforms -> the impairment mask is
            # perfectly correlated across chunks and the 150k-path MC loses independence
            # (Gemini bug 1). Still fully reproducible (deterministic in seed+offset).
            srng = np.random.default_rng((int(solv.get("seed", 0)) + int(path_offset)) & 0xFFFFFFFF)
            u = srng.random(n)
            impaired = deep & (u < h)
            rec = np.where(impaired, np.inf, rec)   # never recovers within the sim
    rec_base = rec.copy()   # natural+solvency recovery; cyclical floor & systemic delay
                            # both compose off THIS base (longer-of), so they don't stack
    # ---- CYCLICAL TWO-PHASE DEMAND TROUGH (memory/DRAM) ----
    # A cyclical crash coincides with a demand down-cycle: earnings keep falling
    # AFTER the price rolls over (a deeper SECOND LEG), and the price cannot reclaim
    # its prior peak until the cycle clears. So recovery is BACK-LOADED, not uniformly
    # slower: it is SUPPRESSED for `freeze_days` (demand-down + stabilization) and only
    # then allowed to complete. This shapes the recovery curve flat-early / steep-late
    # (near-zero P(recover<=6m), catching up by 18m+), which is the demand-rebound
    # picture rather than a constant multiplier. Beta still sets the market-driven depth;
    # the second leg is a distinct CYCLICAL-FUNDAMENTAL deepening, applied only here.
    if cycle is not None:
        md = cycle.get("min_depth", 0.15)
        breached = mdd <= -md
        sl = cycle.get("second_leg", 0.0)
        if sl > 0:
            mdd = np.where(breached, np.clip(mdd * (1.0 + sl), -0.95, 0.0), mdd)
        fd = float(cycle.get("freeze_days", 0))
        if fd > 0:
            # recovery cannot COMPLETE before the demand cycle clears; leaves NaN
            # (never recovered) and +inf (impaired) untouched.
            finite = np.isfinite(rec)
            rec = np.where(breached & finite, np.maximum(rec, fd), rec)
    # ---- SYSTEMIC FREEZE (total-collapse recovery contagion) ----
    # On paths where the BROAD MARKET collapsed past COLLAPSE_DEPTH (the keystone
    # plumbing froze), recovery is suspended MARKET-WIDE -- any name that fell, even a
    # healthy one, cannot reclaim its peak before the freeze clears. This is the 2008
    # "frozen for years, all layers" case: distinct from a name's own fundamentals, it
    # is imposed by the macro failure. freeze = dict(mask[n], days). NaN/inf untouched.
    if freeze is not None:
        fmask = freeze.get("mask"); fdays = float(freeze.get("days", 0.0))
        bday = freeze.get("breach_day")
        if fmask is not None and bday is not None and fdays > 0:
            fell = mdd <= -0.10
            fin = np.isfinite(rec)
            delay = fdays * float(freeze_dep)               # scaled by sub-market dependency
            # CAUSALITY + PAUSED-CLOCK (reviewer red-team): the freeze runs [bday, bday+delay].
            # It can only affect a recovery still in progress when it starts -- a name that
            # already healed before the freeze is untouched (no look-ahead). CRUCIALLY the
            # "still in progress" test uses the recovery AFTER the cyclical floor (pre_freeze_rec),
            # NOT the natural recovery: a memory name whose price path bounced by day 90 but is
            # held to day 315 by its demand cycle is STILL underwater when a day-200 freeze hits,
            # so the freeze must delay it (GPT/Gemini edge case). When it overlaps, recovery is
            # the longest of: the cyclical-floored recovery, the paused-clock (natural climb +
            # post-trough freeze overlap), and "can't finish before the freeze clears."
            troughf = trough_i.astype(float)
            pre_freeze_rec = rec                              # post-cyclical, pre-freeze recovery
            pre_freeze_end = troughf + pre_freeze_rec         # abs day it would recover incl. cyclical floor
            freeze_end = bday + delay
            gate = fell & fin & fmask & (bday < pre_freeze_end)
            overlap = np.zeros_like(rec_base)                 # compute only on gated paths -> no inf-inf warning
            overlap[gate] = np.maximum(0.0, freeze_end[gate] - np.maximum(bday[gate], troughf[gate]))
            freeze_floor = np.where(gate, np.maximum(0.0, freeze_end - troughf), 0.0)
            systemic_rec = np.maximum(rec_base + overlap, freeze_floor)
            rec = np.where(gate, np.maximum(pre_freeze_rec, systemic_rec), rec)
    return mdd, rec


def exceedance(mdd, thresholds):
    """P(max drawdown deeper than each threshold)."""
    return [float((mdd <= -t).mean()) for t in thresholds]


def recovery_stats(mdd, rec, lo, hi, mandate_days):
    """For drawdowns in the [lo, hi) bucket: frequency, median recovery months,
    and P(recover within the mandate)."""
    mask = (mdd <= -lo) & (mdd > -hi)
    if mask.sum() < 30:
        return dict(freq=float(mask.mean()), median_months=float("nan"),
                    p_recover=float("nan"), n=int(mask.sum()))
    r = rec[mask]
    # never-recovered (NaN) and solvency-impaired (np.inf, set ~line 395) are both "did
    # not recover". nan_to_num maps NaN->1e9 and +inf->a huge finite, so p_recover counts
    # them as non-recoveries correctly. The MEDIAN must use np.isfinite (NOT ~isnan, which
    # lets +inf through and poisons the median to inf when a fragile name impairs >50% of a
    # bucket) so it is the median recovery time of paths that DID recover. (Gemini bug B.)
    r_filled = np.nan_to_num(r, nan=1e9)       # never-recovered -> effectively infinite
    recovered = r[np.isfinite(r)]
    return dict(
        freq=float(mask.mean()),
        median_months=float(np.median(recovered) / 21.0) if recovered.size else float("nan"),
        p_recover=float((r_filled <= mandate_days).mean()),
        n=int(mask.sum()),
    )


def recovery_bands(mdd, rec, depth_threshold, band_months=None):
    """Catastrophe-avoidance view of recovery, conditional on a drawdown deeper
    than `depth_threshold`. Instead of one pass/fail number, this splits the
    outcome into the three categories that match the actual tolerance:
        acceptable : recovered within the comfortable band (e.g. 4-18 months)
        fast       : recovered FASTER than the band's lower edge (a V-bounce;
                     still fine, reported separately so the band is honest)
        tail       : did NOT recover by the band's upper edge -- THE DANGER.
                     This is the systemic-failure class the model defends against.
    Returns the conditional probabilities of each, plus the base rate of the
    drawdown itself. `band_months` defaults to C.ACCEPTABLE_BAND_MONTHS.
    """
    if band_months is None:
        band_months = getattr(C, "ACCEPTABLE_BAND_MONTHS", (4.0, 18.0))
    lo_d, hi_d = band_months[0] * 21.0, band_months[1] * 21.0   # months -> trading days
    mask = mdd <= -depth_threshold
    n = int(mask.sum())
    if n < 30:
        return dict(p_drawdown=float(mask.mean()), n=n,
                    p_fast=float("nan"), p_acceptable=float("nan"), p_tail=float("nan"))
    r = rec[mask]
    r_filled = np.nan_to_num(r, nan=1e9)
    p_fast       = float((r_filled < lo_d).mean())                       # quicker than the band
    p_acceptable = float(((r_filled >= lo_d) & (r_filled <= hi_d)).mean())# inside the band
    p_tail       = float((r_filled > hi_d).mean())                        # past 18m = danger
    return dict(
        p_drawdown=float(mask.mean()), n=n,
        p_fast=p_fast,
        p_acceptable=p_acceptable,
        p_within_mandate=p_fast + p_acceptable,   # recovered by the 18m edge, the headline "survivable" number
        p_tail=p_tail,                            # the systemic-failure tail
    )


def recovery_curve(mdd, rec, depth_threshold, horizons_months=None, suggested_months=None):
    """The DYNAMIC recovery view: instead of one hard threshold, report the
    cumulative probability of recovery at a whole SCHEDULE of horizons, so the
    user sees recovery as the curve it actually is and can pick their own
    comfort line rather than having one baked into the model.

    Conditional on a drawdown deeper than `depth_threshold`, returns for each
    horizon h in the schedule:
        months       : h
        p_recovered  : P(recovered by month h | drew down)
        beyond_suggested : True if h is past the suggested acceptability edge
                           -- these rows are FLAGGED, not discarded, so the
                           user can decide whether to count them.
    Also returns:
        p_never      : P(still underwater at the END of the simulation) -- the
                       genuinely permanent / systemic-failure class, distinct
                       from "slow but eventually heals."
        suggested_months : the model's recommended default cutoff (flagged as a
                           suggestion the user may override).

    The distinction this exposes is the one that matters most for catastrophe
    avoidance: a drawdown that heals at month 26 is SLOW (breaches a strict
    mandate) but is NOT permanent; one that never heals is the true systemic
    break. A hard threshold hides that difference; this curve reveals it.
    """
    if horizons_months is None:
        horizons_months = getattr(C, "RECOVERY_SCHEDULE_MONTHS",
                                   [6, 9, 12, 15, 18, 24, 30, 36])
    if suggested_months is None:
        suggested_months = getattr(C, "MANDATE_MONTHS", 18.0)

    mask = mdd <= -depth_threshold
    n = int(mask.sum())
    if n < 30:
        return dict(p_drawdown=float(mask.mean()), n=n, curve=[], p_never=float("nan"),
                    suggested_months=suggested_months)
    r = rec[mask]
    r_filled = np.nan_to_num(r, nan=1e9)
    curve = []
    for h in horizons_months:
        h_days = h * 21.0
        curve.append(dict(
            months=h,
            p_recovered=float((r_filled <= h_days).mean()),
            beyond_suggested=bool(h > suggested_months + 1e-9),  # FLAG, do not discard
        ))
    # "never" = not recovered by the end of the (generous) simulation window
    sim_end_days = C.SIM["days"]
    p_never = float((r_filled > sim_end_days).mean())
    return dict(
        p_drawdown=float(mask.mean()), n=n,
        curve=curve,
        p_never=p_never,                 # truly permanent: the core catastrophe signal
        suggested_months=suggested_months,
        note=("Rows with beyond_suggested=True recover only AFTER the suggested "
              f"{suggested_months:.0f}-month edge. They are flagged, not dropped: "
              "decide whether to count them as acceptable for your mandate."),
    )


# ===========================================================================
#  TOP-LEVEL RUNNERS  (called by run.py)
# ===========================================================================

def run_exposures(thresholds=(0.15, 0.20, 0.25, 0.30, 0.40, 0.50), verbose=True):
    """Run the Monte Carlo for every broad EXPOSURE across all horizons.
    Returns nested dict: results[name][horizon] = {exceedance, recovery_table}.
    """
    rng = np.random.default_rng(C.SIM["seed"])
    N, CH, DAYS = C.SIM["n_paths"], C.SIM["chunk"], C.SIM["days"]
    names = list(C.EXPOSURES.keys())
    store_mdd = {(nm, hz): [] for nm in names for hz in C.HORIZON_LABELS}
    store_rec = {(nm, hz): [] for nm in names for hz in C.HORIZON_LABELS}

    done = 0
    while done < N:
        n = min(CH, N - done)
        factor, crisis, grind = _simulate_factor(rng, n, DAYS, return_grind=True)
        freeze = _systemic_freeze(factor, DAYS)
        for nm in names:
            spec = dict(C.EXPOSURES[nm]); spec["mu"] = spec["alpha"]
            price = _price_path(rng, factor, crisis, spec, n, DAYS, grind=grind)
            for hz, hd in zip(C.HORIZON_LABELS, C.HORIZON_DAYS):
                mdd, rec = _drawdown_and_recovery(price, hd, path_offset=done, freeze=freeze)
                store_mdd[(nm, hz)].append(mdd); store_rec[(nm, hz)].append(rec)
        done += n
        if verbose:
            print(f"  exposures: {done:,}/{N:,} paths")

    results = {}
    md_days = C.MANDATE_YEARS * 252
    for nm in names:
        results[nm] = {}
        for hz in C.HORIZON_LABELS:
            mdd = np.concatenate(store_mdd[(nm, hz)])
            rec = np.concatenate(store_rec[(nm, hz)])
            results[nm][hz] = dict(
                exceedance=exceedance(mdd, thresholds),
                recovery=[dict(bucket=(lo, hi), **recovery_stats(mdd, rec, lo, hi, md_days))
                          for (lo, hi) in C.RECOVERY_BUCKETS],
            )
    return results, list(thresholds)


def _systemic_freeze(factor, days):
    """Per-path systemic-freeze descriptor (recovery contagion). The broad market =
    a beta-1, idio-free walk of the shared macro factor; paths where IT collapses past
    SYSTEMIC_FREEZE['collapse_depth'] are 'frozen' -- the financial plumbing seized, so
    every name's recovery on that path is suspended for `days`. The freeze WINDOW scales
    with funding-stress severity (FREEZE_SEVERITY): a true 2008 seizure freezes ~2y, a
    milder scare less. Returns dict(mask[n_paths], days) or None if disabled."""
    fz = getattr(C, "SYSTEMIC_FREEZE", None)
    if not fz:
        return None
    mkt = np.exp(np.cumsum(factor[:, :days], axis=1))          # broad-market path (beta=1)
    dd = mkt / np.maximum.accumulate(mkt, axis=1) - 1.0
    breached = dd <= -fz["collapse_depth"]                      # collapse crossed, per day
    has = breached.any(axis=1)
    # FIRST day the market breaches the systemic threshold (np.inf if it never does), so
    # the recovery calculator can enforce CAUSALITY -- a freeze can only delay a recovery
    # that hasn't already completed before the freeze starts (no look-ahead).
    bday = np.where(has, breached.argmax(axis=1).astype(float), np.inf)
    sev = float(getattr(C, "FREEZE_SEVERITY", 0.0))
    flo = fz.get("min_severity_floor", 0.4)
    days_frozen = fz["base_freeze_months"] * 21.0 * (flo + (1.0 - flo) * sev)
    return dict(mask=has, breach_day=bday, days=float(days_frozen))


def run_companies(thresholds=(0.15, 0.20, 0.25, 0.30, 0.40, 0.50), verbose=True):
    """Run the TAM-adjusted Monte Carlo for every COMPANY. Returns the premium
    decomposition plus per-name drawdown exceedance and conditional recovery.
    """
    decomp = decompose_premium()
    rng = np.random.default_rng(C.SIM["seed"])
    N, CH, DAYS = C.SIM["n_paths"], C.SIM["chunk"], C.SIM["days"]
    names = list(decomp.keys())
    # per-name idiosyncratic RNG (order-invariant, reproducible across runs):
    _idio_rngs = {nm: np.random.default_rng((C.SIM["seed"] ^ (zlib.crc32(nm.encode()) & 0xFFFFFFFF)) & 0xFFFFFFFF)
                  for nm in names}
    store_mdd = {(nm, hz): [] for nm in names for hz in C.HORIZON_LABELS}
    store_rec = {(nm, hz): [] for nm in names for hz in C.HORIZON_LABELS}
    # forward "fan chart" sampling: the price (as a multiple of today's) at a few
    # months, kept per path so we can percentile it into a p10/median/p90 CONE of
    # simulated futures at the end. This is a distribution, NOT a point forecast.
    # float32 sampled at ~9 points ≈ one extra horizon's worth of memory.
    TRAJ_MONTHS = [0, 3, 6, 9, 12, 18, 24, 30, 36]
    _traj_days = [min(int(m * 21), DAYS - 1) for m in TRAJ_MONTHS]
    store_traj = {nm: [] for nm in names}

    done = 0
    while done < N:
        n = min(CH, N - done)
        factor, crisis, grind = _simulate_factor(rng, n, DAYS, return_grind=True)
        subfactors = {g: rng.standard_normal((n, DAYS))
                      for g in getattr(C, "GROUP_RHO", {})}
        freeze = _systemic_freeze(factor, DAYS)   # per-path market-wide recovery suspension
        for nm in names:
            spec = company_to_spec(decomp[nm], name=nm)
            price = _price_path(rng, factor, crisis, spec, n, DAYS,
                                tail_mult=spec["tail_mult"], subfactors=subfactors,
                                grind=grind, idio_rng=_idio_rngs[nm])
            for hz, hd in zip(C.HORIZON_LABELS, C.HORIZON_DAYS):
                mdd, rec = _drawdown_and_recovery(price, hd, recov_shift=spec["recov_shift"],
                                                  bb=spec.get("bb"), solv=spec.get("solv"),
                                                  dilution=spec.get("dilution"), cycle=spec.get("cycle"),
                                                  path_offset=done, freeze=freeze,
                                                  freeze_dep=spec.get("freeze_dep", 1.0))
                store_mdd[(nm, hz)].append(mdd); store_rec[(nm, hz)].append(rec)
            store_traj[nm].append(price[:, _traj_days].astype(np.float32))
        done += n
        if verbose:
            print(f"  companies: {done:,}/{N:,} paths")

    md_days = C.MANDATE_YEARS * 252
    out = {"decomposition": decomp, "exceedance": {}, "recovery_cond": {}}
    for nm in names:
        out["exceedance"][nm] = {}
        for hz in C.HORIZON_LABELS:
            mdd = np.concatenate(store_mdd[(nm, hz)])
            out["exceedance"][nm][hz] = exceedance(mdd, thresholds)
        # conditional recovery given a >25% drawdown, at the 18m horizon
        mdd = np.concatenate(store_mdd[(nm, "18m")])
        rec = np.concatenate(store_rec[(nm, "18m")])
        mask = mdd <= -0.25
        p_rec = (float(np.mean(np.nan_to_num(rec[mask], nan=1e9) <= md_days))
                 if mask.sum() > 30 else float("nan"))
        # full dynamic recovery curve + the permanent ("never recovers") tail,
        # conditional on a >25% drawdown. This is the catastrophe-avoidance
        # headline (whitepaper Figs 6-7 / Table 1): it was always computable but
        # was not being saved. Now it is.
        rc = recovery_curve(mdd, rec, 0.25)
        # UNCONDITIONAL permanent-loss probability: P(drew down >25% AND never
        # recovered), across ALL paths. Unlike p_never (which is conditional on
        # a >25% drawdown), this does NOT bias against higher-beta names. A
        # high-beta name crosses -25% on many shallow, recoverable dips, which
        # dilutes its CONDITIONAL p_never and makes it look deceptively safe;
        # the unconditional measure is comparable across names of any beta.
        rec_filled_all = np.nan_to_num(rec, nan=1e9)
        p_deep_permanent = float((mask & (rec_filled_all > C.SIM["days"])).mean())
        # DRAWDOWN x RECOVERY MATRIX (the user's framing / GPT spec): for a >25% drawdown
        # occurring within each DRAWDOWN horizon (6/12/18m), the conditional probability it
        # has recovered within each RECOVER-AFTER-TROUGH horizon (6/12/18/24/36m), plus the
        # residual "not recovered by 36m" (slow / cyclical-wait / impaired / permanent).
        # All from already-stored per-horizon arrays -- no extra simulation.
        rec_horizons = getattr(C, "RECOVERY_AFTER_TROUGH_MONTHS", [6, 12, 18, 24, 36])
        matrix = {}
        for hz in C.HORIZON_LABELS:
            mdd_h = np.concatenate(store_mdd[(nm, hz)])
            rec_h = np.concatenate(store_rec[(nm, hz)])
            m_h = mdd_h <= -0.25
            row = {"p_drawdown": float(m_h.mean()), "n": int(m_h.sum())}
            if m_h.sum() > 30:
                rfill = np.nan_to_num(rec_h[m_h], nan=1e9)   # NaN/inf -> never (large)
                for mo in rec_horizons:
                    row[f"recover_{mo}m"] = float((rfill <= mo * 21.0).mean())
                row["not_recovered_36m"] = float(1.0 - row.get("recover_36m", 0.0))
            else:
                for mo in rec_horizons:
                    row[f"recover_{mo}m"] = None
                row["not_recovered_36m"] = None
            matrix[hz] = row
        # FORWARD FAN CHART: percentile cone of the simulated price (as a multiple
        # of today's). p10/median/p90 over the next 36 months — the spread of
        # simulated futures, refreshed every run. NOT a price prediction.
        traj_arr = np.concatenate(store_traj[nm], axis=0)        # (N, P)
        _p10 = np.percentile(traj_arr, 10, axis=0)
        _p50 = np.percentile(traj_arr, 50, axis=0)
        _p90 = np.percentile(traj_arr, 90, axis=0)
        trajectory = {                                           # t0 anchored to 1.0 (today)
            "months": list(TRAJ_MONTHS),
            "p10": [1.0] + [round(float(x), 4) for x in _p10[1:]],
            "p50": [1.0] + [round(float(x), 4) for x in _p50[1:]],
            "p90": [1.0] + [round(float(x), 4) for x in _p90[1:]],
        }
        out["recovery_cond"][nm] = dict(
            p_dd25=float(mask.mean()), p_recover=p_rec,
            recovery_quality=decomp[nm]["recovery_quality"],
            fragility=decomp[nm]["fragility"],
            p_never=rc["p_never"],            # P(never | DD>25%) -- compare within a beta cohort
            p_deep_permanent=p_deep_permanent,# P(DD>25% AND never) -- comparable across betas
            recovery_curve=rc["curve"],       # P(recovered) at 6/9/12/15/18/24/30/36m
            dd_recovery_matrix=matrix,        # drawdown-horizon x recover-after-trough matrix
            trajectory=trajectory,            # forward p10/median/p90 price cone (fan chart)
        )
    return out, list(thresholds)


# ===========================================================================
#  FULL-SIMULATION DOMINANCE SWEEP
#  (adopted from the Gemini/TDVM review: re-run the WHOLE Monte Carlo across a
#   range of dominance assignments, so we get an error bar on the actual output
#   probabilities -- not just on their ranking. This is heavier than the
#   ranking sweep in run.py, by design: it answers "by how many percentage
#   points does the headline risk number move when the moat score moves?")
# ===========================================================================

def dominance_sweep_one(name, d_values, n_paths=None, verbose=False):
    """Re-run the full company simulation for a SINGLE name across the given
    dominance values, holding all other calibration fixed. Returns, for each
    D value, the 18-month P(drawdown > 30%) and the conditional
    P(recover < mandate | drawdown > 25%).

    The point: dominance enters through the runway -> recovery channel (and a
    small bounded crisis-tail effect), so we expect the RECOVERY number to move
    materially and the DRAWDOWN-DEPTH number to move only a little. Reporting
    both makes that architectural choice visible and auditable.
    """
    import copy
    N = n_paths if n_paths is not None else C.SIM["n_paths"]
    CH, DAYS = C.SIM["chunk"], C.SIM["days"]
    md_days = C.MANDATE_YEARS * 252
    base_company = copy.deepcopy(C.COMPANIES[name])

    rows = []
    for d in d_values:
        # build a one-name calibration with dominance overridden, re-decompose
        perturbed = copy.deepcopy(C.COMPANIES)
        perturbed[name]["dominance"] = float(np.clip(d, 0.0, 1.0))
        decomp = decompose_premium(perturbed)
        spec = company_to_spec(decomp[name], name=name)

        rng = np.random.default_rng(C.SIM["seed"])   # same seed -> clean comparison
        mdd_all, rec_all = [], []
        done = 0
        while done < N:
            n = min(CH, N - done)
            # match run_companies: request grind + sub-factor contagion so the sweep's
            # probabilities are comparable to the baseline run (Gemini bug 4).
            factor, crisis, grind = _simulate_factor(rng, n, DAYS, return_grind=True)
            subfactors = {g: rng.standard_normal((n, DAYS)) for g in getattr(C, "GROUP_RHO", {})}
            freeze = _systemic_freeze(factor, DAYS)
            price = _price_path(rng, factor, crisis, spec, n, DAYS,
                                tail_mult=spec["tail_mult"], subfactors=subfactors, grind=grind)
            mdd, rec = _drawdown_and_recovery(price, C.HORIZON_DAYS[-1],  # 18m
                                              recov_shift=spec["recov_shift"],
                                              bb=spec.get("bb"), solv=spec.get("solv"),
                                              dilution=spec.get("dilution"), cycle=spec.get("cycle"),
                                              path_offset=done, freeze=freeze,
                                              freeze_dep=spec.get("freeze_dep", 1.0))
            mdd_all.append(mdd); rec_all.append(rec)
            done += n
        mdd = np.concatenate(mdd_all); rec = np.concatenate(rec_all)
        mask = mdd <= -0.25
        p_dd30 = float((mdd <= -0.30).mean())
        p_rec = (float(np.mean(np.nan_to_num(rec[mask], nan=1e9) <= md_days))
                 if mask.sum() > 30 else float("nan"))
        rows.append(dict(dominance=float(d), recovery_quality=decomp[name]["recovery_quality"],
                         p_dd30=p_dd30, p_recover=p_rec))
        if verbose:
            print(f"    {name:9s} D={d:.2f}  P(DD>30%)={p_dd30*100:4.0f}%  "
                  f"P(rec<2y|DD>25%)={p_rec*100:4.0f}%")
    return rows


def dominance_sweep_all(d_offsets=(-0.20, -0.10, 0.0, +0.10), n_paths=None, verbose=True):
    """Walk EVERY company through the dominance sweep. For each name we sweep
    its dominance from (base + most-negative offset) up through (base + most-
    positive offset), clipped to [0,1], so the sweep is centered on each name's
    own base estimate rather than an absolute scale. Returns a dict keyed by
    company, each holding the swept rows plus the base value and the observed
    swing in each output metric.
    """
    out = {}
    for name in C.COMPANIES:
        base_d = C.COMPANIES[name]["dominance"]
        d_values = sorted(set(float(np.clip(base_d + off, 0, 1)) for off in d_offsets))
        if verbose:
            print(f"  sweeping {name} (base D={base_d:.2f}) over {d_values} ...")
        rows = dominance_sweep_one(name, d_values, n_paths=n_paths, verbose=verbose)
        dd_vals = [r["p_dd30"] for r in rows]
        rec_vals = [r["p_recover"] for r in rows if r["p_recover"] == r["p_recover"]]
        out[name] = dict(
            base_dominance=base_d,
            rows=rows,
            dd30_swing=(min(dd_vals), max(dd_vals)),
            recover_swing=(min(rec_vals), max(rec_vals)) if rec_vals else (float("nan"), float("nan")),
        )
    return out
