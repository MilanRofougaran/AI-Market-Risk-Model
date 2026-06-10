"""
============================================================================
 DRIFT_REPORT  --  systemic_model
============================================================================
 THE "ARE THE NUMBERS STILL GOOD?" CHECK.

 Re-running the model produces the same answer until an INPUT changes. This
 script compares the latest run against a saved baseline and reports only what
 MATERIALLY MOVED -- so a daily/recurring run is quiet when nothing changed and
 loud exactly when something did.

 What it watches:
   - MACRO dashboard   : VIX, rates, oil, credit, valuation -> regime risk
   - per-company       : fragility, recovery-quality, permanent-loss prob,
                         penetration (runway being consumed)
   - threshold crossings: a name crossing into "fragile" or "permanent-loss
                         elevated" territory since last time
   - the discovery registry: names that entered / exited / moved up the curve

 Usage:
   python3 drift_report.py --snapshot      # save current results.json as baseline
   python3 drift_report.py                 # compare current vs baseline, report drift

 The scheduled daily run does: refresh inputs -> run model -> drift_report ->
 snapshot. So each day is compared to the day before. RESEARCH MODEL, NOT ADVICE.
============================================================================
"""
import argparse
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "discovery"))

RESULTS = os.path.join(HERE, "results.json")
BASELINE = os.path.join(HERE, "results_baseline.json")

# Materiality thresholds -- below these, a change is noise and is NOT reported.
THRESH = dict(
    macro_pct=0.08,          # macro field moved > 8% (relative)
    rate_abs=0.20,           # ...or a rate moved > 0.20 (absolute pts)
    fragility_pp=0.05,       # fragility moved > 5 percentage points
    recovery_pp=0.05,        # recovery-quality moved > 5 pp
    permanent_pp=0.03,       # permanent-loss prob moved > 3 pp
    penetration_pp=0.02,     # penetration moved > 2 pp (runway consumed)
)
# Absolute lines that, once crossed, are always worth a flag.
LINES = dict(fragility_high=0.40, permanent_high=0.30)

# Macro fields that are rates (compared in absolute pts, not %).
RATE_FIELDS = {"ust_10y", "ust_10y_real", "fed_funds_mid", "core_pce_yoy",
               "equity_risk_premium"}


def _load(p):
    with open(p) as f:
        return json.load(f)


def snapshot():
    if not os.path.exists(RESULTS):
        print("No results.json to snapshot. Run the model first.")
        return
    shutil.copyfile(RESULTS, BASELINE)
    print(f"Snapshot saved: {os.path.basename(BASELINE)}")


def _macro_drift(cur, base):
    out = []
    for k, v in (cur.get("macro") or {}).items():
        b = (base.get("macro") or {}).get(k)
        if b is None or not isinstance(v, (int, float)) or not isinstance(b, (int, float)):
            if b is not None and v != b:
                out.append(f"{k}: {b} -> {v}")
            continue
        if k in RATE_FIELDS:
            if abs(v - b) >= THRESH["rate_abs"]:
                out.append(f"{k}: {b:g} -> {v:g}  ({v-b:+.2f} pts)")
        else:
            if b != 0 and abs(v - b) / abs(b) >= THRESH["macro_pct"]:
                out.append(f"{k}: {b:g} -> {round(v,2):g}  ({(v-b)/b*100:+.0f}%)")
    return out


def _company_drift(cur, base):
    out = []
    cc = cur["companies"]["recovery_cond"]
    bc = base["companies"]["recovery_cond"]
    for nm, c in cc.items():
        b = bc.get(nm)
        if b is None:
            out.append((nm, "NEW in model universe", []))
            continue
        notes = []
        df = c["fragility"] - b["fragility"]
        if abs(df) >= THRESH["fragility_pp"]:
            notes.append(f"fragility {b['fragility']*100:.0f}%->{c['fragility']*100:.0f}% ({df*100:+.0f}pp)")
        drq = c["recovery_quality"] - b["recovery_quality"]
        if abs(drq) >= THRESH["recovery_pp"]:
            notes.append(f"recovery-quality {b['recovery_quality']*100:.0f}%->{c['recovery_quality']*100:.0f}% ({drq*100:+.0f}pp)")
        if "p_deep_permanent" in c and "p_deep_permanent" in b:
            dp = c["p_deep_permanent"] - b["p_deep_permanent"]
            if abs(dp) >= THRESH["permanent_pp"]:
                notes.append(f"permanent-loss {b['p_deep_permanent']*100:.0f}%->{c['p_deep_permanent']*100:.0f}% ({dp*100:+.0f}pp)")
        # absolute line crossings (only flag the crossing direction)
        if b["fragility"] < LINES["fragility_high"] <= c["fragility"]:
            notes.append(f"** crossed INTO fragile (>{LINES['fragility_high']*100:.0f}%)")
        if c.get("p_deep_permanent", 0) and b.get("p_deep_permanent", 0):
            if b["p_deep_permanent"] < LINES["permanent_high"] <= c["p_deep_permanent"]:
                notes.append(f"** crossed INTO elevated permanent-loss (>{LINES['permanent_high']*100:.0f}%)")
        if notes:
            out.append((nm, None, notes))
    return out


def _registry_drift():
    """Use the persistent registry to report entered/exited/penetration moves."""
    try:
        import registry as R
    except Exception:
        return None
    reg = R.load_registry()
    runs = [r["run_id"] for r in reg.get("runs", [])]
    if len(runs) < 2:
        return None
    diff = R.compare_runs(reg, runs[-2], runs[-1], metric="penetration")
    return diff


def report():
    if not os.path.exists(BASELINE):
        print("No baseline yet. Run with --snapshot once to establish one.")
        return
    cur, base = _load(RESULTS), _load(BASELINE)
    print("#" * 76)
    print("#  DRIFT REPORT   ·   current run vs baseline")
    print(f"#  baseline as_of {base.get('as_of')}   ->   current as_of {cur.get('as_of')}")
    print("#" * 76)

    any_change = False

    macro = _macro_drift(cur, base)
    if macro:
        any_change = True
        print("\nMACRO shifts (regime-risk inputs):")
        for m in macro:
            print(f"  - {m}")

    comp = _company_drift(cur, base)
    if comp:
        any_change = True
        print("\nCOMPANY changes:")
        for nm, tag, notes in comp:
            if tag:
                print(f"  - {nm}: {tag}")
            else:
                print(f"  - {nm}: " + "; ".join(notes))

    diff = _registry_drift()
    if diff and (diff["entered"] or diff["exited"] or diff["moved_up"] or diff["moved_down"]):
        any_change = True
        print(f"\nDISCOVERY registry ({diff['from_run']} -> {diff['to_run']}, penetration):")
        if diff["entered"]:
            print("  entered: " + ", ".join(d["name"] for d in diff["entered"]))
        if diff["exited"]:
            print("  exited:  " + ", ".join(d["name"] for d in diff["exited"]))
        for r in diff["moved_up"][:8]:
            print(f"  up:   {r['name']} {r['from']}->{r['to']} (+{r['delta']})")
        for r in diff["moved_down"][:8]:
            print(f"  down: {r['name']} {r['from']}->{r['to']} ({r['delta']})")

    if not any_change:
        print("\n  No material drift since baseline. Numbers still hold.")
    print()
    return any_change


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", action="store_true",
                    help="Save current results.json as the comparison baseline.")
    args = ap.parse_args()
    if args.snapshot:
        snapshot()
    else:
        report()
