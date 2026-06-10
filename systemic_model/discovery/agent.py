"""
============================================================================
 AGENT  --  systemic_model / discovery
============================================================================
 THE ORCHESTRATION LAYER. This is the "agent": a single controller that drives
 the whole discovery -> narrow -> macro -> TAM -> model pipeline, automating
 everything mechanical and PAUSING at the points where trustworthiness depends
 on human judgment.

 Read this docstring carefully -- it is the honest description of what this
 agent is and is not.

 WHAT IS AUTOMATED (runs with no human, every time):
   - loading the previous candidate list from the registry (warm start)
   - structuring and issuing the research queries for each stage
   - parsing results into the registry with date stamps
   - computing trajectories and run-over-run diffs
   - scoring candidates against the FIXED, AUDITABLE rules in screen_rules.py
   - the red-team FILTER: mechanically flagging hype markers, single-source
     claims, and decimal-precision-on-judgment so they cannot pass silently
   - pouring the surviving universe into the model's calibration

 WHAT IS A HUMAN CHECKPOINT (the agent stops and asks):
   - CHECKPOINT 1 (narrow): after discovery ranks the universe, a human
     confirms or edits the shortlist before expensive TAM work begins.
   - CHECKPOINT 2 (red-team adjudication): where the automated filter flags a
     claim as suspicious, a human decides keep / reject / verify. The agent
     CANNOT decide on its own that a confident-looking number is actually a
     category error -- that judgment is exactly what made this project work.
   - CHECKPOINT 3 (model sign-off): before the model's conclusions are treated
     as final, a human reviews the sensitivity sweep and the assumptions.

 WHY THE CHECKPOINTS EXIST (not a limitation -- the whole point):
   A fully autonomous agent gathers data well but exercises SKEPTICISM badly.
   When it is wrong it is wrong in the same confident tone it uses when right,
   and there is no seam to catch it. The checkpoints ARE that seam. This design
   is automated where automation is safe and paused where judgment is essential.

 HOW IT IS DRIVEN:
   This controller does not call the network itself. It produces a STAGE PLAN
   -- an explicit, ordered list of what to research and what rule to apply --
   which the operating session (Claude, with the search tools) executes,
   feeding results back via the record_* functions. That keeps the agent's
   logic testable offline and keeps the live research observable rather than
   hidden inside an opaque loop.
============================================================================
"""
import json, os
from datetime import datetime
import registry as R

HERE = os.path.dirname(__file__)


# ===========================================================================
#  STAGE DEFINITIONS  --  the fixed pipeline the agent walks every run
# ===========================================================================

STAGES = [
    dict(id="discovery", kind="automated",
         desc="Broad, whole-market high-growth screen. Ranks candidates; "
              "carries forward 3-5 ETFs and 6-8 stocks.",
         output="ranked candidate universe -> registry"),
    dict(id="narrow", kind="CHECKPOINT",
         desc="Human confirms/edits the shortlist before TAM work. Tests the "
              "AI/semis-foundation hypothesis against the evidence."),
    dict(id="macro", kind="automated",
         desc="Defined checklist of systemic factors (debt, rates, credit, "
              "valuation, liquidity, policy). Feeds regime probabilities.",
         output="macro dashboard -> calibration.MACRO"),
    dict(id="tam", kind="automated",
         desc="TAM/SAM + penetration for the survivors, using the existing "
              "premium-decomposition framework.",
         output="company TAM data -> calibration.COMPANIES"),
    dict(id="redteam", kind="CHECKPOINT",
         desc="Human adjudicates every claim the automated filter flagged: "
              "keep / reject / verify. Strips false precision and category errors."),
    dict(id="model", kind="automated",
         desc="Run engine.py on the freshly calibrated inputs; produce tables, "
              "sensitivity sweep, dominance sweep.",
         output="results.json + dominance_sweep.json"),
    dict(id="signoff", kind="CHECKPOINT",
         desc="Human reviews sensitivity ranges and assumptions before the "
              "conclusions are treated as final. Manage to the range, not the decimal."),
]

# Output-size targets you set:
TARGETS = {"etfs": (3, 5), "stocks": (6, 8)}


# ===========================================================================
#  THE STAGE PLAN  --  what the agent hands the operating session each run
# ===========================================================================

def build_stage_plan(scope="whole-market growth screen, AI/semis as hypothesis to test"):
    """Produce the explicit, ordered plan for this run. The operating session
    executes the 'automated' stages with the search tools and presents the
    'CHECKPOINT' stages to the human. Nothing here touches the network; it is
    the agent's reasoning made visible and auditable."""
    reg = R.load_registry()
    prev = R.current_universe(reg)
    plan = {
        "run_date": datetime.now().strftime("%Y-%m-%d"),
        "scope": scope,
        "targets": TARGETS,
        "warm_start": {
            "have_previous_list": bool(prev),
            "previous_count": len(prev),
            "previous_names": [c["name"] for c in prev],
            "note": ("Begin from these and diff against them."
                     if prev else "First ever run -- no previous list; start cold."),
        },
        "stages": STAGES,
    }
    return plan


def print_stage_plan(plan):
    print("#" * 74)
    print(f"#  DISCOVERY AGENT  --  STAGE PLAN  ({plan['run_date']})")
    print(f"#  scope: {plan['scope']}")
    print(f"#  targets: {plan['targets']['etfs'][0]}-{plan['targets']['etfs'][1]} ETFs, "
          f"{plan['targets']['stocks'][0]}-{plan['targets']['stocks'][1]} stocks")
    print("#" * 74)
    ws = plan["warm_start"]
    if ws["have_previous_list"]:
        print(f"\nWARM START: {ws['previous_count']} candidates from last run -> "
              f"{ws['previous_names']}")
        print("  The agent will diff today's findings against these.")
    else:
        print("\nCOLD START: no previous list. This run establishes the baseline.")
    print("\nPIPELINE:")
    for i, s in enumerate(plan["stages"], 1):
        tag = "  [AUTO]    " if s["kind"] == "automated" else "  [HUMAN!] "
        print(f"{tag}{i}. {s['id'].upper():10s} {s['desc']}")
        if s.get("output"):
            print(f"             -> {s['output']}")
    print("\n  [AUTO]   = runs with no human, every time")
    print("  [HUMAN!] = agent stops and asks; this is where trustworthiness lives")


# ===========================================================================
#  THE AUTOMATED RED-TEAM FILTER  --  mechanical, not judgment
#  Flags claims for human adjudication. It does NOT decide truth; it decides
#  what a human must look at. This is the automatable half of skepticism.
# ===========================================================================

HYPE_MARKERS = ["guaranteed", "can't lose", "to the moon", "infinite", "no risk",
                "sure thing", "explosive", "skyrocket", "100% certain"]

def redteam_filter(claim_text, sources=None, has_decimal_precision=False,
                   is_forward_projection=False):
    """Mechanically flag a research claim for human review. Returns a dict of
    flags; an empty flag set means 'no automatic concern' (still reviewable).

    The rules are deliberately simple and fixed, so they are auditable:
      - hype language        -> flag
      - single / no source   -> flag (claims need corroboration)
      - decimal precision on  -> flag (false precision, as with the TDVM tables)
        a forward projection
    """
    flags = []
    low = (claim_text or "").lower()
    if any(m in low for m in HYPE_MARKERS):
        flags.append("hype_language")
    if not sources or len(sources) < 2:
        flags.append("needs_corroboration")
    if has_decimal_precision and is_forward_projection:
        flags.append("false_precision_on_projection")
    return {"claim": claim_text, "flags": flags,
            "needs_human": bool(flags)}


# ===========================================================================
#  RECORDING HELPERS  --  the operating session calls these as it executes
# ===========================================================================

def open_run(notes=""):
    reg = R.load_registry()
    run_id = R.start_run(reg, notes=notes)
    R.save_registry(reg)
    return run_id

def record_discovery(run_id, candidates):
    """candidates: list of dicts {name, sector, kind('etf'|'stock'), metrics{...}}.
    Files each into the registry under this run."""
    reg = R.load_registry()
    for c in candidates:
        m = dict(c.get("metrics", {})); m["kind"] = c.get("kind", "stock")
        R.record_candidate(reg, run_id, c["name"], c.get("sector", "?"), m)
    n = R.commit_run(reg, run_id)
    R.save_registry(reg)
    return n

def diff_against_previous(run_id, metric="growth_pct"):
    """After discovery, diff this run against the immediately previous run."""
    reg = R.load_registry()
    runs = [r["run_id"] for r in reg["runs"]]
    if len(runs) < 2:
        return None
    prev = runs[runs.index(run_id) - 1]
    return R.compare_runs(reg, prev, run_id, metric=metric)


if __name__ == "__main__":
    # Show the stage plan for the next run (warm or cold), and self-test the filter.
    plan = build_stage_plan()
    print_stage_plan(plan)

    print("\n--- red-team filter self-test ---")
    for t, src, dec, fwd in [
        ("AI chip TAM reaches $500B by 2028", ["Deloitte", "AMD IR"], False, True),
        ("This stock will skyrocket, guaranteed", ["blog"], True, True),
        ("HBM market $35B in 2025", ["Micron IR"], False, False),
    ]:
        f = redteam_filter(t, src, dec, fwd)
        print(f"  {'FLAG' if f['needs_human'] else 'ok  '}  {f['flags']}  <- {t}")
