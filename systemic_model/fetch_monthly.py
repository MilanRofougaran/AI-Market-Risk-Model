"""
fetch_monthly.py — AI-assisted monthly re-evaluation of each company's OUTLOOK.

Once a month, the slow-moving "company outlook" inputs (18-month growth, TAM
credibility, earnings durability, moat/dominance, forward P/E) are re-evaluated
by Claude, GROUNDED in fresh financials pulled from Polygon. The result is
written to live_fundamentals.json (the model merges it on every run, same as the
daily live_inputs.json) and to ../site/data/outlook.json (a plain-English record
of WHAT changed and WHY, shown on the How-it-works page).

Run:  ANTHROPIC_API_KEY=xxx POLYGON_KEY=xxx python3 fetch_monthly.py

The judgment fields and what they mean (kept identical to calibration.py so the
AI scores on the same scale):
  growth        18-month revenue-growth estimate (decimal, e.g. 0.45 = 45%)
  rev_bn        current relevant-segment revenue, $bn
  tam_cagr      growth rate of the addressable market (decimal/yr)
  fwd_pe        forward P/E (the valuation premium)
  quality       TAM credibility            (1=customer-anchored, low=soft/cyclical)
  earn_quality  earnings durability        (1=secular, low=price-spike/cyclical)
  dominance     market-share capture/moat  (1=monopoly, low=fragmented)

DESIGN RULE: only move a number when fresh data or a clear reason justifies it.
Stability matters — a risk model should not reshuffle its whole list every month.

RESEARCH MODEL, NOT INVESTMENT ADVICE.
"""
import os, sys, json, datetime, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_FUND = os.path.join(HERE, "live_fundamentals.json")
OUT_LOG  = os.path.join(HERE, "..", "site", "data", "outlook.json")

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
POLYGON_KEY   = os.environ.get("POLYGON_KEY", "").strip()
MODEL         = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-8").strip()

# Individual companies the AI re-evaluates -> their stock ticker for Polygon.
# (ETFs and 3x leveraged funds are excluded: their behaviour is structural, not
#  a company-outlook judgment.)
TICKERS = {
    "IonQ": "IONQ", "Astera Labs": "ALAB", "CoreWeave": "CRWV", "Palantir": "PLTR",
    "Lumentum": "LITE", "Applied Optoelectronics": "AAOI", "Micron": "MU", "AMD": "AMD",
    "NVIDIA": "NVDA", "Broadcom": "AVGO", "Marvell": "MRVL", "AppLovin": "APP",
    "Vertiv": "VRT", "Coherent": "COHR", "ARM": "ARM", "Meta": "META", "Oracle": "ORCL",
    "Microsoft": "MSFT", "Texas Instruments": "TXN", "Amazon": "AMZN", "Alphabet": "GOOGL",
    "Qualcomm": "QCOM", "Apple": "AAPL", "Cisco": "CSCO", "IBM": "IBM", "Tesla": "TSLA",
}


def _get_json(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "market-analyst/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def polygon_facts(ticker):
    """Best-effort fresh fundamentals from Polygon: last price + TTM revenue + YoY."""
    out = {}
    if not POLYGON_KEY:
        return out
    # last close
    try:
        d = _get_json(f"https://api.polygon.io/v2/aggs/ticker/{ticker}/prev?apiKey={POLYGON_KEY}")
        res = (d.get("results") or [])
        if res:
            out["price"] = round(float(res[0]["c"]), 2)
    except Exception:
        pass
    # quarterly revenues -> TTM and YoY
    try:
        d = _get_json(f"https://api.polygon.io/vX/reference/financials?ticker={ticker}"
                      f"&timeframe=quarterly&limit=6&order=desc&sort=period_of_report_date"
                      f"&apiKey={POLYGON_KEY}")
        revs = []
        for row in (d.get("results") or []):
            try:
                v = row["financials"]["income_statement"]["revenues"]["value"]
                revs.append(float(v))
            except Exception:
                continue
        if len(revs) >= 4:
            ttm = sum(revs[:4])
            out["rev_ttm_bn"] = round(ttm / 1e9, 2)
            if len(revs) >= 5:
                prior = sum(revs[1:5])
                if prior > 0:
                    out["rev_yoy"] = round(ttm / prior - 1, 3)
    except Exception:
        pass
    return out


def current_inputs():
    """Read the model's CURRENT scores so the AI sees its starting point."""
    sys.path.insert(0, HERE)
    import calibration as C
    import tiering as T
    rows = {}
    for name, ticker in TICKERS.items():
        rec = {"ticker": ticker}
        u = T.UNIVERSE.get(name)
        if u:
            rec["growth"] = u[2]
        c = C.COMPANIES.get(name)
        if c:
            for f in ("rev_bn", "tam_cagr", "fwd_pe", "quality", "earn_quality", "dominance"):
                if f in c:
                    rec[f] = c[f]
        rows[name] = rec
    return rows


def build_prompt(rows):
    today = datetime.date.today().isoformat()
    lines = []
    for name, rec in rows.items():
        facts = polygon_facts(rec["ticker"])
        fresh = ", ".join(f"{k}={v}" for k, v in facts.items()) or "no fresh data available"
        cur = {k: v for k, v in rec.items() if k != "ticker"}
        lines.append(f"- {name} ({rec['ticker']}): current model scores {json.dumps(cur)} | fresh: {fresh}")
    body = "\n".join(lines)
    return f"""You are the analyst maintaining a quantitative AI/semiconductor risk model. Today is {today}.

Re-evaluate each company's OUTLOOK inputs. These feed a Monte-Carlo risk model, so be calibrated and conservative — only move a value when the fresh data or a clear, current reason justifies it; otherwise keep the current value. Small, well-reasoned changes only.

Field definitions (score on EXACTLY these scales):
- growth: expected revenue growth over the next ~18 months (decimal; 0.45 = 45%). Anchor to the fresh YoY revenue trend where available, adjusted for the known forward trajectory.
- rev_bn: the company's revenue from the AI/relevant SEGMENT in $bn — NOT necessarily total company revenue. The fresh 'rev_ttm_bn' is TOTAL company revenue: for pure-play names (IonQ, CoreWeave, NVIDIA, Micron, Astera, Lumentum, Marvell) it is a good proxy, but for diversified names (Apple, Microsoft, Amazon, Alphabet, Broadcom, Qualcomm, Cisco, IBM, Texas Instruments, Meta, Oracle, Tesla) keep rev_bn as the relevant AI segment and only nudge it for clear segment growth — do not replace it with total revenue.
- tam_cagr: growth rate of the company's addressable market (decimal/yr).
- fwd_pe: forward price/earnings multiple (the valuation premium).
- quality: TAM credibility, 0–1 (1 = customer-anchored demand now, low = soft/speculative/cyclical).
- earn_quality: earnings durability, 0–1 (1 = secular/durable, low = one-off price-spike/cyclical).
- dominance: market-share capture / moat, 0–1 (1 = near-monopoly, low = fragmented/commoditized).

Companies:
{body}

Return ONLY a JSON object, no prose, of this exact shape:
{{"companies": {{"<name>": {{"growth": <num>, "rev_bn": <num>, "tam_cagr": <num>, "fwd_pe": <num>, "quality": <num>, "earn_quality": <num>, "dominance": <num>, "rationale": "<one sentence on what changed and why, or 'unchanged: <reason>'>"}}}}}}
Use the EXACT company names given above as keys. Include every company."""


def call_claude(prompt):
    payload = json.dumps({
        "model": MODEL,
        "max_tokens": 8000,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=payload,
        headers={
            "x-api-key": ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }, method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.load(r)
    text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text").strip()
    # be liberal about wrapping: strip code fences, then grab the outermost {...}
    if "```" in text:
        parts = text.split("```")
        for p in parts:
            p = p[4:] if p.lstrip().startswith("json") else p
            if "{" in p:
                text = p
                break
    i, j = text.find("{"), text.rfind("}")
    if i == -1 or j == -1:
        raise ValueError("no JSON object in model reply: " + text[:200])
    return json.loads(text[i:j + 1])


def main():
    if not ANTHROPIC_KEY:
        print("[fetch_monthly] no ANTHROPIC_API_KEY — skipping (model keeps current scores).")
        return
    today = datetime.date.today().isoformat()
    rows = current_inputs()
    print(f"[fetch_monthly] re-evaluating {len(rows)} companies with {MODEL} ...")
    result = call_claude(build_prompt(rows))
    got = result.get("companies") or {}

    fields = ("growth", "rev_bn", "tam_cagr", "fwd_pe", "quality", "earn_quality", "dominance")
    companies, changes = {}, []
    for name, rec in rows.items():
        new = got.get(name)
        if not isinstance(new, dict):
            continue
        clean = {}
        for f in fields:
            v = new.get(f)
            if isinstance(v, (int, float)):
                clean[f] = round(float(v), 4)
                old = rec.get(f)
                if old is not None and abs(float(old) - float(v)) > 1e-6:
                    changes.append({"name": name, "field": f, "old": old, "new": clean[f]})
        clean["rationale"] = str(new.get("rationale", ""))[:400]
        companies[name] = clean

    if not companies:
        print("[fetch_monthly] AI returned nothing usable — not writing. Model keeps current scores.")
        return

    fund = {"as_of": today, "source": f"Claude ({MODEL}) + Polygon financials", "companies": companies}
    json.dump(fund, open(OUT_FUND, "w"), indent=2)
    print(f"[fetch_monthly] wrote {OUT_FUND} ({len(companies)} companies, {len(changes)} field changes)")

    log = {
        "as_of": today,
        "model": MODEL,
        "n_companies": len(companies),
        "n_changes": len(changes),
        "changes": changes,
        "companies": {n: {"rationale": c.get("rationale", "")} for n, c in companies.items()},
    }
    try:
        os.makedirs(os.path.dirname(OUT_LOG), exist_ok=True)
        json.dump(log, open(OUT_LOG, "w"), indent=2)
        print(f"[fetch_monthly] wrote {OUT_LOG}")
    except Exception as e:
        print("[fetch_monthly] could not write outlook log:", e)


if __name__ == "__main__":
    main()
