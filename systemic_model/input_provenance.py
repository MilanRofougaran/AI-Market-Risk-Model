"""
input_provenance.py -- structured provenance / audit metadata for the model's
RESEARCH-JUDGMENT inputs (the knobs the engine cannot scrape). This is the data;
provenance.py renders the audit and cross-checks it against the live calibration.

Why this exists: every external review flags that `moat` and `tam_cagr` are where
optimism quietly overfits. This layer forces each judgment to carry a confidence, a
low/base/high range, a source, and a sensitivity tag, and flags the HOTSPOTS -- inputs
that are both high-model-sensitivity AND low/medium-confidence. It adds NO synthetic
precision and changes NO engine math; it makes the inputs auditable.

Sources are labeled honestly: most are "research estimate" or "analyst judgment", not
citations. The point is explicit confidence + ranges, not a pretense of external truth.
RESEARCH MODEL -- NOT INVESTMENT ADVICE.
"""

# Per-field model sensitivity (how much the output moves when this input is wrong) and
# the canonical home of the live value (so provenance.py can drift-check it).
FIELD_META = {
 "moat":            {"sensitivity": "HIGH", "home": "COMPETITIVE",       "unit": ""},
 "tam_cagr":        {"sensitivity": "HIGH", "home": "tam_facts",         "unit": ""},
 "rev_drawdown":    {"sensitivity": "HIGH", "home": "OPERATING_LEVERAGE","unit": ""},
 "struct_share":    {"sensitivity": "MED",  "home": "COMPETITIVE",       "unit": ""},
 "pricing_power":   {"sensitivity": "MED",  "home": "COMPETITIVE",       "unit": ""},
 "g":               {"sensitivity": "MED",  "home": "COMPETITIVE",       "unit": ""},
 "op_margin":       {"sensitivity": "MED",  "home": "OPERATING_LEVERAGE","unit": ""},
 "fixed_cost_ratio":{"sensitivity": "MED",  "home": "OPERATING_LEVERAGE","unit": ""},
 "net_cash_to_mcap":{"sensitivity": "LOW",  "home": "extension_data",    "unit": ""},
 "price":           {"sensitivity": "LOW($-scale)", "home": "PRICES",    "unit": "$"},
 "cogs_fragility":  {"sensitivity": "HIGH", "home": "PROFIT_SENSITIVITY","unit": ""},
 "net_debt_to_ebitda":{"sensitivity":"MED","home": "PROFIT_SENSITIVITY","unit": "x"},
 "floating_rate_share":{"sensitivity":"MED","home":"PROFIT_SENSITIVITY","unit": ""},
}

# Per (name, field): confidence + low/base/high range + source + dated note. base is the
# value as last reasoned; provenance.py confirms it still matches the live calibration.
# Confidence: High (well-grounded), Medium (reasoned estimate), Low (early/uncertain).
PROVENANCE = {
 "NVIDIA": {
   "cogs_fragility":{"conf":"Medium","low":0.35,"base":0.45,"high":0.55,"src":"research estimate","date":"2026-06","note":"TSMC/HBM/CoWoS dependent but high pricing power passes it on"},
   "net_debt_to_ebitda":{"conf":"High","low":0.0,"base":0.0,"high":0.0,"src":"filings (est)","date":"2026-06","note":"net cash; no interest drag"},
   "moat":          {"conf":"Medium","low":0.8,"base":0.9,"high":0.98,"src":"analyst judgment","date":"2026-06","note":"DC accelerator + CUDA lock-in; durable but the most dangerous knob"},
   "tam_cagr":      {"conf":"Medium","low":0.30,"base":0.45,"high":0.55,"src":"research estimate","date":"2026-06","note":"AI DC TAM; high but decelerating tail uncertain"},
   "pricing_power": {"conf":"High",  "low":0.8,"base":0.9,"high":0.98,"src":"filings (est)","date":"2026-06","note":"gross margins confirm pricing power"},
   "struct_share":  {"conf":"High",  "low":0.75,"base":0.85,"high":0.93,"src":"market data (est)","date":"2026-06","note":"~80-85% DC accelerator share"},
   "op_margin":     {"conf":"High",  "low":0.55,"base":0.60,"high":0.64,"src":"filings (est)","date":"2026-06","note":"reported operating margin"},
   "fixed_cost_ratio":{"conf":"Medium","low":0.35,"base":0.42,"high":0.50,"src":"research estimate","date":"2026-06","note":"fabless; R&D-heavy but variable COGS"},
   "rev_drawdown":  {"conf":"Medium","low":0.12,"base":0.18,"high":0.28,"src":"research estimate","date":"2026-06","note":"demand resilient; no deep historical DC-AI bust yet"},
   "price":         {"conf":"High",  "low":205,"base":205,"high":205,"src":"market (verified Jun-2026)","date":"2026-06","note":"verified spot; $-scale only"},
 },
 "AMD": {
   "moat":          {"conf":"Medium","low":0.4,"base":0.5,"high":0.65,"src":"analyst judgment","date":"2026-06","note":"#2 in GPU/CPU; real but contested moat"},
   "tam_cagr":      {"conf":"Medium","low":0.25,"base":0.35,"high":0.45,"src":"research estimate","date":"2026-06"},
   "pricing_power": {"conf":"Medium","low":0.35,"base":0.45,"high":0.65,"src":"analyst judgment","date":"2026-06"},
   "struct_share":  {"conf":"Medium","low":0.15,"base":0.45,"high":0.53,"src":"market data (est)","date":"2026-06"},
   "op_margin":     {"conf":"Medium","low":0.40,"base":0.45,"high":0.50,"src":"filings (est)","date":"2026-06"},
   "fixed_cost_ratio":{"conf":"Medium","low":0.45,"base":0.50,"high":0.55,"src":"research estimate","date":"2026-06"},
   "rev_drawdown":  {"conf":"Medium","low":0.20,"base":0.26,"high":0.35,"src":"research estimate","date":"2026-06","note":"cyclical compute exposure"},
 },
 "Broadcom": {
   "net_debt_to_ebitda":{"conf":"Medium","low":1.5,"base":2.5,"high":3.5,"src":"filings (est)","date":"2026-06","note":"acquisition debt -> rate-shock drag"},
   "moat":          {"conf":"Medium","low":0.6,"base":0.75,"high":0.83,"src":"analyst judgment","date":"2026-06","note":"diversified + VMware software; sticky"},
   "tam_cagr":      {"conf":"Low",   "low":0.20,"base":0.38,"high":0.45,"src":"research estimate","date":"2026-06","note":"premium leans on this -> TAM haircut bites hard"},
   "pricing_power": {"conf":"Medium","low":0.55,"base":0.7,"high":0.78,"src":"analyst judgment","date":"2026-06"},
   "struct_share":  {"conf":"Medium","low":0.2,"base":0.55,"high":0.63,"src":"market data (est)","date":"2026-06"},
   "rev_drawdown":  {"conf":"Medium","low":0.15,"base":0.20,"high":0.28,"src":"research estimate","date":"2026-06"},
 },
 "ARM": {
   "moat":          {"conf":"Medium","low":0.7,"base":0.85,"high":0.93,"src":"analyst judgment","date":"2026-06","note":"ISA standard; royalty model"},
   "tam_cagr":      {"conf":"Low",   "low":0.18,"base":0.30,"high":0.40,"src":"research estimate","date":"2026-06","note":"widest SAM gap AND lowest-confidence CAGR -> double hotspot"},
   "pricing_power": {"conf":"Medium","low":0.55,"base":0.7,"high":0.78,"src":"analyst judgment","date":"2026-06"},
   "struct_share":  {"conf":"Medium","low":0.4,"base":0.9,"high":0.98,"src":"market data (est)","date":"2026-06"},
   "rev_drawdown":  {"conf":"Medium","low":0.10,"base":0.14,"high":0.22,"src":"research estimate","date":"2026-06","note":"royalty cushions revenue"},
 },
 "Qualcomm": {
   "moat":          {"conf":"Medium","low":0.45,"base":0.55,"high":0.72,"src":"analyst judgment","date":"2026-06"},
   "tam_cagr":      {"conf":"Medium","low":0.05,"base":0.08,"high":0.14,"src":"research estimate","date":"2026-06","note":"mature; low growth"},
   "rev_drawdown":  {"conf":"Medium","low":0.15,"base":0.20,"high":0.28,"src":"research estimate","date":"2026-06"},
 },
 "Marvell": {
   "moat":          {"conf":"Medium","low":0.45,"base":0.55,"high":0.65,"src":"analyst judgment","date":"2026-06"},
   "tam_cagr":      {"conf":"Medium","low":0.25,"base":0.35,"high":0.45,"src":"research estimate","date":"2026-06"},
   "rev_drawdown":  {"conf":"Medium","low":0.22,"base":0.28,"high":0.36,"src":"research estimate","date":"2026-06"},
 },
 "Micron": {
   "cogs_fragility":{"conf":"Medium","low":0.70,"base":0.80,"high":0.90,"src":"research estimate","date":"2026-06","note":"wafer/fab/energy heavy; low pricing power -> eats input shocks"},
   "net_debt_to_ebitda":{"conf":"Medium","low":0.5,"base":1.0,"high":2.0,"src":"filings (est)","date":"2026-06"},
   "moat":          {"conf":"Medium","low":0.2,"base":0.3,"high":0.45,"src":"analyst judgment","date":"2026-06","note":"commodity memory; thin moat"},
   "tam_cagr":      {"conf":"Medium","low":0.10,"base":0.18,"high":0.25,"src":"research estimate","date":"2026-06"},
   "op_margin":     {"conf":"Medium","low":0.22,"base":0.28,"high":0.35,"src":"filings (est)","date":"2026-06","note":"cyclical-peak margin; troughs near zero"},
   "fixed_cost_ratio":{"conf":"Medium","low":0.60,"base":0.66,"high":0.75,"src":"research estimate","date":"2026-06","note":"fab depreciation = high fixed cost"},
   "rev_drawdown":  {"conf":"Medium","low":0.30,"base":0.36,"high":0.48,"src":"history (est)","date":"2026-06","note":"DRAM ASP collapses 30-50% peak-to-trough"},
 },
 "Kioxia": {
   "moat":          {"conf":"Low",   "low":0.15,"base":0.25,"high":0.4,"src":"analyst judgment","date":"2026-06"},
   "tam_cagr":      {"conf":"Low",   "low":0.08,"base":0.15,"high":0.22,"src":"research estimate","date":"2026-06"},
   "fixed_cost_ratio":{"conf":"Medium","low":0.62,"base":0.68,"high":0.76,"src":"research estimate","date":"2026-06"},
   "rev_drawdown":  {"conf":"Medium","low":0.30,"base":0.38,"high":0.50,"src":"history (est)","date":"2026-06","note":"NAND commodity cyclicality"},
 },
 "Palantir": {
   "moat":          {"conf":"Low",   "low":0.45,"base":0.65,"high":0.73,"src":"analyst judgment","date":"2026-06","note":"platform stickiness unproven at scale"},
   "tam_cagr":      {"conf":"Low",   "low":0.25,"base":0.40,"high":0.55,"src":"research estimate","date":"2026-06"},
   "rev_drawdown":  {"conf":"Low",   "low":0.15,"base":0.22,"high":0.35,"src":"research estimate","date":"2026-06"},
 },
 "Astera Labs": {
   "moat":          {"conf":"Low",   "low":0.4,"base":0.55,"high":0.68,"src":"analyst judgment","date":"2026-06","note":"connectivity niche; early, MC-uncertain"},
   "tam_cagr":      {"conf":"Low",   "low":0.30,"base":0.50,"high":0.65,"src":"research estimate","date":"2026-06"},
   "rev_drawdown":  {"conf":"Low",   "low":0.22,"base":0.30,"high":0.42,"src":"research estimate","date":"2026-06"},
 },
 "CoreWeave": {
   "cogs_fragility":{"conf":"Low","low":0.65,"base":0.75,"high":0.85,"src":"research estimate","date":"2026-06","note":"power + GPU depreciation"},
   "net_debt_to_ebitda":{"conf":"Low","low":3.0,"base":5.0,"high":7.0,"src":"research estimate","date":"2026-06","note":"heavy GPU financing -> interest-expense drag"},
   "moat":          {"conf":"Low",   "low":0.25,"base":0.45,"high":0.55,"src":"analyst judgment","date":"2026-06","note":"GPU-cloud; capex-levered, customer-concentrated"},
   "tam_cagr":      {"conf":"Low",   "low":0.30,"base":0.50,"high":0.70,"src":"research estimate","date":"2026-06"},
   "fixed_cost_ratio":{"conf":"Low", "low":0.62,"base":0.70,"high":0.80,"src":"research estimate","date":"2026-06","note":"GPU depreciation = heavy fixed cost"},
   "rev_drawdown":  {"conf":"Low",   "low":0.22,"base":0.30,"high":0.45,"src":"research estimate","date":"2026-06"},
 },
}
