"""
============================================================================
 ASK_SERVER  --  connect demo.html's "Ask" box to live Claude
============================================================================
 A tiny local proxy so the dashboard's Ask box is answered by Claude doing
 real analysis over the model's current numbers — WITHOUT ever putting your
 API key in the shared HTML (the key stays here, in an environment variable).

 SETUP (one time):
   pip install nothing  (uses only the Python standard library)
   export ANTHROPIC_API_KEY="sk-ant-..."     # your key; never share it
   python3 ask_server.py                       # starts on http://localhost:8765

 Then open demo.html — its Ask box will call this server and get live Claude
 answers. If the server is NOT running, demo.html silently falls back to its
 built-in offline answers, so it never breaks.

 The server feeds Claude the current dashboard data (from tier_table.csv) plus
 the model's methodology, and instructs it to answer as the model's analyst:
 concise, numbers-cited, research-model-not-advice.

 SECURITY: do not commit your key, do not paste it into demo.html, and only
 expose this beyond localhost behind your own auth. RESEARCH MODEL, NOT ADVICE.
============================================================================
"""
import json, os, sys, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("ASK_PORT", "8765"))
MODEL = os.environ.get("ASK_MODEL", "claude-sonnet-4-6")
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


def load_context():
    """Build the data context Claude reasons over, from the current outputs."""
    parts = []
    csv = os.path.join(HERE, "tier_table.csv")
    if os.path.exists(csv):
        parts.append("CURRENT MODEL TABLE (tier_table.csv):\n" + open(csv).read())
    res = os.path.join(HERE, "results.json")
    if os.path.exists(res):
        r = json.load(open(res))
        m = r.get("macro", {})
        parts.append(f"\nAS OF: {r.get('as_of')}\nMACRO: forward P/E {m.get('sp500_forward_pe')}, "
                     f"CAPE {m.get('shiller_cape')}, 10y {m.get('ust_10y')}%, real {m.get('ust_10y_real')}%, "
                     f"VIX {m.get('vix')}, Brent ${m.get('brent_usd')}, HY spread {m.get('hy_oas_bps')}bps, "
                     f"Fed bias {m.get('fed_next_move_bias')}, margin-debt YoY {m.get('margin_debt_yoy')}.")
    return "\n".join(parts) or "(no data files found next to ask_server.py)"


SYSTEM = """You are the analyst for the "Systemic + TAM Risk" model — a regime-switching Monte Carlo that ranks US AI/semiconductor stocks and ETFs.
Answer questions using ONLY the data provided below. Be concise (2-5 sentences), cite the specific numbers, and name tickers.
Key definitions: growth = expected 18-month revenue growth (sets the tier: High >40% / Moderate 15-40% / Safe <15%).
P(>25% fall) = chance of that drawdown in 18 months. recover_by_1y/2y/3y = chance of recovering within that horizon IF it falls >25%.
gt3y_tail = chance a >25% fall is still underwater at ~3.5y (permanent-loss tail; lower safer).
reward_vs_SP / reward_vs_SCHD = (growth/benchmark growth) x (benchmark tail / name tail); benchmark = 1.00; above 1 = better growth-per-unit-of-long-drawdown-risk than the benchmark.
Principle: beta sets how deep a name falls; TAM-penetration sets whether it recovers. The universe is ~1 correlated AI bet (corr ~0.9). The reward scaling is growth-tilted and under-penalizes leveraged ETFs' ~100% fall odds.
ALWAYS end with: this is a research model, not investment advice. Do not give buy/sell recommendations; present the model's numbers and let the user decide.

DATA:
""" + "\n"  # context appended at call time


def ask_claude(question, context):
    body = json.dumps({
        "model": MODEL, "max_tokens": 700,
        "system": SYSTEM + context,
        "messages": [{"role": "user", "content": question}],
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body,
        headers={"x-api-key": API_KEY, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=40) as r:
        data = json.load(r)
    return "".join(b.get("text", "") for b in data.get("content", []))


class H(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")

    def do_OPTIONS(self):
        self.send_response(204); self._cors(); self.end_headers()

    def do_GET(self):
        self.send_response(200); self._cors()
        self.send_header("Content-Type", "text/plain"); self.end_headers()
        self.wfile.write(b"ask_server is running. POST {question} to /ask.")

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            q = json.loads(self.rfile.read(n) or b"{}").get("question", "")
            if not API_KEY:
                ans = "Server has no ANTHROPIC_API_KEY set — set it and restart."
            else:
                ans = ask_claude(q, load_context())
            out = json.dumps({"answer": ans}).encode()
            self.send_response(200); self._cors()
            self.send_header("Content-Type", "application/json"); self.end_headers()
            self.wfile.write(out)
        except Exception as e:
            self.send_response(500); self._cors()
            self.send_header("Content-Type", "application/json"); self.end_headers()
            self.wfile.write(json.dumps({"answer": "Server error: " + str(e)}).encode())

    def log_message(self, *a):  # quiet
        pass


if __name__ == "__main__":
    if not API_KEY:
        print("WARNING: ANTHROPIC_API_KEY not set — the server will run but can't reach Claude.\n"
              '  export ANTHROPIC_API_KEY="sk-ant-..."  then restart.')
    print(f"ask_server on http://localhost:{PORT}  (model {MODEL}).  Open demo.html and use the Ask box.")
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
