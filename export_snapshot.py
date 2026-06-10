"""
export_snapshot.py — turn the model's artifacts into site/data/snapshot.json
Run from the repo root after a pipeline run:
    python3 export_snapshot.py
Reads  systemic_model/tier_table.csv + systemic_model/results.json (+ calibration stress)
Writes site/data/snapshot.json  (the static file the Netlify dashboard and /ask function read)
"""
import csv, json, os, sys, time

ROOT = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.join(ROOT, "systemic_model")
OUT = os.path.join(ROOT, "site", "data", "snapshot.json")

def _f(x):
    try: return float(x)
    except Exception: return None

def rows():
    out = []
    for r in csv.DictReader(open(os.path.join(MODEL, "tier_table.csv"))):
        out.append({
            "name": r["name"], "kind": r.get("type"), "tier": r.get("growth_tier"),
            "verdict": r.get("recovery_rank") or r.get("crash_growth"),
            "crash_growth": r.get("crash_growth"),
            "growth": _f(r.get("exp_growth_18m")), "p25": _f(r.get("P(>25% fall)")),
            "rec2y": _f(r.get("recover_by_2y_if_falls")), "tail": _f(r.get("gt3y_tail_unconditional")),
            "perm": _f(r.get("true_permanent_loss")), "xsp": _f(r.get("perm_vs_SP_multiple")),
            "vssp": _f(r.get("reward_vs_SP")), "vsschd": _f(r.get("reward_vs_SCHD")),
        })
    return out

def matrices_macro():
    res = json.load(open(os.path.join(MODEL, "results.json")))
    mats = {}
    for nm, o in (res.get("companies", {}).get("recovery_cond", {}) or {}).items():
        m = o.get("dd_recovery_matrix")
        if not m: continue
        mats[nm] = {h: {"p": m[h]["p_drawdown"],
                        "r": [m[h]["recover_6m"], m[h]["recover_12m"], m[h]["recover_18m"],
                              m[h]["recover_24m"], m[h]["recover_36m"]]}
                    for h in ("6m", "12m", "18m") if h in m}
    return mats, res.get("macro", {}), res.get("regime_probs", {}), res.get("as_of")

def stress():
    try:
        sys.path.insert(0, MODEL)
        import calibration as C  # noqa
        ss = C.SYSTEMIC_STRESS
        return {"score": round(ss["score"], 3), "structural": round(ss["structural"], 3),
                "acute": round(ss["acute"], 3), "base_pe": round(getattr(C, "BASE_PE", 0), 1),
                "freeze_severity": round(getattr(C, "FREEZE_SEVERITY", 0), 3)}
    except Exception as e:
        print("  (stress unavailable:", e, ")"); return None

if __name__ == "__main__":
    mats, macro, regimes, as_of = matrices_macro()
    snap = {"as_of": as_of,
            "generated": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
            "macro": macro, "stress": stress(), "rows": rows(),
            "matrices": mats, "regimes": regimes}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(snap, open(OUT, "w"))
    print(f"wrote {OUT}: {len(snap['rows'])} rows, {len(snap['matrices'])} matrices, as_of {as_of}")
