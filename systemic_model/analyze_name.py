"""
============================================================================
 ANALYZE_NAME  --  systemic_model
============================================================================
 On-demand: run ANY stock or ETF not already in the universe through the whole
 model and place it next to the existing names.

 Give it the bottom-up inputs for the new name (the "discovery -> TAM" output)
 and it runs the same regime-switching, macro-stress-aware Monte Carlo, then
 reports the new name's growth tier, recovery profile (recover in 1/2/3y, and
 the >3y long tail) and where it RANKS against the current universe.

 Usage:
   python3 analyze_name.py --json newname.json [--paths 30000]
   python3 analyze_name.py --name "Nebius" --kind stock --theme "AI cloud" \\
       --growth 0.65 --rev_bn 1.5 --tam_bn 200 --tam_cagr 0.40 --fwd_pe 90 \\
       --beta 2.1 --quality 0.6 --earn_quality 0.4 --dominance 0.4 --capex_elastic 0.4

 The new name is NOT written into the universe — this is a non-destructive
 what-if. To make it permanent, add it to discovery/tam_bridge.py and tiering.py.
 For an ETF, supply the holdings-aggregated inputs (see tam_bridge.etf_spec).
 RESEARCH MODEL, NOT INVESTMENT ADVICE.
============================================================================
"""
import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "discovery"))

import calibration as C
import engine as E
import tiering as T
import build_dashboard as B

FIELDS = ("rev_bn", "tam_bn", "tam_cagr", "fwd_pe", "beta",
          "quality", "earn_quality", "dominance", "capex_elastic")


def simulate_one(spec_inputs, n_paths=30000):
    """Run the Monte Carlo for one company-spec dict; return p_dd25 + recovery
    curve (uses the live macro-stress-aware engine)."""
    dec = E.decompose_premium({"_X_": dict(spec_inputs)})["_X_"]
    # pass the REAL name so the spec carries its group, ETF idio, crash-growth/cycle, buyback
    # and solvency channels -- without it company_to_spec falls back to defensive/0.11 and
    # skips all of them (Gemini bug 5).
    nm = spec_inputs.get("name")
    spec = E.company_to_spec(dec, name=nm)
    rng = np.random.default_rng(C.SIM["seed"])
    N, CH, DAYS = n_paths, C.SIM["chunk"], C.SIM["days"]
    mdds, recs = [], []
    done = 0
    while done < N:
        n = min(CH, N - done)
        # grind + sub-factor contagion, matching the baseline MC (Gemini bug 4)
        factor, crisis, grind = E._simulate_factor(rng, n, DAYS, return_grind=True)
        subfactors = {g: rng.standard_normal((n, DAYS)) for g in getattr(C, "GROUP_RHO", {})}
        freeze = E._systemic_freeze(factor, DAYS)        # systemic-freeze recovery contagion
        price = E._price_path(rng, factor, crisis, spec, n, DAYS, tail_mult=spec["tail_mult"],
                              subfactors=subfactors, grind=grind)
        mdd, rec = E._drawdown_and_recovery(price, 378, recov_shift=spec["recov_shift"],
                                            bb=spec.get("bb"), solv=spec.get("solv"),
                                            dilution=spec.get("dilution"), cycle=spec.get("cycle"),
                                            path_offset=done, freeze=freeze,
                                            freeze_dep=spec.get("freeze_dep", 1.0))
        mdds.append(mdd); recs.append(rec)
        done += n
    mdd = np.concatenate(mdds); rec = np.concatenate(recs)
    rcurve = E.recovery_curve(mdd, rec, 0.25)
    pdd = float((mdd <= -0.25).mean())
    cv = {pt["months"]: pt["p_recovered"] for pt in rcurve["curve"]}
    return dec, pdd, cv


def _tier(g):
    return "High" if g > 0.40 else ("Moderate" if g >= 0.15 else "Safe")


def analyze(cfg, n_paths=30000):
    name = cfg["name"]
    g = cfg["growth"]
    spec_inputs = {k: cfg[k] for k in FIELDS}
    spec_inputs["name"] = name        # thread the real name -> archetype/group/solvency/cycle
    dec, pdd, cv = simulate_one(spec_inputs, n_paths)
    p12, p24, p36 = cv.get(12, 0), cv.get(24, 0), cv.get(36, 0)
    tail = pdd * max(0.0, 1 - p36)

    print("#" * 72)
    print(f"#  ANALYSIS:  {name}   ({cfg.get('kind','stock')}, {cfg.get('theme','?')})")
    print(f"#  macro-stress index {C.SYSTEMIC_STRESS['score']*100:.0f}/100 "
          f"(x{C.STRESS_CRISIS_MULT:.2f}) applied.  RESEARCH MODEL, NOT ADVICE.")
    print("#" * 72)
    pen = dec["pen"]
    print(f"\n  Inputs: rev ${spec_inputs['rev_bn']:.1f}B / TAM ${spec_inputs['tam_bn']:.0f}B "
          f"-> penetration {pen*100:.1f}% | fwdPE {spec_inputs['fwd_pe']:.0f} | beta {spec_inputs['beta']:.2f}")
    print(f"  Decomposition: fragility {dec['fragility']*100:.0f}% | "
          f"recovery-quality {dec['recovery_quality']*100:.0f}% | "
          f"unsupported premium {dec['unsupported_frac']*100:.0f}%")
    print(f"\n  Expected 18m growth: {g*100:.0f}%   ->   TIER: {_tier(g)}")
    print(f"  P(>25% fall in 18m): {pdd*100:.0f}%")
    print(f"  If it falls >25%, recovers within  1y: {p12*100:.0f}%   2y: {p24*100:.0f}%   3y: {p36*100:.0f}%")
    print(f"  >3y long/uncertain tail (unconditional): {tail*100:.0f}%   (lower = safer)")

    # ---- compare to the existing universe (from results.json) ----
    res = B._load(B.RESULTS)
    if res:
        uni = []
        for nm, (k, th, gg) in T.UNIVERSE.items():
            c = res["companies"]["recovery_cond"].get(nm)
            if not c:
                continue
            uni.append((nm, gg, B._buckets(res, nm)["gt3"]))
        n = len(uni)
        safer_tail = sum(1 for _, _, t in uni if t > tail)
        faster_grow = sum(1 for _, gg, _ in uni if gg < g)
        print("\n  VS THE CURRENT UNIVERSE ({} names):".format(n))
        print(f"    growth higher than {faster_grow}/{n} names "
              f"({100*faster_grow//n}th percentile)")
        print(f"    long tail SAFER than {safer_tail}/{n} names "
              f"({100*safer_tail//n}th percentile)")
        # nearest peers by growth
        peers = sorted(uni, key=lambda r: abs(r[1] - g))[:4]
        print("    nearest peers by growth:")
        for nm, gg, t in peers:
            flag = "safer" if t < tail else "riskier"
            print(f"      {nm:24s} growth {gg*100:3.0f}%  >3y tail {t*100:3.0f}%  ({flag} than {name})")
    print()
    return dict(name=name, growth=g, tier=_tier(g), p_dd25=pdd,
                recover_1y=p12, recover_2y=p24, recover_3y=p36, tail=tail,
                fragility=dec["fragility"], recovery_quality=dec["recovery_quality"])


def _cfg_from_args(a):
    if a.json:
        with open(a.json) as f:
            return json.load(f)
    cfg = dict(name=a.name, kind=a.kind, theme=a.theme, growth=a.growth)
    for k in FIELDS:
        cfg[k] = getattr(a, k)
    return cfg


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=None, help="JSON file with the name's inputs.")
    ap.add_argument("--name"); ap.add_argument("--kind", default="stock")
    ap.add_argument("--theme", default="?"); ap.add_argument("--growth", type=float)
    for k in FIELDS:
        ap.add_argument(f"--{k}", type=float)
    ap.add_argument("--paths", type=int, default=30000)
    a = ap.parse_args()
    cfg = _cfg_from_args(a)
    missing = [k for k in ("name", "growth", *FIELDS) if cfg.get(k) is None]
    if missing:
        ap.error("missing inputs: " + ", ".join(missing))
    analyze(cfg, n_paths=a.paths)
