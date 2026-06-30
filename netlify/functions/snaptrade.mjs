// ============================================================================
//  snaptrade.mjs — securely link a user's real brokerage and import holdings.
//  Keys (SNAPTRADE_CLIENT_ID / SNAPTRADE_CONSUMER_KEY) stay server-side.
//  The browser calls this with {action, userId, userSecret}; we never see the
//  user's brokerage password — SnapTrade handles that in its own portal.
//  Actions:
//    register  -> create a SnapTrade user, return its userSecret (store it)
//    connect   -> return the Connection Portal URL (opens the link window)
//    holdings  -> list accounts + positions, normalized for the portfolio
//  Research tool — not investment advice.
// ============================================================================
import { Snaptrade } from "snaptrade-typescript-sdk";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "Content-Type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Content-Type": "application/json",
};
const ok  = (o) => ({ statusCode: 200, headers: CORS, body: JSON.stringify(o) });
const err = (c, m) => ({ statusCode: c, headers: CORS, body: JSON.stringify({ error: m }) });

export async function handler(event) {
  if (event.httpMethod === "OPTIONS") return { statusCode: 204, headers: CORS, body: "" };
  if (event.httpMethod !== "POST")    return err(405, "POST only");

  const clientId = process.env.SNAPTRADE_CLIENT_ID, consumerKey = process.env.SNAPTRADE_CONSUMER_KEY;
  if (!clientId || !consumerKey) return err(501, "SnapTrade keys not configured on the server");

  let body = {};
  try { body = JSON.parse(event.body || "{}"); } catch { return err(400, "bad JSON"); }
  const { action, userId, userSecret } = body;
  if (!action || !userId) return err(400, "need action and userId");

  const snaptrade = new Snaptrade({ clientId, consumerKey });

  try {
    if (action === "register") {
      const r = await snaptrade.authentication.registerSnapTradeUser({ userId });
      return ok({ userId: r.data.userId, userSecret: r.data.userSecret });
    }

    if (action === "connect") {
      if (!userSecret) return err(400, "need userSecret");
      const r = await snaptrade.authentication.loginSnapTradeUser({ userId, userSecret });
      // SDK returns either { redirectURI } or a session object
      const url = r.data?.redirectURI || r.data?.loginRedirectURI || null;
      if (!url) return err(502, "no connection URL returned");
      return ok({ redirectURI: url });
    }

    if (action === "holdings") {
      if (!userSecret) return err(400, "need userSecret");
      const accts = await snaptrade.accountInformation.listUserAccounts({ userId, userSecret });
      const holdings = [];
      for (const a of (accts.data || [])) {
        let positions = [];
        try {
          const p = await snaptrade.accountInformation.getUserAccountPositions({ userId, userSecret, accountId: a.id });
          positions = p.data || [];
        } catch (e) { /* skip accounts that error */ }
        for (const pos of positions) {
          const us = pos.symbol?.symbol || pos.symbol || {};       // universal-symbol wrapper
          const ticker = us.symbol || us.raw_symbol || pos.symbol?.raw_symbol || null;
          const name = us.description || us.name || ticker;
          if (!ticker) continue;
          holdings.push({
            ticker, name,
            units: pos.units ?? pos.fractional_units ?? null,
            price: pos.price ?? null,
            avg_price: pos.average_purchase_price ?? null,
            account: a.name || a.institution_name || "",
          });
        }
      }
      return ok({ holdings, accounts: (accts.data || []).length });
    }

    return err(400, "unknown action");
  } catch (e) {
    const msg = e?.responseBody?.detail || e?.message || String(e);
    return err(502, msg);
  }
}
