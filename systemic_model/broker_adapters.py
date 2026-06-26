"""
broker_adapters.py -- pluggable market-data adapters that populate a
broker_bridge.OptionQuote from a LIVE API. Pick a provider at runtime.

  IV RANK is COMPUTED FROM HISTORY (no vendor): true history where the API exposes it
  (IBKR), else a local daily IV log you accumulate, else a realized-vol PROXY clearly
  flagged in the quote's `source`.
  The EARNINGS / event date is MANUAL -- you pass next_event_days (it is on no option chain).

==============================  HARD HONESTY  ==============================
This CANNOT run inside the model sandbox (no network to broker/market hosts) and is
NEVER exercised against live data here. Run it in YOUR environment with YOUR API key;
I never see the key or the data. Functions raise loudly when a key is missing or a field
cannot be established -- they do NOT silently hand a half-empty quote to the gate.
API endpoint/field names below match each provider's documented schema AS KNOWN, but
APIs drift: VERIFY against current docs; the field-mapping is isolated per adapter so a
mapping fix never touches the logic. RESEARCH MODEL -- NOT INVESTMENT ADVICE.
===========================================================================
"""
import os, json, math, datetime as dt
from typing import Optional, List
from broker_bridge import OptionQuote

PROVIDERS = ("tradier", "polygon", "ibkr", "schwab")

# ----------------------------------------------------------------------------
# IV RANK FROM HISTORY  (the part you chose to compute yourself)
# ----------------------------------------------------------------------------
def iv_rank_from_history(current_iv: float, iv_history: List[float]):
    """IV rank + percentile from a list of past IV observations (decimals).
    rank = (iv - min)/(max - min)*100 ; percentile = % of history below current iv.
    Needs a meaningful history (>= ~60 obs for a usable 52-wk-style read)."""
    hist = [float(x) for x in iv_history if x is not None and x > 0]
    if len(hist) < 20:
        raise ValueError(f"IV history too short ({len(hist)} obs) to compute a rank; "
                         "log more daily IVs or use the realized-vol proxy explicitly.")
    lo, hi = min(hist), max(hist)
    rank = 100.0 * (current_iv - lo) / (hi - lo) if hi > lo else 50.0
    pctile = 100.0 * sum(1 for x in hist if x < current_iv) / len(hist)
    return {"iv_rank": round(max(0.0, min(100.0, rank)), 1),
            "iv_percentile": round(pctile, 1), "n_obs": len(hist)}


def realized_vol_proxy(close_prices: List[float], window: int = 252):
    """Annualized realized volatility from underlying closes -- a PROXY for IV when no
    true IV history exists. Returns the latest RV and an RV history (for ranking).
    NOTE: realized vol != implied vol; the iv_richness gate on this is approximate."""
    px = [float(p) for p in close_prices if p and p > 0]
    if len(px) < 30:
        raise ValueError("Need >= 30 closes for a realized-vol proxy.")
    rets = [math.log(px[i] / px[i - 1]) for i in range(1, len(px))]
    rv_hist = []
    for i in range(20, len(rets) + 1):
        w = rets[max(0, i - 20):i]
        mu = sum(w) / len(w)
        var = sum((r - mu) ** 2 for r in w) / (len(w) - 1)
        rv_hist.append(math.sqrt(var * 252))
    return {"rv_latest": rv_hist[-1], "rv_history": rv_hist[-window:]}


class IVHistoryStore:
    """Append-only local log of daily IV per ticker, so you ACCUMULATE real IV history
    over time for providers without an IV-history endpoint (Tradier/Polygon/Schwab).
    Run your fetch daily; rank quality improves as the log fills."""
    def __init__(self, path="iv_history.json"):
        self.path = path
        try:
            with open(path) as f: self.data = json.load(f)
        except Exception:
            self.data = {}

    def log(self, ticker, iv, date=None):
        date = date or dt.date.today().isoformat()
        self.data.setdefault(ticker.upper(), {})[date] = float(iv)
        with open(self.path, "w") as f: json.dump(self.data, f, indent=0)

    def history(self, ticker):
        return list(self.data.get(ticker.upper(), {}).values())


# ----------------------------------------------------------------------------
# PROVIDER ADAPTERS  -- each returns a normalized partial dict (chain fields + current IV).
# Live network calls; run in YOUR env. `requests`/`ib_insync` imported lazily so this
# module imports fine without them installed.
# ----------------------------------------------------------------------------
def _occ_symbol(ticker, expiry: str, strike: float, right: str = "C"):
    """OCC-style option symbol, e.g. NVDA260116C00150000 (expiry 'YYYY-MM-DD')."""
    y, m, d = expiry.split("-")
    return f"{ticker.upper()}{y[2:]}{m}{d}{right}{int(round(strike*1000)):08d}"


def fetch_tradier(ticker, expiry, strike, right="C", token=None):
    """Tradier Brokerage API. token = your access token. VERIFY fields vs current docs.
    GET /v1/markets/options/chains?symbol=&expiration=&greeks=true ; greeks are ORATS,
    refreshed ~overnight. No IV-history endpoint -> use IVHistoryStore / proxy."""
    import requests
    token = token or os.environ.get("TRADIER_TOKEN")
    if not token: raise RuntimeError("Set TRADIER_TOKEN (env or arg).")
    base = "https://api.tradier.com/v1/markets"
    h = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    chain = requests.get(f"{base}/options/chains", headers=h,
                         params={"symbol": ticker, "expiration": expiry, "greeks": "true"}).json()
    opts = (chain.get("options") or {}).get("option") or []
    o = next((x for x in opts if abs(x["strike"] - strike) < 1e-6
              and x["option_type"].upper().startswith(right)), None)
    if o is None: raise LookupError(f"contract not found: {ticker} {expiry} {strike}{right}")
    g = o.get("greeks") or {}
    spot = requests.get(f"{base}/quotes", headers=h, params={"symbols": ticker}).json()
    spot = spot["quotes"]["quote"]["last"]
    return {"underlying": ticker, "spot": float(spot), "strike": float(o["strike"]),
            "bid": float(o["bid"]), "ask": float(o["ask"]),
            "iv": float(g.get("mid_iv") or g.get("smv_vol") or 0) or None,
            "delta": g.get("delta"), "theta": g.get("theta"), "vega": g.get("vega"),
            "open_interest": int(o.get("open_interest") or 0), "volume": int(o.get("volume") or 0)}


def fetch_polygon(ticker, expiry, strike, right="C", api_key=None):
    """Polygon.io options snapshot (greeks/IV require a paid plan). VERIFY vs current docs.
    GET /v3/snapshot/options/{under}/{O:contract}. No IV-history endpoint -> store/proxy."""
    import requests
    api_key = api_key or os.environ.get("POLYGON_API_KEY")
    if not api_key: raise RuntimeError("Set POLYGON_API_KEY (env or arg).")
    contract = "O:" + _occ_symbol(ticker, expiry, strike, right)
    r = requests.get(f"https://api.polygon.io/v3/snapshot/options/{ticker.upper()}/{contract}",
                     params={"apiKey": api_key}).json()
    res = r.get("results")
    if not res: raise LookupError(f"contract not found / no entitlement: {contract}")
    lq = res.get("last_quote") or {}; g = res.get("greeks") or {}
    ua = (res.get("underlying_asset") or {})
    spot = ua.get("price") or ua.get("last_updated_price")
    if spot is None:
        spot = requests.get(f"https://api.polygon.io/v2/aggs/ticker/{ticker.upper()}/prev",
                            params={"apiKey": api_key}).json()["results"][0]["c"]
    return {"underlying": ticker, "spot": float(spot), "strike": float(res["details"]["strike_price"]),
            "bid": float(lq.get("bid") or 0), "ask": float(lq.get("ask") or 0),
            "iv": res.get("implied_volatility"),
            "delta": g.get("delta"), "theta": g.get("theta"), "vega": g.get("vega"),
            "open_interest": int(res.get("open_interest") or 0),
            "volume": int((res.get("day") or {}).get("volume") or 0)}


def fetch_ibkr(ticker, expiry, strike, right="C", host="127.0.0.1", port=7497, client_id=11,
               iv_history_days="1 Y"):
    """Interactive Brokers via ib_insync. TWS / IB Gateway must be running and logged in.
    UNIQUELY gives a real historical IV series (whatToShow='OPTION_IMPLIED_VOLATILITY' on
    the underlying) -> true IV rank, returned in 'iv_history'."""
    from ib_insync import IB, Option, Stock
    exp = expiry.replace("-", "")
    ib = IB(); ib.connect(host, port, clientId=client_id)
    try:
        opt = Option(ticker.upper(), exp, float(strike), right, "SMART")
        ib.qualifyContracts(opt)
        t = ib.reqMktData(opt, genericTickList="101", snapshot=False); ib.sleep(2.5)
        und = Stock(ticker.upper(), "SMART", "USD"); ib.qualifyContracts(und)
        ut = ib.reqMktData(und); ib.sleep(1.0)
        mg = t.modelGreeks
        bars = ib.reqHistoricalData(und, "", iv_history_days, "1 day",
                                    "OPTION_IMPLIED_VOLATILITY", useRTH=True)
        iv_hist = [b.close for b in bars if b.close and b.close > 0]
        oi = (t.callOpenInterest if right == "C" else t.putOpenInterest)
        return {"underlying": ticker, "spot": float(ut.last or ut.close),
                "strike": float(strike),
                "bid": float(t.bid or 0), "ask": float(t.ask or 0),
                "iv": float(mg.impliedVol) if mg else None,
                "delta": (mg.delta if mg else None), "theta": (mg.theta if mg else None),
                "vega": (mg.vega if mg else None),
                "open_interest": int(oi or 0), "volume": int(t.volume or 0),
                "iv_history": iv_hist}
    finally:
        ib.disconnect()


def fetch_schwab(ticker, expiry, strike, right="C", access_token=None):
    """Schwab Trader API (OAuth bearer; successor to TDA). VERIFY vs current docs.
    GET /marketdata/v1/chains?symbol=&contractType=&strike=&fromDate=&toDate=. `volatility`
    is IV in PERCENT (converted to decimal here). No IV-history endpoint -> store/proxy."""
    import requests
    access_token = access_token or os.environ.get("SCHWAB_ACCESS_TOKEN")
    if not access_token: raise RuntimeError("Set SCHWAB_ACCESS_TOKEN (OAuth bearer).")
    h = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
    ctype = "CALL" if right == "C" else "PUT"
    r = requests.get("https://api.schwabapi.com/marketdata/v1/chains", headers=h,
                     params={"symbol": ticker.upper(), "contractType": ctype,
                             "strike": strike, "fromDate": expiry, "toDate": expiry}).json()
    mp = r.get("callExpDateMap" if right == "C" else "putExpDateMap") or {}
    o = None
    for _exp, strikes in mp.items():
        for _k, lst in strikes.items():
            if lst and abs(float(lst[0]["strikePrice"]) - strike) < 1e-6:
                o = lst[0]; break
    if o is None: raise LookupError(f"contract not found: {ticker} {expiry} {strike}{right}")
    spot = r.get("underlyingPrice") or (r.get("underlying") or {}).get("last")
    ivpct = o.get("volatility")
    return {"underlying": ticker, "spot": float(spot), "strike": float(o["strikePrice"]),
            "bid": float(o["bid"]), "ask": float(o["ask"]),
            "iv": (float(ivpct) / 100.0 if ivpct not in (None, "NaN") else None),
            "delta": o.get("delta"), "theta": o.get("theta"), "vega": o.get("vega"),
            "open_interest": int(o.get("openInterest") or 0),
            "volume": int(o.get("totalVolume") or 0)}


_DISPATCH = {"tradier": fetch_tradier, "polygon": fetch_polygon,
             "ibkr": fetch_ibkr, "schwab": fetch_schwab}


# ----------------------------------------------------------------------------
# ASSEMBLE -> a fully-populated, gate-ready OptionQuote
# ----------------------------------------------------------------------------
def get_option_quote(provider, ticker, expiry, strike, right="C", *,
                     next_event_days: Optional[int],     # MANUAL: earnings/event days (None if none)
                     is_net_debit: bool = True,
                     iv_store: Optional[IVHistoryStore] = None,
                     underlying_closes: Optional[List[float]] = None,
                     allow_rv_proxy: bool = False,
                     **creds):
    """Fetch one contract from `provider` and return a gate-ready OptionQuote.
    IV RANK resolution order: (1) provider's own IV history (IBKR) -> true rank;
    (2) IVHistoryStore log (+ today's IV appended) -> true rank as it fills;
    (3) realized-vol PROXY from underlying_closes IF allow_rv_proxy -> flagged in `source`.
    If none available -> RAISE (never leaves iv_rank unset). next_event_days is MANUAL."""
    provider = provider.lower()
    if provider not in _DISPATCH:
        raise ValueError(f"provider must be one of {PROVIDERS}")
    raw = _DISPATCH[provider](ticker, expiry, strike, right, **creds)
    if not raw.get("iv"):
        raise ValueError("No current IV from the provider for this contract; cannot run the IV gate.")
    cur_iv = float(raw["iv"])

    iv_rank = iv_pctile = None
    src = f"broker:{provider}"
    iv_hist = raw.pop("iv_history", None)
    if iv_hist and len(iv_hist) >= 20:                       # (1) provider IV history (IBKR)
        rr = iv_rank_from_history(cur_iv, iv_hist); iv_rank, iv_pctile = rr["iv_rank"], rr["iv_percentile"]
        src += "(iv_rank=true:provider_hist)"
    elif iv_store is not None:                               # (2) local accumulated log
        iv_store.log(ticker, cur_iv)
        hist = iv_store.history(ticker)
        if len(hist) >= 20:
            rr = iv_rank_from_history(cur_iv, hist); iv_rank, iv_pctile = rr["iv_rank"], rr["iv_percentile"]
            src += f"(iv_rank=true:local_log_n{len(hist)})"
    if iv_rank is None and allow_rv_proxy and underlying_closes:   # (3) realized-vol PROXY
        rv = realized_vol_proxy(underlying_closes)
        rr = iv_rank_from_history(rv["rv_latest"], rv["rv_history"])
        iv_rank, iv_pctile = rr["iv_rank"], rr["iv_percentile"]
        src += "(iv_rank=RV_PROXY:approx!)"
    if iv_rank is None:
        raise ValueError(
            "Could not establish IV rank. Options: pass an IVHistoryStore and run daily until it "
            "fills (>=20 obs), use IBKR (native IV history), or set allow_rv_proxy=True with "
            "underlying_closes for an approximate realized-vol proxy. Refusing to leave the IV gate "
            "un-evaluated.")

    return OptionQuote(
        underlying=raw["underlying"], spot=raw["spot"], strike=raw["strike"],
        days_to_expiry=(dt.date.fromisoformat(expiry) - dt.date.today()).days,
        bid=raw["bid"], ask=raw["ask"], iv=cur_iv, iv_rank=iv_rank, iv_percentile=iv_pctile,
        delta=raw.get("delta"), theta=raw.get("theta"), vega=raw.get("vega"),
        open_interest=raw["open_interest"], volume=raw["volume"],
        next_event_days=next_event_days, is_net_debit=is_net_debit, source=src)


def select_provider():
    print("Market-data providers:")
    for i, p in enumerate(PROVIDERS, 1):
        note = {"ibkr": " (native IV history -> true IV rank; needs TWS/Gateway running)",
                "tradier": " (REST; IV via ORATS greeks; needs IV log or proxy for rank)",
                "polygon": " (REST; IV/greeks on paid plan; needs IV log or proxy for rank)",
                "schwab": " (OAuth; IV=volatility%; needs IV log or proxy for rank)"}[p]
        print(f"  {i}. {p}{note}")
    return PROVIDERS[int(input("Select [1-4]: ").strip()) - 1]


if __name__ == "__main__":
    print(__doc__)
    print("Example (run in YOUR environment, TWS/Gateway up for ibkr):\n")
    print("  from broker_adapters import get_option_quote, IVHistoryStore, select_provider")
    print("  from broker_bridge import trade_quality")
    print("  prov = select_provider()                       # or 'ibkr' / 'tradier' / ...")
    print("  store = IVHistoryStore('iv_history.json')       # accumulate IV daily (non-IBKR)")
    print("  q = get_option_quote(prov, 'NVDA', '2028-01-21', 150, 'C',")
    print("                       next_event_days=None,      # MANUAL earnings/event days")
    print("                       iv_store=store, allow_rv_proxy=False)")
    print("  # model_fair_pct from premium_check.py for that contract; model_verdict from step 2")
    print("  print(trade_quality(model_fair_pct, model_verdict, q))")
    print("\nIV rank is COMPUTED FROM HISTORY; the earnings date is MANUAL. No fabricated data.")
