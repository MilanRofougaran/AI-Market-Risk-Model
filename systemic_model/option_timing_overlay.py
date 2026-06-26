"""
option_timing_overlay.py -- expose the TIMING dependency of an option structure.

The earnings-collapse / profit-sensitivity layers mainly sharpen recovery TIMING and trough
DEPTH -- and options live or die on timing (theta). This overlay, for each option candidate,
flags whether the EPS trough / cyclical recovery is likely to clear before EXPIRY, and (if you
pass a base P(profit) from premium_check) reports a timing-stressed P(profit).

IT DOES NOT VALIDATE TIMING. Recovery timing is the model's LEAST-VALIDATED axis -- these are
the model's own estimates derived from cyclicality, NOT historically backtested. Every output
is stamped as such. The honest fix (recovery_timing_backtest with real history) is the A+ data
project, not this overlay. RESEARCH MODEL -- NOT INVESTMENT ADVICE.
"""
import sys
import calibration as C
import earnings_waterfall as W

TIMING_NOTE = "MODEL ESTIMATE; recovery timing is NOT historically validated (see #2/#3 data project)"


def _est_recovery_months(name):
    """Crude MODEL ESTIMATE of months-to-recovery from the waterfall's recovery_delay (0..1).
    NOT validated; deep cyclicals (memory) map slow, seculars fast -- consistent with the model's
    'memory pain is the wait' read, but it is an estimate, not a backtested number."""
    w = W.waterfall(name)
    if w is None:
        return None
    rd = w["recovery_delay_estimate"]            # 0..~0.95
    return round(6 + rd * 36, 1)                  # 6mo (secular) .. ~40mo (deep cyclical)


def timing_overlay(name, tenor_months, base_p_profit=None, archetype=None):
    em = _est_recovery_months(name)
    if em is None:
        return {"name": name, "error": "no operating-leverage inputs for timing estimate"}
    trough_m = round(em * 0.4, 1)                 # EPS trough roughly 40% into the recovery arc
    trough_before = trough_m <= tenor_months
    recovery_before = em <= tenor_months
    w = W.waterfall(name); cyc = w["eps_trough_depth"]

    if not recovery_before and cyc >= 0.6:
        status = "REJECT (deep cyclical, recovery est. beyond expiry)"
    elif not recovery_before:
        status = "CAUTION (recovery est. beyond expiry)"
    elif not trough_before:
        status = "CAUTION (EPS trough may overlap expiry)"
    else:
        status = "OK (trough + recovery est. within expiry)"

    out = {"name": name, "tenor_months": tenor_months,
           "eps_trough_depth": cyc,
           "est_recovery_months": em, "est_trough_months": trough_m,
           "eps_trough_before_expiry": trough_before,
           "recovery_before_expiry": recovery_before,
           "timing_status": status, "_timing_note": TIMING_NOTE}

    if base_p_profit is not None:
        # timing-overlap haircut on P(profit): a documented heuristic, NOT a validated adjustment.
        if not recovery_before:
            factor = 0.55 if cyc >= 0.6 else 0.75
        elif not trough_before:
            factor = 0.85
        else:
            factor = 1.0
        out["p_profit_base"] = round(base_p_profit, 3)
        out["p_profit_timing_stressed"] = round(base_p_profit * factor, 3)
        out["_p_profit_note"] = "timing haircut is a heuristic, not a validated calibration"
    return out


if __name__ == "__main__":
    # illustrate the rule it formalizes: short-dated memory = REJECT; long deep-ITM secular = OK
    cases = [("Micron", 6), ("Micron", 12), ("Micron", 36), ("DRAM", 24),
             ("NVIDIA", 12), ("NVIDIA", 36), ("CoreWeave", 24)]
    print("OPTION TIMING OVERLAY (model timing estimates -- NOT historically validated)\n")
    print(f"{'Name':10s}{'tenor':>6s}{'cyc':>6s}{'est_rec_mo':>11s}{'rec<exp':>8s}  status")
    for nm, t in cases:
        r = timing_overlay(nm, t, base_p_profit=0.50)
        if "error" in r:
            print(f"{nm:10s}{t:>6}  {r['error']}"); continue
        print(f"{nm:10s}{t:>6}{r['eps_trough_depth']:>6.2f}{r['est_recovery_months']:>11}"
              f"{str(r['recovery_before_expiry']):>8}  {r['timing_status']}")
    print(f"\n{TIMING_NOTE}")
    print("Formalizes: no short-dated memory calls; deep-ITM/long for memory; the overlay shows WHY.")
