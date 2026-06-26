// ============================================================================
//  exec-cost.mjs — multi-leg execution-cost check (live bid/ask slippage).
//  Endpoint: /.netlify/functions/exec-cost
//     ?underlying=NVDA&long_occ=O:...&short_strike=315&expiry=2027-12-17
//  Sums the half-spread slippage you'd cross on BOTH legs of a debit spread,
//  as a % of the share price, and reports each leg's liquidity. The browser
//  compares that to the spread's modeled edge ("if slippage eats the edge,
//  trade the liquid ETF instead"). POLYGON_KEY stays server-side.
//  Research model — not investment advice.
// ============================================================================
const CORS = {
  "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "Content-Type",
  "Content-Type": "application/json",
};
const ok = (o) => ({ statusCode: 200, headers: CORS, body: JSON.stringify(o) });
const err = (c, m) => ({ statusCode: c, headers: CORS, body: JSON.stringify({ error: m }) });

async function optQuote(underlying, occ, key) {
  const j = await (await fetch(
    `https://api.polygon.io/v3/snapshot/options/${underlying}/${occ}?apiKey=${key}`)).json();
  const r = j.results || {}, lq = r.last_quote || {}, day = r.day || {};
  const bid = lq.bid, ask = lq.ask;
  const half = (bid != null && ask != null && ask >= bid) ? (ask - bid) / 2 : null;
  const mid = (bid != null && ask != null) ? (bid + ask) / 2 : (r.last_trade?.price ?? day.close ?? null);
  return { occ, bid, ask, half, mid, oi: r.open_interest ?? null, volume: day.volume ?? null };
}
async function resolveCall(underlying, expiry, strike, key) {
  const lo = (strike * 0.9).toFixed(0), hi = (strike * 1.1).toFixed(0);
  const j = await (await fetch(
    `https://api.polygon.io/v3/reference/options/contracts?underlying_ticker=${underlying}`
    + `&contract_type=call&expiration_date=${expiry}&strike_price.gte=${lo}&strike_price.lte=${hi}`
    + `&limit=50&apiKey=${key}`)).json();
  const cs = j.results || [];
  if (!cs.length) return null;
  cs.sort((a, b) => Math.abs(a.strike_price - strike) - Math.abs(b.strike_price - strike));
  return cs[0].ticker;
}

export async function handler(event) {
  if (event.httpMethod === "OPTIONS") return { statusCode: 204, headers: CORS, body: "" };
  const q = event.queryStringParameters || {};
  const key = process.env.POLYGON_KEY;
  if (!key) return err(501, "POLYGON_KEY not set");
  const { underlying, long_occ, short_strike, expiry } = q;
  if (!underlying || !long_occ || !short_strike || !expiry) return err(400, "need underlying, long_occ, short_strike, expiry");
  try {
    const longQ = await optQuote(underlying, long_occ, key);
    const shortOcc = await resolveCall(underlying, expiry, parseFloat(short_strike), key);
    const shortQ = shortOcc ? await optQuote(underlying, shortOcc, key) : null;
    // spot from underlying prev close (to express slippage as % of share price)
    const pv = await (await fetch(`https://api.polygon.io/v2/aggs/ticker/${underlying}/prev?apiKey=${key}`)).json();
    const spot = (pv.results || [])[0]?.c ?? null;
    const legHalf = (longQ.half ?? 0) + (shortQ?.half ?? 0);
    const slippage_pct = (spot && (longQ.half != null || shortQ?.half != null)) ? (legHalf / spot) * 100 : null;
    return ok({
      spot, long: longQ, short: shortQ,
      slippage_pts: slippage_pct == null ? null : +slippage_pct.toFixed(2),
      both_quoted: longQ.half != null && shortQ?.half != null,
      etf_note: "Liquid sector ETFs (e.g. SMH) trade at a few basis points — far less than a two-leg option spread.",
    });
  } catch (e) {
    return err(502, String(e));
  }
}
