"""
============================================================================
 RUN_DOMINANCE_SWEEP  --  systemic_model
============================================================================
 The complete moat-sensitivity matrix. Re-runs the FULL company Monte Carlo
 for every name across a range of dominance (D) assignments centered on each
 name's base estimate, and reports how far the two output probabilities move:
   - P(drawdown > 30% within 18m)   -- expected to barely move (beta-driven)
   - P(recover < mandate | drawdown >25%) -- expected to move materially (TAM-driven)

 This is the heavier "error-bar on the probabilities" check adopted from the
 Gemini/TDVM review, complementing the fast ranking sweep in run.py.

 Run:  python3 run_dominance_sweep.py
============================================================================
"""
import json
import numpy as np
import calibration as C
import engine as E

# Path count for the sweep. Lower than the headline run because the SWING
# between D settings is what matters here, not the third decimal of any one
# probability. Raise toward 150k for a final archival run.
SWEEP_PATHS = 80_000

# Offsets applied to each name's base dominance, clipped to [0,1]. Centered on
# the base estimate so the sweep asks "what if my moat judgment is off by this
# much" rather than imposing an absolute scale.
D_OFFSETS = (-0.20, -0.10, 0.0, +0.10, +0.20)


def main():
    print("#" * 74)
    print(f"#  COMPLETE DOMINANCE SWEEP   |   calibrated as of {C.AS_OF_DATE}")
    print(f"#  {SWEEP_PATHS:,} paths/run  |  18-month horizon  |  all {len(C.COMPANIES)} names")
    print(f"#  RESEARCH MODEL, NOT INVESTMENT ADVICE.")
    print("#" * 74)
    print()

    results = E.dominance_sweep_all(d_offsets=D_OFFSETS, n_paths=SWEEP_PATHS, verbose=True)

    # ---- readable matrix ----
    print("\n" + "=" * 74)
    print("COMPLETE DOMINANCE-SENSITIVITY MATRIX  (18-month horizon)")
    print("  For each name: how the two output probabilities move as the moat")
    print("  score (D) swings around its base estimate.")
    print("=" * 74)
    print(f"{'Name':9s} {'D':>5s} {'RecovQ':>7s} {'P(DD>30%)':>10s} {('P(rec<'+str(int(C.MANDATE_MONTHS))+'m|DD>25%)'):>17s}")
    print("-" * 74)
    for nm, info in results.items():
        base = info["base_dominance"]
        for r in info["rows"]:
            marker = "  <- base" if abs(r["dominance"] - base) < 1e-9 else ""
            print(f"{nm:9s} {r['dominance']:5.2f} {r['recovery_quality']*100:6.0f}% "
                  f"{r['p_dd30']*100:9.0f}% {r['p_recover']*100:16.0f}%{marker}")
        dd_lo, dd_hi = info["dd30_swing"]
        rc_lo, rc_hi = info["recover_swing"]
        print(f"{'':9s} {'swing:':>5s} {'':7s} {(dd_hi-dd_lo)*100:8.0f}pp "
              f"{(rc_hi-rc_lo)*100:15.0f}pp")
        print("-" * 74)

    # ---- the takeaway: rank names by how SENSITIVE recovery is to the moat ----
    print("\n" + "=" * 74)
    print("WHERE THE MOAT IS THE SINGLE POINT OF FAILURE")
    print("  Names ranked by recovery-probability swing across the D sweep.")
    print("  A large swing = the conclusion depends heavily on a subjective")
    print("  moat judgment; a small swing = robust regardless of the moat call.")
    print("=" * 74)
    by_sens = sorted(results.items(),
                     key=lambda kv: -(kv[1]["recover_swing"][1] - kv[1]["recover_swing"][0]))
    print(f"{'Name':9s} {'recovery swing (pp)':>20s}  {'reading':s}")
    for nm, info in by_sens:
        rc_lo, rc_hi = info["recover_swing"]
        swing = (rc_hi - rc_lo) * 100
        if swing >= 8:
            read = "MOAT-CRITICAL: recovery hinges on the share judgment"
        elif swing >= 4:
            read = "moat-sensitive: moderate dependence on the call"
        else:
            read = "moat-robust: conclusion holds across assignments"
        print(f"{nm:9s} {swing:18.0f}pp  {read}")
    print()

    # ---- save ----
    def clean(o):
        if isinstance(o, dict):  return {k: clean(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)): return [clean(x) for x in o]
        if isinstance(o, (np.floating,)): return float(o)
        if isinstance(o, (np.integer,)):  return int(o)
        return o
    with open("dominance_sweep.json", "w") as f:
        json.dump(dict(as_of=C.AS_OF_DATE, sweep_paths=SWEEP_PATHS,
                       d_offsets=list(D_OFFSETS), results=clean(results)), f, indent=1)
    print("Saved dominance_sweep.json")
    print("\nDONE.")


if __name__ == "__main__":
    main()
