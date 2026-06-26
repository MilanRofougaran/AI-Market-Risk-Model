"""Dip-buying experiment: after a >25% fall, does a call at the dip pay?
v3 (2026-06-14, credit: GPT full-ZIP audit): ATM premiums are now READ LIVE from
options_lens.json (the K=1.00 fair value) instead of hard-coded -- the old static
block went stale after the earnings-collapse/profit-sensitivity layers raised fair
values, which flipped the experiment's sign. Run options_lens.py FIRST; this refuses
to run on absent/stale data rather than silently using old premiums.
v2 (Gemini 2026-06-10): payoffs discounted at the same 10y rate the premiums carry.

HONEST TAKEAWAY (printed below): at CURRENT model-fair ATM premiums, buying calls after
a >25% dip is NOT positive-EV at any tenor for these names. The model's value here is
avoiding WRONG-TENOR trades, not proving dip-buying calls pay. RESEARCH MODEL -- NOT ADVICE."""
import numpy as np, zlib, json, sys, os
import calibration as C, engine as E
RF = (C.MACRO.get("ust_10y") or 4.0) / 100.0
HERE = os.path.dirname(os.path.abspath(__file__))

PATHS = 8000; DIPWIN = 126; DAYS = 126 + 756
EXP = [("6m", 126), ("12m", 252), ("18m", 378), ("24m", 504), ("36m", 756)]
NAMES = ["Micron", "NVIDIA", "AMD"]


def load_atm_premiums():
    """ATM (K=1.00) fair value per name/tenor from the LIVE options_lens.json (as % of spot)."""
    path = os.path.join(HERE, "options_lens.json")
    if not os.path.exists(path):
        sys.exit("ERROR: options_lens.json not found. Run `python3 options_lens.py` FIRST -- "
                 "this experiment reads CURRENT ATM premiums from it and will not use stale hard-coded values.")
    o = json.load(open(path))["names"]
    prem = {}
    for nm in NAMES:
        if nm not in o:
            sys.exit(f"ERROR: {nm} missing from options_lens.json; re-run options_lens.py.")
        prem[nm] = {}
        for lab, _ in EXP:
            try:
                prem[nm][lab] = o[nm][lab]["strikes"]["1.00"]["fair_value_pct_of_spot"] / 100.0
            except KeyError:
                sys.exit(f"ERROR: ATM (K=1.00) {lab} fair value missing for {nm} in options_lens.json.")
    return prem, o.get("_paths", "unknown")


PREM, lens_paths = load_atm_premiums()
print(f"ATM premiums read LIVE from options_lens.json (not hard-coded). e.g. NVIDIA 36m = {PREM['NVIDIA']['36m']:.1%}",
      file=sys.stderr)

decomp = E.decompose_premium()
rng = np.random.default_rng(C.SIM["seed"])
idio = {nm: np.random.default_rng((C.SIM["seed"] ^ (zlib.crc32(nm.encode()) & 0xFFFFFFFF)) & 0xFFFFFFFF) for nm in decomp}
res = {nm: {l: [] for l, _ in EXP} for nm in NAMES}; ndip = {nm: 0 for nm in NAMES}; ntot = 0
done = 0; CH = 4000
while done < PATHS:
    n = min(CH, PATHS - done)
    factor, crisis, grind = E._simulate_factor(rng, n, DAYS, return_grind=True)
    subf = {g: rng.standard_normal((n, DAYS)) for g in getattr(C, "GROUP_RHO", {})}
    for nm in decomp:
        spec = E.company_to_spec(decomp[nm], name=nm)
        price = E._price_path(rng, factor, crisis, spec, n, DAYS, tail_mult=spec["tail_mult"],
                              subfactors=subf, grind=grind, idio_rng=idio[nm])
        if nm not in NAMES: continue
        peak = np.maximum.accumulate(price[:, :DIPWIN], axis=1)
        dd = price[:, :DIPWIN] / peak - 1.0
        hit = dd <= -0.25
        has = hit.any(axis=1); t0 = np.argmax(hit, axis=1)
        idx = np.where(has)[0]; ndip[nm] += len(idx)
        entry = price[idx, t0[idx]]
        for lab, d in EXP:
            ratio = price[idx, t0[idx] + d] / entry
            res[nm][lab].append(ratio)
    ntot += n; done += n
    print(f"  {done}/{PATHS}", file=sys.stderr)

out = {"paths": PATHS, "dipwin_days": DIPWIN, "premium_source": "options_lens.json (live ATM K=1.00)", "names": {}}
all_negative = True
for nm in NAMES:
    out["names"][nm] = {"p_dip_6m": round(ndip[nm] / PATHS, 3), "tenors": {}}
    for lab, d in EXP:
        r = np.concatenate(res[nm][lab]); prem = PREM[nm][lab]
        disc = float(np.exp(-RF * (d / 252.0)))
        pay_pv = np.maximum(r - 1, 0) * disc
        exp_net = float(np.mean(pay_pv - prem))
        if exp_net > 0: all_negative = False
        out["names"][nm]["tenors"][lab] = {
            "p_itm": round(float(np.mean(r > 1.0)), 3),
            "atm_premium_pct": round(prem * 100, 1),
            "p_profit_net": round(float(np.mean(pay_pv - prem > 0)), 3),
            "exp_net_pv_pct": round(exp_net * 100, 1),
            "disc": round(disc, 4), "med": round(float(np.median(r)), 3),
            "p10": round(float(np.percentile(r, 10)), 3), "p90": round(float(np.percentile(r, 90)), 3)}
json.dump(out, open(os.path.join(HERE, "dip_experiment.json"), "w"), indent=1)

for nm in NAMES:
    o = out["names"][nm]
    print(f"\n{nm}  (P(>25% dip within 6m)={o['p_dip_6m']:.0%}, n={ndip[nm]})")
    print(f"  {'tenor':5s} {'ATMprem':>7s} {'P(ITM)':>7s} {'P(profit,net)':>13s} {'E[net,PV]':>9s} {'med S/entry':>11s}")
    for lab, _ in EXP:
        t = o["tenors"][lab]
        print(f"  {lab:5s} {t['atm_premium_pct']:>6.1f}% {t['p_itm']:>6.0%} {t['p_profit_net']:>12.0%} "
              f"{t['exp_net_pv_pct']:>8.1f}% {t['med']:>10.2f}")

print("\n" + "=" * 78)
print("TAKEAWAY: " + ("at CURRENT model-fair ATM premiums, buying calls after a >25% dip is NOT\n"
      "positive-EV at ANY tenor for these names (E[net,PV] <= 0 across the board)." if all_negative else
      "some tenors show positive E[net,PV] at current premiums -- inspect per-name."))
print("The model's value here is AVOIDING WRONG-TENOR TRADES, not proving dip-buying calls pay.")
print("Premiums are read live from options_lens.json; re-run options_lens.py after any calibration change.")
print("RESEARCH MODEL -- NOT INVESTMENT ADVICE.")
