"""
============================================================================
 ETF_HORIZON_RANK -- rank ETFs by EXPECTED RETURN per holding horizon
============================================================================
 The question this answers (the user's framing): for a 12-month / 2-year /
 3-year / 5-year hold, EACH PERIOD INDEPENDENTLY, rank ETFs on a reward that
 already accounts for "high growth, but if the market drops it has a good
 chance to be recovered in time."

 The key insight: the SAME high-growth ETF ranks differently by horizon,
 because what matters is how its RECOVERY TIME compares to your HOLD. An ETF
 that heals in ~24 months is a poor 12-month hold (you'd exit still underwater)
 but a strong 3-5 year hold (it's recovered and compounding again well before
 you sell). So recoverability is judged TWO ways (user asked for both):
   - horizon-matched : recovered within the hold itself (12m hold -> <=12m,
                       2y -> <=24m, 3y -> <=36m, 5y -> <=60m)   [PRIMARY]
   - fixed 24m       : recovered within 24 months, the user's yardstick

 SCORE (per ETF i, horizon H years), two bases (user asked for both):
   growth path that compounds if nothing breaks:   G = (1+g_ann)^H
   expected UNRECOVERED loss over the horizon:      U = P(fall by H) * E[depth|fall]
                                                        * (1 - P(recovered in time))
   expected return (PRIMARY sort) :  ExpRet = G * (1 - U) - 1
   reward-to-risk                 :  R2R    = (G - 1) / max(U, eps)
 A fall that reliably recovers within the window barely dents ExpRet; a broken
 basket that stays underwater is penalized hard. Each name is tagged with its
 crash-growth archetype so a broken ETF can't top the list on growth alone.

 Self-contained 8-year Monte Carlo over the ETF universe (broad + thematic),
 reusing the same engine mechanics as the main run (grind, sub-factor contagion,
 cycle, buyback/solvency, chunk-decorrelated RNG). ESTIMATES, NOT INVESTMENT ADVICE.
============================================================================
"""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "discovery"))
import calibration as C
import engine as E
import tiering as T
import tam_bridge as TB
try:
    import crash_growth as CG
except Exception:
    CG = None

DAYS_SIM = 2016                                   # ~8y: sim runs longer than the windows
HORIZONS = [("12m", 12, 252), ("24m", 24, 504),   # (label, months, drawdown-window days)
            ("36m", 36, 756), ("60m", 60, 1260)]
RECOV_FROM = 756                                  # condition recovery on a trough in first 36m
DEPTH = 0.25
FIXED_RULE_M = 24                                 # the user's fixed recovery yardstick


def _ensure_universe():
    new, _ = TB.build_company_universe(base_companies=C.COMPANIES, verbose=False)
    for nm, spec in new.items():
        C.COMPANIES.setdefault(nm, spec)


def _etf_names(decomp):
    out = []
    for nm in decomp:
        kind = (T.UNIVERSE.get(nm, (None,))[0] or "")
        if str(kind).lower() == "etf" and nm not in getattr(T, "LEVERAGED", []):
            out.append(nm)
    return out


def _recovered_by(rec_arr, mask, months):
    """P(recovered within `months` of the trough | drew down >25%)."""
    if mask.sum() < 30:
        return None
    r = np.nan_to_num(rec_arr[mask], nan=1e9)     # NaN/inf -> never (large)
    return float((r <= months * 21.0).mean())


def run(n_paths=12000, verbose=True):
    _ensure_universe()
    decomp = E.decompose_premium()
    names = _etf_names(decomp)
    g_of = lambda nm: T.UNIVERSE.get(nm, (None, None, 0.0))[2] or 0.0

    old_days = C.SIM["days"]; C.SIM["days"] = DAYS_SIM
    rng = np.random.default_rng(C.SIM["seed"]); CH = C.SIM["chunk"]
    occ = {nm: {h: [] for h, _, _ in HORIZONS} for nm in names}
    recm = {nm: [] for nm in names}; recr = {nm: [] for nm in names}
    done = 0
    while done < n_paths:
        n = min(CH, n_paths - done)
        factor, crisis, grind = E._simulate_factor(rng, n, DAYS_SIM, return_grind=True)
        subfactors = {g: rng.standard_normal((n, DAYS_SIM)) for g in getattr(C, "GROUP_RHO", {})}
        freeze = E._systemic_freeze(factor, DAYS_SIM)        # systemic-freeze recovery contagion
        for nm in names:
            spec = E.company_to_spec(decomp[nm], name=nm)
            _fdep = spec.get("freeze_dep", 1.0)
            price = E._price_path(rng, factor, crisis, spec, n, DAYS_SIM,
                                  tail_mult=spec["tail_mult"], subfactors=subfactors, grind=grind)
            for h, _, hd in HORIZONS:
                mdd, _ = E._drawdown_and_recovery(price, hd, recov_shift=spec["recov_shift"],
                                                  cycle=spec.get("cycle"), path_offset=done,
                                                  freeze=freeze, freeze_dep=_fdep)
                occ[nm][h].append(mdd)
            mdd_r, rec_r = E._drawdown_and_recovery(price, RECOV_FROM, recov_shift=spec["recov_shift"],
                                                    bb=spec.get("bb"), solv=spec.get("solv"),
                                                    dilution=spec.get("dilution"), cycle=spec.get("cycle"),
                                                    path_offset=done, freeze=freeze, freeze_dep=_fdep)
            recm[nm].append(mdd_r); recr[nm].append(rec_r)
        done += n
        if verbose:
            print(f"  etf-horizon 8y sim: {done:,}/{n_paths:,} paths")
    C.SIM["days"] = old_days

    out = {}
    for nm in names:
        rmdd = np.concatenate(recm[nm]); rrec = np.concatenate(recr[nm])
        fell = rmdd <= -DEPTH
        depth = float((-rmdd[fell]).mean()) if fell.any() else 0.0   # E[depth | fell], horizon-invariant
        prec_fixed = _recovered_by(rrec, fell, FIXED_RULE_M)
        g_ann = (1.0 + g_of(nm)) ** (12.0 / 18.0) - 1.0              # annualize the 18m growth
        arch = CG.archetype(nm) if CG else "n/a"
        rows = {}
        for h, mo, _ in HORIZONS:
            pdd = float((np.concatenate(occ[nm][h]) <= -DEPTH).mean())
            prec_hm = _recovered_by(rrec, fell, mo)                  # recovered within the hold itself
            G = (1.0 + g_ann) ** (mo / 12.0)
            def _score(prec):
                if prec is None:
                    prec = 0.0
                U = pdd * depth * (1.0 - prec)
                exp_ret = G * (1.0 - U) - 1.0
                r2r = (G - 1.0) / max(U, 1e-3)
                return U, exp_ret, r2r
            U_hm, ret_hm, r2r_hm = _score(prec_hm)
            U_24, ret_24, r2r_24 = _score(prec_fixed)
            rows[h] = dict(p_fall=pdd, depth=round(depth, 3),
                           p_rec_horizon=prec_hm, p_rec_24m=prec_fixed,
                           exp_return_horizon=round(ret_hm, 3), exp_return_24m=round(ret_24, 3),
                           reward_to_risk=round(r2r_hm, 2), unrec_loss=round(U_hm, 3))
        out[nm] = dict(kind="ETF", growth_ann=round(g_ann, 3), crash_growth=arch, horizons=rows)

    json.dump(out, open(os.path.join(HERE, "etf_horizon_rank.json"), "w"), indent=1)
    _write_md(out)
    if verbose:
        _print(out)
    return out


def _tag(arch):
    return {"secular": "secular", "cyclical": "cyclical/rebound-dep",
            "broken": "⚠ broken — avoid"}.get(arch, arch)


def _ranked(out, h):
    """Non-broken ETFs ranked by expected return; broken theses are HARD-GATED out
    (returned separately) so they can't rank among the buys on raw growth alone."""
    items = list(out.items())
    main = sorted([kv for kv in items if kv[1]["crash_growth"] != "broken"],
                  key=lambda kv: -(kv[1]["horizons"][h]["exp_return_horizon"]))
    flagged = sorted([kv for kv in items if kv[1]["crash_growth"] == "broken"],
                     key=lambda kv: -(kv[1]["horizons"][h]["exp_return_horizon"]))
    return main, flagged


def _print(out):
    print("\nETF RANKING BY HORIZON — expected return (recovery judged vs the hold)")
    print("=" * 92)
    for h, mo, _ in HORIZONS:
        main, flagged = _ranked(out, h)
        print(f"\n{mo//12 if mo%12==0 else mo}{'y' if mo%12==0 else 'm'} HOLD"
              f"   {'ETF':26s}{'gAnn':>6}{'P(fall)':>8}{'rec<=H':>7}{'rec<=24m':>9}{'ExpRet':>8}{'R/R':>6}  type")
        def _line(nm, d):
            r = d["horizons"][h]
            ph = "-" if r["p_rec_horizon"] is None else f"{r['p_rec_horizon']*100:.0f}%"
            p24 = "-" if r["p_rec_24m"] is None else f"{r['p_rec_24m']*100:.0f}%"
            print(f"      {nm[:26]:26s}{d['growth_ann']*100:5.0f}%{r['p_fall']*100:7.0f}%"
                  f"{ph:>7}{p24:>9}{r['exp_return_horizon']*100:7.0f}%{r['reward_to_risk']:6.1f}  {_tag(d['crash_growth'])}")
        for nm, d in main:
            _line(nm, d)
        for nm, d in flagged:
            _line(nm, d)


def _write_md(out):
    L = ["# ETF ranking by holding horizon — expected return + recoverability",
         "\n*Each horizon ranked INDEPENDENTLY. The score is a probability-weighted expected "
         "return: the growth path an ETF compounds if intact, discounted by its EXPECTED "
         "UNRECOVERED LOSS = P(>25% fall by the horizon) × expected depth × P(not recovered "
         "in time). Recovery is judged two ways: **vs the hold itself** (primary — a 2y hold "
         "needs recovery ≤24m) and **vs a fixed 24-month rule** (shown alongside). A fall that "
         "reliably heals within the window barely dents the score; a broken basket that stays "
         "underwater is penalized hard. Research model, not investment advice.*"]
    for h, mo, _ in HORIZONS:
        yr = f"{mo//12}-year" if mo % 12 == 0 else f"{mo}-month"
        main, flagged = _ranked(out, h)
        L.append(f"\n## {yr} hold — ranked by expected return")
        hdr = ("\n| # | ETF | type | growth p.a. | P(>25% fall by " + h + ") | "
               "P(recover ≤" + h + ") | P(recover ≤24m) | exp return (vs-hold) | "
               "exp return (24m-rule) | reward/risk |")
        sep = "|--:|---|---|--:|--:|--:|--:|--:|--:|--:|"
        def _mrow(i, nm, d):
            r = d["horizons"][h]
            ph = "—" if r["p_rec_horizon"] is None else f"{r['p_rec_horizon']*100:.0f}%"
            p24 = "—" if r["p_rec_24m"] is None else f"{r['p_rec_24m']*100:.0f}%"
            return (f"| {i} | {nm} | {_tag(d['crash_growth'])} | {d['growth_ann']*100:.0f}% | "
                    f"{r['p_fall']*100:.0f}% | {ph} | {p24} | {r['exp_return_horizon']*100:+.0f}% | "
                    f"{r['exp_return_24m']*100:+.0f}% | {r['reward_to_risk']:.1f} |")
        L.append(hdr); L.append(sep)
        for i, (nm, d) in enumerate(main, 1):
            L.append(_mrow(i, nm, d))
        if flagged:
            L.append(f"\n*Flagged — broken thesis, excluded from the ranking (shown for reference; "
                     f"raw growth is not underwritten when the theme is impaired):*")
            L.append(hdr); L.append(sep)
            for nm, d in flagged:
                L.append(_mrow("⚠", nm, d))
    L.append("\n## How to read it")
    L.append("- **Same ETF, different horizon**: a high-growth basket that heals in ~24 months "
             "ranks low at 12m (you'd exit underwater) and high at 3–5y (recovered, compounding "
             "again). Compare its row across the four tables.")
    L.append("- **vs-hold vs 24m-rule columns**: where they diverge, recovery takes longer than "
             "the shorter holds allow — the name needs patience to realize its growth.")
    L.append("- **type** gates the growth: a cyclical basket is rebound-dependent (needs the demand "
             "cycle to turn); a broken one is flagged regardless of how high its raw growth looks.")
    open(os.path.join(HERE, "etf_horizon_rank.md"), "w").write("\n".join(L))


if __name__ == "__main__":
    run()
