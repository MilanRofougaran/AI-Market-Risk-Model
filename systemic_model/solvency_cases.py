"""
============================================================================
 SOLVENCY_CASES -- did the financing/durability fork predict real outcomes?
============================================================================
 Tests the solvency mechanism against REAL names through the 2021-peak ->
 2022 crash -> 2024 outcome. Each case carries its Dec-2021 financials
 (funding_need, debt_load, revenue_durability AS JUDGED AT THE TIME) and the
 KNOWN outcome (recovered to/near old highs by ~2024, vs. permanently impaired
 / bankrupt / still down >60%).

 The thesis under test: among names that all crashed hard, the ones that
 PERMANENTLY impaired are the ones with weak financials AND non-durable
 revenue; the ones that RECOVERED kept their revenue compounding (so they
 could refinance/raise and grow back) even if they were burning cash.

 Pass test = impairment_hazard ranks IMPAIRED above RECOVERED (the hazard is a
 monotone discriminator). This validates the MECHANISM; the financial inputs
 are retrospective, so it is an honesty check of the LOGIC, not a forecast.
 RESEARCH MODEL, NOT INVESTMENT ADVICE.
============================================================================
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import solvency as SV

# name: (funding_need, debt_load, rev_durability, outcome, realized_dd, recovered, note)
#   funding_need/debt_load/rev_durability = Dec-2021 judgment (0..1)
#   recovered = True if back to/near old highs by ~2024
CASES = [
    # ---- IMPAIRED: weak financials AND revenue cratered -> stayed down / failed ----
    ("WeWork",     0.95, 0.90, 0.20, "IMPAIRED", 0.99, False, "burned cash, heavy lease debt, revenue stalled -> bankrupt 2023"),
    ("Carvana",    0.85, 0.95, 0.30, "IMPAIRED", 0.99, False, "huge debt, revenue stalled in a rate shock -> -99%, near-bankruptcy"),
    ("Peloton",    0.80, 0.50, 0.20, "IMPAIRED", 0.95, False, "cash burn + revenue collapsed post-COVID -> still down ~90%"),
    ("Roku",       0.50, 0.20, 0.35, "IMPAIRED", 0.90, False, "ad revenue cratered, unprofitable -> still down ~85%"),
    ("Snap",       0.60, 0.30, 0.35, "IMPAIRED", 0.90, False, "ad revenue stalled, burning -> still down ~80%"),
    ("Affirm",     0.85, 0.70, 0.30, "IMPAIRED", 0.92, False, "BNPL: funding-market dependent + credit-cyclical revenue"),
    # ---- RECOVERED: weak-ish financials BUT revenue kept compounding ----
    ("Shopify",    0.40, 0.10, 0.70, "RECOVERED", 0.80, True,  "cash-light but GMV kept growing ~20-25% -> recovered most"),
    ("Cloudflare", 0.50, 0.20, 0.80, "RECOVERED", 0.75, True,  "unprofitable but revenue +30-40% through -> back to highs"),
    ("Datadog",    0.35, 0.10, 0.80, "RECOVERED", 0.65, True,  "FCF-light but mission-critical revenue compounding -> recovered"),
    ("Uber",       0.50, 0.40, 0.70, "RECOVERED", 0.55, True,  "was burning but bookings grew, turned FCF+ -> back to highs"),
    ("NVIDIA",     0.05, 0.05, 0.85, "RECOVERED", 0.66, True,  "fortress + revenue reaccelerated -> new all-time highs"),
    ("Microsoft",  0.00, 0.10, 0.95, "RECOVERED", 0.38, True,  "fortress, durable revenue -> shallow drawdown, full recovery"),
]


def run(verbose=True):
    scored = []
    for nm, fn, dl, rd, outcome, dd, rec, note in CASES:
        fr = SV.financing_fragility(fn, dl)
        h = SV.SOLVENCY_MAX * fr * (1.0 - rd)
        scored.append((nm, fn, dl, rd, fr, h, outcome, rec, note))
    scored.sort(key=lambda r: -r[5])

    imp = [r for r in scored if r[6] == "IMPAIRED"]
    rcv = [r for r in scored if r[6] == "RECOVERED"]
    # rank-separation: fraction of (impaired, recovered) pairs the hazard orders correctly (AUC)
    pairs = [(a, b) for a in imp for b in rcv]
    correct = sum(1 for a, b in pairs if a[5] > b[5])
    ties = sum(1 for a, b in pairs if abs(a[5] - b[5]) < 1e-9)
    auc = (correct + 0.5 * ties) / len(pairs) if pairs else float("nan")
    # a single threshold that best separates
    hs = sorted(set(round(r[5], 3) for r in scored))
    best_t, best_acc = None, -1
    for t in hs:
        acc = (sum(1 for r in imp if r[5] >= t) + sum(1 for r in rcv if r[5] < t)) / len(scored)
        if acc > best_acc:
            best_acc, best_t = acc, t

    if verbose:
        print("SOLVENCY MECHANISM vs 2021->2024 OUTCOMES")
        print("=" * 78)
        print(f"{'Name':12s} {'fund':>5s} {'debt':>5s} {'revD':>5s} {'haz':>5s}  {'outcome':10s} note")
        print("-" * 78)
        for nm, fn, dl, rd, fr, h, outcome, rec, note in scored:
            print(f"{nm:12s} {fn:5.2f} {dl:5.2f} {rd:5.2f} {h*100:4.0f}%  {outcome:10s} {note[:38]}")
        print("-" * 78)
        print(f"mean hazard: IMPAIRED {sum(r[5] for r in imp)/len(imp)*100:.0f}%  vs  "
              f"RECOVERED {sum(r[5] for r in rcv)/len(rcv)*100:.0f}%")
        print(f"rank separation (AUC, impaired ranked above recovered): {auc:.2f}  (1.0 = perfect)")
        print(f"best single hazard threshold: {best_t*100:.0f}%  -> classifies {best_acc*100:.0f}% of cases correctly")
        print("\nKey discriminator (your thesis): among the cash-burners, REVENUE DURABILITY")
        print("splits them -- Peloton (revDur 0.20) impaired vs Shopify (revDur 0.70) recovered,")
        print("even though both were unprofitable and fell ~80-95%.")
        print("\n(Retrospective inputs -> validates the MECHANISM/ordering, not foresight.)")
    return dict(auc=auc, best_threshold=best_t, best_acc=best_acc,
                impaired_mean=sum(r[5] for r in imp)/len(imp),
                recovered_mean=sum(r[5] for r in rcv)/len(rcv))


if __name__ == "__main__":
    run()
