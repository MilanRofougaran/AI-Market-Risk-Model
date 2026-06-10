"""
============================================================================
 DASH_SERVER  --  one local server for the live Systemic + TAM dashboard
============================================================================
 Supersedes ask_server.py (keeps the same /ask contract) and adds everything
 the live dashboard needs. Standard library only. The Anthropic key stays in
 an environment variable on this machine — never in the HTML.

 RUN:
   export ANTHROPIC_API_KEY="sk-ant-..."      # optional; chat falls back without it
   python3 dash_server.py                      # http://localhost:8765
   open http://localhost:8765                  # serves live_dashboard.html

 ENDPOINTS
   GET  /                  -> live_dashboard.html
   GET  /api/snapshot      -> {as_of, generated, macro, stress, rows[], matrices{}, regimes}
   POST /ask               -> {answer}        (same contract as ask_server.py)
   POST /api/run           -> {job_id}        body: {"mode":"followed"|"discover","paths":30000,"light":false}
   GET  /api/job/<id>      -> {status, returncode, log}
   GET  /report_assets/*   -> static chart PNGs (if present)

 MODES
   followed : re-runs the full pipeline on the tracked universe (run_all.py)
   discover : prints the discovery agent's stage plan + warm-start diff
              (discovery/agent.py). The full discover->narrow->TAM flow keeps
              its human checkpoints by design — run it in a terminal when a
              checkpoint decision is needed.

 SECURITY: bind localhost. Put your own auth/reverse-proxy in front before
 exposing. Do not commit the key. RESEARCH MODEL — NOT INVESTMENT ADVICE.
============================================================================
"""
import csv, json, os, re, subprocess, sys, threading, time, urllib.request, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE   = os.path.dirname(os.path.abspath(__file__))
PORT   = int(os.environ.get("DASH_PORT", "8765"))
MODEL  = os.environ.get("ASK_MODEL", "claude-sonnet-4-6")
APIKEY = os.environ.get("ANTHROPIC_API_KEY", "")
PY     = sys.executable or "python3"

JOBS = {}                 # job_id -> {mode,status,returncode,log,started}
JOB_LOCK = threading.Lock()

# ----------------------------------------------------------------- snapshot
def _f(x):
    try: return float(x)
    except Exception: return None

def load_rows():
    path = os.path.join(HERE, "tier_table.csv")
    if not os.path.exists(path): return []
    rows = []
    for r in csv.DictReader(open(path)):
        rows.append({
            "name": r.get("name"), "kind": r.get("kind") or r.get("type"),
            "tier": r.get("growth_tier"), "verdict": r.get("recovery_rank") or r.get("crash_growth"),
            "crash_growth": r.get("crash_growth"),
            "growth": _f(r.get("exp_growth_18m")),
            "p25": _f(r.get("P(>25% fall)")),
            "rec2y": _f(r.get("recover_by_2y_if_falls")),
            "tail": _f(r.get("gt3y_tail_unconditional")),
            "perm": _f(r.get("true_permanent_loss")),
            "xsp": _f(r.get("perm_vs_SP_multiple")),
            "vssp": _f(r.get("reward_vs_SP")), "vsschd": _f(r.get("reward_vs_SCHD")),
        })
    return rows

def load_matrices():
    path = os.path.join(HERE, "results.json")
    if not os.path.exists(path): return {}, {}, {}, None
    res = json.load(open(path))
    mats = {}
    for nm, o in (res.get("companies", {}).get("recovery_cond", {}) or {}).items():
        m = o.get("dd_recovery_matrix")
        if not m: continue
        mats[nm] = {h: {
            "p": m[h]["p_drawdown"],
            "r": [m[h]["recover_6m"], m[h]["recover_12m"], m[h]["recover_18m"],
                  m[h]["recover_24m"], m[h]["recover_36m"]],
        } for h in ("6m", "12m", "18m") if h in m}
    return mats, res.get("macro", {}), res.get("regime_probs", {}), res.get("as_of")

def load_stress():
    """Best effort: pull the computed stress index from calibration."""
    try:
        sys.path.insert(0, HERE)
        import calibration as C  # noqa
        ss = C.SYSTEMIC_STRESS
        return {"score": round(ss["score"], 3), "structural": round(ss["structural"], 3),
                "acute": round(ss["acute"], 3), "base_pe": round(getattr(C, "BASE_PE", 0), 1),
                "freeze_severity": round(getattr(C, "FREEZE_SEVERITY", 0), 3)}
    except Exception:
        return None

def snapshot():
    mats, macro, regimes, as_of = load_matrices()
    p = os.path.join(HERE, "results.json")
    gen = time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(p))) if os.path.exists(p) else None
    return {"as_of": as_of, "generated": gen, "macro": macro, "stress": load_stress(),
            "rows": load_rows(), "matrices": mats, "regimes": regimes}

# ----------------------------------------------------------------- ask (Claude)
SYSTEM = """You are the analyst for the "Systemic + TAM Risk" model — a regime-switching Monte Carlo that ranks US AI/semiconductor stocks and ETFs.
Answer questions using ONLY the data provided below. Be concise (2-6 sentences), cite the specific numbers, and name tickers.
Definitions: growth = expected 18-month revenue growth (tier: High >40% / Moderate 15-40% / Safe <15%).
P(>25% fall) = chance of that drawdown within 18 months. recover_by_2y = chance of recovering within 2y IF it falls >25%.
gt3y_tail = chance a >25% fall is still underwater at ~3.5y (permanent-loss tail; lower is safer).
reward_vs_SP = (growth/benchmark growth) x (benchmark tail/name tail); 1.00 = the S&P itself.
Principle: beta sets how deep a name falls; TAM-penetration sets whether it recovers. The universe is ~one correlated AI bet (corr ~0.9). Leveraged ETFs' ~100% fall odds are under-penalized by the reward scaling — read them directly.
ALWAYS end with: research model, not investment advice. Never give buy/sell recommendations — present the model's numbers and let the user decide.

DATA:
"""

def ask_context():
    parts = []
    csvp = os.path.join(HERE, "tier_table.csv")
    if os.path.exists(csvp):
        parts.append("CURRENT MODEL TABLE (tier_table.csv):\n" + open(csvp).read())
    mats, macro, _, as_of = load_matrices()
    if macro:
        parts.append(f"AS OF {as_of} MACRO: CAPE {macro.get('shiller_cape')}, real10y {macro.get('ust_10y_real')}%, "
                     f"VIX {macro.get('vix')}, HY {macro.get('hy_oas_bps')}bps, Brent ${macro.get('brent_usd')}, "
                     f"margin-debt YoY {macro.get('margin_debt_yoy')}, fwd P/E {macro.get('sp500_forward_pe')}.")
    st = load_stress()
    if st: parts.append(f"STRESS index {st['score']} (structural {st['structural']}, acute {st['acute']}); fair PE {st['base_pe']}x.")
    if mats:
        keep = ["NVIDIA", "Micron", "AMD", "Microsoft", "IonQ", "VOO (S&P 500)", "QQQ (Nasdaq-100)"]
        for nm in keep:
            if nm in mats:
                h = mats[nm].get("12m")
                if h: parts.append(f"{nm} 12m matrix: P(fall)={h['p']:.0%}, rec 6/12/18/24/36m = " +
                                   "/".join(f"{x:.0%}" for x in h["r"]))
    return "\n".join(parts) or "(no data files found)"

def ask_claude(question):
    body = json.dumps({"model": MODEL, "max_tokens": 700,
                       "system": SYSTEM + ask_context(),
                       "messages": [{"role": "user", "content": question}]}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body,
        headers={"x-api-key": APIKEY, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=45) as r:
        data = json.load(r)
    return "".join(b.get("text", "") for b in data.get("content", []))

# ----------------------------------------------------------------- run jobs
def _run_job(job_id, cmd):
    j = JOBS[job_id]
    logp = os.path.join(HERE, f"job_{job_id}.log")
    with open(logp, "w") as lf:
        try:
            pr = subprocess.Popen(cmd, cwd=HERE, stdout=lf, stderr=subprocess.STDOUT)
            j["status"] = "running"
            rc = pr.wait()
            j["returncode"] = rc
            j["status"] = "done" if rc == 0 else "failed"
        except Exception as e:
            lf.write("\nLAUNCH ERROR: " + str(e))
            j["status"] = "failed"; j["returncode"] = -1
    j["log_path"] = logp

def start_job(mode, paths=30000, light=False):
    with JOB_LOCK:
        if any(j["status"] in ("queued", "running") for j in JOBS.values()):
            return None  # one heavy job at a time
        jid = uuid.uuid4().hex[:8]
        if mode == "discover":
            cmd = [PY, os.path.join("discovery", "agent.py")]
        else:
            cmd = [PY, "run_all.py", "--paths", str(int(paths))] + (["--light"] if light else [])
        JOBS[jid] = {"mode": mode, "status": "queued", "returncode": None,
                     "started": time.strftime("%H:%M:%S"), "cmd": " ".join(cmd)}
        threading.Thread(target=_run_job, args=(jid, cmd), daemon=True).start()
        return jid

def job_status(jid):
    j = JOBS.get(jid)
    if not j: return None
    out = dict(j); out.pop("log_path", None)
    logp = os.path.join(HERE, f"job_{jid}.log")
    if os.path.exists(logp):
        tail = open(logp, errors="replace").read()[-4000:]
        out["log"] = tail
    return out

# ----------------------------------------------------------------- http
class H(BaseHTTPRequestHandler):
    def _hdr(self, code=200, ctype="application/json"):
        self.send_response(code)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Content-Type", ctype)
        self.end_headers()

    def do_OPTIONS(self): self._hdr(204)

    def do_GET(self):
        if self.path in ("/", "/index.html", "/live_dashboard.html"):
            f = os.path.join(HERE, "live_dashboard.html")
            if os.path.exists(f):
                self._hdr(200, "text/html; charset=utf-8")
                self.wfile.write(open(f, "rb").read()); return
            self._hdr(404, "text/plain"); self.wfile.write(b"live_dashboard.html not found"); return
        if self.path == "/api/snapshot":
            self._hdr(); self.wfile.write(json.dumps(snapshot()).encode()); return
        m = re.match(r"^/api/job/([0-9a-f]+)$", self.path)
        if m:
            st = job_status(m.group(1))
            self._hdr(200 if st else 404)
            self.wfile.write(json.dumps(st or {"error": "no such job"}).encode()); return
        if self.path.startswith("/report_assets/"):
            f = os.path.join(HERE, self.path.lstrip("/"))
            if os.path.isfile(f) and os.path.abspath(f).startswith(HERE):
                self._hdr(200, "image/png"); self.wfile.write(open(f, "rb").read()); return
        self._hdr(404, "text/plain"); self.wfile.write(b"not found")

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        try: body = json.loads(self.rfile.read(n) or b"{}")
        except Exception: body = {}
        if self.path == "/ask":
            q = body.get("question", "")
            if not APIKEY:
                self._hdr(); self.wfile.write(json.dumps(
                    {"answer": "", "offline": True,
                     "note": "ANTHROPIC_API_KEY not set on the server — using the dashboard's built-in offline answers."}).encode()); return
            try: ans = ask_claude(q)
            except Exception as e: ans = "Claude call failed: " + str(e)
            self._hdr(); self.wfile.write(json.dumps({"answer": ans}).encode()); return
        if self.path == "/api/run":
            jid = start_job(body.get("mode", "followed"),
                            paths=body.get("paths", 30000), light=bool(body.get("light")))
            if jid is None:
                self._hdr(409); self.wfile.write(json.dumps({"error": "a job is already running"}).encode()); return
            self._hdr(); self.wfile.write(json.dumps({"job_id": jid}).encode()); return
        self._hdr(404); self.wfile.write(json.dumps({"error": "unknown endpoint"}).encode())

    def log_message(self, *a): pass  # quiet


if __name__ == "__main__":
    print(f"dash_server on http://localhost:{PORT}   (key {'SET' if APIKEY else 'NOT set — chat uses offline fallback'})")
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
