# Connect the demo's "Ask" box to live Claude

`demo.html` works on its own — open it and the Ask box answers from the
embedded data (offline, no setup). To make the Ask box answered by **live
Claude doing real analysis** over the model's current numbers, run the small
local helper that holds your API key.

## One-time setup

1. Get an Anthropic API key from https://console.anthropic.com (Settings → API Keys).
2. In a terminal, set the key and start the helper (only the Python standard
   library is needed — nothing to `pip install`):

   ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."      # your key
   python3 ask_server.py
   ```

   You'll see: `ask_server on http://localhost:8765`.

3. Open `demo.html` in your browser. The Ask box now routes questions to the
   helper → Claude → back to the page. If the helper isn't running, the box
   silently falls back to the built-in offline answers, so it never breaks.

Optional: `export ASK_MODEL="claude-opus-4-6"` for a stronger model, or
`export ASK_PORT=9000` to change the port (also update `ASK_URL` in demo.html).

## Security — read this

- **Never put the API key in `demo.html`** or any file you send to friends.
  The key lives only in the server's environment variable. Anyone who runs the
  page hits *your* running helper; the key is never shipped.
- The helper listens on `127.0.0.1` (your machine only). To let friends use it
  remotely you'd need to expose it deliberately and add your own auth — don't
  do that with a bare key.
- Every Ask call costs API tokens against your account. The helper caps each
  answer at 700 tokens.

## What Claude sees

On each question the helper feeds Claude the current `tier_table.csv` +
macro snapshot from `results.json`, plus the model's methodology, and instructs
it to answer concisely with the numbers and the standing caveat: **research
model, not investment advice.**
