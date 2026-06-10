# Live Dashboard — quick start

Two new files turn the model into a live product. Nothing in the model itself was changed.

    cd systemic_model
    export ANTHROPIC_API_KEY="sk-ant-..."     # optional — chat falls back to offline answers without it
    python3 dash_server.py                     # http://localhost:8765
    open http://localhost:8765

## What you get
- LIVE badge when served by dash_server.py (reads tier_table.csv + results.json, computes the
  stress index from calibration.py). Opened as a plain file, the same page runs on its embedded
  2026-06-05 snapshot with a STATIC badge — it never breaks.
- Search, filters (type / tier / archetype), sortable ranking (vs S&P, growth, tail, P(fall)).
- Click any name: stat cards, the full drawdown × recovery matrix, and the conditional recovery curve.
- "Refresh followed universe" → runs run_all.py (choose paths; light = smoke test only, never quote).
- "Discover candidates" → runs discovery/agent.py stage plan + warm-start diff. The full
  discover→narrow→TAM flow keeps its human checkpoints by design — finish those in a terminal.
- "Ask the model" chat → POST /ask, Claude answers as the model's analyst over the live numbers
  (key stays server-side, same pattern as ask_server.py). No key → built-in offline answers.

## Production notes
- Bind localhost; put your own auth + HTTPS in front before exposing.
- Schedule the followed run (cron/systemd) and let the page just reload numbers.
- Macro inputs are a dated calibration; a FRED/market-data ingestion module can automate them.
- Research model — not investment advice.
