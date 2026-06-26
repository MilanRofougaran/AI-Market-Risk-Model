"""
execution_cost.py -- the EXECUTION CHASM check (Gemini red-team 3.C).

The Basket Builder can show a multi-leg custom OPTION basket with better SURVIVAL metrics than a
liquid ETF (SMH). But executing N separate option legs incurs bid/ask slippage + commission that a
single liquid ETF option does not -- and that drag can ERASE the Volatility Risk Premium edge the
model found. broker_bridge checks ONE contract's spread; nothing aggregated the COMBINED execution
cost of a basket and netted it against the modeled edge. This module does exactly that.

It uses the per-leg spread/OI data broker_bridge already consumes (half-spread = (ask-bid)/2 per
contract crossed) -- NO new fabricated inputs. It needs REAL quotes (refuses source='EXAMPLE').
The aggregation + ETF-proxy comparison logic is what's new. RESEARCH MODEL -- NOT INVESTMENT ADVICE;
it sizes nothing and places no orders.
"""
from broker_bridge import OptionQuote


def leg_execution_cost(quote: OptionQuote, contracts=1, commission_per_contract=0.65):
    """Cost to OPEN one leg: half-spread slippage (crossing the spread) + commission.
    Returns dollars and the drag as % of the leg's premium and % of underlying notional."""
    if quote.source == "EXAMPLE":
        raise ValueError("EXAMPLE quote -- supply a REAL broker quote; this module won't price invented data.")
    half_spread = max(0.0, (quote.ask - quote.bid) / 2.0)
    slippage = half_spread * 100.0 * contracts           # 100 shares / contract
    commission = commission_per_contract * contracts
    premium = quote.mid * 100.0 * contracts
    notional = quote.spot * 100.0 * contracts
    total = slippage + commission
    return {"underlying": quote.underlying, "contracts": contracts,
            "slippage_$": round(slippage, 2), "commission_$": round(commission, 2),
            "total_cost_$": round(total, 2), "premium_$": round(premium, 2),
            "cost_pct_of_premium": round(100 * total / premium, 2) if premium > 0 else None,
            "cost_pct_of_notional": round(100 * total / notional, 3) if notional > 0 else None,
            "spread_pct": round(quote.spread_pct, 3)}


def basket_execution_cost(legs, commission_per_contract=0.65):
    """legs: list of (OptionQuote, contracts). Sums execution cost across all legs."""
    per = [leg_execution_cost(q, c, commission_per_contract) for q, c in legs]
    tot_cost = sum(p["total_cost_$"] for p in per)
    tot_prem = sum(p["premium_$"] for p in per)
    tot_notional = sum(q.spot * 100.0 * c for q, c in legs)
    return {"n_legs": len(legs), "per_leg": per,
            "total_cost_$": round(tot_cost, 2), "total_premium_$": round(tot_prem, 2),
            "drag_pct_of_premium": round(100 * tot_cost / tot_prem, 2) if tot_prem > 0 else None,
            "drag_pct_of_notional": round(100 * tot_cost / tot_notional, 3) if tot_notional > 0 else None}


def compare_to_proxy(basket_legs, proxy_quote: OptionQuote, proxy_contracts,
                     basket_vrp_pct, proxy_vrp_pct, commission_per_contract=0.65):
    """The execution-chasm verdict. Nets the basket's MODELED edge over the ETF proxy against the
    INCREMENTAL execution drag of trading N legs instead of one liquid ETF option.

      modeled_advantage = basket_vrp_pct - proxy_vrp_pct      (fundamental edge the model found)
      incremental_drag  = basket_drag%   - proxy_drag%        (extra slippage+commission you pay)
      net_edge          = modeled_advantage - incremental_drag

    If incremental_drag >= modeled_advantage -> execution ERASES the edge -> the ETF proxy is the
    better EXPRESSION even though the custom basket is fundamentally safer. (basket/proxy VRP% come
    from broker_bridge.volatility_risk_premium on real quotes.)"""
    b = basket_execution_cost(basket_legs, commission_per_contract)
    p = leg_execution_cost(proxy_quote, proxy_contracts, commission_per_contract)
    basket_drag = b["drag_pct_of_premium"]; proxy_drag = p["cost_pct_of_premium"]
    if basket_drag is None or proxy_drag is None:
        return {"error": "missing premium to compute drag"}
    modeled_adv = basket_vrp_pct - proxy_vrp_pct
    incr_drag = basket_drag - proxy_drag
    net = modeled_adv - incr_drag
    if incr_drag >= modeled_adv:
        verdict = ("EXECUTION ERASES THE EDGE -> trade the ETF proxy. The custom basket is "
                   "fundamentally safer, but its incremental slippage exceeds its modeled VRP advantage.")
    elif net < modeled_adv * 0.5:
        verdict = ("edge SURVIVES but is HALVED by execution drag -- weigh the basket's survival "
                   "benefit against the slippage you keep paying.")
    else:
        verdict = "edge survives execution drag -- the custom basket remains the better expression."
    return {"basket_drag_pct_of_premium": basket_drag, "proxy_drag_pct_of_premium": proxy_drag,
            "incremental_drag_pct": round(incr_drag, 2),
            "modeled_advantage_pct": round(modeled_adv, 2), "net_edge_pct": round(net, 2),
            "verdict": verdict, "basket_detail": b, "proxy_detail": p,
            "disclaimer": "RESEARCH MODEL -- NOT INVESTMENT ADVICE. Execution-cost diagnostic; no sizing, no order."}


if __name__ == "__main__":
    print("EXECUTION COST AGGREGATOR -- does multi-leg slippage erase the basket's modeled edge?")
    print("In real use this needs LIVE broker quotes (the function refuses source='EXAMPLE').")
    print(">>> The numbers below are DUMMY DEMONSTRATION VALUES (hand-typed, NOT live broker data) <<<")
    print(">>> shown only to exercise the math; do NOT read the verdict as a real trade signal.\n")
    # DUMMY demo: a 4-leg custom basket of long calls (wider spreads / thinner names) vs one liquid SMH
    # option. source="broker" only so the gate doesn't refuse it; these spreads/OI are invented, not real.
    mk = lambda u, spot, k, bid, ask: OptionQuote(underlying=u, spot=spot, strike=k, days_to_expiry=540,
                    bid=bid, ask=ask, iv=0.5, iv_rank=45, open_interest=800, volume=60, source="broker")
    legs = [(mk("NVDA", 205, 150, 70.0, 71.2), 1), (mk("AMD", 160, 120, 48.0, 49.6), 1),
            (mk("MRVL", 95, 70, 30.0, 31.4), 1), (mk("ALAB", 100, 75, 33.0, 35.0), 1)]
    proxy = mk("SMH", 280, 210, 82.0, 82.6)                     # tight, liquid ETF option (DUMMY)
    # DUMMY assumption: suppose the model found the basket ~3.0 pts cheaper-vs-fair than the SMH proxy
    res = compare_to_proxy(legs, proxy, 1, basket_vrp_pct=11.0, proxy_vrp_pct=8.0)
    print(f"  [DUMMY] basket drag {res['basket_drag_pct_of_premium']}% of premium vs proxy {res['proxy_drag_pct_of_premium']}%")
    print(f"  [DUMMY] modeled advantage {res['modeled_advantage_pct']}%  -  incremental drag {res['incremental_drag_pct']}%  =  net {res['net_edge_pct']}%")
    print(f"  [DUMMY] VERDICT: {res['verdict']}   (illustrative only -- run with real quotes for a real verdict)")
    print("\nRESEARCH MODEL -- NOT INVESTMENT ADVICE.")
