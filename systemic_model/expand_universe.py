"""
expand_universe.py — find the highest growth/ROI names and make them priceable.

Uses the model's OWN methodology to grow the universe without dropping quality:
  1. Ask Claude to propose high-growth AI/semiconductor/AI-software names that are
     NOT already modeled, each with a ticker.
  2. For each, pull fresh financials from Polygon and have Claude produce the full
     set of model inputs (the same TAM-facts schema the engine prices on).
  3. Write them to discovery/expansion.json. tam_bridge / tiering / calibration
     merge that file, so the new names flow through the SAME Monte-Carlo engine.
  4. You then run the model and keep the names that actually rank well
     (high growth, good reward vs S&P, not "broken"). Quality is enforced by the
     model, not by hand.

Run:
  ANTHROPIC_API_KEY=xx POLYGON_KEY=xx python3 expand_universe.py --n 40
  ANTHROPIC_API_KEY=xx POLYGON_KEY=xx python3 expand_universe.py --names TSM,ASML,ANET

RESEARCH MODEL, NOT INVESTMENT ADVICE.
"""
import os, sys, json, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "discovery"))

import fetch_monthly as FM   # reuse polygon_facts, call_claude, key handling

OUT = os.path.join(HERE, "discovery", "expansion.json")

GROUPS = ("AI-infra", "AI-platform", "defensive", "disruptive")


def existing_names():
    import tiering as T
    return sorted(T.UNIVERSE.keys())


def propose_candidates(n, exclude):
    prompt = f"""You are building a universe for an AI/semiconductor RISK model. Propose the {n} PUBLICLY-TRADED US-listed names with the highest combination of (a) durable revenue GROWTH and (b) attractive risk-adjusted upside, that are part of the AI / semiconductor / AI-software / data-center / AI-power ecosystem.

EXCLUDE any of these already-modeled names (and obvious duplicates):
{json.dumps(exclude)}

Favor real, liquid, US-exchange-listed companies with a credible AI growth driver. Mix established compounders and earlier-stage high-growth names, but every pick must be investable (no private companies, no OTC microcaps).

Return ONLY JSON: {{"candidates": [{{"name": "<display name>", "ticker": "<US ticker>", "theme": "<3-5 word theme>"}}]}}. Exactly {n} items."""
    res = FM.call_claude(prompt)
    return res.get("candidates", [])


def make_facts(cand):
    """One company -> full model-input dict, grounded in Polygon, scored by Claude."""
    name, ticker = cand["name"], cand.get("ticker", "")
    facts = FM.polygon_facts(ticker) if ticker else {}
    fresh = ", ".join(f"{k}={v}" for k, v in facts.items()) or "no fresh data available"
    prompt = f"""You are the analyst calibrating an AI/semiconductor Monte-Carlo risk model. Produce the model inputs for ONE company. Be calibrated and conservative; ground revenue/valuation in the fresh data where present.

Company: {name} ({ticker})
Fresh data (Polygon): {fresh}
Proposed theme: {cand.get('theme','')}

Score on EXACTLY these scales:
- kind: "stock" (always "stock" here).
- theme: 3-5 word description (e.g. "AI networking silicon").
- growth: expected revenue growth next ~18 months (decimal; 0.45 = 45%). Anchor to fresh YoY where available.
- rev_bn: AI-relevant forward revenue, $bn (use fresh rev_ttm_bn as a guide; for diversified names use the relevant segment).
- tam_bn: served addressable market, $bn.
- tam_cagr: growth rate of that market (decimal/yr).
- fwd_pe: forward P/E (valuation premium; use a high sentinel like 120-200 for pre-profit hyper-growth).
- beta: loading on the market factor (mega-cap ~1.0-1.2; volatile single name ~1.5-2.0; speculative ~2.0-2.6).
- quality: TAM credibility 0-1 (1=customer-anchored demand now, low=speculative).
- earn_quality: earnings durability 0-1 (1=secular, low=one-off/cyclical).
- dominance: market-share/moat 0-1 (1=near-monopoly, low=fragmented).
- capex_elastic: 0-1, how much demand survives a credit/capex freeze (1=non-discretionary/recurring, low=highly cyclical capex).
- group: one of {list(GROUPS)} (AI-infra=chips/hardware/data-center; AI-platform=hyperscalers/software platforms; defensive=mature low-beta tech; disruptive=early/speculative).
- permanence: 0-1, chance a deep drawdown is TRULY terminal (mega-cap durable ~0.30, quality mid ~0.40, cyclical ~0.55, speculative ~0.80).
- role: one sentence on the business + why it sits where it does.

Return ONLY JSON for this one company: {{"name": "{name}", "kind": "stock", "theme": "...", "growth": <n>, "rev_bn": <n>, "tam_bn": <n>, "tam_cagr": <n>, "fwd_pe": <n>, "beta": <n>, "quality": <n>, "earn_quality": <n>, "dominance": <n>, "capex_elastic": <n>, "group": "...", "permanence": <n>, "role": "...", "ticker": "{ticker}"}}"""
    rec = FM.call_claude(prompt)
    return rec


NUM_FIELDS = ("growth", "rev_bn", "tam_bn", "tam_cagr", "fwd_pe", "beta",
              "quality", "earn_quality", "dominance", "capex_elastic", "permanence")


def clean_rec(rec):
    out = {}
    for f in NUM_FIELDS:
        v = rec.get(f)
        if isinstance(v, (int, float)):
            out[f] = round(float(v), 4)
    out["kind"] = "stock"
    out["theme"] = str(rec.get("theme", ""))[:40]
    out["group"] = rec.get("group") if rec.get("group") in GROUPS else "disruptive"
    out["role"] = str(rec.get("role", ""))[:300]
    out["ticker"] = str(rec.get("ticker", ""))[:8]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40, help="how many candidates to propose")
    ap.add_argument("--names", default="", help="comma list of tickers/names to add instead of auto-proposing")
    ap.add_argument("--merge", action="store_true", help="merge into existing expansion.json instead of replacing")
    args = ap.parse_args()

    if not FM.ANTHROPIC_KEY:
        print("[expand] no ANTHROPIC_API_KEY — aborting."); return

    exclude = existing_names()
    if args.names.strip():
        cands = [{"name": x.strip(), "ticker": x.strip(), "theme": ""} for x in args.names.split(",") if x.strip()]
    else:
        print(f"[expand] proposing {args.n} high-growth candidates (excluding {len(exclude)} existing) ...")
        cands = propose_candidates(args.n, exclude)
    # de-dupe against existing
    cands = [c for c in cands if c.get("name") and c["name"] not in exclude]
    print(f"[expand] {len(cands)} candidates: " + ", ".join(c['name'] for c in cands))

    companies = {}
    for i, c in enumerate(cands, 1):
        try:
            rec = clean_rec(make_facts(c))
            if "rev_bn" in rec and "beta" in rec:
                companies[c["name"]] = rec
                print(f"  [{i}/{len(cands)}] {c['name']:<24} growth {rec.get('growth')} beta {rec.get('beta')} ({rec.get('group')})")
            else:
                print(f"  [{i}/{len(cands)}] {c['name']:<24} SKIPPED (incomplete facts)")
        except Exception as e:
            print(f"  [{i}/{len(cands)}] {c['name']:<24} ERROR: {e}")

    if not companies:
        print("[expand] nothing usable — not writing."); return

    if args.merge and os.path.exists(OUT):
        try:
            prev = json.load(open(OUT)).get("companies", {})
            prev.update(companies); companies = prev
        except Exception:
            pass

    import datetime
    json.dump({"as_of": datetime.date.today().isoformat(),
               "source": f"Claude ({FM.MODEL}) + Polygon",
               "companies": companies}, open(OUT, "w"), indent=2)
    print(f"[expand] wrote {OUT} ({len(companies)} names). Now run the model and prune the weak ones.")


if __name__ == "__main__":
    main()
