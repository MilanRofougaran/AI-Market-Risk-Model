// ============================================================================
//  ask-options.mjs — options chatbot, answers ONLY from the model's option data.
//  Endpoint: POST /.netlify/functions/ask-options  { question }
//  Needs ANTHROPIC_API_KEY (Netlify env). Without it, returns {offline:true}
//  and the page uses its built-in model answers instead.
// ============================================================================
const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "Content-Type",
  "Content-Type": "application/json",
};

const SYSTEM = `You are the options analyst for a stock-risk research app. You answer ONLY using the model data provided in the CONTEXT below. Hard rules:
- Never invent numbers or names. If something isn't in the data, say you don't have it.
- The data is the model's PHYSICAL-MEASURE (thesis-conditional) fair values for CALL options on a fixed set of names, across expiries (6m-36m) and strikes (0.50x-2.50x of today's price). Each name has a "gate".
- Respect the gates: gate contains "broken" => tell the user to AVOID (a longer expiry never repairs a broken thesis); leveraged => avoid; "cyclical" => caution on short (6-12m) expiries (demand-trough risk).
- These are NOT market prices and ignore implied volatility, so you CANNOT judge whether the market has an option mispriced. Say so when relevant. Tell users to compare to the real market premium.
- "fair value" = % of share price the model thinks the call is worth. "P(ITM)" = chance it finishes above the strike (not the same as profit).
- Be concise and plain-spoken. Do NOT give direct buy/sell instructions. Always end with: "Research model — not investment advice."`;

function compactContext(lens) {
  // keep it small: gate + a few key strikes at 12m/24m per name
  const lines = [];
  for (const [name, nd] of Object.entries(lens.names || {})) {
    const parts = [`${name} [gate: ${nd.gate || "secular"}]`];
    for (const t of ["12m", "24m", "36m"]) {
      const row = nd[t];
      if (!row || !row.strikes) continue;
      const pick = ["0.90", "1.00", "1.20", "1.50"].map(k => {
        const s = row.strikes[k];
        return s ? `${k}x: ${Math.round(s.p_itm * 100)}% ITM / fair ${s.fair_value_pct_of_spot}%` : null;
      }).filter(Boolean).join("; ");
      if (pick) parts.push(`  ${t} — ${pick}`);
    }
    lines.push(parts.join("\n"));
  }
  return lines.join("\n");
}

export async function handler(event) {
  if (event.httpMethod === "OPTIONS") return { statusCode: 204, headers: CORS, body: "" };
  const key = process.env.ANTHROPIC_API_KEY;
  if (!key) return { statusCode: 200, headers: CORS, body: JSON.stringify({ offline: true, note: "ANTHROPIC_API_KEY not set" }) };

  let body = {};
  try { body = JSON.parse(event.body || "{}"); } catch {}
  const question = (body.question || "").slice(0, 500);
  if (!question) return { statusCode: 400, headers: CORS, body: JSON.stringify({ error: "no question" }) };

  const siteUrl = process.env.URL || process.env.DEPLOY_PRIME_URL || `https://${event.headers.host}`;
  let context = "";
  try {
    const r = await fetch(`${siteUrl}/data/options_lens.json`);
    const lens = await r.json();
    context = compactContext(lens);
  } catch (e) {
    return { statusCode: 200, headers: CORS, body: JSON.stringify({ offline: true, note: "could not load model data" }) };
  }

  try {
    const resp = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: { "x-api-key": key, "anthropic-version": "2023-06-01", "Content-Type": "application/json" },
      body: JSON.stringify({
        model: process.env.ASK_MODEL || "claude-sonnet-4-6",
        max_tokens: 700,
        system: SYSTEM,
        messages: [{ role: "user", content: `CONTEXT (the only data you may use):\n${context}\n\nQUESTION: ${question}` }],
      }),
    });
    const j = await resp.json();
    const answer = j?.content?.[0]?.text;
    if (!answer) return { statusCode: 200, headers: CORS, body: JSON.stringify({ offline: true, note: "model error" }) };
    return { statusCode: 200, headers: CORS, body: JSON.stringify({ answer }) };
  } catch (e) {
    return { statusCode: 200, headers: CORS, body: JSON.stringify({ offline: true, note: String(e) }) };
  }
}
