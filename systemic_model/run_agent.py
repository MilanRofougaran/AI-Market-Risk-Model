"""
============================================================================
 RUN_AGENT  --  systemic_model
============================================================================
 THE SINGLE END-TO-END AGENT.

 One command runs the whole thing:  python3 run_agent.py

 It chains the two halves of the system that until now lived in separate
 scripts, and ties their outputs together:

     STAGE 1  DISCOVERY  (discovery/)  -- screen + score + rank the candidate
                universe, warm-started from the persistent registry, and diff
                this run against the previous one (what entered / exited /
                moved up the S-curve).

     STAGE 2  ANALYSIS  (engine.py)   -- run the regime-switching Monte Carlo
                on the calibrated companies: drawdown exceedance, conditional
                recovery, premium decomposition, and the judgment-score
                sensitivity sweep.

     STAGE 3  CONSOLIDATE             -- cross-reference the two: for every
                modeled company, show its discovery rank/score beside its
                model fragility and recovery conclusion, and flag the gaps
                (discovery picks not yet modeled; modeled names not surfaced
                by the screen). Writes one consolidated report.

 OUTPUTS (all in the package dir):
     results.json            -- full model output (same schema as run.py)
     discovery_report.json   -- ranked shortlist + run-over-run diff
     consolidated_report.json-- the joined discovery+analysis view
     consolidated_report.md   -- the same, human-readable

 DESIGN NOTE -- the checkpoints are preserved, not removed.
   The original agent.py defines three human checkpoints (narrow, red-team,
   sign-off) because a fully autonomous loop gathers data well but exercises
   skepticism badly. This driver RUNS straight through by default (so you get
   discovery -> analysis -> results in one go), but at each checkpoint it
   PRINTS the question a human should answer and records it in the report
   under "checkpoints_for_review". Use --pause to stop at each one. Nothing
   here invents new candidates from the network; adding names to the universe
   is still a researched, human step (feed them with --candidates).

 RESEARCH MODEL, NOT INVESTMENT ADVICE.
============================================================================
"""
import argparse
import copy
import json
import os
import sys
from datetime import datetime

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DISCOVERY_DIR = os.path.join(HERE, "discovery")
# discovery/ holds registry.py, screen_rules.py, agent.py -- put both the
# package dir and discovery/ on the path BEFORE importing from them.
for _p in (HERE, DISCOVERY_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import calibration as C
import engine as E
import registry as R
import screen_rules as SR
import agent as DA  # the discovery agent (stage plan + red-team filter)
import tam_bridge as TB  # discovery -> model TAM bridge (incl. ETF-from-holdings)
import run as RUN   # reuse the model's print + clean helpers


# ---------------------------------------------------------------------------
#  small utilities
# ---------------------------------------------------------------------------
def _clean(o):
    """numpy -> json-native (mirrors run.py's clean)."""
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(x) for x in o]
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    return o


def _banner(title):
    print("\n" + "#" * 74)
    print(f"#  {title}")
    print("#" * 74)


def _checkpoint(cp_log, name, question, pause):
    """Surface a human checkpoint: record it, print it, optionally block."""
    cp_log.append({"checkpoint": name, "question": question})
    tag = "  [HUMAN CHECKPOINT]"
    print(f"\n{tag}  {name.upper()}")
    print(f"      {question}")
    if pause and sys.stdin.isatty():
        try:
            input("      -- press Enter to continue (Ctrl-C to stop) -- ")
        except (EOFError, KeyboardInterrupt):
            print("\n  Stopped at checkpoint by user.")
            sys.exit(0)


# ===========================================================================
#  STAGE 1 -- DISCOVERY
# ===========================================================================
def stage_discovery(candidates_path=None, notes="", pause=False, cp_log=None):
    """Score and rank the candidate universe, record the run, and diff against
    the previous run. Two sources of candidates:

      * --candidates FILE : a JSON list of fresh candidate dicts (researched
        externally). These open a NEW run and are recorded into the registry.
      * (default)         : re-score the CURRENT universe already in the
        registry (the warm-start list), without opening a new run.
    """
    _banner("STAGE 1 / 3   DISCOVERY")

    reg = R.load_registry()
    plan = DA.build_stage_plan()
    DA.print_stage_plan(plan)

    opened_run = None
    if candidates_path:
        with open(candidates_path) as f:
            fresh = json.load(f)
        run_id = DA.open_run(notes=notes or f"run via run_agent {plan['run_date']}")
        reg = R.load_registry()
        for c in fresh:
            m = {k: c[k] for k in c
                 if k not in ("name", "sector", "kind")}
            m["kind"] = c.get("kind", "stock")
            R.record_candidate(reg, run_id, c["name"], c.get("sector", "?"), m)
        R.commit_run(reg, run_id)
        R.save_registry(reg)
        opened_run = run_id
        universe = R.current_universe(reg, run_id)
        print(f"\nRecorded fresh candidates as {run_id} "
              f"({len(universe)} names).")
    else:
        universe = R.current_universe(reg)
        if not universe:
            print("\nNo candidates in the registry and no --candidates file. "
                  "Nothing to discover. Seed first with discovery/first_run.py "
                  "or pass --candidates.")
            return {"shortlist_etfs": [], "shortlist_stocks": [], "diff": None,
                    "universe": []}, reg
        print(f"\nWARM RE-SCORE: scoring the current universe of "
              f"{len(universe)} candidates from the registry "
              f"(no new run opened; pass --candidates to add fresh names).")

    # ---- score + rank with the auditable screen rules ----
    etfs = SR.rank(universe, kind="etf")
    stocks = SR.rank(universe, kind="stock")
    n_e, n_s = DA.TARGETS["etfs"], DA.TARGETS["stocks"]

    print("\n" + "=" * 74)
    print(f"RANKED ETF CANDIDATES   (top {n_e[0]}-{n_e[1]} carried forward)")
    print("=" * 74)
    for i, c in enumerate(etfs, 1):
        star = " *" if i <= n_e[1] else "  "
        print(f"{star}{i:2d}. {SR.explain(c)}   [{c.get('sector','?')}]")

    print("\n" + "=" * 74)
    print(f"RANKED STOCK CANDIDATES (top {n_s[0]}-{n_s[1]} carried forward)")
    print("=" * 74)
    for i, c in enumerate(stocks, 1):
        star = " *" if i <= n_s[1] else "  "
        print(f"{star}{i:2d}. {SR.explain(c)}   [{c.get('sector','?')}]")

    shortlist_etfs = etfs[: n_e[1]]
    shortlist_stocks = stocks[: n_s[1]]

    # ---- run-over-run diff (the payoff of the persistent registry) ----
    diff = None
    runs = [r["run_id"] for r in reg["runs"]]
    if len(runs) >= 2:
        a, b = runs[-2], runs[-1]
        diff = R.compare_runs(reg, a, b, metric="penetration")
        R.print_comparison(diff)
    else:
        print("\n(Only one run on record -- no run-over-run diff yet. The next "
              "run will produce a trajectory.)")

    # ---- CHECKPOINT 1: narrow ----
    _checkpoint(cp_log, "narrow",
                "Confirm or edit the shortlist above before the (expensive) "
                "analysis stage. Does the AI/semis-foundation hypothesis still "
                "hold against this run's evidence?", pause)

    def _slim(c):
        return {"name": c["name"], "sector": c.get("sector", "?"),
                "kind": c.get("kind", "stock"), "score": c["score"],
                "components": c.get("_score_components", {})}

    report = {
        "run_date": plan["run_date"],
        "opened_run": opened_run,
        "targets": DA.TARGETS,
        "shortlist_etfs": [_slim(c) for c in shortlist_etfs],
        "shortlist_stocks": [_slim(c) for c in shortlist_stocks],
        "all_ranked_etfs": [_slim(c) for c in etfs],
        "all_ranked_stocks": [_slim(c) for c in stocks],
        "diff": _clean(diff) if diff else None,
    }
    with open(os.path.join(HERE, "discovery_report.json"), "w") as f:
        json.dump(report, f, indent=1)
    print("\nSaved discovery_report.json")
    return report, reg


# ===========================================================================
#  STAGE 1.5 -- TAM BRIDGE  (the automatable half of the TAM & SAM stage)
#  Turn discovery picks that lack model inputs into priceable companies, and
#  MERGE them into calibration.COMPANIES so the engine scores them too. ETFs
#  get a TAM defined from their holdings; pre-earnings names are flagged.
# ===========================================================================
def stage_bridge(cp_log=None):
    _banner("STAGE 1.5   TAM BRIDGE  (discovery picks -> priceable companies)")
    before = set(C.COMPANIES.keys())
    new, etf_info = TB.build_company_universe(base_companies=C.COMPANIES,
                                              verbose=True)
    # merge in (without clobbering an existing hand-calibrated name)
    added = []
    for nm, spec in new.items():
        if nm not in C.COMPANIES:
            C.COMPANIES[nm] = spec
            added.append(nm)
    print(f"\n  added {len(added)} names to the model universe: {added or 'none'}")
    print(f"  (existing {len(before)} kept as-is; engine now prices "
          f"{len(C.COMPANIES)} names total)")
    if TB.PRE_EARNINGS & set(added):
        flagged = sorted(TB.PRE_EARNINGS & set(added))
        _checkpoint(cp_log, "redteam_pre_earnings",
                    f"{flagged} have no real earnings; their forward P/E is a "
                    f"sentinel, so the model will show their premium as almost "
                    f"entirely floating (max fragility). Confirm you want them "
                    f"priced rather than held out.", False)
    return added, etf_info


def stage_analysis(n_paths=None, pause=False, cp_log=None):
    _banner("STAGE 2 / 3   ANALYSIS  (regime-switching Monte Carlo)")

    if n_paths:
        C.SIM["n_paths"] = int(n_paths)
        import importlib
        importlib.reload(E)  # pick up the new path count cleanly
    print(f"  paths: {C.SIM['n_paths']:,}   horizons: {C.HORIZON_LABELS}   "
          f"mandate: {int(C.MANDATE_MONTHS)}m")

    print("\n[1/3] Broad-exposure Monte Carlo ...")
    eres, thr = E.run_exposures(verbose=True)
    RUN.print_exposure_tables(eres, thr)
    RUN.print_recovery_table(eres)

    print("[2/3] TAM-adjusted company Monte Carlo ...")
    cres, cthr = E.run_companies(verbose=True)
    RUN.print_company_tables(cres, cthr)

    print("[3/3] Sensitivity sweep + reconciliation ...")
    rankings = RUN.sensitivity_sweep()
    RUN.reconciliation_note()

    results = {
        "as_of": C.AS_OF_DATE,
        "macro": C.MACRO,
        "regime_probs": C.REGIME_PROBS,
        "exposures": _clean(eres),
        "companies": _clean(cres),
        "sensitivity": rankings,
        "thresholds": list(thr),
    }
    with open(os.path.join(HERE, "results.json"), "w") as f:
        json.dump(results, f, indent=1)
    print("Saved results.json")

    # ---- CHECKPOINT 3: model sign-off (manage to the range, not the decimal) ----
    _checkpoint(cp_log, "signoff",
                "Review the sensitivity sweep (TABLE 5) and the systemic-tail "
                "reconciliation before treating any conclusion as final. Read "
                "by tier, not by exact rank; manage to the range, not the "
                "decimal.", pause)
    return results


# ===========================================================================
#  STAGE 3 -- CONSOLIDATE  (join discovery picks to model conclusions)
# ===========================================================================
# Map discovery candidate names -> model COMPANIES keys. The screen names are
# verbose ("SMH (VanEck Semis)"); the model uses short tickers/names. This is
# a simple, auditable alias table -- extend it as the universe grows.
NAME_ALIASES = {
    "nvidia": "NVIDIA",
    "broadcom": "Broadcom",
    "amd": "AMD",
    "marvell": "Marvell",
    "micron": "Micron",
    "qualcomm": "Qualcomm",
    "kioxia": "Kioxia",
    "arm": "ARM",
    # bridged names (must match the keys added by tam_bridge):
    "lumentum": "Lumentum",
    "coherent": "Coherent",
    "applied optoelectronics": "Applied Optoelectronics",
    "ionq": "IonQ",
    "smh": "SMH (VanEck Semis)",
    "soxx": "SOXX (iShares Semis)",
    # Jun 2026 megacap / AI-software test set:
    "palantir": "Palantir", "pltr": "Palantir",
    "applovin": "AppLovin", "app)": "AppLovin",
    "meta": "Meta",
    "microsoft": "Microsoft", "msft": "Microsoft",
    "amazon": "Amazon", "amzn": "Amazon",
    "dram": "DRAM (Roundhill Memory)",
    "qtum": "QTUM (Defiance Quantum)",
    "aiq": "AIQ (Global X AI)",
    "chat": "CHAT (Roundhill GenAI)",
}


def _to_model_key(discovery_name):
    low = discovery_name.lower()
    for token, key in NAME_ALIASES.items():
        if token in low:
            return key
    return None


def stage_consolidate(discovery_report, model_results, pause=False, cp_log=None):
    _banner("STAGE 3 / 3   CONSOLIDATE  (discovery picks  x  model verdict)")

    decomp = model_results["companies"]["decomposition"]
    rec_cond = model_results["companies"]["recovery_cond"]

    # index discovery picks by model key
    disc_by_key = {}
    for c in (discovery_report.get("shortlist_stocks", []) +
              discovery_report.get("shortlist_etfs", [])):
        k = _to_model_key(c["name"])
        if k:
            disc_by_key[k] = c

    def _curve_at(rc, months):
        for pt in rc.get("recovery_curve", []) or []:
            if pt["months"] == months:
                return pt["p_recovered"]
        return float("nan")

    rows = []
    # rank by the UNCONDITIONAL permanent-loss probability (comparable across
    # betas); fall back to fragility if unavailable. Lower = safer.
    def _sortkey(n):
        pp = rec_cond[n].get("p_deep_permanent")
        return pp if pp == pp else decomp[n]["fragility"]  # nan-safe
    for nm in sorted(decomp, key=_sortkey, reverse=True):  # worst first
        d = decomp[nm]
        rc = rec_cond[nm]
        disc = disc_by_key.get(nm)
        rows.append({
            "company": nm,
            "in_discovery_shortlist": disc is not None,
            "discovery_score": disc["score"] if disc else None,
            "beta": C.COMPANIES.get(nm, {}).get("beta"),
            "fragility": d["fragility"],
            "recovery_quality": d["recovery_quality"],
            "p_dd25_18m": rc["p_dd25"],
            "p_recover_by_mandate": rc["p_recover"],
            "p_recover_24m": _curve_at(rc, 24),
            "p_never": rc.get("p_never", float("nan")),
            "p_deep_permanent": rc.get("p_deep_permanent", float("nan")),
        })

    # gaps in both directions (these ARE the red-team material)
    modeled = set(decomp.keys())
    discovered = set(disc_by_key.keys())
    discovered_not_modeled = sorted(
        [c["name"] for c in (discovery_report.get("shortlist_stocks", []) +
                             discovery_report.get("shortlist_etfs", []))
         if _to_model_key(c["name"]) is None])
    modeled_not_discovered = sorted(modeled - discovered)

    # ---- print the joined table (now incl. the permanent tail) ----
    _mm = int(C.MANDATE_MONTHS)
    def _pct(x, w):
        return (f"{x*100:.0f}%".rjust(w)) if x == x else "n/a".rjust(w)
    print(f"\n{'Company':24s} {'Disc?':>5s} {'beta':>5s} {'Frag':>5s} "
          f"{'P(DD>25%)':>9s} {'P(never|DD)':>11s} {'P(deep&perm)':>12s}")
    print("  ordered by P(deep&perm) = P(DD>25% AND never recovers), worst first.")
    print("  This is comparable ACROSS betas; P(never|DD) is only comparable")
    print("  WITHIN a similar-beta cohort (high beta dips past -25% on shallow,")
    print("  recoverable moves, flattering its conditional figure).")
    print("-" * 74)
    for r in rows:
        disc = "yes" if r["in_discovery_shortlist"] else "no"
        bt = f"{r['beta']:.2f}" if r.get("beta") is not None else "  -  "
        print(f"{r['company']:24s} {disc:>5s} {bt:>5s} "
              f"{r['fragility']*100:4.0f}% {_pct(r['p_dd25_18m'],9)} "
              f"{_pct(r['p_never'],11)} {_pct(r['p_deep_permanent'],12)}")

    print("\nGAPS (the honest seam between the two stages):")
    print(f"  Discovery picks NOT yet modeled (need TAM stage): "
          f"{discovered_not_modeled or 'none'}")
    print(f"  Modeled names NOT surfaced by discovery shortlist: "
          f"{modeled_not_discovered or 'none'}")

    _checkpoint(cp_log, "redteam",
                "Adjudicate the gaps above. Discovery picks not yet modeled "
                "need the TAM stage (rev/TAM/penetration + judgment scores) "
                "before they enter the engine. Modeled names the screen did "
                "not surface deserve a 'why are we still carrying this?' look.",
                pause)

    consolidated = {
        "as_of": model_results["as_of"],
        "run_date": discovery_report["run_date"],
        "joined": rows,
        "gaps": {
            "discovered_not_modeled": discovered_not_modeled,
            "modeled_not_discovered": modeled_not_discovered,
        },
        "checkpoints_for_review": cp_log,
    }
    with open(os.path.join(HERE, "consolidated_report.json"), "w") as f:
        json.dump(_clean(consolidated), f, indent=1)

    _write_markdown(consolidated, discovery_report, model_results)
    print("\nSaved consolidated_report.json and consolidated_report.md")
    return consolidated


def _write_markdown(consolidated, discovery_report, model_results):
    _mm = int(C.MANDATE_MONTHS)
    L = []
    L.append(f"# Systemic + TAM Risk Agent — Consolidated Report")
    L.append("")
    L.append(f"*Run date: {consolidated['run_date']} · Model calibrated: "
             f"{consolidated['as_of']} · {C.SIM['n_paths']:,} paths · "
             f"mandate {_mm}m*")
    L.append("")
    L.append("**Research model, not investment advice.**")
    L.append("")
    L.append("## 1. Discovery shortlist")
    L.append("")
    L.append("**Stocks (top picks by blended screen score):**")
    L.append("")
    for c in discovery_report["shortlist_stocks"]:
        L.append(f"- **{c['name']}** — score {c['score']:.3f}  "
                 f"_({c['sector']})_")
    L.append("")
    L.append("**ETFs:**")
    L.append("")
    for c in discovery_report["shortlist_etfs"]:
        L.append(f"- **{c['name']}** — score {c['score']:.3f}  "
                 f"_({c['sector']})_")
    L.append("")
    if discovery_report.get("diff"):
        d = discovery_report["diff"]
        L.append("**Run-over-run movement (penetration):**")
        L.append("")
        up = ", ".join(f"{r['name']} {r['from']}→{r['to']}"
                       for r in d.get("moved_up", [])[:8]) or "none"
        dn = ", ".join(f"{r['name']} {r['from']}→{r['to']}"
                       for r in d.get("moved_down", [])[:8]) or "none"
        L.append(f"- Moved up: {up}")
        L.append(f"- Moved down: {dn}")
        L.append(f"- Entered: {', '.join(x['name'] for x in d.get('entered', [])) or 'none'}")
        L.append(f"- Exited: {', '.join(x['name'] for x in d.get('exited', [])) or 'none'}")
        L.append("")
    L.append("## 2. Model verdict, joined to discovery")
    L.append("")
    L.append(f"Ordered by **P(deep & permanent)** = P(drawdown >25% AND never "
             f"recovers within the simulation) — worst first. This is the "
             f"unconditional permanent-loss probability and is **comparable "
             f"across betas**. `P(never|DD)` is conditional on a >25% drawdown "
             f"and is only comparable *within* a similar-beta cohort, because a "
             f"high-beta name dips past −25% on shallow, recoverable moves that "
             f"flatter its conditional figure.")
    L.append("")

    def _md(x):
        return f"{x*100:.0f}%" if x == x else "n/a"
    L.append(f"| Company | In shortlist | β | Fragility | P(DD>25%) | P(never\\|DD) | **P(deep & perm)** |")
    L.append("|---|---|---|---|---|---|---|")
    for r in consolidated["joined"]:
        bt = f"{r['beta']:.2f}" if r.get("beta") is not None else "—"
        L.append(f"| {r['company']} | {'yes' if r['in_discovery_shortlist'] else 'no'} "
                 f"| {bt} | {_md(r['fragility'])} | {_md(r['p_dd25_18m'])} "
                 f"| {_md(r['p_never'])} | **{_md(r['p_deep_permanent'])}** |")
    L.append("")
    L.append("## 3. Gaps to adjudicate (red-team checkpoint)")
    L.append("")
    g = consolidated["gaps"]
    L.append(f"- **Discovery picks not yet modeled** (need the TAM stage before "
             f"they enter the engine): {', '.join(g['discovered_not_modeled']) or 'none'}")
    L.append(f"- **Modeled names not surfaced by the screen** (why still "
             f"carried?): {', '.join(g['modeled_not_discovered']) or 'none'}")
    L.append("")
    L.append("## 4. Human checkpoints recorded this run")
    L.append("")
    for cp in consolidated.get("checkpoints_for_review", []):
        L.append(f"- **{cp['checkpoint']}** — {cp['question']}")
    L.append("")
    with open(os.path.join(HERE, "consolidated_report.md"), "w") as f:
        f.write("\n".join(L))


# ===========================================================================
#  MAIN
# ===========================================================================
def main():
    ap = argparse.ArgumentParser(
        description="End-to-end agent: discovery -> analysis -> consolidated results.")
    ap.add_argument("--candidates", default=None,
                    help="JSON file of fresh candidate dicts to open a new "
                         "discovery run with. Omit to re-score the registry's "
                         "current universe.")
    ap.add_argument("--paths", type=int, default=None,
                    help="Override SIM n_paths (e.g. 20000 for a fast pass, "
                         "150000 for a full run). Default: calibration value.")
    ap.add_argument("--notes", default="", help="Run notes for the registry.")
    ap.add_argument("--pause", action="store_true",
                    help="Stop at each human checkpoint and wait for Enter.")
    ap.add_argument("--skip-analysis", action="store_true",
                    help="Run discovery only (no Monte Carlo).")
    ap.add_argument("--add-bridged", action="store_true",
                    help="Run the TAM bridge: add the researched discovery picks "
                         "(Lumentum, Coherent, IonQ, AAOI) and the ETFs "
                         "(TAM-from-holdings) to the modeled universe before "
                         "the Monte Carlo.")
    args = ap.parse_args()

    _banner(f"SYSTEMIC + TAM RISK AGENT   |   {datetime.now():%Y-%m-%d %H:%M}")
    print("#  discovery  ->  analysis  ->  consolidated results")
    print("#  RESEARCH MODEL, NOT INVESTMENT ADVICE.")

    cp_log = []
    disc_report, _ = stage_discovery(candidates_path=args.candidates,
                                     notes=args.notes, pause=args.pause,
                                     cp_log=cp_log)

    if args.add_bridged:
        stage_bridge(cp_log=cp_log)

    if args.skip_analysis:
        _banner("DONE (discovery only).")
        return

    model_results = stage_analysis(n_paths=args.paths, pause=args.pause,
                                   cp_log=cp_log)
    stage_consolidate(disc_report, model_results, pause=args.pause, cp_log=cp_log)

    _banner("DONE.  Outputs: discovery_report.json, results.json, "
            "consolidated_report.json/.md")


if __name__ == "__main__":
    main()
