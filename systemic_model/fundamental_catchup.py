"""
============================================================================
 FUNDAMENTAL_CATCHUP -- the deterministic "earn-back" clock
============================================================================
 The closed-form complement to the Monte Carlo. If a drop is PURELY multiple
 compression (the business delivers, the market just stops paying the
 premium), recovery time is not random -- it is algebra. The company grows
 INTO the lost multiple:

     T_years = ln(PE_peak / PE_floor) / ln(1 + g_effective)

 This reproduces, in closed form, what the engine's recovery_quality channel
 proves path-by-path: fast compounders heal fast; slow growers on stretched
 multiples are the real value traps.

 THREE refinements over a naive 18x flat floor (these matter a lot):

 1. DYNAMIC FLOOR.  The multiple does not reset to a textbook 18x. Durable,
    cash-rich, high-earnings-quality businesses keep a structurally higher
    floor (a "quality premium" / buyback put). floor = BASE_PE + justified-SAM
    premium + quality lift(earn_quality, balance).

 2. BUYBACK YIELD.  When the stock falls, a cash-rich company's buyback retires
    more shares per dollar, ADDING to EPS growth -- a trampoline the naive
    revenue-growth view misses. We add a balance-sheet-scaled buyback yield to
    effective growth.

 3. TAM SATURATION.  High growth only helps if there is room to sustain it. As
    SAM penetration approaches 1, organic growth decelerates, so we handicap
    the organic component by remaining SAM headroom. A name that must outgrow a
    huge multiple but hits its SAM wall first is a structural trap (-> Never).

 All inputs are ESTIMATES (refresh like calibration.MACRO). "g_eff" starts from
 the model's EXPECTED revenue growth input (not a true bottom-up EPS forecast),
 then adjusts for an S-curve SAM wall and earnings-quality-weighted buybacks.
 KNOWN LIMITS (Gemini red-team): it models the multiple shrinking to a floor,
 not the DENOMINATOR collapsing -- in a cyclical bust forward earnings can fall
 faster than price (P/E expands); and it does not model margins, dilution, or
 operating leverage. The point is the RANKING and mechanism, not exact dates.
 RESEARCH MODEL, NOT INVESTMENT ADVICE.
============================================================================
"""
import os, sys, math, json

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "discovery"))

import calibration as C
import tiering as T
import extension_data as X
import valuation_link as V

MAX_YEARS = 15.0   # beyond this we call it a structural trap
# PEG-justified floor for HIGH-GROWTH names: a fast grower's multiple is justified
# by GROWTH (PEG), not a flat 18x. A name growing g% "deserves" ~PEG_FAIR*g of P/E,
# so its post-crash floor is higher and it earns back faster. Only lifts the floor
# for genuine earners growing above HIGH_GROWTH_G; low growers are unaffected
# (their PEG floor sits below the quality floor, so the max() is a no-op).
PEG_FAIR = 1.4          # a fair PEG for durable growth (1.0 = "GARP", >2 = expensive)
PEG_CAP  = 55.0         # don't justify silly multiples even on huge growth
HIGH_GROWTH_G = 0.20    # annualized growth above which the PEG floor can bind


def _quality_lift(earn_quality, balance):
    """Extra P/E points the floor keeps for durable, cash-generative names.
    A utility-like earnings stream + fortress balance sheet defends a higher
    trough multiple (Apple never resets to 18x). Bounded, never negative."""
    return max(0.0, 7.0 * (earn_quality - 0.50) + 7.0 * (balance - 0.55))


def _buyback_yield(balance):
    """EPS lift from retiring cheap shares in a drawdown. Scales with balance-
    sheet strength: ~0 at neutral, ~4%/yr for a fortress (Apple/NVDA)."""
    return max(0.0, 0.04 * (balance - 0.50) / 0.40)


def _trough_buyback(pe_peak, drop, net_cash_to_mcap, balance, earnq, unsupported_frac):
    """One-time OPPORTUNISTIC buyback at the trough — the 'slingshot'.

    A cash-rich firm deploys excess cash at the depressed price; cheaper shares
    retire a disproportionate chunk of the float, stepping EPS up instantly and
    permanently LOWERING the price it must climb back to. Returns the dict the
    earn-back loop needs. Gated against the four ways a naive version cheats:

      - PROCYCLICAL EXECUTION: only fortress balance sheets with durable
        earnings actually buy the dip; weak/cyclical names hoard or issue
        equity at the low (deploy_pct -> 0).
      - INTEREST DRAG: spending cash forfeits its after-tax T-bill yield; for a
        high-multiple name that lost interest is a big share of earnings.
      - FLOATING-PREMIUM PUNCTURE: if the fall was mostly unsupported premium
        (unsupported_frac high), buying back still-rich stock destroys value, so
        the float-cut credit is scaled down by (1 - unsupported_frac).
      - BALANCE-SHEET DRAW-DOWN: cash spent lowers the post-event floor (handled
        by the caller via bal_after) so cash is not double-counted.
      - ACCRETION (the fix): a value-maximizing board does NOT retire shares when
        the buyback is dilutive. EPS rises iff shares_retired > interest_drag,
        which (both scale linearly with cash_used) reduces to the cash-size-
        independent test  (1 - unsupported_frac)/buy_price_frac > cash_yield*PE.
        Equivalently: the post-discount, premium-haircut earnings yield must beat
        the forfeited cash yield. If it doesn't, capital return is a dividend /
        the cash is held (deploy -> 0) -- not a value-destroying repurchase.
    """
    cy = getattr(C, "CASH_YIELD_AFTER_TAX", 0.035)
    excess = max(0.0, net_cash_to_mcap - 0.05)          # keep 5% of mcap as working cash
    if excess <= 0 or drop <= 0:
        return dict(float_cut=0.0, eps_lift=1.0, cash_used=0.0, bal_after=balance)
    buy_price_frac = max(0.20, 1.0 - drop * 0.75)        # avg buy price (not perfectly at bottom)
    # ACCRETION GATE: only buy back if it lifts EPS at this discount & haircut.
    accretive = (1.0 - unsupported_frac) / buy_price_frac > cy * pe_peak
    deploy = (0.65 if (balance >= 0.80 and earnq >= 0.70)
              else (0.30 if balance >= 0.60 else 0.0)) if accretive else 0.0
    if deploy <= 0:
        return dict(float_cut=0.0, eps_lift=1.0, cash_used=0.0, bal_after=balance)
    cash_used = deploy * excess                          # as fraction of PEAK mcap
    shares_retired = min(0.25, cash_used / buy_price_frac)
    shares_retired *= max(0.0, 1.0 - unsupported_frac)   # no credit for buying punctured premium
    interest_drag = min(0.25, cash_used * cy * pe_peak)      # lost after-tax interest, as frac of E
    eps_lift = (1.0 - interest_drag) / max(1.0 - shares_retired, 0.01)
    bal_after = max(0.0, balance - 0.5 * cash_used / 0.20)   # spent cash lowers the floor
    return dict(float_cut=shares_retired, eps_lift=eps_lift, cash_used=cash_used,
                bal_after=bal_after, interest_drag=interest_drag)


def run(verbose=True):
    decomp = V.sam_decompose()   # has fwd_pe, justified_eff, pen_sam, earn_quality, balance
    rows = []
    for nm, o in decomp.items():
        bb = {}                       # reset per iteration: never inherit a prior name's
                                      # buyback dict via locals() (Gemini bug 2)
        g18 = T.UNIVERSE.get(nm, (None, None, 0.0))[2]
        if g18 is None or g18 <= 0 or o.get("fwd_pe", 0) <= 0:
            continue
        g_ann = (1 + g18) ** (12.0 / 18.0) - 1.0
        bal = o.get("balance", 0.55)
        earnq = o.get("earn_quality", 0.6)
        pen_sam = min(o.get("pen_sam", o.get("pen", 0.5)), 1.0)

        # effective EPS growth: organic (handicapped by an S-CURVE SAM wall) +
        # buyback yield CONDITIONED on earnings quality. Cyclicals (low earn_q)
        # suspend buybacks exactly when the stock craters and FCF collapses, so
        # only durable cash generators get the full buyback trampoline.
        sat = 1.0 / (1.0 + math.exp(8.0 * (pen_sam - 0.85)))   # ~1 below .7, falls off a cliff -> .1 by 1.0
        # CRASH-CONDITIONAL GROWTH (secular holds/accelerates, cyclical dips-then-
        # rebounds, broken steps down) -- the per-theme recovery-growth response.
        try:
            import crash_growth as _CG
            cg_mult = _CG.recovery_g_mult(nm); cg_type = _CG.archetype(nm)
        except Exception:
            cg_mult = 1.0; cg_type = "n/a"
        g_eff = (g_ann * sat * cg_mult) + _buyback_yield(bal) * earnq

        pe_peak = o["fwd_pe"]
        pe_floor = C.BASE_PE + o.get("justified_eff", 0.0) + _quality_lift(earnq, bal)
        # PEG-JUSTIFIED FLOOR (high-growth): a fast, real-earnings grower's multiple
        # is anchored to growth, so its floor is higher and the earn-back is shorter.
        peg_floor = 0.0
        if g_ann >= HIGH_GROWTH_G and earnq >= 0.50:
            peg_floor = min(PEG_CAP, PEG_FAIR * g_ann * 100.0)
            pe_floor = max(pe_floor, peg_floor)
        # CYCLE-ADJUSTED P/E for CYCLICAL names (GPT review): a memory/cyclical name's
        # forward P/E is computed on PEAK (cyclically high) earnings, so it screens
        # deceptively cheap and the clock returns a false "0y (no gap)". Normalize to a
        # through-cycle multiple by marking earnings DOWN to mid-cycle: mid-cycle EPS is
        # ~CYCLE_HAIRCUT (30%) BELOW peak, so the normalized P/E = fwd_pe / (1 - 0.30) =
        # ~1.43x the reported multiple. That RAISES the effective multiple the price must
        # grow back into, and we trim the PEG growth-credit (you don't underwrite full
        # secular PEG at the top of a memory cycle). DRAM/Micron then read as cyclical/
        # rebound-dependent, not a clean 0y case.
        if cg_type == "cyclical":
            CYCLE_HAIRCUT = 0.30                              # mid-cycle EPS ~30% below peak
            pe_peak = pe_peak / (1.0 - CYCLE_HAIRCUT)          # through-cycle (normalized) P/E
            if peg_floor > 0:
                peg_floor *= 0.70
                pe_floor = max(C.BASE_PE + o.get("justified_eff", 0.0) + _quality_lift(earnq, bal),
                               peg_floor)
        unsup = o.get("unsupported_frac", o.get("val_gap", 0.0))
        ncash = X.net_cash(nm)

        def _clock(g, num, den):
            """ln(num/den)/ln(1+g) with the SAM-wall trap; returns (years, verdict)."""
            if den <= 0 or num <= den:
                return 0.0, "0y (no gap)"
            yy = math.log(num / den) / math.log(1 + g)
            need = (1 + g_ann) ** min(yy, MAX_YEARS); room = 1.0 / max(pen_sam, 1e-6)
            if yy > MAX_YEARS or need > room * 1.5:
                return float("inf"), "Never (hits SAM wall first)"
            if yy <= C.MANDATE_MONTHS / 12.0:
                return yy, "FAST (within mandate)"
            return (yy, "DANGER (>5y dead money)") if yy > 5.0 else (yy, "slow")

        pre_earnings = pe_peak >= 150 and earnq < 0.50
        if pre_earnings:
            tag = "no profit base" if earnq < 0.30 else "thin earnings, TAM-priced — use P/S"
            years = years_bb = float("inf"); ratio = float("inf")
            float_cut = 0.0; verdict = f"N/A ({tag})"
        elif g_eff <= 0.0:
            years = years_bb = float("inf"); ratio = float("inf")
            float_cut = 0.0; verdict = "Never (growth ≤ 0)"
        else:
            ratio = pe_peak / pe_floor
            # NAIVE clock: grow into the compressed multiple, no trough buyback.
            years, verdict = _clock(g_eff, pe_peak, pe_floor)
            # BUYBACK-ADJUSTED clock: the multiple-compression drop is d = 1 - floor/peak;
            # the firm fires its cash at that depressed price.
            drop = max(0.0, 1.0 - pe_floor / pe_peak)
            bb = _trough_buyback(pe_peak, drop, ncash, bal, earnq, unsup)
            float_cut = bb["float_cut"]
            pe_floor_after = C.BASE_PE + o.get("justified_eff", 0.0) + _quality_lift(earnq, bb["bal_after"])
            # share retirement steps EPS up -> the effective floor it must reach is
            # Share retirement lifts EPS, so the recovery ratio is
            # PE_peak / (pe_floor_after * eps_lift): fewer shares => old price is
            # reached at a LOWER multiple. (eps_lift MULTIPLIES the denominator.)
            years_bb, vb = _clock(g_eff, pe_peak, pe_floor_after * bb["eps_lift"])
            # the buyback is an OPTION: a firm exercises it only when it helps, so
            # the reported earn-back is never worse than the no-buyback clock. With
            # the accretion gate above this rarely binds, but it is correct insurance.
            if years != float("inf") and years_bb != float("inf"):
                years_bb = min(years_bb, years)
            if float_cut > 0.002 and years_bb < years:
                verdict = vb + f" · buyback −{float_cut*100:.1f}% float"
        drop_c = 0.0 if pre_earnings else max(0.0, 1.0 - pe_floor / pe_peak)
        epslift = bb.get("eps_lift", 1.0)     # bb is {} unless the else-branch assigned it
        pe_after = None if pre_earnings else round(pe_peak * (1.0 - drop_c) / max(epslift, 1e-9), 1)
        rows.append(dict(name=nm, pe_peak=pe_peak, pe_floor=round(pe_floor, 1),
                         ratio=ratio, g_ann=round(g_ann, 3), g_eff=round(g_eff, 3),
                         buyback=round(_buyback_yield(bal) * earnq, 3), pen_sam=round(pen_sam, 2),
                         net_cash=ncash, float_cut=round(float_cut, 3),
                         drop=round(drop_c, 3), cash_used=round(bb.get("cash_used", 0.0), 3),
                         eps_lift=round(epslift, 3), interest_drag=round(bb.get("interest_drag", 0.0), 3),
                         real_pe_after_drop=pe_after, crash_growth=cg_type,
                         years=years, years_bb=years_bb, verdict=verdict))

    rows.sort(key=lambda r: (r["years"] if r["years"] != float("inf") else 1e9), reverse=True)

    L = ["# Fundamental earn-back clock — years to outgrow a pure valuation reset",
         "\n*If a drop is pure multiple compression, recovery is deterministic: the "
         "company grows into the lost multiple. T = ln(PE_peak/PE_floor) / ln(1+g_eff). "
         "Floor is lifted by earnings quality + balance sheet (quality premium / buyback "
         "put); growth is lifted by buyback yield and handicapped by SAM saturation. "
         "Estimates — read the ranking, not the decimals. Research model, not advice.*",
         "\n| Name | P/E peak→floor | real P/E after drop | compression | eff g | SAM pen | naive yrs | trough buyback | **buyback-adj yrs** | verdict |",
         "|---|--:|--:|--:|--:|--:|--:|--:|--:|---|"]
    for r in rows:
        yr = "∞" if r["years"] == float("inf") else f"{r['years']:.1f}"
        yb = "∞" if r.get("years_bb", r["years"]) == float("inf") else f"{r.get('years_bb', r['years']):.1f}"
        rr = "—" if r["ratio"] == float("inf") else f"{r['ratio']:.2f}×"
        fc = "—" if r.get("float_cut", 0) < 0.002 else f"−{r['float_cut']*100:.1f}%"
        rpe = "—" if r.get("real_pe_after_drop") is None else f"{r['real_pe_after_drop']:.1f}×"
        L.append(f"| {r['name']} | {r['pe_peak']:.0f}→{r['pe_floor']:.1f} | {rpe} | {rr} "
                 f"| {r['g_eff']*100:.0f}% | {r['pen_sam']*100:.0f}% | {yr} | {fc} | **{yb}** | {r['verdict']} |")
    L.append("\n## The counter-intuitive lesson")
    L.append("In a multiple-compression regime, **a low-growth name on a stretched multiple is "
             "more dangerous than a high-growth name on a higher one.** A fast compounder "
             "(NVIDIA ~28%) earns back a 30→27× reset inside the mandate; a slow grower (Apple "
             "~5% organic) takes years to earn back a 35→floor reset. Names priced on future TAM "
             "(IonQ — no profit base; Tesla — thin earnings) aren't on a meaningful P/E clock "
             "at all (judge on P/S) and can hit their SAM wall first.")
    L.append("\n## What the trough-buyback 'slingshot' actually shows here")
    L.append("The one-time trough buyback (deploy excess cash at the depressed price, retire a "
             "disproportionate slice of float, step EPS up) is implemented in full — depth-scaled "
             "retirement, interest-income drag, a procyclical execution gate, a balance-sheet-floor "
             "penalty so cash isn't double-counted, a (1−unsupported_frac) haircut so a name gets no "
             "credit for buying back correctly-punctured premium, and an **accretion gate** so a board "
             "only buys when it raises EPS (E/P > after-tax cash yield). **The honest finding: under a "
             "pure multiple-compression reset the rational trough buyback fires for no one in this "
             "universe** — and the reason is structural, not just low cash. The only names with a "
             "compression *drop* to buy into are the high-multiple names, and at those multiples the "
             "earnings yield is below the ~3.5% after-tax cash yield, so the buyback is dilutive and "
             "the gate blocks it (Alphabet at 29× is the closest call — gated out). The low-multiple "
             "names where a buyback WOULD be accretive (Micron, Kioxia, Qualcomm, Meta, Cisco, DRAM) "
             "show '0y — no gap': their P/E already sits at/below the floor, so there is no discount "
             "to exploit. The two conditions — a deep discount and an accretive multiple — are "
             "anti-correlated in a mild de-rating, so the closed-form slingshot is near self-defeating "
             "here by construction. The mega-caps people *assume* have a giant cash slingshot "
             "(Apple ~4% net cash now, Microsoft ~5%) have actually spent their hoards down over a "
             "decade of buybacks, so their dip-buying comes from ongoing FCF (already in the small "
             "annual buyback yield), not a war chest. The big-gap names that *would* benefit from a "
             "cash slingshot (IonQ, CoreWeave, Tesla) are exactly the ones with no deployable cash "
             "or no earnings floor. So the slingshot is real, correctly built — and mostly dormant "
             "today. That is the non-obvious answer: in this cycle, cash-as-an-offensive-weapon is "
             "less available than the narrative suggests. This is the closed-form shadow of what the "
             "Monte Carlo's recovery_quality channel proves path-by-path.")
    open(os.path.join(HERE, "fundamental_catchup.md"), "w").write("\n".join(L))
    # strict-JSON-safe: Infinity -> null + explicit flag (some parsers reject Infinity)
    safe = []
    for r in rows:
        d = dict(r)
        inf = (d["years"] == float("inf"))
        d["is_infinite"] = inf
        d["years"] = None if inf else round(d["years"], 2)
        d["years_bb"] = None if d.get("years_bb", d["years"]) == float("inf") else round(d.get("years_bb", d["years"]), 2)
        d["ratio"] = None if d["ratio"] == float("inf") else round(d["ratio"], 3)
        safe.append(d)
    json.dump({"rows": safe, "base_pe": C.BASE_PE, "mandate_years": C.MANDATE_MONTHS / 12.0},
              open(os.path.join(HERE, "fundamental_catchup.json"), "w"), indent=1)

    if verbose:
        print(f"{'Name':22s} {'PE pk->fl':>11s} {'naive':>6s} {'float':>7s} {'BBadj':>6s}  verdict")
        print("-" * 84)
        for r in rows:
            yr = "Never" if r["years"] == float("inf") else f"{r['years']:.1f}"
            yb = "Never" if r.get("years_bb", r["years"]) == float("inf") else f"{r.get('years_bb', r['years']):.1f}"
            fc = "-" if r.get("float_cut", 0) < 0.002 else f"-{r['float_cut']*100:.1f}%"
            print(f"{r['name']:22s} {('%.0f->%.1f' % (r['pe_peak'], r['pe_floor'])):>11s} "
                  f"{yr:>6s} {fc:>7s} {yb:>6s}  {r['verdict']}")
        print("\nwrote fundamental_catchup.md / .json")
    return rows


if __name__ == "__main__":
    run()
