# Systemic + TAM Risk Model — Live Dashboard

[![refresh-model](https://github.com/MilanRofougaran/AI-Market-Risk-Model/actions/workflows/refresh.yml/badge.svg)](https://github.com/MilanRofougaran/AI-Market-Risk-Model/actions/workflows/refresh.yml)

A regime-switching Monte Carlo (150,000 seven-year paths) that reads the **macro
envelope first**, then prices **depth and recovery separately** for 45 AI-era
stocks and ETFs — published as a live dashboard with rankings, drawdown × recovery
matrices, conditional recovery curves, and a model-analyst chat.

**Live site:** `https://milanrofougaran.github.io/AI-Market-Risk-Model/` (after setup — see
[GITHUB_SETUP.md](GITHUB_SETUP.md), ~5 minutes).

## How it works

```
GitHub Actions (refresh.yml)            GitHub Pages (pages.yml)
  run_all.py  ── 8-stage pipeline ──►   site/ redeploys on every
  export_snapshot.py                    snapshot commit
  commit site/data/snapshot.json ──►    dashboard shows fresh numbers
        ▲                                        │
  weekly cron (Mon 13:00 UTC)                    ▼
  or Actions ► "Run workflow"           visitors: rank, filter, inspect
  or the dashboard's Refresh button     matrices & curves, ask the analyst
```

- **Engine in CI** — the Python Monte Carlo runs in GitHub Actions (numba
  installed), never in the browser. Choose paths per run (default 30,000;
  150,000 = canonical precision).
- **Dashboard** — static `site/index.html`: search, type/tier/archetype filters,
  sortable ranking (reward vs S&P, growth, tail, P(fall)), per-name stat cards,
  the full drawdown × recovery matrix, and the conditional recovery curve. The
  header envelope's crush region binds to the live stress index.
- **Discover mode** — runs `discovery/agent.py`'s whole-market stage plan in CI;
  the full discover → narrow → TAM flow keeps its **human checkpoints** by design.
- **Chat** — on GitHub Pages the dashboard answers from built-in offline logic
  over the published snapshot. For live Claude answers, either run
  `systemic_model/dash_server.py` locally, or connect this same repo to Netlify
  (config included) and set `ANTHROPIC_API_KEY` there — the key never touches
  the browser either way.

## Quickstart (local, no deploy)

```bash
cd systemic_model
python3 run_all.py --paths 30000        # or 150000 for canonical
export ANTHROPIC_API_KEY="sk-ant-..."   # optional — chat falls back without it
python3 dash_server.py                  # http://localhost:8765
```

## Repo layout

```
systemic_model/        the model: calibration, engine, 8-stage pipeline, tests,
                       discovery agent, dash_server.py (local live mode)
site/                  the published dashboard (index.html + data/snapshot.json)
export_snapshot.py     artifacts → site/data/snapshot.json
.github/workflows/     refresh.yml (engine, cron+manual) · pages.yml (deploy)
netlify.toml, netlify/ optional: serverless Claude chat + one-click runs
```

## Snapshot fields (site/data/snapshot.json)

`rows[]`: name, kind, tier, verdict, growth (18m), p25 = P(>25% fall, 18m),
rec2y = P(recover ≤2y | fell), tail = P(still underwater >3y | fell, unconditional),
vssp = reward vs S&P (growth per unit of long-drawdown risk; S&P ≡ 1.00).
`matrices{}`: per-name drawdown × recovery rows for 6/12/18-month falls.
`macro`, `stress`, `regimes`: the envelope readings the run was priced under.

---

**RESEARCH MODEL — NOT INVESTMENT ADVICE.** Probabilities are frequencies over
simulated futures; growth/TAM/archetype inputs are documented judgments the
simulation sweeps. See LICENSE.
