"""
ILLUSTRATIVE history seeder (DEMO ONLY -- not part of the pipeline).

Creates ~1 month of daily snapshots so the change-tracking ledger and the
visual have something to show before real daily runs accumulate. Every entry
is marked {"demo": true}. It anchors the most recent values to today's REAL
model output and walks backward with plausible drift, imposing a few slow
trends so the cumulative-drift detector has something to catch:
   - AppLovin  : permanent-loss & fragility creeping up (slow)
   - Lumentum  : penetration climbing (runway being consumed)
   - Micron    : recovery-quality sliding
   - VIX/oil/real-rate: a stretched-macro drift with a mid-month vol spike
Real daily runs (track_changes.py --record) append genuine snapshots after this.
"""
import datetime as dt
import json
import math
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
random.seed(7)

with open(os.path.join(HERE, "results.json")) as f:
    R = json.load(f)
rc = R["companies"]["recovery_cond"]
dec = R["companies"].get("decomposition", {})

# real "today" endpoint per company
end = {nm: {"fragility": rc[nm]["fragility"],
            "recovery_quality": rc[nm]["recovery_quality"],
            "p_deep_permanent": rc[nm].get("p_deep_permanent"),
            "pen": dec.get(nm, {}).get("pen")} for nm in rc}

# movers: (metric -> total drift over the month, ending at the real value)
MOVERS = {
    "AppLovin": {"p_deep_permanent": +0.055, "fragility": +0.06},
    "Lumentum": {"pen": +0.018, "fragility": +0.04},
    "Micron":   {"recovery_quality": -0.045, "p_deep_permanent": +0.02},
    "IonQ":     {"p_deep_permanent": +0.025},
}

# business days for the past ~month, ending yesterday (today is added live)
today = dt.date.fromisoformat(R.get("as_of", dt.date.today().isoformat()))
days = []
d = today - dt.timedelta(days=1)
while len(days) < 21:
    if d.weekday() < 5:
        days.append(d)
    d -= dt.timedelta(days=1)
days = sorted(days)
n = len(days)

def macro_path(t):
    f = t / (n - 1)
    vix = 14.0 + 2.0 * f + 9.0 * math.exp(-((t - n*0.55)**2) / (2*(n*0.12)**2))  # spike mid-month
    return {
        "vix": round(vix + random.uniform(-0.4, 0.4), 1),
        "brent_usd": round(84 + 11 * f + random.uniform(-1, 1), 1),
        "ust_10y_real": round(1.74 + 0.33 * f + random.uniform(-0.02, 0.02), 2),
        "shiller_cape": round(39.5 + 2.1 * f + random.uniform(-0.2, 0.2), 1),
        "ust_10y": round(4.10 + 0.36 * f, 2),
        "fed_funds_mid": 3.625,
    }

hist = {"history": []}
for t, day in enumerate(days):
    f = t / (n - 1)
    comps = {}
    for nm, ev in end.items():
        c = {}
        for m, vend in ev.items():
            if vend is None:
                c[m] = None; continue
            drift = MOVERS.get(nm, {}).get(m, 0.0)
            v0 = vend - drift                      # value at start of window
            val = v0 + drift * f                   # linear trend to the real endpoint
            val += random.uniform(-0.004, 0.004)   # small daily noise
            c[m] = round(max(0.0, val), 4)
        comps[nm] = c
    hist["history"].append({"date": day.isoformat(), "demo": True,
                            "macro": macro_path(t), "companies": comps})

with open(os.path.join(HERE, "drift_history.json"), "w") as f:
    json.dump(hist, f, indent=1)
print(f"Seeded {len(hist['history'])} illustrative snapshots "
      f"({days[0]} -> {days[-1]}). All marked demo:true.")
