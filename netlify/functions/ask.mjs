// /.netlify/functions/ask — Claude chat proxy. Key lives in Netlify env (ANTHROPIC_API_KEY).
const SYSTEM = `You are the analyst for the "Systemic + TAM Risk" model — a regime-switching Monte Carlo that ranks US AI/semiconductor stocks and ETFs.
Answer using ONLY the data provided below. Be concise (2-6 sentences), cite the specific numbers, and name tickers.
Definitions: growth = expected 18-month revenue growth (tier: High >40% / Moderate 15-40% / Safe <15%).
P(>25% fall) = chance of that drawdown within 18 months. recover_by_2y = chance of recovering within 2y IF it falls >25%.
gt3y_tail = chance a >25% fall is still underwater at ~3.5y (permanent-loss tail; lower is safer).
reward_vs_SP = (growth/benchmark growth) x (benchmark tail/name tail); 1.00 = the S&P itself.
Principle: beta sets how deep a name falls; TAM-penetration sets whether it recovers. The universe is ~one correlated AI bet (corr ~0.9). Leveraged ETFs' ~100% fall odds are under-penalized by the reward scaling — read them directly.
ALWAYS end with: research model, not investment advice. Never give buy/sell recommendations.

DATA:
`;

const pct = x => x == null ? "—" : Math.round(x <= 1.5 ? x * 100 : x) + "%";

async function context(siteUrl) {
  const r = await fetch(`${siteUrl}/data/snapshot.json`);
  if (!r.ok) throw new Error("snapshot fetch " + r.status);
  const s = await r.json();
  const lines = s.rows.map(x =>
    `${x.name} | ${x.kind} | ${x.tier} | ${x.verdict} | growth ${pct(x.growth)} | P(>25% fall) ${pct(x.p25)} | rec2y ${pct(x.rec2y)} | >3y tail ${pct(x.tail)} | vsSP ${x.vssp}`);
  const m = s.macro || {}, st = s.stress || {};
  const parts = [
    `AS OF ${s.as_of} (published ${s.generated})`,
    `MACRO: CAPE ${m.shiller_cape}, real10y ${m.ust_10y_real}%, VIX ${m.vix}, HY ${m.hy_oas_bps}bps, Brent $${m.brent_usd}, margin-debt YoY ${m.margin_debt_yoy}, fwd P/E ${m.sp500_forward_pe}`,
    st.score != null ? `STRESS index ${st.score} (structural ${st.structural}, acute ${st.acute}); fair PE ${st.base_pe}x` : "",
    "TABLE:", ...lines,
  ];
  for (const nm of ["NVIDIA", "Micron", "AMD", "Microsoft", "IonQ", "VOO (S&P 500)"]) {
    const h = s.matrices?.[nm]?.["12m"];
    if (h) parts.push(`${nm} 12m matrix: P(fall)=${Math.round(h.p * 100)}%, rec 6/12/18/24/36m = ` +
      h.r.map(x => Math.round(x * 100) + "%").join("/"));
  }
  return parts.join("\n");
}

export default async (req) => {
  const headers = { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" };
  if (req.method === "OPTIONS") return new Response("", { status: 204, headers });
  const key = process.env.ANTHROPIC_API_KEY;
  let question = "";
  try { question = (await req.json()).question || ""; } catch {}
  if (!key) return Response.json(
    { answer: "", offline: true, note: "ANTHROPIC_API_KEY not set in Netlify env — using offline answers." }, { headers });
  try {
    const site = process.env.URL || process.env.DEPLOY_PRIME_URL || new URL(req.url).origin;
    const ctx = await context(site);
    const r = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: { "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json" },
      body: JSON.stringify({
        model: process.env.ASK_MODEL || "claude-sonnet-4-6",
        max_tokens: 700, system: SYSTEM + ctx,
        messages: [{ role: "user", content: question }],
      }),
    });
    const data = await r.json();
    const answer = (data.content || []).map(b => b.text || "").join("");
    return Response.json({ answer: answer || ("API error: " + JSON.stringify(data).slice(0, 200)) }, { headers });
  } catch (e) {
    return Response.json({ answer: "Claude call failed: " + e.message }, { status: 500, headers });
  }
};
