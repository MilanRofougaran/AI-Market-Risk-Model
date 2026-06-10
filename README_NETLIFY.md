# Deploying the Systemic + TAM dashboard on Netlify

This folder IS the repo. Push it to GitHub, connect to Netlify, set two env vars — done.
The engine (Python Monte Carlo) does NOT run on Netlify; it runs in GitHub Actions and
publishes a fresh `site/data/snapshot.json`, which auto-redeploys the site.

## 1) Push to GitHub
    git init && git add -A && git commit -m "systemic+TAM dashboard"
    git remote add origin https://github.com/YOURNAME/systemic-tam.git
    git push -u origin main

## 2) Connect Netlify
Netlify → Add new site → Import from Git → pick the repo.
`netlify.toml` already sets publish dir = `site/` and functions dir = `netlify/functions/`.
Deploy. The dashboard is live immediately with the committed snapshot (badge: LIVE · published run).

## 3) Environment variables (Site settings → Environment variables)
| Variable | Needed for | Notes |
|---|---|---|
| ANTHROPIC_API_KEY | "Ask the model" chat | key stays server-side in the function; without it, chat uses built-in offline answers |
| GITHUB_TOKEN | "Refresh / Discover" buttons | fine-grained PAT on this repo with **Actions: Read & write** (or classic token with `repo` + `workflow`) |
| GITHUB_REPO | same | e.g. `YOURNAME/systemic-tam` |
| GITHUB_WORKFLOW / GITHUB_REF | optional | default `refresh.yml` / `main` |

## 4) How refresh works
- **Button** → Netlify function `run.mjs` → GitHub `workflow_dispatch` → `refresh.yml` runs
  `run_all.py --paths N`, exports the snapshot, commits → Netlify auto-redeploys (~5–15 min).
- **Schedule** → same workflow runs every Monday 13:00 UTC (edit the cron in `refresh.yml`).
- **Discover** → runs `discovery/agent.py` stage plan in CI; the full discover→narrow→TAM flow
  keeps its human checkpoints — finish those locally before new names enter calibration.
- Local manual run also works: `cd systemic_model && python3 run_all.py --paths 150000 &&
  cd .. && python3 export_snapshot.py && git commit -am "fresh run" && git push`.

## 5) Notes
- Paths: 30,000 in CI ≈ tight enough for the site (SE ≲ 0.3 pt); 150,000 works with numba
  installed (the workflow installs it) if you want canonical precision — watch the runtime.
- Private site? Netlify password protection / Identity, since the model output is yours.
- `Cache-Control: no-cache` is set on `/data/*` so a redeploy shows fresh numbers immediately.
- Research model — not investment advice (the page footer says so on every view).
