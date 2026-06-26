// ============================================================================
//  option-check.mjs — LIVE option metrics for the broker-bridge veto layer.
//  Endpoint: /.netlify/functions/option-check?underlying=NVDA&occ=O:NVDA270617C00150000
//  Returns the RAW live numbers (market price, IV, open interest, volume, bid/ask
//  spread, underlying spot + trailing realized vol). The browser applies the
//  veto thresholds (liquidity / IV-richness / edge) so the logic lives in one
//  place. POLYGON_KEY stays server-side. Research model — not investment advice.
// ============================================================================
const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "Content-Type",
  "Content-Type": "application/json",
};
const ok = (obj) => ({ statusCode: 200, headers: CORS, body: JSON.stringify(obj) });
const err = (code, msg) => ({ statusCode: code, headers: CORS, body: JSON.stringify({ error: msg }) });

function annualizedRealizedVol(closes) {
  const c = (closes || []).filter((x) => x > 0);
  if (c.length < 6) return null;
  const r = [];
  for (let i = 1; i < c.length; i++) r.push(Math.log(c[i] / c[i - 1]));
  const m = r.reduce((a, b) => a + b, 0) / r.length;
  const v = r.reduce((a, b) => a + (b - m) * (b - m), 0) / (r.length - 1);
  return Math.sqrt(v) * Math.sqrt(252);
}

export async function handler(event) {
  if (event.httpMethod === "OPTIONS") return { statusCode: 204, headers: CORS, body: "" };
  const q = event.queryStringParameters || {};
  const key = process.env.POLYGON_KEY;
  if (!key) return err(501, "POLYGON_KEY not set");
  const underlying = q.underlying, occ = q.occ;
  if (!underlying || !occ) return err(400, "need underlying and occ");
  try {
    // 1) live option snapshot
    const sj = await (await fetch(
      `https://api.polygon.io/v3/snapshot/options/${encodeURIComponent(underlying)}/${encodeURIComponent(occ)}?apiKey=${key}`
    )).json();
    const r = sj.results || {};
    const day = r.day || {}, lq = r.last_quote || {};
    const market = r.last_trade?.price ?? lq.midpoint ?? day.close ?? null;
    let spread_pct = null;
    if (lq.bid != null && lq.ask != null) {
      const mid = (lq.bid + lq.ask) / 2;
      if (mid > 0) spread_pct = (lq.ask - lq.bid) / mid;
    }
    // 2) underlying daily bars -> spot + trailing realized vol
    const fmt = (d) => new Date(d).toISOString().slice(0, 10);
    const aj = await (await fetch(
      `https://api.polygon.io/v2/aggs/ticker/${encodeURIComponent(underlying)}/range/1/day/${fmt(Date.now() - 55 * 864e5)}/${fmt(Date.now())}?adjusted=true&sort=asc&limit=60&apiKey=${key}`
    )).json();
    const closes = (aj.results || []).map((b) => b.c).filter((x) => x > 0);
    const spot = closes.length ? closes[closes.length - 1] : (r.underlying_asset?.price ?? null);
    return ok({
      market, iv: r.implied_volatility ?? null,
      oi: r.open_interest ?? null, volume: day.volume ?? null,
      spread_pct, spot, realized_vol: annualizedRealizedVol(closes.slice(-30)),
      greeks: r.greeks || null, as_of: day.last_updated || null,
    });
  } catch (e) {
    return err(502, String(e));
  }
}
