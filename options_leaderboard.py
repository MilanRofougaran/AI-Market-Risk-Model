"""
options_leaderboard.py — the "what to actually buy" call-options leaderboard.

Blends the MODEL (thesis-conditional fair value, IV-blind) with the live OPTION
MARKET (Polygon) into a ranked, decision-oriented list, like a concrete buy list:

  rank · contract (TICKER expiry $strikeC) · market price · model fair value ·
  edge (fair − market) · chance it pays (P>strike) · action · buy/watch/skip

WHY PRECOMPUTED (not live per page-view): the Polygon key is rate-limited
(~5 req/min) and each name needs ~3 calls, so a per-visitor live fetch would be
slow and break under load. This runs in the pipeline (throttled), writes
site/data/options_leaderboard.json, and the dashboard just reads it — same
"as-of-a-date" model as the rest of the site.

HONESTY: model fair value is thesis-conditional and IV-BLIND — it is NOT a market
price and cannot say if the market mispriced the option. Calls only. The "edge"
is the model's view (fair − market), not a guarantee. RESEARCH — NOT ADVICE.

Run:  POLYGON_KEY=xxx python3 options_leaderboard.py [--top 10] [--strike 0.75] [--tenor 18m]
"""
import os, sys, json, time, argparse, datetime as dt, urllib.request, urllib.parse

ROOT = os.path.dirname(os.path.abspath(__file__))
LENS_PATH = os.path.join(ROOT, "site", "data", "options_lens.json")
SPREAD_PATH = os.path.join(ROOT, "site", "data", "spread_lens.json")
OUT = os.path.join(ROOT, "site", "data", "options_leaderboard.json")
KEY = os.environ.get("POLYGON_KEY", "")
BASE = "https://api.polygon.io"
THROTTLE_S = float(os.environ.get("POLY_THROTTLE", "13"))   # ~5 req/min

# model display name -> US options ticker (mirrors site/account.html SECURITIES)
NAME2TICKER = {
    "NVIDIA": "NVDA", "Broadcom": "AVGO", "Micron": "MU", "Marvell": "MRVL",
    "Qualcomm": "QCOM", "AMD": "AMD", "ARM": "ARM", "Palantir": "PLTR",
    "Astera Labs": "ALAB", "CoreWeave": "CRWV", "Lumentum": "LITE",
    "Applied Optoelectronics": "AAOI", "IonQ": "IONQ",
    "DRAM (Roundhill Memory)": "DRAM", "SMH (VanEck Semis)": "SMH",
    # extra large/mid-cap AI-era names that may enter the league:
    "Meta": "META", "Tesla": "TSLA", "Oracle": "ORCL", "Vertiv": "VRT", "AppLovin": "APP",
    "Coherent": "COHR", "Cisco": "CSCO", "IBM": "IBM", "Texas Instruments": "TXN",
    # Kioxia (JP) has no liquid US options -> intentionally omitted
}
# augment with expansion-pool tickers so newly-promoted league names resolve too
try:
    _exp = json.load(open(os.path.join(ROOT, "systemic_model", "discovery", "expansion.json")))
    for _nm, _v in (_exp.get("companies") or {}).items():
        if _v.get("ticker") and _nm not in NAME2TICKER:
            NAME2TICKER[_nm] = _v["ticker"]
except Exception:
    pass


def _get(url):
    time.sleep(THROTTLE_S)                       # stay under the rate limit
    req = urllib.request.Request(url, headers={"User-Agent": "leaderboard/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def model_pick(lens, name, strike_mult, tenor):
    """Model fair% / P(ITM) / gate at the strike multiple closest to strike_mult."""
    nd = lens["names"].get(name)
    if not nd or tenor not in nd:
        return None
    strikes = nd[tenor].get("strikes") or {}
    if not strikes:
        return None
    k = min((float(x) for x in strikes), key=lambda v: abs(v - strike_mult))
    cell = strikes.get(f"{k:.2f}") or strikes.get(str(k))
    if not cell:
        return None
    return {"mult": k, "fair_pct": cell["fair_value_pct_of_spot"],
            "p_itm": cell["p_itm"], "gate": nd.get("gate", "secular")}


def spot_price(ticker):
    d = _get(f"{BASE}/v2/aggs/ticker/{ticker}/prev?apiKey={KEY}")
    res = d.get("results") or []
    return res[0].get("c") if res else None


def find_contract(ticker, target_strike, target_exp):
    """Closest listed LEAP call to (strike, ~18mo expiry)."""
    lo, hi = target_strike * 0.8, target_strike * 1.2
    g = (target_exp - dt.timedelta(days=90)).isoformat()
    l = (target_exp + dt.timedelta(days=120)).isoformat()
    url = (f"{BASE}/v3/reference/options/contracts?underlying_ticker={ticker}"
           f"&contract_type=call&expiration_date.gte={g}&expiration_date.lte={l}"
           f"&strike_price.gte={lo:.0f}&strike_price.lte={hi:.0f}&limit=100&apiKey={KEY}")
    cands = _get(url).get("results") or []
    if not cands:
        return None
    cands.sort(key=lambda c: (abs(c["strike_price"] - target_strike),
                              abs(dt.date.fromisoformat(c["expiration_date"]) - target_exp).days))
    return cands[0]


def market_price(ticker, occ):
    d = _get(f"{BASE}/v3/snapshot/options/{ticker}/{occ}?apiKey={KEY}")
    r = d.get("results") or {}
    return (r.get("day", {}).get("close")
            or r.get("last_quote", {}).get("midpoint")
            or r.get("last_trade", {}).get("price"))


def bucket_and_action(gate, edge):
    """buy / watch / skip + a short action note, from the model's gate + edge."""
    g = (gate or "").lower()
    if "broken" in g:
        return "skip", "Broken thesis — the model says avoid."
    if "cyclical" in g:
        return "watch", "Cyclical — rebound-dependent; give it time."
    # secular
    if edge is not None and edge > 0:
        return "buy", "Durable grower; model fair value is above the market."
    return "watch", "Durable grower, but priced at/above the model's fair value."


def order_rows(rows):
    """Decision order: buys first, then by edge (most value first); re-rank; tag #1."""
    pri = {"buy": 0, "watch": 1, "skip": 2}
    rows.sort(key=lambda r: (pri.get(r["bucket"], 9),
                             -(r["edge"] if r["edge"] is not None else -1e9)))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    if rows and rows[0]["bucket"] == "buy":
        rows[0]["action"] = "Best overall — " + rows[0]["action"][0].lower() + rows[0]["action"][1:]
    return rows


def pick_leg(name, tenor, spreads):
    """The best 2-leg debit vertical (the 'legs') for this name+tenor, from
    spread_lens. Prefers a deep-ITM long + far-OTM short (0.75/1.50 — low tail
    give-up, secular-friendly); else the lowest-give-up vertical available."""
    nd = (spreads.get("names") or {}).get(name)
    ten = (nd or {}).get("tenors", {}).get(tenor)
    if not ten:
        return None
    verts = {k: v for k, v in ten.items()
             if k.count("/") == 1 and "+" not in k and "-" not in k and v.get("fair_debit_pct") is not None}
    if not verts:
        return None
    key = "0.75/1.50" if "0.75/1.50" in verts else min(verts, key=lambda k: verts[k].get("tail_giveup", 1))
    v = verts[key]; a, b = key.split("/")
    return {"k1": float(a), "k2": float(b), "cost_pct": v["fair_debit_pct"],
            "p_max": v.get("p_max"), "giveup": v.get("tail_giveup")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--strike", type=float, default=0.75)   # deep-ITM (model's high-confidence regime)
    ap.add_argument("--tenor", default="18m")
    args = ap.parse_args()

    if not KEY:
        print("[leaderboard] no POLYGON_KEY — skipping (page will hide the leaderboard).")
        return
    lens = json.load(open(LENS_PATH))
    try:
        spreads = json.load(open(SPREAD_PATH))
    except Exception:
        spreads = {}

    # rank candidates by model fair value at the chosen deep-ITM strike (skip broken)
    ranked = []
    for name in lens["names"]:
        if name not in NAME2TICKER:
            continue
        mp = model_pick(lens, name, args.strike, args.tenor)
        if not mp or "broken" in (mp["gate"] or "").lower():
            continue
        ranked.append((name, mp))
    ranked.sort(key=lambda x: -x[1]["fair_pct"])
    ranked = ranked[:args.top]

    today = dt.date.today()
    target_exp = today + dt.timedelta(days=548)             # ~18 months out
    rows = []
    for i, (name, mp) in enumerate(ranked, 1):
        tk = NAME2TICKER[name]
        try:
            spot = spot_price(tk)
            if not spot:
                print(f"  [{i}] {name} ({tk}) — no spot, skip"); continue
            c = find_contract(tk, spot * args.strike, target_exp)
            if not c:
                print(f"  [{i}] {name} ({tk}) — no contract, skip"); continue
            mkt = market_price(tk, c["ticker"])
            fair = mp["fair_pct"] / 100.0 * spot
            edge = (fair - mkt) if mkt is not None else None
            bucket, action = bucket_and_action(mp["gate"], edge)
            ed = dt.date.fromisoformat(c["expiration_date"])
            rows.append({
                "rank": i, "name": name, "ticker": tk,
                "spot": round(spot, 2),
                "expiry": c["expiration_date"],
                "expiry_label": ed.strftime("%b %Y"),
                "strike": c["strike_price"],
                "strike_mult": round(c["strike_price"] / spot, 2),
                "occ": c["ticker"],
                "market": round(mkt, 2) if mkt is not None else None,
                "fair": round(fair, 2),
                "fair_pct": mp["fair_pct"],
                "edge": round(edge, 2) if edge is not None else None,
                "p_itm": round(mp["p_itm"] * 100),
                "gate": mp["gate"], "bucket": bucket, "action": action,
                "leg": pick_leg(name, args.tenor, spreads),   # best 2-leg spread (the "legs")
            })
            print(f"  [{i}] {name} {tk} {c['expiration_date']} ${c['strike_price']}C "
                  f"mkt {mkt} fair {fair:.1f} edge {edge} ({bucket})")
        except Exception as e:
            print(f"  [{i}] {name} ({tk}) ERROR: {e}")

    order_rows(rows)
    out = {
        "as_of": today.isoformat(),
        "generated": dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "tenor": args.tenor, "strike_mult": args.strike,
        "note": ("Model fair value is THESIS-CONDITIONAL and IV-BLIND — not a market price; "
                 "it can't tell you if the market mispriced the option. Edge = model fair − market. "
                 "Calls only. Prices as of the date above. RESEARCH MODEL — NOT INVESTMENT ADVICE."),
        "rows": rows,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w"), indent=1)
    print(f"[leaderboard] wrote {OUT}: {len(rows)} contracts, as_of {today}")


if __name__ == "__main__":
    main()
