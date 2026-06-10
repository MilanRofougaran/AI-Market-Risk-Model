// /.netlify/functions/run — trigger the GitHub Actions engine run (workflow_dispatch).
// Netlify env: GITHUB_TOKEN (repo-scoped, workflow permission), GITHUB_REPO ("owner/repo"),
// optional GITHUB_WORKFLOW (default refresh.yml), GITHUB_REF (default main).
export default async (req) => {
  const headers = { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" };
  if (req.method === "OPTIONS") return new Response("", { status: 204, headers });
  const token = process.env.GITHUB_TOKEN, repo = process.env.GITHUB_REPO;
  if (!token || !repo) return Response.json(
    { error: "Set GITHUB_TOKEN and GITHUB_REPO in Netlify env to enable one-click engine runs." },
    { status: 501, headers });
  let body = {}; try { body = await req.json(); } catch {}
  const wf = process.env.GITHUB_WORKFLOW || "refresh.yml";
  const ref = process.env.GITHUB_REF || "main";
  const inputs = { mode: body.mode === "discover" ? "discover" : "followed",
                   paths: String(body.paths || 30000) };
  const r = await fetch(`https://api.github.com/repos/${repo}/actions/workflows/${wf}/dispatches`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, Accept: "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28", "Content-Type": "application/json" },
    body: JSON.stringify({ ref, inputs }),
  });
  if (r.status === 204) return Response.json(
    { ok: true, actions_url: `https://github.com/${repo}/actions/workflows/${wf}` }, { headers });
  const txt = await r.text();
  return Response.json({ error: `GitHub ${r.status}: ${txt.slice(0, 200)}` }, { status: 502, headers });
};
