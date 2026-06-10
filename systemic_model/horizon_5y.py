"""
============================================================================
 HORIZON_5Y  --  systemic_model
============================================================================
 THE LONGER-HORIZON DRAWDOWN/RECOVERY VIEW (extended Monte Carlo).

 Runs the SAME engine out to ~5 years (1260 trading days) to answer the user's
 question directly:
   - over a longer hold, how much does the chance of a deep drawdown RISE?
   - conditional on falling >25%, what is the chance of recovering by 24 months,
     and what is the truly permanent ("never") tail at 5 years?

 It does NOT mutate the package's short-horizon config (run.py / run_agent.py
 keep their 6/12/18-month tables). It reuses engine internals at a longer DAYS
 and reports three windows: 18m / 36m / 60m.

 IMPORTANT CALIBRATION CAVEAT (read this):
   This engine is calibrated for an 18-month mandate. Its daily regime-transition
   matrix, drifts, and the catalyst premium were tuned so the EMERGENT 18-month
   behaviour matches the dashboard. Running the same matrix for 5 years simply
   lets crises recur at the implied long-run frequency -- which is a reasonable
   mechanical extrapolation but NOT a recalibrated 5-year forecast. Treat the
   60-month numbers as "what this 18m-tuned process implies if extended,"
   read as ranges and orderings, not point forecasts.

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
import tam_bridge as TB

DAYS_SIM = 2016                     # ~8 years -- sim runs LONGER than the windows
                                    # so recovery from a late trough is not censored
WINDOWS = [("18m", 378), ("36m", 756), ("60m", 1260)]   # P(DD>25%) occurrence windows
RECOV_WINDOW = 756                  # condition recovery on a trough in the first 36m,
                                    # then measure recovery across the full 8y sim
SCHEDULE = [6, 12, 18, 24, 30, 36, 48, 60]
DEPTH = 0.25                        # condition recovery on a >25% drawdown


def _ensure_universe():
    new, _ = TB.build_company_universe(base_companies=C.COMPANIES, verbose=False)
    for nm, spec in new.items():
        C.COMPANIES.setdefault(nm, spec)


def run(names=None, n_paths=30000):
    _ensure_universe()
    # run the engine's own decomposition -> path specs
    decomp = E.decompose_premium()
    if names is None:
        names = list(decomp.keys())

    # extend the sim horizon so recovery_curve's p_never uses the full 8y window
    old_days = C.SIM["days"]
    C.SIM["days"] = DAYS_SIM
    rng = np.random.default_rng(C.SIM["seed"])
    CH = C.SIM["chunk"]

    # storage: per name -> occurrence mdd for each window, plus recovery-window mdd/rec
    occ = {nm: {w: [] for w, _ in WINDOWS} for nm in names}
    recov = {nm: {"mdd": [], "rec": []} for nm in names}
    done = 0
    while done < n_paths:
        n = min(CH, n_paths - done)
        # request grind + sub-factor contagion so the 5y horizon matches the baseline MC
        # mechanics (multiple-compression bleed + crisis-spiking correlation). (Gemini bug 4.)
        factor, crisis, grind = E._simulate_factor(rng, n, DAYS_SIM, return_grind=True)
        subfactors = {g: rng.standard_normal((n, DAYS_SIM)) for g in getattr(C, "GROUP_RHO", {})}
        freeze = E._systemic_freeze(factor, DAYS_SIM)   # systemic-freeze recovery contagion
        for nm in names:
            spec = E.company_to_spec(decomp[nm], name=nm)
            price = E._price_path(rng, factor, crisis, spec, n, DAYS_SIM,
                                  tail_mult=spec["tail_mult"], subfactors=subfactors, grind=grind)
            _fdep = spec.get("freeze_dep", 1.0)
            for w, hd in WINDOWS:
                mdd, _ = E._drawdown_and_recovery(price, hd, recov_shift=spec["recov_shift"],
                                                  cycle=spec.get("cycle"), path_offset=done,
                                                  freeze=freeze, freeze_dep=_fdep)
                occ[nm][w].append(mdd)
            # recovery: trough within the first 36m, recovery searched across full 8y
            mdd_r, rec_r = E._drawdown_and_recovery(price, RECOV_WINDOW,
                                                    recov_shift=spec["recov_shift"],
                                                    bb=spec.get("bb"), solv=spec.get("solv"),
                                                    dilution=spec.get("dilution"), cycle=spec.get("cycle"),
                                                    path_offset=done, freeze=freeze, freeze_dep=_fdep)
            recov[nm]["mdd"].append(mdd_r)
            recov[nm]["rec"].append(rec_r)
        done += n
        print(f"  8y sim: {done:,}/{n_paths:,} paths")

    out = {}
    for nm in names:
        p_dd = {w: float((np.concatenate(occ[nm][w]) <= -DEPTH).mean()) for w, _ in WINDOWS}
        mdd = np.concatenate(recov[nm]["mdd"])
        rec = np.concatenate(recov[nm]["rec"])
        rc = E.recovery_curve(mdd, rec, DEPTH, horizons_months=SCHEDULE, suggested_months=24)
        curve = {pt["months"]: pt["p_recovered"] for pt in rc["curve"]}
        out[nm] = dict(
            p_dd25=p_dd,
            curve=curve,                      # full P(recovered) by each month in SCHEDULE
            rec_by_24m=curve.get(24), rec_by_36m=curve.get(36), rec_by_60m=curve.get(60),
            p_never=rc["p_never"],            # not recovered within the 8y sim
            recovery_quality=decomp[nm]["recovery_quality"],
        )
    C.SIM["days"] = old_days
    return out


def report(out):
    print("#" * 84)
    print("#  EXTENDED HORIZON  --  P(deep drawdown) rises with time; recovery is the test")
    print("#  windows: 18m / 36m / 60m   |   recovery conditional on a >25% fall")
    print("#  18m-calibrated process EXTENDED to 5y -- read as ranges, not forecasts")
    print("#" * 84)
    order = sorted(out, key=lambda n: out[n]["p_never"])
    print(f"\n{'Name':24s} | {'DD>25% by':^20s} | {'recover (trough<36m)':^26s} | {'perm':>5s}")
    print(f"{'':24s} | {'18m':>6s}{'36m':>7s}{'60m':>7s} | "
          f"{'by24m':>7s}{'by36m':>8s}{'by60m':>8s} | {'8y':>5s}")
    print("-" * 84)
    for nm in order:
        o = out[nm]
        d = o["p_dd25"]
        print(f"{nm:24s} | {d['18m']*100:5.0f}%{d['36m']*100:6.0f}%{d['60m']*100:6.0f}% | "
              f"{o['rec_by_24m']*100:6.0f}%{o['rec_by_36m']*100:7.0f}%{o['rec_by_60m']*100:7.0f}% | "
              f"{o['p_never']*100:4.0f}%")
    print("\n  Read: P(DD>25%) climbs left-to-right (more time, more chances to fall).")
    print("  The thesis holds when 'recover by 24m' stays high and 'perm 5y' stays low —")
    print("  that is the high-runway names. Cyclical/floating names show the reverse.")
    return order


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", type=int, default=30000)
    args = ap.parse_args()
    out = run(n_paths=args.paths)
    report(out)
    with open(os.path.join(HERE, "horizon_5y.json"), "w") as f:
        json.dump(out, f, indent=1)
    print("\nSaved horizon_5y.json")
