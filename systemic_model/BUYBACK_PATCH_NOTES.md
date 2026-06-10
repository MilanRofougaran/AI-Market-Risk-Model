# Buyback patch — what changed (drop these 3 files into the project)

## 1. calibration.py
- NEW constant `CASH_YIELD_AFTER_TAX = 0.035` — single source for the buyback
  accretion test (E/P > this), read by both fundamental_catchup and engine.

## 2. fundamental_catchup.py  (closed-form earn-back clock)
- `_trough_buyback()`: added an **accretion gate**. A board only retires shares
  when EPS rises, i.e. `(1 - unsupported_frac)/buy_price_frac > cash_yield*PE`
  (cash-size-independent form of `eps_lift > 1`). If dilutive, `deploy -> 0`.
  Both the gate and the interest drag now use `C.CASH_YIELD_AFTER_TAX`.
- `run()`: `years_bb` is floored at the naive `years` (the buyback is an OPTION,
  never exercised to slow recovery). Narrative paragraph rewritten to the gated
  result: under pure multiple-compression the rational buyback fires for NO name
  here, because the compression discount and an accretive multiple are
  anti-correlated (high-PE names have the drop but are dilutive; low-PE names are
  accretive but have no gap -> "0y").
- Effect: Alphabet 1.3y->1.5y (dilutive) is gone; it now reads 1.3y / no float-cut.

## 3. engine.py  (Monte-Carlo path-keyed slingshot — the new capability)
- `import extension_data as X` (pure data, no circular import).
- `company_to_spec()`: emits a `bb` sub-spec (cash_used, pe_peak, unsup,
  cash_yield, min_depth) for cash-rich, durable names via the same procyclical
  gate. ETFs aren't in NET_CASH_TO_MCAP -> net_cash 0 -> no slingshot (correct).
- `_drawdown_and_recovery(..., bb=None)`: on each path, if the realized drawdown
  is a real panic (depth >= min_depth=0.25) AND accretive at that depth, the firm
  deploys cash at the trough; a depth-scaled float cut `min(0.25, cash_used/
  buy_price_frac)*(1-unsup)` lifts the post-trough per-share path by `eps_lift =
  (1-interest_drag)/(1-float_cut)`, clamped to >= 1. Drawdown DEPTH is unchanged;
  only recovery speeds up. Threaded through both `run_companies` and the
  dominance sweep.
- This is where a deep panic creates the accretive opportunity the closed-form
  clock structurally can't see. Validated A/B (same paths): a PE-14 / 25%-net-cash
  name's P(recover<18m | fell>25%) rises 22.7%->39.6%, median 12.7m->7.8m, while a
  PE-60 name stays dormant (gate) and P(>25% fall) is unchanged in both.

All 27 invariants in test_model.py still PASS.
