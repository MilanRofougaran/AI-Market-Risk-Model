# Options layer — file guide

Drop all files into systemic_model/ (alongside engine.py). Run order:

  1. python3 options_lens.py --paths 30000     # single-leg fair values (slow; rerun after any calibration change)
  2. python3 spread_lens.py                     # all multi-leg tables (instant)
  3. python3 premium_check.py "NVIDIA" 24m 0.75 32                          # single call
     python3 premium_check.py "Micron" 24m 0.90/1.20 12                     # bull call spread
     python3 premium_check.py "Micron" 24m 0.80/1.00/1.20 3                 # butterfly 1-2-1 (negative = credit)
     python3 premium_check.py "NVIDIA" 36m tail:0.75/1.50/2.25 36           # tail-kicker +1/-1/+1 (keeps far tail)
     python3 premium_check.py "NVIDIA" 24m custom:+1@0.75,-2@1.00,+1@1.20 8 # any signed legs
     (prefix aliases accepted: spread: fly: tail: custom:)
     Off-grid tenors interpolate: "NVIDIA" 30m 0.75 45.3   # Dec-2028 LEAPS between 24m/36m columns

Files:
  options_lens.py / .json / .md   simulator: 16 names x 5 tenors x 15 strikes (0.50-2.50), gates on every row
  spread_lens.py / .json / .md    post-processor: verticals, far-OTM overwrites, symmetric + broken-wing flies, tail-kickers (+1/-1/+1)
  premium_check.py                gate checker: single / spread / fly / tail-kicker / custom signed legs; net-naked upside shorts auto-REJECTED; broken-wing flies with negative upper payoff REJECTED on seculars; off-grid strikes linearly interpolated in-range
  _dip_experiment.py / dip_experiment.json   dip experiment v2 — PV-consistent (Gemini fix): dip-buying at unconditional fair is negative-EV at ALL tenors; a dip is information, not a discount

Operating rule: archetype -> matrix gate -> tenor -> premium vs model fair -> macro gate.
Limits: physical-measure fair values (thesis-conditional, not risk-neutral); no IV/vega/IV-crush;
short-dated cyclical raw-path numbers are optimistic (the demand trough lives in the recovery matrix);
no calendars/diagonals (needs an IV surface); naked upper short legs are banned structures.
8k-path sandbox values carry ~±0.5-1pt noise — rerun at 30k+ locally before dollar-precision decisions.
RESEARCH MODEL — NOT INVESTMENT ADVICE.
