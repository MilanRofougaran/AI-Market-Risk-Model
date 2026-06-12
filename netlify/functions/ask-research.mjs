// ============================================================================
//  ask-research.mjs — the Research assistant. Answers ONLY from the model.
//  Endpoint: POST /.netlify/functions/ask-research  { question }
//  Needs ANTHROPIC_API_KEY. Without it -> { offline:true } and the page uses
//  its built-in model answers.
// ============================================================================
const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "Content-Type",
  "Content-Type": "application/json",
};

const BRIEF = `THE MODEL: a regime-switching Monte Carlo risk model for US AI/semiconductor stocks and ETFs. Core principle: a stock's BETA sets how deep it falls in a panic; its TAM-penetration (growth runway) sets whether it RECOVERS. Goal = avoid permanent loss, not chase returns. Metrics: growth = expected 18-month revenue growth; P(>25% fall) = chance of that drop in 18m; recover_by_2y = chance of recovering within 2y if it falls; gt3y_tail = chance a >25% fall is still underwater ~3.5y later (the catastrophe / permanent-loss signal, lower is safer); reward_vs_SP = growth per unit of long-term risk vs the S&P (1.00 = the S&P). The whole AI universe is ~one correlated bet (corr ~0.9). Leveraged 3x ETFs (~100% fall odds) are decay products. Macro stress index = how dangerous the overall market is now. Options are physical-measure (thesis-conditional) call fair values with NO implied volatility, so they cannot detect market mispricing. Trust the RANKINGS more than the exact numbers (the model orders well but its precise probabilities are imperfect).`;

const SYSTEM = `You are the Research assistant for a stock-risk app. You help users research and LEARN about investing risk, using ONLY the model knowledge and data provided. Rules:
- Use only the BRIEF and DATA below. Never invent numbers, names, or facts. If you don't have it, say so plainly.
- Teach in clear, plain language; define jargon. Be genuinely helpful for learning.
- Respect the model's verdicts: "broken" = avoid; leveraged = avoid/decays; cyclical = slower to recover.
- Do NOT give personalized buy/sell instructions. You may explain what the model ranks higher/lower and why.
- Be concise but complete. Always end with: "Research model — not investment advice."`;

const pct = x => x == null ? "—" : Math.round(x <= 1.5 ? x * 100 : x) + "%";

async function buildData(siteUrl) {
  let out = [];
  try {
    const s = await (await fetch(`${siteUrl}/data/snapshot.json`)).json();
    const m = s.macro || {}, st = s.stress || {};
    out.push(`AS OF ${s.as_of}. MACRO: stress ${st.score} (structural ${st.structural}, acute ${st.acute}), CAPE ${m.shiller_cape}, real10y ${m.ust_10y_real}%, VIX ${m.vix}, HY ${m.hy_oas_bps}bps, margin-debt YoY ${m.margin_debt_yoy}, S&P fwd P/E ${m.sp500_forward_pe}, fair PE ${st.base_pe}x.`);
    out.push("STOCKS/ETFS (name | type | tier | verdict | growth | P(>25% fall) | rec2y | >3y tail | reward vs S&P):");
    out.push(...s.rows.map(x => `${x.name} | ${x.kind} | ${x.tier} | ${x.verdict} | ${pct(x.growth)} | ${pct(x.p25)} | ${pct(x.rec2y)} | ${pct(x.tail)} | ${x.vssp}`));
  } catch (e) { out.push("(stock data unavailable)"); }
  try {
    const o = (await (await fetch(`${siteUrl}/data/options_lens.json`)).json()).names || {};
    const names = Object.entries(o).map(([n, nd]) => `${n} [${nd.gate || "secular"}]`).join(", ");
    out.push(`OPTIONS (calls priced for): ${names}`);
  } catch (e) {}
  return out.join("\n");
}

export async function handler(event) {
  if (event.httpMethod === "OPTIONS") return { statusCode: 204, headers: CORS, body: "" };
  const key = process.env.ANTHROPIC_API_KEY;
  if (!key) return { statusCode: 200, headers: CORS, body: JSON.stringify({ offline: true, note: "ANTHROPIC_API_KEY not set" }) };

  let body = {};
  try { body = JSON.parse(event.body || "{}"); } catch {}
  const question = (body.question || "").slice(0, 1000);
  if (!question) return { statusCode: 400, headers: CORS, body: JSON.stringify({ error: "no question" }) };
  const history = Array.isArray(body.history) ? body.history.slice(-8) : [];

  const siteUrl = process.env.URL || process.env.DEPLOY_PRIME_URL || `https://${event.headers.host}`;
  const data = await buildData(siteUrl);

  const messages = [
    ...history.filter(m => m && m.role && m.content).map(m => ({ role: m.role === "assistant" ? "assistant" : "user", content: String(m.content).slice(0, 2000) })),
    { role: "user", content: `${question}` },
  ];

  try {
    const resp = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: { "x-api-key": key, "anthropic-version": "2023-06-01", "Content-Type": "application/json" },
      body: JSON.stringify({
        model: process.env.ASK_MODEL || "claude-sonnet-4-6",
        max_tokens: 900,
        system: `${SYSTEM}\n\nBRIEF:\n${BRIEF}\n\nDATA:\n${data}`,
        messages,
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
