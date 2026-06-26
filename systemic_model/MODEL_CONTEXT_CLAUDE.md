# Systemic + TAM Risk Model — Grounding Document (Claude build)

**Purpose.** Paste into a Claude Project to ground the model on the *current canonical state* of the
Systemic + TAM Risk engine and its options / valuation / governance layers. Complete textual spec.
It is **not** code; it describes the code.

**Reviewer instruction.** Treat every number below as canonical for this build (2026-06-13: competitive
+ cash + earnings-collapse + endogenous-operating-leverage + profit-sensitivity + governance +
provenance layers ON). Reason from these definitions; flag any internal inconsistency; never invent
figures. **Research model, NOT investment advice**; every option/stock number is a *thesis-conditional*
read under documented inputs — never a recommendation, target, or signal.

---

## 1. Core philosophy
> **Beta/correlation set how DEEP a name falls in a panic. TAM-penetration, growth duration, balance
> sheet, competitive structure, earnings cyclicality, and profit-sensitivity (rates + input costs) set
> WHETHER and how fast it recovers.**

Depth (market-driven) is decoupled from recovery (business-driven). First-class catastrophe metric:
**P(never)** = probability still underwater at the end of the 7-year sim. Never a single "fair price":
the **stock ledger** says how much of price is anchored vs floating; the **option ledger** says whether
a contract is cheap vs model-fair payoff, after gates. The organizing question is not "is the growth
there?" but **"how much of that growth becomes durable profit under stress?"**

## 2. The 8-stage pipeline (`run_all.py`)
Discovery → TAM/SAM bridge (priceable + true holdings-aggregated ETF baskets) → macro/systemic stress →
regime-switching Monte Carlo → leveraged-ETF decay → change ledger → analysis layers → build outputs.
Determinism: fixed seed; per-name idiosyncratic RNG via `crc32(name)`. `--light`=800-path smoke; real
≥10k (canonical 150k); ~40k OOMs small container. P(never) at ~10k carries ±1–2 sampling noise.

## 3. Macro / systemic stress
0–100, structural (depth) vs acute (timing). Canonical **48/100 (58/25)** — fragile base, no lit fuse.
Causal systemic-freeze (2020 flood vs 2008 drain). Inputs documented, not live-scraped.

## 4. Regime-switching Monte Carlo
Four-state Markov on a single macro factor Φ + group sub-factors + sticky **grind** state (2022).
Student-t fat tails; crisis correlation → ~0.92 (~45-name universe = ~1 effective bet). Trough-buyback
**slingshot** w/ accretion gate; toxic-dilution/solvency caps; cyclical two-phase demand trough.
**Backtest 7/7** — validates drawdown DEPTH, not recovery TIMING.

## 5. Premium decomposition — the valuation core
```
premium_pts      = max(eff_pe - 15.8, 0)               (BASE_PE 15.8; eff_pe see 5c)
justified_pts    = premium_pts * <justification>       (CAPPED at premium_pts -> NO cheapness signal)
unsupported_frac = (premium_pts - justified_pts)/eff_pe
fragility        = 0.5*unsupported_frac + 0.3*(1-earn_quality) + 0.2*(1-balance)
recovery_quality = f(runway/duration, earn_quality, unsupported_frac, capex) then dragged by 5d
```
**5b Competitive-duration (ACTIVE, `USE_COMPETITIVE_PREMIUM`):** GAF convex in duration, growing-TAM
`T_sat`, mean(share_durability, pricing_power, earn_quality), capped at premium. 40% growth → 1.1–20.4
pts (17.9×). Inputs in `COMPETITIVE`; audited in `competitive_assumptions.md` (+moat ±0.15 sensitivity).
**"moat" is the dangerous knob.**
**5c Cash/buyback/balance (ACTIVE, `USE_CASH_ADJUSTMENT`):** net cash de-rates the multiple; an
accretive buyback (E/P > 3.5%) de-rates further; net DEBT no credit, raises fragility. Stretched
multiples non-accretive (NVDA 3.3%, ARM 1.4%) → no de-rating.

### 5d. EARNINGS-COLLAPSE + ENDOGENOUS LEVERAGE + PROFIT-SENSITIVITY (ACTIVE)
In a bust, operating leverage makes EPS fall faster than price → trailing P/E EXPANDS exactly when you
need compression, and recovery waits for the denominator to heal.
- `USE_EARNINGS_COLLAPSE`: `recovery_quality *= (1 - cyc*0.40)` and `tail_mult += min(0.30, cyc*0.30)`
  (valuation-floor erosion). `recovery_quality_precollapse` preserved. Distinct from capex penalty /
  two-phase trough.
- `USE_ENDOGENOUS_EARNINGS`: derive cyclicality from operating leverage instead of a manual number —
  `new_OI=(1-d)*(1-(1-m)*(1-f))-(1-m)*f`, `cyc=1-new_OI/m` (clamp 0..0.95) from op_margin (m),
  fixed_cost_ratio (f), rev_drawdown (d) in `OPERATING_LEVERAGE`. Reproduces the prior manual values
  within ~0.05–0.10; memory → ~0.95 (EPS wiped).
- `USE_PROFIT_SENSITIVITY` (**NEW**): two drawdown-EPS channels the demand model misses, both ADDED to
  cyclicality (so they flow through the recovery drag AND trough depth):
  **(1) interest-expense** `ie_addon = net_debt_to_ebitda * floating_rate_share * 0.06` — a rate shock
  raises interest expense for levered/floating-rate names; net-cash names → 0.
  **(2) input-cost** `ic_addon = cogs_fragility * (1 - pricing_power) * 0.35` — a commodity/inflation
  shock hits COGS (wafers/HBM/substrates/energy); high pricing power passes it on, low pricing power
  eats it. Inputs in `PROFIT_SENSITIVITY`. **Taxes deliberately NOT modeled** — slow, telegraphed,
  cause re-ratings not 6–18m liquidity panics; the after-tax cash yield in the accretion gate already
  captures the one place tax matters here. **HONEST CAVEAT: the endogenous + profit-sensitivity effects
  sharpen trough DEPTH + recovery TIMING — the model's LEAST-VALIDATED axis. More principled, not more
  verifiable.** The 7-yr P(never) tail stays robust to all of it; the effect lives in timing + trough
  depth, where options are sensitive. Reporter: `earnings_collapse.py`.

## 6. Two-ledger valuation (`value_check.py "NAME" [tenor strike premium]`)
**STOCK** (`stock_premium.py`): base=EPS·15.8; anchored=EPS·(15.8+justified_pts) = **FRAGILITY FLOOR,
NOT a target**; AUTO TAM-haircut inline + Tier + confidence + reverse-DCF. **OPTION** (`premium_check.py`):
§7.

## 7. Options layer
Physical measure: `fair = e^(-rT)·E[max(S_T - K, 0)]` over simulated paths — thesis-conditional edge,
NOT arbitrage; **blind to IV / vega / IV-crush.** 16 names × 6/12/18/24/36m (interp) × strikes 0.50–2.50.
Multi-leg = signed sum (verticals, butterflies, tail-kickers). Bans: net-naked upside shorts,
negative-payoff customs, secular broken-wing flies, reversed strikes, no calendars/diagonals.
**P(profit) ≠ P(ITM)**: deep-ITM ~81% ITM yet ~51% profit; `P(profit)=P(S_T > K + premium·e^{rT})`.
**RULE:** archetype → tenor-vs-cycle → structure → premium vs fair → macro → (sizing is the user's). A
positive edge does NOT pass a failed gate.

## 8. Honesty & governance layer
- **`tam_haircut.py` + AUTO in stock ledger** — TAM ×0.5, CAGR −15pts; real vs borrowed resilience.
- **`tier_gate.py` — MANDATORY haircut panel** (base / TAM / moat−.15 / margin / **rate+input**) → Tier.
  **Tier 1 ("clean core") requires base fragility < 0.20 AND worst-across-ALL-panels < 0.30.** The
  **rate+input** column applies the profit-sensitivity addons (input-cost → earn_quality, interest →
  balance) — it is the binding worst-case for memory (Micron, Kioxia) and a non-event for NVIDIA.
- **`confidence.py`** — per-output High/Med/Low; option-fair capped lower (timing + IV-blind) = "good
  under thesis", not "good trade".
- **`reverse_dcf.py`** — implied expectations / structural ceiling. "You cannot grow out of weak pricing power."
- **`provenance.py` + `input_provenance.py`** — structured audit of every research-judgment input (moat,
  tam_cagr, struct_share, pricing_power, op_margin, fixed_cost_ratio, rev_drawdown, **cogs_fragility,
  net_debt_to_ebitda, floating_rate_share**, price, net_cash) with confidence, low/base/high range,
  source, and a model-sensitivity tag. Flags **HOTSPOTS** (HIGH-sensitivity AND not high-confidence:
  moat, TAM, revenue-drawdown, cogs_fragility) and **DRIFT-checks** each base value against the live
  calibration. Adds NO synthetic precision, changes NO engine math. Drift check passes (audit == live).

## 8b. Ranking & the league (`league.py`, `tiering.py`, dashboard)
- **Headline ranking metric = reward-vs-S&P** (`tiering.py` `vs_sp`): `reward_vs_SP = (growth / S&P growth) × (S&P tail / name tail)`, **S&P (VOO) ≡ 1.00**; `tail` = the raw >3y permanent-loss tail (`p_deep_permanent`). Above 1 = more growth per unit of long-drawdown risk than the index. `reward_vs_SCHD` is the same vs SCHD. This is the default sort everywhere and the master-ranking key in `complete_report.md`.
- **The league (`league.py`)** turns that ranking into a **fixed-size board**: `POOL_CAP = 125` tracked, `VIEW_CAP = 50` highlighted on the dashboard. **Everything competes** (stocks + ETFs); the **VOO/SCHD benchmarks are pinned** (shown for comparison, do not consume a slot) and **leveraged 3× vehicles are excluded**.
- **Admission/eviction + hysteresis**: a name **enters only when it out-ranks an incumbent by > MARGIN (5%)**, else the incumbent stays — so Monte-Carlo noise near the cut-off does **not** churn the standings or the published graphs. Nothing genuinely new ⇒ no change; a genuine breakout ⇒ it displaces the weakest member. `league.json` records members (rank, top50, pinned, first_seen) + `entered`/`exited` per run.
- **Pool pruning**: after each run, `discovery/expansion.json` is pruned to the league + a churn buffer (`POOL_CAP + 25`), so the priced universe — and engine cost — stays bounded while the board can still turn over.
- **Discovery is a screen, not a quota**: the weekly job casts a wide net (`expand_universe.py --n 50`) to feed candidates into the pool; the **league**, not the proposal count, decides membership.
- **Dashboard sort**: clicking any column header **re-orders the displayed Top-50** by that field (asc/desc toggle) — it does **NOT** change league membership. Available in both Beginner and Expert views. The default order is reward-vs-S&P (the league rank). `snapshot.json` carries per-row `rank`/`top50`/`in_league` + a `league` summary.

## 9. CANONICAL NUMBERS (build 2026-06-13, all layers ON, ~10k MC / 8k options)
**BASE_PE 15.8 · R_GROWTH 0.09 · T_sat cap 15y · stress 48/100 (58/25) · backtest 7/7 (depth) ·
USE_COMPETITIVE/CASH/EARNINGS_COLLAPSE/ENDOGENOUS_EARNINGS/PROFIT_SENSITIVITY=True · RATE_SHOCK_K 0.06 ·
INPUT_SHOCK_K 0.35 · BUYBACK_PCT 0.**

P(never) (lower=safer; ±1–2): NVIDIA 21 · Marvell 23 · AMD 24 · Qualcomm 26 · Broadcom 29–30 · Kioxia 30 ·
ARM 35 · Micron 37. *(Extended, by P(never): Astera 22, Palantir 24, CoreWeave 46.)*

Growth (18m): Micron 50 · NVIDIA 45 · AMD 45 · Broadcom 38 · Marvell 35 · ARM 25 · Qualcomm 8 · Kioxia 5.
SAM gap: ARM 69 · AMD 34 · NVIDIA 32 · Broadcom 32 · Marvell 28 · rest 0.

Premium decomp (justified/premium pts; floating%): NVIDIA 13.0/14.2 (4%) · Broadcom 7.9/13.2 (18%) ·
AMD 7.9/11.2 (12%) · ARM 24.6/54.2 (42%) · Palantir 53.0/79.2 (28%) · Astera 45.9/74.2 (31%) · CoreWeave
49.5/104.2 (recovery_quality 0.00) · Micron premium 0.

Balance (net_cash/mcap | balance | fragility): NVIDIA +0.04/0.95/0.07 · ARM +0.04/0.80/0.28 · AMD
+0.05/0.70/0.18 · Qualcomm +0.06/0.70/0.15 · Micron +0.02/0.60/0.25 · **Broadcom ~net DEBT/0.45/0.25**.

Earnings cyclicality (incl. profit-sensitivity addons | EPS trough | P/E expansion): Micron 0.95 / 95% /
~20.0× · Kioxia 0.95 / 95% / ~20.0× · Marvell 0.57 / 57% / ~2.3× · AMD 0.52 / 52% / ~2.1× · Qualcomm
0.37 / 37% / ~1.6× · Broadcom 0.35 / 35% / ~1.5× · NVIDIA 0.25 / 25% / ~1.3× · ARM 0.22 / 22% / ~1.3×.
Profit-sensitivity addons (interest+input): NVIDIA +0.00/+0.02 · Broadcom +0.03/+0.04 · AMD +0.00/+0.10 ·
Marvell +0.02/+0.08 · CoreWeave large (levered + power) → clips to 0.95. Memory already wiped → addons
absorbed at the 0.95 clamp.

**Tier panel (fragility: base / TAM / moat−.15 / margin / rate+input → worst → Tier):**
```
NVIDIA   0.07 0.07 0.07 0.14 0.08 ->0.14 Tier 1 CLEAN CORE
Qualcomm 0.15 0.15 0.15 0.20 0.17 ->0.20 Tier 1
AMD      0.18 0.19 0.18 0.25 0.21 ->0.25 Tier 1
Marvell  0.20 0.25 0.20 0.26 0.22 ->0.26 Tier 1
Micron   0.25 0.25 0.25 0.29 0.31 ->0.31 Tier 2  (rate+input now binding)
Palantir 0.29 0.30 0.30 0.37 0.30 ->0.37 Tier 2
Broadcom 0.25 0.38 0.28 0.31 0.27 ->0.38 Tier 2  (borrowed via TAM)
Astera   0.33 0.35 0.34 0.42 0.36 ->0.42 Tier 2
ARM      0.28 0.46 0.32 0.35 0.29 ->0.46 Tier 2  (held OUT of T1 by TAM)
Kioxia   0.35 0.35 0.35 0.40 0.43 ->0.43 Tier 3  (rate+input now binding)
CoreWeave 0.61 0.62 0.62 0.70 0.69 ->0.70 Tier 3
```
(No tier flipped; the rate+input panel tightens the gate and becomes the binding worst-case for memory.)

Confidence: NVIDIA High/High/High · AMD High/Med/High · Marvell & Qualcomm High/Med/Med · Broadcom Med ·
Micron Med · ARM/Palantir/Astera Med · CoreWeave Med/**Low**/**Low**. Option-fair ≤ P(never) grade.
Reverse-DCF structural ceiling: NVIDIA 92 · ARM 87 · Broadcom 84 · AMD 75 · Palantir 73.

Option fair (deep-ITM K=0.75, 24m/36m % of spot): NVIDIA 51.7/64.9 · Astera 58.3/74.6 · Palantir
49.2/60.3 · Broadcom 44.3/53.0 · AMD 49.8/62.0 · Micron 36.3/41.0 · CoreWeave 65.1/85.5 (SPREADS ONLY) ·
IonQ 38.6/43.6 (BROKEN) · DRAM 35.0/39.2 · SMH 38.5/44.4.

TAM-haircut (floating% base→haircut): NVIDIA 4→4 · AMD 12→14 · Marvell 9→20 · Broadcom 18→46 · ARM 42→77.
ETF horizon (1y/2y/3y/5y): DRAM 4/33/68/181 (≥2y) · CHAT 9/24/48/115 · SMH 7/21/42/103 · SOXX 6/19/38/93.
Input HOTSPOTS (provenance): moat, tam_cagr, rev_drawdown, cogs_fragility across the core names.

## 10. Model's read (in its own terms — not advice)
NVIDIA = clean core (Tier 1, lowest P(never), 4% floating, net cash, low cyclicality, immune to rate+input
stress, robust to every haircut + moat sensitivity, High confidence; held NVDA Dec-2028 $150C ~K/S 0.73 ≈
fair at live ask). Astera = highest secular-gated option fair value AND 2nd-lowest P(never), but Tier 2
(PEG-fast/MC-uncertain) → satellite. Palantir/Broadcom secular but more floating; Broadcom leans on TAM +
net debt + rate sensitivity (Tier 2). Micron/AMD/DRAM/Kioxia cyclical → ownable equity; options deep-ITM/
long only, never short/naked; the pain is the WAIT (EPS wipe + input-cost/fab fragility, ~20× trough P/E),
not permanent loss. CoreWeave Tier 3, highest option fair (right-tail illusion), survivability gate
(leverage + power + input cost) → spreads only. IonQ broken; QTUM broken ETF.

## 11. Limits & standing caveats (always state)
(1) Physical-measure, NOT risk-neutral; blind to IV/vega/IV-crush. (2) P(profit) ≠ P(ITM). (3)
Reduced-path (±1–2 on P(never)); rerun 150k. (4) Inputs are research judgments — now AUDITED with
confidence/range/source + HOTSPOT + drift checks (provenance), incl. the profit-sensitivity inputs; moat
is the most dangerous knob. (5) Anchored value is a fragility floor, not a target; reverse-DCF = implied
expectations. (6) Buyback de-rating gated by accretion. (7) Single-factor universe valid within AI/semis
(~1 effective bet); multi-factor covariance NOT YET BUILT (needs real multi-sector returns). (8)
Pre-earnings names use a sentinel P/E → gated, not scored (EV/Sales module NOT YET BUILT). (9) Cyclical
earnings collapse is ENDOGENOUS from operating leverage + profit-sensitivity (interest-expense + input-
cost); **taxes deliberately excluded** (slow/telegraphed, not a panic driver). These sharpen trough depth
+ recovery TIMING — the LEAST-VALIDATED axis; the 7-yr P(never) tail stays robust. (10) Backtest validates
DEPTH, not recovery TIMING; option-fair confidence capped; recovery-timing validation NOT YET BUILT (needs
historical price series). (11) IV / risk-neutral bridge — IMPORTANT ACCOUNTING: the core option lens REMAINS physical-measure and IV-BLIND (it never sees IV, vega, skew, or IV-crush). The new broker_bridge.py is a SEPARATE market-pricing OVERLAY that sits OUTSIDE the physical model and can VETO or downgrade a model-positive trade using a REAL broker quote — it computes the Volatility Risk Premium (model physical fair vs market price) and IV-richness / event-crush / liquidity vetoes. It is a veto, not a replacement for model fair value, and it invents NO IV: no verdict without a real quote. broker_adapters.py supplies the quote (pluggable Tradier / Polygon / IBKR / Schwab fetchers; IV rank COMPUTED from history — IBKR native, else a local daily log, else a flagged realized-vol proxy; earnings date MANUAL); the live feed is YOURS to connect. Net: the model says "good under thesis"; only the overlay + your data say "good trade". (12) **Research model — NOT investment advice; gates are not green lights;
never co-sign an allocation or order.**

*End of Claude grounding document — build 2026-06-13 (competitive + cash + earnings-collapse + endogenous-leverage + profit-sensitivity + governance + provenance).*


================================================================================
HONEST-SIX TRACEABILITY LAYER  (added 2026-06-13)
LABEL: A/A- TRACEABILITY UPGRADE -- *NOT* an A+ CALIBRATION UPGRADE.
These six make the earnings-collapse / profit-sensitivity layer more EXPLAINABLE,
AUDITABLE, and DIAGNOSTIC. They do NOT prove the recovery-timing axis. All baseline
numbers (cyclicality, fragility, tiers, P(never)) are UNCHANGED -- verified, test suite
ALL PASS. The A+ gate remains: sector calibration + recovery-timing backtest + REAL
historical data (the data project; see A_PLUS_DATA_PROJECT_SPEC.md). Do not let the model
look more proven than it is.
--------------------------------------------------------------------------------
1. earnings_waterfall.py -- traceable income statement (revenue shock -> variable cost ->
   fixed-cost absorption -> EBIT -> input-cost & interest drags -> EPS trough). RECONCILES
   to engine earnings_cyclicality (AMD 0.515=0.515, Micron 0.95=0.95). Shows WHAT crushes
   EPS, not just that it does (Micron: fixed cost doesn't scale -> EBIT 0.008 on -36% rev).
   recovery_delay is a MODEL ESTIMATE, stamped timing-UNVALIDATED.
2. profit_sensitivity_attribution.py -- decomposes worst-case fragility by binding panel
   (NVIDIA->margin 0.143, Micron->rate+input 0.315, Broadcom->TAM 0.383) + EPS-trough
   drivers (op-leverage/input-cost/interest). Pure decomposition; no new inputs.
3+4. COGS BUCKET SPLIT (USE_COGS_BUCKETS, engine._effective_cogs_fragility) -- scalar
   cogs_fragility -> weighted COGS_BUCKETS (wafer_foundry/advanced_packaging/hbm/asp_cycle/
   fab_utilization/energy_power/gpu_depreciation/optical_components/cloud_opex/labor/
   customer_capex) x COGS_BUCKET_SHOCKS (baseline 1.0). Weights SUM to the prior scalar ->
   baseline cyc/P(never) UNCHANGED; raise a shock to stress one cost driver. Provenance now
   drift-checks cogs_fragility vs the bucket rollup (drift=0). TAGGED JUDGMENT-HEAVY until
   the historical-calibration data project is done.
5. option_timing_overlay.py -- per (name,tenor) flags EPS-trough/recovery before expiry +
   timing-stressed P(profit) (heuristic, labeled). Formalizes "no short-dated memory calls"
   (Micron 6/12m REJECT, 36m OK; NVIDIA OK; CoreWeave 24m REJECT). EVERY output stamped
   "recovery timing NOT historically validated (#2/#3 data project)".
6. tax_and_policy_scenarios.py -- QUARANTINED long-horizon panel (tax_+5pt / chips_subsidy_
   loss / tariff_shock / rnd_capitalization) affecting anchored value / reverse-DCF / buyback
   ONLY. NEVER P(never) / recovery / option gate. Imports nothing into the engine; panic core
   untouched (verified).
================================================================================


BASKET BUILDER (basket_builder.py, added 2026-06-13): construct your OWN ETF / option basket from
analyzed names (100% coverage by construction -- aggregates analysis already trusted, no holdings
guessing). Weights by risk+value (low fragility-dispersion / low floating-premium / capped). Evaluates
the basket as ONE object: aggregate floating premium + concentration, recovery split (fast/slow/perm),
the DISTRIBUTION across holdings (fragility dispersion, weak-tail weight, premium concentration -- what
the weighted mean hides), and CORRELATION-ADJUSTED effective-N from correlation.py (crisis rho->0.92,
NOT weight-based) + portfolio drawdown prob. Stocks AND option baskets (latter: long options on
correlated names COMPOUND, do not offset -- combined tail worse than average). REPORTS effN + tail and
lets the user decide; does NOT optimize for return (no P&L data -> overfit), does NOT size positions.
Key demonstrated result: a hand-picked "best names" basket is still ~1 effective bet in a panic (effN
~1.0-1.1 vs 6-9 names) -- the model refuses the fake-diversification illusion even on a self-built basket.
RESEARCH MODEL -- NOT INVESTMENT ADVICE.

ETF DISTRIBUTION LENS (etf_distribution_lens.py, added 2026-06-14; spec ETF_DISTRIBUTION_LENS_SPEC.md):
distribution-aware ETF risk/valuation one level below the weighted-average synthetic-company view. Runs
on REAL ETFs (covered subset, coverage<40%=>diagnostic-only, QTUM veto intact) AND custom baskets. Adds:
balance-sheet distribution (net-cash/net-debt wt, dispersion), fragility tail (p75/p90, recovery_barbell),
recovery+premium ATTRIBUTION (which names drive fast/slow/perm and the floating premium), premium_effN +
weak_tail_effN (distinct from weight-effN), a CONSTRAINT-CHECKER (pass/fail vs max-concentration/min-effN/
max-weak-tail/max-cyclical -- NOT an optimizer), and a side-by-side comparison card (custom baskets vs SMH/
CHAT/SOXX/DRAM/NVDA-only). NON-DESTRUCTIVE: adds diagnostics, never overwrites etf_lens. HELD LINES: no
return-maximizing weight search (overfit), virtual basket option is analytics-only/non-tradable, no sizing.
RESEARCH MODEL -- NOT INVESTMENT ADVICE.

EXECUTION-COST AGGREGATOR (execution_cost.py, added 2026-06-14; Gemini red-team 3.C): a multi-leg
option basket can beat a liquid ETF on SURVIVAL metrics yet lose the edge to bid/ask SLIPPAGE across
N legs. broker_bridge checks one contract; this sums COMBINED slippage+commission across the basket,
compares to a single liquid ETF proxy, and nets the modeled VRP advantage against the INCREMENTAL
execution drag: if drag >= modeled advantage -> EXECUTION ERASES THE EDGE -> trade the ETF proxy. Uses
per-leg spread/OI broker_bridge already consumes (no new fabricated inputs); refuses EXAMPLE quotes.
COMPARISON-CARD EXTENSION (etf_distribution_lens, 2026-06-14): added CANONICAL P(never) per basket/ETF via correlation.basket_terminal -- a portfolio-of-paths sim reconciled to the engine's CONDITIONAL definition P(never recover given drawdown>25 percent); NVDA-only reconciles to ~21 percent = canonical NVIDIA, so custom baskets and real ETFs are apples-to-apples. Also added an OPTION-SUITABILITY FLAG (cyclical-heavy -> no short tenor, deep-ITM/long only; premium-concentrated -> single-name-like; weak-tail -> defined-risk only; coverage<40 percent -> speculative/low-confidence). Expected-return-by-horizon was DELIBERATELY NOT added (it leans hardest on the unvalidated growth/timing axis -- adding it would dress a curated estimate as a forecast). RESEARCH MODEL -- NOT INVESTMENT ADVICE.
OPTION-FAIR RE-VERIFIED (2026-06-14): options_lens re-run at 30k paths against the fully-layered build
(earnings-collapse + endogenous-leverage + profit-sensitivity active). Reconciled to the documented
option-fair table; max drift 2.3 pts (CoreWeave 36m), all else within ~1.5 (30k-vs-8k sampling noise).
The new trough-depth/timing layers do NOT materially move deep-ITM/long-dated fair values (correct: they
bite in the SHORT-dated cyclical structures the timing gate already rejects, not in deep-ITM payoff).
The shipped options_lens.json/.md now carry the 30k numbers. Canonical option-fair table CONFIRMED CURRENT.

S&P-NORMALIZED DRAWDOWN/RECOVERY (2026-06-14, drawdown_normalization.py): expresses each name's drawdown
DEPTH and recovery LENGTH as a RATIO to a synthetic S&P-500 reference leg, measured on the SAME market-
crisis paths (paths where the S&P itself fell more than 25 percent). DEPTH ratio is BETA-GROUNDED and ships
(Qualcomm ~1.0x stabilizer -> Micron ~1.2x -> CoreWeave ~1.8x). RECOVERY-LENGTH ratio is DEFERRED: the
synthetic leg is wrong-signed (beta-symmetric mean-reversion makes high-beta names appear to recover FASTER
than the index, contradicting Micron's EPS-trough reality) -- gated behind real S&P anchors + per-archetype
calibration (DRAWDOWN_NORM_CALIBRATION_SPEC.md). P(never recover | crisis) ships as a relative survival
signal. Normalizing changes UNITS, not validation status; recovery timing remains UNVALIDATED. 1-5 BANDS now reported on both axes (B1=~S&P, higher=more): DEPTH bands SHIP (B1 Qualcomm stabilizer / B2 the AI-semi pack ~1.2x -- they barely differ on depth in a crisis / B3 Astera / B4 CoreWeave); RECOVERY bands are PRIOR-ONLY (archetype prior: memory B4-5 slow, secular B1-2 fast) with a synthetic WRONG-SIGNED band shown only to expose the artifact -- Micron synth says fast, prior says slow; calibration must confirm the prior. Spec adds depth_adjusted_recovery_ratio, two-benchmark (macro+sector), price-vs-total-return.

OPTION GATED SCREENER (2026-06-14, option_gated_screener.py): SCOPE single calls + DEBIT VERTICALS (flies/tail-kickers deferred to a payoff-grid engine; out-of-grid P(profit) flagged not clamped). lexicographic gated screener (NOT an optimizer). Vetoes gate/broken/survivability -> tenor-vs-recovery-prior -> structure -> premium-vs-fair (live) -> broker/IV (broker data) -> execution-cost (multi-leg) -> max-debit, THEN ranks survivors by P(profit)=P(S_T>K+premium*e^rT), computed as P(ITM at the breakeven strike) via options_lens p_itm interpolation. ANALYSIS mode (default) = gate-survivor list, never PASS without a live premium, NOT a trade ranking (P(profit-at-fair)~0.5 by construction). LIVE mode (--premiums) evaluates your quoted contracts, ranks by real P(profit), rejects rich/gated. NO weighted score, NO expected-return, NO sizing. P(profit) HIGH-confidence only in long-dated deep-ITM regime; timing axis still UNVALIDATED. Honest name: gated screener, not validated optimizer.
