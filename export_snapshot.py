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

def league():
    """The Top-125 league state (league.json), or empty if not built yet.
    Returns (members_by_name, summary)."""
    p = os.path.join(MODEL, "league.json")
    if not os.path.exists(p):
        return {}, None
    lg = json.load(open(p))
    by_name = {m["name"]: m for m in lg.get("members", [])}
    summary = {k: lg.get(k) for k in
               ("metric", "pool_cap", "view_cap", "margin", "n_members",
                "entered", "exited", "as_of")}
    return by_name, summary

def _load(name):
    try:
        return json.load(open(os.path.join(MODEL, name)))
    except Exception:
        return None

def per_name_analyses():
    """Per-name detail to attach to each row (same names, richer cards):
    valuation/VAL-GAP, fundamental earn-back clock, and premium decomposition."""
    val, eb, dec = {}, {}, {}
    vr = _load("valuation_report.json")
    if vr:
        for grp in ("stocks", "etfs"):
            for nm, v in (vr.get(grp) or {}).items():
                val.setdefault(nm, {"fwd_pe": v.get("fwd_pe"), "fair_pe": v.get("justified_pe_sam"),
                                    "val_gap": v.get("val_gap"), "balance": v.get("balance")})
    fc = _load("fundamental_catchup.json")
    if fc:
        for r in fc.get("rows", []):
            yrs = r.get("years_bb") if r.get("years_bb") is not None else r.get("years")
            eb[r["name"]] = {"years": (None if r.get("is_infinite") else yrs), "verdict": r.get("verdict")}
    res = _load("results.json")
    if res:
        comp = res.get("companies", {})
        dd = comp.get("decomposition", {}) or {}
        rcv = comp.get("recovery_cond", {}) or {}
        for nm, d in dd.items():
            eff = d.get("eff_pe"); rc = rcv.get(nm, {})
            dec[nm] = {"eff_pe": eff, "premium_pts": d.get("premium_pts"),
                       "justified_pts": d.get("justified_pts"),
                       "unsupported_pct": (round((d.get("unsupported_pts") or 0) / eff * 100, 1) if eff else None),
                       "fragility": rc.get("fragility"), "recovery_quality": rc.get("recovery_quality")}
    ex = (_load("model_extras.json") or {}).get("names", {})   # tier-panel / reverse-DCF / confidence / waterfall / solvency
    return val, eb, dec, ex

def rows(lmap, val, eb, dec, ex):
    out = []
    for r in csv.DictReader(open(os.path.join(MODEL, "tier_table.csv"))):
        tier = r.get("growth_tier")
        # leveraged vehicles land in the "Trading" tier; label their verdict so the
        # dashboard's "leveraged" filter shows them (the model's crash_growth column
        # mislabels a 3x daily-reset decay product as "secular").
        verdict = "leveraged" if tier == "Trading" else (r.get("recovery_rank") or r.get("crash_growth"))
        info = lmap.get(r["name"])
        nm = r["name"]
        out.append({
            "name": nm, "kind": r.get("type"), "tier": tier,
            "verdict": verdict,
            "crash_growth": r.get("crash_growth"),
            "growth": _f(r.get("exp_growth_18m")), "p25": _f(r.get("P(>25% fall)")),
            "rec2y": _f(r.get("recover_by_2y_if_falls")), "tail": _f(r.get("gt3y_tail_unconditional")),
            "perm": _f(r.get("true_permanent_loss")), "xsp": _f(r.get("perm_vs_SP_multiple")),
            "vssp": _f(r.get("reward_vs_SP")), "vsschd": _f(r.get("reward_vs_SCHD")),
            # league membership (from league.json): rank within the Top-125 board,
            # whether it's in the highlighted Top-50, and whether it's a member at all.
            "rank": (info or {}).get("rank"),
            "top50": bool(info and info.get("top50")),
            "in_league": info is not None,
            "pinned": bool(info and info.get("pinned")),
            # richer per-name detail (rendered as cards in the detail panel)
            "val": val.get(nm), "earnback": eb.get(nm), "decomp": dec.get(nm),
            "extra": ex.get(nm),   # tier-panel / reverse-DCF / confidence / earnings-waterfall / solvency
        })
    return out

def matrices_macro():
    res = json.load(open(os.path.join(MODEL, "results.json")))
    mats = {}
    trajs = {}
    for nm, o in (res.get("companies", {}).get("recovery_cond", {}) or {}).items():
        m = o.get("dd_recovery_matrix")
        if m:
            mats[nm] = {h: {"p": m[h]["p_drawdown"],
                            "r": [m[h]["recover_6m"], m[h]["recover_12m"], m[h]["recover_18m"],
                                  m[h]["recover_24m"], m[h]["recover_36m"]]}
                        for h in ("6m", "12m", "18m") if h in m}
        t = o.get("trajectory")               # forward p10/median/p90 price cone (fan chart)
        if t:
            trajs[nm] = t
    return mats, trajs, res.get("macro", {}), res.get("regime_probs", {}), res.get("as_of")

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
    mats, trajs, macro, regimes, as_of = matrices_macro()
    lmap, lsummary = league()
    val, eb, dec, ex = per_name_analyses()
    snap = {"as_of": as_of,
            "generated": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
            "macro": macro, "stress": stress(), "rows": rows(lmap, val, eb, dec, ex),
            "league": lsummary,
            "matrices": mats, "trajectories": trajs, "regimes": regimes,
            # extra model analyses (surfaced as their own sections, same table style)
            "etf_horizon": _load("etf_horizon_rank.json"),
            "stress_ladder": _load("stress_test.json"),
            "correlation": _load("correlation_report.json"),
            "backtest2022": _load("backtest_2022.json"),
            "backtest_recovery": _load("backtest_recovery.json")}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(snap, open(OUT, "w"))
    nlg = sum(1 for r in snap["rows"] if r.get("in_league"))
    nv = sum(1 for r in snap["rows"] if r.get("val"))
    print(f"wrote {OUT}: {len(snap['rows'])} rows ({nlg} in league, {nv} with valuation), "
          f"{len(snap['matrices'])} matrices, etf_horizon={'y' if snap['etf_horizon'] else 'n'}, "
          f"stress_ladder={'y' if snap['stress_ladder'] else 'n'}, as_of {as_of}")
