"""
fetch_live.py — pull today's live market numbers (FRED) and write live_inputs.json.
calibration.py merges this in, so the model re-evaluates against today's market on every run.

Run:  FRED_API_KEY=xxxx python3 fetch_live.py
Free FRED key: https://fred.stlouisfed.org/  (My Account -> API Keys)

Daily-available series we pull (the big day-to-day movers of the stress index):
  ust_10y, ust_10y_real, vix, hy_oas_bps, ig_oas_bps, brent_usd, fed_funds_mid
Slow series (CAPE, MOVE, margin debt, forward P/E) aren't daily on FRED — those are
refreshed on the monthly job instead. Missing/holiday values fall back to the last good one.
"""
import os, sys, json, datetime, urllib.request

KEY = os.environ.get("FRED_API_KEY", "").strip()
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "live_inputs.json")

# model field -> (FRED series id, multiplier)   [OAS series are in %, ×100 -> bps]
SERIES = {
    "ust_10y":      ("DGS10", 1),
    "ust_10y_real": ("DFII10", 1),
    "vix":          ("VIXCLS", 1),
    "hy_oas_bps":   ("BAMLH0A0HYM2", 100),
    "ig_oas_bps":   ("BAMLC0A0CM", 100),
    "brent_usd":    ("DCOILBRENTEU", 1),
}

def latest(series_id):
    url = (f"https://api.stlouisfed.org/fred/series/observations?series_id={series_id}"
           f"&api_key={KEY}&file_type=json&sort_order=desc&limit=10")
    with urllib.request.urlopen(url, timeout=30) as r:
        data = json.load(r)
    for o in data.get("observations", []):
        if o.get("value") not in (".", "", None):
            return float(o["value"])
    return None

def main():
    if not KEY:
        print("FRED_API_KEY not set — writing as_of only (no live macro).", file=sys.stderr)
    macro = {}
    if KEY:
        for field, (sid, mult) in SERIES.items():
            try:
                v = latest(sid)
                if v is not None:
                    macro[field] = round(v * mult, 0 if mult != 1 else 3)
            except Exception as e:
                print(f"  warn {sid}: {e}", file=sys.stderr)
        # fed funds midpoint from the target band
        try:
            up, lo = latest("DFEDTARU"), latest("DFEDTARL")
            if up is not None and lo is not None:
                macro["fed_funds_mid"] = round((up + lo) / 2, 3)
        except Exception as e:
            print(f"  warn fed funds: {e}", file=sys.stderr)

    out = {
        "as_of":   datetime.datetime.utcnow().strftime("%Y-%m-%d"),
        "fetched": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "source":  "FRED",
        "macro":   macro,
    }
    json.dump(out, open(OUT, "w"), indent=1)
    print(f"wrote {OUT}")
    print(json.dumps(out, indent=1))

if __name__ == "__main__":
    main()
