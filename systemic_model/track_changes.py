"""
============================================================================
 TRACK_CHANGES  --  systemic_model
============================================================================
 THE LEDGER. drift_report.py answers "what changed since yesterday?". This adds
 the longer memory: "what has drifted over the past MONTH?" -- because the
 dangerous changes are often slow. No single day trips a flag, but penetration
 creeps, a multiple expands, recovery-quality slides, and a month later the
 picture is materially different.

 Every run appends a compact snapshot to drift_history.json:
     date, macro dashboard, and per-company {fragility, recovery_quality,
     permanent-loss prob, penetration}.

 cumulative(window) then compares the latest snapshot to the EARLIEST one in
 the window and flags metrics whose TOTAL drift over the period is material --
 explicitly labeling the ones that drifted slowly (no single-day flag) so you
 see the creep the daily check would miss.

 Usage:
   python3 track_changes.py --record      # append current results.json to history
   python3 track_changes.py --window 30   # cumulative drift over last 30 days
   python3 track_changes.py --export       # dump series JSON for the visual

 RESEARCH MODEL, NOT INVESTMENT ADVICE.
============================================================================
"""
import argparse
import datetime as dt
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results.json")
HISTORY = os.path.join(HERE, "drift_history.json")

# Cumulative-drift thresholds (over the whole window). A metric must move at
# least this much across the period to be reported; 2x this = "major".
CUM = dict(macro_pct=0.12, rate_abs=0.30,
           fragility=0.05, recovery_quality=0.05, permanent=0.04, pen=0.02)
LINES = dict(fragility_high=0.40, permanent_high=0.30)
RATE_FIELDS = {"ust_10y", "ust_10y_real", "fed_funds_mid", "core_pce_yoy",
               "equity_risk_premium"}
COMPANY_METRICS = ("fragility", "recovery_quality", "p_deep_permanent", "pen")


def _load_history():
    if os.path.exists(HISTORY):
        with open(HISTORY) as f:
            return json.load(f)
    return {"history": []}


def _save_history(h):
    with open(HISTORY, "w") as f:
        json.dump(h, f, indent=1)


def snapshot_from_results(results, date=None):
    """Extract the compact tracked metrics from a results.json structure."""
    date = date or results.get("as_of") or dt.date.today().isoformat()
    rc = results["companies"]["recovery_cond"]
    dec = results["companies"].get("decomposition", {})
    comps = {}
    for nm, c in rc.items():
        comps[nm] = {
            "fragility": c.get("fragility"),
            "recovery_quality": c.get("recovery_quality"),
            "p_deep_permanent": c.get("p_deep_permanent"),
            "pen": dec.get(nm, {}).get("pen"),
        }
    return {"date": date, "macro": results.get("macro", {}), "companies": comps}


def record(date=None):
    with open(RESULTS) as f:
        results = json.load(f)
    snap = snapshot_from_results(results, date=date)
    h = _load_history()
    # replace any existing entry with the same date (idempotent daily run)
    h["history"] = [e for e in h["history"] if e["date"] != snap["date"]]
    h["history"].append(snap)
    h["history"].sort(key=lambda e: e["date"])
    _save_history(h)
    print(f"Recorded snapshot for {snap['date']} "
          f"({len(h['history'])} entries in history).")


def _window(h, days):
    if not h["history"]:
        return []
    latest = dt.date.fromisoformat(h["history"][-1]["date"])
    cutoff = latest - dt.timedelta(days=days)
    return [e for e in h["history"] if dt.date.fromisoformat(e["date"]) >= cutoff]


def _max_step(series):
    """Largest single-step absolute change in a numeric series (to tell slow
    drift from a one-day jump). COMPACT the series first (drop None) rather than
    skipping any pair that touches a None — otherwise a skipped snapshot (e.g. a
    weekend the cron didn't run: [0.10, None, 0.15]) would drop BOTH adjacent
    steps and silently hide the 0.10->0.15 creep. (Gemini bug D.)"""
    valid = [x for x in series if x is not None]
    steps = [abs(valid[i] - valid[i - 1]) for i in range(1, len(valid))]
    return max(steps) if steps else 0.0


def cumulative(days=30):
    h = _load_history()
    win = _window(h, days)
    if len(win) < 2:
        print(f"Need at least 2 snapshots in the last {days} days "
              f"(have {len(win)}). Keep running daily; the ledger builds up.")
        return None
    first, last = win[0], win[-1]
    span = f"{first['date']} -> {last['date']}  ({len(win)} snapshots)"
    print("#" * 78)
    print(f"#  CUMULATIVE DRIFT  ·  last {days} days   ({span})")
    print("#  catches slow creep the daily check misses. RESEARCH MODEL, NOT ADVICE")
    print("#" * 78)

    out = {"span": span, "macro": [], "companies": [], "attention": []}

    # ---- macro cumulative ----
    macro_hits = []
    for k, v1 in (last["macro"] or {}).items():
        v0 = (first["macro"] or {}).get(k)
        if not isinstance(v1, (int, float)) or not isinstance(v0, (int, float)):
            continue
        series = [e["macro"].get(k) for e in win if isinstance(e["macro"].get(k), (int, float))]
        if k in RATE_FIELDS:
            d = v1 - v0
            if abs(d) >= CUM["rate_abs"]:
                macro_hits.append((k, v0, v1, d, _max_step(series), "pts"))
        else:
            if v0 and abs(v1 - v0) / abs(v0) >= CUM["macro_pct"]:
                macro_hits.append((k, v0, v1, (v1 - v0) / v0, _max_step(series) / abs(v0), "%"))
    if macro_hits:
        print("\nMACRO drift over the window:")
        for k, v0, v1, d, step, unit in macro_hits:
            slow = " (slow creep — no single-day flag)" if (
                unit == "%" and step < 0.08) or (unit == "pts" and step < 0.20) else ""
            dd = f"{d*100:+.0f}%" if unit == "%" else f"{d:+.2f} pts"
            print(f"  - {k}: {v0:g} -> {round(v1,2):g}  ({dd}){slow}")
            out["macro"].append(dict(field=k, frm=v0, to=round(v1, 3), delta=d, unit=unit))

    # ---- company cumulative ----
    print("\nCOMPANY drift over the window:")
    any_co = False
    for nm in last["companies"]:
        c1 = last["companies"][nm]
        c0 = first["companies"].get(nm)
        if not c0:
            continue
        notes, attn = [], []
        for m in COMPANY_METRICS:
            a, b = c0.get(m), c1.get(m)
            if a is None or b is None:
                continue
            thr = CUM["permanent"] if m == "p_deep_permanent" else CUM.get(m, 0.05)
            d = b - a
            if abs(d) >= thr:
                series = [e["companies"].get(nm, {}).get(m) for e in win]
                step = _max_step([x for x in series if x is not None])
                slow = step < thr * 0.6
                tag = "MAJOR" if abs(d) >= 2 * thr else "notable"
                label = {"fragility": "fragility", "recovery_quality": "recov-quality",
                         "p_deep_permanent": "perm-loss", "pen": "penetration"}[m]
                notes.append(f"{label} {a*100:.0f}%->{b*100:.0f}% ({d*100:+.0f}pp"
                             + (", slow creep" if slow else "") + f", {tag})")
                # attention: crossed an absolute danger line over the window
                if m == "fragility" and a < LINES["fragility_high"] <= b:
                    attn.append("crossed INTO fragile (>40%)")
                if m == "p_deep_permanent" and a < LINES["permanent_high"] <= b:
                    attn.append("crossed INTO elevated permanent-loss (>30%)")
                if tag == "MAJOR":
                    attn.append(f"{label} {tag} move {d*100:+.0f}pp")
        # "approaching a danger line" — within 2pp below and trending up
        fb, fa = c1.get("fragility"), c0.get("fragility")
        if fb is not None and fa is not None and fb > fa and \
                LINES["fragility_high"] - 0.02 <= fb < LINES["fragility_high"]:
            attn.append(f"approaching fragile line ({LINES['fragility_high']*100:.0f}%), now {fb*100:.0f}%")
        pb, pa = c1.get("p_deep_permanent"), c0.get("p_deep_permanent")
        if pb is not None and pa is not None and pb > pa and \
                LINES["permanent_high"] - 0.02 <= pb < LINES["permanent_high"]:
            attn.append(f"approaching elevated permanent-loss ({LINES['permanent_high']*100:.0f}%), now {pb*100:.0f}%")
        if notes:
            any_co = True
            print(f"  - {nm}: " + "; ".join(notes))
            out["companies"].append(dict(name=nm, notes=notes, attention=attn))
            for a in attn:
                out["attention"].append(f"{nm}: {a}")
    if not any_co:
        print("  (no company metric drifted past its cumulative threshold)")

    # ---- attention summary ----
    print("\nATTENTION (changes worth acting on):")
    if out["attention"]:
        for a in out["attention"]:
            print(f"  ** {a}")
    else:
        print("  none — drift is within normal range, but keep watching the trends above.")
    print()
    return out


def export_series(days=60):
    """Dump the time series for the visual: dates + a few key metrics."""
    h = _load_history()
    win = _window(h, days)
    dates = [e["date"] for e in win]
    macro_keys = ["vix", "brent_usd", "ust_10y_real", "shiller_cape"]
    series = {"dates": dates, "macro": {}, "companies": {}}
    for k in macro_keys:
        series["macro"][k] = [e["macro"].get(k) for e in win]
    names = win[-1]["companies"].keys() if win else []
    for nm in names:
        series["companies"][nm] = {
            m: [e["companies"].get(nm, {}).get(m) for e in win]
            for m in ("fragility", "p_deep_permanent")
        }
    print(json.dumps(series))
    return series


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", action="store_true", help="Append current run to history.")
    ap.add_argument("--window", type=int, default=None, help="Cumulative drift over N days.")
    ap.add_argument("--export", action="store_true", help="Print series JSON for the visual.")
    ap.add_argument("--date", default=None, help="Override the snapshot date (for backfill).")
    args = ap.parse_args()
    if args.record:
        record(date=args.date)
    if args.window:
        cumulative(days=args.window)
    if args.export:
        export_series()
    if not (args.record or args.window or args.export):
        cumulative(days=30)
