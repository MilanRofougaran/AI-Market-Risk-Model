"""
============================================================================
 REGISTRY  --  systemic_model / discovery
============================================================================
 THE MEMORY OF THE SYSTEM.

 This module is what turns the discovery pipeline from a tool you re-run into
 a tool that LEARNS across runs. It maintains a persistent, versioned record
 of every candidate the screen has ever surfaced, stamped by run date, so that
 each new run can:
     - load the previous universe as its starting point (not start cold),
     - compare today's findings against last time, and
     - report the TRAJECTORY of each name: what entered, what exited, what
       moved up the S-curve, and what moved down.

 Why this matters (the reasoning, not just the mechanics):
   A single snapshot tells you where a candidate sits today. Two snapshots
   tell you where it is GOING. In a fast-moving area like AI/semis, the second
   is far more valuable -- a name moving from 3% to 8% TAM penetration between
   runs is consuming its runway, and its fragility profile is shifting in a way
   no single reading can show. The persistent registry is the spine that makes
   every future run more informative than the last.

 STORAGE FORMAT:
   candidate_registry.json holds:
     {
       "runs":   [ {run_id, date, n_candidates, notes}, ... ],   # run log
       "candidates": {
           "<ticker_or_name>": {
               "first_seen": "<run_id>",
               "last_seen":  "<run_id>",
               "sector": "...",
               "history": [ {run_id, date, <all metrics for that run>}, ... ]
           }, ...
       }
     }
   Every metric is stored per-run inside history[], so trajectories are just
   a walk down that list. Nothing is ever overwritten; the registry only grows.

 This file is pure state management -- NO network, NO judgment. It is the safe,
 mechanical layer. The judgment (what counts as a candidate, what the scores
 should be) happens in the discovery stage and at the human checkpoints.
============================================================================
"""
import json, os
from datetime import datetime

REGISTRY_PATH = os.path.join(os.path.dirname(__file__), "candidate_registry.json")


def _empty_registry():
    return {"runs": [], "candidates": {}}


def load_registry(path=REGISTRY_PATH):
    """Load the persistent registry, or return an empty one on first ever run.
    This is the 'previous list as starting point' you asked for: every run
    begins by calling this."""
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return _empty_registry()


def save_registry(reg, path=REGISTRY_PATH):
    with open(path, "w") as f:
        json.dump(reg, f, indent=1)


def start_run(reg, notes=""):
    """Open a new run. Returns the run_id. Runs are numbered sequentially and
    stamped with today's date so trajectories are time-anchored."""
    run_id = f"run_{len(reg['runs'])+1:03d}"
    reg["runs"].append({
        "run_id": run_id,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "n_candidates": None,        # filled in at commit
        "notes": notes,
    })
    return run_id


def record_candidate(reg, run_id, name, sector, metrics):
    """Add (or update) a candidate for the current run. `metrics` is a free dict
    of whatever the discovery stage measured this run -- e.g.
        {growth_pct, tam_bn, penetration, fwd_pe, momentum, conviction, ...}
    Stored as a new entry in the candidate's history, never overwriting prior
    runs, so the full trajectory is preserved.

    No judgment here: this just files whatever the discovery stage decided.
    """
    date = next(r["date"] for r in reg["runs"] if r["run_id"] == run_id)
    cand = reg["candidates"].get(name)
    if cand is None:
        cand = {"first_seen": run_id, "last_seen": run_id, "sector": sector, "history": []}
        reg["candidates"][name] = cand
    cand["last_seen"] = run_id
    cand["sector"] = sector            # allow sector reclassification over time
    entry = {"run_id": run_id, "date": date}
    entry.update(metrics)
    cand["history"].append(entry)


def commit_run(reg, run_id):
    """Close the run: stamp how many candidates it recorded."""
    n = sum(1 for c in reg["candidates"].values()
            if c["history"] and c["history"][-1]["run_id"] == run_id)
    for r in reg["runs"]:
        if r["run_id"] == run_id:
            r["n_candidates"] = n
    return n


# ===========================================================================
#  THE TRAJECTORY ENGINE  --  what makes memory pay off
# ===========================================================================

def compare_runs(reg, run_a, run_b, metric="penetration"):
    """Diff two runs and classify every name. This is the headline output the
    persistent registry exists to produce.

    Returns a dict with four lists:
      entered  : names present in run_b but not run_a (new on the radar)
      exited   : names present in run_a but not run_b (fell off)
      moved_up : names in both whose `metric` rose (consuming runway / momentum)
      moved_down: names in both whose `metric` fell
    Each item carries the before/after values so the size of the move is visible.
    """
    def names_in(run_id):
        return {n for n, c in reg["candidates"].items()
                if any(h["run_id"] == run_id for h in c["history"])}
    def value_in(name, run_id):
        for h in reg["candidates"][name]["history"]:
            if h["run_id"] == run_id:
                return h.get(metric)
        return None

    a, b = names_in(run_a), names_in(run_b)
    entered = sorted(b - a)
    exited  = sorted(a - b)
    both    = a & b
    moved_up, moved_down = [], []
    for n in sorted(both):
        va, vb = value_in(n, run_a), value_in(n, run_b)
        if va is None or vb is None:
            continue
        delta = vb - va
        rec = {"name": n, "from": va, "to": vb, "delta": round(delta, 4)}
        if delta > 1e-9:
            moved_up.append(rec)
        elif delta < -1e-9:
            moved_down.append(rec)
    moved_up.sort(key=lambda r: -r["delta"])
    moved_down.sort(key=lambda r: r["delta"])
    return {"metric": metric, "from_run": run_a, "to_run": run_b,
            "entered": [{"name": n} for n in entered],
            "exited":  [{"name": n} for n in exited],
            "moved_up": moved_up, "moved_down": moved_down}


def trajectory(reg, name, metric="penetration"):
    """The full time series of one metric for one name, across all runs it
    appeared in. This is how you watch a single candidate climb (or stall on)
    its S-curve over time."""
    c = reg["candidates"].get(name)
    if not c:
        return []
    return [{"run_id": h["run_id"], "date": h["date"], "value": h.get(metric)}
            for h in c["history"] if metric in h]


def current_universe(reg, run_id=None):
    """The candidate list as of a given run (default: the latest run). This is
    what you hand to the narrowing checkpoint and, after filtering, to the TAM
    and macro stages."""
    if run_id is None:
        run_id = reg["runs"][-1]["run_id"] if reg["runs"] else None
    if run_id is None:
        return []
    out = []
    for n, c in reg["candidates"].items():
        last = c["history"][-1] if c["history"] else None
        if last and last["run_id"] == run_id:
            out.append({"name": n, "sector": c["sector"],
                        "first_seen": c["first_seen"], **last})
    return out


def print_comparison(diff):
    """Human-readable run-over-run report."""
    print(f"\n=== RUN COMPARISON: {diff['from_run']} -> {diff['to_run']}  "
          f"(metric: {diff['metric']}) ===")
    print(f"  ENTERED ({len(diff['entered'])}): "
          + ", ".join(d["name"] for d in diff["entered"]) or "  ENTERED (0):")
    print(f"  EXITED  ({len(diff['exited'])}): "
          + ", ".join(d["name"] for d in diff["exited"]) or "  EXITED (0):")
    print(f"  MOVED UP ({len(diff['moved_up'])}):")
    for r in diff["moved_up"][:12]:
        print(f"     {r['name']:14s} {r['from']} -> {r['to']}  (+{r['delta']})")
    print(f"  MOVED DOWN ({len(diff['moved_down'])}):")
    for r in diff["moved_down"][:12]:
        print(f"     {r['name']:14s} {r['from']} -> {r['to']}  ({r['delta']})")


if __name__ == "__main__":
    # Self-demo: simulate two runs so the trajectory logic is visible and tested
    # WITHOUT any network. This proves the state layer works before we wire in
    # real research.
    reg = _empty_registry()

    r1 = start_run(reg, notes="demo run 1")
    record_candidate(reg, r1, "NVIDIA",  "AI/semis", {"penetration": 0.39, "growth_pct": 66})
    record_candidate(reg, r1, "AMD",     "AI/semis", {"penetration": 0.03, "growth_pct": 32})
    record_candidate(reg, r1, "Marvell", "AI/semis", {"penetration": 0.06, "growth_pct": 42})
    commit_run(reg, r1)

    r2 = start_run(reg, notes="demo run 2 (one quarter later)")
    record_candidate(reg, r2, "NVIDIA",  "AI/semis", {"penetration": 0.42, "growth_pct": 60})
    record_candidate(reg, r2, "AMD",     "AI/semis", {"penetration": 0.07, "growth_pct": 50})  # moved up
    record_candidate(reg, r2, "Credo",   "AI/semis", {"penetration": 0.05, "growth_pct": 120}) # entered
    # Marvell not recorded -> it exited this run
    commit_run(reg, r2)

    print("Registry self-demo (no network):")
    print(f"  runs: {[r['run_id'] for r in reg['runs']]}")
    print(f"  universe now: {[c['name'] for c in current_universe(reg)]}")
    diff = compare_runs(reg, r1, r2, metric="penetration")
    print_comparison(diff)
    print("\n  AMD penetration trajectory:", trajectory(reg, "AMD", "penetration"))
    print("\nState layer works. (This demo data is illustrative, not real.)")
