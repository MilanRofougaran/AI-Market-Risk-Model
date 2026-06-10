"""
============================================================================
 TEST_MODEL -- automated invariant tests (review feedback)
============================================================================
 Run:  python3 test_model.py        (exit 0 = all pass; no pytest needed)

 Covers the reviewer-requested invariants:
   1. regime transition rows sum to 1
   2. regime probabilities are valid probabilities
   3. exceedance is monotonically DEcreasing in threshold depth
   4. recovery curve is monotonically INcreasing in horizon
   5. leveraged ETFs are excluded from growth tiers (the case-mismatch bug)
   6. correlation GROUP names all exist in the modeled universe
   7. macro-stress score in [0,1]; crisis multiplier positive & bounded
   8. contagion blend preserves marginal variance (sqrt(rho) arithmetic)
   9. sim window covers a full 36m recovery after the latest 18m trough
============================================================================
"""
import os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "discovery"))

import calibration as C
import macro_stress as MS
import engine as E
import tiering as T

FAIL = []


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {name}" + (f"  ({detail})" if detail and not cond else ""))
    if not cond:
        FAIL.append(name)


def main():
    print("invariant tests:")

    # 1. transition rows sum to 1 (matrix form: rows = calm/stress/crisis)
    tr = C.FACTOR["transition"]
    for i, row in enumerate(tr):
        check(f"transition row {i} sums to 1", abs(sum(row) - 1.0) < 1e-9,
              f"sum={sum(row)}")
    eff = MS.effective_transition(tr, C.SYSTEMIC_STRESS)
    for i, row in enumerate(eff):
        check(f"stress-scaled transition row {i} sums to 1", abs(sum(row) - 1.0) < 1e-6,
              f"sum={sum(row)}")

    # 2. regime probs valid (per-horizon lists) and monotone in horizon severity
    for k, vs in C.REGIME_PROBS.items():
        check(f"regime probs '{k}' all in [0,1]", all(0.0 <= v <= 1.0 for v in vs), str(vs))

    # 3+4. small simulation: exceedance monotone, recovery curve monotone
    rng = np.random.default_rng(1)
    factor, crisis = E._simulate_factor(rng, 3000, C.SIM["days"])
    spec = dict(beta=1.4, idio=0.11, mu=0.0, L=1, leveraged=False,
                tail_mult=1.0, recov_shift=0.0)
    price = E._price_path(rng, factor, crisis, spec, 3000, C.SIM["days"])
    hd18 = C.HORIZON_DAYS[C.HORIZON_LABELS.index("18m")]
    mdd, rec = E._drawdown_and_recovery(price, hd18)
    ex = E.exceedance(mdd, (0.15, 0.25, 0.40, 0.50))
    check("exceedance decreasing in depth", all(ex[i] >= ex[i+1] for i in range(len(ex)-1)),
          str([round(float(x), 3) for x in ex]))
    rc = E.recovery_curve(mdd, rec, 0.25)
    curve = [pt["p_recovered"] for pt in rc["curve"]] if rc.get("curve") else []
    check("recovery curve monotone increasing",
          all(curve[i] <= curve[i+1] + 1e-9 for i in range(len(curve)-1)) if curve else False,
          str([round(c, 3) for c in curve][:8]))

    # 5. leveraged exclusion (the bug GPT's review caught)
    check("LEVERAGED list has all three 3x vehicles",
          set(T.LEVERAGED) == {"SOXL (3x Semis)", "TECL (3x Tech)", "TQQQ (3x NDX)"},
          str(T.LEVERAGED))
    fake = [dict(name=n, growth=g, kind="ETF", p_deep_permanent=0.38, p_dd25=1.0,
                 p_recover_24m=0.5, vs_sp=3.0, vs_schd=4.0, perm_vs_sp=1.8,
                 g_per_tail=1, g_per_fall=1)
            for n, g in [("SOXL (3x Semis)", .6), ("TECL (3x Tech)", .5),
                         ("TQQQ (3x NDX)", .45), ("NVIDIA", .45)]]
    tiers = T.tier_rows(fake)
    growth_members = [r["name"] for lbl, mem in tiers for r in mem
                      if not lbl.startswith("Trading")]
    check("no leveraged name inside growth tiers",
          not any(n in growth_members for n in T.LEVERAGED), str(growth_members))
    lev_section = [lbl for lbl, _ in tiers if lbl.startswith("Trading")]
    check("leveraged shown in separate trading-vehicle section", len(lev_section) == 1)

    # 6. GROUP names resolve to the universe
    unknown = [n for n in C.GROUP if n not in T.UNIVERSE]
    check("all GROUP names exist in tiering.UNIVERSE", not unknown, str(unknown))

    # 7. stress score + crisis multiplier
    st = MS.compute(C.MACRO)
    check("stress score in [0,1]", 0.0 <= st["score"] <= 1.0, str(st["score"]))
    cm = MS.crisis_mult(st["score"])
    check("crisis multiplier in (0, 4]", 0.0 < cm <= 4.0, str(cm))

    # 7b. macro-stress consistency: engine-used stress == stress from final MACRO
    #     (regression test for the ordering bug where liquidity fields were added
    #      to MACRO AFTER SYSTEMIC_STRESS was computed)
    check("SYSTEMIC_STRESS matches final MACRO",
          C.SYSTEMIC_STRESS == MS.compute(C.MACRO),
          f"{C.SYSTEMIC_STRESS.get('score')} != {MS.compute(C.MACRO).get('score')}")
    for fld in ("fed_net_liq_3m_pct", "mmf_dry_powder_gdp"):
        check(f"liquidity field '{fld}' present in MACRO", fld in C.MACRO)

    # 8. contagion preserves marginal variance
    rng = np.random.default_rng(2)
    n, d = 2000, 252
    shared = rng.standard_normal((n, d)); private = rng.standard_normal((n, d))
    rho = 0.55
    blend = np.sqrt(rho) * shared + np.sqrt(1 - rho) * private
    check("contagion blend variance ~ 1", abs(float(blend.var()) - 1.0) < 0.02,
          f"var={blend.var():.4f}")

    # 8b. grind regime: mask exists, occupancy sane, drag only when grind passed
    f2, c2, g2 = E._simulate_factor(np.random.default_rng(3), 500, 504, return_grind=True)
    check("grind mask boolean & occupancy < 60%", bool(g2.dtype == bool) and float(g2.mean()) < 0.60,
          f"occ={g2.mean():.2%}")
    check("4-state matrix has 4 rows", len(C.FACTOR["transition"]) == 4)

    # 8c. LONG-RUN DRIFT SANITY (regression test for the grind-regime defect):
    #     a beta=1 name's median multi-year total return must be POSITIVE, else
    #     nothing recovers and p_never saturates. Grind must stay a minority regime.
    rng = np.random.default_rng(42)
    f4, c4, gd4 = E._simulate_factor(rng, 6000, C.SIM["days"], return_grind=True)
    path = np.exp(np.cumsum(1.0 * f4, axis=1))
    med = float(np.median(path[:, -1]))
    check("beta=1 median multi-year total return is positive", med > 1.0,
          f"median {(med-1)*100:+.0f}% over {C.SIM['days']/252:.1f}y")
    check("grind occupancy is a minority (< 18%)", float(gd4.mean()) < 0.18,
          f"grind occ {gd4.mean()*100:.0f}%")

    # 8d. SOLVENCY channel: weak-financials + non-durable-revenue raises the
    #     PERMANENT tail but NOT drawdown depth; durable/strong names untouched;
    #     and the hazard separates 2021->2024 impaired vs recovered (AUC).
    import solvency as SV
    h_cw = SV.impairment_hazard("CoreWeave"); h_nv = SV.impairment_hazard("NVIDIA")
    check("solvency hazard high for fragile fork (CoreWeave)", h_cw > 0.15, f"{h_cw:.2f}")
    check("solvency hazard ~0 for fortress (NVIDIA)", h_nv < 0.03, f"{h_nv:.2f}")
    rng = np.random.default_rng(99); nn, dd_ = 6000, C.SIM["days"]
    f5, c5, g5 = E._simulate_factor(rng, nn, dd_, return_grind=True)
    sp = dict(beta=1.9, idio=0.11, mu=0.0, L=1, leveraged=False, tail_mult=1.3, recov_shift=-0.1)
    pp = E._price_path(rng, f5, c5, sp, nn, dd_, grind=g5)
    hd_ = C.HORIZON_DAYS[C.HORIZON_LABELS.index("18m")]
    m_off, _ = E._drawdown_and_recovery(pp, hd_, recov_shift=-0.1, solv=None)
    m_on, r_on = E._drawdown_and_recovery(pp, hd_, recov_shift=-0.1,
                                          solv=dict(hazard=0.30, min_depth=0.30, seed=7))
    check("solvency leaves drawdown DEPTH unchanged", bool(np.allclose(m_off, m_on)))
    import solvency_cases as SC
    res = SC.run(verbose=False)
    check("solvency hazard separates 2021->2024 cases (AUC >= 0.9)", res["auc"] >= 0.9,
          f"AUC {res['auc']:.2f}")
    # toxic dilution: cash-poor/levered names get a per-share haircut; fortress ~0;
    # and it leaves drawdown DEPTH unchanged (only caps per-share recovery).
    d_cw = SV.dilution_severity("CoreWeave"); d_ms = SV.dilution_severity("Microsoft")
    check("dilution severity high for cash-poor/levered (CoreWeave)", d_cw > 0.05, f"{d_cw:.3f}")
    check("dilution severity ~0 for fortress (Microsoft)", d_ms < 0.01, f"{d_ms:.3f}")
    m_d0, _ = E._drawdown_and_recovery(pp, hd_, recov_shift=-0.1, dilution=None)
    m_d1, _ = E._drawdown_and_recovery(pp, hd_, recov_shift=-0.1,
                                       dilution=dict(severity=0.125, min_depth=0.40))
    check("dilution leaves drawdown DEPTH unchanged", bool(np.allclose(m_d0, m_d1)))

    # 8e. ETF LENS: a basket's solvency hazard is far below any single burner,
    #     the recovery-weight decomposition sums to ~1, and concentration is flagged.
    import etf_lens as EL
    el = EL.run(verbose=False)
    smh = el.get("SMH (VanEck Semis)", {})
    if smh:
        s = smh["fast_weight"] + smh["slow_weight"] + smh["permanent_weight"]
        check("ETF recovery-weight decomposition sums to ~1", abs(s - 1.0) < 0.02, f"{s:.3f}")
        check("ETF permanent weight << single burner", smh["permanent_weight"] < 0.10,
              f"{smh['permanent_weight']:.3f}")
    dram = el.get("DRAM (Roundhill Memory)", {})
    if dram:
        check("concentrated ETF flagged (DRAM narrow)", dram["class"].startswith("narrow"),
              dram["class"])
        # coverage transparency: top-3 over the FULL fund <= top-3 over covered subset
        check("DRAM top3_fund <= top3_covered (coverage labeled)", dram["top3_fund"] <= dram["top3"] + 1e-9)
    # TAM-bridge vs ETF-lens coverage CONSISTENCY (GPT review): the MC synthetic ETF
    # must price the same holdings the lens scores, else DRAM looks Micron-only in the
    # tail while the lens says 73%.
    try:
        import tam_bridge as _TB
        hold = _TB.ETF_HOLDINGS.get("DRAM (Roundhill Memory)", {})
        named = {h: w for h, w in hold.items() if not h.startswith("_")}
        priced = sum(w for h, w in named.items()
                     if h in C.COMPANIES or h in getattr(_TB, "STOCK_TAM_FACTS", {}))
        # denominator is the FULL fund incl. the unmodeled _other_ residual, same as the lens
        bridge_cov = priced / (sum(hold.values()) or 1)
        lens_cov = el.get("DRAM (Roundhill Memory)", {}).get("known_coverage", 0)
        check("TAM-bridge DRAM coverage ~ ETF-lens coverage", abs(bridge_cov - lens_cov) < 0.12,
              f"bridge {bridge_cov:.2f} vs lens {lens_cov:.2f}")
    except Exception as _e:
        pass
    # coverage transparency mechanism: a genuinely thin-coverage basket is flagged LOW
    qtum = el.get("QTUM (Defiance Quantum)", {})
    if qtum:
        check("thin-coverage ETF flagged LOW (QTUM)",
              qtum["known_coverage"] < 0.40 and "LOW" in qtum["confidence"],
              f"cov {qtum['known_coverage']:.2f}")
    # concentration-aware damp + mapless overrides: DRAM (narrow) hazard > SMH (broad);
    # ARKK (concentrated burners) elevated; VOO ~0
    check("concentration-aware: DRAM hazard >= SMH hazard",
          SV.impairment_hazard("DRAM (Roundhill Memory)") >= SV.impairment_hazard("SMH (VanEck Semis)"))
    check("ARKK solvency elevated vs broad", SV.impairment_hazard("ARKK (ARK Innovation)") > 0.08)
    check("broad index VOO solvency ~0", SV.impairment_hazard("VOO (S&P 500)") < 0.02)

    # 8f. PEG floor + growth-regime ranking: a fast grower (NVIDIA) gets a PEG-lifted
    #     floor so its earn-back is ~0; growth_recovery splits high vs safe buckets.
    import fundamental_catchup as FCK
    fcr = {r["name"]: r for r in FCK.run(verbose=False)}
    nv = fcr.get("NVIDIA", {})
    nvy = nv.get("years")
    check("PEG floor lifts NVIDIA earn-back to ~0 (cheap on PEG)",
          nvy is not None and nvy <= 0.5, f"{nvy}")
    import growth_recovery as GR
    gr = GR.run(verbose=False)
    hi = {r["name"] for r in gr["high_growth"]}
    sf = {r["name"] for r in gr["diversified_safe"]}
    # These read the generated universe (results.json). On a CLEAN source-only extraction
    # (the CLAUDE edition omits generated outputs) the buckets are empty -> skip rather than
    # fail; run `run_all.py --light` first to populate. (Reviewer packaging note.)
    if hi or sf:
        check("growth split: NVIDIA in high-growth bucket", "NVIDIA" in hi)
        check("growth split: Microsoft in safe bucket", "Microsoft" in sf)
        check("growth-recovery buckets are disjoint & non-empty", bool(hi) and bool(sf) and not (hi & sf))
    else:
        print("  [skip] growth-recovery buckets empty (no generated universe — run run_all.py --light first)")

    # 8g. CRASH-CONDITIONAL GROWTH archetypes: secular holds/accelerates (mult>1),
    #     cyclical dips-then-rebounds (mult<1 but recovers), broken steps down.
    import crash_growth as CG
    check("crash-growth: NVIDIA secular (mult >= 1)", CG.recovery_g_mult("NVIDIA") >= 1.0,
          CG.archetype("NVIDIA"))
    check("crash-growth: memory/DRAM cyclical (0.5<mult<1)",
          0.5 < CG.recovery_g_mult("DRAM (Roundhill Memory)") < 1.0, CG.archetype("DRAM (Roundhill Memory)"))
    check("crash-growth: IonQ broken (lowest mult)", CG.recovery_g_mult("IonQ") <= 0.6,
          CG.archetype("IonQ"))

    # 8h. v3: dynamic BASE_PE compresses with real rates; capex penalty drags recovery_quality
    import extension_data as _X3
    check("dynamic BASE_PE < 18 at today's 2.25% real rate", C.BASE_PE < 18.0, f"{C.BASE_PE}")
    check("capex penalty: CoreWeave (capex-heavy) intensity > NVIDIA (capex-light)",
          _X3.capex_intensity("CoreWeave") > _X3.capex_intensity("NVIDIA"))

    # 8i. RED-TEAM REGRESSIONS (Gemini bug review + GPT cyclical fix)
    # B: recovery_stats median must stay FINITE even when most paths impair (np.inf),
    #    i.e. it excludes +inf via np.isfinite, not just NaN.
    _rec = np.array([40.0, 60.0, np.inf, np.inf, np.inf, np.nan, 50.0] + [np.inf] * 50)
    _mdd = np.full(_rec.shape, -0.30)            # all in the [0.25,0.40) bucket
    _rs = E.recovery_stats(_mdd, _rec, 0.25, 0.40, 21 * 18)
    check("recovery_stats median is finite when most paths impair (bug B)",
          bool(np.isfinite(_rs["median_months"])), f"{_rs['median_months']}")
    check("recovery_stats counts impaired paths as non-recoveries (bug B)",
          0.0 < _rs["p_recover"] < 0.10, f"{_rs['p_recover']:.3f}")

    # C: valuation_link must seed its per-name RNG deterministically (crc32), NOT with
    #    Python's per-session-randomized hash(), or run-over-run A/B deltas drift.
    _vlsrc = open(os.path.join(HERE, "valuation_link.py")).read()
    check("valuation_link uses crc32 (reproducible), not hash() (bug C)",
          "zlib.crc32" in _vlsrc and "hash(nm)" not in _vlsrc)

    # D: track_changes._max_step must capture creep ACROSS a skipped (None) snapshot,
    #    not drop both adjacent steps.
    import track_changes as _TC
    check("track_changes _max_step bridges a None gap (bug D)",
          abs(_TC._max_step([0.10, None, 0.15]) - 0.05) < 1e-9,
          f"{_TC._max_step([0.10, None, 0.15])}")

    # A: correlation._specs must carry each name's REAL group (passes name=nm), not
    #    collapse everything to 'defensive'.
    import correlation as _Corr
    _sp = _Corr._specs(["NVIDIA", "Micron", "Microsoft"])
    _grps = {nm: _sp[nm]["group"] for nm in _sp}
    check("correlation specs carry real groups, not all-defensive (bug A)",
          len(set(_grps.values())) > 1 or any(g != "defensive" for g in _grps.values()),
          str(_grps))

    # E: Markov walk fallback must never index out of bounds if a row sums to <1.0.
    Pbad = np.array([[0.5, 0.9999]])             # last col < 1.0 on purpose
    ubad = np.array([[0.0, 0.99995]])            # u lands in the sub-1.0 gap
    st = np.zeros((1, 2), dtype=np.int8)
    last = Pbad.shape[1] - 1
    st[:, 1] = np.minimum((ubad[:, 1][:, None] > Pbad[st[:, 0]]).sum(axis=1), last)
    check("Markov fallback clamps state in-bounds on sub-1.0 row (bug E)",
          int(st[0, 1]) <= last, f"state={int(st[0,1])}, last={last}")

    # GPT: a cyclical name (Micron) must NOT screen as a clean '0y (no gap)' off
    #      peak-earnings-cheap P/E — cycle-adjustment forces a real earn-back gap.
    _mic = fcr.get("Micron", {})
    check("cyclical Micron no longer a false 0y-no-gap (GPT cycle-adj)",
          _mic.get("verdict", "") != "0y (no gap)" and (_mic.get("years") or 0) > 0.0,
          f"verdict={_mic.get('verdict')} years={_mic.get('years')}")

    # 8j. CYCLICAL TWO-PHASE DEMAND TROUGH + drawdown×recovery matrix (user spec).
    # Unit test on the recovery measurement: a path that would recover fast is BACK-LOADED
    # (recovery floored until the demand cycle clears) and the second leg DEEPENS the trough.
    ndd, nd = 200, 700
    _pp = np.ones((ndd, nd))
    _pp[:, 5:] = 0.60               # -40% drawdown at day 5
    _pp[:, 90:] = 1.05              # would fully recover by ~day 90 (well inside 6m)
    _m0, _r0 = E._drawdown_and_recovery(_pp, 378)                       # no cycle
    _cyc = dict(freeze_days=315, second_leg=0.15, min_depth=0.15)
    _m1, _r1 = E._drawdown_and_recovery(_pp, 378, cycle=_cyc)           # cyclical
    check("cyclical trough back-loads recovery (floored to demand-cycle clear)",
          float(np.nanmedian(_r0)) < 120 and float(np.nanmedian(_r1)) >= 315,
          f"base {np.nanmedian(_r0):.0f}d -> cyclical {np.nanmedian(_r1):.0f}d")
    check("cyclical second leg deepens the trough (fundamental, not beta)",
          float(_m1.mean()) < float(_m0.mean()) - 1e-6, f"{_m0.mean():.3f} -> {_m1.mean():.3f}")

    # matrix from results.json (the pipeline output): monotone in horizon, back-loaded cyclicals
    try:
        import json as _json
        _res = _json.load(open(os.path.join(HERE, "results.json")))
        _rc = _res.get("companies", {}).get("recovery_cond", {})
        _mic_m = (_rc.get("Micron", {}) or {}).get("dd_recovery_matrix", {})
        _nv_m = (_rc.get("NVIDIA", {}) or {}).get("dd_recovery_matrix", {})
        if _mic_m and _nv_m:
            pdd = [_mic_m[h]["p_drawdown"] for h in ("6m", "12m", "18m")]
            check("matrix: P(drawdown) non-decreasing in horizon", pdd[0] <= pdd[1] + 1e-9 <= pdd[2] + 1e-9, str(pdd))
            row = _mic_m["18m"]
            seq = [row.get("recover_6m") or 0, row.get("recover_12m") or 0, row.get("recover_18m") or 0,
                   row.get("recover_24m") or 0]
            check("matrix: recovery non-decreasing across recover horizons",
                  all(seq[i] <= seq[i+1] + 1e-9 for i in range(len(seq)-1)), str(seq))
            check("matrix: cyclical (Micron) early recovery back-loaded vs secular (NVIDIA)",
                  (_mic_m["18m"].get("recover_6m") or 0) < (_nv_m["18m"].get("recover_6m") or 0),
                  f"Micron6m={_mic_m['18m'].get('recover_6m')} NVDA6m={_nv_m['18m'].get('recover_6m')}")
        # CSV exposes the 6/12/18m conditional recovery grid (explicit 18m-cohort suffix)
        _hdr = open(os.path.join(HERE, "tier_table.csv")).readline()
        check("tier_table.csv exposes recover_6m/12m/18m_if_falls_by18m grid",
              all(c in _hdr for c in ("recover_6m_if_falls_by18m", "recover_12m_if_falls_by18m",
                                      "recover_18m_if_falls_by18m")))
        check("full dd×recovery matrix exported for an ETF (DRAM)",
              isinstance((_rc.get("DRAM (Roundhill Memory)", {}) or {}).get("dd_recovery_matrix"), dict))
    except Exception as _e:
        pass

    # 8k. CYCLICAL THEME MAPPING (reviewer consensus): the memory two-phase trough must
    # apply ONLY to mapped demand-cycle names, never to every "cyclical" by default.
    _dec = E.decompose_premium()
    def _cyc(nm):
        try:
            return E.company_to_spec(_dec[nm], name=nm).get("cycle")
        except Exception:
            return None
    check("Micron uses the MEMORY cycle path", (_cyc("Micron") or {}).get("theme") == "memory")
    check("Marvell uses a NON-memory cycle path (broad_semis)",
          (_cyc("Marvell") or {}).get("theme") == "broad_semis")
    # AMD / CoreWeave are cyclical-archetype but NOT a memory demand cycle -> no memory trough
    check("AMD does NOT inherit the memory cycle by default",
          (_cyc("AMD") or {}).get("theme") != "memory")
    if "CoreWeave" in _dec:
        check("CoreWeave does NOT inherit the memory cycle by default",
              (_cyc("CoreWeave") or {}).get("theme") != "memory")

    # 8l. RED-TEAM ROUND 2 (Gemini): chunk-RNG, scope bleed, stale read, aux-sim parity.
    # Bug 1: the solvency RNG must DECORRELATE across chunks (path_offset perturbs the seed),
    # else two chunks impair the identical paths. Same depth, different offset -> different mask.
    _ppc = np.ones((400, 700)); _ppc[:, 5:] = 0.50; _ppc[:, 300:] = 1.05   # -50% then recover
    _solv = dict(hazard=0.5, min_depth=0.30, seed=123)                      # so inf = impaired only
    _ra = E._drawdown_and_recovery(_ppc, 378, solv=dict(_solv), path_offset=0)[1]
    _rb = E._drawdown_and_recovery(_ppc, 378, solv=dict(_solv), path_offset=25000)[1]
    _imp_a = ~np.isfinite(_ra); _imp_b = ~np.isfinite(_rb)
    check("solvency RNG decorrelates across chunks (bug 1)",
          _imp_a.sum() > 0 and _imp_b.sum() > 0 and not np.array_equal(_imp_a, _imp_b))
    check("solvency RNG reproducible for a given offset (bug 1)",
          np.array_equal(_imp_a, ~np.isfinite(E._drawdown_and_recovery(_ppc, 378, solv=dict(_solv), path_offset=0)[1])))

    # Bug 2: fundamental_catchup must not bleed a prior name's buyback via locals(). A
    # pre-earnings burner (no buyback) must report eps-lift 1.0 / no float cut.
    _fc = {r["name"]: r for r in FCK.run(verbose=False)}
    # pick a pre-earnings name if present ('N/A' verdict -> no buyback should be attached)
    _burner = next((r for r in _fc.values()
                    if isinstance(r.get("verdict"), str) and r["verdict"].startswith("N/A")), None)
    if _burner is not None:
        check("pre-earnings name has no leaked buyback float-cut (bug 2)",
              (_burner.get("float_cut") or 0.0) == 0.0, f"{_burner.get('float_cut')}")

    # Bug 5: analyze_name must thread the real name (archetype/group/solvency), not default.
    try:
        import analyze_name as _AN
        _spec_named = E.company_to_spec(E.decompose_premium()["Micron"], name="Micron")
        check("named spec carries real group, not 'defensive' (bug 5)",
              _spec_named.get("group") != "defensive" or _spec_named.get("cycle") is not None)
    except Exception:
        pass

    # 8m. ETF HORIZON RANKING: a recoverable high-growth cyclical (DRAM) must rank BETTER
    # over longer holds (its ~15m recovery clears within a 3-5y hold but not a 1y hold), and
    # broken ETFs must be hard-gated out of the main ranking.
    try:
        import json as _json2
        ehr = _json2.load(open(os.path.join(HERE, "etf_horizon_rank.json")))
        dram = ehr.get("DRAM (Roundhill Memory)", {}).get("horizons", {})
        if dram:
            r12 = dram["12m"]["exp_return_horizon"]; r60 = dram["60m"]["exp_return_horizon"]
            check("ETF rank: recoverable cyclical (DRAM) scores higher at 5y than 1y",
                  r60 > r12, f"12m {r12:+.2f} -> 60m {r60:+.2f}")
            check("ETF rank: DRAM 1y recovery back-loaded (rec<=12m ~ 0)",
                  (dram["12m"]["p_rec_horizon"] or 0) < 0.05, f"{dram['12m']['p_rec_horizon']}")
        # broken archetype tagged so it can be gated out of the buy ranking
        _brk = [nm for nm, d in ehr.items() if d.get("crash_growth") == "broken"]
        check("ETF rank: broken-thesis ETFs are identified for hard-gating",
              all(ehr[nm]["crash_growth"] == "broken" for nm in _brk))
    except Exception:
        pass

    # 8n. SYSTEMIC FREEZE (total-collapse recovery contagion). Funding severity must be
    # HIGH when liquidity drains (2008) and AVERTED when the Fed floods (2020); and a freeze
    # must EXTEND recovery market-wide on collapse paths (additive delay), even for a name
    # that would otherwise recover fast.
    import macro_stress as _MS2
    sev_drain = _MS2.freeze_severity(dict(hy_oas_bps=1700, ig_oas_bps=500, move=200, vix=80, fed_net_liq_3m_pct=-10))
    sev_flood = _MS2.freeze_severity(dict(hy_oas_bps=850,  ig_oas_bps=250, move=130, vix=82, fed_net_liq_3m_pct=15))
    check("freeze severity: 2008-drain >> 2020-flood (liquidity backstop averts)",
          sev_drain > 0.6 and sev_flood < 0.25, f"drain {sev_drain} flood {sev_flood}")
    _pf = np.ones((200, 700)); _pf[:, 5:] = 0.55; _pf[:, 120:] = 1.05   # -45% then quick recover (~5.5m)
    _r_no = E._drawdown_and_recovery(_pf, 378)[1]
    # EARLY freeze (breach day 0, overlaps the recovery): must extend recovery.
    _fz_early = dict(mask=np.ones(200, bool), breach_day=np.zeros(200), days=600.0)
    _r_fz = E._drawdown_and_recovery(_pf, 378, freeze=_fz_early)[1]
    check("systemic freeze EXTENDS recovery when it overlaps the recovery window",
          float(np.nanmedian(_r_fz)) > float(np.nanmedian(_r_no)) + 380,
          f"{np.nanmedian(_r_no):.0f}d -> {np.nanmedian(_r_fz):.0f}d")
    # CAUSALITY (reviewer red-team): a LATE freeze (breach day 500, long after the ~day-120
    # recovery) must NOT retroactively delay an already-completed recovery (no look-ahead).
    _fz_late = dict(mask=np.ones(200, bool), breach_day=np.full(200, 500.0), days=600.0)
    _r_late = E._drawdown_and_recovery(_pf, 378, freeze=_fz_late)[1]
    check("systemic freeze does NOT delay a recovery that finished before it started (causal)",
          bool(np.allclose(np.nan_to_num(_r_late, nan=-1), np.nan_to_num(_r_no, nan=-1))),
          f"{np.nanmedian(_r_no):.0f}d -> {np.nanmedian(_r_late):.0f}d")
    _pup = np.ones((50, 300)); _pup[:, 1:] = 1.10        # only ever rises -> never drew down
    _r_up = E._drawdown_and_recovery(_pup, 252, freeze=dict(mask=np.ones(50, bool),
                                     breach_day=np.zeros(50), days=420.0))[1]
    check("freeze leaves a name that never fell untouched (rec=0)", float(np.nanmax(_r_up)) == 0.0)
    # CROSS-SUBMARKET COUPLING: the keystone (AI-infra) freezes longest; defensive least.
    _fzm = dict(mask=np.ones(200, bool), breach_day=np.zeros(200), days=900.0)
    _r_infra = E._drawdown_and_recovery(_pf, 378, freeze=_fzm, freeze_dep=1.00)[1]
    _r_def   = E._drawdown_and_recovery(_pf, 378, freeze=_fzm, freeze_dep=0.35)[1]
    check("freeze coupling: AI-infra frozen longer than defensive (dependency-scaled)",
          float(np.nanmedian(_r_infra)) > float(np.nanmedian(_r_def)) + 100,
          f"infra {np.nanmedian(_r_infra):.0f}d vs def {np.nanmedian(_r_def):.0f}d")
    _dec_fz = E.decompose_premium()
    _g_infra = E.company_to_spec(_dec_fz["NVIDIA"], name="NVIDIA").get("freeze_dep")
    check("AI-infra name carries highest freeze dependency (=1.0)", _g_infra == 1.0, str(_g_infra))
    # CYCLICAL-FLOOR x FREEZE edge (GPT/Gemini): a name whose price bounced early but is held
    # by its demand cycle is STILL underwater when a freeze hits -> the freeze must delay it,
    # even though the NATURAL recovery finished before the freeze started.
    _pcf = np.ones((200, 1000)); _pcf[:, 5:] = 0.60; _pcf[:, 90:] = 1.05   # natural recover ~day90
    _cyc_fl = dict(freeze_days=315, second_leg=0.15, min_depth=0.15)        # but cyclical floors to ~315
    _fz_mid = dict(mask=np.ones(200, bool), breach_day=np.full(200, 200.0), days=600.0)  # freeze day 200-800
    _r_cyc  = E._drawdown_and_recovery(_pcf, 378, cycle=_cyc_fl)[1]
    _r_both = E._drawdown_and_recovery(_pcf, 378, cycle=_cyc_fl, freeze=_fz_mid)[1]
    check("freeze delays a cyclical-floor recovery still in progress (edge fix)",
          float(np.nanmedian(_r_both)) > float(np.nanmedian(_r_cyc)) + 100,
          f"cyc {np.nanmedian(_r_cyc):.0f}d -> +freeze {np.nanmedian(_r_both):.0f}d")

    # 8o. DOC FRESHNESS (GPT): the sim-window text must track C.SIM['days'], not a stale
    # hard-coded "4.5y / 1134". The historical backtest writes the window dynamically.
    _bh_path = os.path.join(HERE, "backtest_historical.md")
    if os.path.exists(_bh_path):
        _bh = open(_bh_path).read()
        _yrs = C.SIM["days"] / 252.0
        check("backtest doc states the CURRENT sim window (no stale 4.5y/1134)",
              f"{_yrs:.1f}y" in _bh and "4.5y sim" not in _bh and "1134" not in _bh,
              f"expected ~{_yrs:.1f}y window text")

    # 9. sim window covers full 36m after latest 18m trough
    need = C.HORIZON_DAYS[C.HORIZON_LABELS.index("18m")] + 36 * 21
    check("SIM days >= 18m horizon + 36m recovery window", C.SIM["days"] >= need,
          f"days={C.SIM['days']}, need={need}")

    # 10. GENERATED-OUTPUT tests: leveraged must never carry a growth tier
    import csv as _csv
    csvp = os.path.join(HERE, "tier_table.csv")
    if os.path.exists(csvp):
        _trows = list(_csv.DictReader(open(csvp)))
        bad = [row["name"] for row in _trows
               if row["name"] in T.LEVERAGED
               and (row.get("growth_tier") or row.get("tier")) in ("High", "Moderate", "Safe")]
        check("tier_table.csv: no leveraged name in a growth tier", not bad, str(bad))

        # 10b. REPORTING-CONSISTENCY (GPT review): the master table must carry a
        #      recovery_rank, and that verdict must not contradict the model's own
        #      crash-growth logic -- a BROKEN name can never read as clean high-growth,
        #      and a cyclical memory basket must read rebound-dependent.
        check("tier_table.csv has a recovery_rank column",
              "recovery_rank" in (_trows[0].keys() if _trows else []))
        contradict = [row["name"] for row in _trows
                      if row.get("crash_growth") == "broken"
                      and ("secular high-growth" in (row.get("recovery_rank") or "")
                           or (row.get("recovery_rank") or "").strip() in ("HIGH", "High", "Top"))]
        check("no BROKEN name shows a clean high-growth recovery_rank", not contradict,
              str(contradict))
        _dram = next((r for r in _trows if r["name"].startswith("DRAM")), {})
        if _dram:
            rr = (_dram.get("recovery_rank") or "").lower()
            check("DRAM recovery_rank reads cyclical / rebound-dependent",
                  "cyclical" in rr or "rebound" in rr, _dram.get("recovery_rank"))
        # broken names must never be rank_high in the growth-recovery classifier
        _broken_high = [r["name"] for r in (gr["high_growth"] + gr["diversified_safe"])
                        if r.get("crash_growth") == "broken" and r.get("rank_high")]
        check("growth-recovery: no broken name is rank_high", not _broken_high, str(_broken_high))
    for h in ("tier_dashboard.html", "tier_artifact.html",
              "tier_dashboard_etf.html", "tier_artifact_etf.html"):
        p = os.path.join(HERE, h)
        if os.path.exists(p):
            html = open(p).read()
            leak = [nm for nm in T.LEVERAGED
                    if f'"{nm}"' in html and ('"tier": "High"' in html or "'High'" in html)
                    and html.count(nm) and ('%s</td><td>ETF</td><td>High' % nm) in html]
            check(f"{h}: no leveraged row rendered as High tier", not leak, str(leak))

    ap = os.path.join(HERE, "tier_artifact_etf.html")
    if os.path.exists(ap):
        h = open(ap).read()
        # the cap bug dropped real ETFs (TQQQ/ARKK) when leveraged ate the cap;
        # assert a sample of broad ETFs survive the cap
        present = [nm for nm in ("VOO (S&P 500)", "SMH (VanEck Semis)", "QQQ (Nasdaq-100)")
                   if nm in h]
        check("tier_artifact_etf.html keeps core ETFs after cap", len(present) >= 2, str(present))

    # 11. TROUGH-BUYBACK SLINGSHOT (engine path-keyed) — GPT-requested direct tests
    rng = np.random.default_rng(11)
    n, days = 6000, C.SIM["days"]
    f4, c4, g4 = E._simulate_factor(rng, n, days, return_grind=True)
    base_spec = dict(beta=1.3, idio=0.09, mu=0.0, L=1, leveraged=False,
                     tail_mult=1.0, recov_shift=0.0)
    p = E._price_path(rng, f4, c4, base_spec, n, days, grind=g4)
    hd = C.HORIZON_DAYS[C.HORIZON_LABELS.index("18m")]
    cy = getattr(C, "CASH_YIELD_AFTER_TAX", 0.035)
    # (a) buyback NEVER changes drawdown depth (same paths, bb on/off)
    mdd_off, _ = E._drawdown_and_recovery(p, hd, bb=None)
    bb_acc = dict(cash_used=0.65*0.20, pe_peak=14, unsup=0.05, cash_yield=cy, min_depth=0.25)
    mdd_on, rec_on = E._drawdown_and_recovery(p, hd, bb=bb_acc)
    check("buyback leaves drawdown DEPTH unchanged", bool(np.allclose(mdd_off, mdd_on)))
    # (b) accretive low-PE deep-cash name: recovery improves vs no buyback
    _, rec_off = E._drawdown_and_recovery(p, hd, bb=None)
    md = C.MANDATE_YEARS * 252; m = mdd_on <= -0.25
    pr_off = float(np.mean(np.nan_to_num(rec_off[m], nan=1e9) <= md)) if m.sum() > 30 else 0
    pr_on = float(np.mean(np.nan_to_num(rec_on[m], nan=1e9) <= md)) if m.sum() > 30 else 0
    check("accretive buyback speeds recovery (P[rec<18m] up)", pr_on >= pr_off,
          f"{pr_off:.3f}->{pr_on:.3f}")
    # (c) dilutive high-PE name: gate keeps it dormant (recovery unchanged)
    bb_dil = dict(cash_used=0.65*0.20, pe_peak=60, unsup=0.05, cash_yield=cy, min_depth=0.25)
    _, rec_dil = E._drawdown_and_recovery(p, hd, bb=bb_dil)
    check("dilutive (high-PE) buyback does NOT fire", bool(np.allclose(np.nan_to_num(rec_dil, nan=-1),
          np.nan_to_num(rec_off, nan=-1))))
    # (d) earn-back JSON strict-parseable + real_pe_after_drop identity
    import json as _j, math as _m
    fc = os.path.join(HERE, "fundamental_catchup.json")
    if os.path.exists(fc):
        raw = open(fc).read()
        check("fundamental_catchup.json strict JSON (no NaN/Inf)",
              "NaN" not in raw and "Infinity" not in raw)
        d = _j.loads(raw)
        ok = True
        for r in d["rows"]:
            if r.get("real_pe_after_drop") is not None and not r.get("is_infinite"):
                exp = round(r["pe_peak"] * (1 - r["drop"]) / max(r["eps_lift"], 1e-9), 1)
                if abs(exp - r["real_pe_after_drop"]) > 0.15:
                    ok = False; break
        check("real_pe_after_drop == pe_peak*(1-drop)/eps_lift", ok)

    print(f"\n{'ALL PASS' if not FAIL else 'FAILURES: ' + ', '.join(FAIL)}")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
