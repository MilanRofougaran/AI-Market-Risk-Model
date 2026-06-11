// ============================================================================
//  quote.mjs — secure price proxy (keeps API keys server-side)
//  Endpoint: /.netlify/functions/quote
//    stock:  ?kind=stock&symbol=NVDA
//    option: ?kind=option&underlying=NVDA&occ=O:NVDA260612C00050000
//  Keys come from Netlify env vars FINNHUB_KEY (stocks) and POLYGON_KEY (options)
//  — never shipped to the browser.
// ============================================================================
const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "Content-Type",
  "Content-Type": "application/json",
};
const ok = (obj) => ({ statusCode: 200, headers: CORS, body: JSON.stringify(obj) });
const err = (code, msg) => ({ statusCode: code, headers: CORS, body: JSON.stringify({ error: msg }) });

export async function handler(event) {
  if (event.httpMethod === "OPTIONS") return { statusCode: 204, headers: CORS, body: "" };
  const q = event.queryStringParameters || {};

  try {
    if (q.kind === "stock") {
      const key = process.env.FINNHUB_KEY;
      if (!key) return err(501, "FINNHUB_KEY not set");
      const r = await fetch(`https://finnhub.io/api/v1/quote?symbol=${encodeURIComponent(q.symbol || "")}&token=${key}`);
      const j = await r.json();
      return ok({ price: (j && j.c) ? j.c : null });
    }
    if (q.kind === "option") {
      const key = process.env.POLYGON_KEY;
      if (!key) return err(501, "POLYGON_KEY not set");
      const r = await fetch(`https://api.polygon.io/v3/snapshot/options/${encodeURIComponent(q.underlying || "")}/${encodeURIComponent(q.occ || "")}?apiKey=${key}`);
      const j = await r.json();
      const res = j.results || {};
      const price = res.last_trade?.price ?? res.last_quote?.midpoint ?? res.day?.close ?? null;
      return ok({ price });
    }
    return err(400, "kind must be 'stock' or 'option'");
  } catch (e) {
    return err(502, String(e));
  }
}
