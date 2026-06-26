"""
drawdown_normalization.py -- express each name's/basket's drawdown DEPTH and RECOVERY LENGTH as a
RATIO TO THE S&P 500 in the SAME crisis, instead of as absolute (unvalidated) month-counts.

WHY THIS IS MORE HONEST than an absolute recovery clock: I have repeatedly refused to print
"Micron recovers in 18 months" because that needs real per-name historical series I don't have, and
a fabricated month-count is worse than silence. A RELATIVE statement -- "falls ~1.8x the S&P's depth
and takes ~2.3x as long to recover" -- is different: it anchors to the index (whose own drawdown/
recovery history is well-known and NOT name-specific), and it asks the model to do what beta-and-
fundamentals models are good at (relative positioning) rather than what they can't validate (the
absolute clock).

VALIDATION STATUS (stamped on every output, NOT uniform):
  - DEPTH ratio  = name MDD / S&P MDD on the same paths -> BETA-GROUNDED (beta *is* relative depth). Honest.
  - RECOVERY ratio = name recovery / S&P recovery       -> MODEL-ESTIMATED, TIMING-AXIS UNVALIDATED.
    Normalizing to the S&P changes the UNITS, not the validation status -- the recovery-length
    relationship is still on the axis the backtest does not cover. See DRAWDOWN_NORM_CALIBRATION_SPEC.md.

S&P anchor: a SYNTHETIC reference leg now (beta 1.0, high recovery-quality, near-zero permanent
impairment) simulated on the SAME crisis paths. A hook (SP500_HISTORICAL_ANCHORS) lets you swap in
REAL historical S&P depth/recovery (2000/08/20/22) when available, to translate ratios into months.
RESEARCH MODEL -- NOT INVESTMENT ADVICE.
"""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "discovery"))
import calibration as C, engine as E
import correlation as COR   # reuse its joint-sim plumbing (_specs, GROUP_RHO)

# --- the synthetic S&P-500 reference decomposition (index profile) ---
SP500_REF = dict(beta=1.0, fragility=0.08, recovery_quality=0.80, earnings_cyclicality=0.10,
                 runway_norm=0.5, earn_quality=0.85, fwd_pe=20.0, unsupported_frac=0.05, val_gap=0.0)

# --- OPTIONAL real anchors (fill from history to convert ratios -> months). None => synthetic only. ---
# e.g. {"2008": {"depth": 0.57, "recovery_months": 49}, "2020": {"depth":0.34,"recovery_months":5}, ...}
SP500_HISTORICAL_ANCHORS = None

RECOVERY_RATIO_RELIABLE = False   # synthetic leg: beta-symmetric rebound biases it (see _RECOVERY_WARNING)
_RECOVERY_WARNING = (
    "SYNTHETIC-LEG ARTIFACT: in a beta-driven factor model a high-beta name falls deeper AND rebounds "
    "harder when the factor mean-reverts (beta is symmetric), so deep fallers appear to recover FASTER "
    "than the index. This CONTRADICTS cyclical earnings reality (e.g. Micron's ~95% EPS trough -- the pain "
    "is the WAIT). The recovery-LENGTH ratio is therefore NOT usable from the synthetic leg; it requires "
    "real S&P historical anchors + per-archetype recovery calibration (DRAWDOWN_NORM_CALIBRATION_SPEC.md). "
    "Use the DEPTH ratio (beta-grounded, trustworthy) and P(never recover | crisis) instead.")

# --- 1-5 BANDS (Band 1 = ~same as S&P; bands rise = falls/recovers MORE than S&P) -------------------
# DEPTH band cut-points are set from the OBSERVED depth-ratio distribution of this universe (not an
# abstract scheme): ratios compress at ~1.1-1.3x (most AI/semi names fall ~1.2x the index in a crisis --
# they barely differentiate on depth because they're correlated high-beta names), with a lone stabilizer
# (~1.0x) and two elevated names (~1.55, ~1.75). Bands are a HONEST unit: they keep the trustworthy
# ordering + rough magnitude and drop false precision (1.21 vs 1.27 is within MC noise -> same band).
DEPTH_BANDS = [(1.10, 1, "moves with the market (stabilizer)"),
               (1.30, 2, "modestly deeper than S&P (moderate beta)"),
               (1.65, 3, "clearly deeper than S&P (elevated beta)"),
               (2.10, 4, "much deeper than S&P (high beta)"),
               (float("inf"), 5, "extreme depth (high beta + fragility)")]

# RECOVERY bands use the SAME 1-5 logic (Band 1 ~ S&P clock; higher = SLOWER than S&P). Two views:
#  - synthetic: what the synthetic leg produces -> WRONG-SIGNED (beta-symmetric rebound; everything lands
#    at/below Band 1, i.e. "recovers >= as fast as S&P", which is backwards for cyclicals). Shown FLAGGED.
#  - expected prior: the archetype prior the calibration project must CONFIRM (NOT a measurement).
RECOVERY_BANDS = [(0.90, 0, "faster than S&P (artifact zone)"),   # band 0 = below the S&P clock
                  (1.20, 1, "~S&P recovery clock"),
                  (1.60, 2, "modestly slower than S&P"),
                  (2.20, 3, "slower than S&P"),
                  (3.00, 4, "much slower than S&P"),
                  (float("inf"), 5, "damaged / impaired recovery")]
# Archetype recovery PRIORS (analyst prior, pending calibration -- NOT measured). Band ranges per archetype.
RECOVERY_PRIOR = {
    "secular":          (1, 2, "secular: fast snap-back, near/just-above S&P clock"),
    "cyclical_memory":  (4, 5, "cyclical memory: slow -- EPS trough, the pain is the WAIT"),
    "cyclical_broad":   (2, 3, "broad-semi cyclical: modestly-to-clearly slower than S&P"),
    "optical":          (2, 3, "optical/infra cyclical: modestly-to-clearly slower"),
    "hyperscaler":      (5, 5, "levered hyperscaler: impaired/censored recovery risk"),
    "defensive":        (1, 2, "stabilizer: near the S&P clock"),
    "broken":           (5, 5, "broken thesis: impaired/never"),
}
_MEMORY = {"Micron", "Kioxia", "SK Hynix", "Samsung"}


def _band(value, table):
    for hi, b, label in table:
        if value < hi:
            return b, label
    return table[-1][1], table[-1][2]


def _recovery_prior_for(name):
    """Map a name to its archetype recovery-prior band range (analyst prior, NOT measured)."""
    try:
        import crash_growth as CG
        arch = CG.archetype(name)
    except Exception:
        arch = None
    # memory: individual names AND memory-basket ETFs (DRAM/Memory) -- consistent with the model's
    # explicit DRAM cyclical-memory / demand-trough gate. DRAM may not fall much deeper than the S&P
    # (B2 depth), but its RECOVERY clock is still memory-cycle slow (B4-5). (External audit fix.)
    if name in _MEMORY or "DRAM" in name or "Memory" in name:
        key = "cyclical_memory"
    elif arch == "cyclical":
        key = "cyclical_broad"
    elif arch == "broken":
        key = "broken"
    elif arch == "secular":
        key = "secular"
    else:
        key = "defensive"
    if name in {"CoreWeave"}:
        key = "hyperscaler"
    if name in {"Astera Labs"}:
        key = "optical"
    lo, hi, desc = RECOVERY_PRIOR[key]
    return key, lo, hi, desc


def _sp_spec():
    return E.company_to_spec(dict(SP500_REF), name=None)


def normalize(names, n_paths=6000, seed=None):
    """For each name, ratio its drawdown depth and recovery length to the S&P reference leg, measured
    on the SAME MARKET-CRISIS paths (where the S&P itself fell > DEPTH) -- apples-to-apples, so depth
    reflects real beta and recovery compares the same cohort. depth_ratio BETA-GROUNDED; recovery_ratio
    MODEL-ESTIMATED, TIMING-UNVALIDATED."""
    import tam_bridge as TB
    new, _ = TB.build_company_universe(base_companies=C.COMPANIES, verbose=False)
    for k, v in new.items():
        C.COMPANIES.setdefault(k, v)
    specs = COR._specs(names)
    names = [n for n in names if n in specs]
    DEPTH = getattr(E, "DEPTH", getattr(C, "DEPTH", 0.25))
    DAYS = C.SIM["days"]; CH = C.SIM["chunk"]
    rng = np.random.default_rng(seed if seed is not None else C.SIM["seed"])
    sp_spec = _sp_spec()
    name_mdd = {nm: [] for nm in names}; name_rec = {nm: [] for nm in names}
    sp_mdd, sp_rec = [], []
    done = 0
    while done < n_paths:
        n = min(CH, n_paths - done)
        factor, crisis, grind = E._simulate_factor(rng, n, DAYS, return_grind=True)
        freeze = E._systemic_freeze(factor, DAYS)
        sub = {g: rng.standard_normal((n, DAYS)) for g in COR.GROUP_RHO}
        sp_price = E._price_path(rng, factor, crisis, sp_spec, n, DAYS, tail_mult=1.0, subfactors=sub, grind=grind)
        m, r = E._drawdown_and_recovery(sp_price, 378, path_offset=done, freeze=freeze)
        sp_mdd.append(m); sp_rec.append(r)
        for nm in names:
            s = specs[nm]
            price = E._price_path(rng, factor, crisis, s, n, DAYS, tail_mult=s.get("tail_mult", 1.0),
                                  subfactors=sub, grind=grind)
            m, r = E._drawdown_and_recovery(price, 378, path_offset=done, freeze=freeze)
            name_mdd[nm].append(m); name_rec[nm].append(r)
        done += n

    spm = np.concatenate(sp_mdd); spr = np.concatenate(sp_rec)
    crisis_mask = spm <= -DEPTH                                   # the SAME market-crisis cohort for everyone
    if crisis_mask.sum() < 50:
        return {"error": f"too few S&P-crisis paths ({int(crisis_mask.sum())}); raise n_paths"}
    sp_depth = abs(float(np.median(spm[crisis_mask])))
    spr_c = spr[crisis_mask & np.isfinite(spr)]
    sp_recovery = float(np.median(spr_c)) if spr_c.size > 30 else float("nan")

    out = {"sp_reference": {"median_crisis_depth": round(sp_depth, 3),
                            "median_recovery_days": (round(sp_recovery, 0) if sp_recovery == sp_recovery else None),
                            "n_crisis_paths": int(crisis_mask.sum()),
                            "_note": "synthetic S&P leg (beta 1.0, high recovery-quality); ratios measured on its >25% crisis paths"},
           "names": {}}
    for nm in names:
        mm = np.concatenate(name_mdd[nm]); rr = np.concatenate(name_rec[nm])
        d = abs(float(np.median(mm[crisis_mask])))                # name depth on the SAME crisis paths
        rr_c = rr[crisis_mask & np.isfinite(rr)]
        rec = float(np.median(rr_c)) if rr_c.size > 30 else float("nan")
        never_among_crisis = float((~np.isfinite(rr[crisis_mask])).mean())
        depth_ratio = round(d / sp_depth, 2) if sp_depth > 0 else None
        rec_ratio = (round(rec / sp_recovery, 2) if (rec == rec and sp_recovery == sp_recovery and sp_recovery > 0) else None)
        db, dband_label = _band(depth_ratio, DEPTH_BANDS) if depth_ratio else (None, None)
        pkey, plo, phi, pdesc = _recovery_prior_for(nm)
        row = {"depth_ratio_vs_sp": depth_ratio, "depth_band": db, "depth_band_label": dband_label,
               "_depth_status": "BETA-GROUNDED, same crisis cohort -- TRUSTWORTHY (band drops false precision)",
               "p_never_recover_in_crisis": round(never_among_crisis, 3),
               "_p_never_status": "model-estimated, same crisis cohort -- usable as a relative survival signal",
               "recovery_prior_band": f"{plo}-{phi}" if plo != phi else str(plo),
               "recovery_prior_archetype": pkey, "recovery_prior_desc": pdesc,
               "_recovery_prior_status": "ANALYST PRIOR pending calibration -- NOT measured; the data project must confirm it"}
        if RECOVERY_RATIO_RELIABLE and SP500_HISTORICAL_ANCHORS:
            row["recovery_ratio_vs_sp"] = rec_ratio
            rb, rbl = _band(rec_ratio, RECOVERY_BANDS) if rec_ratio else (None, None)
            row["recovery_band"] = rb; row["recovery_band_label"] = rbl
            row["_recovery_status"] = "ANCHORED to real S&P history; still TIMING-AXIS UNVALIDATED per-name"
        else:
            row["recovery_ratio_vs_sp_RAW_synthetic"] = rec_ratio
            rb, rbl = _band(rec_ratio, RECOVERY_BANDS) if rec_ratio else (None, None)
            row["recovery_band_synthetic_WRONG_SIGNED"] = rb
            row["recovery_ratio_vs_sp"] = None; row["recovery_band"] = None
            row["_recovery_status"] = "DEFERRED -- " + _RECOVERY_WARNING
        out["names"][nm] = row
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="S&P-normalized drawdown depth/recovery bands")
    ap.add_argument("names", nargs="*", help="names to band (default: a representative set)")
    ap.add_argument("--paths", type=int, default=6000, help="MC paths (lower = faster smoke test)")
    ap.add_argument("--seed", type=int, default=None, help="override sim seed")
    args = ap.parse_args()
    names = args.names or ["NVIDIA", "AMD", "Micron", "Broadcom", "CoreWeave"]
    print("S&P-NORMALIZED DRAWDOWN / RECOVERY  (ratios to a synthetic S&P-500 leg on the same crisis paths)")
    print("depth band = BETA-GROUNDED (honest) | recovery = PRIOR-only (synthetic band wrong-signed, flagged)\n")
    o = normalize(names, n_paths=args.paths, seed=args.seed)
    if "error" in o:
        print(o["error"]); sys.exit(1)
    sp = o["sp_reference"]
    print(f"S&P reference: median CRISIS depth {sp['median_crisis_depth']:.0%}, median recovery "
          f"{sp['median_recovery_days']} days  (n={sp['n_crisis_paths']} crisis paths; {sp['_note']})\n")
    print(f"{'name':12s}{'depthX':>7s}{'D-band':>8s}{'P(nev|cr)':>10s}{'rec-band(synth)':>16s}{'rec-band(prior)':>16s}")
    for nm in names:
        r = o["names"].get(nm)
        if not r:
            print(f"{nm:12s}  (not priceable)"); continue
        dr = r["depth_ratio_vs_sp"]; db = r["depth_band"]; pn = r["p_never_recover_in_crisis"]
        rbs = r.get("recovery_band_synthetic_WRONG_SIGNED"); rp = r["recovery_prior_band"]
        synth = f"B{rbs}*" if rbs is not None else "n/a"
        print(f"{nm:12s}{(str(dr)+'x'):>7s}{('B'+str(db)):>8s}{(f'{pn:.0%}' if pn is not None else 'n/a'):>10s}"
              f"{synth:>16s}{('B'+rp):>16s}")
    print("\nDEPTH band (B1=~S&P .. B5=extreme): BETA-GROUNDED, TRUSTWORTHY. Cut-points from this universe's")
    print("  observed distribution. Most AI/semi names land B2 (~1.2x) -- they barely differ on DEPTH in a")
    print("  systemic crisis (correlated high-beta); differentiation is in recovery + P(never).")
    print("P(nev|cr): relative survival signal on the same market-crisis cohort -- usable.")
    print("rec-band(synth)* = WRONG-SIGNED synthetic artifact (beta-symmetric rebound -> everything looks fast).")
    print("  Shown only to expose the gap; NOT a verdict. Note Micron synth-band contradicts its prior band.")
    print("rec-band(prior) = archetype ANALYST PRIOR (cyclical memory slow, secular fast) -- NOT measured;")
    print("  the calibration data project must CONFIRM it. See DRAWDOWN_NORM_CALIBRATION_SPEC.md.")
    print("RESEARCH MODEL -- NOT INVESTMENT ADVICE.")

