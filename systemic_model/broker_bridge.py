"""
broker_bridge.py -- STEP 3 of the trade workflow: the bridge between the model's
thesis-conditional fair value and live broker/market reality (IV, Greeks, bid/ask,
liquidity, event risk).

   model (steps 1-2)  ->  "good UNDER THESIS at this price vs fundamental fair value"
   THIS MODULE (step 3) -> "good TRADE at today's market price?"   <-- the veto layer
   you (step 4)        ->  sizing + final decision

================================  HARD HONESTY  ================================
This module does NOT contain, fetch, estimate, or synthesize implied volatility, the
Greeks, skew, the IV surface, or event dates. The model is PHYSICAL-MEASURE and IV-BLIND.
There is no live options feed here. Inventing IV would make the model LOOK like it sees
volatility when it is guessing -- strictly worse than honest blindness.

So this module is an ADAPTER: YOU paste in a real option quote from YOUR broker
(Schwab/IBKR/Tradier/etc.); it then does the math that is only valid once the data is
real -- the Volatility Risk Premium and the IV-richness / event-crush / liquidity vetoes.
With no quote, it returns the DATA CONTRACT and refuses to render a verdict.

A positive model edge does NOT pass a failed gate. Both screens (model + market) must
pass. RESEARCH MODEL -- NOT INVESTMENT ADVICE. This renders a gate, never a buy signal;
it does not size positions or endorse orders.
==============================================================================
"""
from dataclasses import dataclass, asdict, field
from typing import Optional

# ---- the data contract: exactly what YOU must supply from your broker --------
REQUIRED_FIELDS = {
    "underlying":        "ticker (e.g. NVDA)",
    "spot":              "current underlying price ($)",
    "strike":            "option strike ($)",
    "days_to_expiry":    "calendar days to expiration",
    "bid":               "option bid ($, per share)",
    "ask":               "option ask ($, per share)",
    "iv":                "implied volatility of THIS contract (decimal, e.g. 0.55)",
    "iv_rank":           "IV rank 0-100 (where current IV sits in its 52-wk range)",
    "iv_percentile":     "IV percentile 0-100 (optional but better than rank)",
    "delta":             "option delta",
    "theta":             "option theta ($/day, usually negative for longs)",
    "vega":              "option vega ($ per 1 vol point)",
    "open_interest":     "contract open interest",
    "volume":            "contract daily volume",
    "next_event_days":   "calendar days to the next binary event (earnings/FDA/macro); None if none before expiry",
    "is_net_debit":      "True if you PAY premium (long call/debit spread/fly/tail-kicker); the model bans most net-credit structures",
}

# ---- veto thresholds (research defaults; tune to your risk tolerance) ---------
SPREAD_PCT_CAUTION = 0.08    # (ask-bid)/mid above this = liquidity caution
SPREAD_PCT_VETO    = 0.15    # above this = untradeable for the model's structures
OI_MIN             = 100     # below this = thin
VOLUME_MIN         = 25      # below this = thin
IV_RANK_CAUTION    = 60      # buying premium above this rank = paying up for vol
IV_RANK_VETO       = 85      # buying premium this rich = IV-crush trap for a net-debit buyer


@dataclass
class OptionQuote:
    underlying: str
    spot: float
    strike: float
    days_to_expiry: int
    bid: float
    ask: float
    iv: float
    iv_rank: float
    delta: float = None
    theta: float = None
    vega: float = None
    open_interest: int = 0
    volume: int = 0
    iv_percentile: Optional[float] = None
    next_event_days: Optional[int] = None
    is_net_debit: bool = True
    source: str = "UNSPECIFIED"     # set to "EXAMPLE" to mark fabricated/demo data

    @property
    def mid(self):
        return (self.bid + self.ask) / 2.0

    @property
    def spread_pct(self):
        m = self.mid
        return (self.ask - self.bid) / m if m > 0 else float("inf")

    @property
    def mid_pct_of_spot(self):
        return 100.0 * self.mid / self.spot if self.spot else None


def volatility_risk_premium(model_fair_pct_of_spot, quote: OptionQuote):
    """Model PHYSICAL fair value vs the MARKET (risk-neutral) price you'd pay.
    model_fair_pct_of_spot comes from premium_check.py / options_lens (physical E[payoff]).
    Positive VRP = cheap vs our thesis-conditional payoff (edge UNDER THESIS, NOT arbitrage:
    physical vs risk-neutral). It is necessary but NOT sufficient -- it must still clear the
    IV-richness, event, and liquidity gates below."""
    market = quote.mid_pct_of_spot
    if market is None or model_fair_pct_of_spot is None:
        return None
    vrp_pts = model_fair_pct_of_spot - market
    vrp_ratio = (model_fair_pct_of_spot / market) if market > 0 else None
    return {"model_fair_pct": round(model_fair_pct_of_spot, 2),
            "market_mid_pct": round(market, 2),
            "vrp_points": round(vrp_pts, 2),
            "vrp_ratio": round(vrp_ratio, 2) if vrp_ratio else None,
            "edge_under_thesis": vrp_pts > 0}


def liquidity_gate(q: OptionQuote):
    sp = q.spread_pct
    if sp >= SPREAD_PCT_VETO or q.open_interest < OI_MIN or q.volume < VOLUME_MIN:
        status = "VETO"
    elif sp >= SPREAD_PCT_CAUTION:
        status = "CAUTION"
    else:
        status = "PASS"
    return {"gate": "liquidity", "status": status, "spread_pct": round(sp, 3),
            "open_interest": q.open_interest, "volume": q.volume}


def iv_richness_gate(q: OptionQuote):
    # For a NET-DEBIT buyer (the model's allowed structures), high IV = overpaying vol.
    rank = q.iv_percentile if q.iv_percentile is not None else q.iv_rank
    if not q.is_net_debit:
        return {"gate": "iv_richness", "status": "N/A (net-credit; model bans most of these)", "iv_rank": rank}
    if rank >= IV_RANK_VETO:
        status = "VETO"
    elif rank >= IV_RANK_CAUTION:
        status = "CAUTION"
    else:
        status = "PASS"
    return {"gate": "iv_richness", "status": status, "iv": q.iv, "iv_rank_or_pctile": rank,
            "note": "buying premium into rich IV invites IV-crush; the model is blind to this"}


def event_gate(q: OptionQuote):
    # A binary event (earnings/FDA/macro) inside the holding window crushes IV for a long.
    if q.next_event_days is None:
        return {"gate": "event", "status": "PASS", "note": "no binary event before expiry (per your input)"}
    inside = q.next_event_days <= q.days_to_expiry
    if inside and q.is_net_debit:
        status = "CAUTION"   # not an auto-veto: a long can be intentional pre-event, but flag the crush risk
        note = f"binary event in ~{q.next_event_days}d, before expiry ({q.days_to_expiry}d): IV-crush risk for a long"
    elif inside:
        status = "CAUTION"; note = "event before expiry; check vega exposure"
    else:
        status = "PASS"; note = "event falls after expiry"
    return {"gate": "event", "status": status, "next_event_days": q.next_event_days, "note": note}


def trade_quality(model_fair_pct_of_spot, model_verdict, quote: OptionQuote):
    """Combine the model verdict (step 2) with the market vetoes (step 3).
    RULE (same as the model's spine): a positive edge does NOT pass a failed gate.
    Returns PASS only if there is edge under thesis AND every gate is non-VETO. Any VETO -> REJECT.
    Any CAUTION -> CONDITIONAL (a human judgment call, smaller size, or wait). NOT a buy signal."""
    if quote.source == "EXAMPLE":
        return {"verdict": "REFUSED",
                "reason": "Quote is flagged source='EXAMPLE' (demo/fabricated). Replace with a REAL broker "
                          "quote before this renders a verdict. This module will not assess invented IV."}
    vrp = volatility_risk_premium(model_fair_pct_of_spot, quote)
    gates = [liquidity_gate(quote), iv_richness_gate(quote), event_gate(quote)]
    statuses = [g["status"] for g in gates]
    any_veto = any(s == "VETO" for s in statuses)
    any_caution = any(s.startswith("CAUTION") for s in statuses)
    edge = vrp and vrp["edge_under_thesis"]

    if any_veto:
        verdict = "REJECT (market gate veto)"
    elif not edge:
        verdict = "REJECT (no edge under thesis: market price >= model fair)"
    elif model_verdict and "REJECT" in str(model_verdict).upper():
        verdict = "REJECT (model structural gate already failed in step 2)"
    elif any_caution:
        verdict = "CONDITIONAL (edge present, but a market gate is CAUTION -- human call / smaller size / wait)"
    else:
        verdict = "PASS BOTH SCREENS (good under thesis AND market gates clear) -- sizing + final call are YOURS"
    return {"underlying": quote.underlying, "strike": quote.strike, "dte": quote.days_to_expiry,
            "model_verdict_step2": model_verdict, "vrp": vrp, "gates": gates, "verdict": verdict,
            "disclaimer": "RESEARCH MODEL -- NOT INVESTMENT ADVICE. A gate, not a buy signal. No sizing, no order endorsement."}


def fetch_instructions():
    return (
        "STEP 3 DATA CONTRACT -- paste a REAL option quote (this module invents nothing).\n"
        "Pull these for the exact contract (ticker/strike/expiry) the model selected in steps 1-2:\n\n"
        + "\n".join(f"  - {k:16s} {v}" for k, v in REQUIRED_FIELDS.items())
        + "\n\nSources: your broker's option chain or API --\n"
          "  Schwab/thinkorswim, Interactive Brokers (TWS API / ib_insync), Tradier API, Polygon.io,\n"
          "  ORATS / LiveVol for IV rank/percentile + skew, the company IR page for the earnings date.\n\n"
        "Then:\n"
        "  q = OptionQuote(underlying='NVDA', spot=..., strike=..., days_to_expiry=...,\n"
        "                  bid=..., ask=..., iv=..., iv_rank=..., open_interest=..., volume=...,\n"
        "                  next_event_days=..., is_net_debit=True, source='broker')\n"
        "  print(trade_quality(model_fair_pct, model_verdict_from_premium_check, q))\n\n"
        "model_fair_pct = the fair_value_pct_of_spot for that contract from premium_check.py / options_lens.\n"
        "Until you supply a real quote (source != 'EXAMPLE'), this module renders NO verdict."
    )


if __name__ == "__main__":
    print(fetch_instructions())
    print("\n" + "=" * 70)
    print("DEMO on clearly-flagged EXAMPLE data (module REFUSES to assess it):")
    demo = OptionQuote(underlying="NVDA", spot=205.0, strike=150.0, days_to_expiry=730,
                       bid=70.0, ask=72.0, iv=0.52, iv_rank=48, open_interest=4200, volume=180,
                       next_event_days=40, is_net_debit=True, source="EXAMPLE")
    import json
    # model_fair_pct would come from premium_check (e.g. NVDA deep-ITM ~64.9% at 36m); shown only to exercise the path
    print(json.dumps(trade_quality(64.9, "PASS (secular gate, deep-ITM long)", demo), indent=2, default=str))
    print("\n^ REFUSED because source='EXAMPLE'. Set source='broker' with REAL numbers to get a real verdict.")
