"""
============================================================================
 ADD_LEVERAGED  --  systemic_model
============================================================================
 Leveraged 3x ETFs cannot be priced through the TAM/premium path (they have no
 fundamentals — they're a daily-reset bet with volatility decay). This script
 simulates each one through the engine's LEVERAGED price path, measures the
 same recovery_cond fields the companies get (p_dd25, recovery curve, the
 permanent tail), and injects them into results.json so they appear in the
 tiering / dashboards / scaling alongside everything else.

 Run AFTER run.main():  python3 add_leveraged.py
 RESEARCH MODEL, NOT INVESTMENT ADVICE.
============================================================================
"""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "discovery"))
import calibration as C
import engine as E
import tam_bridge as TB

RESULTS = os.path.join(HERE, "results.json")
DEPTH = 0.25


def _recovery_cond(spec, n_paths=30000):
    rng = np.random.default_rng(C.SIM["seed"])
    CH, DAYS = C.SIM["chunk"], C.SIM["days"]
    mdds, recs = [], []
    done = 0
    while done < n_paths:
        n = min(CH, n_paths - done)
        factor, crisis, grind = E._simulate_factor(rng, n, DAYS, return_grind=True)
        freeze = E._systemic_freeze(factor, DAYS)
        price = E._price_path(rng, factor, crisis, spec, n, DAYS, tail_mult=1.0, grind=grind)
        mdd, rec = E._drawdown_and_recovery(price, 378, path_offset=done, freeze=freeze)   # 18m window
        mdds.append(mdd); recs.append(rec)
        done += n
    mdd = np.concatenate(mdds); rec = np.concatenate(recs)
    rc = E.recovery_curve(mdd, rec, DEPTH)
    mask = mdd <= -DEPTH
    md_days = C.MANDATE_YEARS * 252
    p_rec = float(np.mean(np.nan_to_num(rec[mask], nan=1e9) <= md_days)) if mask.sum() > 30 else float("nan")
    rec_filled = np.nan_to_num(rec, nan=1e9)
    p_deep_perm = float((mask & (rec_filled > C.SIM["days"])).mean())
    return dict(p_dd25=float(mask.mean()), p_recover=p_rec,
                recovery_quality=0.0, fragility=1.0,
                p_never=rc["p_never"], p_deep_permanent=p_deep_perm,
                recovery_curve=rc["curve"])


def run(n_paths=None):
    with open(RESULTS) as f:
        res = json.load(f)
    rc_all = res["companies"]["recovery_cond"]
    # case-insensitive exposure lookup (normalization boundary -- the display
    # names are Title Case, calibration's exposure keys may differ in case;
    # a silent miss here previously dropped SOXL/TECL from the outputs)
    exp_ci = {k.lower(): v for k, v in C.EXPOSURES.items()}
    for name, info in TB.LEVERAGED_ETFS.items():
        ex = C.EXPOSURES.get(info["exposure"]) or exp_ci.get(info["exposure"].lower())
        if not ex:
            print(f"  WARNING: no exposure found for {name} ({info['exposure']}) -- SKIPPED")
            continue
        spec = dict(beta=ex["beta"], idio=ex["idio"], mu=ex.get("alpha", 0.0),
                    L=ex["L"], leveraged=ex["leveraged"], tail_mult=1.0)
        cond = _recovery_cond(spec, n_paths=n_paths or 30000)
        rc_all[name] = cond
        print(f"  injected {name:18s} P(>25%)={cond['p_dd25']*100:3.0f}%  "
              f">3y tail={cond['p_deep_permanent']*100:3.0f}%")
    with open(RESULTS, "w") as f:
        json.dump(res, f, indent=1)
    print("Saved results.json with leveraged ETFs.")


if __name__ == "__main__":
    run()
