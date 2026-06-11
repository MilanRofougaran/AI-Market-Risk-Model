"""
============================================================================
 OPTIONS_LENS  --  call-option duration analysis from the model's own paths
============================================================================
 Standalone module: imports the engine, re-simulates with the same seed and
 machinery, and evaluates CALL payoffs at 6/12/18/24/36-month expiries for
 the core simulated companies. NO model source is modified.

 RUN:
   python3 options_lens.py                 # default 30,000 paths
   python3 options_lens.py --paths 8000    # quicker
 Writes options_lens.md + options_lens.json

 WHAT IT REPORTS (per name x expiry x strike, strikes vs entry = 1.00):
   P(ITM)        chance the simulated price ends above the strike
   fair value    discounted E[max(S_T - K, 0)] under the model's REAL-WORLD
                 measure (your growth/TAM judgments) -- NOT risk-neutral.
   S_T quantiles p10 / median / p90 of the price at expiry

 HOW TO USE: compare 'fair value' to the market premium for that strike and
 expiry. Model fair > market premium = a thesis-conditional edge (the odds
 favor it IF the model's judgment inputs are right) -- never an arbitrage.

 HONEST LIMITS (read before trading):
  1. Physical measure, not risk-neutral: this is your thesis priced, not the
     market's. It cannot detect IV mispricing and ignores vega/IV-crush.
  2. Raw market paths: the cyclical demand-trough suppression lives in the
     model's RECOVERY measurement, not in the price path -- so short-dated
     numbers for cyclicals (Micron, Kioxia) are OPTIMISTIC upper bounds.
     Always cross-check the drawdown x recovery matrix before short expiries.
  3. Recovery-to-peak is not breakeven: an option wins only past strike +
     premium. Use the quantiles.
  4. Covers the engine's 8 core companies, 6 extended bridge names (Palantir,
     Astera Labs, CoreWeave, Lumentum, Applied Optoelectronics, IonQ), and
     true holdings-aggregated ETF baskets (DRAM, SMH) — 16 names total.
 RESEARCH MODEL -- NOT INVESTMENT ADVICE.
============================================================================
"""
import argparse, json, sys, zlib
import numpy as np

import os
HERE=os.path.dirname(os.path.abspath(__file__))
import sys; sys.path.insert(0, os.path.join(HERE,"discovery"))
import calibration as C
import engine as E
import tam_bridge as TB

# extended (matrix-only) names now lensed via the SAME spec machinery the
# pipeline uses (tam_bridge inputs -> decompose_premium -> company_to_spec):
EXTENDED = ["Palantir","Astera Labs","CoreWeave","Lumentum","Applied Optoelectronics","IonQ"]
ETFS = ["DRAM (Roundhill Memory)", "SMH (VanEck Semis)"]   # true holdings-aggregated baskets
# archetype gates surfaced next to every fair value (fair value is physical-
# measure: volatility inflates it; the gate is what keeps you out of traps):
GATES = {"Palantir":"secular/watch","Astera Labs":"secular (PEG-fast, MC-uncertain)",
         "CoreWeave":"cyclical — 45% >3y tail: survivability gate","Lumentum":"cyclical — no short calls",
         "Applied Optoelectronics":"cyclical — no short calls",
         "DRAM (Roundhill Memory)":"cyclical memory basket — no short calls; demand-trough gate",
         "SMH (VanEck Semis)":"secular basket (idio-damped)",
         "IonQ":"BROKEN — model gate: avoid; duration does not repair thesis",
         "Micron":"cyclical — no short calls","Kioxia":"cyclical — no short calls",
         "Marvell":"cyclical lean","AMD":"cyclical lean","NVIDIA":"secular",
         "Broadcom":"secular/diversified","Qualcomm":"cyclical/safe","ARM":"secular/safe"}

EXPIRIES = [("6m", 126), ("12m", 252), ("18m", 378), ("24m", 504), ("36m", 756)]
STRIKES = [0.50, 0.60, 0.70, 0.75, 0.80, 0.85, 0.90, 1.00, 1.10, 1.20, 1.50, 1.75, 2.00, 2.25, 2.50]


def discount_rate():
    r = (C.MACRO.get("ust_10y") or 4.0) / 100.0
    return r


def run(paths=30000, chunk=None):
    decomp = E.decompose_premium()
    for nm in EXTENDED:
        inp = dict(TB.STOCK_TAM_FACTS[nm]); inp["name"] = nm
        decomp[nm] = E.decompose_premium({nm: inp})[nm]
    facts = dict(C.COMPANIES); facts.update({k: dict(v) for k, v in TB.STOCK_TAM_FACTS.items()})
    for nm in ETFS:
        spec_inp, _info = TB.etf_spec(nm, facts)
        spec_inp = dict(spec_inp); spec_inp["name"] = nm
        decomp[nm] = E.decompose_premium({nm: spec_inp})[nm]
    names = list(decomp.keys())
    rng = np.random.default_rng(C.SIM["seed"])
    CH = min(chunk or C.SIM["chunk"], paths)
    DAYS = max(d for _, d in EXPIRIES)
    idio = {nm: np.random.default_rng((C.SIM["seed"] ^ (zlib.crc32(nm.encode()) & 0xFFFFFFFF)) & 0xFFFFFFFF)
            for nm in names}
    ST = {nm: {lab: [] for lab, _ in EXPIRIES} for nm in names}

    done = 0
    while done < paths:
        n = min(CH, paths - done)
        factor, crisis, grind = E._simulate_factor(rng, n, DAYS, return_grind=True)
        subfactors = {g: rng.standard_normal((n, DAYS)) for g in getattr(C, "GROUP_RHO", {})}
        for nm in names:
            spec = E.company_to_spec(decomp[nm], name=nm)
            price = E._price_path(rng, factor, crisis, spec, n, DAYS,
                                  tail_mult=spec["tail_mult"], subfactors=subfactors,
                                  grind=grind, idio_rng=idio[nm])
            for lab, d in EXPIRIES:
                ST[nm][lab].append(price[:, d - 1].copy())
        done += n
        print(f"  options lens: {done:,}/{paths:,} paths", file=sys.stderr)

    r = discount_rate()
    out = {"paths": paths, "seed": C.SIM["seed"], "discount_10y": r,
           "note": "physical-measure fair values; thesis-conditional, not risk-neutral",
           "names": {}}
    for nm in names:
        out["names"][nm] = {"gate": GATES.get(nm, "")}
        for lab, d in EXPIRIES:
            s = np.concatenate(ST[nm][lab])
            T = d / 252.0
            disc = np.exp(-r * T)
            row = {"S_T": {"p10": round(float(np.percentile(s, 10)), 3),
                           "median": round(float(np.median(s)), 3),
                           "p90": round(float(np.percentile(s, 90)), 3)},
                   "strikes": {}}
            for K in STRIKES:
                pay = np.maximum(s - K, 0.0)
                row["strikes"][f"{K:.2f}"] = {
                    "p_itm": round(float(np.mean(s > K)), 3),
                    "fair_value_pct_of_spot": round(float(disc * pay.mean()) * 100, 1),
                }
            out["names"][nm][lab] = row
    return out


def write_md(out, path="options_lens.md"):
    L = ["# Options duration lens — call fair values from the model's own paths",
         "",
         f"{out['paths']:,} paths · seed {out['seed']} · discounted at 10y {out['discount_10y']:.2%} · "
         "physical measure (thesis-conditional, NOT risk-neutral, no IV/vega)",
         "",
         "Read with the drawdown × recovery matrix: short-dated cyclical numbers here are "
         "upper bounds (the demand-trough suppression lives in the recovery measurement, "
         "not the raw price path). RESEARCH MODEL — NOT INVESTMENT ADVICE.",
         ""]
    for nm, by in out["names"].items():
        gate = by.get("gate","")
        L += [f"## {nm}" + (f"  — gate: {gate}" if gate else ""), "",
              "| Expiry | S_T p10 / med / p90 | " +
              " | ".join(f"K={k} P(ITM) / fair%" for k in by["6m"]["strikes"]) + " |",
              "|---|---|" + "---|" * len(STRIKES)]
        for lab, _ in EXPIRIES:
            row = by.get(lab)
            if not isinstance(row, dict) or "strikes" not in row: continue
            cells = " | ".join(f"{v['p_itm']:.0%} / {v['fair_value_pct_of_spot']:.1f}%"
                               for v in row["strikes"].values())
            q = row["S_T"]
            L.append(f"| {lab} | {q['p10']:.2f} / {q['median']:.2f} / {q['p90']:.2f} | {cells} |")
        L.append("")
    L += ["### How to act on this",
          "1. Pick the name; check its archetype and matrix first (cyclical → avoid 6/12m regardless of the numbers above).",
          "2. Find your strike column; compare `fair%` to the market premium (% of spot) for that expiry.",
          "3. Edge = fair > premium **and** the matrix supports the duration **and** macro stress isn't escalating (freeze ⇒ roll long).",
          ""]
    open(path, "w").write("\n".join(L))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", type=int, default=30000)
    a = ap.parse_args()
    out = run(paths=a.paths)
    json.dump(out, open("options_lens.json", "w"), indent=1)
    write_md(out)
    print("wrote options_lens.md / options_lens.json")
