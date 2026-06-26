"""
backtest_recovery.py — the RECOVERY-TIMING backtest the model defers until it has
real price history. We get that history (free, from Yahoo's daily series back to
2008), find every real >25% drawdown, measure how long it actually took to climb
back to the prior peak, and compare that to the model's PREDICTED recovery curve.

HONESTY: this validates recovery TIMING (the model's least-validated axis). It is a
small, survivorship-biased sample (only names that exist today and had long history),
realized paths are single draws not distributions, and censored episodes (not yet
recovered) are handled by only counting an episode at horizon h when its outcome at
h is known. RESEARCH MODEL — NOT INVESTMENT ADVICE.

Writes systemic_model/backtest_recovery.json. Run after run_all.py (needs results.json).
"""
import os, sys, json, time, datetime as dt, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
HORIZONS = [6, 12, 18, 24, 36]
THRESH = 0.25
START = "2008-01-01"

# long-history modeled names (display -> Yahoo ticker). Young IPOs are skipped.
TICKERS = {
    "NVIDIA": "NVDA", "AMD": "AMD", "Micron": "MU", "Broadcom": "AVGO",
    "Qualcomm": "QCOM", "Marvell": "MRVL", "Applied Optoelectronics": "AAOI",
    "Lumentum": "LITE", "Coherent": "COHR", "Texas Instruments": "TXN",
    "Cisco": "CSCO", "IBM": "IBM", "Meta": "META", "Tesla": "TSLA",
    "Amazon": "AMZN", "Alphabet": "GOOGL", "Oracle": "ORCL", "Apple": "AAPL",
    "Microsoft": "MSFT", "Vertiv": "VRT", "ARM": "ARM",
    "SMH (VanEck Semis)": "SMH", "SOXX (iShares Semis)": "SOXX",
    "QQQ (Nasdaq-100)": "QQQ", "VOO (S&P 500)": "VOO",
}


def fetch_daily(ticker):
    """(dates, closes) of adjusted daily closes from Yahoo, START..now. None on fail."""
    p1 = int(time.mktime(dt.datetime.strptime(START, "%Y-%m-%d").timetuple()))
    p2 = int(time.time())
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
           f"?period1={p1}&period2={p2}&interval=1d")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.load(r)
        res = d["chart"]["result"][0]
        ts = res["timestamp"]
        cl = res["indicators"]["quote"][0]["close"]
        out = [(dt.date.fromtimestamp(t), c) for t, c in zip(ts, cl) if c]
        return out
    except Exception as e:
        print(f"  [recovery] {ticker} fetch failed: {e}", file=sys.stderr)
        return None


def episodes(series):
    """Non-overlapping >25% drawdown episodes. Each: (depth, recovery_months or None,
    censor_months). Recovery is trough -> reclaim prior peak (matches the engine)."""
    if not series or len(series) < 30:
        return []
    end = series[-1][0]
    out = []
    peak_d, peak = series[0]
    in_dd = False
    trough_d, trough = peak_d, peak
    for d, c in series[1:]:
        if not in_dd:
            if c > peak:
                peak, peak_d = c, d
            elif c <= peak * (1 - THRESH):
                in_dd, trough, trough_d = True, c, d
        else:
            if c < trough:
                trough, trough_d = c, d
            if c >= peak:                       # reclaimed prior peak
                rec_m = (d - trough_d).days / 30.44
                out.append((1 - trough / peak, rec_m, None))
                in_dd, peak, peak_d = False, c, d
    if in_dd:                                    # censored — not recovered by end of data
        out.append((1 - trough / peak, None, (end - trough_d).days / 30.44))
    return out


def realized_cdf(all_eps):
    """P(recovered within h | fell >25%) with proper censoring per horizon."""
    cdf, ns = {}, {}
    for h in HORIZONS:
        num = den = 0
        for depth, rec_m, censor_m in all_eps:
            if rec_m is not None:
                den += 1
                if rec_m <= h:
                    num += 1
            elif censor_m is not None and censor_m >= h:
                den += 1                         # known: not recovered by h
        cdf[str(h)] = round(num / den, 3) if den else None
        ns[str(h)] = den
    return cdf, ns


def predicted_cdf(names):
    """Model's avg predicted recovery curve over the backtest names (12m-fall row)."""
    try:
        rc = json.load(open(os.path.join(HERE, "results.json")))["companies"]["recovery_cond"]
    except Exception:
        return {}
    acc = {h: [] for h in HORIZONS}
    for nm in names:
        m = (rc.get(nm) or {}).get("dd_recovery_matrix", {}).get("12m")
        if not m:
            continue
        for h in HORIZONS:
            v = m.get(f"recover_{h}m")
            if v is not None:
                acc[h].append(v)
    return {str(h): (round(sum(v) / len(v), 3) if v else None) for h, v in acc.items()}


def main():
    all_eps, used, sample = [], [], []
    for name, tk in TICKERS.items():
        s = fetch_daily(tk)
        time.sleep(1.0)                          # be polite to Yahoo
        if not s:
            continue
        eps = episodes(s)
        if not eps:
            continue
        used.append(name)
        all_eps.extend(eps)
        for depth, rec_m, censor_m in eps:
            sample.append({"name": name, "depth": round(depth, 3),
                           "recovery_months": (round(rec_m, 1) if rec_m is not None else None),
                           "censored": rec_m is None})
        print(f"  [recovery] {name} ({tk}): {len(eps)} drawdown episode(s)")

    realized, ns = realized_cdf(all_eps)
    predicted = predicted_cdf(used)
    out = {
        "as_of": dt.date.today().isoformat(), "since": START[:4],
        "n_names": len(used), "n_episodes": len(all_eps),
        "horizons_m": HORIZONS, "realized": realized, "n_at_horizon": ns,
        "predicted": predicted, "names": used,
        "episodes": sorted(sample, key=lambda e: -e["depth"])[:40],
        "note": ("Validates recovery TIMING against real history. Small, survivorship-biased "
                 "sample; realized paths are single draws; censored episodes counted only where "
                 "the outcome at that horizon is known. Research model — not investment advice."),
    }
    json.dump(out, open(os.path.join(HERE, "backtest_recovery.json"), "w"), indent=1)
    print(f"[recovery] wrote backtest_recovery.json: {len(all_eps)} episodes across {len(used)} names")
    print(f"  realized recovered-within: {realized}")
    print(f"  model predicted:           {predicted}")


if __name__ == "__main__":
    main()
