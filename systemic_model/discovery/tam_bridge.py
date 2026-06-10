"""
============================================================================
 TAM_BRIDGE  --  systemic_model / discovery
============================================================================
 THE MISSING SEAM between discovery and analysis -- the automatable half of
 the "TAM & SAM" stage (Stage 3 in the white paper).

 WHY THIS EXISTS
   The discovery screen surfaces names (Lumentum, Coherent, IonQ, optical and
   semis ETFs, ...), but the Monte-Carlo engine cannot price a name until that
   name has the bottom-up inputs the premium-decomposition needs:

       rev_bn, tam_bn, tam_cagr, fwd_pe, beta,
       quality, earn_quality, dominance, capex_elastic

   Until those are filled in, a discovery pick is "surfaced but not modeled" --
   which is exactly the gap the consolidated report flagged. This module fills
   it, and does so in the two distinct ways the two kinds of asset require.

 TWO CASES
   1. SINGLE STOCKS -- a researched block of TAM facts per name (STOCK_TAM_FACTS
      below). These are the output of the TAM stage: revenue and the served
      addressable market, plus the four honest judgment scores the model sweeps.

   2. ETFs -- an ETF has NO standalone TAM of its own. Its addressable market is
      the holdings-weighted aggregate of its constituents' TAMs, and likewise
      its revenue, its multiple, its beta, and its judgment scores. Penetration
      then emerges as (aggregate revenue / aggregate TAM), exactly as for a
      single name -- so the synthetic ETF drops straight into the same engine.
      This is the rule: *an ETF's TAM is defined in relation to its holdings.*

 HONESTY
   rev_bn / fwd_pe are forward / annualized; tam_bn is a served-market estimate
   reconciled from public market-research ranges; the four scores are judgments,
   not measurements (which is why the model sweeps them). Every figure is dated.
   ETF aggregation uses ONLY the holdings we have facts for, renormalizes the
   weights over that covered subset, and REPORTS the coverage so the gap is
   visible rather than hidden.

 RESEARCH MODEL, NOT INVESTMENT ADVICE.
============================================================================
"""

AS_OF = "2026-06-03"

# Fields the engine's decompose_premium() consumes. Kept here so build_* can
# validate that every produced spec is complete.
REQUIRED_FIELDS = ("rev_bn", "tam_bn", "tam_cagr", "fwd_pe", "beta",
                   "quality", "earn_quality", "dominance", "capex_elastic")


# ===========================================================================
#  1. SINGLE-STOCK TAM FACTS  (the researched TAM-stage output)
#     rev_bn  : forward / annualized revenue, $B          [MEASURED ~Jun 2026]
#     tam_bn  : served addressable market, $B              [DERIVED from research]
#     tam_cagr: addressable-market growth rate             [MEASURED/DERIVED]
#     fwd_pe  : forward P/E                                 [MEASURED]
#     beta    : loading on the market factor               [JUDGMENT/MEASURED]
#     quality / earn_quality / dominance / capex_elastic   [JUDGMENT, swept]
# ===========================================================================
STOCK_TAM_FACTS = {
    # memory leaders -- added so the DRAM ETF is priced across its 3 real holdings
    # (Micron + Samsung + SK Hynix), not Micron-only. Cyclical dollar-TAM.
    "Samsung": dict(rev_bn=210.0, tam_bn=200, tam_cagr=0.18, fwd_pe=13, beta=1.10,
                    quality=0.75, earn_quality=0.55, dominance=0.40, capex_elastic=0.45,
                    role="diversified memory+foundry+devices; fortress B/S; cyclical DRAM/NAND"),
    "SK Hynix": dict(rev_bn=45.0, tam_bn=90, tam_cagr=0.22, fwd_pe=11, beta=1.40,
                     quality=0.65, earn_quality=0.45, dominance=0.30, capex_elastic=0.40,
                     role="memory pure-play, HBM leader; moderate debt; deeply cyclical"),
    "Lumentum": dict(
        rev_bn=3.0, tam_bn=25, tam_cagr=0.30, fwd_pe=50, beta=1.50,
        quality=0.78, earn_quality=0.65, dominance=0.45, capex_elastic=0.65,
        role="AI optical interconnect + lasers; FY25 $1.65B, FY26 run-rate "
             "inflecting to ~$3B (+85% YoY guide); datacom-driven"),
    "Coherent": dict(
        rev_bn=6.5, tam_bn=45, tam_cagr=0.28, fwd_pe=49, beta=1.55,
        quality=0.78, earn_quality=0.70, dominance=0.50, capex_elastic=0.65,
        role="datacom optics + lasers + materials; FY25 $5.81B (+23% YoY); "
             "broadest optical franchise"),
    "Applied Optoelectronics": dict(
        rev_bn=0.46, tam_bn=20, tam_cagr=0.30, fwd_pe=40, beta=1.70,
        quality=0.55, earn_quality=0.40, dominance=0.20, capex_elastic=0.60,
        role="800G/1.6T transceivers; FY25 $456M (+83% YoY); small, "
             "single-customer-sensitive, volatile"),
    "IonQ": dict(
        rev_bn=0.235, tam_bn=15, tam_cagr=0.42, fwd_pe=200, beta=1.90,
        quality=0.40, earn_quality=0.15, dominance=0.55, capex_elastic=0.30,
        role="trapped-ion quantum; 2026 guide $225-245M but deeply pre-earnings. "
             "fwd_pe=200 is a SENTINEL for 'no real earnings yet' -> premium is "
             "almost entirely floating. This is the red-team's exhibit A: a high "
             "discovery score that is arithmetic on a tiny base, not substance."),

    # ---- added Jun 2026: AI-software / megacap test set -------------------
    "Palantir": dict(
        rev_bn=4.5, tam_bn=250, tam_cagr=0.35, fwd_pe=95, beta=1.52,
        quality=0.75, earn_quality=0.60, dominance=0.75, capex_elastic=0.55,
        role="AI/data-analytics software; FY25 $4.48B (+56%), FY26 guide +61%. "
             "Real gov+commercial moat (AIP), but fwd_pe ~95 = premium largely "
             "floating; durable demand but rich multiple is the fragility."),
    "AppLovin": dict(
        rev_bn=5.5, tam_bn=80, tam_cagr=0.20, fwd_pe=29, beta=2.37,
        quality=0.65, earn_quality=0.55, dominance=0.65, capex_elastic=0.30,
        role="ad-tech / AXON engine; FY25 $5.48B (+70%). Cheaper multiple but "
             "beta 2.37 (deepest falls) and ad spend is DISCRETIONARY (freezes "
             "in a credit crash) -> low capex_elastic, weak recovery floor."),
    "Meta": dict(
        rev_bn=185, tam_bn=900, tam_cagr=0.15, fwd_pe=18, beta=1.23,
        quality=0.85, earn_quality=0.85, dominance=0.85, capex_elastic=0.55,
        role="digital advertising + AI; fwd_pe 18 is modest for the growth, so "
             "little floating premium; durable earnings, strong moat."),
    "Microsoft": dict(
        rev_bn=290, tam_bn=1500, tam_cagr=0.18, fwd_pe=23, beta=1.10,
        quality=0.90, earn_quality=0.90, dominance=0.85, capex_elastic=0.75,
        role="cloud + enterprise software + AI; lowest beta of the set, sticky "
             "inelastic enterprise demand -> the strongest recovery floor."),
    "Amazon": dict(
        rev_bn=680, tam_bn=3000, tam_cagr=0.15, fwd_pe=29, beta=1.47,
        quality=0.85, earn_quality=0.80, dominance=0.80, capex_elastic=0.65,
        role="retail + AWS cloud + ads; fwd_pe 29 mostly justified by AWS "
             "runway; durable, diversified, defensible."),
    "Tesla": dict(
        rev_bn=95, tam_bn=3000, tam_cagr=0.15, fwd_pe=215, beta=2.20,
        quality=0.55, earn_quality=0.45, dominance=0.55, capex_elastic=0.40,
        role="EV + robotaxi/AI + energy; FY25 rev $94.8B (-3%), Q1'26 +16% "
             "rebound; fwd P/E ~215 = premium almost entirely floating, very "
             "high beta. ARKK's top holding (~10%)."),

    # ---- added Jun 2026: tier-filling set (mature megacaps + high-growth AI) ----
    "Apple": dict(
        rev_bn=451, tam_bn=2000, tam_cagr=0.08, fwd_pe=35, beta=1.09,
        quality=0.85, earn_quality=0.90, dominance=0.85, capex_elastic=0.55,
        role="devices + services; LTM ~$451B, low-single-digit growth; sticky "
             "ecosystem, durable earnings — safe but slow."),
    "Alphabet": dict(
        rev_bn=380, tam_bn=2500, tam_cagr=0.13, fwd_pe=29, beta=1.05,
        quality=0.85, earn_quality=0.88, dominance=0.85, capex_elastic=0.55,
        role="search/ads + Google Cloud + AI; ~12% growth, dominant ads moat."),
    "Oracle": dict(
        rev_bn=57, tam_bn=500, tam_cagr=0.18, fwd_pe=23, beta=1.05,
        quality=0.80, earn_quality=0.80, dominance=0.60, capex_elastic=0.70,
        role="enterprise DB + OCI cloud; FY25 $57B, OCI re-accelerating growth."),
    "Texas Instruments": dict(
        rev_bn=18.4, tam_bn=200, tam_cagr=0.10, fwd_pe=33, beta=1.00,
        quality=0.85, earn_quality=0.85, dominance=0.75, capex_elastic=0.60,
        role="analog/embedded; LTM $18.4B (+15% YoY), industrial+DC led; rich "
             "multiple for the growth."),
    "Cisco": dict(
        rev_bn=56, tam_bn=400, tam_cagr=0.06, fwd_pe=16, beta=0.90,
        quality=0.75, earn_quality=0.85, dominance=0.70, capex_elastic=0.65,
        role="networking + security; ~$56B, low growth, cheap multiple, durable."),
    "IBM": dict(
        rev_bn=64, tam_bn=600, tam_cagr=0.05, fwd_pe=21, beta=0.70,
        quality=0.65, earn_quality=0.80, dominance=0.55, capex_elastic=0.70,
        role="hybrid cloud + consulting + AI; ~$64B, slow growth, low beta."),
    "Astera Labs": dict(
        rev_bn=0.85, tam_bn=30, tam_cagr=0.45, fwd_pe=90, beta=2.0,
        quality=0.75, earn_quality=0.55, dominance=0.55, capex_elastic=0.55,
        role="AI connectivity (retimers/CXL); FY25 ~$0.72B (+115% YoY); very "
             "high beta, rich multiple — high growth, fragile."),
    "Vertiv": dict(
        rev_bn=9.0, tam_bn=60, tam_cagr=0.20, fwd_pe=30, beta=1.50,
        quality=0.75, earn_quality=0.70, dominance=0.55, capex_elastic=0.55,
        role="AI data-center power & cooling; ~$9B, ~28% growth; physical "
             "infra picks-and-shovels."),
    "CoreWeave": dict(
        rev_bn=5.1, tam_bn=250, tam_cagr=0.40, fwd_pe=120, beta=2.40,
        quality=0.55, earn_quality=0.30, dominance=0.40, capex_elastic=0.40,
        role="AI GPU cloud; FY25 $5.1B (from $1.9B), explosive but debt-heavy, "
             "barely profitable, very high beta. fwd_pe=120 ~ sentinel; premium "
             "largely floating — the high-growth/high-fragility archetype."),
}

# Names where the P/E is a sentinel (no real earnings); flagged so downstream
# code and humans treat their decomposition as 'premium ~ all floating'.
PRE_EARNINGS = {"IonQ"}


# ===========================================================================
#  2. ETF HOLDINGS  (constituent weights, % of fund)
#     Source: stockanalysis.com / issuer fact sheets, ~late May 2026.
#     Only holdings we have TAM facts for are listed; weights are renormalized
#     over the covered subset in etf_spec(), and coverage is reported. Weights
#     for names beyond each fund's published top-5 are approximate [JUDGMENT].
# ===========================================================================
# Names with no entry in our fact base (TSMC, Intel, and the long tail) are
# listed too, so that coverage is computed against the WHOLE fund and the
# uncovered share is honestly reported rather than silently dropped.
ETF_HOLDINGS = {
    "SMH (VanEck Semis)": {
        # published top holdings: NVDA 15.2, TSM 9.4, MU 7.8, AMD 7.6, INTC 7.2
        "NVIDIA": 0.152, "Micron": 0.078, "AMD": 0.076,
        "Broadcom": 0.045, "Qualcomm": 0.040, "Marvell": 0.030, "ARM": 0.028,
        # uncovered (no TAM facts) -> counted toward the fund, excluded from agg:
        "TSMC": 0.094, "Intel": 0.072, "_other_": 0.385,
    },
    "SOXX (iShares Semis)": {
        # published top holdings: MU 11.0, AMD 9.5, AVGO 6.6, INTC 6.5, MRVL 6.2
        "Micron": 0.110, "AMD": 0.095, "Broadcom": 0.066, "Marvell": 0.062,
        "NVIDIA": 0.050, "Qualcomm": 0.045, "ARM": 0.030,
        # uncovered:
        "Intel": 0.065, "_other_": 0.477,
    },

    # ---- added Jun 2026 test set ----------------------------------------
    "DRAM (Roundhill Memory)": {
        # highly concentrated: Samsung 25, SK Hynix 24, Micron 24 (=72%)
        "Micron": 0.24,
        "Samsung": 0.25, "SK Hynix": 0.24, "_other_": 0.27,   # uncovered
    },
    "QTUM (Defiance Quantum)": {
        # broad, near-equal-weight quantum/compute basket (~70 holdings)
        "Micron": 0.030, "NVIDIA": 0.020, "AMD": 0.020, "Marvell": 0.020,
        "Broadcom": 0.020, "Qualcomm": 0.018, "ARM": 0.015, "IonQ": 0.015,
        # uncovered (Intel, MediaTek, STMicro, Nokia, Rigetti, ... long tail):
        "Intel": 0.026, "MediaTek": 0.025, "_other_": 0.791,
    },
    "AIQ (Global X AI)": {
        # SK Hynix 7, Micron 6, Samsung 5.1, AMD 4.6, Intel 3.9 + big tech
        "Micron": 0.060, "AMD": 0.046, "NVIDIA": 0.040, "Microsoft": 0.040,
        "Meta": 0.035, "Amazon": 0.035, "Broadcom": 0.030, "Palantir": 0.020,
        # uncovered:
        "SK Hynix": 0.070, "Samsung": 0.051, "Intel": 0.039, "_other_": 0.534,
    },
    "CHAT (Roundhill GenAI)": {
        # Micron 6.2, SK Hynix 6.0, NVDA 6.0, AMD 5.5, Alphabet 5.4 + big tech
        "Micron": 0.062, "NVIDIA": 0.060, "AMD": 0.055, "Meta": 0.040,
        "Microsoft": 0.040, "Amazon": 0.035, "Broadcom": 0.030, "Palantir": 0.025,
        # uncovered:
        "SK Hynix": 0.060, "Alphabet": 0.054, "_other_": 0.539,
    },
}


# ===========================================================================
#  3b. BROAD ETFs (direct specs)  --  baskets whose holdings are mostly OUTSIDE
#      our priced universe (broad market, dividend, innovation), so we give them
#      aggregate characteristics directly rather than holdings-aggregating.
#      rev_bn/tam_bn are abstract units chosen to set a sensible penetration.
#      [JUDGMENT, Jun 2026]
# ===========================================================================
ETF_DIRECT_SPECS = {
    "ARKK (ARK Innovation)": dict(
        rev_bn=5, tam_bn=100, tam_cagr=0.32, fwd_pe=55, beta=1.95,
        quality=0.50, earn_quality=0.40, dominance=0.40, capex_elastic=0.40,
        role="disruptive-innovation basket LED BY TESLA (~10%), then AMD, "
             "CRISPR, Tempus AI, Robinhood. High beta, rich multiples, "
             "Tesla-driven idiosyncratic swings — NOT a semis basket."),
    "QQQ (Nasdaq-100)": dict(
        rev_bn=22, tam_bn=100, tam_cagr=0.12, fwd_pe=28, beta=1.15,
        quality=0.80, earn_quality=0.82, dominance=0.80, capex_elastic=0.65,
        role="Nasdaq-100 mega-cap tech; quality, but rich and tech-tilted."),
    "VOO (S&P 500)": dict(
        rev_bn=25, tam_bn=100, tam_cagr=0.08, fwd_pe=22, beta=1.00,
        quality=0.82, earn_quality=0.85, dominance=0.75, capex_elastic=0.70,
        role="broad US large-cap; the market itself — durable, diversified."),
    "SCHD (Dividend)": dict(
        rev_bn=30, tam_bn=100, tam_cagr=0.05, fwd_pe=16, beta=0.85,
        quality=0.78, earn_quality=0.90, dominance=0.70, capex_elastic=0.80,
        role="quality-dividend value basket; low beta, cheap, durable earnings."),
    # ---- data-center power / grid / cooling / infra (the AI 'picks & shovels') ----
    "DTCR (Data Ctr Infra)": dict(
        rev_bn=20, tam_bn=100, tam_cagr=0.14, fwd_pe=30, beta=0.95,
        quality=0.78, earn_quality=0.80, dominance=0.70, capex_elastic=0.78,
        role="data-center REITs & digital infra (Equinix, Digital Realty, "
             "American Tower); physical, contracted, durable — low beta."),
    "GRID (Smart Grid)": dict(
        rev_bn=18, tam_bn=120, tam_cagr=0.18, fwd_pe=27, beta=1.10,
        quality=0.75, earn_quality=0.75, dominance=0.60, capex_elastic=0.70,
        role="grid/power equipment for the AI electricity demand (Eaton, "
             "Quanta, GE Vernova); inelastic infra spend."),
    "NUKE (Nuclear/Uranium)": dict(
        rev_bn=14, tam_bn=120, tam_cagr=0.22, fwd_pe=28, beta=1.40,
        quality=0.65, earn_quality=0.60, dominance=0.55, capex_elastic=0.60,
        role="nuclear/uranium for data-center baseload (Constellation, Vistra, "
             "Cameco, BWX); high-growth but cyclical/volatile."),
    "VGT (Info Tech)": dict(
        rev_bn=24, tam_bn=120, tam_cagr=0.15, fwd_pe=30, beta=1.15,
        quality=0.82, earn_quality=0.85, dominance=0.80, capex_elastic=0.65,
        role="broad US information-technology sector; mega-cap heavy, durable."),
    "IGV (Software)": dict(
        rev_bn=16, tam_bn=120, tam_cagr=0.20, fwd_pe=40, beta=1.25,
        quality=0.78, earn_quality=0.78, dominance=0.65, capex_elastic=0.60,
        role="application & infrastructure software basket; higher multiple, "
             "subscription-durable."),
}

# Leveraged ETFs (3x daily reset). NOT priced via the TAM path — their recovery
# is computed through the leveraged price path (volatility decay) and injected
# into results by add_leveraged.py. Listed here only for reference.
LEVERAGED_ETFS = {
    "TECL (3x Tech)":  dict(exposure="TECL (3x Tech)",  growth=0.50),
    "SOXL (3x Semis)": dict(exposure="SOXL (3x Semis)", growth=0.60),
    "TQQQ (3x NDX)":   dict(exposure="TQQQ (3x NDX)",   growth=0.45),
}


# ===========================================================================
#  BUILDERS
# ===========================================================================
def _validate(name, spec):
    missing = [f for f in REQUIRED_FIELDS if f not in spec]
    if missing:
        raise ValueError(f"{name}: spec missing required fields {missing}")
    return spec


def stock_spec(name):
    """Return a COMPANIES-format spec for a single researched stock."""
    f = STOCK_TAM_FACTS[name]
    spec = {k: f[k] for k in REQUIRED_FIELDS}
    spec["role"] = f.get("role", "")
    return _validate(name, spec)


def etf_spec(etf_name, company_facts):
    """Build a synthetic-company spec for an ETF from its holdings.

    company_facts: dict {name -> spec} of every name we can price (the model's
      existing COMPANIES merged with the bridged stocks). The ETF aggregates
      over whichever of its holdings appear here.

    Aggregation rules (all weighted by renormalized holding weight w_i):
      rev_bn, tam_bn : weighted sums  -> penetration = Σw·rev / Σw·tam emerges
      beta, tam_cagr : weighted means (betas are additive in a portfolio)
      fwd_pe         : portfolio P/E via earnings-yield weighting,
                       1 / Σ(w_i / PE_i)  (correct way to blend multiples)
      4 scores       : weighted means
    Returns (spec, info) where info carries coverage and the weights used.
    """
    holdings = ETF_HOLDINGS[etf_name]
    covered = {t: w for t, w in holdings.items() if t in company_facts}
    if not covered:
        raise ValueError(f"{etf_name}: none of its listed holdings are priceable")
    total_w = sum(holdings.values())
    cov_w = sum(covered.values())
    coverage = cov_w / total_w
    w = {t: covered[t] / cov_w for t in covered}          # renormalize to 1.0

    g = company_facts
    rev = sum(w[t] * g[t]["rev_bn"] for t in w)
    tam = sum(w[t] * g[t]["tam_bn"] for t in w)
    beta = sum(w[t] * g[t]["beta"] for t in w)
    tam_cagr = sum(w[t] * g[t]["tam_cagr"] for t in w)
    inv_pe = sum(w[t] / g[t]["fwd_pe"] for t in w if g[t]["fwd_pe"] > 0)
    fwd_pe = (1.0 / inv_pe) if inv_pe > 0 else float("inf")
    scores = {s: sum(w[t] * g[t][s] for t in w)
              for s in ("quality", "earn_quality", "dominance", "capex_elastic")}

    spec = dict(rev_bn=rev, tam_bn=tam, tam_cagr=tam_cagr, fwd_pe=fwd_pe,
                beta=beta, role=(f"ETF (holdings-weighted): {len(w)} priceable "
                                 f"constituents = {coverage*100:.0f}% of fund weight"),
                **scores)
    info = dict(coverage=coverage, weights=w,
                excluded=[t for t in holdings if t not in covered])
    return _validate(etf_name, spec), info


def build_company_universe(stock_names=None, etf_names=None, base_companies=None,
                           verbose=True):
    """Produce a {name -> spec} dict ready to merge into calibration.COMPANIES.

    stock_names : which STOCK_TAM_FACTS to include (default: all)
    etf_names   : which ETFs to include (default: all)
    base_companies : the existing model COMPANIES, so ETFs can aggregate over
                     names already in the model as well as the newly bridged
                     stocks. (Pass calibration.COMPANIES.)
    """
    if stock_names is None:
        stock_names = list(STOCK_TAM_FACTS.keys())
    if etf_names is None:
        etf_names = list(ETF_HOLDINGS.keys())

    # the price-able fact base = existing model names + newly bridged stocks
    facts = dict(base_companies or {})
    new = {}
    for nm in stock_names:
        spec = stock_spec(nm)
        new[nm] = spec
        facts[nm] = spec
    if verbose:
        print(f"  bridged {len(new)} stocks: {', '.join(new)}")

    # broad ETFs with direct specs (not holdings-aggregated)
    for nm, f in ETF_DIRECT_SPECS.items():
        spec = {k: f[k] for k in REQUIRED_FIELDS}
        spec["role"] = f.get("role", "")
        new[nm] = spec
        facts[nm] = spec

    etf_info = {}
    for nm in etf_names:
        spec, info = etf_spec(nm, facts)
        new[nm] = spec
        etf_info[nm] = info
        if verbose:
            pen = spec["rev_bn"] / spec["tam_bn"]
            print(f"  bridged ETF {nm}: pen={pen*100:.1f}%  fwdPE={spec['fwd_pe']:.0f}  "
                  f"beta={spec['beta']:.2f}  coverage={info['coverage']*100:.0f}%  "
                  f"(excluded: {', '.join(info['excluded']) or 'none'})")
    return new, etf_info


if __name__ == "__main__":
    # Self-test: build the universe against the real model COMPANIES and show
    # that every produced spec is complete and that ETF penetration emerges
    # sensibly from the holdings.
    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import calibration as C

    print("TAM-bridge self-test (against live COMPANIES):\n")
    new, etf_info = build_company_universe(base_companies=C.COMPANIES)
    print(f"\nProduced {len(new)} new priceable names.")
    print("\nSpec sanity (penetration = rev/TAM, premium vs BASE_PE=18):")
    for nm, s in new.items():
        pen = s["rev_bn"] / s["tam_bn"]
        flag = "  <- PRE-EARNINGS sentinel" if nm in PRE_EARNINGS else ""
        print(f"  {nm:26s} rev={s['rev_bn']:6.2f}  tam={s['tam_bn']:6.1f}  "
              f"pen={pen*100:4.1f}%  fwdPE={s['fwd_pe']:5.0f}  beta={s['beta']:.2f}{flag}")
    print("\nIf every row has a sane penetration and the ETFs sit between their "
          "constituents, the bridge works.")
