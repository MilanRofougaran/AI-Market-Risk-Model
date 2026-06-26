"""
model_extras.py — bundle the per-name "decision detail" analyses the engine
already computes into one JSON for the website (no new model, just surfacing):

  reverse_dcf    — the growth rate the market is implicitly pricing (g*)
  tier_panel     — fragility under each stress haircut (base/TAM/moat/margin/rate+input)
  confidence     — High/Med/Low grade per output (P(never), option-fair, anchored value)
  waterfall      — how EPS troughs in a downturn + what drives it
  solvency       — P(a deep drawdown becomes a permanent impairment)

Writes systemic_model/model_extras.json. export_snapshot.py merges it onto each
row. Run after run_all.py (so the bridge universe + decomposition exist).
RESEARCH MODEL — NOT INVESTMENT ADVICE.
"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "discovery"))
os.chdir(HERE)

import calibration as C
import tam_bridge as TB
# bring the whole league into the priceable universe (same as run_all step 2)
try:
    _new, _ = TB.build_company_universe(base_companies=C.COMPANIES, verbose=False)
    for k, v in _new.items():
        C.COMPANIES.setdefault(k, v)
except Exception as e:
    print("[extras] bridge merge note:", e)

import reverse_dcf as RD
import tier_gate as TG
import confidence as CF
import earnings_waterfall as EW
import solvency as SV

try:
    names = list(json.load(open("results.json"))["companies"]["decomposition"].keys())
except Exception:
    names = list(C.COMPANIES.keys())

def _safe(fn, *a):
    try: return fn(*a)
    except Exception: return None

panels = _safe(TG.run, names) or {}
confs = _safe(CF.run, names) or {}

extras = {}
for nm in names:
    e = {}
    p = panels.get(nm)
    if p:
        e["tier_panel"] = {"fragility": p.get("fragility"), "worst": p.get("worst"), "tier": p.get("tier")}
    cf = confs.get(nm)
    if cf:
        e["confidence"] = {"pnever": cf.get("pnever_conf"), "option": cf.get("option_conf"),
                           "anchor": cf.get("anchor_conf")}
    rd = _safe(RD.implied, nm)
    if rd:
        e["reverse_dcf"] = {"g_star": rd.get("g_star"), "max_justifiable": rd.get("max_justifiable"),
                            "premium_pts": rd.get("premium_pts"), "g_input": rd.get("g_input"),
                            "note": rd.get("note")}
    w = _safe(EW.waterfall, nm)
    if w:
        e["waterfall"] = {"eps_trough_depth": w.get("eps_trough_depth"),
                          "attribution": w.get("attribution"), "pe_expansion": w.get("pe_expansion_at_trough")}
    h = _safe(SV.impairment_hazard, nm)
    if h is not None:
        e["solvency_hazard"] = h
    if e:
        extras[nm] = e

json.dump({"names": extras}, open("model_extras.json", "w"), indent=1)
print(f"[extras] wrote model_extras.json: {len(extras)} names "
      f"(tier_panel {sum(1 for v in extras.values() if 'tier_panel' in v)}, "
      f"reverse_dcf {sum(1 for v in extras.values() if 'reverse_dcf' in v)}, "
      f"confidence {sum(1 for v in extras.values() if 'confidence' in v)})")
