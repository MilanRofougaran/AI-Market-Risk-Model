"""
============================================================================
 RUNWAY_DECAY  --  systemic_model
============================================================================
 THE 5-YEAR CUSHION TEST (no re-simulation).

 The model's recovery thesis rests on RUNWAY: a name far from its TAM ceiling
 (low penetration) into a large, fast-growing market has a justified premium and
 a fundamental floor to recover to. But that cushion is NOT static over a multi-
 year hold. As a company grows, penetration rises and runway (the 1-penetration
 term) shrinks -- UNLESS the TAM grows at least as fast as the company's revenue.

 This script makes that explicit. For each name it rolls:
     revenue_t = revenue_0 * prod(1 + g_s)        g_s = forward revenue growth (fading)
     TAM_t     = TAM_0     * (1 + tam_cagr)^t
     penetration_t = revenue_t / TAM_t
 and then re-runs the engine's OWN decomposition at each horizon, so the
 fragility and recovery-quality numbers are the same math the Monte Carlo uses.

 The verdict for the user's 5-year thesis:
   - penetration FLAT or FALLING  -> TAM outgrows the company -> cushion HOLDS
     -> "still away from TAM, premium still earned, recovery still likely."
   - penetration RISING            -> company outgrows its TAM -> cushion ERODES
     -> the premium quietly converts justified -> floating, recovery weakens.

 g_s fades toward the TAM growth rate (share-gainers converge to their market):
     g_s = tam_cagr + (g0 - tam_cagr) * FADE**(s-1)
 so this is "if current momentum fades normally," not "growth forever."

 GROWTH inputs are forward estimates [JUDGMENT, Jun 2026]. RESEARCH MODEL, NOT
 INVESTMENT ADVICE.
============================================================================
"""
import copy
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "discovery"))

import calibration as C
import engine as E
import tam_bridge as TB

FADE = 0.75   # how fast above-market growth fades toward the TAM growth rate
YEARS = [0, 1, 2, 3, 5]

# Forward near-term revenue-growth estimates (decimal, will fade). [JUDGMENT]
REVENUE_GROWTH = {
    "NVIDIA": 0.45, "Broadcom": 0.38, "Micron": 0.45, "Kioxia": 0.05,
    "Marvell": 0.35, "Qualcomm": 0.08, "AMD": 0.35, "ARM": 0.25,
    "Lumentum": 0.55, "Coherent": 0.25, "Applied Optoelectronics": 0.55, "IonQ": 0.80,
    "Palantir": 0.55, "AppLovin": 0.30, "Meta": 0.16, "Microsoft": 0.14, "Amazon": 0.12,
}


def _ensure_universe():
    """Make sure the bridged names are in COMPANIES so we can project them."""
    new, _ = TB.build_company_universe(base_companies=C.COMPANIES, verbose=False)
    for nm, spec in new.items():
        C.COMPANIES.setdefault(nm, spec)


def _growth_path(g0, c, years):
    """Cumulative revenue multiplier at each year, with growth fading to c."""
    mult = [1.0]
    g = g0
    for t in range(1, years + 1):
        g = c + (g0 - c) * (FADE ** (t - 1))
        mult.append(mult[-1] * (1 + g))
    return mult


def project(name):
    base = C.COMPANIES[name]
    c = base["tam_cagr"]
    g0 = REVENUE_GROWTH.get(name, c)   # default: grows with its market
    rev_mult = _growth_path(g0, c, max(YEARS))
    out = []
    for t in YEARS:
        comp = copy.deepcopy(base)
        comp["rev_bn"] = base["rev_bn"] * rev_mult[t]
        comp["tam_bn"] = base["tam_bn"] * ((1 + c) ** t)
        dec = E.decompose_premium({name: comp})[name]
        out.append(dict(year=t, pen=dec["pen"], runway_norm=dec["runway_norm"],
                        fragility=dec["fragility"], recovery_quality=dec["recovery_quality"]))
    return dict(name=name, g0=g0, tam_cagr=c, traj=out)


def classify(traj):
    p0 = traj[0]["pen"]
    p5 = traj[-1]["pen"]
    rq0 = traj[0]["recovery_quality"]
    rq5 = traj[-1]["recovery_quality"]
    drq = rq5 - rq0
    if p5 <= p0 * 1.05:
        verdict = "CUSHION HOLDS  (TAM keeps pace; still away from ceiling)"
    elif drq < -0.08:
        verdict = "CUSHION ERODES (penetration climbs, recovery quality falls)"
    else:
        verdict = "cushion softens (penetration climbs, recovery quality dips)"
    return verdict, drq


def run(names=None):
    _ensure_universe()
    if names is None:
        names = [n for n in REVENUE_GROWTH if n in C.COMPANIES]
    rows = [project(n) for n in names]
    # sort by 5y recovery_quality desc (best cushion at the end of the hold)
    rows.sort(key=lambda r: -r["traj"][-1]["recovery_quality"])

    print("#" * 82)
    print("#  RUNWAY-DECAY  --  does the recovery cushion survive a multi-year hold?")
    print(f"#  growth fades to TAM rate (fade={FADE}); penetration = revenue / TAM")
    print("#  RESEARCH MODEL, NOT INVESTMENT ADVICE")
    print("#" * 82)
    print(f"\n{'Name':24s} {'g0':>4s} {'TAMc':>5s} | "
          + " ".join(f"pen{y}y" for y in YEARS) + " | "
          + " ".join(f"rq{y}y" for y in YEARS) + "  verdict")
    print("-" * 82)
    results = []
    for r in rows:
        verdict, drq = classify(r["traj"])
        pens = " ".join(f"{p['pen']*100:4.0f}" for p in r["traj"])
        rqs = " ".join(f"{p['recovery_quality']*100:4.0f}" for p in r["traj"])
        print(f"{r['name']:24s} {r['g0']*100:3.0f}% {r['tam_cagr']*100:4.0f}% | "
              f"{pens} | {rqs}  {verdict}")
        results.append(dict(**r, verdict=verdict, drq=drq))
    print("\n  pen#y = penetration (% of TAM used) at year #;  rq#y = recovery-quality score")
    print("  Read across: penetration rising + recovery-quality falling = cushion eroding.")
    return results


if __name__ == "__main__":
    run()
