# GitHub setup — exact steps (~5 minutes)

## 1) Create the repo
On github.com → New repository → name it (e.g. `systemic-tam`).
**Make it Public** if you want free GitHub Pages (private repos need GitHub Pro
for Pages). Don't add a README/license — this folder already has them.

## 2) Push this folder
```bash
cd <this-folder>
git init
git branch -M main
git add -A
git commit -m "Systemic + TAM risk model + live dashboard"
git remote add origin https://github.com/MilanRofougaran/AI-Market-Risk-Model.git
git push -u origin main
```

## 3) Two Settings toggles (once)
- **Settings → Actions → General → Workflow permissions** → select
  **"Read and write permissions"** → Save.
  (Lets refresh.yml commit the fresh snapshot back to the repo.)
- **Settings → Pages → Build and deployment → Source** → **GitHub Actions**.

## 4) Point the dashboard at your repo (one line)
Edit `site/index.html`, near the top of the `<script>`:
```js
const GH_REPO="MilanRofougaran/AI-Market-Risk-Model";
```
Commit and push. That push deploys the site (pages.yml watches `site/**`).

## 5) Open it
`https://milanrofougaran.github.io/AI-Market-Risk-Model/` — badge reads **LIVE · published run**,
showing the committed snapshot. (First deploy can take ~1–2 minutes; check the
Actions tab.)

## 6) Refresh the numbers
- **Manual:** Actions → **refresh-model** → Run workflow → mode `followed`,
  paths `30000` (or `150000`). It runs the engine, commits the fresh snapshot,
  and the site redeploys itself. The dashboard's Refresh button links you
  straight here.
- **Automatic:** every Monday 13:00 UTC (edit the cron in
  `.github/workflows/refresh.yml`).
- **Discover:** same workflow with mode `discover` runs the discovery agent's
  stage plan; finish its human checkpoints locally before new names enter
  calibration.

## 7) Chat
On GitHub Pages the chat uses built-in offline answers over the snapshot
(no key needed, nothing to configure). For live Claude answers:
- **Local:** `python3 systemic_model/dash_server.py` with `ANTHROPIC_API_KEY` set, or
- **Netlify (optional):** import this same repo on Netlify (netlify.toml is
  included), set `ANTHROPIC_API_KEY` (+ `GITHUB_TOKEN`/`GITHUB_REPO` for
  one-click runs) — see README_NETLIFY.md.

## Troubleshooting
- **Pages 404** → Settings → Pages → Source must be "GitHub Actions"; check the
  deploy-pages run in Actions.
- **refresh-model fails at the commit step** → Workflow permissions toggle
  (step 3) wasn't saved.
- **Numbers didn't change after a run** → hard-refresh; `/data/*` is served
  no-cache on Netlify, but a browser may cache on Pages (Ctrl/Cmd-Shift-R).
