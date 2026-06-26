"""
============================================================================
 LEAGUE  --  systemic_model
============================================================================
 The ranked, fixed-size league table with ADMISSION / EVICTION + HYSTERESIS.

 The engine prices a broad universe every run. This module turns that full
 ranking into a STABLE league:

   POOL_CAP = 125   the tracked board — Top-125 by reward-vs-S&P
   VIEW_CAP =  50   the highlighted Top-50 shown by default on the dashboard

 EVERYTHING COMPETES for a slot (stocks + ETFs) EXCEPT:
   - PINNED benchmarks (the S&P / SCHD) — always present for comparison,
     they do not consume a competitive slot.
   - LEVERAGED 3x vehicles — excluded by design (path-dependent decay, not a
     fundamental view).

 RANKING METRIC = reward_vs_S&P  (the model's headline, relative to the index):
     reward_vs_SP = (growth / S&P growth) x (S&P tail / name tail),  S&P = 1.00.

 WHY HYSTERESIS:
   The engine is a Monte-Carlo, so scores wiggle a point or two between runs.
   Without a margin, names near the cut-off would swap in and out on noise and
   the published table — and the graphs — would churn for no real reason. A
   challenger only DISPLACES an incumbent when it beats it by MARGIN. So:
     * nothing genuinely new outranks the board -> the league is unchanged ->
       the dashboard and graphs stay put.
     * something genuinely breaks in -> it displaces the weakest incumbent ->
       the standings (and the graphs) update.

 This is pure state logic over the already-computed ranking (no engine, no
 network), so it is fully testable offline: run `python3 league.py` for a
 self-contained demo + assertions.

 RESEARCH MODEL, NOT INVESTMENT ADVICE.
============================================================================
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
LEAGUE_PATH = os.path.join(HERE, "league.json")

POOL_CAP = 125          # the tracked league
VIEW_CAP = 50           # the highlighted Top-50 view
MARGIN   = 0.05         # a challenger must beat an incumbent by >5% (relative) to displace it
METRIC   = "reward_vs_SP"

# Always-present reference rows (do not consume a competitive slot).
PINNED = ["VOO (S&P 500)", "SCHD (Dividend)"]


# ---------------------------------------------------------------------------
#  helpers
# ---------------------------------------------------------------------------
def _score(r):
    """The ranking score for a row (reward_vs_S&P). Missing -> -inf (ranks last)."""
    v = r.get("vs_sp")
    return v if isinstance(v, (int, float)) else float("-inf")


def _eligible(rows, leveraged):
    """Names that COMPETE for a slot: everything priced, minus leveraged
    vehicles, minus the pinned benchmarks, minus anything without a score."""
    lev = set(leveraged or [])
    pin = set(PINNED)
    out = []
    for r in rows:
        nm = r.get("name")
        if not nm or nm in lev or nm in pin:
            continue
        if _score(r) == float("-inf"):
            continue            # unpriced names can't be ranked
        out.append(r)
    return out


def load_league(path=LEAGUE_PATH):
    """Previous league state, or an empty shell on the first ever run."""
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return {"members": []}


def _prev_names(prev):
    return {m["name"] for m in (prev or {}).get("members", [])}


def _prev_first_seen(prev):
    return {m["name"]: m.get("first_seen") for m in (prev or {}).get("members", [])}


# ---------------------------------------------------------------------------
#  the core: select the league with hysteresis
# ---------------------------------------------------------------------------
def select(rows, prev=None, leveraged=None, pool_cap=POOL_CAP,
           view_cap=VIEW_CAP, margin=MARGIN, as_of=None):
    """Compute the new league from the full ranked `rows`.

    rows       : list of dicts, each with at least {name, vs_sp, kind, growth,
                 p_deep_permanent}. (tiering.build_rows output is exactly this.)
    prev       : the previous league dict (for hysteresis + first_seen + diff).
    leveraged  : names to exclude entirely (tiering.LEVERAGED).

    Returns the new league dict (also see update_and_save to persist it).
    """
    prev = prev or {"members": []}
    prev_set = _prev_names(prev)
    first_seen = _prev_first_seen(prev)

    elig = _eligible(rows, leveraged)
    ranked = sorted(elig, key=_score, reverse=True)

    # pinned benchmarks are shown ALONGSIDE the league (they do not consume a
    # competitive slot), so the competitive field keeps the full pool_cap slots.
    pinned_present = [r for r in rows if r.get("name") in set(PINNED)]
    slots = max(0, pool_cap)

    inN = ranked[:slots]
    outN = ranked[slots:]

    # ---- HYSTERESIS: protect incumbents from marginal newcomers -----------
    # If the weakest NEWCOMER inside the cut only barely beat an INCUMBENT now
    # sitting just outside, keep the incumbent instead. Repeat until stable.
    # Net effect: a challenger must beat the incumbent by > margin to get in.
    changed = True
    while changed and inN and outN:
        changed = False
        newcomers_in = [r for r in inN if r["name"] not in prev_set]
        incumbents_out = [r for r in outN if r["name"] in prev_set]
        if not newcomers_in or not incumbents_out:
            break
        weakest_new = min(newcomers_in, key=_score)
        best_inc_out = max(incumbents_out, key=_score)
        # incumbent kept unless the newcomer cleared it by the full margin
        if _score(best_inc_out) >= _score(weakest_new) * (1.0 - margin):
            inN.remove(weakest_new); inN.append(best_inc_out)
            outN.remove(best_inc_out); outN.append(weakest_new)
            changed = True

    # ---- assemble the league: pinned + the competitive winners ------------
    members_rows = pinned_present + inN
    members_rows.sort(key=_score, reverse=True)

    members = []
    for i, r in enumerate(members_rows, 1):
        nm = r["name"]
        members.append({
            "name": nm,
            "rank": i,
            "vs_sp": (round(r["vs_sp"], 4) if isinstance(r.get("vs_sp"), (int, float)) else None),
            "kind": r.get("kind"),
            "pinned": nm in set(PINNED),
            "top50": i <= view_cap,
            "first_seen": first_seen.get(nm, as_of),
        })

    new_set = {m["name"] for m in members}
    entered = sorted(new_set - prev_set)
    exited = sorted(prev_set - new_set)

    return {
        "as_of": as_of,
        "metric": METRIC,
        "pool_cap": pool_cap,
        "view_cap": view_cap,
        "margin": margin,
        "n_members": len(members),
        "members": members,
        "entered": entered,
        "exited": exited,
    }


def update_and_save(rows, leveraged=None, as_of=None, path=LEAGUE_PATH,
                    pool_cap=POOL_CAP, view_cap=VIEW_CAP, margin=MARGIN):
    """Compute the new league against the saved one and persist it.
    Returns the new league dict. Use this from run_all.py after the model run."""
    prev = load_league(path)
    new = select(rows, prev=prev, leveraged=leveraged, pool_cap=pool_cap,
                 view_cap=view_cap, margin=margin, as_of=as_of)
    with open(path, "w") as f:
        json.dump(new, f, indent=1)
    return new


def membership(path=LEAGUE_PATH):
    """{name -> {rank, top50, pinned}} for export_snapshot / tiering to tag rows."""
    lg = load_league(path)
    return {m["name"]: {"rank": m["rank"], "top50": m.get("top50", False),
                        "pinned": m.get("pinned", False)}
            for m in lg.get("members", [])}


def pool_keep_names(rows, leveraged=None, keep=None):
    """Names worth keeping PRICED next run: the league members plus a buffer of
    the next-best challengers, so the engine cost stays bounded while the board
    can still turn over. Used to prune discovery/expansion.json.
    `keep` defaults to pool_cap + 25 (a churn buffer)."""
    keep = keep or (POOL_CAP + 25)
    elig = _eligible(rows, leveraged)
    ranked = sorted(elig, key=_score, reverse=True)
    return {r["name"] for r in ranked[:keep]} | set(PINNED)


# ---------------------------------------------------------------------------
#  self-test (no engine, no network): proves admission/eviction + hysteresis
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    def row(nm, vs, kind="stock"):
        return {"name": nm, "vs_sp": vs, "kind": kind, "growth": 0.3,
                "p_deep_permanent": 0.2}

    # --- tiny universe, cap 3 (+ pinned), margin 10% ---
    cap, vcap, marg = 3, 2, 0.10
    base = [row("A", 5.0), row("B", 4.0), row("C", 3.0), row("D", 2.9),
            row("E", 1.0), row("VOO (S&P 500)", 1.0, "ETF"),
            row("SCHD (Dividend)", 0.9, "ETF"), row("LEV", 9.9, "ETF")]
    lev = ["LEV"]

    # run 1 (cold): pinned always in; top-3 competitive = A,B,C
    l1 = select(base, prev=None, leveraged=lev, pool_cap=cap, view_cap=vcap,
                margin=marg, as_of="2026-06-01")
    names1 = [m["name"] for m in l1["members"]]
    assert "LEV" not in names1, "leveraged must be excluded"
    assert "VOO (S&P 500)" in names1 and "SCHD (Dividend)" in names1, "benchmarks pinned"
    assert set(["A", "B", "C"]).issubset(names1), names1
    assert "D" not in names1, "D just missed the cut"
    assert l1["members"][0]["rank"] == 1 and l1["members"][0]["top50"] is True
    # view_cap=2 -> only the top 2 by score are top50
    assert sum(1 for m in l1["members"] if m["top50"]) == vcap

    # run 2: D rises to 3.05 — only BARELY beats incumbent C (3.0); within 10%
    # margin, so HYSTERESIS keeps C and D stays out (no churn on noise).
    base2 = [row("A", 5.0), row("B", 4.0), row("C", 3.0), row("D", 3.05),
             row("E", 1.0), row("VOO (S&P 500)", 1.0, "ETF"),
             row("SCHD (Dividend)", 0.9, "ETF"), row("LEV", 9.9, "ETF")]
    l2 = select(base2, prev=l1, leveraged=lev, pool_cap=cap, view_cap=vcap,
                margin=marg, as_of="2026-06-08")
    names2 = [m["name"] for m in l2["members"]]
    assert "C" in names2 and "D" not in names2, ("hysteresis should keep C", names2)
    assert l2["entered"] == [] and l2["exited"] == [], (l2["entered"], l2["exited"])

    # run 3: D genuinely breaks out to 3.6 — clears C (3.0) by > margin -> D in, C out
    base3 = [row("A", 5.0), row("B", 4.0), row("C", 3.0), row("D", 3.6),
             row("E", 1.0), row("VOO (S&P 500)", 1.0, "ETF"),
             row("SCHD (Dividend)", 0.9, "ETF"), row("LEV", 9.9, "ETF")]
    l3 = select(base3, prev=l2, leveraged=lev, pool_cap=cap, view_cap=vcap,
                margin=marg, as_of="2026-06-15")
    names3 = [m["name"] for m in l3["members"]]
    assert "D" in names3 and "C" not in names3, ("genuine breakout admits D", names3)
    assert l3["entered"] == ["D"] and l3["exited"] == ["C"], (l3["entered"], l3["exited"])

    print("league self-test OK:")
    print("  run1 league:", names1, "| top50:", [m["name"] for m in l1["members"] if m["top50"]])
    print("  run2 (noise):  entered", l2["entered"], "exited", l2["exited"], "-> stable")
    print("  run3 (breakout): entered", l3["entered"], "exited", l3["exited"])
    print("All assertions passed. Admission/eviction + hysteresis work.")
