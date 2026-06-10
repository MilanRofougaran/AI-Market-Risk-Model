"""
============================================================================
 GROWTH_RECOVERY -- two ranking regimes, because recovery works differently
============================================================================
 The user's framing: rank names/ETFs by HOW they recover, which depends on the
 growth regime.

   HIGH-GROWTH (secular fast growers): recovery is about GROWING INTO the
     multiple. The right anchor is JUSTIFIED PEG, not P/E -- a 60x P/E on 50%
     growth is PEG ~1.2, cheap, and fills fast. So recovery TIME is the
     PEG-justified earn-back clock, and a name "ranks high" when it is highly
     likely to reclaim its level within the 18-month mandate
     (P(recover<=18m) >= RANK_HIGH_P, default 0.75) OR its PEG earn-back is
     inside the mandate.

   DIVERSIFIED / SAFE (low growth): recovery is the EXISTING mechanism -- a
     cash-rich name buys back stock at the low (the slingshot), and the
     adjusted-P/E earn-back clock measures how long growth + buybacks take to
     reclaim the old price. Ranked by reward-vs-S&P.

 For ETFs the same split applies, but read the etf_lens: a HIGH-GROWTH thematic
 ETF is a good fast-recovery bet ONLY IF the theme's TAM/SAM stays intact and
 growth persists/accelerates after the crash (secular) -- a cyclical-TAM basket
 (DRAM/memory) can still rank high on execution-diversification but carries a
 dip-then-rebound growth path the deterministic clock doesn't yet model.

 Reads fundamental_catchup.json (PEG earn-back), results.json (MC recovery),
 tier_table.csv (growth, reward), etf_lens.json. ESTIMATES. NOT INVESTMENT ADVICE.
============================================================================
"""
import os, sys, csv, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "discovery"))

HIGH_GROWTH_G = 0.40      # > 40% expected 18m growth = HIGH-GROWTH regime (the High tier)
RANK_HIGH_P  = 0.75       # P(recover within 18m | fell) at/above this = MC "strong"
MC_FLOOR     = 0.55       # softer "MC acceptable" bar; below this the MC is "uncertain"
MANDATE_Y    = 1.5        # 18 months


def _recovery_rank(cg, pr, py, is_high):
    """Crash-growth-aware recovery label (GPT reporting-consistency review). The
    growth TIER ('High') only says a name grows fast; this says HOW it recovers, so
    a broken or cyclical name never wears the same clean verdict as a secular grower:

      broken    -> 'broken thesis — avoid unless evidence changes'   (hard gate)
      cyclical  -> 'cyclical high-growth / rebound-dependent'        (needs TAM rebound)
      secular   -> unqualified 'secular high-growth' ONLY when the PEG earn-back is
                   inside the 18m mandate AND the Monte-Carlo recovery prob is at least
                   acceptable. If PEG is fast but the MC is weak (common at high stress),
                   it is the honest hedge 'PEG-fast / MC-uncertain', NOT a clean HIGH.
      low-growth secular -> 'diversified / safe (buyback earn-back)'.
    Returns (rank_high: bool, label: str)."""
    peg_pass  = py <= MANDATE_Y
    mc_strong = pr >= RANK_HIGH_P
    mc_ok     = pr >= MC_FLOOR
    if cg == "broken":
        return False, "broken thesis — avoid unless evidence changes"
    if cg == "cyclical":
        return False, ("cyclical high-growth / rebound-dependent" if (peg_pass or mc_ok)
                       else "cyclical — needs TAM rebound")
    # secular (or unknown archetype treated as secular)
    if not is_high:
        return False, "diversified / safe (buyback earn-back)"
    if peg_pass and (mc_strong or mc_ok):
        return True, "secular high-growth"
    if peg_pass:                      # PEG-justified fast, but MC recovery not convincing
        return False, "PEG-fast / MC-uncertain"
    if mc_strong:
        return True, "secular high-growth"
    return False, "watch"


def _load(p, d=None):
    try:
        return json.load(open(os.path.join(HERE, p)))
    except Exception:
        return d


def run(verbose=True):
    res = _load("results.json", {}) or {}
    rc = (res.get("companies", {}) or {}).get("recovery_cond", {})
    fc = {r["name"]: r for r in (_load("fundamental_catchup.json", {}) or {}).get("rows", [])}
    el = _load("etf_lens.json", {}) or {}
    # Build the rows from results.json IN MEMORY via tiering.build_rows -- NOT by reading
    # tier_table.csv, which run_all writes AFTER this module (so the CSV is always a run
    # stale, and a freshly bridged name would be missing). (Gemini bug 3.)
    import tiering as _T
    rows = []
    try:
        rows = _T.build_rows(res)
    except Exception:
        rows = []

    high, safe = [], []
    for r in rows:
        nm = r["name"]; g = r.get("growth") or 0.0
        if nm in getattr(_T, "LEVERAGED", []):            # 3x trading vehicles excluded
            continue
        d = rc.get(nm, {})
        p_rec = d.get("p_recover")                       # P(recover within 18m | fell >25%)
        peg_y = fc.get(nm, {}).get("years")              # PEG-justified earn-back (years)
        bb_y = fc.get(nm, {}).get("years_bb")            # buyback-adjusted earn-back
        try:
            import crash_growth as _CG
            cg = _CG.archetype(nm)
        except Exception:
            cg = "n/a"
        rec = dict(name=nm, kind=r.get("kind"), growth=g, p_recover=p_rec,
                   peg_years=peg_y, bb_years=bb_y, crash_growth=cg,
                   tail=r.get("p_deep_permanent"), vs_sp=r.get("vs_sp"),
                   theme=(el.get(nm, {}) or {}).get("class", "").split(" (")[0])
        pr = p_rec if p_rec is not None else 0.0
        py = peg_y if peg_y is not None else 99
        rh, label = _recovery_rank(cg, pr, py, is_high=(g > HIGH_GROWTH_G))
        rec["rank_high"] = rh
        rec["rank_label"] = label      # back-compat field used by the .md table
        rec["recovery_rank"] = label   # canonical name surfaced into tier_table.csv + report
        if g > HIGH_GROWTH_G:
            high.append(rec)
        else:
            safe.append(rec)

    # HIGH-GROWTH: sort by PEG earn-back speed (fastest first), then recovery prob
    high.sort(key=lambda r: ((r["peg_years"] if r["peg_years"] is not None else 99),
                             -(r["p_recover"] or 0)))
    # SAFE/DIVERSIFIED: sort by reward-vs-S&P
    safe.sort(key=lambda r: -(r["vs_sp"] or 0))

    if verbose:
        print("GROWTH-REGIME RECOVERY RANKING")
        print("=" * 84)
        print(f"\nHIGH-GROWTH (>40% 18m) — recovery via PEG earn-back; rank-high if "
              f"P(recover<=18m)>={RANK_HIGH_P:.0%} or PEG earn-back<=18m")
        print(f"  {'Name':24s} {'grow':>5s} {'PEGyrs':>7s} {'P(rec<18m)':>10s} {'>3yT':>5s}  rank")
        for r in high:
            py = "∞" if r["peg_years"] in (None, float('inf')) else f"{r['peg_years']:.1f}"
            pr = "-" if r["p_recover"] is None else f"{r['p_recover']*100:.0f}%"
            print(f"  {r['name'][:24]:24s} {r['growth']*100:4.0f}% {py:>7s} {pr:>10s} "
                  f"{(r['tail'] or 0)*100:4.0f}%  {r.get('rank_label','HIGH' if r['rank_high'] else 'watch')}")
        print(f"\nDIVERSIFIED / SAFE (<=40%) — recovery via buyback + adjusted-PE earn-back; rank by vs-S&P")
        print(f"  {'Name':24s} {'grow':>5s} {'BByrs':>6s} {'vsS&P':>6s} {'>3yT':>5s}")
        for r in safe:
            by = "∞" if r["bb_years"] in (None, float('inf')) else f"{r['bb_years']:.1f}"
            print(f"  {r['name'][:24]:24s} {r['growth']*100:4.0f}% {by:>6s} "
                  f"{(r['vs_sp'] or 0):6.2f} {(r['tail'] or 0)*100:4.0f}%")

    # flat name -> recovery_rank map so build_dashboard / complete_report can stamp the
    # recovery verdict onto the master tables without re-deriving the gate (GPT review).
    rank_map = {r["name"]: r["recovery_rank"] for r in (high + safe)}
    out = {"high_growth": high, "diversified_safe": safe, "recovery_rank": rank_map,
           "params": {"high_growth_g": HIGH_GROWTH_G, "rank_high_p": RANK_HIGH_P,
                      "mc_floor": MC_FLOOR}}
    json.dump(out, open(os.path.join(HERE, "growth_recovery.json"), "w"), indent=1)

    L = ["# Growth-regime recovery ranking",
         "\n*Two regimes, because recovery works differently. HIGH-GROWTH names grow "
         "INTO the multiple — anchored to JUSTIFIED PEG (a 60x P/E on 50% growth is "
         "PEG ~1.2, cheap), so recovery time is the PEG earn-back clock and they rank "
         "high when likely to reclaim their level within the 18-month mandate. "
         "DIVERSIFIED/SAFE names recover via buyback + adjusted-P/E earn-back, ranked "
         "by reward-vs-S&P. Research model, not investment advice.*",
         f"\n## High-growth (>40% 18m) — rank-high if P(recover≤18m) ≥ {RANK_HIGH_P:.0%} or PEG earn-back ≤ 18m",
         "\n| Name | type | growth | crash-growth | PEG earn-back | P(recover≤18m) | >3y tail | rank |",
         "|---|---|--:|:--:|--:|--:|--:|:--:|"]
    for r in high:
        py = "∞" if r["peg_years"] in (None, float('inf')) else f"{r['peg_years']:.1f}y"
        pr = "—" if r["p_recover"] is None else f"{r['p_recover']*100:.0f}%"
        lbl = r.get("rank_label", "HIGH" if r["rank_high"] else "watch")
        lbl = ("**" + lbl + "**") if r["rank_high"] else lbl
        L.append(f"| {r['name']} | {r['kind']} | {r['growth']*100:.0f}% | {r.get('crash_growth','')} | {py} | {pr} | "
                 f"{(r['tail'] or 0)*100:.0f}% | {lbl} |")
    L.append("\n## Diversified / safe (≤40% 18m) — buyback + adjusted-P/E earn-back, ranked by vs-S&P")
    L.append("\n| Name | type | growth | buyback earn-back | vs S&P | >3y tail |")
    L.append("|---|---|--:|--:|--:|--:|")
    for r in safe:
        by = "∞" if r["bb_years"] in (None, float('inf')) else f"{r['bb_years']:.1f}y"
        L.append(f"| {r['name']} | {r['kind']} | {r['growth']*100:.0f}% | {by} | "
                 f"{(r['vs_sp'] or 0):.2f} | {(r['tail'] or 0)*100:.0f}% |")
    L.append("\n## How to read it")
    L.append("- **High-growth recovery = PEG earn-back**: a fast grower's fair multiple is set by "
             "growth (PEG≈1.4×g), so a name trading below that floor has ~no gap and reclaims fast.")
    L.append("- **Rank-high gate**: P(recover≤18m) ≥ 75% (the user's threshold) OR a PEG earn-back "
             "inside the 18-month mandate. At today's elevated-stress calibration the conditional "
             "MC recovery rarely clears 75% on its own, so the PEG earn-back time is the binding, "
             "more discriminating signal for the high-growth bucket.")
    L.append("- **For high-growth ETFs** this holds only if the theme's TAM/SAM stays intact and "
             "growth persists/accelerates after the crash (secular). A cyclical-TAM basket (DRAM/"
             "memory) dips-then-rebounds — execution-diversified, but on a cyclical demand curve.")
    open(os.path.join(HERE, "growth_recovery.md"), "w").write("\n".join(L))
    if verbose:
        print("\nwrote growth_recovery.md / .json")
    return out


if __name__ == "__main__":
    run()
